# Plan — Modular Agent Platform ("pick your agents, pay accordingly")

**Date:** 2026-09-08 · Status: proposal v3 — all 11 agents planned; every v2 agent verified against candidate OSS/organs (evidence inline) · Grounded in `docs/architecture-report-2026-09-08.md` and `Trade_Agent_Appliance_Flowchart_v1_0.md`.

## Vision (one paragraph)

A client onboards once: WhatsApp connected, catalog imported, pricing rules set, KB loaded — the **spine** now holds their business knowledge. From the console they **pick agents à la carte** and pay per selection. Agents are feature-switches on one appliance, not custom projects. Turning an agent off never deletes data; turning it on later finds the knowledge warm. Payment fulfills as a signed license file — no billing infrastructure until scale demands it.

## Operating principles

1. **Every phase ships to ≥1 live design partner.** No stockpiling. Build → deploy → feedback → next.
2. **Base platform is never optional:** spine + console + WhatsApp/email channel + threads/escalation. Human takeover is safety, not a feature.
3. **Agents are manifests, not forks:** `agents/*.yml` declares routes, pipeline hooks, data appetite, gates, and `status: available | roadmap`. Roadmap agents are never sold.
4. **Entitlements gate execution, never data.** License off → honest "not in your plan"; spine untouched.
5. **Build order = data synergy × effort**, cheapest-from-spine first, so each new agent both gives value and deepens the moat.

---

## Phase 0 — Honest menu + manual payment (this week, zero code)

- Cut the 11-agent slide: **Available** = Sales Core (Inquiry + Quoting, bundled), Social (early access), Product Knowledge, Quote PDFs. **Roadmap** = the rest.
- Repositioning line: *"The quoting appliance that never guesses a number."*
- **Payment = manual fulfillment:** invoice + bank transfer → `scripts/make_license.py` (sign: hs256-v1 HMAC-SHA256 — stdlib-only; Ed25519 = upgrade path — appliance_id, client, agents[], trial?, expires_at) → drop file into appliance. No Stripe. SME B2B pays by wire; infrastructure now would be waste.

## Phase 1 — Entitlement layer — ✅ BUILT 2026-09-08

- `agents/manifest.yml` + `make_license.py` + glue middleware extension (`_console_auth`, `mock_responder.py:620`) + console LicensePage/nav gating + `tests/test_entitlements.py`.
- No license found = everything on (back-compat).
- **Renewals ride existing infra:** license expiry warnings via console banner + boss WhatsApp nudge — same pattern as the A6 SLA beacon, n8n cron.
- Payment still manual; license issuance is now a 2-minute habit.
- **BUILT 2026-09-08:** `agents/manifest.json` (JSON, not YAML — pyyaml
  absent from the venv; stdlib discipline), `glue/entitlement.py`
  (longest-prefix route map, shadow semantics, 30s cache),
  `scripts/make_license.py` (issue/verify; refuses roadmap agents),
  middleware gate + `GET /console/license` in `mock_responder.py`,
  console `LicensePage` + entitlement-aware nav, and gate
  `tests/test_entitlements.py` — 22/22; console `npm run build` green.

## Phase 2 — Package built agents + payment links (~1 wk)

- Per-agent manifests for what's built; per-agent onboarding checklist in console (GoLive-gate pattern).
- **Payment link** (Stripe or Midtrans/Xendit for IDR) per plan SKU; payment webhook/email still triggers manual license issuance. Portal comes only at scale.

## Phases 3–5 — The build queue (one design partner per agent, feedback before next)

Ordering rationale: spine-cheap first (value fast, moat deepens), new-domain stores last.

| Phase | Agent | Why this order |
|---|---|---|
| 3 | Customer Knowledge, Document Gen ext | pure spine reads + carbone reuse |
| 4 | SOP Guide, Meeting Intelligence | KB infra reuse, then new ASR dependency |
| 5 | Supplier & Procurement, Market Intel, Positioning | new stores / external data costs |

