# NEXT SESSION PROMPT — paste into a fresh session

Copy everything below the line.

---

You are continuing the MJCX Trade Agent Appliance — a working, gated product.
Read these first, in order: `HANDOFF.md` (state table + gate board + queue),
`docs/spike-log.md` (traps #1–#31 — do not re-hit them), and
`docs/console-plan.md` (design contract; **Part 2 v1.1 A+B+C is DONE**).
Everything claimed in those files was executed and verified; do not redo it.

## Where things stand

- v1 appliance + Appliance Console v1.1: ALL SHIPPED AND GATED
  (calc 22/22 · e2e 13/13 · classify PASS · voice PASS · B4 12/12 ·
  O2 20/20+0fab last run · O5 auto 10/10 · S9 5/5 · build/lint clean).
- Console v1.1 (session #12, 2026-08-25) delivered:
  - **A Inbox face + take-over**: `/console/inbox/*` glue proxies over
    chatwoot (second client, never second store). Two-col tab at `/inbox`,
    violet bot lines vs plain humans, free-edit PUBLIC reply under the ADMIN
    identity. `CHATWOOT_ADMIN_TOKEN` in `.env` — trap #28: the old API token
    belonged to the evo-bridge user and could NEVER flip sla_tick. Drill
    passed (beacon before reply, silent after, idempotency ruled out).
  - **B Pricing form editor**: calc `POST /rules/reload` (+ `/rules/validate`,
    lock + .bak rollback); glue save endpoint refreshes its B1 parse vocab
    live (no restart); console §20 overlay w/ guarded numerics, semantic
    +/- diff, add/delete of process fees & sizes, editable ISO currency.
    Glue now passes S2 currency into calc (was silently cosmetic before).
  - **C Price visibility**: S2 schema v3 `price_visibility`
    (STS-200 = internal_only), enforced STRUCTURALLY in glue BEFORE calc —
    internal asks route to B5, buyer hears "team will confirm". Editor
    toggle + viewer eye column + QuotesPage "internal" tag w/ hidden totals.
  - **Leonard's same-day follow-ups**: manual catalog add/edit/delete
    (`POST /catalog/item`, `DELETE /catalog/{sku}`), KB "write a doc"
    textarea (reuses kb/ingest), and staff-set customer tiers:
    `PATCH /customers/{cid}` + CustomersPage edit panel — tier select is
    sourced FROM S2's tier list (agent never assigns tiers; unknown tier ⇒
    calc escalates; changes audited as S8 `tier_change` events).
- Rules of record: `spine/rules/pricing_rules.generators.json` schema **v3**
  (keep `price_visibility` intact when the boss's real numbers land; the
  editor round-trips it automatically). Placeholder prices until O3.
- `/console/*` glue endpoints bearer-gated by CONSOLE_TOKEN (in `.env`;
  never print it). Buyer webhook stays unauthenticated by design (hardening
  note in HANDOFF/spike-log).
- Stack on this Mac (left running): colima up; evo/dify/chatwoot/n8n/postiz/
  carbone containers up; uvicorns calc :8100 (RULES_PATH=generators.json,
  set by keepalive) + spine :8101 + glue :8102 up under
  `scripts/dev_keepalive.sh`. Boot recipe if needed: `runbooks/cold-start.md`.
  Dev console: `cd console && npm run dev`. Spike artifacts left in place on
  purpose: chatwoot conv #3 (open, for Inbox-tab eyeballing).

## Your task

No big spec'd build queue remains — the console-plan Part 2 is fully built.
Work falls into three buckets, in this order:

1. **Support the go-live gates (human inputs — assist, don't wait):**
   - **O3 boss pricing interview** (`runbooks/o3-pricing-interview.md`) —
     ≥10 REAL quotes → `data/o3_history.json` → backtest must hit ≥90%
     within ±2% before ANY client go-live. If Leonard brings numbers mid-
     session: capture them as a NEW rules JSON (v3!), swap PRICING_RULES,
     run the backtest through the console, help interpret misses.
   - **Postiz channel connect** — owner signup :13000, channels, API key →
     `.env POSTIZ_API_KEY` → restart glue → rerun
     `tests/test_o5_s9_social.py --expect-scheduled`.
   - **Phone drills**: S4 PDF-in-thread repeat; S10 live QR drop
     (`tests/test_o5_s10_qr_drill.py --execute`, <5 min target); visual pass
     of the Inbox tab + pricing editor + catalog forms on :5173/:8090.
2. **Optional polish (pick only if no human input is available):**
   - escalation-note dedupe in chatwoot (consecutive OTHER escalations re-arm
     the same conversation with identical notes);
   - "what do you actually do?" should answer concretely instead of
     greeting-pitch;
   - webhook-auth hardening design (buyer webhook is deliberately open —
     document options before touching anything);
   - X5 report: surface the new `tier_change` audit events.
3. **Repo hygiene (ask Leonard first — committing is his call):** the whole
   appliance (glue/, console/, tests/, docs/, compose changes…) is still
   uncommitted on `main`. If he agrees: stage deliberately, no secrets
   (`.env` is ignored; verify `.gitignore` covers `.env`, `.bak` files,
   `spine/quotes_pdf/`), sensible commit series, then push if a remote exists.

## House rules (unchanged, sacred)

1. LLM never does arithmetic — calc computes. Uncomputable → escalate, never guess.
2. Repos stay whole; HTTP-only integration. Client variation lives in DATA + .env.
3. `.env` holds secrets — never print/commit them. Run local python via
   `env -u PYTHONPATH calc/.venv/bin/python …`.
4. After every glue/spine/calc edit, re-run gates: `tests/e2e_spike.py`,
   `tests/test_o5_s9_social.py`, `tests/test_voice.py`, `tests/test_b4.py`,
   (+ classifier when prompts change). Frontend: `npm run build` +
   `npm run lint` clean. If the data story changes, re-run EVERY gate —
   stale fixtures bite (traps #29/#30).
5. Append a dated entry to `docs/spike-log.md` per task with raw results;
   keep HANDOFF §5 current. One in_progress todo at a time.
6. New traps get numbers (#32+).

## Start here

1. `git status` + skim the tail of `docs/spike-log.md` (sessions #12*) to
   confirm state matches above.
2. Health check: `curl localhost:8100/health localhost:8101/health
   localhost:8102/health` — keepalive revives any dead uvicorn within 30s;
   containers per cold-start §2 if down.
3. Then work bucket 1 with whatever human input exists today; bucket 3 needs
   an explicit yes from Leonard.

Standing human blockers (don't wait on them): boss O3 interview ≥10 REAL
quotes, postiz key/channels, phone drills.
