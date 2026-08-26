# Cold start — bring the whole appliance back up

Everything was stopped cleanly on 2026-08-24 (ports closed, VM down).
Nothing deleted — containers/volumes/session intact. Order matters:
VM first, then containers, then the three local APIs.

## 0. From where

All commands assume the product repo:

```
cd /Users/leonard/Documents/WORK/MJCX/Projects/trade-agent-appliance
DIFY=/Users/leonard/Documents/WORK/MJCX/Projects/pull_all_repo_here/glue/dify/docker
```

## 1. Colima (Docker VM)

```bash
colima start          # reuses saved config (currently 8GB RAM / 45GB disk)
```

## 2. Containers

```bash
# evolution-api + its postgres (WhatsApp session survives — NO QR rescan)
docker start evo evo-postgres

# dify stack (15 containers: api, worker, nginx :8180, weaviate, ...)
docker compose -f $DIFY/docker-compose.yaml start
```

Wait ~15–20s, then `curl -s -o /dev/null -w '%{http_code}' localhost:8080`
→ 200 means evo is up. Dify console: http://localhost:8180

## 3. Local APIs (three uvicorns, backgrounded)

`env -u PYTHONPATH` discipline is mandatory (spike-log trap #6).

```bash
nohup env -u PYTHONPATH RULES_PATH=spine/rules/pricing_rules.example.json \
        calc/.venv/bin/uvicorn app:app \
        --app-dir calc --host 0.0.0.0 --port 8100 >> /tmp/calc.log 2>&1 &
nohup env -u PYTHONPATH calc/.venv/bin/uvicorn spine_api:app \
        --app-dir spine --host 0.0.0.0 --port 8101 >> /tmp/spine.log 2>&1 &
nohup env -u PYTHONPATH calc/.venv/bin/uvicorn mock_responder:app \
        --app-dir glue --host 0.0.0.0 --port 8102 >> /tmp/glue.log 2>&1 &
```

(RULES_PATH is mandatory for calc — without it the app defaults to the
container-only path `/data/rules/…` and crashes on startup.)

## 4. Verify (all should answer)

```bash
curl -s localhost:8100/health   # calc   -> ok
curl -s localhost:8101/health   # spine  -> ok
curl -s localhost:8102/health   # glue   -> {"ok":true,...,"dry_run":false}
curl -s -o /dev/null -w '%{http_code}\n' localhost:8080    # evo     -> 200
curl -s -o /dev/null -w '%{http_code}\n' localhost:8180    # dify    -> 307
```

Then confirm WhatsApp is really connected before trusting replies:
`docker logs evo 2>&1 | grep -i "mjcx-test"` → look for state `open` /
CONNECTED. If it shows logout/QR instead, see
`runbooks/whatsapp-qr-rescan.md`.

## Optional: chatwoot — A6 human-inbox (started when escalations matter)

```bash
# one-time: secrets live in the clone's untracked .env (see spike-log A6)
# boot (repos stay whole; override lives in the product repo):
docker network create evo-net 2>/dev/null
docker compose -p chatwoot \
  -f $PULL/channels/chatwoot/docker-compose.production.yaml \
  -f compose/chatwoot.override.yaml up -d
# first boot only, once rails answers:
docker exec chatwoot-rails-1 bundle exec rails db:setup
```

Staff UI `http://localhost:3000` (login in `.env`: CHATWOOT_ADMIN_*).
evo needs the global switch to bridge: recreate it with `-e CHATWOOT_ENABLED=true`
(see §2 recipe) plus `POST /chatwoot/set/mjcx-test` — values recorded in
`.env` (CHATWOOT_*) and docs/spike-log.md. The glue escalation hook posts
the A6 package automatically; staff send PUBLIC replies inside chatwoot and
they go out over WhatsApp.

## Port map

| Port | Service | Started by |
|---|---|---|
| 8100 | calc | uvicorn (step 3) |
| 8101 | spine | uvicorn (step 3) |
| 8102 | glue | uvicorn (step 3) |
| 8080 | evolution-api | docker (step 2) |
| 8180 | dify nginx (console+API) | docker (step 2) |
| 15432 | evo-postgres (internal only) | docker (step 2) |
| 3000 | chatwoot rails (staff inbox) | docker (A6 section) |
| 8090 | console UI (stamp compose only) | docker |
| 8200 | carbone — OPTIONAL, not auto-started |

## Optional: carbone (B4 formal-PDF quotes — glue calls it automatically)

```bash
docker run -d --name carbone-test -p 8200:4000 carbone/carbone-ee:latest
# wait ~10s, then: curl localhost:8200/status -> {"success":true,...}
```

carbone-ee **v5 API is async** (trap #19 in docs/spike-log.md):
`POST /template` (multipart) → templateId → `POST /render/{templateId}` →
renderId → `GET /render/{renderId}` returns the binary exactly ONCE.
PDF conversion is license-gated → glue renders docx, then converts:
`soffice --headless --convert-to pdf --outdir spine/quotes_pdf <file.docx>`
(first conversion after boot can take ~2 min; later ones are seconds).
Gate: `env -u PYTHONPATH calc/.venv/bin/python tests/test_b4.py`
(live document send: add `SEND_JID=<jid>`).

## O1 stamp — fresh CLIENT box (the product, not this dev Mac)

```bash
git clone <product repo> && cd trade-agent-appliance
cp .env.example .env   # fill GLM/EVO/chatwoot/staff-boss values + CONSOLE_TOKEN
docker compose -f compose/docker-compose.appliance.yml up -d
docker compose -f compose/docker-compose.appliance.yml exec chatwoot-rails \
  bundle exec rails db:setup     # first boot only
```

Brings up calc/spine/glue + **console :8090** + evo(+pg) + chatwoot(+pg/redis)
+ carbone + n8n on one flat network (unique names — no trap-#16 DNS
collisions). dify boots separately from its own repo; point glue via
DIFY_BASE_URL/USE_DIFY. The console serves the SPA and proxies /spine + /glue
same-origin (nginx inside the container).

First-boot checklist (order matters):
0. Console http://localhost:8090 → paste CONSOLE_TOKEN → walk Setup tabs:
   Connect (QR) → Catalog import → Knowledge docs → Pricing backtest.
   The O2/O3 gates + go-live switch are enforced here.
1. WhatsApp: create instance + QR scan (`runbooks/whatsapp-qr-rescan.md`,
   or just the console Connect tab)
2. evo webhook → `http://<host>:8102/webhook/evo` for messages.upsert
3. chatwoot seed (admin + evo-bridge users) → spike-log 2026-08-24 A6 entry
   has the rails-runner script; inbox named after instance w/ webhook
   `http://evo:8080/chatwoot/webhook/{instance}`; then `POST /chatwoot/set/…`
4. n8n: import + activate `n8n/workflows/*.json`
5. B6/SLA recipients in `.env` (STAFF_WHATSAPP / BOSS_WHATSAPP)

Not yet scripted: steps 1–5 are manual (~20 min; the console absorbs most of
the old checklist UI-side). Script = future O2 work.

## Console dev mode (this Mac)

```bash
cd console && npm install && npm run dev     # Vite :5173, proxies /spine+/glue
```
Login accepts any token when glue runs without CONSOLE_TOKEN set; with it
set (now in .env), paste that value. Prod image: see console/Dockerfile +
the `console` service in the stamp compose.

## Optional: n8n (the clock — B6 follow-ups + SLA beacon)

```bash
docker run -d --name n8n -p 5678:5678 --network evo-net \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE=Asia/Jakarta -e TZ=Asia/Jakarta \
  -e N8N_SECURE_COOKIE=false \
  docker.n8n.io/n8nio/n8n:latest
# import the scheduled ticks (workflows live in n8n/workflows/, config-as-code):
for wf in n8n/workflows/*.json; do
  docker cp "$wf" n8n:/tmp/wf.json
  docker exec n8n n8n import:workflow --input=/tmp/wf.json
done
docker exec n8n n8n list:workflow   # grab ids
docker exec n8n n8n update:workflow --id=<id> --active=true   # per workflow
# NOTE: update needs a restart to show in UI: docker restart n8n
```

UI: http://localhost:5678 (first visit asks owner signup — local spike).
Workflows just POST two glue endpoints; all logic/approvals live in glue:
- `/b6/tick` every 4h — quotes sent >48h w/o follow-up → DRAFT to staff WA,
  approve by replying APPROVE <qid> (v1: manual send)
- `/a6/sla_tick` every 15min — chatwoot open conversations with no HUMAN
  reply >2h → beacon to boss WA (bridge/bot messages don't count)
Test manually any time: `curl -X POST localhost:8102/b6/tick` (add
`?hours=0` to include fresh quotes) · `curl -X POST localhost:8102/a6/sla_tick`.
Configure via .env: STAFF_WHATSAPP / BOSS_WHATSAPP / FOLLOWUP_HOURS /
SLA_HOURS. Idempotent — S8 events prevent double nudges.

## Optional: postiz — Phase C social publisher (:13000)

**v1.2 (2026-08-26): run it from the compose file, NOT docker run** — the
compose pins `postiz-app:v2.11.2` (trap #42: `latest` ≥ v2.12 needs a
Temporal stack or the backend crashes while the frontend LOOKS fine).

```bash
docker compose -f compose/docker-compose.appliance.yml --env-file .env \
  up -d postiz-postgres postiz-redis postiz
# if the port is squatted by an old hand-run container:
#   docker rm -f postiz postiz-postgres postiz-redis   (safe pre-key: nothing persists)
```

⚠ the image serves on **5000**, not 3000 (trap #25). First boot: open
http://localhost:13000 → owner signup → connect client channels → create
API key → put in `.env` POSTIZ_API_KEY. Until then approvals still work;
push is skipped + logged (`postiz_push_skipped` in S8).
Verify health: all four pm2 processes `online`
(`docker exec trade-agent-postiz-1 pm2 list`) + backend log shows
"🚀 Backend is running".

## Shutting it all down again

```bash
pkill -f "uvicorn app:app --app-dir calc"
pkill -f "uvicorn spine_api:app --app-dir spine"
pkill -f "uvicorn mock_responder:app --app-dir glue"
docker stop evo evo-postgres
docker stop n8n 2>/dev/null
docker compose -p chatwoot -f $PULL/channels/chatwoot/docker-compose.production.yaml \
  -f compose/chatwoot.override.yaml stop   # when chatwoot was started
docker compose -f $DIFY/docker-compose.yaml stop
colima stop
```

## Gotchas while running

- **The three uvicorns have no restart policy** — a stray pkill, crash, or
  anything else kills buyer replies SILENTLY (evo can't deliver the
  webhook). Guard: `nohup scripts/dev_keepalive.sh &` (checks /health every
  30s and revives). On client boxes the O1 stamp solves this properly via
  compose `restart: unless-stopped`.

- evo dies of Node heap OOM (~2GB) sometimes when dify's 15 containers are
  also up — messages sent while it's down are silently LOST.
  `docker update --restart unless-stopped evo evo-postgres` is set, so it
  usually self-heals; still, watch memory.
- Mac sleep kills containers; step 2 alone revives them.
- GLM key: glm-4.6/4.7 return 1113 (insufficient balance) even after the
  Aug-24 top-up — Leonard is checking the console. Default model is
  **glm-4.5-air** (passes the 17-case classifier gate + voice eval);
  embeddings still blocked, so RAG stays on economy indexing.
