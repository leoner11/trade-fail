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
| Agent autonomy dial | ✅ `assistant`/`standard`/`closer` in S2 `agent_policy` — console toggle on Pricing→Terms, hot-reloads via the save pipeline; always-human list sacred at ALL levels | PricingPage header + glue `AUTONOMY` |
| Natural-sales voice layer | ✅ thread continuity, offer fulfillment ("yes please"/"10 units" close the loop), grounded not-our-line, capability answers from S1, alias resolution, noise gate | session #13, spike-log traps #32–#41 |
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
| Email inquiry channel | ✅ **BUILT (#14)** — pseudo-jid `email:*` through the SAME route(); IMAP poll + SMTP replies; escalations arm the same Threads store | glue `_handle_email`+`/email/poll`, `docs/design-email-channel.md`, gate 12/12 |
| X5 report full depth | ✅ **BUILT (#14)** — spine `/reports/x5` computes (AI vs escalated, median response, KB misses, reasons, tier_change); `/x5/send` delivers to boss WA (drilled live); monthly+weekly n8n clocks | spine_api, glue `_x5_text`, console ReportsPage |
| :8090 stamp | ✅ **LIVE (#14)** — caddy serves SPA + /spine /glue proxies; dual-topology upstreams (host uvicorns ↔ compose names) | `console/Dockerfile`, `console/Caddyfile`, container `console-stamp` |

**Gate board (after session #14, 2026-08-26):** calc 22/22 · e2e 13/13 ·
voice PASS 8/8 · B4 12/12 · S9 5/5 · **email 12/12** (new) · **O5 auto
10/10** (re-run after the email-channel glue edits) · console build/lint
clean. O2 skipped #13–#14 with cause (dify apps untouched).
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

1. **Leonard soak + sign-offs (session #15 opener):**
   - Threads tab visual pass (:8090 now LIVE or :5173) → if happy, STOP the
     chatwoot containers (compose override; rollback proxies stay).
   - Postiz: signup should work now (#14 fixed `NEXT_PUBLIC_BACKEND_URL`).
     Owner account is ALREADY probe@mjcx.test / ProbeTest123! (SUPERADMIN,
     key wired into .env). Connect ≥1 channel under THAT org (OAuth popup)
     → rerun `tests/test_o5_s9_social.py --expect-scheduled`. If he wants
     his own account instead: channels live per-org — re-point .env at his
     org's key via login→`GET /api/user/self`→`publicApi`.
   - Phone drills: S4 PDF-in-thread repeat · S10 live QR drop
     (`tests/test_o5_s10_qr_drill.py --execute`).
   - SCOPE QUESTIONS for boss: (a) margin data model — cost field in S2
     rows so calc computes margin internally (X4/X5)? (b) marketplace
     listings — v1 scope or phase 2?
2. **O3 real pricing (THE go-live gate)** — run
   `runbooks/o3-pricing-interview.md`; ≥10 REAL quotes into
   `data/o3_history.json` (gitignored); backtest ≥90% within ±2% before ANY
   client go-live. Keep price_visibility when writing the real rules file.
3. **Email channel live round-trip** — wire client mailbox creds into .env,
   import n8n email_poll_tick.json, send a real mail, target <60s.
4. **X5 clocks** — import x5_monthly/x5_weekly n8n workflows and activate.
5. Optional polish: dify spec DSL fake-promise #34 (structured marker +
   re-import; then kb_misses becomes exact), webhook-auth hardening DESIGN
   DOC, escalation-note dedupe glue-side, voice-gate zh variation flake.

## 6. REPORTING BACK

Keep `docs/spike-log.md` as the single source of truth — append a dated
entry per task with raw results. One in_progress todo at a time.

*Built by Hermes + Claude + ox alpha (sessions #1–#9), Aug 2026.
The organs work, the gates are green. What's left is sales material.*
