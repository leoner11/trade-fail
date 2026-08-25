#!/bin/bash
# Dev keepalive — revives the three local uvicorns within 30s of death.
# (Containers already have restart policies; these host processes don't.)
# Run once:   nohup scripts/dev_keepalive.sh >> /tmp/keepalive.log 2>&1 &
cd "$(dirname "$0")/.." || exit 1

start_calc()   { nohup env -u PYTHONPATH RULES_PATH=spine/rules/pricing_rules.generators.json \
                 calc/.venv/bin/uvicorn app:app --app-dir calc --host 0.0.0.0 --port 8100 >> /tmp/calc.log 2>&1 & }
start_spine()  { nohup env -u PYTHONPATH calc/.venv/bin/uvicorn spine_api:app \
                 --app-dir spine --host 0.0.0.0 --port 8101 >> /tmp/spine.log 2>&1 & }
start_glue()   { nohup env -u PYTHONPATH calc/.venv/bin/uvicorn mock_responder:app \
                 --app-dir glue --host 0.0.0.0 --port 8102 >> /tmp/glue.log 2>&1 & }

echo "[keepalive] watching calc/spine/glue every 30s"
while true; do
  curl -sf -m 5 localhost:8100/health >/dev/null || { echo "[keepalive] $(date '+%H:%M') calc down -> start"; start_calc; }
  curl -sf -m 5 localhost:8101/health >/dev/null || { echo "[keepalive] $(date '+%H:%M') spine down -> start"; start_spine; }
  curl -sf -m 5 localhost:8102/health >/dev/null || { echo "[keepalive] $(date '+%H:%M') glue down -> start"; start_glue; }
  sleep 30
done
