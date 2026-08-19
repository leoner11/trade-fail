# MJCX Trade Agent Appliance

Plug-and-play AI agent product line for foreign-trade SMEs.
Blueprint & flowchart: see `pull_all_repo_here/Trade_Agent_Appliance_Flowchart_v1_0.md`
and `pull_all_repo_here/WEAVE_PLAN.md` (same parent folder).

## v1 modules (per flowchart)
- **Phase A** Inquiry auto-response (evo → dify → chatwoot)
- **Phase B** Quoting & pricing (dify → calc → carbone)
- **Phase C** Social ops (dify → postiz)

## Layout
```
calc/      ▣ calc  — pricing engine (OUR IP). LLM parses, THIS computes.
spine/     ▣ spine — SQLite: catalog (S1), pricing rules (S2), customers (S3), quotes (S5)
docs/      design docs
compose/   docker-compose.appliance.yml — the full stamp (S7)
dify/      workflow DSL exports (filled during spike)
runbooks/  client-facing ops runbooks (QR rescan etc.)
```

## Principles (from flowchart)
1. LLM never does arithmetic — `calc` does.
2. One source of truth per concept — spine owns identity/pricing/quotes.
3. Repos stay whole — OSS runs unmodified in containers, HTTP-only integration.
4. Client variation lives in DATA (S1/S2/S3) + .env, never code edits.
5. Uncomputable = escalate with rules-gap hint, never guess.

## Quick start (spike)
```bash
# calc tests (no deps beyond python)
python3 calc/test_calculator.py

# calc API (needs: uv venv && uv pip install fastapi uvicorn)
uv run --directory calc api

# full stack (needs colima/docker)
docker compose -f compose/docker-compose.appliance.yml up -d
```
