# DESIGN — Conversation core v2 (stateful agent loop)

Status: DESIGN (2026-08-26, session #15 end) — implement after Leonard's OK.
One paragraph: v1's classify→regex→RAG→compose pipeline is stateless per
message; five live flakes in one evening share that single root cause. v2
replaces the routing cascade with ONE stateful tool-calling agent. Every
organ — calc, spine, escalation/Threads, console, evo, email, B6, n8n —
stays untouched.

## Evidence (tonight's log, all one disease)

| Time | Buyer said | v1 did | Root cause |
|---|---|---|---|
| 21:17 | "DG-30 lets say" | OTHER 0.4 → human flag mid-sale | stateless classifier, no thread context |
| 22:34 | "what models are there" | RAG stall → spec_stub + escalation | deterministic S1 list behind an intent gate |
| 22:51 | "30 kva is dg 30?" | hyphen missed regex → RAG prose as "facts" | brittle text matching |
| 22:53 | "yes please" | guard killed padded specs → GOODBYE sent | weak facts + wrong fallback |
| 22:53 | "i want the details" | "which product?" amnesia | RAG sees one message only |
| 23:20 | "tell me more bout ur industry" | OTHER 0.85 → human flag | regex can't enumerate phrasings |

Diagnosis: each fix chases the previous phrasing (4 regex patches today);
thread state lives in process RAM and dies on restart; regex coverage is
unknowable. This is architecture, not bugs.

## Shape

```
msg → deterministic pre-guards (noise, complaint/anger, spam)     [unchanged]
    → AGENT LOOP (glm-4.5; context = system + voice guide + last N turns
                   from S4 + tool results; decides: tool call / reply /
                   escalate; max 4 tool calls per message)
         tools:  catalog_lookup(q)            S1 fuzzy: "dg 30"/"30kva"/alias
                 list_models()                S1 line + company facts
                 kb_search(q)                 dify spec workflow as a tool
                 price_quote(lines, formal)   B1→calc→S5→(B4 PDF); numbers
                                             ONLY from calc result
                 escalate(reason)             arms the SAME spine store
    → deterministic post-guards (digits ⊆ tool facts; link/capability
      guard; language mirror)                                      [unchanged]
    → send + _mirror                                             [unchanged]
```

## Grounding rules (unchanged philosophy, stronger enforcement)

1. The agent may only state facts a tool returned. The number guard
   (today's compose guard, reused verbatim) rejects any digit not present
   in tool output — rejected generations fall back to DETERMINISTIC tool
   output (catalog card / quote bullets), never a wrong-template reply
   (tonight's goodbye bug).
2. Arithmetic: calc only. The agent never computes; price_quote returns
   finished numbers the agent relays.
3. Always-human list stays sacred and PRE-model: complaints/anger are
   detected in the pre-guard and routed to the escalation path before the
   agent sees anything. Payment/legal/discount-beyond-cap: calc refuses
   (gaps) → forced escalate tool with reason.

## Memory

- History: S4 already mirrors every line of every thread (`_mirror`).
  Agent context = last N=20 messages for the jid, read from spine.
  Restart-proof, identical truth as the console Threads page.
- Small state (pending offer / PDF promise / clarified-once): one
  `agent_state` JSON column on the spine conversation row (live
  PRAGMA-guarded migration, the social_images pattern). Replaces `_THREAD`
  RAM dict.

## Autonomy dial (S2 `agent_policy`, hot-reload, unchanged semantics)

- assistant → price_quote tool not offered; agent says the team prepares
  the quotation + escalate (today's behavior).
- standard → inline computed quotes.
- closer → loop prompt variant: one clarifying reply before escalate is
  accepted.

## Model + flag

- `CONVERSATION_MODEL` env (default `glm-4.5` — confirmed served by our
  endpoint; benchmark vs `glm-5.3-flash` during the gate phase, pick on
  O5 results + latency, not vibes).
- `CONVERSATION_CORE=v1|v2` (default v1 until soak). `route()` delegates
  to `glue/agent.py` when v2. **v1 is FROZEN from tonight** — live flakes
  get pinned as v2 scenarios, not more regex.

## Migration + acceptance

1. Build `glue/agent.py` + tool wrappers (thin HTTP to existing services;
   catalog/alias/normalization code MOVED, not rewritten) behind the flag.
2. Gates: existing O5 16/16 run with the flag flipped to v2, plus new
   S15–S19 = tonight's five flakes pinned verbatim (message → expected
   behavior). e2e/B4/email/S9/voice unchanged — organs untouched. O2 quiz
   re-run (kb_search touches dify).
3. Leonard live phone soak (same drills as tonight). One clean week →
   default flips to v2 → v1 cascade deleted (~700 lines) with its
   breadcrumb logic.
4. Cost/latency: today ≤3 LLM calls per message (classify + RAG +
   compose); v2 = one loop × 1–3 tool calls, tools are local HTTP (ms).
   Same ballpark, capped by max-iterations.

## Open questions (decide at build time)

- Offer/PDF fulfillment: deterministic post-tool handler when the agent's
  reply ends in an offer (lean yes — keeps "yes please" off the LLM
  roulette) vs. agent-managed.
- dify #34 NOT_FOUND marker — IN scope (kb_search needs an honest miss
  signal; kills the stall-repair hack).
- History window N and trimming for long threads (token budget).
- Anything else reading `_THREAD` today (SLA tick? closer clarify-once?)
  must move to `agent_state` in the same change.
