# Foreign-Trade AI Suite — Repo Inventory & Weave Plan

Pulled: 2026-08-19 · 18 repos · ~2.2 GB (shallow clones)
Location: `/Users/leonard/Documents/WORK/MJCX/Projects/pull_all_repo_here`

The product (from Leonard's spec): bilingual CN/EN AI-agent suite for export/foreign-trade
companies. 5 external agents (market intel, positioning, inquiry auto-response, social,
meetings) + 6 internal agents (quoting, customer memory, SOP, product knowledge, docs,
procurement). Strategy: weave proven OSS, build the missing pieces.

---

## 1. Inventory

### glue/ — orchestration backbone
| Repo | Covers | License | Run |
|---|---|---|---|
| **dify** (langgenius) | Agent workflows + RAG + model routing. CN founders, bilingual UI. The brain-orchestrator | Apache 2.0 **modified** (multi-tenant/hosting restriction) | `docker/docker-compose-template.yaml` |
| **n8n** | Event/webhook glue between all systems; 400+ integrations | **Sustainable Use** (fair-code, NOT OSI; fine for internal use + client delivery, can't resell as SaaS) | official docker image `docker.n8n.io/n8nio/n8n` |

### channels/ — inquiry auto-response entry points
| Repo | Covers | License | Run |
|---|---|---|---|
| **evolution-api** | WhatsApp gateway (Baileys), webhooks, multi-account. De-facto standard | Apache 2.0 modified | `docker-compose.dev.yaml` |
| **chatwoot** | Omni-channel team inbox: WhatsApp/email/web, human handoff UI, API-first | MIT (enterprise/ dir exempt) | `docker-compose.production.yaml` |
| **LangBot** | Multi-IM bot platform (Telegram/WeChat-ish/Discord/LINE), knowledge base, plugins. CN project | Apache 2.0 | Dockerfile / `docker-compose.cn.yml` |

### brain/ — RAG knowledge (product encyclopedia, SOP answers, quote knowledge)
| Repo | Covers | License | Run |
|---|---|---|---|
| **anything-llm** | Local-first RAG over catalog PDFs/spec sheets. Easiest product-百科 win | MIT | `docker/docker-compose.yml` |
| **tgo** | AI customer-support platform: agent teams + RAG + omni-channel. Reference architecture (TS) | Apache 2.0 modified | `docker-compose.cn.yml` |

### data-spine/ — customer memory + pricing + procurement
| Repo | Covers | License | Run |
|---|---|---|---|
| **twenty** | Open-source CRM "designed for AI", GraphQL API, MCP server exists | **AGPLv3** (+2 exceptions) | `packages/twenty-docker/docker-compose.yml` |
| **erpnext** | Full ERP: quoting, pricing, supplier ledger, POs, stock. GPL-3.0 | GPL-3.0 | via `frappe/frappe_docker` (not cloned) |

### meetings/ — 会议助手
| Repo | Covers | License | Run |
|---|---|---|---|
| **meetily** | Whisper/Parakeet local transcription → diarization → summaries. 29k⭐ MIT, very active | MIT | `backend/docker-compose.yml` |

### social/ — 社媒运营
| Repo | Covers | License | Run |
|---|---|---|---|
| **postiz-app** | Self-hosted Buffer: scheduling + AI gen, all platforms | **AGPL** | `docker-compose.dev.yaml` |

### docs/ — 智能文件
| Repo | Covers | License | Run |
|---|---|---|---|
| **carbone** | DOCX/PDF/XLSX from templates + JSON. Quotes/contracts/packing lists. Has MCP server | **Carbone CE** (AGPL-ish: free unless you resell doc-gen-as-a-service) | npm/docker |

### market-intel/ — 市场情报
| Repo | Covers | License | Run |
|---|---|---|---|
| **RSSHub** | RSS feeds for everything (news, Google News, trade portals). Data source layer | **AGPL** | `docker-compose.yml` |

### sourcing/ — 选品 & procurement helpers
| Repo | Covers | License | Run |
|---|---|---|---|
| **1688-cli** | AI-agent CLI for 1688 sourcing/supplier eval/procurement inquiry | MIT | npm |
| **amazon-skills** | Agent skills: Amazon product research, listing audits | MIT | agent-skill files |

### patterns/ — small but exactly-on-point references
| Repo | Why it matters | License |
|---|---|---|
| **email-quote-automation** | Email inquiry → parse → quotation generator (custom manufacturing!). The exact quoting-agent pattern, minimal | MIT |
| **quotr** | PHP quote → PDF/DOCX/HTML. ⚠️ **no license file = all rights reserved; read code, don't copy** | none |
| **SkillHuoke** | 外贸 AI 获客 + CRM workflow platform (CN). Reference for how a CN shop assembled this | MIT |

---

## 2. ⚠️ License cheat-sheet (for client work)

- **Safe to build a business on / deliver to clients:** anything-llm (MIT), meetily (MIT), chatwoot (MIT), LangBot/evolution-api/tgo/dify (Apache-2.0-*modified*: fine self-hosted for one client; the clause restricts multi-tenant hosting & logo — read `LICENSE` before white-labeling)
- **AGPL (twenty, postiz, RSSHub, carbone CE):** fine self-hosted for clients; you must share source of modifications if users interact over a network. Don't embed in a closed multi-tenant SaaS.
- **n8n Sustainable Use:** internal use + client delivery OK; you cannot sell n8n itself as a service.
- **ERPNext GPL-3.0:** fine as a separate service the suite talks to via API; keep it a separate deployment, don't mix code into your app.
- **quotr:** no license — treat as read-only reference.

Pragmatic rule: keep each OSS as its **own container/service**, integrate only via **HTTP APIs/webhooks**, never copy code between repos. That keeps every license uncontaminated and components swappable.

---

## 3. The weave — target architecture

```
                         ┌─────────────────────────────────────────────┐
                         │                CLIENT's TEAM                │
                         │   (WhatsApp / WeChat / email / web chat)    │
                         └──────┬──────────────┬──────────────┬────────┘
                                │              │              │
                    ┌───────────▼───┐   ┌──────▼──────┐  ┌────▼─────┐
   channels/        │ evolution-api │   │  LangBot /  │  │ IMAP →   │
                    │  (WhatsApp)   │   │  wechaty    │  │ n8n poll │
                    └───────┬───────┘   └──────┬──────┘  └────┬─────┘
                            │  webhook         │              │
                            └────────┬─────────┴──────────────┘
                                     ▼
                          ┌─────────────────────┐        ┌──────────────────┐
   glue/                  │        n8n          │◄──────▶│      dify        │
                          │ (routing, CRM sync, │        │ (agent workflows,│
                          │  escalations, cron) │        │  RAG pipelines)  │
                          └──┬────┬────┬────────┘        └───┬──────┬───────┘
                             │    │    │                     │      │
             ┌───────────────▼┐ ┌─▼──────────┐  ┌────────────▼──┐ ┌▼─────────────┐
   data-spine│     twenty     │ │  erpnext   │  │ anything-llm  │ │  carbone     │
             │ (customer mem, │ │ (quotes,   │  │ (catalog RAG: │ │ (quote PDF/  │
             │  history,terms)│ │  pricing,  │  │  specs/SOPs)  │ │  contract/PL)│
             └────────────────┘ │  suppliers)│  └───────────────┘ └──────────────┘
                                └────────────┘
   peripheral: meetily (meetings→action items→twenty) · postiz (social, cron-fed)
   · RSSHub (feeds→dify digest→WhatsApp) · 1688-cli/amazon-skills (sourcing agents)
```

**Contract-first integration points (all HTTP, no code mixing):**
1. evolution-api → n8n webhook on incoming message
2. n8n → dify `/v1/chat-messages` (RAG answer w/ catalog + customer context from twenty)
3. n8n → chatwoot API (open conversation, human handoff for flagged/complex)
4. dify agent → erpnext REST API (price lists, Item, Supplier Quotation) for quoting
5. dify agent → carbone API (render quote PDF) → send back via evolution-api
6. meetily summary → n8n → twenty (notes, tasks, commitments)
7. RSSHub feeds → n8n cron → dify digest → morning WhatsApp/email push

---

## 4. Try-order (what I'd stand up first)

**Phase 0 — kick tires (half a day)**
1. `dify` — up, create one workflow, attach an LLM key
2. `anything-llm` — drop a fake product catalog PDF, ask questions (product-百科 PoC)
3. `evolution-api` + `chatwoot` — scan a WhatsApp QR, message yourself, see handoff

**Phase 1 — first end-to-end thread (the money path): inquiry → answer**
evolution-api → n8n → dify(RAG over anything-llm-style KB) → reply. Flag-if-unsure → chatwoot.
This one agent alone (询盘智能应答) is a sellable product.

**Phase 2 — quoting**: same thread, + erpnext price list lookup + carbone template →
PDF quote. Use `patterns/email-quote-automation` as the design reference.

**Phase 3 — memory & meetings**: twenty as customer memory (n8n syncs every conversation
thread); meetily for CN/EN meetings → action items → twenty.

**Phase 4 — peripheral agents**: postiz social, RSSHub digests, sourcing CLIs as dify tools.

**Gaps with no real OSS (= our IP):**
- **Quoting agent** (rules + tiers + margins) — only primitive references exist
- **SOP with photo verification** — genuinely greenfield
- **WeChat**: all OSS routes (wechaty etc.) violate WeChat ToS → risk note for clients; official
  WeCom (企业微信) API is the compliant path; LangBot supports it

---

## 5. Deep-dive findings (per-repo, post-clone inspection)

### The overlap problem — "who brings its own X"

| Capability | dify | anything-llm | tgo | LangBot | chatwoot | twenty | erpnext |
|---|---|---|---|---|---|---|---|
| RAG / knowledge base | ✔ | ✔ | ✔ `tgo-rag` | ✔ basic | ✖ | ✖ | ✖ |
| Workflow engine | ✔ | cron tasks | ✔ `tgo-workflow` | ✖ | automation rules | ✔ | ✔ |
| Human agent inbox | ✖ | ✖ | ✔ workspace | ✖ | ✔✔ (best) | ✖ | ✖ |
| CRM / contacts | ✖ | ✖ | visitor mgmt | ✖ | light contacts | ✔✔ (best) | ✔ full CRM module |
| Own channel widget | ✖ | ✔ embed | ✔ web+miniapp | ✖ | ✔ website widget | ✖ | ✖ |
| Own IM server | ✖ | ✖ | ✔ WuKongIM | ✖ | ✖ | ✖ | ✖ |

**Do NOT run tgo + chatwoot + anything-llm + dify simultaneously** — that's 4 agent UIs,
3 RAGs, 3 workflow engines. Pick per client (below).

### Per-repo reality check

- **tgo** — the heavyweight. Docker Compose CN bundle = **17 services**: postgres, redis,
  WuKongIM (own IM server), tgo-rag(+worker/beat), tgo-ai, tgo-api, tgo-plugin-runtime,
  tgo-device-control, tgo-platform (channel intake: WeChat/Feishu/DingTalk/Telegram/Slack/email),
  tgo-workflow(+worker), web, widget-js, nginx, certbot. Monorepo of 15 sub-repos.
  Brings: WeChat **Official Account + Mini Program** widgets (the compliant WeChat surface),
  order/logistics/product cards, smart handoff, visitor management = its own mini-Chatwoot.
  Verdict: it IS the product for a China-facing client; don't pair with chatwoot/dify/anything-llm.
- **evolution-api** — the connector gem. Native built-in integrations: **Chatwoot, Dify,
  OpenAI, Typebot**, RabbitMQ/Kafka/SQS, S3/MinIO. Both Baileys (free, ToS-grey) and official
  WhatsApp Cloud API. Verdict: WhatsApp front door in the global stack; the weave is
  literally a config screen, not custom code.
- **chatwoot** — community = pure helpdesk (omnichannel inbox, canned responses, auto-assignment,
  campaigns, Shopify/Linear integrations, reports). Its AI "Captain" lives in `enterprise/` =
  **paid edition, not ours**. Has light contact management (custom attributes/segments) — treat
  as inbox-only, NOT the CRM (twenty owns that).
- **LangBot** — the Chinese-IM bridge: **WeCom (企业微信) ✅ official, personal WeChat, DingTalk,
  Lark/Feishu, QQ**, Telegram/Discord/Slack/LINE/KOOK. Built-in RAG, hundreds of plugins, MCP,
  web panel, multi-pipeline (different bot per scenario). README literally suggests
  "connect n8n/Dify workflows to WeCom/DingTalk". Verdict: use for WeCom, not as the brain.
- **anything-llm** — more than RAG: multi-user + permissions (Docker ed.), embeddable widget,
  scheduled agent tasks, model routing, memories, MCP. Verdict: perfect as the **internal ops
  KB** (产品百科 + SOP for workers) — zero-config, client's office staff can self-serve.
  Skip it for customer-facing flows (dify owns that).
- **twenty** — "objects, views, workflows, agents, extend as code". Ships `twenty-claude-skills`,
  codex plugin, client SDK, Zapier. This is the CRM an agency can customize per client fast.
- **erpnext** — has its own CRM + full quoting/pricing/supplier/PO/manufacturing. Keep at arm's
  length (GPL): deploy standalone, integrate via REST only. It's the pricing-truth DB.
- **carbone** — templates authored in Word/LibreOffice with `{d.marker}` tags, JSON in →
  PDF/DOCX/XLSX out, multilingual templates, free Docker edition v5+. The doc-gen engine, full stop.
- **meetily** — clean 3-service compose (whisper-server, backend, web-ui), local-first,
  OpenAI-compatible endpoints. Simple to stand up.
- **postiz** — scheduling + AI generation + lead capture; now ships an agent CLI (scriptable).
- **1688-cli** — surprise powerhouse: full 1688 lifecycle — product search, supplier
  scraper/research, **image search, pre-sale supplier inquiry, cart, checkout, order tracking,
  post-sale seller chat, 旺旺 inbox**. JSON output for agents. This is the procurement agent's hands.
- **amazon-skills** — installable agent skills (选品验证, listing health check, keyword/market
  analysis) for Claude-Code-style agents. Feed to our dify/Hermes agents as reference patterns.
- **SkillHuoke** — solo-dev Next.js prototype (v0.11→v0.43 zips committed in-repo 😬).
  Lead-gen CRM + AI 开发信 drafts. **Reference for UX only, do not build on it.**
- **email-quote-automation** — 822 lines Python. IMAP → translate → `quote_calculator.py`
  (hardcoded price tables) → CN+EN quote email. Its `pricing_rules_example.md` is gold:
  a clean markdown format for material base prices / size coefficients / process fees /
  quantity discounts / terms — **the seed schema for our quoting agent** (LLM reads rules,
  deterministic code computes, or LLM computes w/ verification).
- **quotr** — one PHP file, no license. Idea reference only.

### Two concrete stacks (pick per client)

**Stack A — China-facing client (国内获客+客服):**
tgo (front: WeChat OA/MP widget + agent workspace + RAG) · LangBot (WeCom/DingTalk bridge)
· twenty (CRM) · erpnext (pricing/PO) · carbone (docs) · meetily · postiz
*No chatwoot, no evolution-api, no anything-llm, no dify — tgo already has agent+RAG+workflow.*

**Stack B — export/global client (外贸出海):**
evolution-api (WhatsApp, native Dify+Chatwoot integration) · dify (brain/RAG/workflows)
· chatwoot (human handoff, community ed.) · anything-llm (internal ops KB)
· twenty (CRM) · erpnext (pricing) · carbone (docs) · meetily · postiz · 1688-cli (sourcing)
*No tgo. LangBot only if WeCom needed.*

**Shared IP we build either way:** quoting rules engine (seeded from email-quote-automation's
schema) · SOP w/ photo verification · the n8n/HTTP glue layer · CN+EN digests.
