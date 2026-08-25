#!/usr/bin/env python3
"""O5 Scenario 9 — social draft -> boss approval -> postiz.

Automated: weekly-draft tick -> pending post in S6 -> APPROVE via the real
webhook path -> state machine lands on approved/scheduled, postiz push
attempted (skips + logs while POSTIZ_API_KEY/channels are missing).
Manual remainder (needs human accounts): connect a channel in postiz :13000,
create API key -> .env POSTIZ_API_KEY -> re-run with --expect-scheduled.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_o5_s9_social.py
Prereq: spine :8101 · glue :8102 · catalog non-empty. BOSS_WHATSAPP set.
"""
import json
import sys
import urllib.request

GLUE = "http://127.0.0.1:8102"
SPINE = "http://127.0.0.1:8101"
BOSS_JID = None  # resolved from glue .env via an approve round-trip

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} {name}" +
          (f"  [{detail}]" if detail and not cond else ""))
    passed += bool(cond)
    failed += not cond


def req(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    r = urllib.request.Request(url, data=data, method=method,
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=180) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


print("== S9a: weekly tick drafts a new post ==")
res = req("POST", f"{GLUE}/c/draft_tick?count=1")
drafted = res.get("drafted") or []
check("draft created", len(drafted) >= 1, json.dumps(res)[:120])
if not drafted:
    print("    (all SKUs already have live posts — clear some S6 rows to rerun)")
    sys.exit(0 if passed and not failed else 1)
pid = drafted[0]["post_id"]

print("== S9b: pending in S6 ==")
posts = req("GET", f"{SPINE}/posts?status=pending&limit=100")["items"]
row = next((p for p in posts if p["post_id"] == pid), None)
check("pending row exists", row is not None)

print("== S9c: boss approves via webhook (real intercept path) ==")
# the intercept only honors the configured boss number; read it from glue cfg
sys.path.insert(0, "glue")
import mock_responder as mr  # noqa: E402

boss_num = mr.cfg("BOSS_WHATSAPP", mr.BOSS_WHATSAPP).lstrip("+")
fake = {"event": "messages.upsert",
        "data": {"key": {"remoteJid": f"{boss_num}@s.whatsapp.net",
                         "fromMe": False, "id": f"s9-{pid}"},
                 "message": {"conversation": f"APPROVE {pid}"}}}
res = req("POST", f"{GLUE}/webhook/evo", fake)
check("intercept accepted", res.get("action") == "APPROVE"
      and res.get("ref") == pid, json.dumps(res))

print("== S9d: S6 state machine after approval ==")
row = next(p for p in req("GET", f"{SPINE}/posts?limit=200")["items"]
           if p["post_id"] == pid)
expect_scheduled = "--expect-scheduled" in sys.argv
if expect_scheduled:
    check("scheduled w/ postiz pointer", row["status"] == "scheduled"
          and bool(row.get("postiz_id")), str(row))
else:
    check("approved", row["status"] == "approved", str(row))
    ev = [e for e in req("GET", f"{SPINE}/events?kind=postiz_push_skipped")["items"]
          if json.loads(e["detail_json"]).get("post_id") == pid]
    check("push skip logged (no key/channels yet)", len(ev) >= 1)

print("\nManual remainder for FULL S9 credit:")
print("  1. postiz UI http://localhost:13000 -> signup owner -> connect the")
print("     client's channel(s)")
print("  2. create API key -> .env POSTIZ_API_KEY=... -> restart glue")
print(f"  3. re-run this script with a fresh draft + --expect-scheduled")

print(f"\nS9 RESULT: {passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
