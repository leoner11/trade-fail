# MJCX Trade Agent Appliance — Detailed System Flowchart
### Full Business Process Flow
### Plug-and-Play AI Agent Product Line — v1 (Inquiry · Quoting · Social)

**Version:** 1.0
**Date:** August 2026
**Status:** Working Document — For Internal Planning
**Prepared by:** MJCX Studio

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

  ⛔ Blocked              = Cannot proceed until condition met

  ⚠ Alert / Rule          = Business rule or system behavior

  ═══ CONNECTOR ═══       = Links between phases

  ▣ Component tag         = WHICH tool in the stack executes this box
                            (dify / evo / chatwoot / carbone / postiz / calc / spine / n8n)
                            — this is what makes the WEAVE visible

Teams color-coded in labels:
  [BUYER]    = End customer abroad (WhatsApp / email / social DM)
  [AGENT]    = AI agent layer (dify workflows) — acts autonomously
  [STAFF]    = Client's sales team (works in chatwoot inbox)
  [BOSS]     = Client's decision maker (approvals via WhatsApp)
  [MJCX]     = Us — onboarding & maintenance
  [SYSTEM]   = Automated / system-generated
```

### Component Map — who executes what

```
╭──────────────────────────────────────────────────────────────╮
│  THE APPLIANCE — ONE STACK PER CLIENT (single-tenant)         │
│                                                              │
│  ▣ evo     = evolution-api      WhatsApp door in/out.         │
│              NATIVE config-screen links to dify + chatwoot.   │
│  ▣ dify    = dify                The brain: workflows, RAG,   │
│              agent logic, language handling.                  │
│  ▣ chatwoot= chatwoot            Human inbox for escalated    │
│              conversations. Community edition.                │
│  ▣ calc    = pricing-calculator  OUR CODE. Deterministic      │
│              math on pricing rules. LLM never does arithmetic.│
│  ▣ carbone = carbone             PDF generation: quotes, PIs. │
│  ▣ postiz  = postiz              Social scheduling/publishing.│
│  ▣ spine   = spine service       OUR CODE. Catalog + pricing  │
│              rules + customer identity map. Source of truth.  │
│  ▣ n8n     = n8n                 Glue: email polling, crons,  │
│              digests, webhooks routing.                       │
│                                                              │
│  INTEGRATION TYPES:                                          │
│  ══[NATIVE]══  = built-in config screen, zero custom code     │
│  ──[HTTP]───   = one API call, our glue code                  │
│  [OURS]         = MJCX-built service (the IP)                 │
│                                                              │
│  NOT IN V1: erpnext (enters when client needs real POs /      │
│  inventory), twenty (enters when client needs CRM views),     │
│  tgo/LangBot (China-facing stack, separate SKU), meetily.     │
╰──────────────────────────────────────────────────────────────╯
```

### Data Stores

```
╭──────────────────────────────────────────────────────────────╮
│  DATA STORES — COMPLETE LIST                                  │
│                                                              │
│  S1 — Catalog Store  [spine, OURS]                           │
│         Structured product data: SKU, specs, MOQ, models,     │
│         compatibility, certs, photos. PLUS the raw catalog    │
│         PDFs/Excel chunked as RAG documents inside dify KB.   │
│         One ingest feeds: inquiry answers, quoting, social.   │
│                                                              │
│  S2 — Pricing Rules Store  [spine, OURS]                     │
│         pricing_rules.md per client — base prices, qty        │
│         tiers, spec coefficients, process fees, customer-tier │
│         terms, discount authority caps. Seeded from the       │
│         email-quote-automation schema. Version controlled.    │
│                                                              │
│  S3 — Customer Identity Map  [spine, OURS]                   │
│         THE source of truth for who a customer is.            │
│         Key: phone/email/WhatsApp JID → customer_id.          │
│         Country, language, tier, first-seen, notes.           │
│         chatwoot/evo store POINTERS to S3 ids, never their    │
│         own conflicting copies.                              │
│                                                              │
│  S4 — Conversation Store  [chatwoot + dify logs]             │
│         Full transcripts: AI-answered + human-answered.       │
│         Searchable by customer, topic, outcome.               │
│                                                              │
│  S5 — Quote Store  [spine, OURS]                             │
│         Every quote: version, line items, computed price,     │
│         margin, expiry, status (sent/viewed/accepted/         │
│         rejected/negotiating), PDF link.                      │
│                                                              │
│  S6 — Content Store  [postiz + approval queue]               │
│         Social drafts, approval state, publish schedule,      │
│         post links, performance stats.                       │
│                                                              │
│  S7 — Appliance Config  [git repo, OURS]                     │
│         Config-as-code: dify workflow DSL exports, compose    │
│         files, calculator config, per-client overrides.       │
│         THIS is what makes client #7 a stamp, not a project.  │
│                                                              │
│  S8 — Audit & Alert Log                                      │
│         Every escalation, failure, session drop, price        │
│         override. Feeds the monthly client report.            │
╰──────────────────────────────────────────────────────────────╯
```

---

## Table of Contents

1. Phase O: Onboarding (The Stamp) — one-time, MJCX-run
2. Phase A: Inquiry Intake & Triage — runtime
3. Phase B: Quoting & Pricing — runtime
4. Phase C: Social & Channel Ops — weekly cadence
5. Cross-Cutting: Escalation rules, session health, notifications, reporting, data visibility

---

## 0. The One-Screen Version

```
  BUYER abroad                         CLIENT company                    MJCX
  ────────────                         ──────────────                    ────
                                           │
                    Phase O (once) ◄───────┘
                    MJCX stamps appliance:
                    catalog in, rules in, WhatsApp QR
                                           │
  WhatsApp msg ──► evo ══[NATIVE]══► dify ──► answer from S1 (catalog)
                        │                   │
                        │                   ├── price ask? ──► calc (S2) ──► inline price
                        │                   │                    └─ formal ──► carbone PDF
                        │                   │                         ◄── back in same chat
                        │                   └── complex? ──► chatwoot ◄── STAFF replies
                        │                                       (draft + summary waiting)
                        │
                    dify cron ──► social drafts ──► BOSS approves ──► postiz publishes
