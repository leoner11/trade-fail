# HANDOFF — MJCX Trade Agent Appliance → next session (ox alpha / any)
### Date: 2026-08-24 (evening) · Sessions #3–#9 by ox alpha · Status: **ALL v1 PHASES BUILT & GATED** — machine waits on real-world inputs only

You are continuing a real, working product. Read `docs/spike-log.md` (traps
#1–#25!) then this file. Everything claimed below was executed and gated —
do not redo it.

---

## 1. WHAT THIS IS

Plug-and-play AI agent line for foreign-trade SMEs (one stack per client).
v1 = inquiry auto-response → quoting → social. The Bible: `WEAVE_PLAN.md`,
`Trade_Agent_Appliance_Flowchart_v1_0.md`, `docs/spike-log.md`.

## 2. CURRENT STATE — verified live on this Mac

| Spec box | Status | Where |
|---|---|---|
| Phase A intake→triage→RAG | ✅ live | glue :8102 → dify :8180 (GLM fallback) |
| A4 KB answers + never-guess | ✅ **O2 quiz 20/20, 0 fabrications** | `tests/test_o2_quiz.py` |
| A6 escalation + human loop | ✅ **v1.2: spine S4 store** — chatwoot OFF (`CHATWOOT_ENABLED=0`), Threads page in console, take-over via evo direct, sla_tick reads spine | glue `_mirror`+`escalate`, `/console/threads/*`, spine `/conversations/*` |
| B inline quotes | ✅ calc :8100 (generator rules), S5 save+sent | `tests/e2e_spike.py` 13/13 |
| B4 formal PDF in chat | ✅ carbone :8200 + soffice → evo sendMedia | `tests/test_b4.py` 12/12 |
| B5 human quote path | ✅ gaps hint lands in chatwoot w/ draft | glue escalate hooks |
| B6 follow-up + APPROVE | ✅ n8n cron → drafts to staff WA → APPROVE sends | `n8n/workflows/`, `/b6/tick` |
| SLA beacon (>2h unanswered) | ✅ boss WA nudges, once per conversation | `/a6/sla_tick` |
| Phase C social | ✅ draft→boss card→APPROVE/REJECT→postiz push | `/c/draft_tick`, postiz :13000 |
| O1 stamp | ✅ compose validated + images build | `compose/docker-compose.appliance.yml` |
| O5 acceptance | ✅ auto scenarios **10/10** incl. off-domain S8b | `tests/test_o5_acceptance.py` |
| Voice layer | ✅ generated replies, digit/link/capability guards | voice_guide.md rules 1–8 |
| Appliance Console | ✅ **SHIPPED** — M0–M5: runtime views, WA QR connect, KB+O2 gate, pricing+O3 gate, go-live page, voice samples editor, X5 report. :8090 in stamp, token-gated | `console/`, `docs/console-plan.md` |

**Gate board (after session #13, 2026-08-25):** calc 22/22 · e2e 13/13 ·
classify PASS 17/17 · voice PASS 8/8 (expanded: capability + not-ours
cases) · B4 12/12 · O2 20/20+0fab (last run; skipped #13 with cause —
dify apps untouched) · O5 auto 10/10 · S9 5/5 · O3 example-mode ✓.
Run them: they are plain scripts under `tests/`. If the data story changes,
re-run EVERY gate — stale fixtures bite (spike-log traps #29/#30).

**Stack running now:** evo :8080 · dify :8180 · chatwoot :3000 ·
carbone :8200 · n8n :5678 · postiz :13000 · calc/spine/glue (uvicorns,
guarded by `scripts/dev_keepalive.sh`). ~5 GB RAM total.

**Data story:** ONE aligned generator line (DG-30/50/100 · ATS-50 ·
STS-200): S1 catalog = S2 `pricing_rules.generators.json` = dify KB
(`data/example/knowledge/`). Trophy file remains as unit-test fixture only.
⚠️ Generator prices are PLACEHOLDERS.

## 3. NON-NEGOTIABLE RULES (unchanged — still sacred)

1. LLM never does arithmetic — calc computes.
2. Uncomputable → escalate with gaps, never guess.
3. Always-human list hardcoded (complaints, payment/legal, discount > cap, low confidence).
4. Repos stay whole; HTTP-only integration.
5. Client variation lives in DATA (S1/S2/S3/S6) + `.env` — never code edits.
6. Config-as-code: DSLs, workflows, compose, prompts in git (S7).
7. `.env` holds secrets. Never print/commit keys.
8. `env -u PYTHONPATH <venv>/bin/python` discipline for every local run.

## 4. ENVIRONMENT

- Full boot order: `runbooks/cold-start.md` (covers every container +
  uvicorns + keepalive + first-boot checklists). Trust it, don't improvise.
- Key traps live in `docs/spike-log.md` §"New traps" of each session —
  highlights: carbone v5 async API (#19), evo sendMedia not sendDocument
  (#20), chatwoot webhooks fire from sidekiq (#17) + SafeFetch private-net
  (#18) + DNS alias collisions (#16), postiz serves on 5000 (#25),
  n8n import needs top-level id (#23), host reachability via
  host.docker.internal only (#22).

## 5. NEXT SESSION — in order

1. **O3 real pricing (the go-live gate)** — run
   `runbooks/o3-pricing-interview.md` with Leonard's boss; capture answers
   into a new rules JSON + 10–20 real quotes into `data/o3_history.json`;
   `tests/test_o3_backtest.py` must hit ≥90% within ±2% before ANY client
   go-live. Harness already runs in EXAMPLE mode so you can verify plumbing.
   NOTE: rules now ship as schema v3 — keep `price_visibility` when writing
   the boss's real file (the editor round-trips it automatically).
2. **Postiz channel connect** — owner signup at :13000, connect channels,
   create API key → `.env POSTIZ_API_KEY` → restart glue → rerun
   `tests/test_o5_s9_social.py --expect-scheduled`.
3. **Physical phone drills** — S4 PDF-in-thread confirm (already delivered
   once ✓, repeat on a clean ask); S10 real drop:
   `tests/test_o5_s10_qr_drill.py --execute` (target <5 min self-serve).
   Eyeball the Inbox tab on :8090/:5173 (drill conv #3 open) AND the new
   voice behavior artifacts in chatwoot convs #3/#4 (session #13).
4. **Voice overhaul DONE (session #13, 2026-08-25)** — replies no longer
   stall/re-greet/pitch generically; grounded "not our line" + pivot,
   concrete capability answers from S1 facts, thread continuity, zh
   softeners + seeded samples (from Leonard's real-thread evidence), and
   offer fulfillment: the bot now DELIVERS when the buyer accepts its own
   offer ("yes please" → details/PDF), never hands off (traps #35/#36).
   Quantity replies close the sale loop inline ("10 units" → computed
   quote; trap #40). Verified on Leonard's real phone. Follow-up queued:
   dify spec DSL still fake-promises "let me check" on attribute misses
   (trap #34) — needs structured marker + re-import.
5. **v1.2 THREADS DONE (session #13 cont., 2026-08-26)** — chatwoot removed
   from the loop (installed, disabled): spine S4 store mirrors every line;
   console Threads page = escalations + take-over via evo direct;
   sla_tick reads spine. Event-loop lag fixed (trap #41 — webhook routing
   offloaded). Soak it, then stop the chatwoot containers and ship the
   :8090 caddy stamp.
6. Optional polish: webhook-auth hardening design doc (buyer webhook is
   deliberately open); X5 report: surface S8 `tier_change` events.

## 6. REPORTING BACK

Keep `docs/spike-log.md` as the single source of truth — append a dated
entry per task with raw results. One in_progress todo at a time.

*Built by Hermes + Claude + ox alpha (sessions #1–#9), Aug 2026.
The organs work, the gates are green. What's left is sales material.*
