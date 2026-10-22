# MJCX Trade Agent Appliance — Detailed System Flowchart
### Full Business Process Flow
### Plug-and-Play Modular AI Agent Platform — v2.0 (Sales Core · Growth Suite · Ops Suite)

**Version:** 2.0
**Date:** September 2026
**Status:** Working Document — For Internal Planning
**Prepared by:** MJCX Studio
**Based on:** v1.0 (August 2026) — preserved unchanged; this file supersedes it for planning.

**What changed v1 → v2 (read this first):**
1. **One brain-stem, named:** all traffic routes through ▣glue (OUR CODE) — deterministic
   gates → triage → overrides → generative paths, with digit/link guards on every reply.
   ▣dify hosts workflows + RAG; it no longer appears as the direct receiver of webhooks.
2. **chatwoot → OFF.** The staff inbox is the ▣console Threads page (v1.2 reality).
   chatwoot remains a documented rollback, not a drawn organ.
3. **Conversation core v2 is the live path** (CONVERSATION_CORE=v2 in .env;
code default remains v1 pending soak flip): one stateful tool-calling agent loop
   (glue/agent.py) over the organs; the v1 deterministic cascade is frozen rollback.
4. **The menu is the product:** agents are licensed modules on one appliance
   (Phase L: license file → entitlements → per-agent gates). Minimum plan =
   1 market-side + 1 ops-side agent, so the data loop spins.
5. **Six new phases:** M (Market Intel) · P (Positioning) · T (Meeting & Voice) ·
   K (Customer Knowledge) · S (SOP Guide) · U (Supplier & Procurement) — plus
   Phase L (Licensing & Billing, MJCX-side).
6. **New organs (all optional, client-paid):** ▣speaches, ▣cdio (changedetection.io),
   ▣rsshub, ▣rss-bridge. Deferred organs (twenty / erpnext / dolibarr / meetily)
   carry explicit re-entry triggers — see Component Map.
7. **Data stores extended:** S9–S12 + `customer_facts` (S3 ext) + `agent_state`
   (S4 ext). Every new store declared master-or-pointer per X1.

---

## Reading Guide

```
Notation:

  ╭─────────────────────╮
  │  Rounded rectangle   │  = Process / Action
  │  [TEAM]              │
  ╰─────────────────────╯

  ◇ Diamond shape         = Decision point

  ══► Arrow               = Flow direction

  ↩ Loop back             = Return to earlier step

  ● Data store            = Where data is read/written

  ⛔ Blocked / Never      = Cannot proceed until met · hard never-rule

  ⚠ Alert / Rule          = Business rule or system behavior

  ⊞ AGENT GATE            = Entitlement check — the license decides
                            ON/OFF before this box may run.
                            ⊞ on a ● Write line = write belongs to a
                            licensed add-on.

  ═══ CONNECTOR ═══       = Links between phases

  ▣ Component tag         = WHICH tool in the stack executes this box
                            — this is what makes the WEAVE visible

Teams (color-coded in labels):
  [BUYER]    = End customer abroad (WhatsApp / email / social DM)
  [AGENT]    = AI agent layer (glue pipeline + dify workflows) — acts autonomously
  [STAFF]    = Client's sales team (works the Console Threads inbox)
  [BOSS]     = Client's decision maker (approvals via WhatsApp + Console)
  [MJCX]     = Us — onboarding & maintenance
  [SYSTEM]   = Automated / system-generated
```

### Component Map — who executes what

```
╭────────────────────────────────────────────────────────────────────╮
│  THE APPLIANCE — ONE STACK PER CLIENT (single-tenant)              │
│                                                                    │
│  CORE (always present):                                            │
│  ▣ evo     = evolution-api       WhatsApp door in/out.             │
│  ▣ glue    = glue service        OUR CODE. THE BRAIN-STEM:         │
│                 deterministic gates, triage, overrides,            │
│                 reply guards (digits ⊆ facts ∪ thread; exact       │
│                 mode for quotes; link guard), channel handlers     │
│                 (WA webhook, IMAP/SMTP email), console API,        │
│                 escalation + mirror. LLM never passes unguarded.   │
│  ▣ dify    = dify                Workflow host: triage classifier, │
│                 spec-RAG (KB), prompt/DSL assets; GLM fallback.    │
│  ▣ calc    = calc engine         OUR CODE. Deterministic math on   │
│                 S2 rules. LLM never does arithmetic.               │
│  ▣ carbone = carbone-ee          PDF generation: quotes, PIs, POs. │
│  ▣ postiz  = postiz (headless)   Social engine; driven by glue     │
│                 via auth-header; OAuth callbacks land on console.  │
│ ▣ spine   = spine service       OUR CODE. SQLite S1–S8 ✅ (S2 file);│
│ S9–S12 📐 planned. Zero-auth by design — loopback only.             │
│  ▣ n8n     = n8n                 The clock: SLA ticks, B6 follow-  │
│ ups, X5 reports. (intel/PO clocks 📐 planned — ship with M/U).      │
│  ▣ console = console (React+Caddy) OUR CODE. Staff surface:        │
│                 Threads inbox + takeover, Quotes + approvals,      │
│                 Customers, Social, Events, Reports, Setup pages,   │
│ License page (Phase L 📐) + per-agent pages. Bearer token.          │
│                                                                    │
│  OPTIONAL ORGANS (ship with the agent that needs them):            │
│  ▣ speaches = faster-whisper     ASR: OpenAI-compatible /v1/       │
│                 audio/transcriptions. ogg/opus in-memory. ~1-2GB.  │
│  ▣ cdio     = changedetection.io Competitor price/page watches     │
│                 (CSS/JSONPath selectors) → webhook → glue.         │
│  ▣ rsshub   = RSSHub (no-Chromium profile) Trade-policy feeds      │
│                 (MOFCOM/PBC/Google News) → RSS.                    │
│ ▣ rss-bridge = RSS-Bridge       Feedless portal → RSS. ~50MB.      │
│  ▣ psrv     = MJCX-side scraper  Positioning ListingSource         │
│                 [OURS; runs ops/VPS, gated at glue /positioning/*] │
│                                                                    │
│  INTEGRATION TYPES:                                                │
│  ══[NATIVE]══  = built-in config, zero custom code                 │
│  ──[HTTP]───   = one API call, our glue code                       │
│  [OURS]        = MJCX-built service (the IP)                       │
│                                                                    │
│  DEFERRED ORGANS — verified weights, explicit re-entry triggers:   │
│  ▣ twenty    CRM: 2GB min + own PG/Redis. Enters ONLY as a         │
│              derived view behind a spine sync (client asks for     │
│              pipeline views; 16GB box). S3 stays master.           │
│  ▣ dolibarr  Light ERP: 1-2GB, REST supplier orders. Enters when   │
│              client needs formal supplier-invoice workflows.       │
│              Spine S12 stays master.                               │
│  ▣ erpnext   Heavy ERP: ~7 containers, 4-8GB. Enters only with     │
│              real inventory/PO volume + a dedicated box.           │
│  ▣ meetily   Desktop recorder (Tauri). Not a server organ.         │
│  ▣ LangBot   China-facing channel — separate SKU (tgo stack).      │
╰────────────────────────────────────────────────────────────────────╯
```

