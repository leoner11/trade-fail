# Appliance Console — Spec v1.0

Date: 2026-08-25 · Status: SPEC (not built) · Accent decided: **MJCX Indigo**
Design contract inherited from `trade-agent-appliance-design-system-not-adapted.md`
(NaraHome/Cooljek derivation), retuned for MJCX. Where this doc and that doc
disagree, THIS doc wins for the appliance.

---

## 1. What this is

The face of the appliance, shipped in the O1 stamp. Two jobs:

1. **Productize Phase O.** Today the stamp is a 20-min manual checklist spread
   across evo manager, dify console, and terminals (cold-start §O1 first-boot
   1–5). The console walks a client through Connect → Catalog → Knowledge →
   Pricing → Voice → Go-Live, with the O2/O3 gates rendered as what they are:
   blocking banners.
2. **Steady-state ops view** (HANDOFF §5 item 5, Leonard's dashboard): quotes,
   customers, social queue state, audit trail — reading **spine only**, so
   chatwoot/evo/postiz stay replaceable organs (X1).

Audiences (flowchart X4): BOSS (everything, approvals stay on WhatsApp),
STAFF (runtime tabs), MJCX (setup tabs during onboarding). Single shared login
token per appliance — this is a single-tenant box on the client's LAN, not a
SaaS. No roles matrix in v1.

### Explicit non-goals (v1)

- ❌ Chatwoot inbox rebuild — pointer chip to :3000 instead (X1).
- ❌ Approvals in-browser. B6 follow-ups and C posts are approved on
  WhatsApp (canonical, flowchart B6-1/C3-1). Console shows STATE read-only;
  acting here would create a second approval truth.
- ❌ Postiz UI clone — pointer chip to :13000.
- ❌ Multi-tenant anything. One stack, one client, one token.
- ❌ Mobile app. Desktop web ≥1280px target; degrades to usable, not perfect.

---

## 2. Architecture

```
┌──────────────┐  static    ┌─────────────────────────────────────────┐
│ console/     │◄───────────│ caddy/nginx container (:8090), O1 stamp │
│ Vite+React+TS│            └──────────────┬──────────────────────────┘
│ Tailwind SPA │                           │ same-origin reverse proxy
└──────┬───────┘                           ▼
       │ fetch (JSON, bearer CONSOLE_TOKEN)
       │                                   ┌──────────────┐
       ├── DATA (S1/S3/S5/S6/S8) ────────► │ spine :8101  │  OURS
       └── ORGAN ACTIONS ────────────────► │ glue  :8102  │  OURS
             QR/session → evo              └──┬───┬───┬───┘
             KB ingest/quiz → dify            │   │   └─► evo      :8080
             backtest → calc rules            │   └─────► dify     :8180
                                              └─────────► calc/spine local
```

Rules:

- **The browser never talks to organs directly.** Every organ call is proxied
  by a thin glue endpoint (`/console/*` below) because glue already owns all
  orchestration logic ("n8n is just the clock" — likewise "the console is just
  eyes"). Keeps evo/dify creds server-side and keeps X1 clean: spine stays the
  only place runtime data lives.
- **Auth:** `Authorization: Bearer $CONSOLE_TOKEN` checked by glue + spine
  (new shared dep or 10-line check). Token lives in `.env`. Login screen =
  paste token once; stored in localStorage; 401 → login.
- **Shipping:** `console/Dockerfile` builds static → caddy serves SPA +
  `/spine/*` and `/glue/*` upstreams on one origin (:8090). Joins the flat
  network in `compose/docker-compose.appliance.yml`.
- Dev mode: Vite dev server proxies to localhost:8101/:8102.

### New glue endpoints (all under `/console`, all thin)

| Endpoint | Wraps | Notes |
|---|---|---|
| `GET /console/wa/status` | evo `GET /instance/connectionState/{inst}` | `{state, instance}` |
| `GET /console/wa/qr` | evo `GET /instance/connect/{inst}` | `{base64}` — poll q3s while state≠open. Same calls as `tests/test_o5_s10_qr_drill.py` uses today |
| `POST /console/wa/logout` | evo logout | gated by confirm dialog (design §7) |
| `GET /console/kb/docs` | dify datasets API via existing `knowledge_ingest.py` helpers | id, name, indexing_status |
| `POST /console/kb/ingest` | `knowledge_ingest.py --replace` path | multipart md/txt/pdf → index; returns doc_id. Long job → `{job_id}` + poll |
| `POST /console/gates/o2_quiz` | logic of `tests/test_o2_quiz.py` | runs N questions through live A3-Spec app → per-Q verdicts + fabrication count. Job + poll (~min) |
| `POST /console/gates/o3_backtest` | logic of `tests/test_o3_backtest.py` | body = history JSON (schema = `data/o3_history.example.json`) → per-ref delta table + pass-rate at ±2% vs ≥90% gate. Refuses in EXAMPLE mode exactly like the harness does |
| `GET /console/gates/summary` | reads last gate runs (persisted as S8 events `gate_o2` / `gate_o3`) | powers go-live page banners |

### New spine capability (ours, allowed)

- `POST /catalog/import` (CSV rows → S1 upsert) + gap report response
  (`skus_imported`, `fields_missing[]`). This is flowchart O2-1's GAP REPORT,
  deliverable #1. Excel → client converts to CSV in v1 (say so in UI).
- `GET /quotes/{qid}/pdf` file stream if `pdf_path` set (B4 already writes it).

---

## 3. Screens

Nav order IS onboarding order. Setup group collapses after go-live flag.

### SETUP

**S1 · Connect** (Phase O4-1)
- WhatsApp card: state badge (`open`=success tag / `close`=attention /
  absent=danger), big QR panel (polls `/console/wa/qr`), "Scan with the phone
  that owns the number" caption, link-out to runbook
  `runbooks/whatsapp-qr-rescan.md`, Danger-zone: Logout session
  (ConfirmDialog names the consequence).
- This screen IS the S10 self-serve drill (<5 min target) — design it so.
- Channel pointer chips: postiz :13000 (signup/API-key steps inline), n8n
  :5678, chatwoot :3000, dify :8180. Each chip shows reachability
  (`/health` via glue proxy) as dot+label.

**S2 · Catalog** (O2-1)
- DataTable of S1 SKUs (sku mono, name, key specs, updated).
- Import: drop CSV → `POST /catalog/import` → GAP REPORT rendered as
  attention banner + missing-fields table. Deliverable framing verbatim from
  flowchart: "shows the client exactly what their AI will and won't know."

**S3 · Knowledge** (O2-2)
- Doc list (name, status, size, re-ingest ghost button) from `/console/kb/docs`.
- Upload slot per design §14 (dashed, camera→FileUp icon, progress bar on row).
- Gate card: [Run verification quiz] → job progress → result banner:
  ≥90% & 0 fabricated → success banner; else danger banner naming weak
  questions. ⛔ blocks Go-Live until pass. Results persist as S8 event.

**S4 · Pricing** (O3)
- Rules viewer first: render current S2 JSON as key-value blocks + qty-tier
  ladder table + authority cap callout (this is the boss's money logic —
  readable beats editable).
- Editor (v1.1): guarded form for base prices/tiers/fees/cap → versioned S2
  write + diff preview. v1 ships viewer + "edit JSON in git" note (config-as-code
  rule #6 unchanged).
- Backtest gate card: upload history JSON (template downloadable =
  example file) → per-ref table (ref, quoted_total, recomputed, Δ%) →
  pass-rate banner at ±2% / ≥90%. Fail → "interview round 2 on mismatches"
  hint (o3-pricing-interview.md). ⛔ blocks Go-Live.

**S5 · Voice & guardrails**
- Always-human list rendered READ-ONLY (it is hardcoded rule #3 by design).
- Samples editor: textarea grid (lang × situation) → writes into
  `voice_guide.md` samples section via glue file-writer (data, not code —
  O4-2). Show current escalation holding-reply contract text.

**S6 · Go-Live** (O5)
- Checklist mirroring O5-1 scenarios 1–10. Auto-verifiable ones pull gate
  summary (O2, O3, WA connected, postiz key present); physical ones (phone
  scenarios, QR drill) are manual check rows with "how to test" expanders.
- All green → GO LIVE switch → writes S8 `go_live` event, flips header
  badge. No partial go-lives: switch disabled with reason list otherwise.

### RUNTIME

**R1 · Home**
- KPI tiles (max 4): open escalations 24h (S8, attention tone), quotes sent
  awaiting reply >48h (S5), social posts pending approval (S6), WA session
  state. Delta line where history allows.
- Attention queue: latest S8 events needing eyes (sla_beacon,
  escalation, postiz_push_skipped) as timeline (design §10).

**R2 · Quotes (S5)** — DataTable: qid mono, customer (S3 join), total
right-aligned tabular + currency fmt, status tag via tone map, created,
pdf link (ghost Download). Row click → detail panel (two-column pattern):
key-value block + status rail (draft→sent→accepted…) + S8 events for qid.

**R3 · Customers (S3)** — DataTable: name, JID mono (truncated), country,
tier tag, first-seen, last event. Detail: their quotes inline.

**R4 · Social (S6)** — read-only queue table: pid mono, SKU, status
(pending/approved/rejected/scheduled/posted tone map), scheduled_at,
postiz pointer if published. Banner when pending>0: "Approve on WhatsApp".

**R5 · Events (S8)** — filterable timeline (kind chips), paginated 50.

**R6 · Inbox** — not a screen: pointer card with chatwoot URL + "why we don't
duplicate it" one-liner.

---

## 4. Design tokens (adaptation deltas)

Inherit wholesale: philosophy (ops tool, quiet confidence), 16px root +
absolute px type scale, Lucide 1.75px line icons, tables-first + DataTable
rule, status triplet system, buttons/forms/modals/toasts/empty-loading/
timeline/motion/a11y floor. Changes and additions:

### Palette

| Role | Token | Hex | Usage |
|---|---|---|---|
| **Brand** | `brand-primary` | `#4F46E5` | primary buttons, focus rings, links, selected row wash/border |
| Brand hover | `brand-primary-hover` | `#4338CA` | hover darken only |
| Brand wash | `brand-primary-wash` | `#EEF2FF` | selected rows, active chips/tabs bed |
| Ink rail | `sidebar-bg` | `#12142B` | sidebar, dark surfaces |
| Rail raised | `sidebar-hover` | `#1C1F3D` | sidebar hover |
| Rail active | `sidebar-active` | `#818CF8` | active nav marker on dark rail |
| Rail text | `sidebar-text` | `#A0AEC0` | inactive labels |

**NEW semantic family — AI Violet** (the honest way to add colour: it means
something). Marks ANYTHING model-generated: AI drafts, AI summaries, quiz
answers, backtest recomputations, social captions. Human/system content never
wears it. A buyer-facing draft shown to staff is ai-accent bordered; the
staff edit inside it is plain.

| Role | Token | Hex |
|---|---|---|
| AI accent | `ai-fg` / `ai-dot` / `ai-wash` | `#6D28D9` / `#8B5CF6` / `#F5F3FF` |

Statuses keep the six tones + hex from the base system unchanged (incl.
attention amber `#B45309`). Channel colours exist ONLY inside channel chips:
WhatsApp `#25D366` dot max 8px, never fills.

Per-client accent swap: every colour above lands as CSS vars in
`tokens.css`; `.env CLIENT_ACCENT` → build arg overrides brand family only
(rule #5: variation in config). AI violet + statuses are NOT client-tunable.

### Type & voice

- English UI v1; strings centralized `src/i18n/en.ts` from day one (id later).
- Monospace for ALL ids: quote Q-*, post P-*, sku, JID, ref (base system rule).
- Money: `formatMoney(n, currency)` → `USD 10,088.00` (ISO code prefix, since
  S2 currency is ISO). Dates `formatDateTime()` local tz.

### Component inventory (from base patterns)

DataTable (align/sticky/skeleton/footer additions) · StatusBadge with
`tone=` prop (domain maps: quote-status, post-status, wa-state, gate-result) ·
GateBanner (= approval-banner pattern, tones: success/danger/attention, ONE
per panel, ⛔ copy when blocking) · KPI tile · Section panel · Key-value
block · Timeline (events) · Upload slot · PointerChip (icon + label + health
dot + external-link) · ConfirmDialog (destructive: logout WA session) ·
Skeleton rows everywhere.

Empty states follow the three-case wording rule. Loading = skeletons, spinner
only in-button. Motion table unchanged (150ms hovers; the ONLY loop allowed =
live pulse on the WA-connecting QR state dot).

---

## 5. Build milestones

| M | Scope | Why this order |
|---|---|---|
| **M0** | scaffold, tokens.css, shell (rail+topbar), auth, DataTable/StatusBadge/GateBanner primitives | foundation, half day |
| **M1** | R1–R5 read-only over existing spine APIs (zero backend changes) | Leonard's dashboard wish, immediately useful |
| **M2** | S1 Connect + R6 pointers (glue `/console/wa/*`, health probes) | highest-drama demo, unblocks S10 drill |
| **M3** | S3 Knowledge + O2 gate (wrap knowledge_ingest + quiz) | first blocking gate live |
| **M4** | S4 Pricing viewer + O3 gate, S6 Go-Live page, spine `/catalog/import` + S2 import | completes Phase O productization |
| M5 (later) | S2 rules form editor, S5 samples writer, X5 monthly report tab | polish |

Each M ends with: lint+tsc clean, smoke against the live spike stack, dated
spike-log entry.

## 6. Open questions (decide before the milestone that needs them)

1. M4 pricing editor: form-with-diff vs "edit JSON in git" forever? (Boss
   persona may never touch git — lean form.)
2. Gate persistence: S8 events vs small `console_state` table in spine?
   (Lean S8 — zero schema, X5 gets the history free.)
3. Does the console ship enabled-by-default in the stamp, or behind
   `CONSOLE_ENABLED=1`? (Lean enabled; LAN-only exposure.)

---

# Part 2 — v1.1 backlog (spec'd 2026-08-25, not built)

Decided with Leonard: console keeps its steady-state shape; three additions
next session. Ordering below is build order.

## V1.1-A · Inbox face + take-over (chats in the console)

Bosses won't keep a second tab at :3000. The console becomes a second CLIENT
of chatwoot's API — never a second store (X1: chatwoot remains S4; nothing
transcript-shaped is persisted outside it).

Glue endpoints (bearer-gated like all /console/*):

| Endpoint | Wraps |
|---|---|
| `GET /console/inbox/conversations` | chatwoot GET /api/v1/accounts/{id}/conversations (open first) |
| `GET /console/inbox/{cid}/messages` | chatwoot messages list + contact meta |
| `POST /console/inbox/{cid}/reply` | chatwoot create-message, message_type=outgoing, private=false |

Behavior:
- Two-column pattern (list 45% / thread 55%), independent scroll, selection
  in URL (?c={conversation_id}).
- Sender rendering: evo-bridge/bot senders in AI-violet, humans plain,
  buyer lines left-aligned. Names resolved via /agents email map
  (trap #21 lesson: never hardcode ids).
- **Take-over** = edit the reply freely in-console, then send as a PUBLIC
  outgoing message through chatwoot using the ADMIN api-token identity
  (CHATWOOT_API_TOKEN) — NOT the evo-bridge bot identity. This matters:
  /a6/sla_tick counts a conversation as human-handled the moment a non-
  bridge agent sends a public reply (trap #21 rule), so replying from the
  console correctly STOPS the SLA beacons. DECIDED (Leonard): take-over =
  handled-by-human; the console reply box is free-edit, no drafts pipeline.
- Poll 5s while the page is open. Unread badge count in nav (attention dot).
- Out of scope: assignment drag-drop, canned responses, private notes
  (chatwoot stays authoritative for those).

Acceptance: complaint arrives on phone 2 → appears in console <10s →
take-over reply lands on phone 2 → thread shows violet bot lines vs plain
human line → sla_tick no longer fires for that conversation.

## V1.1-B · Pricing form editor + hot reload

- calc gains `POST /rules/reload` (our IP): re-reads RULES_PATH, swaps the
  in-memory object under a lock, returns schema_version. WITHOUT this an
  edited file does nothing until restart — the silent-stale-rules trap.
- Console PricingPage gains Edit mode (full-width editor overlay, design
  §20): guarded numeric inputs for base/bulk prices, qty ladder rows, tier
  factors, process fees, authority cap, validity_days. Diff preview
  (old → new, red/green) before Save. Save writes RULES_PATH in place
  (.bak versioned, same pattern as voice_guide) → calls calc reload →
  re-renders viewer from live rules. Unknown-tier/XL coef-0 escape hatch
  rendered immutable with an explainer.
- Validation mirrors calc's own expectations (positive numbers, ladder
  min_qty strictly increasing, factors > 0). Server re-validates on reload;
  failed reload rolls back from .bak and reports.

## V1.1-C · Price visibility policy ("knows but never tells")

Structural, model-independent enforcement (same philosophy as removing the
PDF CTA from generation): the agent cannot leak a number it was never given.

S2 schema addition (schema_version 2 → 3, backward-compatible):

```json
"price_visibility": {
  "default": "public",
  "per_material": { "STS-200": "internal_only" }
}
```

Enforcement lives in GLUE's B-path (A3→B routing decision), not in prompts:
after B1 parse, if ANY line's material resolves to internal_only → skip
inline computation entirely → B5 escalation package with gap hint
"pricing for {material} is internal — human quote required". Buyer hears
"team will confirm"; calc may still be called for STAFF-facing context
(margin notes in chatwoot), which is exactly flowchart X4.

Console surface:
- PricingPage visibility column (eye / eye-off tag) + toggle in Edit mode.
- QuotesPage: rows containing internal items get an "internal" tag; their
  inline total renders as "—" when the quote originated from a hidden item.

Explicitly DEFERRED (needs boss input, bigger S2 change): true two-number
mode — `floor_price` (authority checks) vs `base_price` (quoted). Ship
hide/show first; revisit when a client asks for dual lists.

## Build order & estimates

A ≈ 1 session (glue proxy + thread UI + acceptance drill).
B ≈ 1 session (calc reload endpoint is the risky half).
C ≈ half session after B (schema bump rides the editor work).
Each ends with gates sweep + dated spike-log entry, per house rules.
