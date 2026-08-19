#!/usr/bin/env python3
"""calc test suite — run: python3 calc/test_calculator.py

Cases mirror the flowchart Phase B decision points:
- B1-2 computable?      -> NotComputable(gaps) must fire and carry gaps
- B2-1 deterministic    -> same input, same price, every time
- qty tiers             -> per pricing_rules.example.json
- process fees, customer tiers (tier supplied by S3, not looked up here)
- unknown tier          -> NotComputable(gaps), no guessed factor
- XL escalation         -> manual per rules
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from calculator import PricingEngine, QuoteRequest, QuoteLine, NotComputable

RULES = Path(__file__).parent / ".." / "spine" / "rules" / "pricing_rules.example.json"

passed, failed = 0, 0
def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        print(f"  ✗ {name}  {detail}")

eng = PricingEngine(RULES)

print("== T1: single line, qty 10 (tier 6-20 -> 5%), no processes ==")
r = eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
# base 180 × coef 1.0 = 180/pc; ×10 = 1800; −5% = 1710
check("unit price 180.0", r.lines[0].unit_price == 180.0, f"got {r.lines[0].unit_price}")
check("subtotal 1800.0", r.subtotal == 1800.0, f"got {r.subtotal}")
check("total 1710.0", r.total == 1710.0, f"got {r.total}")
check("discount 5%", r.discount_pct == 5, f"got {r.discount_pct}")

print("== T2: deterministic (same input 3×) ==")
r2 = eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
r3 = eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
check("identical totals", r.total == r2.total == r3.total)

print("== T3: process fee + size coefficient (L ×1.5, etching +30) ==")
r = eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
    QuoteLine(material="Metal Casting", size="L", qty=2, processes=["Metal Etching + Paint"])]))
# (180×1.5)+30 = 300/pc; qty 2 -> tier 0%; total 600
check("unit 300.0", r.lines[0].unit_price == 300.0, f"got {r.lines[0].unit_price}")
check("total 600.0", r.total == 600.0, f"got {r.total}")

print("== T4: customer tier from S3 (distributor 0.90) ==")
r = eng.quote(QuoteRequest(customer_id="cus_dist_001", customer_tier="distributor", lines=[
    QuoteLine(material="Gold Foil/Wood", size="M", qty=3, processes=["Gold Foil Stamping"])]))
# (85×1.0)+5 = 90; ×0.9 = 81/pc; qty 3, no tier discount -> 243
check("unit 81.0", r.lines[0].unit_price == 81.0, f"got {r.lines[0].unit_price}")
check("total 243.0", r.total == 243.0, f"got {r.total}")

print("== T5: multi-line, qty sums for tier ==")
r = eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
    QuoteLine(material="Crystal/Glass", size="S", qty=12),
    QuoteLine(material="Acrylic/Composite", size="M", qty=10)]))
# L1: 120×0.8=96 ×12 = 1152 ; L2: 55×1.0=55 ×10 = 550 ; sum qty 22 -> 15% tier
check("subtotal 1702.0", r.subtotal == 1702.0, f"got {r.subtotal}")
check("tier 15%", r.discount_pct == 15, f"got {r.discount_pct}")
check("total 1446.7", r.total == 1446.7, f"got {r.total}")

print("== T6: XL -> escalate with gap ==")
try:
    eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
        QuoteLine(material="Metal Casting", size="XL", qty=5)]))
    check("NotComputable raised", False)
except NotComputable as e:
    check("NotComputable raised", True)
    check("gap mentions size XL", any("XL" in g for g in e.gaps), f"gaps={e.gaps}")

print("== T7: unknown material -> escalate with gap ==")
try:
    eng.quote(QuoteRequest(customer_id="cus_new_001", lines=[
        QuoteLine(material="Titanium Unobtainium", size="M", qty=5)]))
    check("NotComputable raised", False)
except NotComputable as e:
    check("NotComputable raised", True)
    check("gap names material", any("Titanium" in g for g in e.gaps), f"gaps={e.gaps}")

print("== T7b: unknown tier -> escalate with gap (never guess a factor) ==")
try:
    eng.quote(QuoteRequest(customer_id="cus_x", customer_tier="platinum", lines=[
        QuoteLine(material="Metal Casting", size="M", qty=5)]))
    check("NotComputable raised", False)
except NotComputable as e:
    check("NotComputable raised", True)
    check("gap names the tier", any("platinum" in g for g in e.gaps), f"gaps={e.gaps}")

print("== T7c: customer_id does NOT affect price (X1 — tier is S3's, not calc's) ==")
a = eng.quote(QuoteRequest(customer_id="cus_repeat_001", customer_tier="new", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
b = eng.quote(QuoteRequest(customer_id="cus_anyone_else", customer_tier="new", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
check("same tier -> same price regardless of id", a.total == b.total, f"{a.total} vs {b.total}")
c = eng.quote(QuoteRequest(customer_id="cus_repeat_001", customer_tier="repeat", lines=[
    QuoteLine(material="Metal Casting", size="M", qty=10)]))
check("tier is what moves the price", c.total == round(a.total * 0.95, 2), f"{c.total} vs {a.total}")

print("== T8: result JSON-serializable (for dify tool response) ==")
try:
    json.dumps(r.to_dict())
    check("serializes", True)
except Exception as e:
    check("serializes", False, str(e))

print("== T9: FastAPI app builds (service wiring) ==")
try:
    import os
    if os.environ.get("PYTHONPATH"):
        del os.environ["PYTHONPATH"]          # shell session may leak host PYTHONPATH
    import importlib
    calculator = importlib.import_module("calculator")
    app = calculator.build_app(RULES)
    check("app builds", app is not None)
except Exception as e:
    check("app builds", False, str(e))

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