### Data Stores

```
╭────────────────────────────────────────────────────────────────────╮
│ DATA STORES [spine unless noted] — S1–S8 BUILT · v2 block PLANNED  │
│                                                                    │
│  S1 — Catalog Store  [OURS]                                        │
│         SKU, specs, MOQ, models, compatibility, certs, photos.     │
│         Raw catalog PDFs/Excel chunked into dify KB (derived).     │
│         One ingest feeds: inquiry answers, quoting, social,        │
│         positioning drafts (PROPOSED status from Phase P).         │
│                                                                    │
│  S2 — Pricing Rules Store  [OURS, versioned]                       │
│         Base prices, qty tiers, spec coefficients, process fees,   │
│         customer-tier terms, discount authority cap,               │
│         price_visibility, agent_policy (autonomy dial).            │
│         v2: gains COST fields (from S12) → calc computes margin.   │
│                                                                    │
│  S3 — Customer Identity Map  [OURS]                                │
│         JID/email/phone → customer_id. Country, language, tier,    │
│         notes. THE identity master; everything points here.        │
│         EXT v2 (PLANNED) — customer_facts: agent-written memory    │
│         (fact, source_message_id, ts, confidence). Extract-not-    │
│         infer; every row cites the message it came from.           │
│                                                                    │
│  S4 — Conversation Store  [spine tables, OURS]                     │
│         conversations + messages. Full transcripts (AI + human),   │
│         escalation tags, sla_beacon_at, agent_state (BUILT; v2 core│
│         memory — restart-proof). Console Threads reads this.       │
│                                                                    │
│  S5 — Quote Store  [OURS]                                          │
│         Versioned quotes: line items, computed price, margin,      │
│         validity, status machine, pdf_path (B4).                   │
│                                                                    │
│  S6 — Content Store  [spine + postiz pointer]                      │
│         Social drafts, approval state, schedule, postiz_id,        │
│         links, stats. Approvals: WhatsApp card AND Console.        │
│                                                                    │
│  S7 — Appliance Config  [git repo, OURS]                           │
│         Config-as-code: dify DSL exports, compose files, calc      │
│         config, per-client overrides, agent manifests              │
│         (agents/*.yml), intel feed lists, SOP docs.                │
│                                                                    │
│  S8 — Audit & Alert Log                                            │
│         Escalations, failures, session drops, price overrides,     │
│         gate runs, positioning analyses, license events.           │
│                                                                    │
│ v2 STORES (📐 PLANNED — not yet in spine):                          │
│  S9 — Intel Store [OURS]          intel_items: source, url,        │
│         title, summary_json, kind (news|tariff|price_watch).       │
│         Master for intelligence; feeds = S7 config.                │
│  S10 — Meetings Store [OURS]      meetings: transcript,            │
│         summary_json, action_items_json, audio_path (volume        │
│         pointer — same pattern as S5 pdf_path).                    │
│  S11 — SOP Runs Store [OURS]      sop_runs: staff, step, photo     │
│         path (prefix-validated), verdict_json. SOP docs = S7 git   │
│         + staff-only dify KB (derived). Never buyer-reachable.     │
│  S12 — Procurement Store [OURS]   suppliers, supplier_items        │
│         (capability + price pointers), purchase_orders (status     │
│         machine draft→approved→sent→confirmed→shipped→received).   │
│                                                                    │
│ L — License & Entitlements [signed file + S7] (PLANNED)            │
│         hs256-v1-signed JSON (Ed25519 = upgrade path):       │
│         trial?, expires_at. Gates EXECUTION, never DATA:           │
│         agent off → honest "not in plan"; spine untouched.         │
│                                                                    │
│  ⚠ X1 RULE: one source of truth per concept. Derived copies fine   │
│  (dify KB chunks, twenty view). Conflicting opinions are not.      │
│  Any new store declares master-or-pointer BEFORE entering.         │
╰────────────────────────────────────────────────────────────────────╯
```

---

## Table of Contents

1. Phase O: Onboarding (The Stamp) — one-time, MJCX-run
2. Phase A: Inquiry Intake & Triage — runtime (Sales Core)
3. Phase B: Quoting & Pricing — runtime (Sales Core)
4. Phase C: Social & Channel Ops — weekly (Growth add-on)
5. Phase M: Market Intelligence — daily clock (Growth add-on)
6. Phase P: Positioning & Catalog R&D — on demand (Growth add-on)
7. Phase T: Meeting & Voice Intelligence — runtime (Ops add-on)
8. Phase K: Customer Knowledge — runtime (Ops add-on)
9. Phase S: SOP & Process Guide — staff runtime (Ops add-on)
10. Phase U: Supplier & Procurement — per deal (Ops add-on)
11. Phase L: Licensing & Billing — MJCX-side lifecycle
12. Cross-Cutting: X1–X7

---

## 0. The One-Screen Version

```
  BUYER abroad                      CLIENT company                       MJCX
  ────────────                      ──────────────                       ────
                                            │
                  Phase O (once) ◄──────────┘
                  MJCX stamps appliance:
                  catalog in, rules in, QR scanned,
                  license dropped, agents ticked  ◄── [BOSS] picks from menu
                                            │
  WhatsApp msg ──► evo ──► GLUE ══[HTTP]══► dify (triage / spec-RAG)
                            │  │              └── GLM (parse/compose)
                            │  └── price ask? ──► calc (S2) ──► inline price
                            │                     └─ formal ──► carbone PDF
                            │                            ◄── same chat
                            ├── complex? ──► S4 ──► Console Threads takeover
                            │                  ◄── STAFF takeover reply
                            │
                            ├── voice note? ──► speaches ──► text ──► route()
                            ├── meeting? ────► speaches ──► S10 ──► follow-up draft
                            ├── market clock ► digest (S9) ──► BOSS WhatsApp
                            └── quote won? ──► S12 PO draft ──► BOSS approve ──► carbone

                  BOSS phone = approvals (WhatsApp) · STAFF screen = Console ·
                  MJCX = stamps, licenses, maintenance
```

---

## 1. Phase O: Onboarding — "The Stamp" (v2)

Target: **3–5 working days, one MJCX engineer.** Every hour past day 5 is a
product defect to fix in the kit, not billable work. This phase IS the product.

### O1. Appliance Provisioning + License

