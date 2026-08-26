# NEXT SESSION PROMPT — paste into a fresh session

Copy everything below the line.

---

You are continuing the MJCX Trade Agent Appliance — a working, gated product.
Read these first, in order: `HANDOFF.md` (state table + gate board + queue),
`docs/ARCHITECTURE.md` (v1.2 system map — NEW, read it), `docs/spike-log.md`
(traps #1–#41 — do not re-hit them), and `docs/console-plan.md` (design
contract; Part 2 v1.1 done). Everything claimed was executed and verified;
do not redo it.

## Where things stand (session #13, 2026-08-25/26)

- v1 appliance + console v1.1 + **voice overhaul** + **v1.2 THREADS** +
  **autonomy dial**: ALL SHIPPED AND GATED. Board after session #13:
  calc 22/22 · e2e 13/13 · classify PASS · voice PASS (8 cases) · B4 12/12 ·
  O5 auto 10/10 · S9 5/5 · O2 last state 20/20+0fab (skipped #13 with cause:
  dify apps untouched) · build/lint clean.
- **Voice overhaul** (Leonard's real-thread evidence): no more stalls,
  re-greets, or generic pitches. Thread continuity; grounded "not our line"
  + pivot (S1 aliasing: "the ats panel"→ATS-50); concrete capability answers
  from real catalog facts; offer fulfillment — "yes please" delivers info or
  the PDF, "10 units" computes an inline quote (forced PRICE_Q, trap #40);
  zh softeners + seeded samples. Verified on Leonard's real phone.
- **v1.2 THREADS — chatwoot removed from the loop**: spine S4 store
  (`conversations`+`messages`) mirrors every line via glue `_mirror`;
  escalations arm as thread tags w/ staff notes + S8 events; console
  ThreadsPage (route /inbox) = two-col threads, violet bot vs plain human,
  take-over reply sends via evo DIRECTLY and clears the flag; sla_tick v2
  reads spine. Chatwoot still installed but OFF (`CHATWOOT_ENABLED=0` in
  `.env`); legacy `/console/inbox/*` glue proxies kept as rollback.
- **Autonomy dial**: S2 `agent_policy.autonomy` = assistant / standard /
  closer; toggle on Pricing→Terms header; rides the pricing-save pipeline
  (hot reload, no restart). assistant never quotes; closer asks ONE
  clarifying question before handoff. Gates pin STANDARD. Always-human list
  sacred at all levels.
- **Lag root-caused & fixed** (trap #41): webhook routing offloaded to a
  worker thread — console polls stay <150ms during active LLM routing.
- Rules of record: `spine/rules/pricing_rules.generators.json` schema v3
  (`price_visibility`; `agent_policy` currently ABSENT = standard). Editor
  round-trips both keys. Placeholder prices until O3.
- Repo: everything committed on `main` in a deliberate series (~15 commits);
  NO remote configured yet (push pending Leonard creating one). Working tree
  clean.
- Stack running: colima; evo/dify/chatwoot(off)/n8n/postiz/carbone
  containers; uvicorns calc :8100 (RULES_PATH=generators.json via keepalive)
  + spine :8101 + glue :8102 under `scripts/dev_keepalive.sh`. Console dev:
  `cd console && npm run dev` (:5173). **:8090 caddy stamp NOT shipped yet**
  (nothing listens there — don't mistake that for a broken console).
- Spike artifacts left deliberately: chatwoot convs #3/#4 (pre-v1.2
  evidence), spine conversations #1–#4 (v1.2 drills incl. SLA drill).

## Your task

1. **Soak + ship v1.2 (first hour):**
   - Visual pass WITH Leonard of the Threads tab (:5173) — escalation
     badges, take-over to his phone, Resolve flow.
   - If he's happy: stop chatwoot containers (compose override), keep the
     rollback documented; then ship the :8090 stamp (console Dockerfile +
     caddy per docs/console-plan §2) so the dashboard isn't dev-only.
2. **Go-live gates (human inputs — assist, don't wait):**
   - **O3 boss pricing interview** (`runbooks/o3-pricing-interview.md`) —
     ≥10 REAL quotes → `data/o3_history.json` (gitignored!) → backtest ≥90%
     within ±2% before ANY client go-live. Capture boss rules as a NEW v3
     JSON (keep price_visibility; agent_policy only if he chooses non-
     standard), swap PRICING_RULES, backtest via console, interpret misses.
   - **Postiz channel connect** — backend FIXED & PROVEN (trap #42: old
     `latest` backend was dead behind a live frontend; now pinned v2.11.2,
     all pm2 processes online). OPEN PROBLEM (Leonard delegated to this
     session): **browser signup still fails** with Next.js "router state
     header could not be parsed" even after cache clear — server-side auth
     is NOT the problem:
     * POST `/api/auth/register` {email,password,name,company,
       provider:"LOCAL" ← UPPERCASE} → {"register":true} 200 ✓
     * POST `/api/auth/login` same shape → {"login":true} 200 + cookie ✓
     * Probe account already exists: probe@mjcx.test / ProbeTest123!
     Debug order: (1) reproduce headlessly — hit the signup PAGE flow, check
     whether the RSC/server-action path itself 500s on v2.11.2 (frontend
     logs show the router-state throw during HIS attempts); (2) if it's the
     Next skew bug, consider pinning a slightly different v2.11.x patch or
     skipping the UI entirely; (3) LEONARD'S PREFERRED ROUTE: **bypass the
     UI** — register his account via the API above, login (capture
     Set-Cookie), then locate the API-key minting endpoint (look in
     integrations.controller.js / settings.controller.js under
     /app/apps/backend/dist/apps/backend/src/api/routes/ inside the
     container — grep for key routes), mint `POSTIZ_API_KEY`, write `.env`
     WITHOUT printing it, restart glue, rerun
     `tests/test_o5_s9_social.py --expect-scheduled`.
     ⚠ scheduling still needs ONE connected channel (OAuth against the real
     platform — LinkedIn/X app credentials or browser popup). That human
     step may survive the UI problem since incognito might work for OAuth
     even if the dashboard JS is broken — test before assuming.
   - **Phone drills**: S4 PDF-in-thread repeat; S10 live QR drop
     (`tests/test_o5_s10_qr_drill.py --execute`, <5 min).
3. **CLOSE THE PITCH GAPS (the 3 sold products vs reality):**
   - **Email inquiry channel (v1-scope hole)** — IMAP poll (n8n cron or
     glue loop) → normalize to the SAME glue route() path; replies go out
     via email; escalations land in the same spine Threads store. Design
     note first (mailbox config lives in .env per client).
   - **X5 monthly report, full depth + delivery** — AI-answered vs
     escalated counts, median response time, top asked products,
     unanswerable questions (KB misses!), escalation-reason breakdown,
     tier_change events; auto-send to BOSS on schedule (WhatsApp text or
     PDF). "This report is why clients renew."
   - Weekly boss digest (short stats version of the above).
   - **Margin data model (scope decision — ask Leonard):** cost field in
     S2 material rows → calc can compute margin at quote time (internal
     only, X4); surfaces in X5 avg-margin stat. Needed for "knows your
     margins" in the pitch.
   - **Marketplace listings (scope decision — ask Leonard):** in v1 pitch
     or phase 2? If v1: listing generator reuses social-draft machinery
     per marketplace template.
4. **Queued engineering polish (pick when idle):**
   - dify spec DSL fake-promise (#34): structured [NOT_FOUND]-style marker
     in the code node + RE-IMPORT cycle (find the import procedure used for
     a3_triage/spec_answer; update DIFY keys if the app id changes); gates
     after.
   - Webhook-auth hardening DESIGN DOC first (buyer webhook deliberately
     open — options + recommendation before touching anything).
   - X5 report: surface S8 `tier_change` events.
   - Escalation-note dedupe glue-side (consecutive OTHER escalations still
     append near-identical system notes to the same spine thread).
   - Voice-gate flake: capability-zh variation case is borderline
     (canonical opener) — consider stronger diversification for list-format
     replies if it trips again.

## House rules (unchanged, sacred)

1. LLM never does arithmetic — calc computes. Uncomputable → escalate, never guess.
2. Repos stay whole; HTTP-only integration. Client variation lives in DATA + .env.
3. `.env` holds secrets — never print/commit them. Run local python via
   `env -u PYTHONPATH calc/.venv/bin/python …`.
4. After every glue/spine/calc edit, re-run gates: `tests/e2e_spike.py`,
   `tests/test_o5_s9_social.py`, `tests/test_voice.py`, `tests/test_b4.py`,
   (+ classifier when prompts change). Frontend: `npm run build` +
   `npm run lint` clean. Data story changed? Re-run EVERY gate (#29/#30).
   Never block an async handler on sync I/O (#41) — use asyncio.to_thread.
5. Append a dated entry to `docs/spike-log.md` per task with raw results;
   keep HANDOFF §5 current. One in_progress todo at a time.
6. New traps get numbers (#42+).

## Start here

1. `git status` + skim the tail of `docs/spike-log.md` (sessions #13*) to
   confirm state matches above.
2. Health check: `curl localhost:8100/health localhost:8101/health
   localhost:8102/health` — keepalive revives dead uvicorns within 30s;
   containers per cold-start §2 if down.
3. Then bucket 1 (soak+ship) with Leonard, bucket 2 with whatever human
   input exists today. Committing/pushing is Leonard's call — ask first.

Standing human blockers (don't wait on them): boss O3 interview ≥10 REAL
quotes, postiz key/channels, phone drills.