```

---

## 1. Phase O: Onboarding — "The Stamp"

Target: **3–5 working days, one MJCX engineer.** Every hour past day 5 is a
product defect to fix in the kit, not billable work. This phase IS the product.

### O1. Appliance Provisioning

```
START
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  O1-1. STAMP NEW INSTANCE FROM BLUEPRINT                      │
│  [MJCX → SYSTEM]                                             │
│                                                              │
│  From S7 (config-as-code repo):                              │
│  - docker compose up: evo, dify, chatwoot, carbone,          │
│    calc, spine, n8n, postiz (~8 containers)                  │
│  - Load dify workflow DSLs (inquiry, quoting, social)        │
│  - Load carbone templates (quote_EN, quote_ID, quote_ZH)     │
│  - Point calc at this client's S2 rules file                 │
│                                                              │
│  ⚠ NOTHING HERE IS CLIENT-SPECIFIC EXCEPT CONFIG VALUES.     │
│  If we are hand-editing workflows per client, the product    │
│  is broken. All client variation lives in data (S1/S2/S3)    │
│  and .env values.                                            │
│                                                              │
│  ● Read: S7 (blueprint)                                      │
│  ● Write: running instance                                   │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ══► Lanjut ke O2 (Catalog Ingest)
```

### O2. Catalog Ingest

```
╭──────────────────────────────────────────────────────────────╮
│  O2-1. CLIENT HANDS OVER CATALOG                              │
│  [MJCX]                                                      │
│                                                              │
│  Reality: it will be messy. Excel + PDF + photos + "ask      │
│  the factory". The kit's ingest pipeline handles:            │
│  - Excel/CSV → structured rows → S1                          │
│  - PDFs → chunk → dify knowledge base docs                    │
│  - Photos → stored against SKU                               │
│  - Gaps ("MOQ unknown for 12 SKUs") → GAP REPORT for client  │
│                                                              │
│  ⚠ THE GAP REPORT IS DELIVERABLE #1. It shows the client     │
│  exactly what their AI will and won't know. No surprises.    │
│                                                              │
│  ● Write: S1 (structured catalog + RAG docs)                  │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  O2-2. CATALOG VERIFICATION QUIZ                              │
│  [SYSTEM → MJCX]                                             │
│                                                              │
│  Agent asks itself 20 questions against the KB:              │
│  specs, MOQs, compatibility, certifications.                 │
│  MJCX reviews answers vs source docs.                        │
│                                                              │
│  ◇ Pass rate ≥ 90% and zero fabricated answers?              │
│    YES → proceed                                             │
│    NO → fix chunks/source docs, re-run. ⛔ Blocked until pass│
│                                                              │
│  ● Read: S1                                                  │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ══► Lanjut ke O3 (Pricing Rules)
```

### O3. Pricing Rules Capture

```
╭──────────────────────────────────────────────────────────────╮
│  O3-1. EXTRACT PRICING FROM "THE BOSS'S HEAD + EXCEL"         │
│  [MJCX + BOSS]                                               │
│                                                              │
│  Interview + existing sheets → pricing_rules.md:             │
│  - Base prices per model/material                            │
│  - Quantity tiers                                            │
│  - Spec/option coefficients                                  │
│  - Customer-tier terms (new / repeat / distributor)          │
│  - Discount authority cap (max % without human sign-off)     │
│  - Currency + validity terms                                 │
│                                                              │
│  ● Write: S2 (pricing_rules.md, versioned)                    │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  O3-2. BACKTEST AGAINST HISTORY                               │
│  [MJCX]                                                      │
│                                                              │
│  Client provides 10–20 REAL past quotes.                     │
│  calc re-computes each from S2 rules.                        │
│                                                              │
│  ◇ Calculator matches historical prices (± tolerance)?       │
│    YES → rules are trusted → proceed                         │
│    NO → interview round 2. ⛔ Blocked.                        │
│  ⚠ NEVER GO LIVE ON UNVERIFIED PRICING. One wrong price      │
│  sent to a real buyer destroys the client's trust forever.   │
│                                                              │
│  ● Read: S2, historical quotes                               │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ══► Lanjut ke O4 (Channel Connect)
```

### O4. Channel Connect & Escalation Setup

```
╭──────────────────────────────────────────────────────────────╮
│  O4-1. CONNECT CHANNELS                                       │
│  [MJCX + STAFF]                                              │
│                                                              │
│  v1 channels:                                                │
│  - WhatsApp: QR scan in evo (client's number)                │
│  - Email: IMAP/SMTP creds → n8n polling (shared inbox)       │
│                                                              │
│  Add-on modules (separate SKUs, not base):                   │
│  - WeCom/WeChat → LangBot container                          │
│  - Website chat widget → chatwoot widget                     │
│                                                              │
│  ⚠ BAILEYS QR SESSIONS DROP. It's a when, not if. See        │
│  cross-cutting X2 (session health) — client gets a 1-page    │
│  "re-scan the QR" runbook with pictures.                     │
│                                                              │
│  ● Write: S3 (initial customer import if client has a list)  │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  O4-2. ESCALATION RULES + GUARDRAILS                          │
│  [MJCX + BOSS]                                               │
│                                                              │
│  ALWAYS-HUMAN list (hardcoded, not AI-discretion):           │
│  ⛔ Payment terms negotiation                                │
│  ⛔ Legal / contract language                                │
│  ⛔ Complaints & anger                                        │
│  ⛔ Discounts beyond authority cap                            │
│  ⛔ Anything the agent isn't ≥ confident about                │
│                                                              │
│  Brand voice: client provides 5–10 comms they like →         │
│  becomes tone guide in dify prompt.                          │
│                                                              │
│  Business hours: instant AI 24/7; staff hours shown in       │
│  auto-responses for escalated items.                         │
│                                                              │
│  ● Write: S7 (escalation config), dify prompts               │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ══► Lanjut ke O5 (Acceptance Test)
```

### O5. Acceptance Test — the gate

```
╭──────────────────────────────────────────────────────────────╮
│  O5-1. SCRIPTED SCENARIOS (run on test WhatsApp number)      │
│  [MJCX]                                                      │
│                                                              │
│  1. Spec question, English → cited catalog answer            │
│  2. Spec question, Indonesian → same, in Indonesian          │
│  3. Standard price ask, qty 100 → calc → inline price        │
│  4. Formal quote ask → carbone PDF arrives in chat           │
│  5. Custom ODM request → escalates w/ draft + summary        │
│  6. "Your generator exploded" (complaint) → escalates        │
│     immediately, empathetic holding reply                    │
│  7. Discount push beyond cap → escalates                     │
│  8. Gibberish/spam → politely dropped                        │
│  9. Social draft → approval → postiz (if module on)          │
│ 10. QR drop drill → client re-scans using runbook            │
│                                                              │
│  ◇ All 10 pass?                                              │
│    YES → GO LIVE 🎉                                          │
│    NO → fix, re-run. ⛔ No partial go-lives.                  │
│                                                              │
│  ● Write: S8 (acceptance record)                             │
╰──────────────────────────────────────────────────────────────╯

  ═══════════════════════════════════════════
  ═══ APPLIANCE LIVE — RUNTIME PHASES A/B/C ═══
  ═══════════════════════════════════════════
```

---

## 2. Phase A: Inquiry Intake & Triage

Every inbound message from every channel walks this same path.

```
  INBOUND (WhatsApp via evo / email via n8n)
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  A1-1. MESSAGE RECEIVED                                       │
│  [SYSTEM]  ▣evo / ▣n8n                                       │
│                                                              │
│  WhatsApp: evo webhook fires ══[NATIVE]══► dify              │
│  Email: n8n polls IMAP → extracts text/attachments → dify    │
│                                                              │
│  ⚠ Idempotency: every message has a unique key; duplicates   │
│  (webhook retries) are dropped, not double-answered.         │
│                                                              │
│  ● Write: S4 (raw transcript row)                            │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  A2-1. WHO IS THIS? — IDENTITY RESOLUTION                     │
│  [AGENT]  ▣dify ──[HTTP]── ▣spine                             │
│                                                              │
│  Lookup phone/JID/email in S3:                               │
│  - Known customer → load profile: country, language, tier,   │
│    past quotes (S5), past conversations summary              │
│  - New → create record, detect country/language, tier=new    │
│                                                              │
│  ⚠ S3 IS THE ONLY SOURCE OF TRUTH. chatwoot contact =       │
│  pointer. Never two opinions about who a customer is.        │
│                                                              │
│  ● Read/Write: S3                                            │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  A3-1. CLASSIFY INTENT + LANGUAGE                             │
│  [AGENT]  ▣dify                                               │
│                                                              │
│  One LLM call, structured output:                            │
│  - language (reply in SAME language, always)                 │
│  - intent: SPEC_Q / PRICE_Q / CUSTOM_ODM / COMPLAINT /       │
│            SHIPPING / GREETING / SPAM / OTHER                │
│  - urgency + sentiment                                       │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ◇ A3-2. WHAT KIND OF INQUIRY?
  │
  ├── SPAM/GIBBERISH ──────► polite one-liner or silence.
  │                          ● Write: S4 (classified)
  ├── GREETING/OTHER ──────► friendly canned + "how can I help",
  │                          offer catalog highlights. [AGENT]
  ├── COMPLAINT ───────────► A6 (ESCALATE — always human)
  ├── SPEC_Q ──────────────► A4 (RAG answer)
  ├── PRICE_Q ─────────────► ══► Phase B (Quoting)
  └── CUSTOM_ODM/COMPLEX ──► A6 (ESCALATE)
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  A4-1. RAG ANSWER FROM CATALOG                                │
│  [AGENT]  ▣dify (KB built from S1)                            │
│                                                              │
│  Retrieve catalog chunks → answer with specifics:            │
│  model numbers, specs, MOQ, certs. Reply in buyer language.  │
│                                                              │
│  ◇ Confidence ≥ threshold AND grounded in S1 chunks?         │
│    YES → send answer + citation (product name/SKU)           │
│    NO  → ⛔ NEVER GUESS SPECS → A6 (ESCALATE)                │
│                                                              │
│  ⚠ A wrong spec answer is worse than no answer. The KB       │
│  says "I don't know" beautifully, with a human callback.     │
│                                                              │
│  ● Read: S1                                                  │
│  ● Write: S4 (answer logged)                                 │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  A6-1. ESCALATION WITH DRAFT — "flag complex ones with a      │
│         draft reply" (the spec's exact promise)               │
│  [AGENT → STAFF]  ▣dify ══[NATIVE]══ ▣chatwoot                │
│                                                              │
│  What lands in chatwoot:                                     │
│  - The full conversation so far                              │
│  - AI summary: who, what they want, context, sentiment       │
│  - DRAFT REPLY (in buyer's language) — staff edits & sends   │
│  - If price-adjacent: calc's suggested number + margin note  │
│  - Priority tag: COMPLAINT > CUSTOM > LOW_CONFIDENCE         │
│                                                              │
│  Staff replies INSIDE chatwoot → goes out the same channel   │
│  the buyer wrote in on. One inbox, all channels.             │
│                                                              │
│  ⚠ SLA beacon: escalated item unanswered > 2h (config) →     │
│  nudge [BOSS] on WhatsApp. ⚠ After hours → auto-holding      │
│  reply tells buyer when a human follows up.                  │
│                                                              │
│  ● Write: S4 (human reply logged), S3 (topic note on         │
│    customer), S8 (escalation event)                          │
╰──────────────────────────────────────────────────────────────╯

  ↩ Loop: every subsequent message from this buyer re-enters
    at A1 with full context loaded from S3/S4.
```

---

## 3. Phase B: Quoting & Pricing

"Accurate quotes in seconds, not hours. No calling the boss,
no checking Excel." The LLM never does the math.

```
  PRICE_Q DETECTED (from A3)
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B1-1. PARSE REQUIREMENTS                                     │
│  [AGENT]  ▣dify                                               │
│                                                              │
│  From conversation extract structured quote request:         │
│  product/model, qty, options, customization asks,            │
│  destination (if stated), incoterm (if stated), language.    │
│  Missing essentials → ONE clarifying question, then proceed. │
│                                                              │
│  ● Write: S5 (draft quote record)                            │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ◇ B1-2. COMPUTABLE FROM RULES?
  │
  ├── YES: standard item, known qty, rules cover it ──► B2
  │
  └── NO: custom/ODM/out-of-rules ──► B5 (HUMAN QUOTE)
      ⚠ dify has ZERO discretion here. If S2 doesn't
        contain the rule, it's a human quote. Period.
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B2-1. CALCULATOR COMPUTES (deterministic)                    │
│  [SYSTEM]  ▣dify ──[HTTP]── ▣calc ──● S2                      │
│                                                              │
│  Input: parsed request + customer tier from S3               │
│  Rules engine: base × qty-tier × coefficients + fees         │
│  → price, currency, validity, margin (margin visible to      │
│    STAFF only, never to buyer)                               │
│                                                              │
│  ⚠ LLM READS RULES, CODE DOES ARITHMETIC.                    │
│  This box is our IP and our quality guarantee.               │
│                                                              │
│  ● Read: S2, S3 (tier)                                       │
│  ● Write: S5 (quote computed)                                │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
  ◇ B3-1. INLINE OR FORMAL?
  │
  ├── Simple/standard ask ──► B3-2 INLINE PRICE
  │   [AGENT] ▣dify → ▣evo
  │   Price + terms + MOQ in the chat, in buyer language.
  │   Offer formal quote as next step. Fast lane.
  │
  └── Formal request / big qty / distributor ──► B4 FORMAL PDF
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B4-1. RENDER PDF QUOTE                                       │
│  [SYSTEM]  ▣dify ──[HTTP]── ▣carbone                          │
│                                                              │
│  carbone template (quote_EN / _ID / _ZH per buyer lang)      │
│  + JSON from S5/S3/S1 → branded PDF, numbered, dated,        │
│  valid-until. No copy-paste errors, no missing fields.       │
│                                                              │
│  ● Write: S5 (version + PDF link)                            │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B4-2. DELIVER IN THE SAME CHAT                               │
│  [SYSTEM → BUYER]  ▣evo                                       │
│                                                              │
│  PDF lands in the buyer's WhatsApp thread / email reply —    │
│  same channel they asked in. With a one-line summary and     │
│  "any questions, I'm here."                                  │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B5-1. HUMAN QUOTE PATH (custom/ODM)                          │
│  [AGENT → STAFF/BOSS]  ▣chatwoot                              │
│                                                              │
│  Same escalation package as A6, plus:                        │
│  - Structured requirement sheet (auto-generated)             │
│  - What's missing from S2 rules to make this computable      │
│    next time (rules-gap hint → boss decides whether to       │
│    add the rule)                                             │
│  ⚠ Every human quote is a PRICING RULES IMPROVEMENT          │
│   OPPORTUNITY. Month over month, escalations shrink.         │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  B6-1. QUOTE FOLLOW-UP LOOP                                    │
│  [SYSTEM]  ▣n8n cron + ▣dify                                  │
│                                                              │
│  Quote in S5 with status SENT:                               │
│  - 48h no reply → gentle follow-up DRAFT → staff approves    │
│    (v1) / auto-send (v1.1, client's choice)                  │
│  - Buyer negotiates → ◇ discount within authority cap?       │
│      YES → calc re-computes, new quote version               │
│      NO  → escalate w/ draft counter + floor-price context   │
│  - Accepted → 🎉 record win; next step offer: PI / contract  │
│    via carbone (doc-gen add-on module)                       │
│                                                              │
│  ● Read/Write: S5 (status machine), S8 (events)              │
╰──────────────────────────────────────────────────────────────╯
```

---

## 4. Phase C: Social & Channel Ops

"Your products everywhere, without a marketing team. Consistent
voice, auto-scheduled." Human approves; AI does everything else.

```
  WEEKLY CRON (e.g., Monday 09:00, configurable)
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  C1-1. PLAN THE WEEK'S CONTENT                                │
│  [AGENT]  ▣dify ──● S1                                         │
│                                                              │
│  Input: catalog (S1) + seasonal hooks + buyer-region themes  │
│  + what performed well (S6 stats).                           │
│  Output: content plan — which products, which angle,         │
│  which platforms (client's connected set), languages.        │
│                                                              │
│  ● Read: S1, S6                                              │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  C2-1. DRAFT THE POSTS                                        │
│  [AGENT]  ▣dify                                               │
│                                                              │
│  Batch of drafts in brand voice (from O4 guardrails):        │
│  captions, hashtags, image picks from S1 photos,             │
│  per-platform variants (LI formal / IG visual / X short).    │
│                                                              │
│  ● Write: S6 (drafts, status: PENDING_APPROVAL)              │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  C3-1. APPROVAL — v1 is ALWAYS human-approved                 │
│  [BOSS/STAFF]                                                 │
│                                                              │
│  Approval lands where the boss already lives: WhatsApp       │
│  card (approve/edit/reject per post) or postiz queue UI.     │
│                                                              │
│  ⚠ NO AUTO-PUBLISH IN V1. One bad post on a company          │
│  account costs more than a year of scheduler fees.           │
│  Auto-publish becomes a config flag in v1.1 for clients      │
│  who earn it.                                                │
│                                                              │
│  ● Write: S6 (status: APPROVED / EDITED / REJECTED)          │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  C4-1. SCHEDULE & PUBLISH                                     │
│  [SYSTEM]  ▣dify ──[HTTP]── ▣postiz                            │
│                                                              │
│  Approved posts pushed to postiz with optimal-time schedule. │
│  postiz publishes + collects stats.                          │
│                                                              │
│  ● Write: S6 (scheduled → published + links + stats)         │
╰──────────────────────────────────────────────────────────────╯
  │
  ▼
╭──────────────────────────────────────────────────────────────╮
│  C5-1. SOCIAL INBOUND → FUNNEL (the weave that pays)          │
│  [SYSTEM]                                                     │
│                                                              │
│  Comments/DMs on connected accounts that look like real      │
│  buying intent → routed into Phase A inquiry flow (same      │
│  agent, same catalog, same quoting).                         │
│                                                              │
│  ⚠ Social isn't vanity: it's another door into the same      │
│  funnel. CTA on every post → WhatsApp deep link.             │
│                                                              │
│  ● Write: S3 (new lead source=social), S4                    │
╰──────────────────────────────────────────────────────────────╯

  ↩ Loop: weekly, stats feed next week's C1 plan.
```

---

## 5. Cross-Cutting

### X1. The Spine — data ownership rules

```
╭──────────────────────────────────────────────────────────────╮
│  ONE SOURCE OF TRUTH PER CONCEPT  [spine — OURS]              │
│                                                              │
│  Customer identity  → S3 (everything else points here)       │
│  Product facts      → S1 (structured) + dify KB (derived)    │
│  Price math         → S2 + calc (nobody else computes)       │
│  Quote record       → S5 (chatwoot/evo reference quote_id)   │
│                                                              │
│  ⚠ Derived copies are fine (dify KB chunks). Conflicting     │
│  opinions are not. Any new store must decide: master or      │
│  pointer — before it's allowed into the stack.               │
╰──────────────────────────────────────────────────────────────╯
```

### X2. Session Health & Runbook

```
╭──────────────────────────────────────────────────────────────╮
│  FAILURE MODES — known, boring, documented                     │
│                                                              │
│  WhatsApp QR session drops (baileys):                        │
│    evo → alert → client follows 1-page picture runbook       │
│    to re-scan. Target: self-serve in <5 min.                 │
│                                                              │
│  LLM provider outage:                                        │
│    dify fallback model chain. If all down: holding reply     │
│    + everything routes to chatwoot (graceful dumb mode).     │
│                                                              │
│  Webhook storms / duplicates: idempotency keys, drop dupes.  │
│                                                              │
│  calc/carbone down: quoting degrades to escalation path —    │
│    inquiries still get answered, quotes wait for humans.     │
│    Never total silence to buyers.                            │
│                                                              │
│  Daily 07:00: n8n health digest to MJCX (not client):        │
│    sessions up, errors, escalations pending, quote stats.    │
│                                                              │
│  ● Write: S8                                                │
╰──────────────────────────────────────────────────────────────╯
```

### X3. Notifications

```
┌──────────────────────────────┬──────────┬────────────────────┐
│ Trigger                      │ Who      │ Where              │
├──────────────────────────────┼──────────┼────────────────────┤
│ Escalated inquiry created    │ STAFF    │ chatwoot + email   │
│ Escalation unanswered > 2h   │ BOSS     │ WhatsApp           │
│ Complaint detected           │ STAFF+   │ chatwoot PRIORITY  │
│ Quote sent (formal)          │ STAFF    │ chatwoot note      │
│ Quote accepted               │ STAFF    │ chatwoot + WhatsApp│
│ Discount beyond cap requested│ BOSS     │ WhatsApp w/ context│
│ Social drafts ready          │ BOSS     │ WhatsApp card      │
│ WhatsApp session dropped     │ STAFF    │ WhatsApp + runbook │
│ Any service down > 5 min     │ MJCX     │ MJCX channel       │
│ Weekly summary (Fri)         │ BOSS     │ WhatsApp digest    │
└──────────────────────────────┴──────────┴────────────────────┘
```

### X4. Data Visibility — per role

```
  BUYER:  catalog answers, their quotes, their thread.
          ⛔ Never: margins, other customers, internal notes.

  STAFF:  all conversations, all drafts, margin on quotes,
          customer history (S3/S4/S5). ⛔ Never: rule editing.

  BOSS:   everything staff sees + pricing rules (S2),
          discount approvals, social approvals, reports.
          ⛔ Not required to touch chatwoot day-to-day.

  MJCX:   infrastructure + logs (S7/S8) for maintenance.
          ⛔ Not business secrets (pricing visible only as
          needed for calc backtests during onboarding).
```

### X5. Monthly Client Report (the retention artifact)

```
  Auto-generated, sent to BOSS:
  - Inquiries: total, AI-answered vs escalated, median
    response time (the "before" is usually HOURS or a day)
  - Quotes: sent, accepted, win rate, avg margin
  - Top asked products (→ content & stock insight)
  - Questions the AI couldn't answer (→ catalog gap report)
  - Escalation reasons breakdown (→ rules-gap opportunities)
  ⚠ This report is why clients renew. It shows the machine
  working in numbers a boss cares about.
```

---

## Summary: Process Count

| Section | Steps | Decision Points | Loops | Human Touchpoints |
|---|---|---|---|---|
| Phase O: Onboarding | 12 | 3 (gates) | 1 (pricing interview) | MJCX + client ~2-3h total |
| Phase A: Inquiry Triage | 6 | 2 | 1 (per message) | STAFF only on escalation |
| Phase B: Quoting | 7 | 3 | 1 (follow-up) | STAFF on custom/beyond-cap |
| Phase C: Social | 5 | 0 | 1 (weekly) | BOSS approval only |
| Cross-Cutting | 5 blocks | 0 | 1 (health digest) | — |
| **TOTAL** | **~35** | **~8** | **~5** | **2 approval points in steady state** |

Steady state: the client's team touches TWO things — chatwoot
escalations (with drafts ready) and WhatsApp approvals. Everything
else runs itself.

---

## Scope Notes — For Proposal

### Included in Base Appliance (v1)

- Onboarding stamp: catalog ingest + gap report, pricing rules
  capture + backtest, channel connect, acceptance test
- Inquiry auto-response (WhatsApp + shared email inbox), bilingual
  CN/EN + buyer's language
- Escalation to chatwoot with AI drafts + summaries, SLA beacons
- Quoting: calculator (deterministic), inline prices, carbone
  PDF quotes, quote tracking + follow-up drafts
- Monthly report + weekly boss digest
- Session health monitoring + runbooks, MJCX maintenance window

### Add-On Modules (separate SKUs)

- Social & channel ops (Phase C: dify drafting + postiz)
- WeCom/WeChat channel (LangBot container) — China-facing
- Doc-gen bundle: PI, contract, packing list via carbone
- Website chat widget (chatwoot widget)
- China-facing full stack (tgo-based) — separate product line

### NOT in Scope v1 (roadmap)

- Auto-publish social without approval
- ERP/inventory/PO integration (erpnext enters when needed)
- Full CRM UI (twenty enters when client asks for pipeline views)
- Meeting intelligence, market-intel digests (v2 menu items)
- Multi-tenant hosting of the OSS components (license + ops)

---

*MJCX Studio — Building Products that Actually Ship*