```
START
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O1-1. STAMP NEW INSTANCE FROM BLUEPRINT                           │
│  [MJCX → SYSTEM]                                                   │
│                                                                    │
│  From S7 (config-as-code repo):                                    │
│ - docker compose up: core organs (evo, glue, calc, spine, n8n,     │
│ carbone, postiz, console; dify = its own stack via DIFY_BASE_URL)  │
│  - Load dify workflow DSLs + prompts                               │
│ - Load carbone quote template (single branded docx; per-language   │
│ templates = roadmap) · point calc at this client's S2 rules file   │
│                                                                    │
│  ⚠ NOTHING HERE IS CLIENT-SPECIFIC EXCEPT CONFIG VALUES.           │
│  Hand-editing workflows per client = broken product.               │
│  Client variation lives in DATA (S1/S2/S3) + .env + LICENSE.       │
│                                                                    │
│  ● Read: S7 (blueprint)        ● Write: running instance           │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O1-2. DROP THE LICENSE  [MJCX]                        (Phase L)   │
│                                                                    │
│ Provisional license (plan pre-agreed w/ BOSS) via make_license.py  │
│  {appliance_id, client, agents[], trial?, expires_at}              │
│  dropped next to .env.                                             │
│                                                                    │
│  ⊞ From this moment every agent box in this document is            │
│  entitlement-gated: OFF agents return "not in your plan" —         │
│  honestly, and never touching data.                                │
│  No license found = everything on (back-compat + trial mode).      │
│                                                                    │
│  ● Write: L (license file)     ● Read: S8 (license event)          │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  Next → O2 (Catalog Ingest)
```

### O2. Catalog Ingest

```
╭────────────────────────────────────────────────────────────────────╮
│  O2-1. CLIENT HANDS OVER CATALOG                                   │
│  [MJCX]                                                            │
│                                                                    │
│  Reality: messy. Excel + PDF + photos + "ask the factory".         │
│  - Excel/CSV → structured rows → S1                                │
│  - PDFs → chunk → dify knowledge base (derived)                    │
│  - Photos → stored against SKU                                     │
│  - Gaps ("MOQ unknown for 12 SKUs") → GAP REPORT                   │
│                                                                    │
│  ⚠ THE GAP REPORT IS DELIVERABLE #1: exactly what the AI           │
│  will and won't know. No surprises.                                │
│                                                                    │
│  ● Write: S1 (+ dify KB derived)                                   │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O2-2. CATALOG VERIFICATION QUIZ (O2 gate)                         │
│  [SYSTEM → MJCX]                                                   │
│                                                                    │
│  Agent asks itself 20 questions against the KB.                    │
│                                                                    │
│  ◇ Pass ≥ 90% AND zero fabricated answers?                         │
│    YES → proceed   NO → fix chunks, re-run. ⛔ Blocked.             │
│                                                                    │
│  ● Read: S1                                                        │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  Next → O3 (Pricing Rules)
```

### O3. Pricing Rules Capture

```
╭────────────────────────────────────────────────────────────────────╮
│  O3-1. EXTRACT PRICING FROM "THE BOSS'S HEAD + EXCEL"              │
│  [MJCX + BOSS]                                                     │
│                                                                    │
│  Interview + sheets → S2 rules (versioned JSON, schema v3):        │
│  base prices · qty tiers · spec coefficients · tier terms ·        │
│  discount authority cap · price_visibility · autonomy policy       │
│                                                                    │
│  ● Write: S2                                                       │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O3-2. BACKTEST AGAINST HISTORY (O3 gate — THE go-live gate)       │
│  [MJCX]                                                            │
│                                                                    │
│  Client provides 10–20 REAL past quotes; calc re-computes.         │
│                                                                    │
│  ◇ Matches historical prices (± tolerance, target ≥90%)?           │
│    YES → rules trusted → proceed   NO → interview round 2. ⛔       │
│                                                                    │
│  ⚠ NEVER GO LIVE ON UNVERIFIED PRICING. One wrong price to a       │
│  real buyer destroys trust forever.                                │
│                                                                    │
│  ● Read: S2, historical quotes                                     │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  Next → O4 (Channels)
```

### O4. Channel Connect & Escalation Setup

```
╭────────────────────────────────────────────────────────────────────╮
│  O4-1. CONNECT CHANNELS                                            │
│  [MJCX + STAFF]                                                    │
│                                                                    │
│  Base: WhatsApp QR scan in evo (client's number) ·                 │
│        Email IMAP/SMTP creds → glue polling (shared inbox)         │
│  Add-ons: WeCom/WeChat → LangBot (separate SKU) ·                  │
│           website widget (roadmap)                                 │
│                                                                    │
│  ⚠ BAILEYS QR SESSIONS DROP. It's a when, not if. Client gets      │
│  the 1-page picture runbook (X2).                                  │
│                                                                    │
│  ● Write: S3 (initial customer import), S7 (channel config)        │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O4-2. ESCALATION RULES + GUARDRAILS                               │
│  [MJCX + BOSS]                                                     │
│                                                                    │
│  ALWAYS-HUMAN list (hardcoded, never AI-discretion):               │
│  ⛔ Payment terms negotiation      ⛔ Complaints & anger             │
│  ⛔ Legal / contract language      ⛔ Discounts beyond cap           │
│  ⛔ Anything below confidence threshold                             │
│                                                                    │
│  Brand voice: 5–10 client comms → voice guide (dify prompt).       │
│  Autonomy dial seeded: assistant / standard / closer               │
│  (S2 agent_policy — console toggle, hot-reload; gates pin          │
│  STANDARD at go-live).                                             │
│                                                                    │
│  ● Write: S7, dify prompts, S2 (agent_policy)                      │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  Next → O5 (Agent Activation)
```

### O5. Agent Activation — the menu (NEW in v2)

```
╭────────────────────────────────────────────────────────────────────╮
│  O5-1. PICK AGENTS FROM THE MENU                                   │
│  [BOSS] — with [MJCX] advising                                     │
│                                                                    │
│  From agents/*.yml manifests (status: available only):             │
│   MARKET-SIDE                       OPS-SIDE                       │
│   💬 Inquiry (Sales Core)           🤝 Customer Knowledge (K)        │
│   💰 Quoting (Sales Core)           📋 SOP & Process Guide (S)       │
│   📱 Social & Channels (C)          🎙 Meeting & Voice (T)           │
│   🌍 Market Intelligence (M)        🏭 Supplier & Procurement (U)    │
│   📊 Positioning (P)                📄 Doc-Gen bundle                │
│                                                                    │
│ ⚠ MINIMUM PLAN = Sales Core + ≥1 ops-side agent. Sales Core        │
│ counts as the market side; the loop must spin — capture demand,    │
│ act internally. That is what fills the spine.                      │
│                                                                    │
│  ● Write: S7 (entitlement list) → re-issue license (Phase L)       │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  O5-2. PER-AGENT DATA CHECKLIST + GATE                             │
│  [MJCX + SYSTEM]                                                   │
│                                                                    │
│  Each enabled agent runs its onboarding checklist (console,        │
│  GoLive-gate pattern), e.g.:                                       │
│   K → customer import exists       T → ASR profile picked          │
│   M → feed list + watch targets    S → first 3 SOPs ingested       │
│   U → first 5 suppliers + costs    P → first category brief        │
│                                                                    │
│  ◇ Agent's own gate suite green? (O2-quiz for KB, O3 for           │
│ pricing, O5-scenario-9 social test, Doc-Gen render test,           │
│    intel-digest test, ASR bake-off, K brief-cite test...)          │
│    YES → agent marked LIVE   NO → ⛔ that agent waits.              │
│  ⚠ No partial claims: an agent is sellable only when its gate      │
│  exists and is green. Roadmap ≠ menu.                              │
│                                                                    │
│  ● Write: S8 (gate records), L (activated agents)                  │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  Next → O6 (Acceptance Test)
```

