#!/usr/bin/env python3
"""O3-2 — Pricing Rules Backtest (the go-live gate).

Re-computes REAL past quotes through calc from the current S2 rules and
compares against what the boss actually charged. Gate: >=90% of quotes match
within ±2% (flowchart: never go live on unverified pricing).

Input: data/o3_history.json — schema:
  [{"ref": "...", "customer_tier": "new|repeat|distributor",
    "lines": [{"material","size","qty","processes":[...]}],
    "quoted_total": <what the boss actually quoted>}]

No real history yet? The harness self-tests against data/o3_history.example.json
(marked EXAMPLE, does NOT count as a pass) and prints the O3-1 interview
checklist (runbooks/o3-pricing-interview.md).

Run: env -u PYTHONPATH calc/.venv/bin/python tests/test_o3_backtest.py
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CALC = "http://127.0.0.1:8100"
TOLERANCE = 0.02          # ±2%
GATE = 0.90               # ≥90% of quotes must match

real = ROOT / "data" / "o3_history.json"
example = ROOT / "data" / "o3_history.example.json"
mode = "REAL"
src = real


def post(url, payload):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


if not real.exists() or json.loads(real.read_text() or "[]") == []:
    mode = "EXAMPLE"
    src = example
    print("⚠️  No data/o3_history.json — running in EXAMPLE mode against the\n"
          "   placeholder rules themselves. This proves the machinery but does\n"
          "   NOT clear the go-live gate.\n")

history = json.loads(src.read_text())
if not history:
    print(f"{src} is empty — nothing to backtest.")
    sys.exit(1)

print(f"== O3-2 backtest ({mode}) — {len(history)} historical quote(s) ==")
match = mismatch = errors = 0
for h in history:
    try:
        r = post(f"{CALC}/quote", {
            "customer_id": "o3-backtest",
            "customer_tier": h["customer_tier"],
            "lines": h["lines"]})
        if r.get("status") != "OK":
            raise RuntimeError(r.get("gaps") or r.get("detail") or r)
        got = r["quote"]["total"]
        want = float(h["quoted_total"])
        delta = (got - want) / want if want else 1.0
        ok = abs(delta) <= TOLERANCE
        match += ok
        mismatch += not ok
        print(f"  {'✓' if ok else '✗'} {h['ref']}: rules {got:,.2f} vs "
              f"charged {want:,.2f} ({delta:+.1%})")
    except Exception as e:
        errors += 1
        print(f"  ✗ {h['ref']}: calc error — {str(e)[:100]}")

print("\n== O3-1 interview checklist still open? ==")
rb = ROOT / "runbooks" / "o3-pricing-interview.md"
print(("  ✓ exists: " if rb.exists() else "  ✗ missing: ") + str(rb.relative_to(ROOT)))

if mode == "EXAMPLE":
    print(f"\nEXAMPLE MODE: {match}/{len(history)} self-consistent. "
          "Gate NOT cleared — capture real history first.")
    print("  → interview the boss (runbooks/o3-pricing-interview.md), fill")
    print("    data/o3_history.json with 10-20 real past quotes, re-run.")
    sys.exit(0)

total = len(history)
rate = match / total if total else 0
verdict = "PASS — pricing rules are trusted" if rate >= GATE and errors == 0 \
    else "FAIL — do NOT go live (interview round 2)"
print(f"\nO3 RESULT: {match}/{total} within ±{TOLERANCE:.0%} "
      f"(gate ≥{GATE:.0%}), {errors} calc errors — {verdict}")
sys.exit(0 if rate >= GATE and errors == 0 else 1)
