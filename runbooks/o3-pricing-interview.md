# O3-1 — Pricing Rules Interview (the boss's head → S2)

Goal: turn "how we actually price" into `spine/rules/pricing_rules.*.json`.
Timebox: 60–90 min with the decision maker. Bring the current rules file
printed, and 10–20 real past quotes (Excel/PDF/WeChat screenshots).

## Ask, in this order

1. **Products & base prices** (→ `material_base_prices`)
   - "Which models do you actually sell? What's the FOB price for ONE unit?"
   - "Is there a different price at volume? From how many?" (→ `bulk_price`)
2. **Quantity tiers** (→ `quantity_discounts`)
   - "At what quantities do you start giving discounts, and how much?"
   - Capture the LADDER exactly (min_qty → discount_pct), including the top rung.
3. **Options / add-on fees** (→ `process_fees`)
   - "What extras do customers ask for, and what do you charge? (canopy,
     controller, warranty, installation…)"
4. **Size/config coefficients** (→ `size_coefficients`)
   - "Any variant that changes price by a factor? What's manual-quote-only?"
     (coef 0 = never auto-price → escalation escape hatch)
5. **Customer types** (→ `customer_tiers`)
   - "Do new / returning / distributor customers pay differently? Factors?
     Payment terms for each?" (terms land on the quote)
6. **Guardrails** (→ `authority`)
   - "What discount can the sales assistant give WITHOUT asking you?"
     (max_discount_pct — the AI's hard cap; anything beyond escalates to you)
7. **Validity & currency**
   - "How long is a quote valid? Which currency?" (`validity_days`, `currency`)

## Then (O3-2)

- Type the answers into a copy of the rules JSON.
- Pull 10–20 REAL past quotes into `data/o3_history.json`
  (ref / customer_tier / lines / quoted_total).
- Run: `env -u PYTHONPATH calc/.venv/bin/python tests/test_o3_backtest.py`
- ≥90% within ±2% → rules trusted → go-live allowed.
  Anything less → interview round 2 on the mismatches only.

## Red flags to listen for

- "It depends…" without a number → that line belongs in XL/manual or a
  process fee, not a guessed coefficient.
- "Usually around X" → pin it. The AI cannot price vibes.
- Discounts given per-customer ad hoc → that's what tiers + authority cap
  are for; anything outside becomes an escalation, not a rule.
