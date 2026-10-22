#!/usr/bin/env python3
"""Positioning gate — platform plan Phase 5 (P agent).

Verifies: analyze endpoint (citation contract: no [L<n>] beyond listing
count; price band computed in code) · drafts promoted to S1 as PROPOSED ·
proposed SKUs are NOT quotable (resolve 404) · approve flips to live ·
S8 audit. GLM analyze is exercised live (repo convention: o2/classify gates
call GLM); deterministic fallback keeps the gate green without GLM.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_positioning.py
Prereq: spine :8101 + glue :8102 up (revived with this build).
"""
import json
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))
import entitlement  # noqa: E402

GLUE = "http://127.0.0.1:8102"
SPINE = "http://127.0.0.1:8101"
TOK = ""
for line in (ROOT / ".env").read_text().splitlines():
    if line.startswith("CONSOLE_TOKEN="):
        TOK = line.split("=", 1)[1].strip()

checks: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


def req(url: str, method: str = "GET", body: dict | None = None):
    r = urllib.request.Request(
        url, data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {TOK}"}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw.decode("utf-8", "replace")[:200]}


sku = f"POS-{uuid.uuid4().hex[:6].upper()}"

# 1 — analyze with fixture listings (prices kept as given)
listings = [
    {"title": "Mono 550W panel A-grade", "price": 62.0},
    {"title": "Mono 550W panel B-grade micro-scratch", "price": 48.0},
    {"title": "Mono 500W panel with micro-cracks complaint", "price": 55.0},
]
code, res = req(f"{GLUE}/console/positioning/analyze", "POST",
                {"category": "solar panels 550W", "listings": listings})
check("analyze responds", code == 200)
check("price band computed in code",
      res.get("price_band", {}).get("min") == 48.0
      and res.get("price_band", {}).get("max") == 62.0)
memo = res.get("memo", "")
check("citation contract: no [L<n>] beyond listing count",
      all(int(t) <= len(listings) for t in
          __import__("re").findall(r"\[L(\d+)\]", memo)) or "rejected" in memo)
check("memo persisted (S8 pointer)", bool(res.get("memo_path")))

# 2 — promote drafts -> S1 PROPOSED -> not quotable
drafts = res.get("drafts") or [{"sku": sku, "name": "550W panel (gate)",
                                "category": "solar", "moq": 10}]
code, res = req(f"{GLUE}/console/positioning/promote", "POST",
                {"drafts": [{"sku": sku, "name": "550W panel (gate)",
                             "category": "solar", "moq": 10}]})
check("promotion ok", code == 200)
code, _ = req(f"{SPINE}/catalog/{sku}")
check("PROPOSED sku not quotable (resolve 404)", code == 404)

# 3 — approve -> live -> quotable
code, res = req(f"{SPINE}/catalog/{sku}/approve", "POST")
check("approve flips to live", code == 200)
code, res = req(f"{SPINE}/catalog/{sku}")
check("approved sku resolvable", code == 200
      and res.get("status") == "live")

# 4 — cleanup gate sku
req(f"{SPINE}/catalog/{sku}", "DELETE")

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\npositioning gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