### O6. Acceptance Test — the gate

```
╭────────────────────────────────────────────────────────────────────╮
│  O6-1. SCRIPTED SCENARIOS (test WhatsApp number)                   │
│  [MJCX]                                                            │
│                                                                    │
│  Base (always):                                                    │
│  1. Spec question EN → cited catalog answer                        │
│  2. Spec question ID/ZH → same, buyer's language                   │
│  3. Price ask, qty 100 → calc → inline price (digits exact)        │
│  4. Formal quote ask → carbone PDF arrives in chat                 │
│  5. Custom ODM → escalates w/ draft + summary (Console Threads)    │
│  6. "Your product exploded" → complaint path, human, fast          │
│  7. Discount push beyond cap → escalates                           │
│  8. Gibberish/spam → politely dropped (noise gate)                 │
│  9. QR drop drill → client re-scans via runbook                    │
│  ⊞ Per enabled agent — its scenario pack, e.g.:                    │
│   C:  draft → approve (WhatsApp card) → postiz scheduled           │
│   M:  digest arrives, every claim cites an intel_item id           │
│   T:  voice note → transcript → reply stays grounded               │
│   K:  brief cites only spine facts; invented fact rejected         │
│   S:  photo-verify rejects wrong-object photo                      │
│   U:  PO draft → approve → PDF → supplier message                  │
│                                                                    │
│  ◇ All pass? YES → GO LIVE   NO → fix, re-run. ⛔ No partials.      │
│                                                                    │
│  ● Write: S8 (acceptance record)                                   │
╰────────────────────────────────────────────────────────────────────╯

  ══════════════════════════════════════════════
  ═══ APPLIANCE LIVE — RUNTIME PHASES A→U ══════
  ══════════════════════════════════════════════
```

---

## 2. Phase A: Inquiry Intake & Triage (Sales Core)

Every inbound message from every channel walks this same path through ▣glue.

```
  INBOUND (WhatsApp via evo webhook / email via glue IMAP poll)
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A1-1. MESSAGE RECEIVED                                            │
│  [SYSTEM]  ▣evo / ▣glue                                            │
│                                                                    │
│  WhatsApp: evo webhook → glue. Email: glue polls IMAP, replies     │
│  via SMTP; pseudo-JID email:<addr> walks the SAME route().         │
│                                                                    │
│  ⚠ Idempotency: unique msg key; webhook retries dropped.           │
│  ⚠ MIRROR FIRST: every inbound/outbound line lands in S4           │
│  (best-effort, before routing) — staff always sees the thread.     │
│                                                                    │
│  ⊞ T0 (voice intake, Phase T enabled): voice note → ▣speaches      │
│  → text → continues below. Transcript saved to S4.                 │
│                                                                    │
│  ● Write: S4 (mirror)                                              │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A1-2. NOISE GATE (deterministic — no LLM)                         │
│  [SYSTEM]  ▣glue                                                   │
│                                                                    │
│  ≥4 chars and <50% alphabetic → polite silence. Keyboard mash      │
│  never reaches a human or burns a token.                           │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A2-1. WHO IS THIS? — IDENTITY RESOLUTION                          │
│  [SYSTEM]  ▣glue ──[HTTP]── ▣spine                                 │
│                                                                    │
│  Lookup JID/email in S3: known → load profile (country,            │
│  language, tier, past quotes S5, agent_state,                      │
│  ⊞ customer_facts if Phase K on). New → create, tier=new.          │
│                                                                    │
│  ⚠ S3 IS THE ONLY SOURCE OF TRUTH. Console/postiz store            │
│  POINTERS to S3 ids, never their own copies.                       │
│                                                                    │
│  ● Read/Write: S3                                                  │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A3-1. TRIAGE — v2 agent loop (default)                            │
│  [AGENT]  ▣glue (CONVERSATION_CORE=v2)                             │
│                                                                    │
│  ONE stateful loop (glm-4.5-air class, ≤4 tool rounds) over        │
│  the organs with EXACTLY these tools:                              │
│    catalog_lookup · list_models · kb_search · price_quote ·        │
│    escalate                                                        │
│  Memory: S4 last-20 turns + conversations.agent_state              │
│  (restart-proof).                                                  │
│                                                                    │
│  Deterministic pre-guards run BEFORE the loop: complaint filter,   │
│  spam filter, offer fulfillment ("yes please" / qty reply closes   │
│  the loop — no classifier re-run).                                 │
│                                                                    │
│  v1 cascade (classify→regex→RAG→compose) = FROZEN 30-second        │
│  rollback via CONVERSATION_CORE=v1.                                │
│                                                                    │
│  ◇ Paths out of the loop:                                          │
│    SPEC/other  → grounded answer or escalate                       │
│    PRICE_Q     → ══► Phase B                                       │
│    complaint / low confidence / unknown → A6 (always human)        │
│                                                                    │
│  ⚠ ADVISORY-CLASSIFIER MODE (v1 path): conf < 0.7 or unknown       │
│  intent ⇒ human. The classifier never decides money.               │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A4-1. REPLY GUARDS (every generative path, no exceptions)         │
│  [SYSTEM]  ▣glue                                                   │
│                                                                    │
│  Digit subset: reply numerals ⊆ tool facts ∪ buyer msg ∪ thread.   │
│  Digit exact (quotes): reply numbers == fact numbers.              │
│  Link guard: no URLs / attachment promises / 附件.                   │
│  Banned openings: regenerate if first 4 words repeat last bot      │
│  message. One repair round; fallback = raw tool card, never an     │
│  ungrounded goodbye.                                               │
│                                                                    │
│  ⚠ THE KB SAYS "I DON'T KNOW" BEAUTIFULLY, WITH A HUMAN            │
│  CALLBACK. A wrong spec answer is worse than no answer.            │
│                                                                    │
│  ● Write: S4 (answer logged), S8 (guard rejections)                │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  A6-1. ESCALATION WITH DRAFT                                       │
│  [AGENT → STAFF]  ▣glue ──► ▣spine S4 ──► ▣console Threads         │
│                                                                    │
│  What staff sees in Console:                                       │
│  - Full conversation (mirrored from S4)                            │
│  - ⊞ K-brief: who, what they want, open quotes, last sentiment,    │
│    suggested next step — every line cited to spine                 │
│  - DRAFT REPLY (buyer's language) — staff edits & sends            │
│  - If price-adjacent: calc's suggested number (margin STAFF-only)  │
│  - Priority: COMPLAINT > CUSTOM > LOW_CONFIDENCE                   │
│                                                                    │
│  Staff replies in Console → out via ▣evo on the buyer's channel.   │
│  Human outbound auto-clears the escalation tag (spine).            │
│                                                                    │
│  ⚠ SLA beacon: unanswered > SLA_HOURS → BOSS WhatsApp nudge,       │
│  once per conversation until handled (n8n → glue /a6/sla_tick).    │
│                                                                    │
│  ● Write: S4 (human reply), S3 (notes), S8 (event)                 │
│  ⊞ Write: customer_facts (Phase K memory capture, extract-only)    │
╰────────────────────────────────────────────────────────────────────╯

  ↩ Loop: every subsequent buyer message re-enters at A1 with full
    context from S3/S4 (+facts). Restart-safe (agent_state).
```

