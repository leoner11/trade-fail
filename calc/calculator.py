#!/usr/bin/env python3
"""
▣ calc — MJCX Trade Agent Appliance pricing engine (Phase B of flowchart).

THE rule: the LLM never does arithmetic. dify parses a buyer's request into
JSON (QuoteRequest); this engine computes price deterministically from
pricing_rules (S2). If any needed rule is missing -> QuoteGapError and the
flow escalates to a human (B5), with a rules-gap hint.

Rules format: pricing_rules.json (see spine/rules/pricing_rules.example.json,
seeded from the email-quote-automation markdown schema:
material base prices / size coefficients / process fees / qty discounts /
customer-tier terms / authority caps).
"""
# NOTE: no `from __future__ import annotations` here — pydantic + function-local
# models (build_app) can't resolve string ForwardRefs on 3.12 without it mattering.
import json
import re
import threading
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

class NotComputable(Exception):
    """Raised when rules cannot price this request. -> Phase B5 (human quote).

    Carries `gaps`: what's missing from S2 so the escalation package can
    include a rules-gap hint (flowchart B5-1) and the boss can decide to
    extend the rules.
    """

    def __init__(self, gaps: list[str], msg: str = ""):
        self.gaps = gaps
        super().__init__(msg or ("Not computable — missing rules: " + "; ".join(gaps)))


# ---------------------------------------------------------------- request models

@dataclass
class QuoteLine:
    """One line item as parsed by the LLM (dify B1-1)."""
    material: str                 # e.g. "Metal Casting" (must match rules)
    size: str                     # "S" | "M" | "L" | "XL"
    qty: int
    processes: list[str] = field(default_factory=list)  # e.g. ["Gold Foil Stamping"]
    notes: str = ""


@dataclass
class QuoteRequest:
    """Structured request from dify — Phase B1-1 output.

    `customer_tier` comes from S3 (spine.customers.tier), passed in by the
    caller — flowchart B2-1: "Input: parsed request + customer tier from S3".
    S2 owns the FACTOR per tier; S3 owns WHICH tier a customer is in. calc
    never maps customer_id -> tier itself (that would be a second opinion
    about a customer, forbidden by X1). customer_id is carried for S5
    linkage and tracing only — it does not affect price.
    """
    customer_id: str
    lines: list[QuoteLine]
    customer_tier: str = "new"
    currency: str = "USD"
    incoterm: str | None = None
    destination: str | None = None
    request_id: str = ""


@dataclass
class LineResult:
    description: str
    qty: int
    unit_price: float
    line_total: float
    breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass
class QuoteResult:
    request_id: str
    customer_id: str
    currency: str
    lines: list[LineResult]
    subtotal: float
    discount_pct: float
    total: float
    margin_note: str          # STAFF-only, never sent to buyer
    valid_until: str
    computed_at: str
    rule_trace: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Deep-JSON-safe dict (dify tool responses must serialize)."""
        d = self.__dict__.copy()
        d["lines"] = [l.__dict__ for l in self.lines]
        return d


# ---------------------------------------------------------------- engine

def validate_rules(rules: dict) -> list[str]:
    """Structural + numeric validation mirroring what quote() actually needs.
    Returns human-readable problems (empty list = valid). Money-bearing
    values must be > 0; size coefficients may be 0 — that is the XL
    manual-quote escape hatch, not an error."""
    p: list[str] = []

    def num(v) -> float | None:
        try:
            f = float(v)
            return f if f == f else None   # NaN guard
        except (TypeError, ValueError):
            return None

    mbp = rules.get("material_base_prices")
    if not isinstance(mbp, list) or not mbp:
        p.append("material_base_prices must be a non-empty list")
    else:
        names = set()
        for m in mbp:
            n = m.get("name")
            if not n:
                p.append("material_base_prices: entry without name")
            elif n in names:
                p.append(f"material_base_prices: duplicate '{n}'")
            names.add(n or "")
            for k in ("base_price", "bulk_price"):
                v = num(m.get(k))
                if v is None or v <= 0:
                    p.append(f"{n or '?'}: {k} must be > 0 (got {m.get(k)!r})")

    sc = rules.get("size_coefficients")
    if not isinstance(sc, list) or not sc:
        p.append("size_coefficients must be a non-empty list")
    else:
        names = set()
        for s in sc:
            n = str(s.get("size", "")).strip()
            if not n:
                p.append("size_coefficients: entry without size")
            elif n.lower() in names:
                p.append(f"size_coefficients: duplicate '{n}'")
            names.add(n.lower())
            v = num(s.get("coefficient"))
            if v is None or v < 0:
                p.append(f"size '{s.get('size', '?')}': coefficient must be >= 0 "
                         f"(got {s.get('coefficient')!r}; 0 = manual-quote hatch)")

    pf = rules.get("process_fees", [])
    if not isinstance(pf, list):
        p.append("process_fees must be a list")
    else:
        seen = set()
        for f in pf:
            n = str(f.get("name", "")).strip()
            if not n:
                p.append("process_fees: entry without name")
            elif n.lower() in seen:
                p.append(f"process_fees: duplicate '{n}'")
            seen.add(n.lower())
            v = num(f.get("fee"))
            if v is None or v <= 0:
                p.append(f"process '{f.get('name', '?')}': fee must be > 0")

    qd = rules.get("quantity_discounts")
    if not isinstance(qd, list) or not qd:
        p.append("quantity_discounts must be a non-empty list")
    else:
        qtys = [num(t.get("min_qty")) for t in qd]
        if any(q is None or q <= 0 or q != int(q) for q in qtys):
            p.append("quantity_discounts: min_qty must be a positive integer")
        else:
            ordered = sorted(qtys)  # type: ignore[arg-type]
            if any(a >= b for a, b in zip(ordered, ordered[1:])):
                p.append("quantity_discounts: min_qty must be strictly increasing")
        for t in qd:
            d = num(t.get("discount_pct"))
            if d is None or d < 0 or d >= 100:
                p.append(f"tier min_qty={t.get('min_qty')}: discount_pct must be 0..<100")

    ct = rules.get("customer_tiers")
    if not isinstance(ct, list) or not ct:
        p.append("customer_tiers must be a non-empty list")
    else:
        seen = set()
        for t in ct:
            n = t.get("name")
            if not n:
                p.append("customer_tiers: entry without name")
            elif str(n).lower() in seen:
                p.append(f"customer_tiers: duplicate tier '{n}'")
            seen.add(str(n).lower())
            f = num(t.get("price_factor", 1.0))
            if f is None or f <= 0:
                p.append(f"tier '{n or '?'}': price_factor must be > 0")

    auth = rules.get("authority", {})
    cap = num(auth.get("max_discount_pct", 0)) if isinstance(auth, dict) else None
    if cap is None or cap < 0 or cap > 100:
        p.append("authority.max_discount_pct must be 0..100")

    vd = num(rules.get("validity_days", 30))
    if vd is None or vd < 1 or vd != int(vd):
        p.append("validity_days must be a positive integer")

    cur = rules.get("currency", "USD")
    if not isinstance(cur, str) or not re.fullmatch(r"[A-Z]{3}", str(cur).strip()):
        p.append("currency must be a 3-letter ISO code (e.g. USD, EUR, CNY)")

    return p


class PricingEngine:
    def __init__(self, rules: dict | Path | str):
        if isinstance(rules, (str, Path)):
            rules = json.loads(Path(rules).read_text())
        self.rules = rules
        self._validate_rules()

    # -- rule lookup helpers -------------------------------------------------

    def _find(self, collection: str, name: str, key: str = "name") -> dict:
        for item in self.rules.get(collection, []):
            if item.get(key, "").lower() == name.lower():
                return item
        raise NotComputable([f"{collection}: no entry for '{name}'"])

    def _qty_tier(self, total_qty: int) -> dict:
        tiers = sorted(self.rules["quantity_discounts"], key=lambda t: t["min_qty"])
        chosen = None
        for t in tiers:
            if total_qty >= t["min_qty"]:
                chosen = t
        if chosen is None:
            raise NotComputable([f"quantity_discounts: no tier for qty {total_qty}"])
        return chosen

    def _validate_rules(self) -> None:
        required = ["material_base_prices", "size_coefficients",
                    "quantity_discounts", "customer_tiers"]
        missing = [k for k in required if k not in self.rules]
        if missing:
            raise ValueError(f"pricing rules missing sections: {missing}")

    # -- core -----------------------------------------------------------------

    def quote(self, req: QuoteRequest) -> QuoteResult:
        trace: list[str] = []
        line_results: list[LineResult] = []
        total_qty = sum(l.qty for l in req.lines)

        tier = self._qty_tier(total_qty)
        trace.append(f"qty tier: {total_qty} pcs -> {tier['discount_pct']}% ({tier.get('label','')})")

        customer_tier = self._tier(req.customer_tier)
        trace.append(f"customer tier: {customer_tier['name']} (from S3) "
                     f"(factor {customer_tier.get('price_factor', 1.0)}, "
                     f"payment terms {customer_tier.get('payment_terms','standard')})")

        subtotal = 0.0
        for idx, line in enumerate(req.lines, 1):
            base = self._find("material_base_prices", line.material)
            coef = self._find("size_coefficients", line.size, key="size")
            if float(coef.get("coefficient", 0)) <= 0 and line.size.upper() == "XL":
                raise NotComputable([f"size '{line.size}' for '{line.material}': manual quote per rules"])

            unit = float(base["base_price"]) * float(coef["coefficient"])
            trace.append(f"L{idx} base {base['name']} {base['base_price']} × size {line.size} "
                         f"{coef['coefficient']} = {round(unit,2)}")

            fees: dict[str, float] = {}
            for p in line.processes:
                fee = self._find("process_fees", p)
                fees[p] = float(fee["fee"])
                unit += float(fee["fee"])
                trace.append(f"L{idx} + process {p} {fee['fee']}")

            unit *= float(customer_tier.get("price_factor", 1.0))

            line_total = round(unit * line.qty, 2)
            subtotal += line_total
            line_results.append(LineResult(
                description=f"{line.material} {line.size}" + (f" ({', '.join(line.processes)})" if line.processes else ""),
                qty=line.qty,
                unit_price=round(unit, 2),
                line_total=line_total,
                breakdown={"base": base["base_price"], "size_coef": coef["coefficient"],
                           "processes": fees, "customer_tier": customer_tier["name"]},
            ))

        discount_pct = float(tier["discount_pct"])
        total = round(subtotal * (1 - discount_pct / 100), 2)
        trace.append(f"subtotal {round(subtotal,2)} × (1 - {discount_pct}%) = {total}")

        authority = self.rules.get("authority", {})
        margin_note = (f"Auto-computed. Discount {discount_pct}% (qty tier). "
                       f"Authority cap: {authority.get('max_discount_pct', 0)}%.")

        return QuoteResult(
            request_id=req.request_id or f"qr-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            customer_id=req.customer_id,
            currency=req.currency,
            lines=line_results,
            subtotal=round(subtotal, 2),
            discount_pct=discount_pct,
            total=total,
            margin_note=margin_note,
            valid_until=(date.today() + timedelta(days=self.rules.get("validity_days", 30))).isoformat(),
            computed_at=datetime.now().isoformat(timespec="seconds"),
            rule_trace=trace,
        )

    def _tier(self, tier_name: str | None) -> dict:
        """S3 tier name -> S2 pricing terms. Unknown tier = rules gap, not a guess."""
        name = (tier_name or "new").strip()
        for t in self.rules.get("customer_tiers", []):
            if t.get("name", "").lower() == name.lower():
                return t
        raise NotComputable(
            [f"customer_tiers: no entry for tier '{name}' — add it to S2 "
             f"(known: {[t.get('name') for t in self.rules.get('customer_tiers', [])]})"])


# ---------------------------------------------------------------- FastAPI service

def build_app(rules_path: str | Path):
    from fastapi import Body, FastAPI
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    rules_file = Path(rules_path)
    _lock = threading.Lock()
    engine = PricingEngine(rules_file)   # boot failure still crashes loudly

    app = FastAPI(title="MJCX calc", version="0.1.0",
                  description="Deterministic pricing. LLM parses, calc computes.")

    class LineIn(BaseModel):
        material: str
        size: str
        qty: int
        processes: list[str] = []
        notes: str = ""

    class QuoteIn(BaseModel):
        customer_id: str
        lines: list[LineIn]
        customer_tier: str = "new"   # from spine /resolve -> customer.tier (S3)
        currency: str = "USD"
        incoterm: str | None = None
        destination: str | None = None
        request_id: str = ""

    @app.post("/quote")
    def quote(inp: QuoteIn = Body(...)):
        with _lock:
            eng = engine
        try:
            r = eng.quote(QuoteRequest(
                customer_id=inp.customer_id,
                customer_tier=inp.customer_tier,
                lines=[QuoteLine(**l.model_dump()) for l in inp.lines],
                currency=inp.currency, incoterm=inp.incoterm,
                destination=inp.destination, request_id=inp.request_id,
            ))
            return {"status": "OK", "quote": r.__dict__}
        except NotComputable as e:
            return {"status": "ESCALATE", "gaps": e.gaps}   # -> Phase B5

    @app.post("/rules/validate")
    def rules_validate(inp: dict = Body(...)):
        """Dry-run validation of a candidate rules object (console editor
        pre-check). Pure: touches no state."""
        problems = validate_rules(inp.get("rules") or {})
        return {"ok": not problems, "problems": problems}

    @app.post("/rules/reload")
    def rules_reload():
        """Hot reload (console editor path): re-read RULES_PATH, re-validate,
        swap under lock. WITHOUT this an edited file does nothing until
        restart — the silent-stale-rules trap. A failed parse/validation
        rolls the FILE back from its .bak twin and reports; the running
        engine keeps serving the last good rules either way."""
        nonlocal engine
        bak = rules_file.with_suffix(rules_file.suffix + ".bak")
        with _lock:
            try:
                raw = rules_file.read_text()
                candidate = PricingEngine(json.loads(raw))
                problems = validate_rules(candidate.rules)
                if problems:
                    raise ValueError("; ".join(problems[:6]))
            except Exception as e:
                rolled_back = False
                if bak.exists():
                    try:
                        restored = json.loads(bak.read_text())
                        PricingEngine(restored)          # sanity: .bak must load
                        rules_file.write_text(bak.read_text())
                        rolled_back = True
                    except Exception as be:
                        return JSONResponse(status_code=400, content={
                            "ok": False, "error": f"{e}",
                            "rolled_back": False,
                            "rollback_error": str(be)[:160],
                            "engine_state": "previous-rules-still-live"})
                return JSONResponse(status_code=400, content={
                    "ok": False, "error": str(e)[:300],
                    "rolled_back": rolled_back,
                    "engine_state": "previous-rules-still-live"})
            engine = candidate
        return {"ok": True,
                "schema_version": engine.rules.get("schema_version"),
                "materials": len(engine.rules.get("material_base_prices", []))}

    @app.get("/health")
    def health():
        with _lock:
            eng = engine
        return {"ok": True, "engine": "calc", "rules": str(rules_path),
                "schema_version": eng.rules.get("schema_version")}

    return app


if __name__ == "__main__":
    # sanity: python3 calc/calculator.py  (runs self-check against example rules)
    here = Path(__file__).parent
    rules = here / ".." / "spine" / "rules" / "pricing_rules.example.json"
    eng = PricingEngine(rules)
    r = eng.quote(QuoteRequest(customer_id="cus_new_001", customer_tier="new", lines=[
        QuoteLine(material="Metal Casting", size="M", qty=10, processes=["Metal Etching + Paint"]),
    ]))
    print(json.dumps(r.__dict__, indent=2, ensure_ascii=False))
