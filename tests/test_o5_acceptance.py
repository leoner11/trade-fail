#!/usr/bin/env python3
"""O5-1 — the acceptance gate (flowchart).

Scenarios 1-3, 5-8, 11 run automatically through glue route() in DRY_RUN
(no WhatsApp traffic). Scenario 2 runs Indonesian through the same RAG.
Scenarios 4 / 9 / 10 need a real phone or postiz channels -> printed as a
manual checklist for Leonard.

Conversation core v2 (session #16): run the same suite with the v2 brain —
  v1:  env -u PYTHONPATH calc/.venv/bin/python tests/test_o5_acceptance.py
  v2:  CONVERSATION_CORE=v2 env -u PYTHONPATH calc/.venv/bin/python \
           tests/test_o5_acceptance.py
Both modes must be 100% green (S15-S19 pin 2026-08-26's six live flakes
verbatim; v1 passes them via the same-night patches, v2 via the agent
loop — they stay as regression pins through the soak).
Prereq: spine :8101 · calc :8100 (generator rules) · dify spec workflow · GLM.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

os.environ["DRY_RUN"] = "1"          # never send anything anywhere
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

BUYER = {"customer_id": "cus_new_001", "tier": "new", "name": "O5 Buyer"}

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} {name}" +
          (f"  [{detail}]" if detail and not cond else ""))
    passed += bool(cond)
    failed += not cond


from mock_responder import route  # noqa: E402
import mock_responder as mr  # noqa: E402


def reset_thread(jid):
    """Deterministic chain scenarios: clear BOTH cores' thread state —
    v1's in-process _THREAD and v2's spine agent_state column (which
    survives across runs/days, unlike _THREAD)."""
    mr._THREAD.pop(jid, None)
    try:
        cid = json.loads(urllib.request.urlopen(
            f"{mr.SPINE_URL}/conversations/by_jid/{jid}", timeout=5
        ).read())["conversation_id"]
        req = urllib.request.Request(
            f"{mr.SPINE_URL}/conversations/{cid}/agent_state", data=b"{}",
            method="PUT", headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()
    except Exception:
        pass


HANDOFF = ("personal attention", "colleague will follow", "team will get back",
           "check with", "spec sheet")

print("== S1: spec question EN -> cited catalog answer ==")
r = route(dict(BUYER), "What is the fuel tank size and noise level of the DG-50?", "o5@s.whatsapp.net")
check("grounded specs (120L + dB)", r and "120" in r and ("70" in r or "dB" in r), str(r)[:90])

print("== S2: spec question ID -> same answer in Indonesian ==")
r = route(dict(BUYER), "Berapa kapasitas tangki dan berapa desibel genset DG-50?",
          "o5@s.whatsapp.net")
check("grounded, Indonesian", r and "120" in r and any(
    k in r.lower() for k in ("tangki", "desibel", "bahan bakar")), str(r)[:90])

print("== S3: standard price ask -> calc inline price ==")
r = route(dict(BUYER), "Please give me your best price for 2 units DG-50 STD.",
          "o5@s.whatsapp.net")
check("inline total 10,088.00 present", r and "10,088" in r, str(r)[:120])
check("validity date line", bool(r) and "Valid until" in r or "有效期" in (r or ""))

print("== S4: formal quote ask -> PDF in chat (needs phone; dry-run here) ==")
r = route(dict(BUYER), "Can you send me an official quotation PDF for "
                       "10 units of the ATS-50 panel?", "o5@s.whatsapp.net")
check("formal path armed (PDF offer line)", r and ("on its way" in r or
      "PDF quotation" in r), str(r)[:100])
print("     → live check on phone: PDF document arrives in-thread "
      "(tests/test_b4.py SEND_JID=... covers delivery)")

print("== S5: custom ODM request -> escalates with draft+summary ==")
r = route(dict(BUYER), "We need a 200kVA containerized genset with custom "
                       "switchgear and remote telemetry. Can you build it?", "o5@s.whatsapp.net")
check("escalation holding reply", r and any(k in r.lower() for k in (
    "human", "team", "colleague", "engineer")), str(r)[:100])

print("== S6: 'your generator exploded' -> immediate complaint escalation ==")
r = route(BUYER | {"tier": "repeat"}, "Your generator exploded and this is unacceptable!",
          "o5@s.whatsapp.net")
check("empathetic urgent holding reply", r and any(k in r.lower() for k in (
    "sorry", "urgent", "flagged")), str(r)[:100])

print("== S7: discount push beyond cap -> escalates to human ==")
r = route(BUYER | {"tier": "distributor"},
          "The price is too high. I want a 40% discount on the DG-50.", "o5@s.whatsapp.net")
check("not discounted by AI (escalated/clarified)", r and "40%" not in r
      and any(k in r.lower() for k in ("human", "team", "colleague", "question",
                                       "how many", "quantity", "what size")),
      str(r)[:110])

print("== S8b: OFF-DOMAIN ask -> neutral handoff, NEVER invents a service ==")
r = route(BUYER | {"tier": "distributor"},
          "i thought ur a foreign trade company, so u also do tour and travels to tibet?",
          "o5@s.whatsapp.net")
low = (r or "").lower()
confirms = ("we do offer" in low or "we offer" in low or "yes, as a foreign"
            in low or "travel arrangements" in low or "tour services" in low)
check("no invented capability + human handoff",
      r is not None and not confirms and any(k in low for k in (
          "human", "colleague", "team")), str(r)[:110])

print("== S8: gibberish/spam -> politely dropped ==")
r = route(dict(BUYER), "asdfgh qwerty 12345 !!! ???", "o5@s.whatsapp.net")
check("silence", r is None, str(r))

print("== S11: bare SKU pick under low-conf OTHER -> S1 catalog answer ==")
# Live flake 2026-08-26: triage read "DG-30 lets say" as OTHER conf 0.4 and
# the thread dead-ended in a human handoff mid-sale (usually the buyer
# answering OUR "which model?" question). The bare-SKU rescue must answer
# from the catalog instead.
r = route(dict(BUYER), "DG-30 lets say", "o5sku@s.whatsapp.net")
check("grounded DG-30 answer, no human handoff",
      r and "DG-30" in r.upper()
      and not any(k in r.lower() for k in ("personal attention",
                                           "colleague will follow",
                                           "team will get back")),
      str(r)[:110])

print("== S11b: UNKNOWN SKU -> never guesses ==")
# v2 (Leonard's call, session #16): unknown product asks get the NATURAL
# grounded-negative + pivot (real sales tone) while the ask is armed to
# staff in the background as a demand signal. v1 (frozen) hands off with
# the holding line. Both must refuse to invent specs either way.
r = route(dict(BUYER), "DG-9000 lets say", "o5sku@s.whatsapp.net")
if os.environ.get("CONVERSATION_CORE") == "v2":
    check("natural 'not our line' + line pivot, no invented specs",
          r and any(k in r.upper() for k in ("DG-30", "DG-50", "ATS-50"))
          and "9000 kVA" not in r
          and not any(k in r.lower() for k in ("check with", "spec sheet")),
          str(r)[:110])
else:
    check("holding line for a product S1 does not have",
          r and any(k in r.lower() for k in ("personal attention",
                                             "colleague will follow"))
          and "9000 kVA" not in r, str(r)[:110])

print("== S12: catalog-line question -> S1 model list, never a stall ==")
# Live flake 2026-08-26 22:34: "what models are there" hit RAG, which
# stalled ("check with team") and dead-ended into spec_stub + SPEC_Q
# escalation. The model list IS S1 data — answer it deterministically.
r = route(dict(BUYER), "what models are there", "o5line@s.whatsapp.net")
check("full line from S1, no stall/handoff",
      r and "DG-30" in r and "DG-100" in r
      and not any(k in r.lower() for k in ("spec sheet", "come back to you",
                                           "check with", "personal attention",
                                           "colleague will follow")),
      str(r)[:130])

print("== S13: 'yes please' after a catalog offer -> SPECS, never a goodbye ==")
# Live flake 2026-08-26 22:52: hyphenless "dg 30" missed the SKU path ->
# weak RAG-prose offer -> fulfillment compose padded invented numbers ->
# guard killed it (right) -> fallback was the 'welcome' CLOSING template
# (wrong). Chain fix: SKU normalization + catalog facts + deterministic
# fallback.
R = "o5fu@s.whatsapp.net"
reset_thread(R)
r = route(dict(BUYER), "so i assume 30 kva is dg 30? can i know that one more", R)
check("hyphenless 'dg 30' -> catalog card", r and "DG-30" in r.upper()
      and "80L" in r, str(r)[:100])
r = route(dict(BUYER), "yes please", R)
check("fulfillment delivers real specs (80L tank), no goodbye template",
      r and "80L" in r and "68dB" in r
      and "message me here any time" not in r, str(r)[:130])

print("== S14: follow-up 'the details' with no product -> last SKU, not amnesia ==")
r = route(dict(BUYER), "i said i want the details and specifications", R)
check("resolves to last discussed SKU (DG-30 card)",
      r and "DG-30" in r.upper() and "80L" in r
      and "specify which product" not in r.lower(), str(r)[:130])

print("== S15 (flake 21:17): 'DG-30 lets say' -> catalog answer, no human flag ==")
# 2026-08-26 evidence table row 1, verbatim: buyer answering our own
# "which model?" question must land on the S1 card mid-sale.
r = route(dict(BUYER), "DG-30 lets say", "o5v2sku@s.whatsapp.net")
check("grounded DG-30 answer, no handoff",
      r and "DG-30" in r.upper() and not any(k in r.lower() for k in HANDOFF),
      str(r)[:110])

print("== S16 (flake 22:34): 'what models are there' -> S1 list, no stall ==")
r = route(dict(BUYER), "what models are there", "o5v2line@s.whatsapp.net")
check("full line from S1, zero stall/handoff",
      r and "DG-30" in r and "DG-100" in r
      and not any(k in r.lower() for k in HANDOFF), str(r)[:130])

print("== S17 (flakes 22:51+22:53): '30 kva is dg 30?' then 'yes please' ==")
# Verbatim pair from the evidence table (live message had the 'so i
# assume' prefix — the bare short form is <50% letters and the shared
# noise gate correctly silences it): hyphenless pick must hit the
# catalog, and the pure agreement must deliver REAL specs — never a
# goodbye template mid-sale.
R17 = "o5v2fu@s.whatsapp.net"
reset_thread(R17)
r = route(dict(BUYER), "so i assume 30 kva is dg 30?", R17)
check("hyphenless pick -> DG-30 card", r and "DG-30" in r.upper()
      and "80L" in r, str(r)[:100])
r = route(dict(BUYER), "yes please", R17)
check("'yes please' -> real specs (80L + 68dB), no goodbye",
      r and "80L" in r and "68dB" in r
      and "message me here any time" not in r, str(r)[:130])

print("== S18 (flake 22:53): 'i want the details' -> last SKU, no amnesia ==")
r = route(dict(BUYER), "i want the details", R17)
check("resolves against the thread (DG-30 card)",
      r and "DG-30" in r.upper() and "80L" in r
      and "specify which product" not in r.lower()
      and "which product" not in r.lower(), str(r)[:130])

print("== S19 (flake 23:20): 'tell me more bout ur industry' -> line, no flag ==")
r = route(dict(BUYER), "hello bro, tell me more bout ur industry",
          "o5v2cap@s.whatsapp.net")
check("company line from S1, no human handoff",
      r and ("DG-30" in r or "generator" in r.lower())
      and not any(k in r.lower() for k in HANDOFF), str(r)[:130])

print("\n== Manual scenarios (Leonard, ~5 min on the real phones) ==")
print("  S4  formal-PDF lands IN WhatsApp thread  → text a formal ask")
print("  S9  social draft -> approval card -> postiz scheduled (postiz channel needed)")
print("  S10 QR-drop drill -> rescan via runbooks/whatsapp-qr-rescan.md")

print(f"\nAUTO RESULT: {passed} passed, {failed} failed "
      f"(gate: all auto scenarios green)")
sys.exit(1 if failed else 0)
