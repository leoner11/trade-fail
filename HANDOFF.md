# HANDOFF — MJCX Trade Agent Appliance → next session
> ⚠ SUPERSEDED for planning purposes by HANDOFF-2026-09-14.md (console hookup:
> all 9 agent surfaces in the UI, intel-digest fix, traps #50–#51). Then
> HANDOFF-2026-09-08.md (platform build-out: entitlement layer, 9 gated
> agents, flowchart v2). Keep for v1 history and traps. (ox alpha / any)
### Date: 2026-08-27 · Sessions #3–#16 · Status: **ALL v1 PHASES + CONVERSATION CORE v2 BUILT & GATED — v2 soak LIVE**

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
| Natural-sales voice layer | ✅ thread continuity, offer fulfillment ("yes please"/"10 units" close the loop), grounded not-our-line, capability answers from S1, alias resolution, noise gate, bare-SKU rescue, model-line gate, hyphenless SKU matching + deterministic fulfillment fallback + last-SKU memory | session #13 + #15, spike-log traps #32–#41, #46 |
| **Conversation core v2** | ✅ **BUILT + GATED (#16), SOAK LIVE** — ONE stateful tool-calling agent loop (`glue/agent.py`, glm-4.5-air; flash benchmarked 19/22 + 3.6× slower → rejected) over the organs via tools catalog_lookup/list_models/kb_search/price_quote/escalate; deterministic pre-guards (noise/complaint/spam/agreement-fulfillment) + post-guards (digits ⊆ tool facts ∪ guarded thread, exact-mode quotes, deterministic fallbacks); memory = S4 last-20 turns + `agent_state` spine column (restart-proof); dify trap #34 CLOSED ([[KB_NOT_FOUND]] marker); behind CONVERSATION_CORE=v1\|v2, **.env=v2 now live**, v1 frozen in-tree as 30s rollback; S15–S19 pin the six live flakes verbatim | `docs/design-conversation-core-v2.md`, `glue/agent.py`, `dify/prompts/agent_core_v2.md`, session #16 spike-log |
| B inline quotes | ✅ calc :8100 (generator rules), S5 save+sent | `tests/e2e_spike.py` 13/13 |
| B4 formal PDF in chat | ✅ carbone :8200 + soffice → evo sendMedia | `tests/test_b4.py` 12/12 |
| B5 human quote path | ✅ gaps hint lands in chatwoot w/ draft | glue escalate hooks |
| B6 follow-up + APPROVE | ✅ n8n cron → drafts to staff WA → APPROVE sends · **LIVE-FIRE VERIFIED #16** (8 drafts, idempotent, fail-closed on seed JIDs) · **console approvals (#16): Quotes page shows pending drafts VERBATIM + Approve&send / Dismiss** (same handler as WA APPROVE; dismiss = draft only, S5 untouched) | `n8n/workflows/`, `/b6/tick`, `/console/b6/*`, QuotesPage FollowupPanel |
| SLA beacon (>2h unanswered) | ✅ boss WA nudges, once per conversation | `/a6/sla_tick` |
| Phase C social | ✅ **HEADLESS (#14)** — postiz = engine only; console Channels panel drives it via auth-header (trap #45: their UI unusable on Safari); OAuth callbacks land on OUR console | `/console/social/*`, SocialPage + callback route |
| O1 stamp | ✅ compose validated + images build | `compose/docker-compose.appliance.yml` |
| O5 acceptance | ✅ auto scenarios **10/10** incl. off-domain S8b | `tests/test_o5_acceptance.py` |
| Voice layer | ✅ generated replies, digit/link/capability guards | voice_guide.md rules 1–8 |
| Appliance Console | ✅ **SHIPPED** — M0–M5: runtime views, WA QR connect, KB+O2 gate, pricing+O3 gate, go-live page, voice samples editor, X5 report. :8090 in stamp, token-gated | `console/`, `docs/console-plan.md` |
| Email inquiry channel | ✅ **BUILT (#14)** — pseudo-jid `email:*` through the SAME route(); IMAP poll + SMTP replies; escalations arm the same Threads store | glue `_handle_email`+`/email/poll`, `docs/design-email-channel.md`, gate 12/12 |
| X5 report full depth | ✅ **BUILT (#14)** — spine `/reports/x5` computes (AI vs escalated, median response, KB misses, reasons, tier_change); `/x5/send` delivers to boss WA (drilled live); monthly+weekly n8n clocks | spine_api, glue `_x5_text`, console ReportsPage |
| :8090 stamp | ✅ **LIVE (#14)** — caddy serves SPA + /spine /glue proxies; dual-topology upstreams (host uvicorns ↔ compose names) | `console/Dockerfile`, `console/Caddyfile`, container `console-stamp` |

**Gate board (after session #16, 2026-08-27):** e2e 13/13 · voice PASS
· B4 12/12 · email 12/12 · **O5 22/22 on BOTH cores** (v1 frozen + v2
agent; S11–S14 regression pins + S15–S19 = the six live flakes pinned
verbatim) · S9 **--expect-scheduled 4/4** (plain mode structurally red
while a postiz key + channel exist — trap #47; postiz entry deleted by
group + S6 zeroed after the run) · **O2 quiz 20/20, 0 fabrications**
(dify DSL touched → re-run required, passed). O3 untouched (example
mode). Trap #46: one-off B1 size-clarify flake — watch, don't fix yet.
Run them: they are plain scripts under `tests/`. If the data story
changes, re-run EVERY gate — stale fixtures bite (traps #29/#30).
v2 gate runs need `CONVERSATION_CORE=v2` in the env; v1 needs nothing
(default). GLM API had one transient brownout mid-gate (slow-trickle
stall) — background+poll rerun pattern is in the session #16 log.

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

1. **Conversation core v2 soak (LIVE since #16):** glue runs v2 on real
   traffic (.env CONVERSATION_CORE=v2). Leonard's phone drills = repeat
   the six flakes verbatim + normal sales threads. Any new flake → pin
   as a v2 scenario + tune prompt/tools (v1 cascade stays FROZEN as the
   30s rollback: flip the env line, keepalive revives). One clean week →
   flip the code default to v2 → only then delete the v1 cascade
   (~700 lines) with its breadcrumb regexes. Watch: premium GLM tiers
   unbillable (trap #48) — resource pack reopens glm-4.5 benchmark via
   CONVERSATION_MODEL.
2. **B6 console approvals — Leonard drill:** Quotes page → Q-AFCDFB
   (real jid) → Approve → follow-up lands on the phone. Then dismiss
   the ~25 seed-artifact drafts (Test Buyer / PT Contoh Repeat / no-jid)
   with one click each — they keep reappearing 48h after each gate run
   unless purged; bulk S8 purge offered if clicking gets old.
3. **Leonard soak + sign-offs:**
   - Threads tab visual pass (:5173 dev is Leonard's daily; :8090 stamp
     is the deployable same app) → if happy, STOP the chatwoot
     containers (compose override; rollback proxies stay).
   - Postiz: FORGET their frontend (trap #45 — Safari drops its session
     cookie; register/login actually returned 200). Console → Social →
     Channels: "Connect linkedin/x" opens the provider's consent popup
     and the callback lands on our console. STILL NEEDS from Leonard:
     provider app creds inside postiz env (LINKEDIN_CLIENT_ID/SECRET,
     X_API_KEY/SECRET, …) + whitelisting
     `http://localhost:8090/integrations/social/<platform>` as the
     callback URL in each developer app. Then rerun
     `tests/test_o5_s9_social.py --expect-scheduled`.
   - Phone drills: S4 PDF-in-thread repeat · S10 live QR drop
     (`tests/test_o5_s10_qr_drill.py --execute`).
   - SCOPE QUESTIONS for boss: (a) margin data model — cost field in S2
     rows so calc computes margin internally (X4/X5)? (b) marketplace
     listings — v1 scope or phase 2?
4. **O3 real pricing (THE go-live gate)** — run
   `runbooks/o3-pricing-interview.md`; ≥10 REAL quotes into
   `data/o3_history.json` (gitignored); backtest ≥90% within ±2% before
   ANY client go-live. Keep price_visibility when writing the real
   rules file.
5. **Email channel live round-trip** — wire client mailbox creds into
   .env, import n8n email_poll_tick.json, send a real mail, target <60s.
6. **X5 clocks** — import x5_monthly/x5_weekly n8n workflows and
   activate.
7. Optional polish: webhook-auth hardening DESIGN DOC, escalation-note
   dedupe glue-side, voice-gate zh variation flake. (dify #34 is DONE —
   marker shipped #16; kb_misses in X5 can now key on the new
   `kb_miss` S8 event instead of SPEC_Q escalations.)

⚠️ Trap #49 (bites anyone touching the stamp): `docker compose -f
compose/docker-compose.appliance.yml up -d console` DRAGS UP dependency
containers that SHADOW the host uvicorns (spine container's
127.0.0.1:8101 binding beats *:8101 → dashboards go quietly empty).
Stamp rebuild = `docker compose … build console` then recreate
`console-stamp` by hand (`docker run -d --name console-stamp -p
127.0.0.1:8090:80 -p 127.0.0.1:80:80 trade-agent-console`). If
trade-agent-{spine,calc,glue}-N ever shows in docker ps: `docker rm -f`
it — host uvicorns + keepalive are the organs of record.

## 6. REPORTING BACK

Keep `docs/spike-log.md` as the single source of truth — append a dated
entry per task with raw results. One in_progress todo at a time.

*Built by Hermes + Claude + ox alpha (sessions #1–#9), Aug 2026.
The organs work, the gates are green. What's left is sales material.*
