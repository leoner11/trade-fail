#!/usr/bin/env python3
"""O5-1 — the 10-scenario acceptance gate (flowchart).

Scenarios 1-3, 5-8 run automatically through glue route() in DRY_RUN
(no WhatsApp traffic). Scenario 2 runs Indonesian through the same RAG.
Scenarios 4 / 9 / 10 need a real phone or postiz channels -> printed as a
manual checklist for Leonard.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_o5_acceptance.py
Prereq: spine :8101 · calc :8100 (generator rules) · dify spec workflow · GLM.
"""
import os
import sys
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

print("\n== Manual scenarios (Leonard, ~5 min on the real phones) ==")
print("  S4  formal-PDF lands IN WhatsApp thread  → text a formal ask")
print("  S9  social draft -> approval card -> postiz scheduled (postiz channel needed)")
print("  S10 QR-drop drill -> rescan via runbooks/whatsapp-qr-rescan.md")

print(f"\nAUTO RESULT: {passed} passed, {failed} failed "
      f"(gate: all auto scenarios green)")
sys.exit(1 if failed else 0)