---

## 3. Phase B: Quoting & Pricing (Sales Core)

"Accurate quotes in seconds, not hours." The LLM never does the math.

```
  PRICE_Q (from A3, or forced by thread continuation)
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  B1-1. PARSE REQUIREMENTS                                          │
│  [AGENT]  ▣glue + GLM (closed vocab from S2)                       │
│                                                                    │
│  Extract: product/model, qty, options, destination, incoterm,      │
│  language. Missing essentials → ONE clarifying question.           │
│  ⊞ Autonomy dial: assistant → PRICE_Q goes straight to A6          │
│  (honest holding line + human quote). standard/closer → below.     │
│                                                                    │
│  ● Write: S5 (draft quote)                                         │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  ◇ B1-2. COMPUTABLE FROM RULES?
  │
  ├── YES ──► B2                    └── NO (custom/ODM/gap) ──► B5
  │       ⚠ ZERO discretion: if S2 lacks the rule, it is a human
  │       quote. Period. Internal-only materials never reach calc.
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  B2-1. CALCULATOR COMPUTES (deterministic)                         │
│  [SYSTEM]  ▣glue ──[HTTP]── ▣calc ──● S2                           │
│                                                                    │
│  unit = (base × size_coef + Σ fees) × tier_factor                  │
│  total = Σ(unit×qty) × (1 − qty_discount)                          │
│  Gap (unknown material/tier/coef 0) → NotComputable → ESCALATE     │
│  with gaps list → B5.                                              │
│                                                                    │
│  ⚠ LLM READS RULES, CODE DOES ARITHMETIC. This box is our IP       │
│ and our quality guarantee. Margin STAFF-only (⊞ real margin = U).  │
│                                                                    │
│  ● Read: S2, S3 (tier)   ● Write: S5 (computed, saved)             │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
  ◇ B3-1. INLINE OR FORMAL?
  ├── simple ──► B3-2 INLINE PRICE (guarded exact digits, validity
  │              date appended structurally) ▣evo
  └── formal / big qty / distributor ──► B4
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  B4-1/2. RENDER + DELIVER PDF IN THE SAME CHAT                     │
│  [SYSTEM]  ▣glue ──[HTTP]── ▣carbone ──► ▣evo                      │
│                                                                    │
│  Template per buyer language + JSON from S5/S3/S1 → branded,       │
│  numbered, valid-until PDF → lands in the buyer's thread.          │
│                                                                    │
│  ● Write: S5 (version + pdf_path)                                  │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  B5-1. HUMAN QUOTE PATH (custom/ODM)                               │
│  [AGENT → STAFF/BOSS]  ▣console Threads                            │
│                                                                    │
│  A6 package + structured requirement sheet + RULES-GAP HINT        │
│  (what S2 needs to make this computable next time).                │
│  ⚠ Every human quote is a rules-improvement opportunity.           │
│  Month over month, escalations shrink.                             │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  B6-1. QUOTE FOLLOW-UP LOOP                                        │
│  [SYSTEM]  ▣n8n cron → ▣glue /b6/tick                              │
│                                                                    │
│  Sent quotes, no reply in 48h → guarded follow-up DRAFT →          │
│  approval where the approver lives: WhatsApp APPROVE card or       │
│  Console Quotes panel (same handler, idempotent).                  │
│  Negotiation → within cap: calc re-computes, new version.          │
│  Beyond cap → escalate w/ floor-price context.                     │
│  Accepted → 🎉 record win → ⊞ next-step offer: PI/contract via      │
│  Doc-Gen bundle (carbone) → ⊞ U: PO drafting to supplier (S12).    │
│                                                                    │
│  ● Read/Write: S5 (status machine), S8                             │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 4. Phase C: Social & Channel Ops (Growth add-on) ⊞

```
  WEEKLY CRON ▣n8n → ▣glue /c/draft_tick
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  C1/C2. PLAN + DRAFT                                               │
│  [AGENT]  ▣glue + GLM ──● S1, S6                                   │
│                                                                    │
│  Content plan from catalog + season + last week's stats →          │
│  drafts in brand voice, per-platform variants, images from S1.     │
│  ⊞ P feed: approved positioning memos inject angle ideas.          │
│                                                                    │
│  ● Write: S6 (PENDING_APPROVAL)                                    │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  C3. APPROVAL — always human in v2                                 │
│  [BOSS]  WhatsApp card and/or Console Social page                  │
│                                                                    │
│  ⚠ NO AUTO-PUBLISH. One bad post costs more than a year of         │
│  scheduler fees. Config flag for clients who EARN it later.        │
│                                                                    │
│  ● Write: S6 (APPROVED / EDITED / REJECTED)                        │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  C4/C5. SCHEDULE, PUBLISH, FUNNEL                                  │
│  [SYSTEM]  ▣glue ──[HTTP]── ▣postiz (headless, auth-header)        │
│                                                                    │
│  Channels connected headlessly from Console (OAuth callbacks       │
│  land on Console /integrations/social/:provider → glue →           │
│  postiz; state-validated, 5-min TTL).                              │
│  Buying-intent comments/DMs → routed into Phase A (same agent,     │
│  same catalog). CTA on every post → WhatsApp deep link.            │
│                                                                    │
│  ● Write: S6 (published + stats), S3 (lead source=social), S4      │
╰────────────────────────────────────────────────────────────────────╯

  ↩ Loop: weekly, stats feed next C1.
