# NEXT SESSION PROMPT — paste into a fresh session

Copy everything below the line.

---

You are continuing the MJCX Trade Agent Appliance — a working, gated
product. Read these first, in order: `HANDOFF-2026-09-14.md` (latest —
what session #17 changed and why), `HANDOFF-2026-09-08.md` (platform
build-out: entitlement layer, 9 gated agents, flowchart v2),
`docs/spike-log.md` (traps #1–#51 — do not re-hit them), and
`docs/modular-agent-platform-plan.md` (statuses current). Everything
claimed was executed and verified; do not redo it.

## Where things stand (session #17, 2026-09-14)

- **The console now front-ends EVERY available agent.** Session #17
  built the four missing surfaces: **Positioning** (paste listings →
  GLM memo w/ [L<n>] citations → promote drafts → approve → live),
  **Market Intel** (feed fetch, GLM digest w/ [I<id>] contract,
  kind-filtered table), **Procurement** (suppliers + items + POs with
  status transitions), **Doc-Gen** (Documents panel in Quote detail →
  carbone render → .docx download). Nav is entitlement-aware; all
  agents/manifest.json `available` agents are one click away.
- **Fixed a born-dead endpoint:** `/console/intel/digest` had been 500ing
  since it was written (copy-paste corruption) while its gate stayed
  green via a silent skip — now rewritten (trap #51) and the gate's live
  check is REAL: intel gate 11/11. Also: spine `/catalog` list now
  returns `status` (PROPOSED drafts were invisible), duplicate
  `/console/positioning/promote` route removed, docgen manifest routes
  truthed.
- **Trap #50:** entitlement `LICENSE_SECRET` is read from `os.environ`
  ONLY (not the `.env` fallback glue's `cfg()` uses) — host-run
  uvicorns need it exported or licensing silently falls back to open.
- Gate board after #17: manifest 11/11 · entitlements 22/22 ·
  positioning 8/8 · intel 11/11 · procurement 13/13 · customer
  knowledge 12/12 · docgen 7/7 (+1 skip) · console build green.
  Live browser drills of all four surfaces passed (see HANDOFF §2).
- Stack RUNNING on this Mac: colima; evo :8080 (WhatsApp `mjcx-test`
  connected; restart policy fixed to unless-stopped) · dify :8180 ·
  carbone :8200 · n8n :5678 · postiz :13000 · chatwoot :3000
  (auto-started, off by design — ignore or stop) · uvicorns calc/spine/
  glue under keepalive · vite :5173. **:8090 stamp serves the OLD
  image** — new pages are dev-only until a rebuild (trap #49 recipe).
- Working tree UNCOMMITTED (two sessions of work). Committing/pushing
  is Leonard's call — ask first.

## Your task

1. **Leonard visual pass (first hour):** the three new pages at :5173 —
   Positioning with a REAL category's listings (analyze → promote →
   approve), Market Intel digest wording, Procurement PO flow vs how he
   actually buys. Cheap to change now; bake his verdicts in.
2. **Ship the stamp:** `docker compose -f compose/docker-compose.appliance.yml
   build console` → recreate `console-stamp` by hand (trap #49: NEVER
   `up -d console`) so :8090 matches :5173.
3. **Human-input buckets (assist, don't wait):**
   - **O3 boss pricing interview** — STILL the go-live gate
     (`runbooks/o3-pricing-interview.md`): ≥10 REAL quotes →
     `data/o3_history.json` (gitignored) → backtest ≥90% within ±2%.
   - **ASR decision** (unblocks Meeting Intel): speaches (~1-2GB RAM)
     vs GLM-ASR (0 RAM, ≤30s clips) → 10-clip bake-off.
   - **Per-client activation data:** feeds.json curation, first 5
     suppliers w/ terms + lead times, cost fields into S2 (margin —
     standing scope question for the boss), carbone template branding.
4. **When idle:** security backlog (09-08 §6 — note trap #50's
   verify-failure lands on open; fail-closed closes it), payment rail,
   escalation-note dedupe. SOP Guide stays parked until a client brings
   SOPs.

## House rules (unchanged, sacred)

1. LLM never does arithmetic — calc computes. Uncomputable → escalate,
   never guess. Cite-or-reject on digest/memo/brief variants.
2. Repos stay whole; HTTP-only integration. Client variation lives in
   DATA + .env. Spine is never entitlement-gated (rule 9).
3. `.env` holds secrets — never print/commit them. Local python:
   `env -u PYTHONPATH calc/.venv/bin/python …`.
4. After backend edits re-run the touched gates; frontend: `npm run
   build`. Data story changed? Re-run EVERY gate (#29/#30).
5. Append a dated entry to `docs/spike-log.md` per task with raw
   results; keep the latest HANDOFF §5 current. One in_progress todo.
6. New traps get numbers (#52+).

## Start here

1. `git status` + skim the tail of `docs/spike-log.md` (session #17)
   to confirm state matches above.
2. Health: `curl localhost:8100/health localhost:8101/health
   localhost:8102/health` — keepalive revives dead uvicorns within 30s;
   containers per `runbooks/cold-start.md` if down.
3. Then bucket 1 (Leonard's visual pass), bucket 3 with whatever human
   input exists today.
