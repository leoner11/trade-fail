# Architecture Report — MJCX Trade Agent Appliance

**Date:** 2026-09-08 · **Method:** 4 parallel role audits (backend, agent layer, frontend, security/infra) + doc-vs-code verification
**Sources verified:** `docs/ARCHITECTURE.md` (v1.2), `HANDOFF.md`, compose stamp, all first-party code (`glue/`, `spine/`, `calc/`, `console/`, `dify/`), tests, runbooks.
**Every claim below is grounded in file:symbol evidence. Nothing was taken from the docs on faith.**

---

## 1. Verdict (TL;DR)

The codebase **matches its own documentation to an unusual degree**. All headline claims — calc as sole money authority, spine as single source of truth, deterministic guards around LLM output, the 5-hop S2 rules save pipeline, headless postiz, v1↔v2 conversation-core switch — are real, implemented, and citable.

The real risk is **not architectural, it's the trust model**: spine, calc, and the buyer webhook are intentionally zero-auth, and that decision is fine on a single-tenant LAN appliance but becomes the pivot path the moment any port leaves loopback (evo's `:8080` already does). Five high-severity findings, all fixable in <1 day of work, none requiring architecture change.

---

## 2. What This System Is

A **WhatsApp-native AI sales agent appliance** for foreign-trade SMEs, deployed **one stack per client**. The buyer chats on WhatsApp; an agent pipeline triages, answers catalog questions from a grounded KB, computes prices deterministically, sends formal PDF quotes, escalates to humans with rules, nudges on SLA breaches and stale quotes, drafts social posts, and reports KPIs to the boss — with staff oversight through a token-gated web console.

```
buyer ⇄ WhatsApp ⇄ evo :8080 ──webhook──► glue :8102 ──► dify :8180 (triage / spec-RAG)
                                            │  ▲            ──► GLM direct (parse/compose)
                       sendText/sendMedia ◄──┘  └──────────► calc :8100 (quotes ONLY)
                                             │
                    transcripts/escalations/tiers/quotes/posts/events
                                             ▼
                                          spine :8101 (SQLite = S1 S3 S4 S5 S6 S8)
                                             ▲
            console :5173 dev / :8090 stamp ─┘  (bearer CONSOLE_TOKEN)
```

- **First-party IP (the code we own):** `calc`, `spine`, `glue`, `console` + dify prompts/DSL + n8n workflow JSONs.
- **Replaceable OSS organs (HTTP-only, repos unmodified):** evo (WhatsApp), chatwoot (installed, OFF since v1.2), carbone (PDF), postiz (social, headless), n8n (clock), dify (LLM workflows, external repo), GLM (LLM).
- **Client variation lives in DATA + `.env`, never code forks** — verified: rules are `spine/rules/*.json`, catalog is DB rows, KB is dify datasets.

**Sizing:** glue ~4.4k LOC (3,435 in the v1 cascade alone) · spine_api 927 · calc engine 435 · console ~5.8k TS/CSS across 30 files · dify console_api 233 · test gates ~1.4k LOC.

---

## 3. The Message Pipeline (heart of the system)

### 3.1 v1 deterministic cascade — `glue/mock_responder.py:2873 route()`

| Stage | What happens | Where |
|---|---|---|
| 0 | `CONVERSATION_CORE=v2` → delegate to `agent.handle()` (v2 is **live in `.env`**; v1 frozen as 30s rollback) | `mock_responder.py:2877` |
| 1 | **Noise gate**: ≥4 chars with <50% alphabetic → polite silence, no LLM ever | `mock_responder.py:2882` |
| 2 | **Thread state**: pending offer + buyer quantity/agreement → synthesize canonical inquiry, force `PRICE_Q` / fulfill offer | `mock_responder.py:2893` |
| 3 | **Triage**: dify `a3_triage` workflow (local GLM fallback); conf < 0.7 or unknown intent → human; `SPAM` → silent drop | `mock_responder.py:2914` |
| 4 | **Agreement fulfillment**: "yes please"/"好的" closes the loop — facts or background PDF delivery | `mock_responder.py:2939` |
| 5 | **Deterministic overrides**: capability answers from S1, exact-SKU/alias `SPEC_Q` resolution, grounded "not our line" pivots, RAG stall-signature repair | `mock_responder.py:3013` |
| 6 | **B-path pricing**: autonomy gate → GLM parses (closed vocab from S2) → hidden-material filter → calc `/quote` → S5 save → inline reply with `numbers="exact"`; formal ask → background carbone PDF (B4) | `mock_responder.py:3153` |
| 7 | **Escalation + mirror**: S4 conversation armed w/ tag + system note, S8 event; every line mirrored to spine *before* routing | `_mirror` |