```

---

## 5. Phase M: Market Intelligence (Growth add-on) ⊞ NEW

Organs: ▣rsshub (no-Chromium) · ▣rss-bridge · native Google-News RSS ·
▣cdio for watches. Digest composer is ▣glue [OURS] — X5-send pattern.

```
  DAILY CRON ▣n8n → ▣glue /intel/digest
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  M1-1. COLLECT                                                     │
│  [SYSTEM]  ▣rsshub / ▣rss-bridge / native RSS / ▣cdio webhooks     │
│                                                                    │
│  Client's feed list (S7 config): trade ministries (MOFCOM/PBC/     │
│  customs — where routes are clean), Google News category feeds,    │
│  tariff/policy pages via rss-bridge, competitor watches via        │
│  changedetection.io (CSS/JSONPath selectors incl. JSON prices,     │
│  webhook → glue on change).                                        │
│                                                                    │
│  ⚠ No-Chromium profile on the appliance box. Customs routes        │
│  needing Playwright/China-IP run MJCX-side, never client-side.     │
│                                                                    │
│  ● Write: S9 intel_items (raw, kind-tagged)                        │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  M2-1. COMPOSE THE DIGEST                                          │
│  [AGENT]  ▣glue + GLM                                              │
│                                                                    │
│  New S9 items → categorized summary in boss's language.            │
│  ⚠ GATE: every claim MUST cite intel_item ids. No synthesized      │
│  news. Price-watch alerts echo observed value + URL verbatim.      │
│                                                                    │
│  ● Read: S9   ● Write: S9 (digest record), S8                      │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  M3-1. DELIVER                                                     │
│  [SYSTEM]  ▣glue → ▣evo → BOSS WhatsApp + Console IntelPage        │
│  Urgent price-watch hits → immediate alert, not next digest.       │
│  ↩ Weekly: digest engagement + watch hits tune the feed list (S7). │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 6. Phase P: Positioning & Catalog R&D (Growth add-on) ⊞ NEW

Data acquisition: scraping-first (owner decision 2026-09-08). Connector is
pluggable — gray-area today, clean pipe (Keepa/manual) swappable later.

```
  [BOSS/STAFF] picks a category in Console → ▣glue /positioning/analyze
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  P1-1. COLLECT LISTINGS                                            │
│  [SYSTEM]  ▣scraper connector (OURS, pluggable ListingSource)      │
│                                                                    │
│  alibaba/1688 headless scrape (rate-limited, cached, snapshot      │
│  kept) · manual paste fallback · keepa_api slot (clean pipe,       │
│  when a client pays for legitimacy).                               │
│                                                                    │
│  ⚠ Runs from MJCX ops/VPS, never the appliance box IP. Selector    │
│  rot is accepted maintenance. CI tests use frozen fixtures only.   │
│                                                                    │
│ ● X1: snapshots/memos = file masters, S8 = pointer (no new store)  │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  P2-1. ANALYZE                                                     │
│  [AGENT]  ▣glue + GLM                                              │
│                                                                    │
│  Structured extraction: price bands, winner feature language,      │
│  review-complaint clusters (= product-opportunity list), gaps.     │
│  ⚠ GATE: memo claims cite listing ids from the fetched set.        │
│                                                                    │
│  ● Read: snapshots   ● Write: positioning memo + S8                │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭─────────────────────────────────────────────────────────────────────╮
│  P3-1. DRAFT → APPROVE → CATALOG                                    │
│  [AGENT → STAFF]                                                    │
│                                                                     │
│  Suggested bundles + draft S1 items (status PROPOSED) → staff       │
│  approve (S6-style flow) → live in S1 → instantly sellable via      │
│ Phase A/B; ⊞ content angles → C1 (needs C; else stops at S1 drafts).│
│                                                                     │
│  ● Write: S1 (PROPOSED→live), S6 (content hooks), S8                │
╰─────────────────────────────────────────────────────────────────────╯

  ⚠ This phase is the "find me a new market" answer: the appliance
  turns a supplier network + a category hunch into catalog, content,
  and quotes — with human approval at the gate.
```

---

## 7. Phase T: Meeting & Voice Intelligence (Ops add-on) ⊞ NEW

Organ: ▣speaches (faster-whisper turbo INT8, ogg in-memory) · fallback
GLM-ASR on 8GB boxes (glue transcodes + slices ≤30s). Summarize = GLM [OURS].

```
  T0 (cross-cutting into A1): inbound voice notes → ▣speaches → text
      → walks Phase A. Transcript to S4. Buyer language preserved.
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  T1-1. MEETING IN                                                  │
│  [STAFF]  Console upload (recording / WA voice notes)              │
│  ──► ▣glue /meetings ──► ▣speaches ──[HTTP] transcript             │
│  ⚠ GATE: 10-clip CN/EN noisy-audio bake-off (WER threshold) must   │
│  be green before extraction is trusted.                            │
│  ● Write: S10 meetings (transcript, audio_path volume pointer)     │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  T1-2. SUMMARIZE + ACTION ITEMS                                    │
│  [AGENT]  ▣glue + GLM (agent_core contract)                        │
│                                                                    │
│  Structured: attendees, decisions, commitments, dates.             │
│  ⚠ GATE: every action item cites transcript spans. No invented     │
│  commitments (O2 philosophy).                                      │
│  ● Write: S10 (summary_json, action_items_json)                    │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  T1-3. FOLLOW-THROUGH                                              │
│  [SYSTEM → STAFF]  action items → S8 events; follow-up drafts      │
│  land in the B6 approval flow (Approve & send via WA/Console).     │
│  ⊞ K: meeting facts about a known customer also append to          │
│  customer_facts (cited to the meeting, not a chat message).        │
│  ● Write: S8, B6 drafts, customer_facts                            │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 8. Phase K: Customer Knowledge (Ops add-on) ⊞ NEW

No new organ. Pure spine reads + guarded writes. The CRM that remembers.

```
  K1. 360° PROFILE (Console)
      S3 identity + S4 timeline + S5 quotes + S8 events +
      customer_facts → one page per customer. [STAFF/BOSS]
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  K2-1. PRE-TAKEOVER BRIEF                                          │
│  [SYSTEM]  ▣glue /console/customers/{id}/brief                     │
│                                                                    │
│  Staff opens a thread (or escalation fires) → one cited            │
│  paragraph: who they are, what they want, open quotes, last        │
│  sentiment, suggested next step.                                   │
│  ⚠ GATE: brief may cite ONLY retrieved spine rows. No synthesis.   │
│  ● Read: S3/S4/S5/S8/facts   ● Write: S4 (brief note)              │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  K3-1. AGENT MEMORY WRITES (the loop closes)                       │
│  [AGENT]  ▣glue, after each v2 conversation turn                   │
│                                                                    │
│  Durable buyer facts (preferences, stated terms, constraints,      │
│  volunteered personal details) → customer_facts rows, each         │
│  citing its message_id. Extract-NOT-infer. Duplicates merge.       │
│  Staff leave → knowledge stays. Any teammate gets full context.    │
│                                                                    │
│  ⚠ Buyer NEVER sees facts. Staff/BOSS do (X4).                     │
│  ● Write: customer_facts   ● Read back: A2 profile load, K2 brief  │
╰────────────────────────────────────────────────────────────────────╯

  ↩ The memory loop: conversations write facts; facts enrich the
  next conversation. This is the retention moat — leaving the
  platform means erasing the company's memory.