---

# Per-agent build plans

## ✅ Built — package only (Phase 2)

**Inquiry Auto-Response** — Phase A, gated (O2 20/20). Sell inside Sales Core.
**Quoting & Pricing** — Phase B, calc + guards, e2e 13/13. Flagship; price against "fraction of a junior sales hire."
**Social & Channel Ops** 🟡 — headless postiz + S6 queue + drafts live. Gap to close for GA: provider-app creds onboarding runbook per client, content-generation breadth (listing copy), scheduling QA. Est: 1 wk polish.
**Product Knowledge** 🟡 — S1 + dify KB + spec-RAG + O2 quiz. Gap: KB ingestion UX for non-markdown files, per-client dataset provisioning script (kills the hardcoded dataset ID, discrepancy D2). Est: 3–4 days.
**Document Generation** 🟡 — quote PDFs only. **MVP extension:** invoice + packing-list + proforma templates via carbone (template + data merge — `spine/templates/` pattern exists), console template picker, S8 audit per doc. Est: 1 wk.

## 🏗️ Build — Phase 3

> **Status 2026-09-08:** Customer Knowledge **BUILT** — `customer_facts` table +
> guarded CRUD (citation required, dedupe, staff/agent source tags) in spine,
> brief endpoint (`/console/customers-facts/brief/{cid}`, GLM + deterministic
> fallback), agent memory capture in the v2 loop (`KNOWLEDGE_CAPTURE`, background,
> extract-not-infer), gate `tests/test_customer_knowledge.py` 12/12 live-spine.
> Manifest flipped to `available`. Console facts/brief panel wired
> (CustomersPage: facts list, delete, takeover-brief button). Doc-Gen
> bundle **BUILT** — `scripts/make_doctemplates.py`
> (invoice/packing-list/proforma docx), `POST /console/docgen/render`
> (S5 quote → carbone → S8 audit), gate `tests/test_docgen.py` 7/7
> (live render skipped while carbone is down). **Phase 3 COMPLETE.** Market Intelligence backend **BUILT**
> (S9 store + url-dedupe, feed fetch via agents/feeds.json, digest with
> mandatory [I<id>] citations, changedetection watch webhook → boss WA),
> gate `tests/test_intel_digest.py` 10/10, manifest flipped `available`.
> Supplier & Procurement (U) **BUILT** — S12 tables (suppliers/items/POs
> with status machine + S8 audit + overdue delay flags), gate
> `tests/test_procurement.py` 13/13, manifest flipped `available`.
> Positioning (P) **BUILT** — `POST /console/positioning/analyze`
> (citation contract [L<n>], code-computed price bands, memo persisted to
> data/positioning/ + S8 pointer), `/console/positioning/promote` → S1
> PROPOSED drafts (never quotable until approved — resolve/quote paths
> filter status='live'), gate `tests/test_positioning.py` 8/8, manifest
> flipped `available`. Phase 4:
> SOP + Meeting Intel (needs ASR organ/bake-off).

**Customer Knowledge (客户记忆)** — *pure spine reads; no new organ. twenty verified 2026-09-08.*

