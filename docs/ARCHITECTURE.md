# ARCHITECTURE — MJCX Trade Agent Appliance (v1.2 snapshot, 2026-08-26)

One paragraph: a WhatsApp-native sales agent for foreign-trade SMEs. evo
transports WhatsApp; glue (:8102) is the brain-stem — every message is
routed through deterministic checks first, an LLM classifier second, and
calc (:8100) is the ONLY thing allowed to compute money. spine (:8101) owns
all runtime data. dify (:8180) hosts two LLM workflows (triage, spec-RAG).
The console is eyes + staff actions; n8n is just the clock.

```
buyer ⇄ WhatsApp ⇄ evo :8080 ──webhook──► glue :8102 ──► dify :8180 (classify / spec-RAG)
                                             │  ▲            ──► GLM direct (parse/compose)
                        sendText/sendMedia ◄──┘  └──────────► calc :8100 (quotes, rules reload)
                                             │
                     mirror/transcripts/escalations/tiers/quotes/posts/events
                                             ▼
                                          spine :8101 (SQLite = S1 S2-pointer S3 S4 S5 S6 S8)
                                             ▲
             console :5173 dev / :8090 stamp ┘  (reads spine, acts via glue; bearer CONSOLE_TOKEN)
```

Replaceable organs (X1): evo, chatwoot (OFF since v1.2), postiz, carbone,
n8n, dify. Our IP: calc, spine, glue, console. Client variation lives in
DATA + config only — never code forks.

## Life of one inbound WhatsApp message (glue `route()`)

1. **Noise gate** (deterministic): letters < 50% of a ≥4-char message →
   polite silence. Keyboard mash never reaches a human or an LLM.
2. **Thread state** (`_THREAD`, per-contact, in-process):
   - pending offer + buyer agreement ("yes please", 好的) → FULFILL it
     (info from stored facts, or render+send the quoted PDF).
   - pricing continuation: we asked for quantity + buyer replies with one →
     synthesize "N units of SKU STD" and FORCE route=PRICE_Q (the triage
     model calls bare quantity+SKU "OTHER").
   - engagement opener ("lets go") on first contact → anchored welcome.
3. **Triage**: dify workflow (GLM fallback) → intent/language/confidence.
   conf < 0.7 or unknown intent → human handoff.
4. **Deterministic overrides BEFORE generative paths**:
   - capability questions ("what do you sell?", 你们是做什么的) → answer
     with REAL product line from spine S1 + ONE question.
   - SPEC_Q: exact SKU token OR alias resolution from S1 names
     ("the ats panel"→ATS-50) → catalog facts answer. Out-of-domain
     availability probes ("do you have kaolin?") → grounded "not our line"
     + pivot. RAG answers matching stall signatures ("check with our team")
     are repaired via alias, else escalated FOR REAL — no fake promises.
5. **PRICE_Q → B-path**: B1 parse (closed vocab from S2) → calc /quote →
   inline price (numbers=exact guard: every fact digit must survive),
   validity date appended structurally, quote saved to S5, PDF offer armed;
   formal ask → carbone PDF in-thread (B4). Gaps/internal-only/unknown-tier
   → B5 human quote.
6. **Escalations** arm the SPINE conversation (S4): tag + staff note as a
   system message + S8 event. Buyer hears a holding line that is TRUE.
7. **Mirror**: every inbound/outbound line lands in spine `messages`
   (best-effort, before routing) so staff always see the thread.
8. **SLA tick** (n8n cron → `/a6/sla_tick`): open conversations whose last
   buyer inbound sits > SLA_HOURS without a human outbound → boss WhatsApp
   nudge, once per conversation until handled/re-armed.

## Decision authority (who may decide what)

| Layer | Examples | Authority |
|---|---|---|
| Deterministic glue | noise, agreements, continuations, aliases, stall repair | code + spine/calc facts only |
| LLM generation | wording ONLY; facts are the ceiling; numbers guarded subset/exact | voice_guide.md contract |
| LLM classification | intent/language/confidence | advisory — low confidence ⇒ human |
| calc | ALL arithmetic, discounts, validity | the only money authority |
| Humans (always, rule #3) | complaints, payment/legal, discount beyond authority cap, unknown tier, internal-only pricing | sacred at every autonomy level |

## Autonomy dial (S2 `agent_policy.autonomy`; Pricing page toggle; hot-reload)

- `assistant` — AI never touches money: PRICE_Q → honest holding line +
  human quote escalation. Everything else unchanged.
- `standard` (default; key absent) — inline computed quotes within S2.
- `closer` — ambiguous OTHER gets ONE clarifying question (commits to
  nothing) before handoff; budget resets when any message routes cleanly.
- Gates pin STANDARD. Clients move off standard only after go-live gates
  pass; document per client.

## Data stores (spine.db)

| Store | Table(s) | Writer |
|---|---|---|
| S1 catalog | `catalog` | console import/manual, init seed |
| S2 pricing rules | `spine/rules/*.json` (file) | console editor (validate→.bak→write→calc reload→glue vocab refresh); holds price_visibility v3 + agent_policy |
| S3 identity+tiers | `customers` | resolve on every message; staff PATCH (tier_change audited) |
| S4 conversations | `conversations`, `messages` | glue `_mirror` (all traffic), staff take-over (human out clears escalations) |
| S5 quotes | `quotes` | B-path save+sent; B4 records pdf_path |
| S6 social queue | `social_posts` | c_draft_tick; postiz publish pointer |
| S8 audit | `events` | escalations, sla beacons, gates, tier changes |

chatwoot remains INSTALLED but disabled (`CHATWOOT_ENABLED=0`); its glue
proxies (`/console/inbox/*`) are the documented rollback path. Remove from
compose only after v1.2 soaks.

## Voice (how replies sound)

`dify/prompts/voice_guide.md` is config-as-code: tone principles (one
question per message, acknowledge-first, never re-ask, zh softeners ～/哦
max one), seeded sample lines from real sales threads, and hard contract
rules (facts ceiling, VERBATIM numbers, no links, neutral escalation
holding lines, grounded negatives allowed only where the situation proves
absence). Glue enforces mechanically: number-subset/exact guards, link
guard, opening-clash regeneration with banned openings.

## Gates (plain scripts under tests/, run after EVERY organ edit)

calc unit 22 · e2e 13 · classify eval · voice eval 8 cases · B4 12 ·
O2 quiz · O3 backtest (example mode until boss data) · O5 acceptance 10 ·
S9 social 5. Console: `npm run build` + `lint`. If the data story changes,
re-run EVERY gate (traps #29/#30). Gates pin standard autonomy.

## Config-as-code inventory (rule #6)

dify/dsl/{a3_triage,spec_answer}.yml · dify/prompts/{a3_classify,voice_guide}.md ·
n8n/workflows/* · compose/* · spine/rules/*.json · this doc + HANDOFF +
docs/spike-log.md (history & traps #1–#41).

## Known gaps / queued

- dify spec DSL still fake-promises "let me check" on attribute misses
  (trap #34) — needs structured marker + DSL re-import cycle.
- :8090 caddy stamp unshipped (console runs in dev mode only).
- Thread decision-state is in-process; restart re-learns on next message
  (full transcripts are in spine if deeper recall is ever needed).
- Webhook-auth hardening design doc (buyer webhook deliberately open).
