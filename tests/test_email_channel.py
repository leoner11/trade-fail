#!/usr/bin/env python3
"""Email inquiry channel gate (docs/design-email-channel.md).

Drives glue._handle_email() DIRECTLY with a stubbed _email_send (capture
list) against the LIVE spine/calc/dify stack — IMAP/SMTP never touched.
Covers: spec answer, inline quote via calc, complaint escalation armed in
S4 Threads, Message-ID dedupe, transport dispatch of send_text/send_document.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_email_channel.py
Prereq: spine :8101 · glue code importable · calc :8100 (quote case).
"""
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, "glue")
import mock_responder as mr  # noqa: E402

GLUE = "http://127.0.0.1:8102"
SPINE = "http://127.0.0.1:8101"

sent = []          # captured outbound email
orig_send = mr._email_send


def fake_send(to, subject, body, attachments=None, in_reply_to=""):
    sent.append({"to": to, "subject": subject, "body": body,
                 "attachments": [p.name for p in attachments or []],
                 "in_reply_to": in_reply_to})


mr._email_send = fake_send

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} {name}" +
          (f"  [{detail}]" if detail and not cond else ""))
    passed += bool(cond)
    failed += not cond


def convo_by_jid(jid):
    req = urllib.request.Request(
        f"{SPINE}/conversations?include_last=1")
    with urllib.request.urlopen(req, timeout=15) as r:
        for c in json_items(r):
            if c.get("wa_jid") == jid:
                return c
    return None


def json_items(resp):
    import json
    return json.loads(resp.read()).get("items", [])


def messages(cid):
    with urllib.request.urlopen(f"{SPINE}/conversations/{cid}/messages",
                                timeout=15) as r:
        return json_items(r)


print("== E1: spec question -> KB/catalog answer via SMTP ==")
res = mr._handle_email("gate-e1@example.com", "Gate One",
                       "Inquiry from website",
                       "Hello, what can you tell me about the DG-50 generator?",
                       msg_id="<gate-e1@mjcx.test>")
check("handled + replied", res.get("ok") and res.get("replied"), str(res))
check("reply went to SMTP door (not evo)",
      bool(sent) and sent[-1]["to"] == "gate-e1@example.com")
check("subject threads as Re:",
      sent and sent[-1]["subject"].lower().startswith("re: inquiry"),
      sent[-1]["subject"] if sent else "")
check("in-reply-to header kept",
      sent and sent[-1]["in_reply_to"] == "<gate-e1@mjcx.test>")
c1 = convo_by_jid("email:gate-e1@example.com")
check("mirrored into S4 threads", c1 is not None)

print("== E2: price ask -> inline computed quote (calc authority) ==")
n_before = len(sent)
res = mr._handle_email("gate-e2@example.com", "Gate Two", "Quote request",
                       "Please quote 2 units of DG-30 STD.",
                       msg_id="<gate-e2@mjcx.test>")
body = sent[-1]["body"] if len(sent) > n_before else ""
check("handled + replied", res.get("ok") and res.get("replied"), str(res))
check("contains a computed number (USD total)",
      any(ch.isdigit() for ch in body), body[:120])

print("== E3: complaint -> escalation armed, holding line TRUE ==")
n_before = len(sent)
res = mr._handle_email("gate-e3@example.com", "Gate Three", "Serious issue",
                       "I am very unhappy, this is a formal complaint about my order.",
                       msg_id="<gate-e3@mjcx.test>")
check("holding reply sent", len(sent) > n_before)
c3 = convo_by_jid("email:gate-e3@example.com")
armed = False
if c3:
    rows = messages(c3["id"])
    armed = (str(c3.get("escalation_tag") or "") != ""
             or any(m.get("sender_kind") == "system" for m in rows))
check("escalation visible in S4 thread (tag/system note)", armed,
      str(c3)[:160] if c3 else "no conversation")

print("== E4: Message-ID dedupe (webhook-retry analogue) ==")
n_before = len(sent)
mr._handle_email("gate-e1@example.com", "Gate One", "Inquiry from website",
                 "Hello, what can you tell me about the DG-50 generator?",
                 msg_id="<gate-e1@mjcx.test>")
check("duplicate produced NO second email", len(sent) == n_before)

print("== E5: transport dispatch — send_text/send_document on email:* jids ==")
n_before = len(sent)
mr.send_text("email:e5@example.com", "staff take-over test line")
check("send_text routed to SMTP capture", len(sent) > n_before)
mr.send_document("email:e5@example.com", Path(__file__), "gate doc caption")
check("send_document attached a file",
      len(sent) > n_before + 1 and sent[-1]["attachments"] == ["test_email_channel.py"],
      str(sent[-1].get("attachments")) if len(sent) > n_before + 1 else "")

print("\nEMAIL CHANNEL RESULT: "
      f"{passed} passed, {failed} failed"
      "  (SMTP/IMAP were stubbed; live round-trip is the --execute drill)")
sys.exit(1 if failed else 0)