```

---

## 9. Phase S: SOP & Process Guide (Ops add-on) ⊞ NEW

No new organ. KB + quiz engine + photo-verify composed. Staff-only by construction.

```
  SG1. AUTHOR: SOPs as structured markdown (trigger, steps, expectation
      prompts, photos) — S7 git per client → staff-only dify dataset.
      ⚠ NEVER mixed with the buyer KB: internal pricing must be
      unreachable from buyer-facing route() (leak gate in tests).
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  SG2-1. RUNNER (Console)                                           │
│  [STAFF]  pick SOP → step-by-step → photo checkpoints              │
│  Photo upload → glue /sop/verify (path prefix-validated — closes   │
│  the M1 file-read class properly) → GLM vision pass/fail against   │
│  the step's expectation → verdict audited.                         │
│  ⚠ GATE: adversarial test — wrong-object photo MUST fail.          │
│  ● Write: S11 sop_runs, S8                                         │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  SG3-1. ASK + QUIZ                                                 │
│  [AGENT/STAFF]  "How do we handle a bank-detail change?" →         │
│  RAG answer citing SOP + step. New-hire mode: O2-quiz engine       │
│  over the SOP dataset (0 fabricated steps required).               │
│  ● Read: SOP dataset   ● Write: S8 (quiz results)                  │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 10. Phase U: Supplier & Procurement (Ops add-on) ⊞ NEW

Build-ours on spine S12. erpnext/dolibarr deferred with triggers (Component Map).

```
  WIN in S5 (B6 accepted) or restock need
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  U1-1. DRAFT THE PO                                                │
│  [AGENT → BOSS]  ▣glue /procure/draft                              │
│                                                                    │
│  GLM proposes supplier split from S12 (capability notes, lead      │
│  times, price pointers) → PO draft → BOSS approves (B6 pattern,    │
│  WhatsApp card or Console). NEVER auto-send in v2.                 │
│  Approved → PO PDF via ▣carbone → emailed/WhatsApp'd to supplier.  │
│                                                                    │
│  ● Read: S12, S5   ● Write: S12 purchase_orders, S8                │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  U2-1. TRACK + COMPARE                                             │
│  [SYSTEM/STAFF]                                                    │
│  Status machine: draft→approved→sent→confirmed→shipped→received.   │
│  ▣n8n age check: PO older than promised lead time → BOSS beacon    │
│  (A6 pattern). Comparison view: same lines across suppliers,       │
│  landed-cost columns.                                              │
│  ● Read/Write: S12   ● Write: S8 (delay events)                    │
╰────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭────────────────────────────────────────────────────────────────────╮
│  U3-1. CLOSE THE MARGIN LOOP (the quiet payoff)                    │
│  Supplier real costs → S2 cost fields → ▣calc computes MARGIN      │
│  internally → B2 quotes show true margin (STAFF-only) → X5         │
│  reports real margin per quote. Closes the HANDOFF scope item.     │
│  ● Write: S2 (costs, versioned)   ● Read: calc                     │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 11. Phase L: Licensing & Billing (MJCX-side) — NEW

```
  [BOSS] picks plan (O5) ──► [MJCX] invoice + wire ──► make_license.py
  │
  ▼