### 3.2 v2 stateful agent loop — `glue/agent.py:handle`

- **Pre-guards (no LLM):** noise, keyword complaint filter, spam filter, offer fulfillment.
- **Memory:** last-20 turns from spine S4 + `conversations.agent_state` JSON column → **restart-proof** (v1's `_THREAD` dict dies with the process).
- **Loop:** `CONVERSATION_MODEL` (glm-4.5-air, temp 0.3) with exactly 5 tools — `catalog_lookup`, `list_models`, `kb_search`, `price_quote`, `escalate` — capped at `MAX_TOOL_ROUNDS = 4`.
- **Post-guards:** digit-subset guard (compose: reply numerals ⊆ tool facts ∪ buyer msg ∪ thread), digit-exact guard (quotes: `==`), link guard `_LINKY` (URLs/attachments/附件 blocked), banned-opening regeneration; one repair round; deterministic fallback (raw tool cards, never an ungrounded sign-off).

**Assessment:** the guard design is the strongest part of this codebase. "LLM never does arithmetic" and "never guess" are not slogans — they're regex-enforced pre/post-conditions on every generative path.

---

## 4. Data Layer — spine (:8101)

SQLite at `/data/spine.db` (container) / `spine/spine.db` (dev) — `spine/spine_api.py:18`.

| Store | Table | Key invariants (verified) |
|---|---|---|
| S1 catalog | `catalog` (`init_db.py:15`) | SKU PK, specs JSON, CSV import with gap report |
| S3 identity | `customers` (`init_db.py:27`) | `wa_jid` UNIQUE; tier only via staff PATCH (writes `tier_change` S8 event) |
| S4 conversations | `conversations`, `messages` (`init_db.py:73`) | human outbound clears `escalation_tag` (`spine_api.py:649`); `agent_state_json` (PRAGMA-migrated) |
| S5 quotes | `quotes` (`init_db.py:39`) | draft→sent→… lifecycle; `pdf_path` from B4 |
| S6 social | `social_posts` (`init_db.py:60`) | status pipeline pending→…→posted; `postiz_id` pointer |
| S8 audit | `events` (`init_db.py:52`) | append-only; escalations, SLA beacons, gates, tier changes |

**23 routes** total (`spine_api.py`), incl. `/resolve` (identity on every message), `/conversations/*` (threads, escalate, sla_beacon, agent_state), `/reports/x5` (boss analytics), `/health`.

---

## 5. Money Layer — calc (:8100)

- **DSL (S2, schema v3):** `material_base_prices`, `size_coefficients` (coef `0` = manual-quote escape hatch), `process_fees`, strictly increasing `quantity_discounts`, `customer_tiers`, `authority.max_discount_pct`, `price_visibility` — `calc/calculator.py:80-192`.
- **Formula** (`calculator.py:228-282`): `unit = (base × size_coef + Σprocess_fees) × tier_factor`; `total = round(Σ(unit×qty) × (1 − qty_discount), 2)`.
- **Gaps raise `NotComputable`** (`calculator.py:34`) → `{"status": "ESCALATE", "gaps": [...]}` — uncomputable never becomes a guess.
- Endpoints: `/quote` (mutex-locked), `/rules/validate`, `/rules/reload` (auto-rollback to `.bak`), `/health` (`calculator.py:355-424`).

**The S2 save pipeline — all 5 hops verified in code:**
1. console `POST /glue/console/pricing/rules` (`console/src/api/glue.ts:153`) →
2. calc `/rules/validate` (`mock_responder.py:2516`) →
3. glue writes `<rules>.bak` + overwrite (`mock_responder.py:2524-2533`) →
4. calc `/rules/reload`, rollback on failure on both sides (`calculator.py:393-404`, `mock_responder.py:2541-2549`) →
5. glue `_refresh_rules_vocab()` hot-swaps B1 closed vocab + `AUTONOMY` in memory (`mock_responder.py:2551`).

---

## 6. Brain-Stem — glue (:8102) + dify assets

**Surfaces:** `POST /webhook/evo` (WhatsApp intake, dedupe, staff APPROVE/REJECT interception, `route()` in `asyncio.to_thread`) · `POST /email/poll` (IMAP UNSEEN → same `route()` → SMTP reply, `\Seen` flagged only on success) · `/a6/sla_tick`, `/b6/tick` (n8n clocks) · `/x5/send` (boss WA report, zero LLM arithmetic) · `/console/*` proxies (bearer-gated) covering WA session/QR, KB ingest, pricing, gates, social, thread takeover.

**dify assets:** `a3_triage.yml` (classify → Python `parse_route` enforcing conf<0.7→human) · `spec_answer.yml` (RAG top_k=4 → `[[KB_NOT_FOUND]]` structured miss marker — trap #34 closed as claimed) · `agent_core_v2.md` (11-rule tool contract) · `voice_guide.md` (config-as-code voice) · OpenAPI tool specs for spine + calc.

---

## 7. Console — React 19 / Vite 8 / TS / Tailwind / Caddy

- **Auth:** single shared `CONSOLE_TOKEN` in localStorage, `Authorization: Bearer` on every call (`api/client.ts:apiFetch`). No RBAC — acceptable for a single-tenant ops console, noted in security section.
- **Strict organ decoupling verified:** browser speaks ONLY to relative `/spine/*` and `/glue/*`; evo/dify/postiz never reachable from the client; no organ credential ships to the browser.
- **State:** no Redux — `useAsync` (one-shot) + `usePoll` (5s threads, 3s QR stream, 8s KB index, 30s escalation badges).
- **15 pages:** runtime (Home KPIs, Threads takeover, Quotes + B6 approve/dismiss, Customers tier editor, Social queue + headless channels, OAuth callback, Events audit, Reports X5) + setup (Connect QR, Catalog CSV, Knowledge + O2 quiz, Pricing editor + autonomy dial + O3 backtest, Voice samples, GoLive gates).
- **Stamp:** multi-stage node:22→caddy:2 (`console/Dockerfile`); Caddy proxies `/spine/*`, `/glue/*` (handle_path strip), `/uploads/*` (postiz avatars), SPA fallback; dual topology via `SPINE_UPSTREAM`/`GLUE_UPSTREAM` env (host uvicorns ↔ compose DNS).

---

## 8. Design Principles — verified

| Rule | Status | Evidence |
|---|---|---|
| 1. LLM never does arithmetic | ✅ enforced | calc is sole compute; digit guards reject invented/dropped numbers |
| 2. Uncomputable → escalate with gaps | ✅ | `NotComputable` → `ESCALATE` payload; stall-signature repair else real escalation |
| 3. Always-human list sacred | ✅ | hardcoded; conf<0.7 → human; autonomy dial never touches it |
| 4. OSS repos stay whole, HTTP-only | ✅* | only postiz dist patches (`compose/postiz-patches/*.js`) bend this — documented, mount-based, version-locked |
| 5. Client variation = DATA + .env | ✅ | S1/S2/S3/S6 + env; zero client-specific code paths found |
| 6. Config-as-code in git | ✅ | dify DSL/prompts, n8n JSONs, compose, rules all tracked |
| 7. Secrets in .env only | ⚠️ | `.env` gitignored (good) — but see §10 defaults |

---

## 9. Verification Gates (as shipped)

`calc/test_calculator.py` (22 unit) · `tests/e2e_spike.py` (13, money path) · `tests/test_classify.py` (eval) · voice gate (8) · `test_b4.py` (12, PDF-in-thread) · `test_o2_quiz.py` (20/20, 0 fabrications) · `test_o3_backtest.py` (example mode — **real pricing data is THE go-live blocker**) · `test_o5_acceptance.py` (22/22 on both cores) · `test_o5_s9_social.py` · `test_email_channel.py` (12) · `test_o5_s10_qr_drill.py` · console `npm run build` + lint. Gates pin `standard` autonomy. ~1.4k LOC of plain-script gates, run after every organ edit per HANDOFF.

---

## 10. Security Posture (dedicated audit)

**Context that matters:** this is a deliberately open, single-tenant LAN appliance. Several findings are *accepted risks per docs* (`spike-log.md` threat model). They become urgent the instant the box leaves the LAN or any port is forwarded.

### High

| # | Finding | Evidence |
|---|---|---|
| H1 | **evo management API on 0.0.0.0 with repo-published default key** — only service not bound to 127.0.0.1; key defaults to `mjcx-spike-key` (also shipped in `.env.example:12`). Anyone on the LAN can read/send WhatsApp, fetch QR, drop sessions. | `compose:86,89` |
| H2 | **Unauthenticated buyer webhook + tick endpoints; approvals authorize on forgeable JID.** `/webhook/evo`, `/b6/tick`, `/a6/sla_tick`, `/email/poll`, `/x5/send` take any POST; `APPROVE` compares against attacker-supplied `remoteJid` → spoofed STAFF JID approves drafts. Docs admit: hardening design-only. | `mock_responder.py:3354-3397`, `ARCHITECTURE.md:126` |
| H3 | **spine has zero auth on all 23 routes** (customer PII, full transcripts, quotes). Loopback-published in the stamp, but reachable from every container on the flat net; the documented dev topology binds it 0.0.0.0 (`scripts/dev_keepalive.sh:10-12`). | `spine_api.py` (no middleware/Depends anywhere) |
| H4 | **Console auth fails OPEN when `CONSOLE_TOKEN` empty** (the `.env.example` default): `if CONSOLE_TOKEN and path.startswith("/console")` — an out-of-box boot exposes `/console/wa/logout`, `/console/pricing/rules` (server-side file write), thread takeover-as-staff. When set: bearer in localStorage over plain-HTTP Caddy `:80`. | `mock_responder.py:620-631`, `.env.example:33`, `Caddyfile` |
| H5 | **Functional placeholder secrets everywhere**: `SECRET_KEY_BASE`/`JWT_SECRET` fall back to literal `replace_with_...` strings (Rails sessions / postiz JWTs forgeable if unset); `postiz-redis` runs with **no password at all**. Placeholders boot successfully, so nothing forces rotation. | `compose:129,192,176-180` |

### Medium

- **M1 — Chained arbitrary file read:** spine `/posts/{pid}/images` stores any path string unvalidated (`spine_api.py:398-411`) → glue preview reads it verbatim (`mock_responder.py:1991-2002`). With H3+H4 an attacker plants `/proc/self/environ` and reads GLM/EVO keys back.
- **M2 — Supply chain:** 5 images on mutable `:latest` (evo, chatwoot ×2, carbone-ee, n8n, redis:alpine), no digest pins; postiz pinned v2.11.2 but two compiled vendor files silently overridden by read-only mounts — patches match exactly one upstream version.
- **M3 — Flat network:** all 14 services share one bridge; internet-adjacent organs (evo, postiz, n8n, chatwoot) sit beside unauth spine/calc/postgres/redis. `SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true` disables chatwoot's SSRF guard; console+n8n get `host-gateway` pivot.
- **M4 — n8n:** `N8N_SECURE_COOKIE=false`, unpinned `:latest`, open first-visit owner signup, workflow code-exec + host-gateway access → code-exec foothold if ever reachable.

### Low / Info

- OAuth relay `/console/social/finish/*` exempt from bearer guard (by design; mitigated by postiz single-use 5-min `state`).
- Webhook dedupe is an in-process set cleared wholesale every 5000 msgs — replay window (fix alongside H2).

### Hardening order (cheap → structural, no architecture change)

1. `127.0.0.1:8080:8080` for evo + make `EVO_API_KEY` mandatory (kill the `:-` fallback).
2. Shared-secret/HMAC on `/webhook/evo` + tick endpoints (kills H2 + the replay window).
3. Refuse to serve `/console/*` when `CONSOLE_TOKEN` empty (fail closed); TLS on Caddy.
4. Fail-closed generation of `SECRET_KEY_BASE`/`JWT_SECRET` at first boot; password postiz-redis.
5. Static shared token on spine+calc (dify tools can carry it); stop binding dev uvicorns to 0.0.0.0.
6. Digest-pin images; prefix-whitelist social image paths (kills M1); split channels/core networks.

---

## 11. Doc-vs-Code Discrepancies & Tech Debt

| # | Finding | Impact |
|---|---|---|
| D1 | **`glue/Dockerfile:4` copies only `mock_responder.py`** — omits `glue/agent.py` + `dify/prompts/agent_core_v2.md`. A containerized glue with `CONVERSATION_CORE=v2` crashes on `import agent`. v2 currently runs on host uvicorns, so it's latent — but it silently breaks the O1 stamp story. | **Fix before any containerized deploy** |
| D2 | `dify/dsl/spec_answer.yml:81` hardcodes a dify dataset ID; `knowledge_ingest.py` recreation mints a new one requiring manual DSL patch via `console_api.py`. Fragile for per-client onboarding (the appliance's core loop). | Onboarding friction |
| D3 | `spine/init_db.py` schema lags runtime: `conversations.agent_state_json` + `social_posts.images_json` exist only via PRAGMA migrations (`spine_api.py:350,542`). Fresh DBs work, but schema truth is split across two files. | Maintainability |
| D4 | `RULES_PATH` defaults disagree 3 ways: calc Dockerfile `pricing_rules.json`, `calc/app.py` `…example.json`, keepalive `…generators.json`. Works by keepalive precedence; a trap for the next operator. | Trap-class |
| D5 | Dead code: `calc/render_quote.js` + `calc/package*.json` (superseded by carbone-ee in glue, trap #1), `console/.../ComingPanel.tsx` (never imported), ~120 lines of chatwoot `/console/inbox/*` proxies duplicating `/console/threads/*` (documented rollback path — keep until chatwoot teardown decision). | Cleanup |
| D6 | Stale copy: `GoLivePage.tsx:14` still says "chatwoot escalation inbox"; `glue.ts:inboxConversations` unused. v1.2 killed chatwoot. | Copy rot |
| D7 | Vite dev proxy lacks `/uploads/*` (Caddyfile has it) → broken channel avatars at `:5173` dev. | Dev DX |
| D8 | `console-plan.md` declared in-browser approvals a non-goal; `QuotesPage` B6 approve/dismiss shipped anyway (an improvement — update the plan doc). | Doc rot |
| R1 | SQLite connections per-request without `PRAGMA journal_mode=WAL` → `database is locked` risk under concurrent webhook + console polling load. | Stability at scale |
| R2 | `classify()`/`spec_answer()` use blocking `urllib` with 90s timeouts inside `asyncio.to_thread` — threadpool saturation under spikes. | Stability |
| R3 | `_LOCAL_TURNS.clear()` wipes ALL offline gate thread memory at 2000 entries (`agent.py:183`). | Test-only path, minor |
| R4 | Background console tabs poll unchanged (no `document.hidden` check) → redundant traffic. | Minor |
| R5 | calc's reload reads the rules file under its own lock, but glue's write is outside that lock — a torn read is possible mid-save (validated+`.bak` flow makes this unlikely, not impossible). | Edge case |

---

## 12. Bottom Line

- **Architecture: sound and unusually self-consistent.** Deterministic spine + deterministic calc with an LLM squeezed between guards is the right shape for a money-touching sales agent, and the code enforces what the docs preach.
- **Ship-blockers before any client deployment:** D1 (containerized v2), the O3 real-pricing gate (already tracked), and hardening items 1–3 from §10 — roughly one focused day.
- **Watch item:** the v1 cascade is 3,435 lines of frozen rollback. After a clean v2 soak week, deleting it (per HANDOFF §5.1) removes the single largest maintenance surface in the repo.

*Report generated 2026-09-08 from four parallel role audits; raw findings preserved in agent transcripts (BackendScout, AgentLayerScout, FrontendScout, SecAuditor).*
