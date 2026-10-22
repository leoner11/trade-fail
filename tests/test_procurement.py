#!/usr/bin/env python3
"""Supplier & Procurement gate — platform plan Phase 5 (U agent).

Verifies S12 end to end against live spine :8101: supplier register,
item catalog, unknown-supplier 404, PO draft with deterministic totals
(LLM proposes, arithmetic is code), status machine enforcement,
overdue filtering (delay flags), S8 audit events.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_procurement.py
Prereq: spine :8101 up.
"""
import json
import sys
import uuid

import urllib.error
import urllib.request

SPINE = "http://127.0.0.1:8101"
UNIQ = str(int(__import__("time").time()))

checks: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


def req(method: str, path: str, body: dict | None = None):
    r = urllib.request.Request(
        SPINE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# 1 — supplier register
code, res = req("POST", "/suppliers",
                {"name": f"Gate Factory {UNIQ}", "contact": "gate@test",
                 "terms": "30% deposit", "lead_time_days": 21,
                 "notes": "gate supplier"})
check("supplier registered", code == 200)
sid = res["supplier_id"]
code, _ = req("POST", "/suppliers", {"name": ""})
check("empty name -> 400", code == 400)

# 2 — supplier items
code, res = req("POST", f"/suppliers/{sid}/items",
                {"sku": "DG-30", "description": "30kVA silent genset",
                 "price": 3200.0, "moq": 1,
                 "capability_note": "core product"})
check("supplier item added", code == 200)
code, res = req("POST", "/suppliers/999999/items", {"price": 1})
check("unknown supplier -> 404", code == 404)

# 3 — PO draft: totals are CODE arithmetic (2×3200 + 1×550 = 6950)
lines = [{"sku": "DG-30", "qty": 2, "price": 3200.0},
         {"description": "ATS panel", "qty": 1, "price": 550.0}]
code, res = req("POST", "/purchase-orders",
                {"supplier_id": sid, "lines": lines,
                 "promised_date": "2026-01-01"})
check("PO drafted", code == 200)
check("PO total computed by code (6950.0)", res.get("total") == 6950.0)
pid = res["po_id"]
code, _ = req("POST", "/purchase-orders",
              {"supplier_id": sid, "lines": []})
check("empty lines -> 400", code == 400)
code, _ = req("POST", "/purchase-orders",
              {"supplier_id": 999999, "lines": lines})
check("unknown supplier PO -> 404", code == 404)

# 4 — status machine
for status in ("approved", "sent"):
    code, res = req("POST", f"/purchase-orders/{pid}/status",
                    {"status": status})
    check(f"status -> {status}", code == 200 and res["status"] == status)
code, res = req("POST", f"/purchase-orders/{pid}/status",
                {"status": "bogus"})
check("bogus status -> 400", code == 400)

# 5 — overdue delay flag: promised 2026-01-01, still "sent" -> overdue
code, res = req("GET", "/purchase-orders?overdue=1")
overdue_ids = [r["po_id"] for r in res.get("items", [])]
check("delay flag catches stale PO", pid in overdue_ids)

# 6 — S8 audit trail for status changes
code, res = req("GET", "/events?limit=50")
po_events = [e for e in res.get("items", [])
             if e.get("kind") == "po_status"
             and json.loads(e.get("detail_json") or "{}").get("po_id") == pid]
check("po_status audited to S8", len(po_events) >= 2)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\nprocurement gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
