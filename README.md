# MJCX Trade Agent Appliance

Plug-and-play AI agent product line for foreign-trade SMEs.
Blueprint & flowchart: see `pull_all_repo_here/Trade_Agent_Appliance_Flowchart_v1_0.md`
and `pull_all_repo_here/WEAVE_PLAN.md` (same parent folder).

## v1 modules (per flowchart)
- **Phase A** Inquiry auto-response (evo → dify → chatwoot) — **LIVE**
- **Phase B** Quoting & pricing (dify → calc → carbone) — core live; formal-PDF in chat = current spike
- **Phase C** Social ops (dify → postiz) — not started

## Layout
```
calc/      ▣ calc  — pricing engine (OUR IP). LLM parses, THIS computes.
spine/     ▣ spine — SQLite: catalog (S1), pricing rules (S2), customers (S3),
                     quotes (S5), events (S8). Source of truth for dashboards.
glue/      ▣ glue  — mock-dify router (:8102): webhook intake, routing, voice
                     generation, chatwoot escalation hook. dify replaces the brain;
                     the glue stays.
dify/      prompts (voice_guide, a3_classify) + workflow DSL exports + console API
tests/     gates: classifier eval, voice gate, e2e money path
docs/      spike-log.md = single source of truth for state & traps
compose/   docker-compose.appliance.yml (stamp, drifted — see HANDOFF §2)
           + chatwoot.override.yaml (A6 topology)
runbooks/  cold-start.md (boot the whole stack), whatsapp-qr-rescan.md
```

## Principles (from flowchart)
1. LLM never does arithmetic — `calc` does.
2. One source of truth per concept — spine owns identity/pricing/quotes/events.
3. Repos stay whole — OSS runs unmodified in containers, HTTP-only integration.
4. Client variation lives in DATA (S1/S2/S3) + .env, never code edits.
5. Uncomputable = escalate with rules-gap hint, never guess.

## Quick start

Don't hand-roll it — the verified boot order lives in
[`runbooks/cold-start.md`](runbooks/cold-start.md) (colima, containers,
three uvicorns, health checks, chatwoot/carbone optional sections).

```bash
# gates only (no stack needed for unit tests):
python3 calc/test_calculator.py
env -u PYTHONPATH calc/.venv/bin/python tests/test_classify.py   # needs GLM key
env -u PYTHONPATH calc/.venv/bin/python tests/e2e_spike.py       # needs calc+spine up
```
