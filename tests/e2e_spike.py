#!/usr/bin/env python3
"""E2E spike test — Phase A → B money path, locally.

Simulates what dify will do at runtime:
  1. spine /resolve            (A2-1 identity — and the tier, S3-owned)
  2. calc  /quote              (B2-1 deterministic pricing, tier passed in)
  3. spine /quotes save        (S5)
  4. carbone render (local CE) (B4-1 PDF)

Prereqs:
  - spine API:  uvicorn spine_api:app --port 8101  (in spine/)
  - calc  API:  uvicorn app:app --port 8100        (in calc/, RULES_PATH set)
  - carbone local render: node /tmp/carbone-local/render.js (or docker CE, docx)

Run: env -u PYTHONPATH calc/.venv/bin/python tests/e2e_spike.py
"""
import json
import sys
import urllib.request

CALC = "http://127.0.0.1:8100"
SPINE = "http://127.0.0.1:8101"

passed, failed = 0, 0


def check(name, cond, detail=""):
    global passed, failed
    mark = "✓" if cond else "✗"
    print(f"  {mark} {name}" + (f"  [{detail}]" if detail and not cond else ""))
    passed = passed + (1 if cond else 0)
    failed = failed + (0 if cond else 1)


def post(url, payload, timeout=30):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


print("== E2E-1: spine identity resolution (A2-1) ==")
try:
    r = post(f"{SPINE}/resolve", {"wa_jid": "6281234567890@s.whatsapp.net"})
    check("known customer resolved", r["status"] == "known" and r["customer"]["customer_id"] == "cus_repeat_001",
          json.dumps(r)[:120])
    tier = r["customer"]["tier"]
    check("tier loaded (repeat)", tier == "repeat", tier)
except Exception as e:
    check("spine /resolve reachable — is uvicorn on 8101 up?", False, str(e))

print("== E2E-2: new customer creation ==")
try:
    import random
    r = post(f"{SPINE}/resolve", {"wa_jid": f"62899{random.randint(100000, 999999)}@s.whatsapp.net",
                                  "name": "Walk-in Buyer", "country": "MY"})
    check("new customer created", r["status"] == "new" and r["customer"]["customer_id"].startswith("cus_"),
          json.dumps(r)[:120])
except Exception as e:
    check("spine /resolve new", False, str(e))

print("== E2E-3: resolve -> tier -> calc quote via HTTP (A2-1 into B2-1) ==")
try:
    # exactly what dify does: S3 says WHICH tier, S2/calc says what that costs.
    who = post(f"{SPINE}/resolve", {"email": "dist@example.com"})
    check("distributor resolved from S3", who["customer"]["tier"] == "distributor",
          who["customer"].get("tier"))
    r = post(f"{CALC}/quote", {
        "customer_id": who["customer"]["customer_id"],
        "customer_tier": who["customer"]["tier"],
        "lines": [
            {"material": "DG-50", "size": "STD", "qty": 2},
            {"material": "ATS-50", "size": "STD", "qty": 5},
        ],
    })
    check("status OK", r["status"] == "OK", json.dumps(r)[:150])
    if r["status"] == "OK":
        # DG-50 2×5200×0.9 = 9360 · ATS-50 5×420×0.9 = 1890 · qty tier 6%
        check("total = 10575.0", abs(r["quote"]["total"] - 10575.0) < 0.01,
              str(r["quote"]["total"]))
        check("has valid_until", bool(r["quote"]["valid_until"]))
except Exception as e:
    check("calc /quote reachable — is uvicorn on 8100 up?", False, str(e))

print("== E2E-4: escalation path returns gaps (B5) ==")
try:
    r = post(f"{CALC}/quote", {
        "customer_id": "cus_new_001",
        "lines": [{"material": "Unobtainium", "size": "M", "qty": 5}],
    })
    check("status ESCALATE", r["status"] == "ESCALATE", json.dumps(r)[:150])
    check("gaps present", len(r.get("gaps", [])) > 0)
except Exception as e:
    check("escalation path", False, str(e))

print("== E2E-4b: tier unknown to S2 -> ESCALATE, never a guessed price ==")
try:
    r = post(f"{CALC}/quote", {
        "customer_id": "cus_new_001", "customer_tier": "platinum",
        "lines": [{"material": "Metal Casting", "size": "M", "qty": 5}],
    })
    check("status ESCALATE", r["status"] == "ESCALATE", json.dumps(r)[:150])
    check("gap names the tier", any("platinum" in g for g in r.get("gaps", [])), json.dumps(r)[:150])
except Exception as e:
    check("unknown tier path", False, str(e))

print("== E2E-5: quote saved to S5 ==")
try:
    qr = post(f"{CALC}/quote", {
        "customer_id": "cus_repeat_001",
        "customer_tier": "repeat",
        "lines": [{"material": "DG-30", "size": "STD", "qty": 1,
                   "processes": ["Extended Warranty 2 Years"]}],
    })
    s = post(f"{SPINE}/quotes", {
        "customer_id": "cus_repeat_001",
        "request_json": {"lines": 1, "note": "spike"},
        "result_json": qr["quote"],
        "total": qr["quote"]["total"],
        "currency": "USD",
    })
    check("quote id issued", s["quote_id"].startswith("Q-"), json.dumps(s))
    st = post(f"{SPINE}/quotes/{s['quote_id']}/status", {"status": "sent"})
    check("status -> sent", st.get("status") == "sent", json.dumps(st))
except Exception as e:
    check("spine /quotes", False, str(e))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