╭─────────────────────────────────────────────────────────────────────╮
│  L1-1. ISSUE                                                        │
│  Ed25519-sign {appliance_id, client, agents[], trial?,              │
│  expires_at} → license.json dropped at deploy.                      │
│  ⊞ Glue middleware: /console/* + agent routes check L;              │
│  console hides nav; OFF = honest "not in your plan".                │
│  ● Write: L   ● Write: S8 (license_issued)                          │
╰─────────────────────────────────────────────────────────────────────╯
  │
  ▼
╭─────────────────────────────────────────────────────────────────────╮
│  L2-1. RENEW / EXPAND / EXPIRE                                      │
│  T-14d and T-7d: console banner + BOSS WhatsApp nudge (beacon       │
│  pattern). Expand = re-issue with more agents (no downtime;         │
│ data was always there). Expire OR deleted-file-post-issuance =      │
│ agents gate OFF, spine intact. Grace 7d. Payment links (Phase 2+:   │
│  of the platform plan; hosted portal only past ~10 clients.         │
│  ● Write: L, S8                                                     │
╰─────────────────────────────────────────────────────────────────────╯

  ⚠ THE RETENTION MECHANIC: execution gates, data never. Six months
  of spine = transcripts, facts, quote history. Churning = erasing
  the company's memory. Say this in every renewal call.
```

---

## 12. Cross-Cutting

### X1. The Spine — data ownership rules (updated)

```
╭────────────────────────────────────────────────────────────────────╮
│  ONE SOURCE OF TRUTH PER CONCEPT  [spine — OURS]                   │
│                                                                    │
│  Customer identity  → S3 (+customer_facts ext; twenty = pointer)   │
│  Product facts      → S1 (structured) + dify KB (derived)          │
│  Price math         → S2 + calc (nobody else computes)             │
│  Quote record       → S5 (console/evo reference quote_id)          │
│  Conversations      → S4 spine tables (console = view)             │
│  Intel/Meetings/SOP-runs/Procurement → S9/S10/S11/S12              │
│                                                                    │
│  ⚠ Derived copies fine. Conflicting opinions not. Every new        │
│  store declares master-or-pointer before entering the stack.       │
╰────────────────────────────────────────────────────────────────────╯
```

### X2. Session Health & Runbook

```
╭─────────────────────────────────────────────────────────────────────╮
│  FAILURE MODES — known, boring, documented                          │
│  QR drop (baileys): evo alert → client picture runbook <5 min.      │
│  LLM outage: dify fallback chain → all-down = holding replies +     │
│    route human (graceful dumb mode). Never silence to buyers.       │
│  calc/carbone down: quoting degrades to escalation; inquiry         │
│    answering unaffected.                                            │
│  speaches down: voice notes queue + text-only notice (T0 off).      │
│  Webhook storms: idempotency keys.                                  │
│  License expiry: 14d/7d beacons → grace → agents gate OFF           │
│    (data intact); renew = re-issue file, zero downtime.             │
│  Daily 07:00: n8n health digest to MJCX (not client).               │
│  ● Write: S8                                                        │
╰─────────────────────────────────────────────────────────────────────╯
```

### X3. Notifications (updated)

```
┌────────────────────────────────┬─────────┬─────────────────────┐
│ Trigger                        │ Who     │ Where                │
├────────────────────────────────┼─────────┼─────────────────────┤
│ Escalated inquiry created      │ STAFF   │ Console + email      │
│ Escalation unanswered > SLA    │ BOSS    │ WhatsApp             │
│ Complaint detected             │ STAFF+  │ Console PRIORITY     │
│ Quote sent / accepted          │ STAFF   │ Console + WhatsApp   │
│ Discount beyond cap requested  │ BOSS    │ WhatsApp w/ context  │
│ Social drafts ready            │ BOSS    │ WhatsApp + Console   │
│ WhatsApp session dropped       │ STAFF   │ WhatsApp + runbook   │
│ ⊞ Intel digest (daily/weekly)  │ BOSS    │ WhatsApp + Console   │
│ ⊞ Price-watch hit              │ BOSS    │ WhatsApp immediate   │
│ ⊞ PO delayed vs lead time      │ BOSS    │ WhatsApp             │
│ ⊞ Meeting action items ready   │ STAFF   │ Console (B6 flow)    │
│ B6 follow-up drafts ready      │ STAFF+  │ WA + Console         │
│ ⊞ PO draft ready               │ BOSS    │ WhatsApp + Console   │
│ ⊞ Positioning drafts ready     │ STAFF   │ Console              │
│ ⊞ License expiring (T-14/T-7)  │ BOSS+MJCX │ Console+WhatsApp   │
│ Any service down > 5 min       │ MJCX    │ MJCX channel         │
│ Weekly summary (Fri)           │ BOSS    │ WhatsApp digest      │
└────────────────────────────────┴─────────┴─────────────────────┘
```

### X4. Data Visibility — per role (updated)

```
  BUYER:  catalog answers, their quotes, their thread.
          ⛔ Never: margins, facts, other customers, SOP content.
  STAFF:  Console — all conversations, drafts, margin, customer
          history + facts, SOPs, meeting notes.
          ⛔ Never: rule editing, license management.
  BOSS:   everything staff sees + S2 rules, discount/social/PO
          approvals, intel digests, reports, license page (Phase L 📐).
  MJCX:   infrastructure + logs (S7/S8) + license issuance.
          ⛔ Pricing access limited to the O3 capture/backtest window.
```

### X5. Monthly Client Report (the retention artifact)

```
  Auto-generated (spine /reports/x5) → BOSS WhatsApp:
  - Inquiries: total, AI vs escalated, median response time
  - Quotes: sent, accepted, win rate, avg margin (⊆ once U ships)
  - Top asked products (→ content & stock insight)
  - Unanswerable questions (→ catalog gap report)
  - Escalation reasons (→ rules-gap opportunities)
  - ⊞ Growth/Ops add-ons: intel highlights, PO performance,
    meeting-to-action conversion
  ⚠ This report is why clients renew.
```

### X6. Entitlements & Agent Manifests (NEW)

```
╭──────────────────────────────────────────────────────────────────╮
│  AGENTS/*.YML (S7) — one manifest per agent:                        │
│    id · name(en/zh) · tier(market|ops) · routes (glue prefixes)     │
│    · pipeline_hooks (where in route()) · data (stores touched)      │
│    · gates (its test suite) · status: available | roadmap           │
│                                                                     │
│  RULES:                                                             │
│  - Execution gated, data never. OFF agent = honest refusal.         │
│  - No license BEFORE first issuance = trial (all on). After
    issuance, a missing/deleted file = EXPIRED (grace), not trial —
    last-known entitlement persisted in S8 keyed to appliance_id.         │
│  - roadmap agents are NEVER sold. Menu ≠ promises.                  │
│  - Self-hosted DRM is intentionally soft (signed file, not a        │
│    fortress). The real lock is the data moat.                       │
╰──────────────────────────────────────────────────────────────────╯
```

### X7. Appliance Profiles (NEW)

```
  BASE (today):        core organs only                    ~5 GB
  8 GB BOX:            + cdio, rss-bridge; ASR = GLM-ASR    ~5.5 GB
  16 GB BOX:           + all four organs + speaches INT8    ~7.5 GB
  Choose at O1; ASR and intel organs are license-tied anyway.
```

---

## Summary: Process Count

| Section | Steps | Decision Points | Loops | Human Touchpoints |
|---|---|---|---|---|
| Phase O: Onboarding | 11 | 4 (gates) | 1 (pricing interview) | MJCX + client ~3h total |
| Phase A: Inquiry Triage | 6 | 1 | 1 (per message) | STAFF only on escalation |
| Phase B: Quoting | 5 | 2 | 1 (follow-up) | STAFF on custom/beyond-cap |
| Phase C: Social ⊞ | 3 | 1 | 1 (weekly) | BOSS approval |
| Phase M: Market Intel ⊞ | 3 | 0 | 1 (daily) | none (read-only intel) |
| Phase P: Positioning ⊞ | 3 | 1 | 1 (per category) | STAFF approve S1 drafts |
| Phase T: Meeting ⊞ | 3 | 1 (bake-off gate) | 1 (per meeting) | STAFF approve follow-ups |
| Phase K: Customer Knowledge ⊞ | 2 | 0 | 1 (memory loop) | none (writes are cited) |
| Phase S: SOP ⊞ | 2 | 1 (photo verify) | 1 (per run) | STAFF executes |
| Phase U: Procurement ⊞ | 3 | 1 | 1 (PO lifecycle) | BOSS approves POs |
| Phase L: Licensing | 2 | 1 (expiry) | 1 (renewal) | BOSS pays; MJCX issues |
| Cross-Cutting | 7 blocks | 0 | 1 (health digest) | — |
| **TOTAL** | **~43 boxes (+7 X-blocks)** | **~15** | **~12** | **2–4 approval points in steady state** |

Steady state per enabled-agent set: STAFF touches the Console (threads with
briefs, approvals); BOSS touches WhatsApp cards; everything else runs itself.

---

## Scope Notes — For Proposal (v2)

### Base Platform (always included)

- Stamp + license + host box sizing (X7); spine S1–S8; Console (Threads
  inbox + takeover, quotes, events, reports, setup pages); WhatsApp + email
  channels; escalation w/ drafts + SLA beacons; conversation core v2
  (+ frozen v1 rollback); X5 monthly report; session health + runbooks;
  MJCX maintenance window.

### Sales Core (flagship SKU)

- Phase A + Phase B: inquiry auto-response (CN/EN/ID + buyer language),
  deterministic quoting, inline prices, carbone PDF quotes, follow-up loop.
- Positioning line: *"The quoting appliance that never guesses a number."*
- Plan rule: Sales Core counts as the market-side; a minimum plan =
  Sales Core + ≥1 ops-side add-on (Customer Knowledge recommended first).

### Add-On Modules (separate SKUs; minimum plan = 1 market + 1 ops)

- 📱 Social & Channels (C) · 🌍 Market Intelligence (M) · 📊 Positioning (P)
- 🤝 Customer Knowledge (K) · 📋 SOP Guide (S) · 🎙 Meeting & Voice (T)
- 🏭 Supplier & Procurement (U) · 📄 Doc-Gen bundle (PI, contract, packing list)
- WeCom/WeChat channel (LangBot) — China-facing, separate product line

### Deferred (re-entry triggers in Component Map)

- twenty (CRM views) · dolibarr (supplier invoices) · erpnext (inventory/PO
  volume) · meetily (desktop companion) · auto-publish social · tgo China
  full stack · multi-tenant hosting

---

*MJCX Studio — Building Products that Actually Ship*
*Companion documents: docs/modular-agent-platform-plan.md (build + pricing plan),
docs/architecture-report-2026-09-08.md (verified architecture audit).*