Component map (flowchart notation):
```
  ┌─ read:  S3 customers + S4 conversations + S5 quotes + customer_facts (spine)
  │            ──► glue /console/customers/{id}/brief --GLM digest, cited--> ThreadsPage
  │  read:  console 360° profile page ──► ▣spine read APIs (DataTable/Timeline)
  └─ write: v2 turn ends ──► guarded fact-extraction ──► customer_facts (message_id cited)
```
- Effort: ~1.5 wk. Gates: brief may cite ONLY facts present in retrieved S3/S4/S5/S8/facts rows (no synthesis); fixture-customer test asserting brief ⊆ facts; memory-write test — invented fact must be rejected; take-over-flow regression (brief injection must not slow `route()`).
- MVP: (a) **360° profile page** — identity, tier, first-seen, full message timeline, quote history with statuses, notes, S8 events for this customer — all existing spine reads, one page; (b) **pre-takeover brief** — when staff opens a thread (or an escalation fires), glue composes one cited paragraph: who they are, what they want, open quotes, last sentiment, suggested next step; (c) **staff-departure insurance** — the brief is generated from spine, so any team member gets full context instantly (the slide's exact promise); (d) **agent memory writes** — the CRM is two-directional: after each v2 conversation turn, guarded fact-extraction pulls durable buyer facts (preferences, stated terms, payment/shipment constraints, personal details the buyer volunteered) and appends them to a new `customer_facts` table, each row tagged with the `message_id` it came from. The agent then reads these facts back in the brief — this is the "memory" the owner asked for.
- Data: **`customer_facts(id, customer_id, fact, source_message_id, ts, confidence)`** — the only new table; S3 stays master for identity, S4/S5 read as pointers. X1-clean.
- Memory gate (same discipline as everything else): a fact may only be written if traceable to a real message; extraction prompt is extract-not-infer (no "probably means"); duplicate/near-duplicate facts merge on write.
- Organ verdict: **▣twenty (twentyhq/twenty) = DEFER** — verified: 2 GB RAM minimum / 4 GB recommended, its own PostgreSQL 16 + Redis stack, AGPLv3 with `/* @license Enterprise */`-gated files. It wants to own contacts (mastership conflict with S3). Trigger to revisit: a client explicitly needs pipeline/deal views → ship twenty as a *derived view* behind a spine→twenty sync job, 16 GB box only. The flowchart already said exactly this ("twenty enters when client needs CRM views").
- Effort: ~1 wk. Gates: brief may cite ONLY facts present in retrieved S3/S4/S5/S8 rows (no synthesis); test with a fixture customer + assert brief ⊆ facts; take-over-flow regression (brief injection must not slow `route()`).

**Document Generation** (extension above) ships here if not in Phase 2.

## 🏗️ Build — Phase 4

**SOP & Process Guide (操作指引)** — *no new organ; KB + quiz + photo-verify are all existing patterns composed.*

Component map (flowchart notation):
```
  SOP docs (structured markdown, git S7) ──► ▣dify KB (separate dataset, per-client)
  Staff asks in console/WA ──► RAG answer + step citation ──► "show me" runner page
  Runner: step N ──► photo upload ──► glue /sop/verify (path-whitelisted, GLM checks
        photo against step's expectation prompt) ──► pass → step N+1 ──► S8 audit
  New-hire mode ──► O2-quiz engine re-run over SOP dataset (gate: 0 fabrications)
```
- MVP: (a) SOP authoring — structured markdown (title, trigger, steps with expectation prompts, photos) versioned in S7 per client, ingested to a **dedicated dify dataset** (never mixed with the buyer KB — a staff answer must never leak internal pricing to a buyer); (b) **guided runner** — staff picks an SOP, console walks steps, each verify-step demands a photo, GLM vision pass/fails against the step's expectation, result audited to S8; (c) Q&A — staff asks "how do we handle a bank-detail change?" → RAG answer citing SOP + step; (d) new-hire quiz — O2 engine over the SOP dataset.
- Data: **S11 SOP Store [spine, OURS]** — `sop_runs(id, sop_id, staff, step, status, photo_path, verdict_json, ts)` (runs are master; SOP docs live in S7 git + dify KB as derived). Photo files on a volume, path-pointer in spine — with **prefix validation inside SOCIAL_IMAGES-style storage** (kills the audit's M1 file-read chain class properly).
- Privacy rule: SOP dataset is **staff-only** — entitlement-checked in glue; buyer-facing `route()` never queries it. This agent is 运营端-only by construction.
- Effort: ~2 wks (dataset + runner page + verify endpoint + quiz wiring + gate).
- Gates: (a) quiz over SOP dataset with 0 fabricated steps (O2 pattern, staff Q&A eval); (b) verify-endpoint adversarial test — wrong-object photo must fail; (c) cross-tenant leak test — buyer-side route() must be unable to retrieve SOP dataset content.

**Meeting Intelligence (会议与沟通助手)** — *needs a new organ: a transcriber. Verified 2026-09-08.*

Component map (flowchart notation):
```
  ▣evo voice-note / console upload ──► glue /meetings ──► ▣speaches (faster-whisper)
        --HTTP: POST /v1/audio/transcriptions (OpenAI-compatible)--> transcript
        ──► GLM summarize + action items (structured JSON) ──► S10 meetings (spine)
        ──► action items → S8 events; follow-ups → B6 approve flow ──► ▣evo send
```
- **Organ ▣speaches** (`speaches-ai/speaches`, MIT, self-hosted): faster-whisper `large-v3-turbo` INT8, **~1.0–1.8 GB RAM**, decodes WhatsApp `.ogg`/Opus **in memory** (no ffmpeg temp files), OpenAI-compatible HTTP API, diarization endpoint bundled. Chosen over: FunASR (needs ≥8 GB box — skip), whisper.cpp (ogg needs external ffmpeg), hosted OpenAI/Deepgram (cost + data leaves client box).
- **Fallback organ: GLM-ASR-2512** (reuses existing `GLM_API_KEY`, $0.0024/min, 0 RAM) — but strict `.wav`/`.mp3` ≤30 s ⇒ glue must transcode + slice. Profile choice per box (see §Organ deltas): 16 GB box → speaches; 8 GB box → GLM-ASR.
- MVP: (a) **voice-note intake** — inbound buyer voice notes in Phase A auto-transcribed before `route()` (instant upgrade to the live agent, not just meetings); (b) meeting upload in console → transcript → summary + action items → approve → send as follow-up via existing B6 draft flow.
- Data: **S10 Meetings Store [spine, OURS]** — `meetings(id, ts, source, customer_id?, audio_path, transcript, summary_json, action_items_json, status)`; raw audio on a volume, path-pointer in spine (same pattern as S5 `pdf_path`). Per X1: meetings = master; contacts = pointer to S3.
- Effort: ~2–2.5 wks (compose service + glue transcribe adapter + console Meetings page + voice-note intake branch).
- Gates (before trusting extraction): 10-clip CN/EN bake-off on real noisy factory/trade audio (WER threshold), plus claims-grounding: every action item must cite transcript spans — no invented commitments (O2 philosophy).

## 🏗️ Build — Phase 5

**Supplier & Procurement (采购协同)** — *largest build; new domain; ERP-organ question answered.*

Component map (flowchart notation):
```
  Quote (S5) or stock need ──► glue /procure/draft ──► GLM picks suppliers (S12) +
        splits lines ──► PO draft ──► boss approval (B6 pattern) ──► PO PDF (▣carbone)
        ──► emailed/WhatsApp'd to supplier ──► status updates ──► S12 purchase_orders
  ▣n8n clock ──► open-PO age check ──► delay flags → boss WhatsApp (A6 beacon pattern)
```
- MVP: (a) supplier register — terms, lead times, quality notes, contacts, price lists per item; (b) **PO drafting** — from a won quote or restock need, GLM proposes supplier split (which factory makes which lines, based on capability notes + lead time), human approves (never auto-send in v1); (c) comparison view — same lines across suppliers, landed-cost columns; (d) delay flags — POs older than promised lead time → beacon.
- Data: **S12 Procurement Store [spine, OURS]** — `suppliers`, `supplier_items` (capability + price pointers), `purchase_orders` (status machine draft→approved→sent→confirmed→shipped→received). Master per X1; contacts may pointer to S3 if the supplier is also a customer.
- **ERP organ verdicts (verified 2026-09-08):** ▣erpnext = **DEFER** — production stack is ~7 containers (backend, MariaDB, Redis ×3, socketio, workers, proxy) wanting **4–8 GB RAM**; disqualifying on this box. ▣Dolibarr = **DEFER (the credible one)** — all-in-one PHP container + MariaDB, 1–2 GB, GPLv3+, and its REST API genuinely supports supplier-order creation (`date`/`socid`/`lines`). Trigger to revisit: a client needs formal supplier-invoice workflows or inventory accounting — then Dolibarr ships as the PO-document organ with spine `suppliers` synced in as master. Until pulled: **build-ours** (matches how quote-PO drafts already work via carbone).
- Bonus: the supplier price pointer feeds a **cost field in S2 → calc computes margin internally** — closes HANDOFF's open scope question; X5 then reports real margin per quote (boss-grade retention artifact).
- Effort: ~3 wks. Design partner: one ICP #2 trader (solar-parts profile) — this is their agent.

**Market Intelligence (市场情报)** — *new organs for sourcing + watching; digest composer is OURS. Candidates verified 2026-09-08 (LibrarianOSS + LandscapeScout).*

Component map (flowchart notation):
```
  ▣rsshub (optional, no-Chromium profile) ─┐
  ▣rss-bridge (page→RSS for dull portals)  ├─► ▣n8n daily tick ──► glue /intel/digest
  native Google-News RSS ──────────────────┘         (GLM summarize, cite item ids)
  ▣changedetection.io ── CSS/JSONPath price & page selectors ── webhook ──► glue
                                             │
               digest + alerts ──► ▣evo boss WhatsApp + console IntelPage
                                             ▼
                                    S9 intel_items (spine, OURS)
```
- **Verified verdicts on your 4 candidates:**
  - **RSSHub** (46k★, AGPL-3.0, active): **SHIP selective, no-Chromium profile** — first-class MOFCOM / PBC / China-Customs / Google-News routes (pure HTTP RSS out, ~200 MB). ⚠ Customs route needs Playwright + China-resident IP (+1–1.5 GB) → excluded from default stamp; WeChat 公众号 routes are brittle mirrors → client-opt-in only. Run unmodified per rule #3.
  - **condenseit** (81★, MIT): **REFERENCE-ONLY** — clean OpenAI-compatible LLM config + preference scoring to borrow as patterns, but its web app duplicates our n8n→glue→WhatsApp pipeline (~100–180 MB for redundancy we don't need).
  - **competitive-intelligence** (20★, MIT): **SKIP** — 7-commit demo; hard paid Tavily dependency (`TAVILY_API_KEY` or it raises); no HTTP server at all (MCP/CLI only).
  - **Discount-Bandit** (739★, MIT): **SKIP** — 100% Amazon/AliExpress scraping via stock Chromium (no proxies/CAPTCHA): ToS-toxic in a client-shipped product, selector rot, IP bans, 1.5 GB + MySQL. Competitor watching is done properly by ▣changedetection.io below.
- **Organ additions:** ▣changedetection.io (~150 MB, watches *competitor's own sites* — B2B pages, not Amazon — CSS/JSONPath selectors incl. JSON price extraction → webhook → glue alert flow); ▣rss-bridge (50 MB, turns feedless trade/tariff portals into RSS — the lightweight RSSHub alternative); n8n RSS-read for native Google News (no organ needed).
- **Digest composer is OURS** (X5-send pattern): n8n daily tick → glue fetches new `intel_items` → GLM summarize **with mandatory item-id citations** → boss WhatsApp + console IntelPage. Paid data (TradeInt-class) only as a client-paid add-on.
- Data: **S9 Intel Store [spine, OURS]** — `intel_items(id, ts, source, url, title, summary_json, kind[news|tariff|price_watch], status)`; feed/watch list = S7 config-as-code (git). Per X1: intel items = master; delivery = existing WhatsApp path.
- Effort: ~2 wks (compose additions + glue digest/alert endpoints + IntelPage + n8n workflows + gate).
- Gates: every digest claim must cite an `intel_item` id (no synthesized news — O2 philosophy); price-watch alerts must echo the observed value + URL verbatim; `test_intel_digest.py` with fixture feeds.

**Marketplace & Positioning (选品与市场定位)** — *decision locked with owner (2026-09-08): scraping-first MVP; we're a China company, gray-area listing collection is an accepted operating stance. Ship it working; optimize later.*

Component map (flowchart notation):
```
  ▣scraper connector (OURS, pluggable) ──► raw listings cache (data/positioning/)
        alibaba.com / 1688 (home turf, headless browser, rate-limited)
        amazon (harder blocks: manual paste in MVP, scraper behind flag later)
        ──► glue /positioning/analyze ──► GLM structured extraction (price bands,
        feature language, review complaints, gaps) ──► positioning memo
        ──► draft S1 items (PROPOSED) ──► staff approve ──► S1  ──► Phase C content hooks
```
- MVP: connector scrapes a category's listings (title, price, MOQ, reviews count) on demand → extraction → **positioning memo** (price bands, winner language, unmet complaints = product-opportunity list) → suggested catalog bundles + **draft S1 items** staff approve into the catalog (S6-style approve flow). Manual paste remains as fallback input mode for anything the scraper can't reach.
- Connector design (so "optimize later" is a swap, not a rewrite): one `ListingSource` interface — implementations `alibaba_scrape`, `manual_paste`, `keepa_api` (~€49/mo, the clean pipe, pluggable the day a client wants legitimacy). Cache every fetch; rate-limit; per-run raw snapshots kept so analysis is reproducible.
- Operational risks accepted (engineering facts, not moralizing): selectors rot and platforms block — expect maintenance; never scrape from the appliance box's home IP for clients (runs from MJCX ops or a cheap VPS); CAPTCHA → fall back to manual paste for that run. These are costs-of-doing-business, priced into MJCX ops time, not product code.
- Data: no new store — raw snapshots + memos under `data/positioning/`, run records in S8, outputs into S1 (draft status) + S6 (content hooks).
- Effort: ~2.5 wks (scraper connector + analyze endpoint + extraction schema + memo render + S1 draft flow + gate).
- Gates: memo claims must cite listing ids from the fetched set (no invented "the market wants"); extraction schema validation; fixture eval with 3 planted gaps asserting recall; scraper test runs against a frozen HTML fixture (never live-platform CI).

---

## Organ & store deltas (v2 additions — compose + component map)

**New organs (all optional, off in the default stamp unless the client buys the agent):**

| Organ | Image | RAM | Integration | Serves |
|---|---|---|---|---|
| ▣speaches | `speaches-ai/speaches` (MIT) | 1.0–1.8 GB (turbo INT8) | HTTP OpenAI-compatible `/v1/audio/transcriptions` | Meeting Intel, voice-note intake |
| ▣changedetection.io | official (GPL-3.0) | ~150 MB | Webhook → glue | Market Intel price/page watches |
| ▣rsshub | `diygod/rsshub` + redis (AGPL-3.0) | ~200 MB (no Chromium) | RSS over HTTP | Market Intel trade-policy feeds |
| ▣rss-bridge | `rss-bridge/rss-bridge` (Unlicense) | ~50 MB | RSS over HTTP | Market Intel portal→feed |

**New spine stores (each declared master-per-X1):** S9 `intel_items` (Market Intel) · S10 `meetings` (Meeting Intel) · S11 `sop_runs` (SOP Guide; SOP docs live in S7 git, dify KB derived) · S12 `suppliers`/`supplier_items`/`purchase_orders` (Supplier & Procurement) · Phase 3 Customer Knowledge adds none (reads only) · Positioning adds none (outputs into S1/S6, artifacts in S8).

**Appliance profiles (RAM budget, box selection):**
| Profile | Stack | Total RAM |
|---|---|---|
| Base (today) | compose as shipped | ~5 GB |
| 8 GB box | base + changedetection + rss-bridge; ASR = hosted GLM-ASR; no rsshub | ~5.5 GB |
| 16 GB box | base + all four organs + speaches turbo INT8 | ~7.5 GB |

**License notes:** RSSHub is AGPL-3.0 — run the container unmodified (rule #3 keeps us safe; modification would trigger source-disclosure of our fork). changedetection.io GPL-3.0 — same, container-as-organ. pyannote diarization weights are HF-gated (token + acceptance) → **diarization OFF in default profile**; enable only for clients who need speaker labels and accept the setup step.

**Deferred organs — verified weights, explicit re-entry triggers (flowchart line 75-77 made these opt-in; here is the evidence):**

| Organ | Verified weight | Verdict | Re-entry trigger |
|---|---|---|---|
| ▣twenty CRM | 2 GB min / 4 GB rec + own PostgreSQL + Redis; AGPLv3 + enterprise-gated files | DEFER | Client explicitly needs pipeline/deal views → ship as derived view behind spine→twenty sync, 16 GB box only |
| ▣erpnext | ~7 containers, 4–8 GB RAM, MariaDB + Redis ×3 + workers | DEFER | Client has real inventory/PO volume AND a dedicated box |
| ▣dolibarr | 1–2 GB all-in-one + MariaDB, GPLv3+, REST supplier-orders API | DEFER (credible) | Client needs formal supplier-invoice workflows → ships as PO-document organ, spine S12 stays master |
| ▣meetily | Tauri **desktop** app (Rust+Next.js+Ollama, local whisper.cpp) | REFERENCE-ONLY | Wrong distribution model for a server appliance; revisit only as a per-staff desktop companion SKU |

**Positioning data add-on:** ▣keepa API (token-based, from ~€49/mo) — the only ToS-clean pipe for real Amazon price/rank history; client-paid, never in base. Alibaba Open Platform is seller-ops integration, not analytics → manual exports.

---


## Pricing shape

- **Base platform:** flat monthly (channel + spine + threads + console) — low, it's the hook.
- **Sales Core (Inquiry + Quoting):** flagship, priced vs. junior sales hire.
- **Minimum plan = 1 market-side + 1 ops-side** (data loop must spin).
- **Additional agents:** accessory pricing; **30-day all-available trial** flag in license.
- Renewal nudges via existing beacon infra; grace period 7 days.

## Payment roadmap
| Stage | Mechanics |
|---|---|
| Now | Invoice + wire + `make_license.py` (2-min fulfillment habit) |
| Phase 2 | Payment links per SKU (Stripe/Midtrans/Xendit); manual issuance on payment confirmation |
| Scale | Mini hosted portal: issue/renew/revoke licenses, self-serve trial. Build only when >10 active clients |

## Deliberately NOT doing

Usage metering · billing infrastructure before 10 clients · DRM hardening · any roadmap-agent sale before its gate suite exists · live-platform scraping in CI (fixture-based tests only) · residential-proxy farms in base pricing (gray-area scraping is accepted per owner decision 2026-09-08, but its ops costs stay in MJCX ops time, not the sticker price).


## Open decisions

1. ~~ASR vendor~~ **DECIDED (2026-09-08, verified):** self-hosted ▣speaches (faster-whisper large-v3-turbo INT8) default; hosted GLM-ASR-2512 fallback on 8 GB boxes (needs transcode+slice, ≤30 s clips). Remaining sub-decision at Phase 4 start: the 10-clip noisy-audio bake-off now validates only the WER threshold, not the vendor.
2. Payment rail: Midtrans/Xendit (IDR-native) vs Stripe (international) — follow where first 5 clients bank.
3. Sales Core bundled-only (default) vs Inquiry purchasable alone.
4. Design partners: aim 1 per agent = 6 clients total across phases 3–5; recruit from the solar guy's trader network for Phase 5.
