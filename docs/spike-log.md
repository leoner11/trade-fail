# Spike Log — 2026-08-19 (Phase 0 of the flowchart)

Goal: prove the Phase A→B money path pieces locally, no client, no risk.

## What was proven ✅

| Piece | Result |
|---|---|
| **calc engine (our IP)** | 18/18 unit tests. Deterministic pricing, qty tiers, process fees, customer tiers, escalation-with-gaps (`NotComputable` → B5), JSON-safe for dify tools. FastAPI service on :8100. |
| **spine (our IP)** | SQLite S1/S3/S5/S8 + HTTP API on :8101. Identity resolution (A2-1) known/new, catalog lookup, quote store + status machine (draft→sent→accepted…). |
| **E2E money path** | 10/10: resolve buyer → quote via HTTP ($4360.50, matches unit math) → escalate unpriceable w/ gaps → save quote → status→sent. |
| **carbone docker EE** | Template upload + JSON render → complete DOCX, values to the cent, markers all replaced. Listens on **port 4000** (not 3000 — cost us 20 min). |
| **DOCX → PDF** | LibreOffice headless (`soffice --headless --convert-to pdf`) → `spine/templates/quote_spike_sample.pdf`, PDF 1.7, 1 page, 37KB. |

## Full chain proven

```
buyer ask (parsed) → calc /quote → spine /quotes (S5)
                  → carbone-ee /render (template upload once)
                  → soffice --headless --convert-to pdf
                  → PDF in spine/templates/quote_spike_sample.pdf
```

## Traps found (do not re-hit)

1. **carbone npm CE (v4) corrupts our template** — output `document.xml`
   truncated to 350 bytes, Word says "error in the document". Root cause:
   npm CE is a major version behind (v4 vs v5 docker). **Use docker
   `carbone/carbone-ee` for rendering; it's correct.** (npm install is fine
   for nothing; skip it in the repo — Dockerfile deps only.)
2. **carbone-ee PDF *conversion* is license-gated** — `convertTo: pdf`
   silently ignored without a license key; you get DOCX back. PDF via
   self-run LibreOffice instead (free, unlimited).
3. **carbone-ee in-container port is 4000**, despite READMEs implying 3000.
4. **carbone array rows need `[i+1]` markers** — `{d.lines[i].desc}` alone →
   w101 error. Template generator already fixed.
5. **pydantic + `from __future__ import annotations`** breaks
   function-local models (ForwardRef). Removed from calculator.py.
6. **PYTHONPATH leak** — Hermes session exports PYTHONPATH into shells;
   always run project venv binaries via `env -u PYTHONPATH .venv/bin/…`.
7. Word AppleScript "save as PDF" unreliable headless (-1708); LibreOffice
   headless is the dependable converter on this Mac.
8. uvicorn installed via brew python needs `--python .venv` discipline; use uv.

## Ports (spike allocation)

| Port | Service |
|---|---|
| 8100 | calc (ours) |
| 8101 | spine (ours) |
| 8200 | carbone-ee docker (maps to in-container 4000) |
| 8080 | evolution-api (next session) |

## Not yet done (next session)

- dify stack up + inquiry workflow DSL (needs an LLM key from Leonard)
- evolution-api instance + WhatsApp test number QR scan (needs Leonard, 5 min)
- evo ↔ dify ↔ chatwoot native config screens walked end to end
- postiz container (Phase C)
- The above chained with calc/spine as dify custom tools → full A→B on a
  real phone

## Stack decisions locked by this spike

- Rendering: carbone-ee docker (docx) + soffice (pdf). No carbone Cloud,
  no EE license needed at this scale.
- calc/spine: python 3.12 + FastAPI + uv venvs. Containerize later with the
  existing Dockerfiles.
- PDF artifact naming: quote_spike_sample.pdf = proof, keep in repo.

---

## Changelog after the spike

### 2026-08-19 — S3 owns the tier (flowchart X1 fix), repo put under git

**The bug:** customer tier was declared twice — `spine.customers.tier` (S3)
*and* `pricing_rules.customer_tiers[].customer_ids` (S2) — and calc read only
the S2 copy. Any customer spine created at runtime priced as if untiered until
a human hand-edited the rules JSON. Two opinions about a customer is exactly
what X1 forbids.

**The fix:**
- S3 says WHICH tier a customer is in. S2 says what that tier COSTS. Nothing
  says both.
- `QuoteRequest.customer_tier` / `POST /quote {"customer_tier": …}` — the
  caller (dify) passes what `spine /resolve` returned, per B2-1.
- `customer_id` is carried for S5 linkage and tracing only; it no longer
  moves the price. Test T7c pins this.
- rules: `customer_ids` removed, explicit `new` tier (factor 1.0) added,
  `schema_version` 1 → 2.
- Unknown tier → `NotComputable` with a rules-gap hint → B5. No guessed
  factor, ever (Principle #5). Tests T7b / E2E-4b pin this.

calc 22/22, e2e 13/13. Reference quote still $4360.50 — price-neutral.

**Also:** `git init` + first commit. Until now S7 ("config-as-code repo") and
S2 ("version controlled") were aspirational — there was no history at all.

### Known-stale, not yet fixed (see next session)

1. `calc/render_quote.js` contradicts trap #1 above — its header argues for
   local npm carbone CE, which is the path that *corrupts the template*.
   Rewrite against carbone-ee docker + soffice, or delete it.
2. `compose/docker-compose.appliance.yml` has drifted from what actually
   runs: carbone mapped to in-container 3000 (it's 4000), image
   `atendai/evolution-api` (running: `evoapicloud/evolution-api`, plus a
   postgres compose doesn't declare), and no dify / chatwoot / postiz / n8n.
   The live stack was hand-started, not stamped.
3. `.gitignore` excludes `spine/templates/*.pdf`, but this log says to keep
   `quote_spike_sample.pdf` as proof. Pick one.
4. S8 (`events`) has a schema and no writer — nothing logs escalations,
   session drops, or quote events, so X3/X5 have no data to stand on.
5. `spine /resolve` with neither wa_jid nor email always creates a new
   customer — no dedupe. Source of the stray `Walk-in Buyer` rows.
