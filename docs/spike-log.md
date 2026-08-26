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

### 2026-08-24 — A3-1 classifier eval executed: PASS

`tests/test_classify.py` (Claude's harness, had never been run) executed
against `glm-4-flash`: **14/14 intent, 14/14 language, 14/14 parseable JSON**
— clears the O2-2 bar (≥90% intent + 100% JSON) with zero prompt edits.
Both override rules held (price+custom→CUSTOM_ODM, anger→COMPLAINT);
urgency/sentiment secondary fields also correct. Full raw outputs:
`docs/eval-a3-classifier.md`. The prompt is cleared for wiring into dify.

### 2026-08-24 — Task 2 done: Phase A skeleton wired live (evo → glue → spine/calc)

**State on arrival:** colima up; `evo` + `evo-postgres` had died with Mac
sleep (expected) — `docker start evo evo-postgres` revived both. The
WhatsApp instance survived as **`mjcx-test`** (NOT a new "spike" instance):
state `open`, session intact, no QR re-scan needed. Reuse it.

**New: `glue/mock_responder.py`** (:8102, FastAPI, stdlib-urllib only — venv
has no httpx) — the mock-dify router from handoff Task 2.5:
- A1 idempotency by message id (in-memory set); skips fromMe/groups/status.
- A2 identity via spine `/resolve` (S3) — verified: seeded JID
  `6281234567890@…` resolves known/cus_repeat_001/tier=repeat.
- A3 classify via GLM using the eval-passed prompt verbatim.
- A3-2 routes verified locally (synthetic webhook payloads, DRY_RUN):
  SPAM→silence · GREETING→canned · SPEC_Q+SKU→grounded S1 read from
  spine /catalog (deterministic; dify RAG replaces later) · PRICE_Q→B1 parse
  (closed S2 vocab) → calc /quote → inline price + S5 save(status=sent)
  · calc ESCALATE (XL size)→human-quote reply w/ gaps · CUSTOM_ODM/
  COMPLAINT→escalation holding reply.
- Math spot-check: Metal Casting M ×100 +foil, repeat tier: 185×0.95×100×0.85
  = USD 14,938.75 — matches unit math. Margin never leaves calc's response
  into buyer text (X4).
- B1 parser initially quoted qty=1 for a qty-less ask; fixed with a hard
  "NEVER assume a quantity" rule → now sends ONE clarify question (flowchart
  B1-1).

**Wiring:** webhook registered on mjcx-test → `http://host.docker.internal:8102/webhook/evo`
(events: MESSAGES_UPSERT). Container→host reachability confirmed by node
probe inside the evo container (200 on glue /health). Outbound proven: REST
sendText to Leonard's own JID queued OK ("message yourself" smoke test).
calc :8100 + spine :8101 restarted via calc/.venv uvicorn (`--app-dir`
discipline: spine needs `--app-dir spine`, calc `--app-dir calc`).

**Remaining for live loop:** one real inbound message from a second phone
(Leonard, 1 min). Everything else is armed.

`tests/test_classify.py` (Claude's harness, had never been run) executed
against `glm-4-flash`: **14/14 intent, 14/14 language, 14/14 parseable JSON**
— clears the O2-2 bar (≥90% intent + 100% JSON) with zero prompt edits.
Both override rules held (price+custom→CUSTOM_ODM, anger→COMPLAINT);
urgency/sentiment secondary fields also correct. Full raw outputs:
`docs/eval-a3-classifier.md`. The prompt is cleared for wiring into dify.

### 2026-08-24 — Task 3 done: dify is live and IS the brain now

**Stack up** (`pull_all_repo_here/glue/dify/docker`, v1.16.1, 15 containers,
nginx on **:8180** — .env was already staged there; colima bumped to
8GB RAM / 45GB disk first, evo revived after). Admin created via console
API; creds + service key in appliance `.env` (gitignored):
`DIFY_ADMIN_*`, `DIFY_A3_API_KEY` (app-…), `DIFY_BASE_URL`.

**Console-API traps (1.16):**
- Login wants the password **base64-encoded**, returns `{"result":"success"}`
  with NO token body — auth is cookie-based (access_token + csrf_token).
- Mutating calls need header **`X-CSRF-Token`** (hyphen), not X-CSRFToken.
- Model providers are **plugins**: installed `langgenius/zhipuai`
  (0.0.33) via marketplace API. Its credential validator defaults to a paid
  model (error 1113) — pass `"validate_model":"glm-4-flash"` in credentials.
- App import: POST `/console/api/apps/imports` {"mode":"yaml-content",...}.
- Custom tools: POST `/console/api/workspaces/current/tool-provider/api/add`,
  `credentials:{"auth_type":"none"}` required.

**A3 workflow as config-as-code:** `dify/dsl/a3_triage.yml` (imported clean,
app_id 307d9d7e…). Start(query) → LLM glm-4-flash classify (same eval-passed
prompt) → **code node applies override rules + closed-enum guard +
confidence<0.7→human** (routing logic is OUR code, not LLM discretion) → End.
Published; runs green via `/v1/workflows/run`. Parity spot-checks through
dify: COMPLAINT→escalate_complaint · zh PRICE_Q→price · SPAM→silence ·
GREETING→greet · price+custom→escalate_custom. 5/5.

**calc+spine registered as dify custom tools:** OpenAPI schemas in git at
`dify/tools/calc.openapi.yml` + `spine.openapi.yml`; providers "MJCX calc
pricing" / "MJCX spine data" (compute_quote, resolve_identity,
catalog_by_sku, catalog_search, save_quote, set_quote_status). dify api
container reaches both over host.docker.internal (:8100/:8101 → 200).

**Glue swapped to dify brain:** `mock_responder.classify()` calls the dify
workflow first (`USE_DIFY=1`, key in .env); direct-GLM is the fallback
(graceful dumb mode). Verified live path [a3] route=price / route=human from
dify outputs. Also hardened: sendText failures no longer 500 the webhook.

**Running now:** evo :8080 · calc :8100 · spine :8101 · glue :8102 · dify
:8180 (15 containers). Still pending: real-phone inbound test (Leonard),
chatwoot wiring, B-path inside dify workflow (parse+calc as tool nodes).

### 2026-08-24 — LIVE on Leonard's phone: Phase A loop closed end-to-end

Real inbound WhatsApp traffic from Leonard's second number
(6287887982344@…): evo webhook → glue → spine identity (new customer
auto-created, then recognized known) → **dify** classify → route → reply
delivered in-thread. Verified live:
- "testtt" → OTHER → human holding reply; S3 row created.
- "so what do u do" → PRICE_Q → B1 clarify… but parser INVENTED a product
  (Gold Foil/Wood + engraving). Leonard pushed back ("wtf") → COMPLAINT
  urgent → escalate ✓. Lesson: vague asks must clarify, not guess. Fixed:
  PARSE_PROMPT now forbids picking a closest-match material when none was
  named — retested, action=clarify. This is exactly O5-1-style acceptance
  catching a real defect before a client ever sees it.
- Anger → COMPLAINT escalation held on real traffic, not just eval cases.

**New trap:** evo died of Node heap OOM (~2GB) shortly after dify's 15
containers came up — messages sent while it was down are silently lost.
`docker update --restart unless-stopped evo evo-postgres` applied so it
self-heals; watch memory when dify+evo coexist on colima.

### 2026-08-24 — Voice guide + bilingual replies wired

- `dify/prompts/voice_guide.md` created (O4-2): tone rules + language
  register (en/zh/id) + empty samples section for the client's 5–10 real
  comms during onboarding. This file becomes the dify reply-prompt source
  once dify owns generation; glue templates follow it meanwhile.
- `glue/mock_responder.py`: all buyer-facing strings moved to TEMPLATES
  {en, zh} keyed by classifier language (fallback en); PARSE_PROMPT now
  emits clarify questions in the buyer's language. Verified live-path:
  zh greeting/complaint/quote all reply in Chinese; en unchanged.
  zh quote math checked: Crystal M +3D laser ×100 repeat = 13,300×0.85
  = USD 11,305 ✓ (Q-E494F4).
- Data mismatch surfaced (expected, example data): seeded S1 catalog is
  diesel gensets but example S2 rules are trophy/award materials, so
  "DG-50 价格?" correctly does NOT get a guessed price — it clarifies/
  escalates per rule #2 of the appliance. Real onboarding ingests aligned
  S1+S2 (flowchart O2/O3) so this disappears.

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

---

## Session 2026-08-24 (ox alpha #2) — THANKS fix + RAG live

### Real-chat defect caught & fixed: "谢谢" got a sales pitch

Leonard tested on the real thread: `好吧，谢谢` / `好谢谢` were classified
GREETING and answered with the canned intro pitch ("Hello! I'm the sales
assistant…") — rigid and wrong after a close. Root cause: closed enum had
no acknowledgment class.

**Fix (config-as-code, all four layers):**
- `dify/prompts/a3_classify.md`: new `THANKS` intent (thanks/ack/goodbye,
  no request), GREETING redefined as opening-only, zh+en examples added.
- dify workflow code node: ENUM + ROUTE gained `THANKS -> welcome`.
  Draft patched via API, republished, exported DSL back over
  `dify/dsl/a3_triage.yml`.
- eval harness grew to **17 cases** (`tests/test_classify.py`): thanks in
  en/zh/id. Result **17/17 intent, 17/17 lang, 17/17 JSON** — PASS.
- glue: `THANKS→welcome` in ROUTE_MAP + welcome templates (en/zh) + a real
  branch in `route()` (first run exposed that a mapped route with no
  template branch still fell through to the human reply).

Live-path verified through dify AND glue-in-process: zh/en/id thanks now
get "不客气/You're welcome", greeting unchanged, price path unchanged.

### RAG is live: dify Knowledge + A3-Spec workflow

- **Docs home:** `data/{client}/knowledge/` in-repo = source of truth;
  seeded example from spine S1 catalog (5 product sheets + company FAQ,
  facts only from S1). Client variation stays DATA (rule #5).
- **Ingest:** `glue/knowledge_ingest.py` (stdlib) — ensures dataset, uploads
  md/txt via create-by-text, waits for indexing, prints dataset_id.
  `--replace` re-uploads. Dataset `mjcx-knowledge`, 6 docs indexed.
- **Brain:** new dify workflow app **A3-Spec Answer**
  (`dify/dsl/spec_answer.yml`, app f8f1→deleted, final 4eea0176…):
  Start(query) → knowledge-retrieval (top_k 4) → glm-4-flash grounded
  answer (answer ONLY from context, never prices, mirror buyer language,
  deflect when unsure) → End(answer). Published; key in .env
  `DIFY_SPEC_API_KEY`. Verified: en/zh spec Qs answered correctly from
  docs; an Indonesian PRICE_Q was correctly deflected to quotation flow.
- **Glue wiring:** SPEC_Q keeps the deterministic spine SKU read first
  (fast/exact); without a SKU it calls A3-Spec; stub only if dify is down.
  Verified live-path: ISO9001 question and "tank size of your 50kVA"
  (no SKU in text) answered from the knowledge base.

**New traps:**
9. **GLM embeddings are paid** — dataset creation with high_quality +
   zhipuai embedding-2/3 fails indexing with error 1113 (余额不足), same
   trap as glm-4.7/4.6 chat. Current dataset uses dify **economy** (keyword)
   indexing — fine at this doc count. After Leonard tops up:
   delete dataset, re-run ingest with `KNOWLEDGE_INDEXING=high_quality`,
   update dataset_id in spec_answer.yml, re-import.
10. **dify 1.16 console draft save is POST, not PUT**, and the body must
    carry the current draft `hash` or you get 409 draft_workflow_not_sync.
    Encoded in `dify/console_api.py` (login/base64/CSRF/hash dance).
11. DSL import validation rejects `reranking_mode: null` /
    `score_threshold: null` inside knowledge-retrieval nodes — omit the
    keys entirely.
12. dify service-API workflow errors surface as HTTP 400 invalid_param with
    a pydantic message naming the offending node — read the body before
    assuming the workflow logic is wrong.

**Known gap:** templates exist for en/zh only; id-classified messages fall
back to en (voice_guide lists id as onboarding register). Add `id` dict to
glue TEMPLATES during Ducotti onboarding.

**New tooling:** `dify/console_api.py` — scripted login/apps/get-draft/
put-draft/publish/export/import/patch-node/dataset-key/app-key. All future
dify edits go through this (config-as-code), not the browser.

---

## Session 2026-08-24 (ox alpha #3) — voice generation live, air everywhere

### glm-4.7 still blocked

Despite Leonard's top-up, `glm-4.7` / `glm-4.6` on the `.env` key return
`429 {"code":"1113","message":"余额不足或无可用资源包"}` — flash and
**glm-4.5-air** work. Leonard will check the Zhipu console; until then
`GLM_MODEL=glm-4.5-air` is the default brain (passes every gate below).
Embeddings remain paid-blocked → RAG stays on economy indexing.

### Replies are now GENERATED, not canned ("too chatbotty" fix)

Every buyer-facing reply used to come from fixed strings in glue
`TEMPLATES`. Now `compose()` in `glue/mock_responder.py` generates the
wording from `dify/prompts/voice_guide.md` (extended with a
reply-generation contract) + injected FACTS, with the templates kept only
as failure fallback:

- **Facts are the ceiling.** calc/spine numbers are passed verbatim;
  guards reject output whose digit-set ≠ fact digit-set
  (`numbers=exact` for quotes: every fact number must survive;
  `subset` elsewhere: invention blocked, omission allowed).
- **No fabricated links/files** — `_LINKY` guard rejects `[x](y)`,
  http, .pdf/.docx, "attachment", 附件… (glm-4-flash zh fabricated
  PDF links on ~every quote attempt — see trap 13).
- **Quote CTA is deterministic**: body generated, then glue appends
  fixed `pdf_offer` line. Models could not resist inventing documents.
- **Variation**: temperature 0.7 + previous-reply memory per JID
  (`_last_reply`) so consecutive messages don't repeat openings.
- **id register** works through generation (no template needed);
  en/zh/id all verified.

New gate: `tests/test_voice.py` — 6 situations ×2 generations, checks
guard-pass + opening variation; wording itself judged by Leonard.
Result with air: **6/6 PASS**, natural varied replies, digits exact.

### Model switched to glm-4.5-air across ALL layers (eval-gated)

- `tests/test_classify.py MODEL=glm-4.5-air`: **17/17 intent,
  17/17 lang, 17/17 JSON — PASS**.
- dify A3-1 Triage + A3-Spec Answer LLM nodes patched flash→air via
  console API; both DSLs re-exported to `dify/dsl/`.
- Live parity through dify: zh price→price ✓ anger→escalate_complaint ✓
  thanks→welcome ✓ spec grounding (120L tank, 70dB@7m) ✓ no think-leaks.

### New traps

13. **glm-4-flash zh cannot resist fabricating PDF links** when asked to
    deliver a price — `[下载PDF报价单](#)`, "附件：…" etc., regardless of
    negative instructions. Guard rejects them (correct); solution was
    structural: CTA moved out of the model into a deterministic append.
14. **Reasoning models (glm-4.5-air/4.7) prepend `<think>…</think>`**:
    - its braces poison the classifier's greedy `\{.*\}` JSON match →
      parse_ok=false storms; strip think-blocks BEFORE extracting JSON
      (fixed inside dify parse_route code node), and
    - raw thinking LEAKS INTO ANSWERS if an LLM node feeds End directly
      (A3-Spec did). Added a `sanitize` code node between llm_answer and
      end; any future reasoning-model LLM node needs the same treatment.
15. **calc crashes at boot without `RULES_PATH`** when started locally
    (default `/data/rules/...` is container-only). Fixed in
    `runbooks/cold-start.md`.

### State

Running: evo :8080 · calc :8100 · spine :8101 · glue :8102 · dify :8180.
Pending: Leonard's live-phone voice pass (greet×2 / thanks zh / spec /
price zh / complaint), then chatwoot (A6).

---

## 2026-08-24 (later) — A6 done: chatwoot human inbox + escalation loop

Leonard passed the live voice test; the one dead-end found was escalations
("I'll check with our team…" then nothing — no follow-up mechanism exists
by design until A6). A6 closes exactly that: escalated threads now land in
a human inbox, and a human reply goes back out over WhatsApp.

### What's running

chatwoot community via its own production compose (rails :3000 · sidekiq ·
pgvector pg16 · redis) — boot recipe in `runbooks/cold-start.md`, topology
in `compose/chatwoot.override.yaml` (product repo; repos stay whole).
Secrets in the clone's untracked `channels/chatwoot/.env`; product `.env`
gained CHATWOOT_URL / ACCOUNT_ID / INBOX_NAME / ADMIN_* / API_TOKEN.

### Wiring

- **evo global switch**: recreated evo with `-e CHATWOOT_ENABLED=true`
  (session survived). Per-instance config via `POST /chatwoot/set/mjcx-test`
  → url http://chatwoot:3000, bridge token, signMsg, inbox name mjcx-test.
  Every incoming WhatsApp message is mirrored into the matching chatwoot
  conversation from now on (S4 conversation store).
- **Inbox**: Channel::Api named `mjcx-test` (id 1), webhook_url
  `http://evo:8080/chatwoot/webhook/mjcx-test` — container-reachable, NOT
  the localhost default evo would have registered.
- **glue escalation hook** (`escalate_to_chatwoot`): fires on COMPLAINT /
  CUSTOM_ODM / SHIPPING / OTHER low-confidence / PRICE_GAPS (B5) /
  CALC_DOWN and on SPEC_Q knowledge-base misses (A4's never-guess path —
  KB misses now become LOW-confidence escalations instead of dead-end
  deflects). Package per flowchart A6-1: contact by JID identifier, open
  conversation (source_id=JID so evo mirrors attach), PRIVATE note with
  buyer text + AI holding reply + intent/lang/tier + reason, label
  (intent, lowercased), S8 event. Best-effort: never breaks the reply path.
- **spine S8 writer**: `POST /events` + `GET /events?kind=` (schema existed
  since the spike; this is its first writer).

### Verified

1. complaint through `route()` → conversation armed, private note +
   label + spine event id=2 ✓
2. public reply posted as staff in that conversation → chatwoot webhook →
   **evo ChatwootService attempted sendText to the JID** (`exists:false`
   only because the test number isn't a real WhatsApp account) ✓

### New traps

16. **Docker DNS collisions on shared networks**: evo-postgres carries the
    network alias `postgres` on evo-net; multi-homed chatwoot containers
    resolved THE WRONG DATABASE round-robin style. Rule: when stacks share
    a network, point them at unique aliases (cw-postgres), never bare
    service names.
17. **chatwoot api-inbox webhooks fire from sidekiq**, not rails — rails
    resolving a hostname is NOT proof sidekiq can reach it ("Could not
    resolve hostname 'evo'" appeared only at delivery time).
18. **SafeFetch blocks private-network webhook targets by default**
    ("has no public ip addresses") → SAFE_FETCH_ALLOW_PRIVATE_NETWORK=true
    for any self-hosted stack whose webhooks stay inside docker networks.

### Deferred (noted, not built)

- SLA beacon (>2h unanswered escalation nudges boss) — needs cron/n8n;
  S8 events are its feed.
- After-hours auto-holding replies; priority field only settable at
  conversation creation in this chatwoot version (label carries urgency).
- Real-number confirmation of the WhatsApp delivery hop (needs Leonard's
  phones — same 2-minute drill as before).

### State

Running: evo :8080 · calc :8100 · spine :8101 · glue :8102 · dify :8180 ·
chatwoot :3000 (+sidekiq/pg/redis containers). Gates re-run after glue/spine
edits: voice 6/6 ✓ classifier 17/17 ✓.
Pending: Leonard's live A6 test — send a complaint/custom ask from phone 2,
watch it land in localhost:3000 with draft+summary, reply there, confirm it
arrives on phone 2.

---

## Session 2026-08-24 (ox alpha #4) — A6 closed + B4 formal-PDF dry-run

Leonard confirmed A6 closed from his side (data verified in chatwoot DB;
he'll skip the chatwoot UI day-to-day — future custom dashboard reads spine
only, per X1 pointer rule). Docs refreshed (HANDOFF §2/§5, README layout).

### B4: formal PDF quote delivered in chat (dry-run grade)

Per Leonard's call: spike template is fine for now; each client gets its own
template via a later custom generator. Scope = prove the plumbing.

**Flow:** buyer explicitly asks for official/formal/PDF quote or PI →
`PARSE_PROMPT` new `"formal"` flag → calc OK → S5 save+sent → **background
thread** `b4_deliver` (inline price text goes out first, PDF follows):
carbone render → soffice pdf (`spine/quotes_pdf/Q-*.pdf`) → S5.pdf_path →
evo `POST /message/sendMedia` `{number, mediatype:"document", mimetype,
fileName, caption, media:<base64>}` (v2.3.7 has NO sendDocument).
Caption digits come from calc verbatim; any failure degrades silently to the
inline-only reply; DRY_RUN blocks real sends.

**spine:** `GET /quotes/{qid}` + `POST /quotes/{qid}/pdf` (sets existing
pdf_path column).

**Gate: `tests/test_b4.py` 12/12 PASS** (3s warm; render→PDF→S5 readback,
send skipped unless SEND_JID set). Voice gate 6/6, classifier 17/17 re-run ✓.

### New traps

19. **carbone-ee v5 API is async and undocumented-in-readme**: template
    upload is `POST /template` (NOT /template/upload), render is
    `POST /render/{templateId}` → {renderId}, fetch via one-shot
    `GET /render/{renderId}` (binary once, then 404 forever). The old sync
    `POST /render` from the v4 era 404s silently.
20. evo v2.3.7 document send = `/message/sendMedia` with `mediatype:
    "document"`; payload field is `media` (base64|url), NOT "document".

### State

Running: everything above + carbone-test :8200.
Pending (Leonard): optional live check — text a formal-quote ask on the real
thread ("please send me an official quotation, 100 pcs crystal trophy M with
3D laser engraving") and confirm the PDF lands in WhatsApp; or run
`SEND_JID=<jid> ... tests/test_b4.py`. Next build item per HANDOFF §5: B6
follow-up loop + SLA beacon via n8n.

---

## Session 2026-08-24 (ox alpha #5) — B6 follow-ups + SLA beacon via n8n

Leonard's call: capacity optimization deferred; ship the scheduler. n8n is
deployed as THE CLOCK ONLY — every bit of logic/approval stays in glue so
ticks are testable with plain curl and n8n remains disposable plumbing
(WEAVE_PLAN role split: n8n=cron/routing ◄──▶ dify=brain).

### Deployed

- **n8n** container on evo-net (:5678, volume `n8n_data`, TZ Asia/Jakarta,
  N8N_SECURE_COOKIE=false). Reaches host uvicorns via colima's
  `host.docker.internal` (172.18.0.1 gateway does NOT work — refused).
- Two workflows as code in **`n8n/workflows/*.json`** (S7), imported via
  `n8n import:workflow` + activated via `n8n update:workflow --active=true`
  (restart required to take effect; verified firing end-to-end).
  - `b6-followup-tick-001`: POST glue `/b6/tick` every 4h
  - `a6-sla-beacon-001`: POST glue `/a6/sla_tick` every 15min

### Logic (all in glue/mock_responder.py)

- **`POST /b6/tick[?hours=N]`** — S5 quotes status=sent older than
  FOLLOWUP_HOURS (48) without a followup_draft event yet → GLM composes a
  gentle buyer-language nudge (same digit/link guards as compose()) → DRAFT
  goes to STAFF_WHATSAPP with "approve by replying APPROVE <qid>" (v1 =
  human approves, flowchart-faithful; auto-send is a v1.1 config flag) →
  S8 event logged → idempotent (re-run drafted 0).
- **`POST /a6/sla_tick[?hours=N]`** — open chatwoot conversations with NO
  message from a HUMAN agent older than SLA_HOURS (2) → beacon BOSS on
  WhatsApp w/ contact + last buyer line → S8 sla_beacon event, once per
  conversation. Criterion note (trap #21): chatwoot sets
  first_reply_created_at on BOT holding replies too — bridge user id must
  be excluded; humans = /agents minus evo-bridge@mjcx.test.
- **spine reads added:** `GET /quotes?status=&older_than_hours=` and
  `GET /customers/{id}` (tick feeds).

### Verified live

- sla_tick(hours=0.1) beaconed both spike conversations → 2 WhatsApp
  messages reached Leonard + 2 S8 events.
- b6_tick drafted 5 stale Aug-19 quotes → drafts arrived on Leonard's
  phone as staff; second run = 0 (idempotent ✓).
- n8n SLA workflow fired 3× during a deliberate 1-minute-cadence test;
  reverted to 15min after proof.

### New traps

21. **chatwoot first_reply_created_at lies for SLA purposes** — bot/evo
    holding replies set it. Human-reply detection = any outgoing public
    message whose sender.id ∉ {bridge user}. Resolve bridge id from
    /agents by email (hardcoding ids breaks across installs).
22. colima containers reach HOST ports only via `host.docker.internal`;
    the docker bridge gateway IP (172.18.0.1) is refused.
23. `n8n import:workflow` requires a top-level `"id"` in v2-format JSON,
    else SQLITE_CONSTRAINT NOT NULL workflow_entity.id; CLI changes need
    `docker restart n8n` to take effect.

### State

Running: evo :8080 · calc :8100 · spine :8101 · glue :8102 · dify :8180 ·
chatwoot :3000 · carbone-test :8200 · n8n :5678.
Next per HANDOFF §5: O1 compose stamp consolidation (fold chatwoot/n8n +
CHATWOOT_ENABLED env into one file), then Phase C postiz.

---

## Session 2026-08-24 (ox alpha #6) — APPROVE loop + O1 stamp

### B6 closed: staff approval actually sends

- followup_draft S8 events now store the **draft text + buyer JID**.
- Webhook intercept: `APPROVE Q-XXXX` from the STAFF number only →
  `_approve_followup` reads the stored draft (exact words staff saw),
  sends to buyer, logs S8 `followup_sent`, acks staff. Failures keep the
  draft and say so ("retry with APPROVE …"). Non-staff senders never reach
  the branch.
- Tick retry semantics: quotes whose draft generation failed (empty draft
  stored) are retried next tick; successful ones stay idempotent.
- **Live-verified**: fabricated webhook APPROVE → real WhatsApp delivered
  to Leonard's phone (buyer-side test on his own JID) + staff ack + event.
- Trap #24: evo v2 rejects sendText to numbers not on WhatsApp
  (`exists:false` 400) — seeded fake buyers can't receive; test with a
  real JID.

### O1 stamp: `compose/docker-compose.appliance.yml` rewritten

All drift traps fixed in one pass: evo image `evoapicloud/*` (+ its postgres
now DECLARED), CHATWOOT_ENABLED=true, carbone mapped 8200→4000, chatwoot +
n8n included. Single flat network with unique names/aliases (cw-postgres for
chatwoot's pg — bare "postgres" is evo's db); chatwoot env anchors shared
rails/sidekiq incl. SAFE_FETCH_ALLOW_PRIVATE_NETWORK; glue gets container-
relative URLs (EVO_URL/SPINE_URL/CALC_URL/CARBONE_URL/CHATWOOT_URL) and the
root `.env` via env_file. New `glue/Dockerfile` (builds ✓). dify stays a
separate deployment by design (~15 containers); glue points at it via
DIFY_BASE_URL/USE_DIFY=1.
Validated: `docker compose config` clean + glue image build OK. First real
`up` happens on client box #1 (this Mac's spike stack still hand-run).
First-boot checklist lives in cold-start §O1 stamp (steps manual ~20 min;
scripting them = future work).

### State

Running (spike stack): evo :8080 · calc :8100 · spine :8101 · glue :8102 ·
dify :8180 · chatwoot :3000 · carbone-test :8200 · n8n :5678.
Next: Phase C postiz, or Ducotti real-catalog ingest + full O5 acceptance.

---

## Session 2026-08-24 (ox alpha #7) — Phase C live: social drafts → approval → postiz

### Deployed

postiz single-container production recipe (+ its pg17/redis) on evo-net;
staff UI **http://localhost:13000**. Trap #25: the ghcr image serves on
**5000**, not 3000 like every doc says — port map must be 13000:5000.
Temporal "connection refused" log spam is cosmetic in this mode.

### S6 content store (spine)

`social_posts` table + endpoints mirroring S5's style:
POST /posts · GET /posts?status= · POST /posts/{id}/status
(pending|approved|rejected|scheduled|posted) · POST /posts/{id}/publish
(records postiz_id + scheduled_at). Migration applied to the live DB.

### The C loop (glue)

- `POST /c/draft_tick[?count=N]` — picks catalog SKUs without live posts,
  GLM drafts one caption+hashtags per SKU (facts-only prompt + digits guard:
  invented numbers get the caption dropped), stores pending, sends an
  approval card to BOSS WhatsApp.
- Boss replies `APPROVE P-XXXXXX` / `REJECT P-XXXXXX` (same webhook
  intercept family as B6; boss-number-gated): approve → status approved →
  push to postiz public API (`POST /public/v1/posts`, X-API-KEY) → on
  success /posts/{id}/publish records pointer. No API key/channels yet?
  Approved anyway with reason logged as S8 `postiz_push_skipped`.
  Reject → rejected.
- n8n workflow #3 active: `c-weekly-draft-001` Mondays 09:00 → draft_tick.

### Verified live

draft_tick(count=2) → 2 captions (DG-30, DG-50) + boss card on Leonard's
phone; APPROVE P-C565C6 → approved + skipped-push event (no key yet);
REJECT P-F43242 → rejected. Stamp compose updated with postiz trio
(config still valid).

### State

Running: evo :8080 · calc :8100 · spine :8101 · glue :8102 · dify :8180 ·
chatwoot :3000 · carbone :8200 · n8n :5678 · postiz :13000.
To finish Phase C for a real client: postiz UI signup + channel connect +
API key into .env. Next per HANDOFF §5: Ducotti real-catalog ingest +
formal O5 acceptance on a real phone.

---

## Session 2026-08-24 (ox alpha #8) — S1/S2 ALIGNED + O2/O5 GATES GREEN

The appliance now runs ONE coherent product story end-to-end: the generator
line (S1 catalog = S2 rules = dify KB). Trophy example rules remain only as
`pricing_rules.example.json` (unit-test fixture); live stack switched via
`PRICING_RULES` env (glue) + `RULES_PATH` (calc) to the new
`spine/rules/pricing_rules.generators.json`. ⚠️ prices are PLACEHOLDERS —
O3's boss-interview + backtest against real history is still the go-live
gate before any client.

### Changes

- **S2**: generator rule set (DG-30/50/100 · ATS-50 · STS-200; STD/XL sizes;
  genset process fees; qty tiers 0/3/6/10%; authority cap 15%; validity 14d).
  XL coef=0 keeps the never-guess escape hatch.
- **glue**: PRICING_RULES env selects the parse vocabulary; compose() guard
  now allows echoing the BUYER'S OWN digits (they are not invention — fixes
  escalation texts that repeat "200kVA" etc. getting silently downgraded to
  static templates).
- **e2e_spike** expectations moved to the aligned dataset (13/13 ✓);
  test_voice price case likewise (voice 6/6 ✓ — note: spec-en variation is
  stochastic, one flaky run self-healed on retry).

### New gates

- **tests/test_o2_quiz.py** — O2-2 verification quiz: 20 questions vs the KB
  through the live A3-Spec workflow. Result: **20/20 correct, 0 fabricated
  numbers** (gate ≥18 + 0). Fabrication heuristic = every number token's
  parts must exist in the source facts. Two initial retrieval misses were
  question phrasing (HS code / turbo-intercooled needed product context),
  not chunking defects.
- **tests/test_o5_acceptance.py** — scenarios 1-3+5-8 automated through
  route() in DRY_RUN: **9/9 PASS** (spec en ✓ spec id ✓ inline price w/
  exact total 10,088.00 ✓ formal-path armed ✓ custom ODM escalate ✓
  complaint escalate ✓ discount-push does NOT get discounted ✓ spam silence ✓).

### Full gate board (this session)

calc 22/22 · e2e 13/13 · classify 17/17 · voice 6/6 · B4 PDF 12/12 ·
O2 quiz 20/20+0fab · O5 auto 9/9.

### State

Running: evo :8080 · calc :8100 (generator rules) · spine :8101 (S6 live) ·
glue :8102 · dify :8180 · chatwoot :3000 · carbone :8200 · n8n :5678 ·
postiz :13000.
Remaining = purely physical: Leonard's phone pass on O5 scenarios 4/9/10 +
the O3 pricing interview whenever the boss's real numbers exist.

---

## Session 2026-08-24 (ox alpha #9) — live-chat defect: invented capability

Leonard's free-form chat caught a REAL defect the gates missed. On Tibet
travel asks, the escalation branch replied:

> "Yes, as a foreign trade company, we do offer travel arrangements to
> Tibet among our services."

A fabricated business capability — the exact failure class the appliance
exists to prevent, and invisible to every guard (digits/links only) and
every gate (none ask off-domain questions).

**Root cause:** escalation compose() said "thank them and promise a
colleague" with NO facts ceiling → the model politely engaged with the
request's content and confirmed whatever was implied.

**Fix (both layers):**
- glue generic-escalation prompt rewritten: do NOT engage with content,
  do NOT confirm/deny/comment on any service or plan; neutral holding line
  only.
- `dify/prompts/voice_guide.md` contract rule #8: escalation holding replies
  stay neutral; the company offers ONLY what is in `facts`.

Verified: Tibet / tours / shipping-to-Tibet all now produce exactly
"This needs personal attention from the team and a colleague will follow up
here shortly." — no engagement, no invention. Voice gate re-run ✓.

**Lesson for the gates:** O5 needs an off-domain scenario (ask for
something the client obviously doesn't sell; assert the reply neither
confirms nor discusses it). Added mentally to next O5 revision.

Note: chatwoot conversation 2 still contains the embarrassing Tibet
replies — spike data, delete at will.

---

## Session 2026-08-24 (ox alpha #10) — S9/S10/O3 harnesses + handoff wrap

Last build session of the sprint; HANDOFF.md fully rewritten.

### New gates (all executed green)

- **`tests/test_o5_s9_social.py` (5/5)** — draft_tick → pending post →
  APPROVE through the REAL webhook intercept → S6 state machine + skip-log.
  `--expect-scheduled` flag waits for postiz key/channels to claim full credit.
- **`tests/test_o5_s10_qr_drill.py`** — dry mode verifies evo/session/runbook;
  `--execute` performs the real logout→QR-rescan→poll drill (10-min cap,
  X2 target <5 min self-serve). Not yet run with --execute (needs the phone).
- **`tests/test_o3_backtest.py` + `data/o3_history.example.json` +
  `runbooks/o3-pricing-interview.md`** — O3 machinery complete: backtests
  rules vs historical quotes at ±2%, ≥90% gate, refuses to clear in EXAMPLE
  mode (3/3 self-consistent). Real history = boss interview → go-live.

### Handoff

HANDOFF.md rewritten: full state table, gate board, trap index, and a
5-item next-session list led by O3 real pricing. The appliance is feature-
complete for v1; everything remaining needs human inputs (boss's prices,
social accounts, a phone) rather than code.

---

## Session 2026-08-25 (ox alpha #11) — console spec written

No code. `docs/console-plan.md` v1.0: the Appliance Console (frontend) spec,
adapting the NaraHome design-system doc to MJCX. Decisions locked:

- Accent **MJCX Indigo** (#4F46E5 family, ink-navy rail #12142B); NEW semantic
  AI-violet triplet reserved for model-generated content; status hexes
  unchanged; per-client accent = CSS var from .env.
- Screens = Phase O productized (Connect/Catalog/Knowledge/Pricing/Voice/
  Go-Live with O2+O3 gates as blocking banners) + runtime read-only over
  spine (Home/Quotes/Customers/Social/Events). Approvals stay WhatsApp-
  canonical; chatwoot/postiz are pointer chips (X1).
- Browser never talks to organs directly — new thin glue `/console/*`
  proxies (wa/qr+status from evo, kb ingest+o2 quiz via dify, o3 backtest,
  gate summary); spine gains `/catalog/import` only.
- Milestones M0 shell → M1 runtime read-only → M2 QR connect → M3 KB+O2 →
  M4 pricing+O3+go-live. Open questions listed in §6 of the plan.

---

## Session 2026-08-25 (ox alpha #11, cont.) — console M0+M1 BUILT & VERIFIED

Spec → build in one session. `console/` = Vite + React + TS + Tailwind 3 +
lucide-react + react-router. Node 22.

### Shipped

- **M0**: tokens.css (MJCX Indigo family + AI-violet triplet + six status
  tones as CSS vars; per-client accent = var override) · tailwind.config.ts
  maps every token · AppLayout shell (240px ink-navy rail collapsible to
  64px, grouped SETUP/RUNTIME nav, active = mint marker + hover bg; 56px
  topbar w/ route titles) · auth (token in localStorage, Login screen,
  bearer on all fetches) · primitives: Button/StatusBadge(tone=)/GateBanner/
  DataTable(sticky+skeleton+empty+active-row)/KpiTile/SectionPanel+KeyValue/
  EmptyState/SkeletonRows+Block/Timeline/PointerChip.
- **M1** (read-only over existing spine APIs): Home (4 KPI tiles + attention
  banners for pending posts/stale quotes + S8 timeline) · Quotes (45/55
  two-column, selection in URL ?q=, StageRail FSM chips, request_json shown
  on ai-wash "extracted by model" vs result_json plain "deterministic") ·
  Customers (search + tier tags) · Social (read-only queue + WhatsApp-
  canonical approval banner) · Events (kind filter chips + limit select +
  timeline) · Catalog read-only table wired early.
- **spine**: new `GET /customers?limit=` (S3 listing for R3). Read-only;
  e2e re-run to prove no regression: **13/13 PASS**.

### Verified this session

- `tsc -b && vite build` clean (Tailwind processed — postcss.config.js was
  required; without it lightningcss passes @tailwind through untouched).
- `npm run lint` (oxlint) clean except the standard context-file
  fast-refresh warning (accepted).
- Live smoke: spine :8101 up → real spike data through the Vite proxy
  (:5173/spine/*) — customers incl. Leonard's JID, quotes, events all render.
- All routes 200 via dev server.

### Running now (dev, NOT the full stack)

spine :8101 (`nohup env -u PYTHONPATH calc/.venv/bin/uvicorn spine_api:app
--app-dir spine --port 8101`) · console dev :5173 (`npm run dev` in
console/, proxies /spine→8101 and /glue→8102). Login accepts any token —
server-side CONSOLE_TOKEN enforcement lands with the glue proxy endpoints
(M2). calc :8100 stopped again after the e2e gate.

### Next

M2 Connect screen (glue `/console/wa/*` QR proxy + health pointer chips) —
needs evo up. Then M3 KB+O2 quiz gate, M4 pricing viewer + O3 backtest +
go-live page.

---

## Session 2026-08-25 (ox alpha #11, cont. 2) — console M2: Connect live

### Glue additions (all additive, after `/health`)

- `GET /console/wa/status` — evo connectionState → `{state, instance}`;
  unreachable degrades to a field, never a 500.
- `GET /console/wa/qr` — evo connect → `{qr: dataURI|null, state}`; null
  when already open (verified live).
- `POST /console/wa/logout` — deliberate session drop; logs S8
  `session_drop {source:"console"}` for audit.
- `GET /console/organs` — root-HTTP probes (any answer <500 = up) for the
  seven stamp organs → pointer-chip feed.
- `_get()` gained an optional headers kwarg (backward-compatible).

### Console

- ConnectPage: WA card with live state badge (5s poll), QR panel (3s poll,
  only while not connected) + 3-step linking instructions from the runbook,
  success banner when open, danger-zone logout behind ConfirmDialog that
  names the consequence, and the organ pointer-chip grid (X1 note printed
  under it). New primitives: ConfirmDialog (no-blur overlay, Esc, focus),
  usePoll hook; api/glue.ts client.
- Login still accepts any token — server-side CONSOLE_TOKEN check lands
  with the glue proxy auth pass in a later milestone (tracked).

### Verified

- Live through Vite proxy (:5173/glue/*): status `{state:"open",
  instance:"mjcx-test"}`, organs all 7 up (stack was already running).
- QR correctly null while session open — destructive logout NOT tested
  (needs Leonard's phone to re-scan; same drill as S10 --execute).
- Gates re-run after glue edits: **S9 social 5/5 · voice 6/6 PASS**.
- tsc + build clean; oxlint clean except known context-file warning.

---

## Session 2026-08-25 (ox alpha #11, cont. 3) — console M3: Knowledge + O2 gate

### Glue additions (KB section after the console WA block)

- `GET /console/kb/docs` — dataset find + paginated document list
  (`{dataset, items:[{id,name,status,enabled}]}`, degrade-in-body errors).
- `POST /console/kb/ingest` — raw-body upload w/ `X-Filename` header (no
  python-multipart dependency); .md/.txt only (PDFs must be converted —
  matches create-by-text reality). Same-name upload replaces. Reuses
  `knowledge_ingest.py` as a module (`ensure_dataset`, `create-by-text`,
  `wait_indexed`) — one dify dialect, one implementation.
- `DELETE /console/kb/docs/{doc_id}`.
- `POST /console/gates/o2_quiz` → `{job_id}`; runs in a daemon thread,
  polls spec_answer() per question, scores hit+fabrication exactly like
  `tests/test_o2_quiz.py` but with ALLOWED DIGITS COMPUTED FROM THE KB DIR
  (`KNOWLEDGE_DIR`, default data/example/knowledge) instead of hardcoded —
  generalizes to client KBs. Question list overridable via
  `data/o2_quiz.json` (`[{q, want_any}]`) — client variation stays DATA.
  Gate = ≥90% AND 0 fabricated. Persists verdict as S8 `gate_o2`.
- `GET /console/gates/o2_quiz/{job}` · `GET /console/gates/last`
  (reads latest gate event back from S8).

### Console

- KnowledgePage: O2 gate banner (pass/fail/not-run, ⛔ go-live copy),
  Run quiz action with progress + per-question results (answers shown in
  AI-violet), doc table w/ indexing status tags + delete confirm, upload
  slot (.md/.txt). usePoll gained loading state.

### Verified LIVE (dify :8180 up)

- docs list: mjcx-knowledge → 6 real docs ✓
- upload test doc → indexed → listed ✓ · same-name replace ✓ · delete ✓
- full quiz run through the console API: **20/20 correct, 0 fabrications,
  gate PASS (~90 s)** — identical to the harness result; S8 event written
  and `/console/gates/last` reads it back ✓
- gates after glue edits: voice 6/6 · S9 5/5 ✓ · tsc/build/lint clean ✓

### New traps

26. **dify DELETE answers 204 with an EMPTY body** — `json.loads(r.read())`
    500s even though the delete succeeded. All dify deletes go through a
    tolerant `_dify_delete()` helper now.
27. **importlib-file-loaded mock_responder can't see siblings** —
    test_voice.py loads it by file path, so glue/ isn't on sys.path and
    `import knowledge_ingest` failed. mock_responder inserts its own dir
    into sys.path before the import (same trick the tests use).

### Next

M4: Pricing viewer + O3 backtest gate endpoint + Go-Live checklist page +
spine `/catalog/import`. Then the console ships in the O1 stamp compose.

---

## Session 2026-08-25 (ox alpha #11, cont. 4) — console M4: Phase O complete

### Glue additions (pricing + go-live)

- `GET /console/pricing/rules` — current S2 JSON + path (read-only; rules
  stay editable in git per rule #6).
- `POST /console/gates/o3_backtest` — optional body `{history:[...]}`;
  empty body falls back to data/o3_history.json, else the example file in
  EXAMPLE mode (gate never clears). Re-computes through calc :8100 at ±2%.
- **Gate hardening found by live testing**: uploaded the 3-row example file
  as "REAL" → it cleared the gate and flipped go-live. Fixed with
  `_O3_MIN_QUOTES = 10` (flowchart: "10–20 REAL past quotes") — under 10
  rows gate_pass stays False with a note. Purged the polluted test events
  from S8 afterwards.
- `GET /console/gates/summary` — one call for the checklist page: last
  o2/o3/go_live events from S8 + live WhatsApp state + postiz_key_set.
- `POST /console/gates/go_live` — SERVER-SIDE enforcement of "no partial
  go-lives": re-checks WA open + O2 pass + O3 REAL-pass before writing the
  `go_live` S8 event; returns blockers otherwise. Verified blocked.

### Spine addition

- `POST /catalog/import` — CSV (raw body) → S1 upsert (ON CONFLICT update)
  + GAP REPORT (`{imported, skipped[], gap_report[{sku, missing[]}]}`).
  Columns: sku,name,category,specs(k=v;k=v),moq,hs_code,certs. Live-tested:
  DG-50 flagged certs-missing, ZZ-01 flagged certs+moq — the deliverable-#1
  framing works. Test SKUs removed from the live DB after verification.

### Console screens

- **PricingPage**: terms panel (currency/validity/authority cap/manual-only
  sizes), base-price table, qty ladder, customer tiers w/ payment terms,
  process fees — the boss's money logic rendered read-only. Backtest card:
  choose history JSON → Run (or example-mode self-test), per-ref Δ table,
  banner distinguishes EXAMPLE vs REAL vs FAILED.
- **CatalogPage**: CSV import + gap report banner + S1 SKU table.
- **GoLivePage**: auto gates (WA open / catalog / KB / O2 / O3-REAL) as
  ready/open tags, social module shown as optional add-on info row, three
  human sign-off checkboxes, GO LIVE switch enabled only when everything is
  green — ConfirmDialog → server verdict; blockers render if refused;
  once live, permanent success banner from S8.

### Verified

- backtest: empty-body → EXAMPLE (gate False ✓); 3-row upload → refused on
  min_quotes ✓; go_live → blocked ("O3 backtest not passed") ✓
- catalog import via proxy incl. gap report ✓ (DB cleaned after)
- full gate sweep after all edits: e2e **13/13** · S9 **5/5** · voice
  **6/6** · O3 harness still refuses EXAMPLE ✓ · tsc/build/lint clean ✓
- note: S9 had consumed all free SKUs across runs ("all SKUs already have
  live posts") — cleared spike social_posts to restore repeatability.

### State

Console M0–M4 COMPLETE: the appliance now has a face. Remaining console
work is M5 polish (rules form editor, voice samples writer, X5 report tab)
+ shipping the built SPA in the O1 stamp compose (caddy container). The
go-live gate itself still needs real-world inputs: boss pricing interview,
postiz channel connect, phone drills.

---

## Session 2026-08-25 (ox alpha #11, cont. 5) — console SHIPPED in the stamp

### Auth is real now

- `CONSOLE_TOKEN` generated into `.env` (`openssl rand -hex 24`, value never
  printed in-session) + `.env.example` created (key names only).
- glue http middleware: `Bearer` guard on `/console/*` ONLY. Empty token =
  open (dev convenience). Buyer webhook `/webhook/evo`, ticks and /health
  deliberately untouched — evo/n8n can't carry our token without re-registering
  webhooks (noted as future hardening). Verified live: no/wrong → 401,
  right → 200, webhook → 200 unauthenticated.
- Threat model unchanged: single-tenant LAN box; spine data reads stay
  unauthenticated as before (dify tools + tests call spine directly —
  adding auth there breaks the dify tool providers for marginal gain).

### Shipping

- `console/Dockerfile`: node22 build stage → nginx:1.27-alpine serving
  `dist/` with same-origin proxies `/spine/→spine:8101`, `/glue/→glue:8102`
  (trailing-slash strip = same contract as the Vite dev proxy) + SPA
  fallback for client routing.
- Stamp compose gained the `console` service (:8090→80, depends_on
  spine+glue). Build context is the repo ROOT so nginx.conf resolves;
  Dockerfile COPYs are prefixed `console/` accordingly.
- `docker compose config` clean · `compose build console` succeeds
  (trade-agent-console image).
- cold-start runbook updated: port map +8090, first-boot step 0 = walk the
  console Setup tabs, dev-mode section documented.

### Gate sweep after all changes

e2e **13/13** · S9 **5/5** · voice **PASS** · classifier **17/17** ·
tsc/build/lint clean · compose config OK.

### Left

M5 polish (rules form editor, voice samples writer, X5 report tab);
webhook-auth hardening note above; and the standing human inputs (O3 boss
interview w/ ≥10 REAL quotes, postiz key, phone drills) — the console's
Go-Live page now blocks on exactly those.

---

## Session 2026-08-25 (ox alpha #11, cont. 6) — console M5: voice + reports

### Voice samples writer (O4-2)

- glue `GET/POST /console/voice/samples` — reads/writes ONLY the Samples
  section of `dify/prompts/voice_guide.md` (span = heading line → next
  `## `). Heading line + suffix preserved on write; block containing any
  section heading is rejected; `.md.bak` backup before every write;
  config-as-code intact (file stays in git).
- Round-trip proven lossless via md5 (GET → POST → identical file).
  First implementation ATE the heading suffix + comment — caught by the
  diff check, rewritten to a body-excludes-heading contract.

### Console: VoicePage real

Samples textarea (mono) + Save w/ success/error banners; always-human list
rendered read-only (rule #3); escalation contract excerpt incl. the
Tibet-travel lesson as AI-violet note.

### Console: ReportsPage (X5, retention artifact)

Client-side aggregation over spine reads only (quotes ≤500 / events ≤500 /
posts ≤200): period chips (30 days | this month), KPIs (quotes sent, win
rate accepted/closed, escalations, posts published), total quoted value,
top-asked products from request_json lines (Array.isArray guard — spike
rows carry `"lines": 1`), escalation-intent breakdown ("why the AI handed
off" → B5 rules-gap framing), social summary. Nav item Reports (BarChart3).

### Verified

- voice round-trip md5-lossless ✓ · heading-injection rejected ✓
- reports renders live spike data ✓ (route 200)
- gates after all edits: S9 **5/5** · e2e **13/13** · build/lint clean ✓

### State

Console feature-complete per spec §5 (M0–M5 minus the pricing FORM editor,
which deliberately waits for the boss's real numbers — the viewer +
git-edit workflow covers v1). Shipped in stamp compose at :8090 with token
auth. Remaining: humans (O3 interview ≥10 REAL quotes, postiz key, phone
drills) + optional webhook-auth hardening.

### v1.1 spec'd with Leonard (no code this session)

`docs/console-plan.md` Part 2: A) inbox face + take-over over chatwoot's
API (second client of S4, never a copy), B) pricing form editor gated on a
new calc `POST /rules/reload`, C) price_visibility per-material
public/internal_only enforced structurally in glue's B-path. Build order
A→B→C recorded in HANDOFF §5.1.

---

## Session 2026-08-25 (ox alpha #12) — v1.1-A inbox face + take-over SHIPPED

### Glue (all under /console, bearer-gated by the existing middleware)

- `GET /console/inbox/conversations[?status=open]` — chatwoot conversations
  proxied live; normalized rows (id, contact name/identifier from meta,
  unread_count, last_activity_at, last_buyer_line preview), newest first,
  plus `total_unread` for the nav badge. Second CLIENT of chatwoot, zero
  transcript persistence on our side (X1 holds).
- `GET /console/inbox/{cid}/messages` — conversation + full message list +
  `/agents` map. Sender resolution is done per call against agent EMAILS
  (trap #21 discipline): response carries `bot_sender_ids` (agents whose
  email == evo-bridge) and `agents{id->available_name}`; ids never hardcoded.
- `POST /console/inbox/{cid}/reply {"content"}` — PUBLIC outgoing via
  chatwoot. Negative tests: unauth 401/401, empty content 400, unknown conv
  404 (chatwoot passthrough).

### Trap #28 (new): CHATWOOT_API_TOKEN belonged to the BRIDGE user

First take-over drill: reply posted fine but chatwoot attributed it to
sender id 2 "WhatsApp Bridge" — /a6/sla_tick's human rule (non-bridge
senders only) would NEVER fire, so beacons would continue forever. Root
cause: the spike's api token was minted for the bridge user, not the admin.
Fix: minted the ADMIN user's own permanent access token via rails runner
(`User.find_by(email:…).access_token.token` — note: `.access_token` is an
AccessToken OBJECT in this chatwoot, need `.token`; logger noise goes to
stdout so extract between sentinels). Stored as `CHATWOOT_ADMIN_TOKEN` in
.env (+ .env.example key). glue replies use CW_ADMIN_TOKEN with fallback;
reads stay on the original token. Never printed the value.

### Console

- New runtime tab **Inbox** (`/inbox`, MessageSquare icon, second in nav):
  two-column 45%/55%, independent scroll, selection in URL `?c={id}`,
  5s poll while open. Thread bubbles: buyer lines left plain; outgoing from
  bot_sender_ids = AI-violet wash/border + Bot icon + "AI assistant";
  other senders plain card w/ resolved agent name. Private notes + activity
  (type 2) filtered out of threads (out of scope per spec).
- Reply box: free-edit textarea → POST reply → immediate refresh; footer
  states the human-take-over contract. Send errors inline.
- Nav unread badge: AppLayout polls `/console/inbox/conversations` every
  30s, attention dot on Inbox when total_unread > 0.
- tsc/vite build clean · oxlint clean (2 pre-existing warnings elsewhere).

### Acceptance drill (raw results)

Setup: stale test conv #2 resolved (toggle_status) to give a clean thread
for Leonard's real number; baseline `/a6/sla_tick` = {checked:2,beacons:[]}
(convs 1+2 already beaconed Aug-24 → idempotent skip).
1. Complaint injected via webhook (Leonard JID, COMPLAINT text): glue
   round-trip **11.5s** end-to-end incl. classify+compose GLM calls;
   conversation #3 armed at second ~9 (created_at check). In the REAL flow
   the buyer text itself appears instantly via evo→chatwoot mirror —
   Leonard's live "so?" hit chatwoot at 11:33:55 while glue was still
   routing it (<2s wall clock). Console showed conv #3 immediately after.
2. sla_tick BEFORE human reply: {checked:2,**beacons:[3]**} — bot-only
   state correctly beacons boss (msg 72 "[SLA 0h] Escalation unanswered"
   delivered to boss WA = Leonard here).
3. Take-over reply v1 (bridge token) → sender id 2 → trap #28 found+fixed.
4. Take-over reply v2 (admin token, msg 74): evo log shows WhatsApp send
   ("Update result: 1 rows affected"); delivery to phone confirmed by
   Leonard on-device during session. Thread classes now: 69/71 BOT-VIOLET
   (sid 2), 70 BUYER, 74 HUMAN-PLAIN (sid 1 'Leonard') ✓
5. sla_tick AFTER: purged conv-3 sla_beacon event (id 51) so idempotency
   couldn't mask the result → re-run {checked:2,**beacons:[]**}. Conv #3
   skipped solely because msg 74's sender ∉ bridge — take-over flips the
   SLA state exactly as designed.

### State

Conv #3 left open intentionally for console inspection. A is DONE pending
Leonard's visual pass on :5173/:8090. Next: B (calc /rules/reload + editor).

---

## Session 2026-08-25 (ox alpha #12, cont.) — v1.1-B pricing form editor + hot reload SHIPPED

### calc: POST /rules/reload (+ POST /rules/validate)

- `module-level validate_rules(rules) -> [problems]` — mirrors quote()'s
  real expectations: base/bulk/fee > 0, factor > 0, ladder min_qty strictly
  increasing ints, pct 0..<100, cap 0..100, validity_days int ≥ 1,
  coefficients ≥ 0 (0 = XL manual-quote hatch — explicitly NOT an error),
  duplicate material/tier names caught.
- `POST /rules/reload` — re-reads RULES_PATH under a threading.Lock,
  re-validates, swaps engine (nonlocal). Failure → 400 {error, rolled_back}
  + file restored from `<file>.json.bak` when one exists; engine keeps
  serving last-good rules either way. /quote now reads engine under the same
  lock (no torn reads mid-swap). /health gained schema_version.
- Live drills: clean reload ok ✓ · invalid JSON + .bak present → 400 +
  rolled_back:true + file byte-identical to pre-corruption ✓ · negative
  bulk_price (valid JSON) → 400 naming the field, disk untouched, engine
  still quoted old price ✓.

### glue: save endpoint + live parse vocabulary

- Refactor: RULES/MATERIALS/SIZES/PROCESSES/PARSE_PROMPT now built by
  `_refresh_rules_vocab()` at boot AND after every save — an edited rules
  file reaches the B1 parser without a glue restart (the other half of the
  silent-stale trap). Prompt text byte-equivalent to the old f-string.
- `POST /console/pricing/rules {"rules"}` — order of operations:
  1. calc /rules/validate (server authority, dry-run)
  2. `.bak` write + in-place write (single .bak rotation, voice_guide pattern)
  3. calc /rules/reload — on failure: restore old text + resync calc + 400
     with stage:"reload"
  4. _refresh_rules_vocab()
  unchanged payload short-circuits.
- Live drill through the console API: DG-50 base 5200→5300 saved → calc
  /quote returned unit_price 5300.00 with ZERO restarts ✓; invalid ladder
  edit rejected 400 stage=validate before any disk write ✓; revert to 5200
  verified on disk ✓.

### console: PricingEditor (design §20 full-content-area editor mode)

- Edit button on Terms panel → editor takes the content area (absolute
  inset-0 z-20 over the viewer inside a relative wrapper; wrapper freezes
  h-full+overflow-hidden while the mode is open). Own scroll region,
  sticky footer action bar, single explicit Close.
- Guarded numerics everywhere (regex-gated typing, red state + per-field
  message): base/bulk, process fees, qty-ladder rows (strict-increase rule
  enforced inline), tier factors, authority cap, validity_days. Currency +
  notes read-only. XL coef-0 rendered immutable w/ explainer ("editing it
  away would teach the model to guess").
- Diff preview before save: changed paths table with strikethrough-old /
  green-new. Save disabled until dirty && zero client errors; server
  problems render as a list; reload-stage failures explain that previous
  prices stayed live and were restored.
- Save success → onClose → viewer refetches LIVE rules (post-reload).

### Gates after all B edits

e2e **13/13** · voice **PASS** (6 cases) · S9 **5/5** · classifier gate
**PASS** (PARSE_PROMPT rebuild sanity) · tsc/build/lint clean.

---

## Session 2026-08-25 (ox alpha #12, cont. 2) — v1.1-C price visibility SHIPPED

### S2 schema v3 (backward-compatible)

Both rules files bumped `schema_version` 2→3 and gained:

```json
"price_visibility": { "default": "public",
                      "per_material": { "STS-200": "internal_only" } }
```

v2 files (no section) still load everywhere — lookups default to public.
calc's validator ignores the section (no numeric semantics), so the editor
can write it freely; calc 22/22 still green under v3.

### Structural enforcement in glue's B-path

- `material_visibility()` + `hidden_materials()` helpers; the PRICE_Q branch
  checks parsed lines BEFORE calc is ever called. ANY internal_only material
  → skip inline computation entirely → B5 escalation tagged PRICE_INTERNAL
  w/ gap hint ("price visibility: STS-200 is internal_only … human quote
  required"). Buyer hears the internal_price holding line ("team will
  confirm"); templates added en+zh. No prompt edits — the agent cannot leak
  a number it was never given (same philosophy as the PDF-CTA removal).
  calc is NOT called on this path at all in v1.1 (staff-facing margin notes
  remain an optional future use of X4).
- Live drills: "2 units of STS-200 STD" → parse action=quote → log line
  `[b-path] internal_only materials [STS-200] -> B5, no calc call`, NO new
  S5 quote, chatwoot note `[ESCALATION PRICE_INTERNAL]` armed ✓.
  Negative control: DG-50 ×3 still quoted inline (Q-746590 = 15,132.00 =
  5200×3×0.97 ladder math intact) ✓.

### Console

- Pricing viewer gained a Visibility column (eye public / eye-off internal,
  AI-violet for internal) + explainer line when any item is hidden.
- PricingEditor: per-material public/internal toggle (role=switch) in the
  base-price table; visibility changes appear in the diff preview
  (`{name}.visibility: public → internal_only`); save writes
  price_visibility back (only non-default entries in per_material).
- QuotesPage: rows whose request_json lines contain a hidden material get
  an "internal" StatusBadge (special tone) and render total as "—";
  detail header carries the tag too. Spike-row shape guarded (`"lines": 1`
  / string JSON tolerated via quoteMaterials()).
- Round-trip drill through glue API: per_material {} saved → readback {}
  → {"STS-200": "internal_only"} restored → readback exact ✓.
- Two-number floor/list variant: NOT built (deferred per spec).

### Traps found while gating (new numbers)

29. **Test fixtures go stale against the ALIGNED data line.** test_b4.py
    still quoted trophy vocab ('Crystal/Glass', '3D Laser Engraving') —
    unpriceable by generators.json, so the gate could only pass against the
    old example file. It stayed "green" in the HANDOFF board because later
    sweeps (#10/#11) silently dropped B4 from the list. Fixed the fixture to
    generator vocab (DG-50/STD/'Remote Start Controller') → **B4 12/12**
    again. Rule going forward: when the data story changes, re-run EVERY
    gate, not just the fashionable ones.
30. **S1↔KB spec drift breaks grounded answers by design.** The aligned
    DG-50 catalog row carried only power+tank (noise=70dB @ 7m lost during
    alignment), so SPEC_Q correctly REFUSED to invent dB and O5-S1 failed
    on missing data, not code. Reimported DG-50 with the full KB spec set
    (import replaces whole rows!) → grounded answer includes 120L + 70dB.
    Alignment means all three stores: S1 catalog = S2 rules = KB docs.
    (Also noted: chatwoot status changes need POST /conversations/{id}/
    toggle_status — PATCHing the conversation is a silent no-op.)
31. (minor, no fix needed) dify spec workflow can transiently stall >90s
    under concurrent load — one O5 run hung twice on S1/S2 then completed
    normally minutes later; direct probes answered in 5s throughout.

### Final gate board after A+B+C (this session)

calc 22/22 · e2e **13/13** (re-run under v3) · classify **PASS** ·
voice **PASS** · B4 **12/12** (fixture realigned, trap #29) ·
O5 auto **10/10** (after trap #30 data fix) · S9 **5/5** ·
console tsc/build/lint clean. O2 quiz not re-run (prompts untouched,
dify-live; last state 20/20+0fab).

### State

v1.1 A+B+C complete. Console now: inbox face w/ human take-over (SLA-aware),
hot-editable pricing w/ diff preview + rollback safety, per-material price
visibility enforced structurally before calc. Standing human inputs
unchanged: boss O3 interview (≥10 REAL quotes), postiz key/channels,
phone drills (S4 repeat + S10 live drop).

---

## Session 2026-08-25 (ox alpha #12, cont. 3) — Leonard's v1.1 follow-ups: manual catalog, KB writer, editor add/delete, staff-set tiers

### Spine (data layer, still unauthenticated-by-design)

- `POST /catalog/item` — single-SKU upsert (same row shape + gap semantics
  as /catalog/import; returns `{sku, missing[]}`). `DELETE /catalog/{sku}` —
  404 on unknown. Live-tested upsert→readback→delete.
- `PATCH /customers/{cid}` — staff edits {tier, name, country, language,
  email}; blank strings ignored; **tier_change events written to S8**
  ({from, to, source:"console"}) whenever tier actually moves. This closes
  a real gap: tiers were default-"new" at first resolve and NOTHING in the
  stack could change them short of sqlite.

### The customer-tier answer (now also IN the console UI)

The agent never decides tier. Flowchart B2-1 splits it: S3 owns WHICH tier
a buyer is in (staff's commercial call), S2 owns the FACTOR per tier, glue
just passes `customer.tier` into calc. CustomersPage now has an edit panel:
tier <select> populated from S2's own `customer_tiers` list (+ the current
value if it's missing from S2, flagged red "not in pricing rules!"), plus
name/country/language. A tier unknown to S2 fails safe — calc ESCALATES,
never guesses. Caption explains the split verbatim.

### PricingEditor extensions

- Currency now editable (ISO 3-letter guarded client+calc). REAL wiring fix
  found by drilling it: glue never passed currency to calc, so S2's currency
  was cosmetic — quotes always said USD (request default). PRICE_Q now sends
  `"currency": RULES["currency"]`; live drill: EUR save → Q-C98285 saved as
  5874.00 EUR → reverted to USD through the same endpoint.
- Process fees + size coefficients: add/delete rows w/ per-row delete,
  "+ Add" appends; names required + unique (case-insensitive), ≥1 size must
  remain, XL coef-0 stays value-immutable but deletable like any size.
  Diff upgraded to semantic +/- lines: fees/sizes matched by NAME so adds,
  removes and value-changes render correctly (green +, red − strikethrough).
- calc validate_rules extended: duplicate process/size names caught server-
  side too, currency regex ^[A-Z]{3}$. Editor saves rebuild glue's parse
  vocabulary (existing mechanism) — a new fee/size is quotable immediately:
  drill "DG-30 XXL + Drill Fee" parsed action=quote with both new tokens and
  priced 3850×1.5+99 = 5874 EUR without restarts.

### Console: catalog manual add/edit + knowledge writer

- CatalogPage: "Add product" opens an inline form (SKU/name/category/MOQ/
  HS/certs + dynamic spec key=value rows); pencil icon loads the same form
  from GET /catalog/{sku} for edits; trash icon deletes via ConfirmDialog;
  gap report renders after every save ("Gaps: certs, moq").
- KnowledgePage: "Write a doc" — filename (auto .md suffix) + textarea,
  reuses POST /console/kb/ingest (X-Filename), same replace-on-same-name
  semantics. Zero backend change needed. Round-trip tested: created →
  indexing completed → deleted.

### Gates after this round

e2e **13/13** · calc unit **22/22** · voice **PASS** · classifier **PASS** ·
B4 **12/12** · O5 auto **10/10** (one intermediate 8/10 was GLM generation
nondeterminism — clean rerun passed; see trap #31) · S9 **5/5** (after
clearing S6 spike rows again — same known artifact as session #11; nothing
publishes without a postiz key) · tsc/build/lint clean.

---

## Session 2026-08-25 (ox alpha #13) — VOICE OVERHAUL: "没有就说没有" (naturalness fixes from real sales-thread evidence)

### Trigger

Leonard brought two REAL WeChat sales transcripts (思鹿旅行, Tibet tours,
小红书→WeChat funnel) and asked why our replies feel unnatural next to them.
Side-by-side against our own conv #3 drill thread found 5 concrete failure
modes, all reproduced from logs:

| Buyer said | We replied | Why |
|---|---|---|
| "so what do u do?" | invented "wide range of products across industries" pitch | greeting path composes with `facts=(none — purely social)` → model fills the vacuum |
| "do u have kaolin?" | "I'll need to check with our team" ×2, nobody ever checks | dify spec_answer.yml instructs "say you will check with the team and come back" on KB miss; glue relays WITHOUT arming an escalation → fake promise |
| "so, is there anything?" | re-greeted from scratch ("Hello there! Thanks for reaching out") | classify() is stateless per message; nothing marks an ongoing thread |
| repeat ask | near-identical stall again | `_last_reply` kept ONE prior msg; opening-clash guard too weak |
| 没有就说没有，有就说有 | still deflecting | rule-8 neutrality over-applied to catalog-absence questions |

What the human seller does that we didn't: one goal + one ask per message,
a REASON attached to every ask ("小红书不能发，消息要被否"), buyer's last
answer banked and never re-asked, menu options offered to undecided buyers
(冰川/雪山/圣湖 ≈ our DG-30 backup vs DG-100 site power), uncertainty
absorbed instead of bounced. Deliberate non-goal: we do NOT copy their
move-off-platform lead-gen — inline computed quotes are the product.

### Built (all glue/dify-prompts, zero calc/spine changes)

1. **Thread continuity** (`_THREAD` replaces `_last_reply`): per-remote
   {greeted, last_buyer, last_reply, recent[2]} injected into every compose
   call. GREETING intent on a greeted thread becomes mid-conversation small
   talk steering ("…what were you looking for specifically?") — never a
   second welcome. compose() regenerates once when an opening clashes with
   either of the last two replies; after retries it prefers the guard-clean
   repeated-opening candidate over a static template (blemish < regression).
2. **Capability answers** (deterministic regex `_CAPABILITY_RES`, en/zh/id):
   "what do u do / 你们是做什么的" now composes with REAL facts from S1
   (`_company_line()` = spine /catalog names+skus, fallback S2 MATERIALS) +
   one application question. No more invented breadth.
3. **Availability probes answered plainly** (`_AVAILABILITY_RES` +
   `_in_domain()`): "do u have kaolin?" with NO SKU hit AND no domain vocab
   overlap → grounded negative + pivot to real line + chatwoot note (demand
   signal for staff). `_in_domain` = S1 name/category tokens ∪ generic
   power-domain markers (genset/kVA/ATS…), 5-min TTL cache so console
   catalog edits reach it without restart. In-domain availability asks
   ("do you have a 50kVA silent genset?") still go to RAG — we likely DO
   carry those.
4. **voice_guide.md**: new tone principle #8 (one question max, acknowledge
   first, never re-ask banked info, offer named options); contract rule 8
   scope narrowed to true escalations; NEW rule 9 allows grounded negatives
   only when the situation establishes absence; zh register gains restrained
   softeners (每条至多一个「～/哦/呢」); samples section seeded with 5
   adapted anchors from Leonard's transcripts (tone only, facts ceiling
   untouched). NEVER fake-check added to rule 7.
5. **test_voice.py expanded 6→8 cases** (capability zh + not-ours en) and
   switched to per-case jids.

### Live replay of conv #3's failure sequence (in-process, live dify/GLM/
### spine/chatwoot; throwaway jid → chatwoot conv #4 left open as artifact)

- greeting now anchors the line ✓ · capability answer names DG-30/50/100 +
  ATS/STS with ONE follow-up ✓ · kaolin → "No, we don't carry kaolin…" +
  pivot + conv-4 private note armed ✓ · "so, is there anything?" → in-context
  steer, NO re-greet ✓ · repeat kaolin → varied opening ("We don't carry
  kaolin products…") ✓ · undecided → neutral handoff (unchanged by design) ✓
- S8b regression: tibet-tours probe still neutral handoff, zero invented
  capability ✓ (detector deliberately matches identity asks only)

### New traps

32. **Prompt wording changes guard outcomes.** Rewriting the facts header to
    "Facts you *may* use" made the model OMIT line totals under
    numbers=exact → guard rejection → static fallback → voice-gate ✗ on a
    case that passed for weeks. Fixed by mode-dependent wording ("must
    convey" under exact). Lesson: in exact mode the prompt is part of the
    delivery guarantee; re-run voice gate after ANY wording change there.
33. **Voice-gate cases shared one jid**, so the new anti-repeat clash check
    compared unrelated situations' replies → double clash → false fallbacks.
    Per-case remotes fixed it. Variation is a WITHIN-THREAD property; test
    fixtures must model threads, not a global monologue.
34. (known gap, not yet fixed) dify spec_answer.yml still generates "let me
    check with the team" for KB misses that are NOT availability probes
    (attribute questions on carried products), and glue returns it without
    arming an escalation. Honest fix needs a structured [NOT_FOUND]-style
    marker in the DSL code node + dify re-import cycle — deferred, logged
    here so nobody trusts that stall line.

### Gates after all edits (FULL sweep — prompts changed)

calc unit **22/22** · e2e **13/13** · classify **PASS 17/17** · voice
**PASS 8/8** (expanded) · B4 **12/12** · O5 auto **10/10** (S8b green) ·
S9 **5/5**. O2 quiz skipped with cause: triage/spec dify apps untouched;
voice_guide feeds GLUE compose only. Console untouched → build/lint N/A.

### State

Bucket-1 human inputs still open (O3 interview, postiz key, phone drills).
Conv #3 (original evidence) and conv #4 (voice-fix artifacts) both left open
for Leonard's visual pass. Follow-ups queued: DSL fake-promise rework (#34),
escalation-note dedupe (visible again in conv #4 — two near-identical
SPEC_Q notes), webhook-auth design doc, X5 tier_change surfacing.

### Session #13 cont. (same evening) — Leonard's live phone test + the
### promise-breaking bug ("yes please" -> handoff)

Live WA test on Leonard's phone: capability answer ✓ concrete, ATS spec
answer ✓ grounded, but TWO regressions of naturalness remained:
1. First message "so okay, lets go" → cold neutral handoff. Buyer leaning IN
   got pushed away.
2. Bot offered "more details / other accessories?" → buyer: "yes please" →
   "This needs personal attention from our team…" — **the bot broke its own
   promise**. Root cause: routing is stateless per message; an agreement is
   classified fresh (agreement ≈ closure territory) with no knowledge that
   OUR previous message created an obligation.

### Built

- `_THREAD[remote].offer_pending` — every branch whose reply ends in an
  offer arms {about, facts, …}: SPEC_Q SKU path (spec facts + MOQ), RAG path
  (its own answer text as fact source — subset-number guard then permits
  reuse but blocks invented specs), capability path (company line), PRICE_Q
  delivery (kind=pdf + quote_id + customer + quote dict).
- `_is_agreement()` full-message match (en/zh/id: yes please / 好的 / 可以 /
  ya…): with a pending offer → FULFILL it (pdf kind → b4_deliver thread +
  "on its way" line; info kind → compose "deliver it now from the facts,
  no hedging, no handoff"). Agreement without pending + greeted thread →
  warm acknowledgment, never escalation.
- Substantive messages clear stale offers (no hijacking later flow).
- `_is_engage()` for bare readiness ("so okay, lets go", 开始吧): FIRST
  contact → anchored welcome (was cold handoff); regexes full-match only.
- compose() retry now spells out banned openings on attempt 2 — an
  identical prompt just reproduced id "Sama-sama pak…" twice (voice-gate ✗).

Replay of the exact phone sequence: lets-go → anchored welcome ✓ ·
capability → line + ONE question ✓ · ATS-50 → grounded specs + offer armed ✓
· "yes please" → fulfills with bullet recap of REAL facts + invites quantity
for quote ✓ (no new numbers — guard holds).

### New traps

35. **Stateless routing breaks conversational obligations.** A bot that
    makes an offer OWNS the next turn after acceptance; classifying the
    acceptance in isolation routes it to closure/handoff. Any branch that
    ends a reply with a question/offer must arm fulfillment state, and
    pure-agreement messages must check it BEFORE classification-based
    routing. (Found live on Leonard's phone, not by any gate — add a gate
    case when the thread-state API settles.)
36. **Regenerating with an identical prompt reproduces the identical
    opener** (dominant register wins at temp 0.7). Retries must inject the
    banned openings explicitly.

### Gates after this round (FULL board)

calc **22/22** · e2e **13/13** · voice **PASS 8/8** · B4 **12/12** ·
O5 auto **10/10** (one intermediate 9/10 = GLM nondeterminism, trap #31
pattern; clean rerun green) · S9 **5/5**. Classify N/A (no prompt-file
edits this round). Chatwoot artifacts: convs #3/#4 + replay threads left
for the visual pass.

### Session #13 cont. 2 (2026-08-26, 00:xx) — trap #34 bites Leonard LIVE:
### "can i know more about the ats panel?" → fake "I'll check with our team"

Leonard's 00:39 phone test: capability ✓, but an alias-phrased product
question ("the ats panel" — no digit → no SKU regex hit) fell through to
the dify RAG workflow, whose KB-miss prompt STILL says "say you will check
with the team" (#34, deferred too long). Glue relayed the stall WITHOUT
arming anyone → second broken promise in one thread ("okay so?" → handoff).

### Built (glue-side; dify DSL untouched tonight — re-import still queued)

- **Alias resolution** `_alias_sku()`: natural names → ONE catalog SKU,
  data-driven from S1 (word-overlap scoring; a shared word like "genset"
  never resolves alone, unique words like "ats"/"container" do; ties refuse
  to guess). Cached 5 min. "the ats panel"→ATS-50, "soundproof
  container"→STS-200, "100kVA open one"→DG-100 ✓.
- **`_catalog_reply()`** refactor: one S1 answer path shared by exact-SKU,
  alias, and stall-repair entries.
- **Stall repair**: RAG output matching `_STALL_RE` (check with/get back to/
  稍后核实/同事回复…) is never relayed raw — glue retries alias-resolution;
  if that fails it arms a REAL escalation so `spec_stub` finally tells the
  truth.
- **Validity backstop** (trap #38): exact-mode guards date digits, not
  phrasing — GLM occasionally rewords "Valid until" away (O5-S3 flake,
  failed once tonight after passing twice). Glue now appends the validity
  line deterministically when the generated body lacks it.

Replay of Leonard's failing sequence: company-do → line+question ✓ ·
"can i know more about the ats panel?" → full ATS-50 spec sheet + pricing
offer, ZERO stall ✓.

### New traps

37. **Alias-phrased product questions bypass SKU routing** and inherit
    whatever pathology the downstream organ has. Any product mention MUST
    resolve deterministically before falling to generative paths; resolve
    from DATA (S1 names), not hardcoded synonyms.
38. **Exact-mode number guards don't guard PHRASING.** A gated string
    ("Valid until …", contract terms) that the model may reword needs a
    deterministic post-check/backstop, not just a prompt note.

### Gates (FULL board, after all changes)

calc **22/22** · e2e **13/13** · voice **PASS 8/8** · B4 **12/12** ·
O5 auto **10/10 ×2** (validity backstop proven against its own flake) ·
S9 **5/5** (after the usual S6 spike-row clear). Classify N/A (no prompt
files touched).

### Session #13 cont. 3 (01:xx) — pricing continuation closes the sale loop

Leonard's 01:05 test: spec→offer→fulfillment all ✓, but "probably like 10
units" (answering OUR quantity question) → human handoff. Root cause chain:
(1) stateless classify sees no product/price verb → OTHER; (2) even after
glue synthesizes "10 units of ATS-50 STD" from pending-offer state, the
LIVE triage app labels that canonical ask OTHER too ("asks nothing
literally"). Fix: confirmed continuation FORCES route=PRICE_Q (cls built
locally, thread lang reused) — zero prompt roulette, no dify re-import.
Replay: specs ✓ → yes → fulfillment+quantity ask ✓ → "probably like 10
units" → **inline computed quote** ATS-50 ×10 = USD 3,780.00 (qty discount)
+ validity line + PDF offer armed ✓✓ — the full sales conversation now runs
without a single human touchpoint.

Also: O5-S8 flake caught live — triage wavered on gibberish across runs
(SPAM conf .95 vs OTHER conf .3/lang=un); low-confidence routing then
escalated KEYBOARD MASH to a human. New `_looks_like_noise` gate
(deterministic): letters < 50% of a ≥4-char message → polite silence,
before any LLM call. Bare-number replies ("10") unaffected.

### New traps

39. **Gated scenario inputs are adversarial by nature** — gibberish sits on
    a classifier decision boundary, so a gate can pass for weeks then flip
    on model drift. Anything the O5 board asserts MUST have a deterministic
    backstop where semantics allow it (noise → silence is pure glue logic;
    no model opinion needed).
40. **Canonical synthesized text still needs forced routing**: rewriting
    the buyer's words into a clean ask does NOT help if the classifier has
    never seen that intent surface without a verb. When thread state
    already proves the intent, skip classification entirely.

### Gates (FULL board)

calc **22/22** · e2e **13/13** · voice **PASS 8/8** (one zh-capability
variation flake — canonical-opener case — green on rerun) · B4 **12/12** ·
O5 auto **10/10 ×2 consecutive** (noise gate proven against its own flake) ·
S9 **5/5**. Classify N/A (triage app untouched).

### Session #13 cont. 4 (01:xx) — dashboard lag root-caused + fixed

Leonard: "everytime a message comes, it always lags and nothing loads".
Diagnosis:
1. :8090 (caddy/stamp console) is NOT RUNNING — http=000. Only :5173 dev
   mode lives. Any "dashboard" attempt at :8090 dead-ends. (Stamp build
   still pending as a deployment step; dev-mode only so far.)
2. THE REAL BUG: `/webhook/evo` is `async def` but called route()
   INLINE — classify/dify/GLM/spine are blocking urllib calls, so one
   inbound WhatsApp message froze the ENTIRE event loop for seconds
   (dify timeout alone = 90s). Every console poll queued behind it.
   Fix: `await asyncio.to_thread(route/send_text)`. Measured: console
   polls 66-137ms DURING active routing (was: hung until routing done).

Trap 41: **never block an async handler on sync I/O** — FastAPI only
offloads sync `def` handlers; an `async def` that calls blocking HTTP
starves the whole service. Any future glue endpoint touching organs must
use to_thread or async clients.

### Gates: calc 22/22 · e2e 13/13 · voice PASS · B4 12/12 · S9 5/5 ·
O5 auto **10/10**.

---

## Session #13 cont. 5 (02:xx) — v1.2 THREADS: chatwoot removed from the loop

Leonard decision (02:0x): "we are not gonna use chatwoot anymore" —
escalations live on a dashboard page instead; spine becomes THE conversation
store (X1 gets cleaner: one runtime store). Agreed plan: keep chatwoot
installed but disabled-by-default (`CHATWOOT_ENABLED=0`), rollback path
preserved.

### Spine (S4 store)

- `conversations` (wa_jid UNIQUE, contact_name, status open|resolved,
  escalation_tag/escalated_at, sla_beacon_at) + `messages` (direction
  in|out, sender_kind buyer|bot|human|system). Live migration via
  `_ensure_convo_tables()` (init_db DELETES the db — never run it against
  the live spike).
- Endpoints: `/conversations/upsert`, `/{cid}/messages` (human outbound
  auto-clears escalation; buyer inbound reopens resolved), `GET
  /conversations?include_last=1` (conditional aggregates → last_in_at /
  last_human_out_at without N+1), `/{cid}/messages`, `/{cid}/escalate`
  (arms flag + system-note + S8 event), `/{cid}/sla_beacon`,
  `/{cid}/status`.

### Glue

- `_mirror()` — every webhook inbound + every bot outbound lands in spine,
  best-effort, BEFORE routing (staff see the thread even if routing dies).
- `escalate_to_chatwoot` split: default arms the SPINE conversation;
  CHATWOOT_ENABLED=1 restores the legacy inbox path verbatim.
- NEW `POST /console/threads/{cid}/reply` (bearer-gated): staff take-over
  sends via evo DIRECTLY (no bridge identity at all), mirrors as HUMAN
  outbound → clears escalation → stops SLA. evo failure → 502, nothing
  mirrored (never record an unsent message).
- `sla_tick` v2 reads spine: beacon when last_in_at > SLA_HOURS old AND no
  human out after it AND not already beaconed. Legacy path behind the flag.

### Console

- ThreadsPage replaces InboxPage (route /inbox kept): two-col list/thread,
  violet AI bubbles vs plain human vs left buyer lines, centered system
  notes (escalation summaries are STAFF-facing), escalation badge per row,
  Resolve button (ConfirmDialog), reply box → glue take-over. Sidebar
  attention dot now = open conversations WITH pending escalation (was:
  chatwoot unread count).

### Drills executed LIVE

- complaint webhook → transcript mirrored → COMPLAINT armed ✓
- take-over via new endpoint → delivered to Leonard's REAL phone ✓,
  escalation cleared ✓
- sla_tick: 3h-old drill thread → boss nudged once ✓, second tick silent ✓
- dashboard lag fix verified earlier this session (polls 66-137ms during
  active LLM routing; :8090 still needs its caddy container to ship)

### Gates (FULL board after all layers)

calc **22/22** · e2e **13/13** · voice **PASS** · B4 **12/12** · S9 **5/5**
· O5 auto **10/10** · console tsc/build/lint clean (2 pre-existing
warnings). DRY_RUN gates write nothing to the store by design.

### State / follow-ups

Chatwoot containers still RUNNING but unused (flag off) — stop them in a
later cleanup once v1.2 soaks. Stamp (:8090 caddy) still pending as a
deployment step. Legacy /console/inbox/* glue endpoints retained untouched
for rollback. dify DSL fake-promise (#34) still queued (needs re-import).

### Session #13 cont. 6 (02:xx) — the AUTONOMY DIAL (Leonard: "control the
### 程度 of the decisions")

Bosses differ: some want an assistant that barely decides, some want a
closer. Implemented as a DATA dial in S2 (`agent_policy.autonomy`), riding
the EXISTING hot-reload pipeline — no new endpoints, no restarts, editor-
compatible (calc validator ignores unknown keys, same precedent as
price_visibility v3).

- **assistant** — AI never touches money: PRICE_Q → honest holding line
  ("team is preparing your quotation") + escalation armed for a human quote.
  Specs/capability/thread behavior unchanged.
- **standard** (default; key absent = standard) — everything built today.
- **closer** — ambiguous OTHER gets ONE clarifying question before handoff
  (commits to nothing; grounded menu of options offered), budget resets when
  any message routes successfully. Second ambiguity still escalates.

NON-NEGOTIABLE at every level: always-human list (complaints, payment/legal,
discount beyond authority cap, unknown tiers, internal-only pricing). The
dial moves SALES autonomy, never safety.

Console: segmented control on Pricing → Terms panel header
(assistant/standard/closer) writing agent_policy via the same save endpoint
as the editor (validate → .bak → write → calc reload → glue vocab refresh).
'standard' REMOVES the key entirely (clean data story). Live-immediate.

Drilled LIVE through the real save pipeline:
- assistant: "price for 2 DG-50 STD" → holding line, NO numbers, escalation
  armed ✓ (hot reload proven — glue picked up the level without restart)
- closer: greeting ✓ → "what about that thing we talked about?" (conf 0.6)
  → clarifying question WITH menu ("diesel gensets, ATS panels, soundproof
  containers") ✓ → "so?? is yes or no" (conf 0.75, budget spent) → normal
  handoff ✓
- restored standard; full gate board re-run GREEN (calc 22/22 · e2e 13/13 ·
  voice PASS · B4 12/12 · S9 5/5 after the usual S6 clear · O5 10/10).
Gates pin STANDARD behavior — a client may only move OFF standard AFTER
go-live gates pass; document per client.

### Session #13 cont. 7 (04:xx) — postiz "can't login" root-caused: the
### backend was NEVER alive (trap #42)

Leonard: signup worked, login doesn't. Diagnosis: `docker logs postiz` —
backend (Nest) crashes on boot since v2.12.0: it REQUIRES a reachable
Temporal scheduler (`TEMPORAL_ADDRESS`, port 7233); unset → falls back to
localhost:7233 → ECONNREFUSED → process dies. The Next frontend survives,
so :13000 serves a login PAGE whose every request dead-ends. Signup looked
like it worked; nothing persisted. Our S9 gate never caught it because it
gracefully skips without POSTIZ_API_KEY — and `/console/organs` probes only
frontend reachability.

Fix (appliance-appropriate): PINNED `ghcr.io/gitroomhq/postiz-app:v2.11.2`
(last pre-Temporal release) in compose + MAIN_URL/FRONTEND_URL/
STORAGE_PROVIDER=local env to silence config warnings. Removed the old
hand-run containers (safe: nothing had ever persisted) and recreated via
compose. Now: all four pm2 processes online, backend "🚀 running", auth
endpoints answering.

ALSO found: compose-created container came up with NO network attached
(empty Networks after the earlier port-bind failure) — force-recreate
fixed it. If a compose service looks alive but is unreachable, check
`.NetworkSettings.Networks` for {}.

### New trap

42. **`latest` organ images rot under you.** Postiz ≥2.12 silently needs a
    Temporal stack; the failure mode is nasty (backend dead, frontend
    alive = organ looks healthy). Pin versions in compose; probe organs
    with a REAL endpoint, not a TCP connect / homepage 200.
