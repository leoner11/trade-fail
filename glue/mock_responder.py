#!/usr/bin/env python3
"""▣ glue — mock Phase A router (Task 2 of handoff).

evo webhook receiver that stands in for dify until Task 3. It walks the
flowchart's Phase A path with REAL organs:

    evo MESSAGES_UPSERT ──► :8102/webhook/evo
        A1  idempotency (drop webhook-retry dupes)
        A2  spine /resolve      -> S3 identity (who is this?)
        A3  GLM + a3_classify   -> {language,intent,...} (eval-passed prompt)
        A3-2 route:
            SPAM            -> silence (log only)
            GREETING/THANKS -> generated welcome reply (template fallback)
            OTHER           -> escalation holding reply
            SPEC_Q          -> spine /catalog lookup if SKU present (S1,
                               deterministic read), else dify RAG over the
                               client knowledge base (A3-Spec workflow),
                               else deflect stub
            COMPLAINT / CUSTOM_ODM / SHIPPING / OTHER -> escalation holding reply
            PRICE_Q         -> B-path: GLM parses lines (B1-1, closed S2 vocab)
                               -> calc /quote (B2-1, deterministic)
                                  OK       -> inline price reply (B3-2),
                                              quote saved to S5 as sent
                                  ESCALATE -> human-quote reply w/ rules gaps (B5)

Replies are GENERATED from dify/prompts/voice_guide.md (facts injected
verbatim, numbers guarded) with the static TEMPLATES below kept only as
failure fallback. They go out the same door via evo
POST /message/sendText/{instance}.
Margin never leaves calc's response here (X4: buyer-visible text is built
from price fields only).

Run:  env -u PYTHONPATH calc/.venv/bin/uvicorn mock_responder:app \
        --app-dir glue --host 0.0.0.0 --port 8102
Env:  reads .env (GLM_* , EVO_API_KEY). Optional overrides:
      EVO_URL, EVO_INSTANCE, SPINE_URL, CALC_URL, GLM_MODEL, DRY_RUN=1.
"""
import asyncio
import base64
import imaplib
import json
import math
import os
import re
import smtplib
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import date
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from email import policy
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

ROOT = Path(__file__).resolve().parent.parent


def _env_file() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


_FILE_ENV = _env_file()


def cfg(name: str, default: str = "") -> str:
    return os.environ.get(name) or _FILE_ENV.get(name) or default


EVO_URL = cfg("EVO_URL", "http://localhost:8080").rstrip("/")
EVO_KEY = cfg("EVO_API_KEY", "mjcx-spike-key")
INSTANCE = cfg("EVO_INSTANCE", "mjcx-test")
SPINE_URL = cfg("SPINE_URL", "http://localhost:8101").rstrip("/")
CALC_URL = cfg("CALC_URL", "http://localhost:8100").rstrip("/")
CW_URL = cfg("CHATWOOT_URL", "http://localhost:3000").rstrip("/")
CW_ACCOUNT = cfg("CHATWOOT_ACCOUNT_ID", "1")
CW_TOKEN = cfg("CHATWOOT_API_TOKEN")
# v1.2: spine is THE conversation store (S4). Chatwoot stays installed as a
# replaceable organ but is off unless explicitly re-enabled.
CHATWOOT_ENABLED = cfg("CHATWOOT_ENABLED", "0") == "1"
# Take-over replies must carry a HUMAN identity: CHATWOOT_API_TOKEN often
# belongs to the evo-bridge user (trap #28) — API messages posted with it
# show bridge as sender and /a6/sla_tick keeps beaconing. The ADMIN user's
# own access token (rails runner: User.access_token.token) is what marks
# a conversation human-handled.
CW_ADMIN_TOKEN = cfg("CHATWOOT_ADMIN_TOKEN", "")
CW_INBOX_NAME = cfg("CHATWOOT_INBOX_NAME", "")
CARBONE_URL = cfg("CARBONE_URL", "http://localhost:8200").rstrip("/")
SOFFICE = cfg("SOFFICE_PATH", "/Applications/LibreOffice.app/Contents/MacOS/soffice")
QUOTE_TEMPLATE = ROOT / "spine" / "templates" / "quote_template.docx"
PDF_DIR = ROOT / "spine" / "quotes_pdf"
# B4 document placeholders — per-client values arrive with O3 onboarding
# (rule #5: variation lives in config/.env, never code edits).
COMPANY_NAME = cfg("COMPANY_NAME", "MJCX Client Co")
INCOTERM_DEFAULT = cfg("DEFAULT_INCOTERM", "FOB")
PAYMENT_TERMS_DEFAULT = cfg("DEFAULT_PAYMENT_TERMS", "T/T 30% deposit")
LEAD_TIME_DEFAULT = cfg("DEFAULT_LEAD_TIME", "20-30 days after PI")
# B6/SLA tick jobs (n8n is just the clock; logic + approvals live here)
STAFF_WHATSAPP = cfg("STAFF_WHATSAPP", "")
BOSS_WHATSAPP = cfg("BOSS_WHATSAPP", "")
FOLLOWUP_HOURS = cfg("FOLLOWUP_HOURS", "48")
SLA_HOURS = cfg("SLA_HOURS", "2")
CW_BRIDGE_EMAIL = cfg("CHATWOOT_BRIDGE_EMAIL", "evo-bridge@mjcx.test")
POSTIZ_URL = cfg("POSTIZ_URL", "http://localhost:13000").rstrip("/")
POSTIZ_API_KEY = cfg("POSTIZ_API_KEY", "")
POSTIZ_PLATFORM = cfg("POSTIZ_PLATFORM", "linkedin")  # v1: one platform per post
# Email inquiry channel (docs/design-email-channel.md): transport only, the
# pipeline is THE SAME route() as WhatsApp. Off unless the client opts in.
EMAIL_ENABLED = cfg("EMAIL_ENABLED", "0") == "1"
EMAIL_IMAP_HOST = cfg("EMAIL_IMAP_HOST", "")
EMAIL_IMAP_PORT = int(cfg("EMAIL_IMAP_PORT", "993"))
EMAIL_SMTP_HOST = cfg("EMAIL_SMTP_HOST", "")
EMAIL_SMTP_PORT = int(cfg("EMAIL_SMTP_PORT", "587"))
EMAIL_USER = cfg("EMAIL_USER", "")
EMAIL_PASS = cfg("EMAIL_PASS", "")
EMAIL_FOLDER = cfg("EMAIL_FOLDER", "INBOX")
EMAIL_FROM_NAME = cfg("EMAIL_FROM_NAME", COMPANY_NAME)
MODEL = cfg("GLM_MODEL", "glm-4-flash")
DRY_RUN = os.environ.get("DRY_RUN") == "1"
USE_DIFY = cfg("USE_DIFY", "") == "1"
DIFY_URL = cfg("DIFY_BASE_URL", "http://localhost:8180").rstrip("/")
DIFY_A3_KEY = cfg("DIFY_A3_API_KEY", "")
DIFY_SPEC_KEY = cfg("DIFY_SPEC_API_KEY", "")
CONSOLE_TOKEN = cfg("CONSOLE_TOKEN", "")

# intent -> route, mirrors the code node in dify/dsl/a3_triage.yml. Used only
# when dify is unavailable (graceful dumb mode) or USE_DIFY is off.
ROUTE_MAP = {
    "SPEC_Q": "spec", "PRICE_Q": "price", "CUSTOM_ODM": "escalate_custom",
    "COMPLAINT": "escalate_complaint", "SHIPPING": "human",
    "GREETING": "greet", "THANKS": "welcome", "OTHER": "human", "SPAM": "silence"}

# Buyer-facing templates — voice per dify/prompts/voice_guide.md: mirror the
# buyer's language always, short, concrete. Keyed by classifier language
# prefix; en is the fallback. X4: no margin/internal content in any of these.
TEMPLATES = {
    "en": {
        "greet": ("Hello! I'm the sales assistant. Ask me about products, "
                  "specs, MOQ or pricing and I'll help right away."),
        "welcome": ("You're welcome! If anything else comes up — specs, "
                    "quantities, pricing — just message me here any time."),
        "spec_stub": ("Let me check the full spec sheet with our product team "
                      "and come back to you shortly."),
        "capability": ("We build diesel generator sets and transfer switches "
                       "— our line: {line}. Tell me what you need to power "
                       "and I'll point you to the right model."),
        "not_ours": ("That item isn't our line, to be straight with you — we "
                     "focus on {line}. If it's power equipment you need, "
                     "though, tell me the application and I'll quote right "
                     "here."),
        "custom": ("That request needs a tailored quotation — I've flagged it "
                   "for our engineer ({reason}). A human will follow up shortly."),
        "calc_down": ("Our pricing system is briefly offline — a human will "
                      "send you the price shortly."),
        "escalate_gaps": ("This one needs a manual quotation (it falls outside "
                          "our standard pricing rules). Our team will get back "
                          "to you with numbers shortly."),
        "price_ok": ("Thank you! Here is your indicative price:\n{lines}\n"
                     "Total: {currency} {total:,.2f} "
                     "(qty discount {discount:.0f}% included)\n"
                     "Valid until {valid_until}. Want a formal PDF quotation?"),
        "pdf_offer": "Want me to prepare a formal PDF quotation?",
        "formal_offer": "The official quotation PDF is on its way right here "
                        "in this chat.",
        "human": ("Thanks for your message — this needs personal attention from "
                  "our team. A colleague will follow up here shortly."),
        "complaint": ("We're very sorry about this. Your message has been "
                      "flagged as URGENT and our team is on it — a human will "
                      "reply here shortly."),
        "internal_price": ("Thanks for asking! Some of the items you mentioned "
                           "are quoted by our team only. I've passed your "
                           "request to a colleague who will confirm the "
                           "numbers with you right here shortly."),
        "manual_quote": ("Great question! Our team is preparing your "
                         "quotation now — a colleague will send the numbers "
                         "right here shortly."),
    },
    "zh": {
        "greet": ("您好！我是销售助手。欢迎咨询产品规格、MOQ 或价格，"
                  "我会立即为您解答。"),
        "welcome": ("不客气！如需了解更多产品规格、数量或价格信息，"
                    "随时联系我。"),
        "spec_stub": ("完整规格书正在为您核对，我们的同事稍后回复您。"),
        "capability": ("我们是做柴油发电机组和转换开关的厂家——产品线：{line}。"
                       "告诉我您的用途，我帮您推荐合适的型号～"),
        "not_ours": ("说实话，这个不在我们的产品线里哦～我们主打{line}。"
                     "如果是电力设备方面的需求，告诉我用途，我可以在聊天里直接报价。"),
        "custom": ("该需求需要定制报价（{reason}）——已为您标记给工程师，"
                   "稍后将有人工跟进。"),
        "calc_down": ("报价系统短暂维护中，人工将尽快为您提供价格。"),
        "escalate_gaps": ("该需求超出标准报价规则，需要人工核算。"
                          "我们的团队将尽快回复您具体价格。"),
        "price_ok": ("感谢您的询价！以下是参考价格：\n{lines}\n"
                     "合计：{currency} {total:,.2f}（已含数量折扣 {discount:.0f}%）\n"
                     "有效期至 {valid_until}。如需正式 PDF 报价单请告知。"),
        "pdf_offer": "需要我为您准备一份正式的 PDF 报价单吗？",
        "formal_offer": "正式报价单（PDF）稍后直接发到本聊天窗口。",
        "human": ("感谢您的留言——此事需由我们的团队亲自处理，"
                  "同事将尽快在此回复您。"),
        "complaint": ("非常抱歉给您带来不便。您的消息已被标记为紧急，"
                      "我们的团队正在处理，将尽快回复您。"),
        "internal_price": ("感谢咨询！您提到的部分产品由团队专门报价，"
                           "已将您的需求转交同事，稍后将在此为您确认具体价格。"),
        "manual_quote": ("好的！我们的团队正在为您准备报价，"
                         "同事会很快把具体数字发给您。"),
    },
}


def tt(lang: str, key: str) -> str:
    return TEMPLATES.get((lang or "en")[:2], TEMPLATES["en"])[key]


# --- grounded capability / availability handling ---------------------------
# A real sales thread answers "do you even have X?" plainly instead of
# stalling. Both checks are DETERMINISTIC glue code (no prompt roulette),
# and every fact they allow still comes from spine/calc — a negative is
# grounded when the item matches no SKU in S1 and nothing in the KB.

_CAPABILITY_RES = [
    r"\bwhat\s+(do|does|is|are)\s+(you|u|yr|your)\b.*\b(do|sell|make|build|"
    r"offer|supply|export|produce|company|factory|business)\b",
    r"\bwhat\s+(products?|range|lines?)\s+(do|you|have|sell)\b",
    r"\bwho\s+are\s+(you|u)\b",
    r"\bwhat\s+(company|business)\s+is\s+this\b",
    r"你们?(是做什么|做什么的|是干什么的|卖什么|主营|有哪些?产品|生产什么|经营什么|是什么公司)",
    r"\bapa\s+(yang\s+)?(anda|kalian|perusahaan)\s+(jual|buat|produksi)\b",
]

# Pure-agreement messages ("yes please", 好的, ya) answering OUR OWN offer.
# FULL-match only — "yes but we need 500 units custom" must route normally.
_AGREEMENT_RES = [
    r"^\s*(?:yes|yeah|yep|yea|sure|ok(?:ay)?|okey|please(?: do)?|yes ?please|"
    r"pls|plz|go ahead|sounds good|i(?:'| a)m interested|interested|deal)\s*"
    r"[!.~ ]*\s*$",
    r"^\s*(?:好|好的|好啊|好呀|可以|可以呀|要|需要的|行|行啊|嗯+|哦克|ok的)\s*"
    r"[吧呢啊呀～~！!。.\s]*$",
    r"^\s*(?:ya|ya ?betul|baik|boleh|silakan|oke|ok)\s*[!.~ ]*\s*$",
]


def _is_agreement(text: str) -> bool:
    return any(re.match(p, text.strip(), re.I) for p in _AGREEMENT_RES)


# Bare engagement-readiness ("so ok, let's go") is a buyer leaning IN.
# Handing that to a human reads cold (live test 2026-08-25); it gets the
# anchored welcome/steer instead.
_ENGAGE_RES = [
    r"^\s*(?:so\s+)?ok(?:ay)?[,.]?\s*(?:then\s+)?(?:lets?|let's|let us)\s+"
    r"(?:go|start|begin)\s*[!.~ ]*\s*$",
    r"^\s*(?:lets?|let's|let us)\s+(?:go|start|begin|talk|do this)\s*"
    r"[!.~ ]*\s*$",
    r"^\s*i(?:'| a)m ready\b[!.~ ]*\s*$",
    r"^\s*(?:那我们)?开始吧\s*[吧～~！!。\.\s]*$",
]


def _is_engage(text: str) -> bool:
    return any(re.match(p, text.strip(), re.I) for p in _ENGAGE_RES)


def _set_offer(remote: str, about: str, facts: list[str],
               **extra) -> None:
    """Record that our last reply ended with an offer the buyer can accept.
    Cleared on the next substantive message so stale offers never hijack
    later routing."""
    rec = {"about": about, "facts": list(facts)}
    rec.update(extra)
    _THREAD.setdefault(remote, {})["offer_pending"] = rec

_AVAILABILITY_RES = [
    r"\b(do|does|can|is)\s+(you|u|it|there)\b.*\b(have|carry|sell|stock|"
    r"supply|make|manufacture|produce|offer|available|any)\b",
    r"\bis\s+there\s+any\b",
    r"\bdo\s+you\s+have\b",
    r"(有没|有没有|有没有卖|有卖|卖不卖|做不做|能不能做|能做吗|生产吗|供应吗|有没有这)",
]


def _match_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.I) for p in patterns)


# Is the buyer talking about things resembling our actual line? Availability
# probes are only answered with a grounded "not our line" when the ask is
# OUT of domain ("do you have kaolin?"); "do you have a 50kVA silent
# genset?" is in-domain and belongs to RAG/spec paths. Tokens come from S1
# catalog names (+ generic power-domain markers), cached 5 min so console
# catalog edits reach this check without a glue restart.
_DOMAIN_CACHE: tuple[float, set[str]] = (0.0, set())

# Natural-name -> SKU resolution ("the ats panel" -> ATS-50). Buyers rarely
# type exact SKUs; without this they fall into the dify RAG workflow whose
# KB-miss behaviour is a fake "let me check" (traps #34/#37). Data-driven
# from S1 so it adapts to every client's catalog. Cached 5 min.
_ALIAS_CACHE: tuple[float, list[tuple[str, str, int]]] = (0.0, [])
_STOPWORDS = {"the", "a", "an", "and", "for", "with", "more", "about",
              "know", "info", "information", "detail", "details", "product",
              "products", "your", "our", "this", "that", "what", "panel"}


def _catalog_alias_rows() -> list[dict]:
    try:
        items = _get(f"{SPINE_URL}/catalog")
        return items.get("items") if isinstance(items, dict) else (items or [])
    except Exception:
        return []


def _alias_sku(text: str) -> str | None:
    """Resolve a natural product mention to ONE catalog SKU.

    Scoring: word overlap between the buyer's content words and each item's
    name+sku words. A single matching word only counts when it is UNIQUE to
    that item across the catalog ('ats' -> ATS-50 here; 'genset' alone,
    shared by three models, resolves to nothing)."""
    import time as _t
    now = _t.time()
    ts, index = _ALIAS_CACHE
    if not index or now - ts >= 300:
        index = []
        for r in _catalog_alias_rows():
            words = {w for w in re.findall(r"[a-z0-9]+",
                                           str(r.get("name", "")).lower())
                     if w not in _STOPWORDS}
            words.add(str(r.get("sku", "")).lower())
            words.add(str(r.get("sku", "")).lower().replace("-", ""))
            index.append((r["sku"], words, len(words)))
        globals()["_ALIAS_CACHE"] = (now, index)
    text_words = {w for w in re.findall(r"[a-z0-9]+", text.lower())
                  if w not in _STOPWORDS}
    # how many items share each word — uniqueness matters for 1-word hits
    owners: dict[str, int] = {}
    for _, words, _ in index:
        for w in words:
            owners[w] = owners.get(w, 0) + 1
    best_sku, best_score = None, 0
    for sku, words, size in index:
        hits = sum(1 for w in text_words & words
                   if len(w) >= 2 and (owners.get(w, 0) == 1 or len(w) > 3))
        score = hits * 100 // max(size, 1)
        if hits >= 1 and score > best_score:
            best_sku, best_score = sku, score
        elif hits and score == best_score and best_sku:
            # tie between two items on weak evidence -> refuse to guess
            best_sku = None
    return best_sku


_STALL_RE = re.compile(
    r"check with|get back to|come back|look into|i'?ll find out"
    r"|稍后(回复|核实|告诉)|同事(将|会)?(回复|核实|确认)|团队.*(核对|确认)", re.I)


def _looks_like_stall(rag_text: str) -> bool:
    """The dify spec workflow was prompted to stall on KB misses ("say you
    will check with the team"). Until its DSL is reworded + reimported
    (#34), glue detects that signature and repairs the flow: nothing that
    promises a follow-up may leave the house without an armed escalation."""
    return bool(_STALL_RE.search(rag_text or ""))


def _catalog_reply(item: dict, lang: str, text: str, remote: str) -> str:
    """Deterministic S1 answer for one SKU: generated weave over the facts,
    static fallback otherwise. Arms offer-fulfillment state."""
    facts = [f"{item['name']} ({item['sku']})"] + [
        f"{k}: {v}" for k, v in item["specs"].items()]
    if item.get("moq"):
        facts.append(f"MOQ {item['moq']}")
    if item.get("certs"):
        facts.append(f"certifications: {item['certs']}")
    gen = compose(
        f"answering a question about {item['sku']} using the catalog "
        "facts — weave them into natural sentences, offer pricing help at "
        "the end", lang, text, facts=facts, remote=remote)
    _set_offer(remote, item["sku"],
               facts + [f"MOQ: {item.get('moq') or 'ask'}"])
    if gen:
        return gen
    specs = "; ".join(f"{k}: {v}" for k, v in item["specs"].items())
    moq = f" MOQ {item['moq']}." if item.get("moq") else ""
    certs = f" Certs: {item['certs']}." if item.get("certs") else ""
    return (f"{item['name']} ({item['sku']}): {specs}.{moq}{certs} "
            f"Ask me for a price any time.")


def _domain_tokens() -> set[str]:
    import time as _t
    now = _t.time()
    ts, toks = _DOMAIN_CACHE
    if toks and now - ts < 300:
        return toks
    toks = set()
    try:
        items = _get(f"{SPINE_URL}/catalog")
        rows = items.get("items") if isinstance(items, dict) else items
        for r in rows or []:
            toks |= set(re.findall(r"[a-z]{3,}", str(r.get("name", "")).lower()))
            cat = str(r.get("category") or "").lower()
            if cat:
                toks |= set(re.findall(r"[a-z]{3,}", cat))
    except Exception:
        pass
    if not toks:  # spine unreachable — degrade to the S2 vocabulary
        for m in MATERIALS:
            toks |= set(re.findall(r"[a-z]{3,}", m.lower()))
    toks |= {"generator", "generators", "genset", "gensets", "transfer",
             "switch", "switches", "diesel", "silent", "ats", "sts",
             "power", "kva", "kw"}
    globals()["_DOMAIN_CACHE"] = (now, toks)
    return toks


def _in_domain(text: str) -> bool:
    words = re.findall(r"[a-z]+", text.lower())
    dom = _domain_tokens()
    if any(w in dom for w in words):
        return True
    return bool(re.search(r"\d\s*-?\s*k ?(va|w)\b", text, re.I))


def _company_line() -> list[str]:
    """Facts describing what the company ACTUALLY makes, straight from S1
    (falls back to the S2 price-list materials when spine is unreachable).
    This is what lets 'what do you do?' and 'do you have X?' be answered
    concretely instead of pitched generically."""
    names = ""
    try:
        items = _get(f"{SPINE_URL}/catalog")
        rows = items.get("items") if isinstance(items, dict) else items
        names = ", ".join(f"{r['name']} ({r['sku']})"
                          for r in (rows or [])[:12])
    except Exception:
        pass
    if not names:
        names = ", ".join(MATERIALS)
    return [f"Product line: {names}",
            f"Prices are quoted in {RULES.get('currency', 'USD')}"]


def material_visibility(material: str) -> str:
    """S2 v3 price_visibility lookup (backward-compatible: missing section
    or unknown material -> 'public')."""
    pv = RULES.get("price_visibility") or {}
    if not isinstance(pv, dict):
        return "public"
    per = pv.get("per_material") or {}
    return str(per.get(material) or pv.get("default") or "public")


def hidden_materials(lines: list) -> list[str]:
    """Materials the buyer must never receive numbers for. Structural
    enforcement happens HERE — before calc is ever called — so no prompt
    change can leak an internal price (the agent cannot reveal what it
    was never given)."""
    out = set()
    for ln in lines or []:
        mat = (ln or {}).get("material", "")
        if mat and material_visibility(mat) == "internal_only":
            out.add(mat)
    return sorted(out)

CLASSIFY_PROMPT = (ROOT / "dify" / "prompts" / "a3_classify.md").read_text().split("\n---\n", 1)[1].strip()
VOICE_PROMPT = (ROOT / "dify" / "prompts" / "voice_guide.md").read_text().split("\n---\n", 1)[1].strip()

# B1-1 parser: closed vocabulary straight from S2 so the LLM can only emit
# values calc can actually price. Anything outside -> it must say "custom".
RULES_PATH = cfg("PRICING_RULES", str(ROOT / "spine" / "rules" /
                                        "pricing_rules.example.json"))
RULES: dict = {}
# How much the agent may decide (S2 agent_policy.autonomy, hot-reloaded):
#   assistant — never touches money: every price ask -> human quote
#   standard  — inline computed quotes within S2 rules (the default)
#   closer    — works ambiguous threads harder: ONE clarifying question
#               before handing off. Always-human list is sacred at ALL levels.
AUTONOMY = "standard"
MATERIALS: list[str] = []
SIZES: list[str] = []
PROCESSES: list[str] = []
PARSE_PROMPT = ""


def _refresh_rules_vocab() -> None:
    """(Re)build the closed parse vocabulary + PARSE_PROMPT from RULES_PATH.
    Called at boot AND after every console pricing save, so an edited file
    reaches the B1 parser without a glue restart. Also picks up the agent
    autonomy dial (S2 agent_policy) — bosses choose how much the AI may
    decide; hot-reloads with the same save pipeline."""
    global RULES, MATERIALS, SIZES, PROCESSES, PARSE_PROMPT, AUTONOMY
    RULES = json.loads(Path(RULES_PATH).read_text())
    MATERIALS = [m["name"] for m in RULES["material_base_prices"]]
    SIZES = [s["size"] for s in RULES["size_coefficients"]]
    PROCESSES = [p["name"] for p in RULES["process_fees"]]
    pol = RULES.get("agent_policy") or {}
    AUTONOMY = pol.get("autonomy") if pol.get("autonomy") in (
        "assistant", "standard", "closer") else "standard"
    PARSE_PROMPT = f"""You parse ONE buyer message into a structured quote request.
Return ONE JSON object, nothing else.

Pick values ONLY from these lists (they mirror the pricing engine's rules):
materials: {json.dumps(MATERIALS)}
sizes: {json.dumps(SIZES)}
processes: {json.dumps(PROCESSES)}

Schema:
{{
  "action": "quote" | "clarify" | "custom",
  "formal": <true ONLY if the buyer explicitly asks for an official/formal/
             written/PDF quotation or a proforma invoice (PI)>,
  "lines": [{{"material": "<material>", "size": "<size>", "qty": <int>,
              "processes": ["<process>", ...]}}],
  "question": "<only when action=clarify: ONE short question asking for the single missing essential>",
  "reason": "<only when action=custom: why this cannot be priced from standard rules>"
}}

Rules:
- NEVER assume a quantity. If the buyer does not state how many units ->
  action=clarify and ask for the quantity.
- If the buyer has NOT clearly named one of the listed materials, do NOT
  pick a "closest match". Use action=clarify and ask what product they want.
  Vague questions like "what do you sell?" or "what do you do?" are
  action=clarify, not quote requests.
- If the buyer names a product not in the materials list, or asks for custom/
  ODM/bespoke work -> action=custom.
- If material+size are clear but qty is missing -> action=clarify (ask ONLY for qty).
- If material or size cannot be determined -> action=clarify (ask for whichever is missing).
- "formal" is false unless the ask is explicit — a plain price question is
  NOT formal, even at large quantity.
- Map descriptions to the closest listed material/size; map finish requests to processes.
- Write `question` in the SAME language the buyer wrote in.
- Never invent prices. You only structure the request."""


_refresh_rules_vocab()

_CTX = ssl.create_default_context(
    cafile="/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)

_seen: set[str] = set()

app = FastAPI(title="MJCX glue — mock Phase A router", version="0.1.0")


@app.middleware("http")
async def _console_auth(request: Request, call_next):
    """Bearer guard for the console surface ONLY. Empty CONSOLE_TOKEN = open
    (dev). Everything else (buyer webhook, ticks, /health) stays as-is."""
    if CONSOLE_TOKEN and request.url.path.startswith("/console"):
        if request.headers.get("authorization", "") != f"Bearer {CONSOLE_TOKEN}":
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
    return await call_next(request)


def _post(url: str, payload: dict, headers: dict | None = None, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={
        "Content-Type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return json.loads(r.read())


def _get(url: str, timeout: int = 15, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return json.loads(r.read())


def glm(system: str, user: str) -> dict:
    raw = _post(f"{cfg('GLM_BASE_URL').rstrip('/')}/chat/completions", {
        "model": MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0,
    }, headers={"Authorization": f"Bearer {cfg('GLM_API_KEY')}"})
    content = raw["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise ValueError(f"no JSON in model output: {content[:200]}")
    return json.loads(m.group(0))


LANG_NAME = {"en": "English", "zh": "简体中文 (Simplified Chinese)",
             "id": "Bahasa Indonesia"}


def glm_text(user: str, temperature: float = 0.7) -> str:
    raw = _post(f"{cfg('GLM_BASE_URL').rstrip('/')}/chat/completions", {
        "model": MODEL,
        "messages": [{"role": "system", "content": VOICE_PROMPT},
                     {"role": "user", "content": user}],
        "temperature": temperature,
    }, headers={"Authorization": f"Bearer {cfg('GLM_API_KEY')}"}, timeout=120)
    return raw["choices"][0]["message"]["content"].strip()


# quote CTA is deterministic — models keep fabricating PDF links (trap #13)
PRICE_FINAL_NOTE = ("Your message must END with the validity-date line. "
                    "Do NOT ask any question, do NOT offer or mention any "
                    "document, PDF, link or attachment — a separate system "
                    "sends that later.")


# --- reply guards: the LLM may word it, but facts stay calc/spine's -------

_NUM = re.compile(r"\d+(?:[.,]\d+)*")


def _nums(s: str) -> set[str]:
    return {m.group(0).replace(",", "").lstrip("0") or "0" for m in _NUM.finditer(s)}


_LINKY = re.compile(
    r"\]\(|https?://|\.(docx|xlsx?|pdf)\b|\bdownload\b|\battach\w*\b"
    r"|\benclosed\b|附件|请查阅", re.I)

# Per-buyer thread memory (in-process; restarts re-learn from the next
# message). Feeds continuity into compose: no second welcome, no re-asking
# answered questions, no repeated openings. Nothing transcript-shaped is
# persisted here beyond the last exchange (chatwoot stays S4).
_THREAD: dict[str, dict] = {}


def _remember(remote: str, reply: str, buyer_text: str = "") -> None:
    th = _THREAD.setdefault(remote, {})
    if buyer_text:
        th["last_buyer"] = buyer_text
    th["last_reply"] = reply
    recent = th.setdefault("recent", [])
    recent.append(reply)
    if len(recent) > 2:
        recent.pop(0)
    if len(_THREAD) > 2000:
        _THREAD.clear()


def _same_opening(a: str, b: str, n: int = 4) -> bool:
    wa = re.findall(r"\w+", (a or "").lower())[:n]
    wb = re.findall(r"\w+", (b or "").lower())[:n]
    return bool(wa) and wa == wb


def _mirror(remote: str, name: str | None, direction: str,
            sender_kind: str, body: str) -> int | None:
    """v1.2 S4 store: every transcript line lands in spine (chatwoot
    replacement; X1 — spine stays the only runtime store). Best-effort:
    a spine hiccup must never break the buyer-facing path."""
    if DRY_RUN:
        return None
    try:
        cid = _post(f"{SPINE_URL}/conversations/upsert",
                    {"wa_jid": remote, "name": name},
                    timeout=5)["conversation_id"]
        _post(f"{SPINE_URL}/conversations/{cid}/messages",
              {"direction": direction, "sender_kind": sender_kind,
               "body": body[:4000]}, timeout=5)
        return cid
    except Exception as e:
        print(f"[s4] mirror skipped ({e})", flush=True)
        return None


def compose(situation: str, lang: str, buyer_text: str,
            facts: list[str] | None = None,
            remote: str = "",
            numbers: str = "subset",
            final_note: str = "") -> str | None:
    """Generate a buyer-facing reply from voice_guide.md + supplied facts.

    Returns None when generation/guard fails so callers fall back to their
    static template (graceful dumb mode). Guards enforce rule #1/#6:
    - numbers=subset (default): every number in the output must come from
      facts (no invention); the model may omit facts it doesn't need.
    - numbers=exact: additionally, every fact number must survive — used
      for quotes, where omitting a line total is as bad as inventing one.
    Fabricated links/files/attachments are always rejected.
    Thread continuity: when this buyer already has an exchange in flight,
    it is injected so the model never re-welcomes and never re-asks an
    answered question; a candidate that opens like either of the last two
    replies is regenerated once before falling back.
    """
    facts = facts or []
    lang_name = LANG_NAME.get((lang or "en")[:2], "the buyer's language")
    if facts:
        # exact mode (quotes) needs every fact delivered; subset mode only
        # caps invention. Wording matters — 'may use' made the model omit
        # line totals under exact (voice gate caught it).
        verb = ("you must convey" if numbers == "exact"
                else "you may use (the ceiling — invent nothing)")
        facts_block = f"Facts {verb}:\n- " + "\n- ".join(facts)
    else:
        facts_block = "Facts you may use: (none — keep it purely social)"
    parts = [f"Situation: {situation}",
             f"The buyer wrote: \"{buyer_text}\"",
             facts_block]
    th = _THREAD.get(remote) or {}
    if th.get("last_buyer"):
        parts.append(f"The buyer previously wrote: \"{th['last_buyer']}\"")
    if th.get("recent"):
        parts.append("Your last messages to this buyer were:\n"
                     + "\n---\n".join(f"\"{p}\"" for p in reversed(th["recent"]))
                     + "\nDo not reuse their opening words; do not repeat "
                       "questions they already answered.")
    parts.append(final_note)
    parts.append(f"Write the WhatsApp reply now, ONLY in {lang_name}.")
    base_prompt = "\n\n".join(parts)
    prompt = base_prompt
    last_ok = None  # guard-passing candidate; kept if openings keep clashing
    for attempt in range(2):
        try:
            cand = glm_text(prompt)
        except Exception as e:
            print(f"[voice] generation failed ({e}); static fallback",
                  flush=True)
            return None if last_ok is None else last_ok
        have, need = _nums(cand), _nums("\n".join(facts))
        if numbers == "subset":
            # echoing the BUYER'S OWN numbers is never invention
            need = need | _nums(buyer_text)
        ok = (have == need) if numbers == "exact" else (have <= need)
        if not ok or _LINKY.search(cand):
            print(f"[voice] guard rejected generated text\n"
                  f"[voice] generated was: {cand[:200]}", flush=True)
            continue
        last_ok = cand
        if not any(_same_opening(cand, p) for p in th.get("recent", [])):
            return cand
        # Retry with the banned openings spelled out — an identical prompt
        # just reproduces the same natural opener (e.g. id "Sama-sama pak").
        banned = sorted({p.split("\n")[0][:40] for p in th.get("recent", [])})
        prompt = (base_prompt
                  + "\n\nIMPORTANT: do NOT start your reply with anything "
                    f"like {banned} — choose a clearly different opening.")
        print("[voice] opening clashed with a recent reply; regenerating",
              flush=True)
    # A repeated opening is a blemish; a static template mid-thread is a
    # regression. Prefer the guard-clean candidate.
    return last_ok


def classify(text: str) -> dict:
    """A3-1 via the dify workflow (dify/dsl/a3_triage.yml); GLM direct fallback.

    Returns {intent, language, urgency, sentiment, confidence, route}.
    """
    if USE_DIFY and DIFY_A3_KEY:
        try:
            res = _post(f"{DIFY_URL}/v1/workflows/run", {
                "inputs": {"query": text, "customer_tier": ""},
                "response_mode": "blocking", "user": "glue-router",
            }, headers={"Authorization": f"Bearer {DIFY_A3_KEY}"}, timeout=90)
            if res.get("data", {}).get("status") == "succeeded":
                out = res["data"]["outputs"]
                if out.get("parse_ok"):
                    return out
                print("[a3-dify] parse_ok=false, falling back to local glm", flush=True)
        except Exception as e:
            print(f"[a3-dify] unavailable ({e}); local glm fallback", flush=True)
    cls = glm(CLASSIFY_PROMPT, text)
    intent = cls.get("intent")
    conf = float(cls.get("confidence") or 0)
    route = ROUTE_MAP.get(intent, "human")
    if intent != "SPAM" and (intent not in ROUTE_MAP or conf < 0.7):
        route = "human"
    cls["route"] = route
    return cls


def spec_answer(text: str) -> str | None:
    """RAG over the client knowledge base via the A3-Spec dify workflow
    (dify/dsl/spec_answer.yml). Returns None when unavailable so the caller
    falls back to the deflect stub."""
    if not DIFY_SPEC_KEY:
        return None
    try:
        res = _post(f"{DIFY_URL}/v1/workflows/run", {
            "inputs": {"query": text}, "response_mode": "blocking",
            "user": "glue-router"},
            headers={"Authorization": f"Bearer {DIFY_SPEC_KEY}"}, timeout=90)
        if res.get("data", {}).get("status") == "succeeded":
            return res["data"]["outputs"].get("answer") or None
    except Exception as e:
        print(f"[a3-spec] unavailable ({e})", flush=True)
    return None


def send_text(number_jid: str, text: str) -> None:
    if number_jid.startswith("email:"):
        # email channel (design-email-channel.md): same reply, SMTP door.
        ctx = getattr(_EMAIL_CTX, "msg", None) or {}
        subj = ctx.get("subject") or "your inquiry"
        _email_send(number_jid.split(":", 1)[1],
                    subj if subj.lower().startswith("re:") else f"Re: {subj}",
                    text, in_reply_to=ctx.get("msg_id", ""))
        return
    number = number_jid.split("@")[0].replace("+", "")
    if DRY_RUN:
        print(f"[dry-run] would send to {number}: {text[:160]}", flush=True)
        return
    _post(f"{EVO_URL}/message/sendText/{INSTANCE}",
          {"number": number, "text": text},
          headers={"apikey": EVO_KEY})


# ------------------------------------------------------- A6 human handoff ----

CW_INBOX_NAME = CW_INBOX_NAME or INSTANCE
_inbox_id = 0


def _cw(method: str, path: str, payload: dict | None = None,
        timeout: int = 8, token: str = ""):
    req = urllib.request.Request(
        f"{CW_URL}/api/v1/accounts/{CW_ACCOUNT}{path}",
        method=method, data=json.dumps(payload or {}).encode(),
        headers={"api_access_token": token or CW_TOKEN or "",
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as r:
        return json.loads(r.read() or b"{}")


def _cw_inbox() -> int:
    global _inbox_id
    if _inbox_id:
        return _inbox_id
    for ib in _cw("GET", "/inboxes").get("payload", []):
        if ib.get("name") == CW_INBOX_NAME:
            _inbox_id = ib["id"]
            return _inbox_id
    raise RuntimeError(
        f"inbox '{CW_INBOX_NAME}' not created yet (evo builds it on the "
        "first bridged WhatsApp message)")


def _contact_id(resp: dict) -> int:
    inner = resp.get("payload")
    if isinstance(inner, dict) and isinstance(inner.get("contact"), dict):
        return inner["contact"]["id"]
    if resp.get("id"):
        return resp["id"]
    raise RuntimeError(f"unexpected contact response: {str(resp)[:120]}")


def _find_contact(remote: str) -> list[dict]:
    """chatwoot's search endpoint has no exact identifier filter in this
    version — search broadly, match exactly."""
    res = _cw("GET", f"/contacts/search?q={urllib.parse.quote(remote)}")
    return [c for c in res.get("payload", []) if c.get("identifier") == remote]


def escalate_to_chatwoot(remote: str, buyer_text: str, tag: str, lang: str,
                         customer: dict, holding_reply: str,
                         note_extra: str = "") -> None:
    """A6-1 escalation package. v1.2 default: arm the SPINE conversation
    (S4 store; the console Threads page renders it). CHATWOOT_ENABLED=1
    restores the legacy chatwoot-inbox path unchanged.
    Best-effort — the buyer-facing holding reply already went out via evo;
    a store hiccup must never break that path."""
    if DRY_RUN:
        return
    summary = (
        f"{customer.get('name') or remote.split('@')[0]}"
        f" — lang {lang}, tier {customer.get('tier') or 'new'},"
        f" id {customer.get('customer_id')}\n"
        f"Buyer wrote: \"{buyer_text[:400]}\"\n"
        f"AI holding reply already sent: \"{holding_reply[:300]}\"\n"
        + note_extra +
        "Next: reply from the console Threads page — it goes to the buyer "
        "over WhatsApp and clears this flag.")
    if not (CHATWOOT_ENABLED and CW_TOKEN):
        try:
            cid = _post(f"{SPINE_URL}/conversations/upsert",
                        {"wa_jid": remote,
                         "name": customer.get("name") or None}, timeout=5
                        )["conversation_id"]
            _post(f"{SPINE_URL}/conversations/{cid}/escalate",
                  {"tag": tag, "note": summary}, timeout=5)
            print(f"[a6] spine conversation {cid} armed ({tag})", flush=True)
        except Exception as e:
            print(f"[a6] spine handoff skipped: {e}", flush=True)
        return
    try:
        inbox = _cw_inbox()
        matches = _find_contact(remote)
        if matches:
            cid = matches[0]["id"]
        else:
            try:
                cid = _contact_id(_cw("POST", "/contacts", {
                    "identifier": remote,
                    "name": customer.get("name") or remote.split("@")[0]}))
            except Exception:
                matches = _find_contact(remote)  # duplicate race
                if not matches:
                    raise
                cid = matches[0]["id"]

        conv = None
        listed = _cw("GET", f"/contacts/{cid}/conversations")
        candidates = []
        data = listed.get("data") or {}
        for cand in (listed.get("payload"), data.get("payload"),
                     data.get("conversations")):
            if isinstance(cand, list):
                candidates.extend(cand)
        for item in candidates:
            c = item.get("conversation") or item
            if c.get("status") == "open":
                conv = c
                break
        priority = "urgent" if tag == "COMPLAINT" else "high"
        if not conv:
            conv = _cw("POST", "/conversations", {
                "source_id": remote, "inbox_id": inbox,
                "contact_id": cid, "status": "open", "priority": priority})
            convid = conv["id"] if isinstance(conv.get("id"), int) else \
                conv.get("conversation", {}).get("id")
        else:
            convid = conv["id"]

        _cw("POST", f"/conversations/{convid}/messages",
            {"content": f"[ESCALATION {tag}] {summary}", "private": True})
        labels = [tag.lower()]
        try:
            _cw("POST", f"/conversations/{convid}/labels", {"labels": labels})
        except Exception as lab_err:
            print(f"[a6] label skipped ({lab_err})", flush=True)
        try:
            _post(f"{SPINE_URL}/events", {"kind": "escalation",
                 "detail_json": json.dumps({
                     "intent": tag, "remote": remote,
                     "customer_id": customer.get("customer_id"),
                     "chatwoot_conversation_id": convid})}, timeout=5)
        except Exception as ev_err:
            print(f"[a6] S8 event skipped ({ev_err})", flush=True)
        print(f"[a6] chatwoot conversation {convid} armed ({tag})",
              flush=True)
    except Exception as e:
        print(f"[a6] chatwoot handoff skipped: {e}", flush=True)


# --------------------------------------------------- B4 formal quote PDF ----

def send_document(number_jid: str, path: Path, caption: str) -> None:
    """B4-2: PDF into the SAME chat (evo v2.3.7 has no sendDocument —
    sendMedia with mediatype=document is the endpoint; media=base64).
    email:* jids attach the PDF to an SMTP reply instead (same thread)."""
    if number_jid.startswith("email:"):
        ctx = getattr(_EMAIL_CTX, "msg", None) or {}
        subj = ctx.get("subject") or "your inquiry"
        _email_send(number_jid.split(":", 1)[1],
                    subj if subj.lower().startswith("re:") else f"Re: {subj}",
                    caption, attachments=[path],
                    in_reply_to=ctx.get("msg_id", ""))
        return
    number = number_jid.split("@")[0].replace("+", "")
    if DRY_RUN:
        print(f"[dry-run] would send document {path.name} to {number}",
              flush=True)
        return
    _post(f"{EVO_URL}/message/sendMedia/{INSTANCE}", {
        "number": number, "mediatype": "document",
        "mimetype": "application/pdf", "fileName": path.name,
        "caption": caption,
        "media": base64.b64encode(path.read_bytes()).decode()},
        headers={"apikey": EVO_KEY}, timeout=180)


# --------------------------------------------- email inquiry channel (X-v1) --
# docs/design-email-channel.md — email is a TRANSPORT, not a pipeline. The
# pseudo-jid "email:<addr>" makes spine S3/S4/S8 and the thread-state memory
# work unchanged; only the doors differ (IMAP in, SMTP out).

_EMAIL_CTX = threading.local()  # per-worker-thread message metadata (trap #41 discipline: route() runs in to_thread)


def _email_send(to: str, subject: str, body: str,
                attachments: list[Path] | None = None,
                in_reply_to: str = "") -> None:
    """SMTP reply door. Raises on failure — callers decide policy
    (never mirror an unsent message). DRY_RUN prints instead."""
    if DRY_RUN:
        print(f"[dry-run] would email {to}: {subject} :: {body[:120]}",
              flush=True)
        return
    if not (EMAIL_SMTP_HOST and EMAIL_USER):
        raise RuntimeError("email SMTP not configured (EMAIL_SMTP_HOST/USER)")
    msg = EmailMessage()
    msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_USER}>"
    msg["To"] = to
    msg["Subject"] = subject
    if in_reply_to:
        msg["In-Reply-To"] = in_reply_to
        msg["References"] = in_reply_to
    msg.set_content(body)
    for p in attachments or []:
        msg.add_attachment(p.read_bytes(), maintype="application",
                           subtype="pdf", filename=p.name)
    port = EMAIL_SMTP_PORT
    if port == 465:
        server = smtplib.SMTP_SSL(EMAIL_SMTP_HOST, port, timeout=30,
                                  context=ssl.create_default_context())
    else:
        server = smtplib.SMTP(EMAIL_SMTP_HOST, port, timeout=30)
    with server:
        if port != 465:
            server.starttls(context=ssl.create_default_context())
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


def _handle_email(addr: str, name: str | None, subject: str, body: str,
                  msg_id: str = "") -> dict:
    """Shared post-fetch handler — the email twin of the /webhook/evo body
    (resolve → mirror → route → send → remember → mirror). Also the seam
    the offline gate drives (tests/test_email_channel.py stubs _email_send)."""
    jid = f"email:{addr.lower()}"
    text = (((subject or "").strip() + ("\n\n" if subject.strip() else "")
             + (body or "").strip()).strip())
    if not text:
        return {"skipped": "no text"}
    if msg_id and msg_id in _seen:
        return {"deduped": msg_id}
    if msg_id:
        _seen.add(msg_id)

    try:
        resolved = _post(f"{SPINE_URL}/resolve", {"wa_jid": jid, "name": name})
        customer = resolved["customer"]
    except Exception as e:
        print(f"[a2-email] spine down, anonymous fallback: {e}", flush=True)
        customer = {"customer_id": "anonymous", "tier": "new"}

    _mirror(jid, name, "in", "buyer", text)

    _EMAIL_CTX.msg = {"to": addr, "subject": (subject or "").strip(),
                      "msg_id": msg_id}
    try:
        reply = route(customer, text, jid)
        if reply:
            _email_send(addr,
                        (subject or "your inquiry")
                        if (subject or "").lower().startswith("re:")
                        else f"Re: {(subject or 'your inquiry').strip()}",
                        reply, in_reply_to=msg_id)
            _remember(jid, reply, buyer_text=text)
            _mirror(jid, name, "out", "bot", reply)
    finally:
        _EMAIL_CTX.msg = None
    return {"ok": True, "replied": bool(reply), "to": jid}


def _email_poll_sync(limit: int = 20) -> dict:
    """One IMAP pass. Marks \\Seen ONLY after handling succeeds; Message-ID
    dedupe keeps a crash between fetch and mark from double-replying."""
    if not (EMAIL_ENABLED and EMAIL_IMAP_HOST and EMAIL_USER):
        return {"skipped": "email channel not configured (EMAIL_ENABLED)"}
    with imaplib.IMAP4_SSL(EMAIL_IMAP_HOST, EMAIL_IMAP_PORT) as imap:
        imap.login(EMAIL_USER, EMAIL_PASS)
        imap.select(EMAIL_FOLDER, readonly=False)
        typ, ids = imap.uid("search", None, "UNSEEN")
        if typ != "OK":
            raise RuntimeError(f"imap search failed: {typ}")
        uids = (ids[0].split() if ids and ids[0] else [])[-limit:]
        handled = []
        for uid in uids:
            typ, parts = imap.uid("fetch", uid, "(BODY.PEEK[])")
            if typ != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            raw = bytes(parts[0][1])
            m = BytesParser(policy=policy.default).parsebytes(raw)
            frm_name, frm_addr = parseaddr(str(m.get("From") or ""))
            mid = str(m.get("Message-ID") or "").strip()
            body = ""
            if m.is_multipart():
                for part in m.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
            else:
                try:
                    body = m.get_content()
                except Exception:
                    body = m.get_payload(decode=True).decode(
                        "utf-8", "replace")
            res = _handle_email(frm_addr, frm_name or None,
                                str(m.get("Subject") or ""), body, mid)
            handled.append({"uid": uid.decode(), **res})
            if res.get("ok"):
                imap.uid("store", uid, "+FLAGS", "(\\Seen)")
        return {"fetched": len(uids), "handled": handled}


@app.post("/email/poll")
async def email_poll(limit: int = 20):
    """n8n clock hits this every minute during office hours. Sync IMAP/SMTP
    I/O stays OFF the event loop (trap #41)."""
    return await asyncio.to_thread(_email_poll_sync, limit)


# ------------------------------------------------------- X5 report delivery --

def _fmt_span(seconds: float | None) -> str:
    if seconds is None:
        return "n/a"
    s = int(round(seconds))
    if s >= 3600:
        return f"{s // 3600}h{s % 3600 // 60:02d}m"
    if s >= 60:
        return f"{s // 60}m{s % 60:02d}s"
    return f"{s}s"


def _x5_text(rep: dict, short: bool) -> str:
    """Render the spine /reports/x5 computation as a boss-readable WhatsApp
    text. LLM NEVER writes this — numbers come verbatim from the store
    (house rule #1: calc/store computes, glue copies)."""
    c = rep["conversations"]
    q = rep["quotes"]
    head = (f"📊 {'Weekly digest' if short else 'Monthly report'} "
            f"(last {int(rep['days'])} days)")
    lines = [head,
             f"Conversations: {c['total']} — AI handled {c['ai_handled']}, "
             f"escalated {c['escalated']}, human-only {c['human_only']}",
             f"Median response time: {_fmt_span(rep['median_response_seconds'])}"
             f" ({rep['responses_measured']} measured)"]
    if not short:
        top = ", ".join(f"{p['name']} ×{p['count']}"
                        for p in rep["top_products"][:5])
        if top:
            lines.append(f"Top asked products: {top}")
        misses = rep["kb_misses"]
        lines.append(f"Unanswerable questions (KB misses): {len(misses)}")
        for m in misses[:3]:
            lines.append(f"  • \"{m['snippet'][:60]}\"")
    reasons = ", ".join(f"{k} {v}" for k, v in
                        sorted(rep["escalation_reasons"].items(),
                               key=lambda kv: -kv[1]))
    if reasons:
        lines.append(f"Why handed off: {reasons}")
    if not short:
        tc = rep["tier_changes"]
        lines.append(f"Tier changes: {len(tc)}")
    lines.append(f"Quotes sent {q['sent']} · win rate "
                 f"{q['win_rate_pct'] if q['win_rate_pct'] is not None else '—'}%"
                 f" · value {q['value_sent']:,.0f}")
    lines.append(f"SLA beacons {rep['sla_beacons']} · social posted/scheduled "
                 f"{rep['social']['posted_or_scheduled']}")
    return "\n".join(lines)


@app.post("/x5/send")
async def x5_send(days: float = 30, short: bool = False):
    """Auto-send the X5 report to BOSS on schedule (n8n monthly/weekly).
    Text-only for now; PDF export is a later custom generator."""
    import urllib.request as _u
    req = _u.Request(f"{SPINE_URL}/reports/x5?days={days}")
    with _u.urlopen(req, timeout=20) as r:
        rep = json.loads(r.read())
    boss = cfg("BOSS_WHATSAPP", BOSS_WHATSAPP)
    if not boss:
        return {"skipped": "no BOSS_WHATSAPP configured"}
    text = _x5_text(rep, short)
    await asyncio.to_thread(send_text, f"{boss.lstrip('+')}@s.whatsapp.net",
                            text)
    try:
        await asyncio.to_thread(
            _post, f"{SPINE_URL}/events",
            {"kind": "x5_sent",
             "detail_json": json.dumps({"days": days, "short": short})})
    except Exception as e:
        print(f"[x5] S8 log skipped ({e})", flush=True)
    return {"ok": True, "to": boss, "preview": text}


def _carbone_docx(data: dict) -> bytes:
    """B4-1 render via carbone-ee docker (:8200 → in-container 4000).
    carbone-ee v5 API is ASYNC: POST /template (multipart) → {templateId},
    POST /render/{templateId} {"data":…} → {renderId}, then GET
    /render/{renderId} returns the binary exactly ONCE (subsequent polls
    404). Traps honored: npm CE corrupts templates — docker only;
    convertTo:pdf is license-gated, so we render docx and convert here."""
    tpl = QUOTE_TEMPLATE.read_bytes()
    boundary = "----mjcxB4Boundary"
    part = (
        f"--{boundary}\r\n"
        "Content-Disposition: form-data; name=\"template\"; "
        "filename=\"quote_template.docx\"\r\n"
        "Content-Type: application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document\r\n\r\n").encode() + tpl + \
        f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{CARBONE_URL}/template", data=part, method="POST",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
        up = json.loads(r.read())
    template_id = ((up.get("data") or {}).get("templateId"))
    if not template_id:
        raise RuntimeError(f"no templateId in upload reply: {str(up)[:150]}")
    payload = json.dumps({"data": data, "convertTo": "docx"}).encode()
    req = urllib.request.Request(
        f"{CARBONE_URL}/render/{template_id}", data=payload, method="POST",
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
        rid = json.loads(r.read())["data"]["renderId"]
    for _ in range(30):
        time.sleep(1)
        try:
            with urllib.request.urlopen(f"{CARBONE_URL}/render/{rid}",
                                        timeout=60, context=_CTX) as r:
                out = r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # still queued (or already consumed — loop guards)
            raise
        if out.startswith(b"PK"):
            return out
    raise RuntimeError("carbone render timed out")


def _docx_to_pdf(docx_bytes: bytes, stem: str) -> Path:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    docx_path = PDF_DIR / f"{stem}.docx"
    docx_path.write_bytes(docx_bytes)
    subprocess.run([SOFFICE, "--headless", "--convert-to", "pdf",
                    "--outdir", str(PDF_DIR), str(docx_path)],
                   check=True, capture_output=True, timeout=300)
    pdf_path = docx_path.with_suffix(".pdf")
    if not pdf_path.exists() or pdf_path.stat().st_size < 5000:
        raise RuntimeError(f"soffice output unusable: {pdf_path}")
    return pdf_path


def _quote_render_data(quote: dict, customer: dict, quote_id: str) -> dict:
    """calc QuoteResult + S3 customer -> template markers. Numbers come from
    calc verbatim (rule #1); placeholders are .env-configurable per client."""
    return {
        "companyName": COMPANY_NAME,
        "quoteId": quote_id,
        "date": date.today().isoformat(),
        "validUntil": quote.get("valid_until", ""),
        "buyerName": customer.get("name") or customer.get("customer_id"),
        "buyerCountry": customer.get("country") or "",
        "incoterm": INCOTERM_DEFAULT,
        "currency": quote.get("currency", "USD"),
        "paymentTerms": PAYMENT_TERMS_DEFAULT,
        "leadTime": LEAD_TIME_DEFAULT,
        "subtotal": f"{quote['subtotal']:,.2f}",
        "discountPct": quote.get("discount_pct", 0),
        "total": f"{quote['total']:,.2f}",
        "lines": [{"description": l["description"], "qty": l["qty"],
                   "unitPrice": f"{l['unit_price']:,.2f}",
                   "lineTotal": f"{l['line_total']:,.2f}"}
                  for l in quote["lines"]],
    }


def b4_deliver(remote: str, customer: dict, quote: dict, quote_id: str) -> bool:
    """Render formal PDF, record in S5, deliver in the same chat.
    Dry-run grade by design — per-client templates are a later custom
    generator. Best-effort: any failure prints and returns False; the
    inline price path must never break because of document rendering."""
    try:
        data = _quote_render_data(quote, customer, quote_id)
        pdf = _docx_to_pdf(_carbone_docx(data), quote_id)
        _post(f"{SPINE_URL}/quotes/{quote_id}/pdf", {"path": str(pdf)},
              timeout=10)
        caption = (f"Official quotation {quote_id} — total "
                   f"{quote['currency']} {quote['total']:,.2f}, "
                   f"valid until {quote['valid_until']}. Any questions, "
                   f"just reply here.")
        send_document(remote, pdf, caption)
        print(f"[b4] {quote_id} rendered+delivered ({pdf.name})", flush=True)
        return True
    except Exception as e:
        print(f"[b4] formal PDF skipped ({e})", flush=True)
        return False


# ------------------------------------------ B6 follow-ups + A6 SLA beacon ----

def _event_qids(kind: str, key: str = "quote_id") -> set:
    seen = set()
    try:
        for e in _get(f"{SPINE_URL}/events?kind={kind}&limit=500")["items"]:
            try:
                v = json.loads(e["detail_json"] or "{}").get(key)
                if v:
                    seen.add(v)
            except Exception:
                pass
    except Exception as e:
        print(f"[tick] events unreadable ({e})", flush=True)
    return seen


def _followup_draft(qid: str, quote: dict, cust: dict) -> str | None:
    """Gentle B6 nudge in the buyer's language. Same discipline as compose():
    digits must come from the stored calc facts, no links."""
    q = quote.get("result_json") or {}
    if isinstance(q.get("quote"), dict):   # calc HTTP envelope -> unwrap
        q = q["quote"]
    currency = quote.get("currency") or q.get("currency") or "USD"
    facts = [f"{l.get('description','')} x{l.get('qty')} — {currency} "
             f"{(l.get('line_total') or 0):,.2f}" for l in (q.get("lines") or [])]
    facts += [f"Total: {currency} {(q.get('total') or 0):,.2f}",
              f"Valid until {q.get('valid_until','')}"]
    lang = ((cust.get("language")) or "en")[:2]
    lang_name = LANG_NAME.get(lang, "the buyer's language")
    parts = [f"Situation: writing a follow-up for quotation {qid} we already sent.",
             "Facts you may reference:\n- " + "\n- ".join(facts),
             "Write a SHORT WhatsApp follow-up to the buyer: gently remind them "
             "of the offer, offer to adjust quantities or answer questions. No "
             "numbers beyond the facts above and the quotation number itself. "
             "No links, no attachments.",
             f"Write it ONLY in {lang_name}."]
    try:
        draft = glm_text("\n\n".join(parts), temperature=0.7).strip()
        # allowed digits: calc facts + the quote id itself (models echo it)
        if _nums(draft) <= _nums("\n".join(facts) + f" {qid}") \
                and not _LINKY.search(draft):
            return draft
        print(f"[b6] guard rejected draft: {draft[:160]}", flush=True)
    except Exception as e:
        print(f"[b6] draft generation failed ({e})", flush=True)
    return None


def _approve_followup(qid: str) -> str:
    """Staff replied APPROVE <qid> -> send the stored draft to the buyer.
    Draft text + buyer jid were logged in the followup_draft S8 event, so
    approval is exact — staff approve the very words that get sent."""
    try:
        items = _get(f"{SPINE_URL}/events?kind=followup_draft&limit=500")["items"]
    except Exception as e:
        return f"spine unreachable ({e})"
    entry = None
    for e in items:  # newest first
        try:
            d = json.loads(e.get("detail_json") or "{}")
        except Exception:
            continue
        if d.get("quote_id") == qid and d.get("draft"):
            entry = d
            break
    if not entry:
        return f"No stored draft found for {qid}."
    buyer = entry.get("buyer_jid")
    if not buyer:
        return f"{qid}: draft has no buyer JID recorded."
    try:
        _post(f"{SPINE_URL}/quotes/{qid}/status", {"status": "sent"}, timeout=10)
    except Exception:
        pass
    try:
        send_text(buyer, entry["draft"])
    except Exception as e:
        return f"Delivery failed ({e}). Draft kept — retry with APPROVE {qid}."
    try:
        _post(f"{SPINE_URL}/events",
              {"kind": "followup_sent",
               "detail_json": json.dumps({"quote_id": qid,
                                          "buyer_jid": buyer})},
              timeout=10)
    except Exception:
        pass
    print(f"[b6] {qid} approved -> sent to {buyer}", flush=True)
    return f"Sent. ({qid})"


@app.post("/b6/tick")
def b6_tick(hours: float = -1):
    """B6-1 v1: quotes status=sent older than N hours without a follow-up yet
    -> gentle DRAFT goes to STAFF WhatsApp for approval (never auto-send).
    Idempotent via S8 followup_draft events. n8n calls this on a schedule."""
    h = hours if hours >= 0 else float(cfg("FOLLOWUP_HOURS", FOLLOWUP_HOURS))
    staff = cfg("STAFF_WHATSAPP", STAFF_WHATSAPP)
    due = _get(f"{SPINE_URL}/quotes?status=sent&older_than_hours={h}")["items"]
    seen = _event_qids("followup_draft")
    # retry quotes whose earlier draft failed generation (empty draft stored)
    try:
        ok_drafts = {json.loads(e["detail_json"]).get("quote_id")
                     for e in _get(f"{SPINE_URL}/events?kind=followup_draft&limit=500")["items"]
                     if json.loads(e.get("detail_json") or "{}").get("draft")}
    except Exception:
        ok_drafts = set()
    drafted = []
    for row in due:
        qid = row["quote_id"]
        if qid in seen and qid in ok_drafts:
            continue
        try:
            cust = _get(f"{SPINE_URL}/customers/{row['customer_id']}")
        except Exception:
            cust = {}
        try:
            quote = json.loads(row["result_json"]) if isinstance(row["result_json"], str) \
                else (row["result_json"] or {})
        except Exception:
            quote = {}
        draft = _followup_draft(qid, row | {"result_json": quote}, cust)
        logged = {"quote_id": qid,
                  "buyer_jid": cust.get("wa_jid") or "",
                  "draft": draft or ""}
        if draft and staff:
            send_text(staff,
                      f"[Follow-up draft • {qid}] To: "
                      f"{cust.get('name') or row['customer_id']}\n\n{draft}"
                      f"\n\n— approve by replying: APPROVE {qid}")
            logged["drafted"] = True
        elif not staff and draft:
            logged["drafted"] = False
            logged["reason"] = "no STAFF_WHATSAPP configured"
        try:
            _post(f"{SPINE_URL}/events",
                  {"kind": "followup_draft", "detail_json": json.dumps(logged)},
                  timeout=10)
        except Exception as e:
            print(f"[b6] S8 log failed ({e})", flush=True)
        drafted.append(qid)
        print(f"[b6] {qid}: draft {'sent to staff' if draft and staff else 'logged'}",
              flush=True)
    return {"due": len(due), "drafted": drafted, "staff_configured": bool(staff)}


@app.post("/a6/sla_tick")
def sla_tick(hours: float = -1):
    """A6 SLA beacon: open conversations where the buyer's LAST inbound has
    sat unanswered by a human for > SLA_HOURS -> nudge BOSS on WhatsApp,
    once per conversation (until handled or re-escalated).
    v1.2 default reads the SPINE S4 store; CHATWOOT_ENABLED=1 restores the
    legacy chatwoot path unchanged."""
    h = hours if hours >= 0 else float(cfg("SLA_HOURS", SLA_HOURS))
    boss = cfg("BOSS_WHATSAPP", BOSS_WHATSAPP)
    if not CHATWOOT_ENABLED:
        from datetime import datetime, timezone
        convs = _get(f"{SPINE_URL}/conversations?status=open"
                     "&include_last=1").get("items", [])
        now = time.time()
        fired = []
        for c in convs:
            last_in = c.get("last_in_at")
            if not last_in:
                continue  # nothing to chase yet
            waited = (now - datetime.strptime(
                last_in, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=timezone.utc).timestamp()) / 3600
            if waited < h:
                continue
            if c.get("sla_beacon_at"):
                continue  # once per conversation until handled/re-armed
            human_out = c.get("last_human_out_at")
            if human_out and human_out >= last_in:
                continue  # a person already took over after the buyer wrote
            name = c.get("contact_name") or c["wa_jid"].split("@")[0]
            preview = (c.get("preview") or "")[:120]
            if boss:
                send_text(boss,
                          f"[SLA {waited:.0f}h] Escalation unanswered — "
                          f"{name} (thread #{c['id']}): \"{preview}\"")
            try:
                _post(f"{SPINE_URL}/conversations/{c['id']}/sla_beacon",
                      {}, timeout=5)
                _post(f"{SPINE_URL}/events",
                      {"kind": "sla_beacon",
                       "detail_json": json.dumps({
                           "conversation_id": c["id"],
                           "hours": round(waited, 1)})}, timeout=10)
            except Exception as e:
                print(f"[sla] store update skipped: {e}", flush=True)
            fired.append(c["id"])
            print(f"[sla] beacon thread {c['id']} ({waited:.1f}h)", flush=True)
        return {"checked": len(convs), "beacons": fired, "store": "spine"}
    if not CW_TOKEN:
        return {"skipped": "no CHATWOOT_API_TOKEN"}
    humans = {a["id"] for a in _cw("GET", "/agents")
              if a.get("email") != CW_BRIDGE_EMAIL}
    convs = _cw("GET", "/conversations?status=open")["data"]["payload"]
    beaconed = _event_qids("sla_beacon", key="conversation_id")
    now = time.time()
    fired = []
    for c in convs:
        cid = c["id"]
        waited = (now - (c.get("created_at") or 0)) / 3600
        if waited < h or cid in beaconed:
            continue
        msgs = _cw("GET", f"/conversations/{cid}/messages").get("payload", [])
        human_replied = any(
            m.get("message_type") == 1 and not m.get("private")
            and ((m.get("sender") or {}).get("id") in humans)
            for m in msgs)
        if human_replied:
            continue
        contact = (c.get("meta") or {}).get("sender") or {}
        name = contact.get("name") or contact.get("identifier") or f"#{cid}"
        last_buyer = next((str(m.get("content", ""))[:120] for m in reversed(msgs)
                           if m.get("message_type") == 0 and not m.get("private")), "")
        if boss:
            send_text(boss,
                      f"[SLA {waited:.0f}h] Escalation unanswered — {name} "
                      f"(chatwoot #{cid}): \"{last_buyer}\"")
        _post(f"{SPINE_URL}/events",
              {"kind": "sla_beacon",
               "detail_json": json.dumps({"conversation_id": cid,
                                          "hours": round(waited, 1)})},
              timeout=10)
        fired.append(cid)
        print(f"[sla] beacon conv {cid} ({waited:.1f}h)", flush=True)
    return {"checked": len(convs), "beacons": fired}


# --------------------------------------------------- Phase C: social ops ----

_CAPT_PROMPT = """You draft ONE {platform} post for a foreign-trade company.
Product facts (the ONLY claims allowed):
- {facts}

Voice: professional, concrete, no hype, no emoji walls (at most one), short
paragraphs. End with a soft call-to-action inviting inquiries via WhatsApp.
Return STRICT JSON: {{"caption": "...", "hashtags": "#tag1 #tag2"}}"""


POSTIZ_API_BASE = f"{POSTIZ_URL}/api/public/v1"  # trap #44: nginx strips /api/


def _postiz_auth(key: str) -> dict:
    """v2.11.2 middleware reads the RAW key from Authorization; newer versions
    use X-API-KEY — send both."""
    return {"Authorization": key, "X-API-KEY": key}


def _postiz_integrations() -> list:
    """v2.11.2 public API has no /organizations; /integrations lists the
    connected channels (org itself is derived from the key server-side)."""
    req = urllib.request.Request(
        f"{POSTIZ_API_BASE}/integrations",
        headers=_postiz_auth(POSTIZ_API_KEY or ""))
    with urllib.request.urlopen(req, timeout=20, context=_CTX) as r:
        return json.loads(r.read())


def _push_to_postiz(caption: str, hashtags: str, when: str) -> tuple[bool, str]:
    """C4-1: create a scheduled post. Needs POSTIZ_API_KEY + at least one
    connected channel in postiz; anything missing -> graceful skip."""
    if not POSTIZ_API_KEY:
        return False, "POSTIZ_API_KEY not configured"
    try:
        integrations = _postiz_integrations()
        if not integrations:
            return False, "no connected channel in postiz yet"
        body = json.dumps({
            "date": when,
            "settings": {POSTIZ_PLATFORM: [{"content": f"{caption}\n\n{hashtags}"}]},
        }).encode()
        req = urllib.request.Request(
            f"{POSTIZ_API_BASE}/posts", data=body, method="POST",
            headers={**_postiz_auth(POSTIZ_API_KEY),
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
            res = json.loads(r.read())
        pid = ""
        if isinstance(res, list) and res:
            pid = str(res[0].get("id") or res[0].get("postID") or "")
        elif isinstance(res, dict):
            pid = str(res.get("id") or "")
        return True, pid or "submitted"
    except Exception as e:
        return False, str(e)[:160]


@app.post("/c/draft_tick")
def c_draft_tick(count: int = 3):
    """C1+C2: pick catalog products without live posts, draft one
    {POSTIZ_PLATFORM} caption each -> S6 pending -> approval card to BOSS.
    v1 is ALWAYS human-approved (flowchart C3); nothing auto-publishes."""
    boss = cfg("BOSS_WHATSAPP", BOSS_WHATSAPP)
    items = _get(f"{SPINE_URL}/catalog")["items"]
    existing = _get(f"{SPINE_URL}/posts?limit=200")["items"]
    used = {(p["sku"], p["status"]) for p in existing
            if p["status"] in ("pending", "approved", "scheduled", "posted")}
    fresh = [i for i in items if (i["sku"], ) not in
             {(u[0], ) for u in used}]
    drafted = []
    for item in fresh[:max(1, count)]:
        specs = _get(f"{SPINE_URL}/catalog/{item['sku']}")
        facts = [f"{item['name']} ({item['sku']})"] + [
            f"{k}: {v}" for k, v in (specs.get("specs") or {}).items()]
        if specs.get("moq"):
            facts.append(f"MOQ {specs['moq']}")
        if specs.get("certs"):
            facts.append(f"certifications: {specs['certs']}")
        try:
            raw = glm(_CAPT_PROMPT.format(platform=POSTIZ_PLATFORM,
                                          facts="\n- ".join(facts)),
                      "Write the JSON now.")
            caption, hashtags = str(raw.get("caption", "")).strip(), \
                str(raw.get("hashtags", "")).strip()
        except Exception as e:
            print(f"[c] caption failed for {item['sku']} ({e})", flush=True)
            continue
        # digits guard: model may only reuse catalog fact digits
        if _nums(caption) - _nums("\n".join(facts)):
            print(f"[c] caption invented numbers for {item['sku']}; dropped",
                  flush=True)
            continue
        saved = _post(f"{SPINE_URL}/posts",
                      {"sku": item["sku"], "platform": POSTIZ_PLATFORM,
                       "caption": caption, "hashtags": hashtags})
        drafted.append({"post_id": saved["post_id"], "sku": item["sku"],
                        "preview": caption[:80]})
    if drafted and boss:
        lines = [f"{i+1}. {d['post_id']} [{POSTIZ_PLATFORM}] {d['sku']}\n"
                 f"{d['preview']}…" for i, d in enumerate(drafted)]
        send_text(boss,
                  "[Social drafts ready — approve to schedule]\n"
                  + "\n\n".join(lines)
                  + "\n\nReply APPROVE <id> or REJECT <id>.")
    return {"drafted": drafted, "boss_notified": bool(drafted and boss)}


def _approve_post(pid: str) -> str:
    try:
        posts = _get(f"{SPINE_URL}/posts?status=pending&limit=200")["items"]
    except Exception as e:
        return f"spine unreachable ({e})"
    row = next((p for p in posts if p["post_id"] == pid), None)
    if not row:
        return f"No pending post {pid}."
    _post(f"{SPINE_URL}/posts/{pid}/status", {"status": "approved"}, timeout=10)
    ok, detail = _push_to_postiz(row["caption"], row["hashtags"],
                                 row.get("scheduled_at") or "")
    if ok and detail and detail != "submitted":
        _post(f"{SPINE_URL}/posts/{pid}/publish",
              {"postiz_id": detail,
               "scheduled_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
              timeout=10)
        print(f"[c] {pid} scheduled in postiz ({detail})", flush=True)
        return f"Approved + scheduled. ({pid})"
    _post(f"{SPINE_URL}/events",
          {"kind": "postiz_push_skipped",
           "detail_json": json.dumps({"post_id": pid, "reason": detail})},
          timeout=10)
    print(f"[c] {pid} approved; postiz push skipped ({detail})", flush=True)
    return f"Approved — but NOT pushed to postiz ({detail})."


def _reject_post(pid: str) -> str:
    try:
        _post(f"{SPINE_URL}/posts/{pid}/status", {"status": "rejected"},
              timeout=10)
    except Exception as e:
        return f"reject failed ({e})"
    print(f"[c] {pid} rejected by boss", flush=True)
    return f"Rejected. ({pid})"


# ------------------------------------------------------------------ routes

@app.get("/health")
def health():
    return {"ok": True, "glue": "mock_responder", "instance": INSTANCE, "dry_run": DRY_RUN}


# ------------------------------------------------------------- console API
# Thin proxies for the Appliance Console (docs/console-plan.md §2). The
# browser never talks to organs directly; creds stay server-side. Logic
# lives in the organs/glue — these endpoints are eyes, not brains.

def _evo_get(path: str) -> dict:
    return _get(f"{EVO_URL}{path}", timeout=15, headers={"apikey": EVO_KEY})


def _probe(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=3, context=_CTX) as r:
            return r.status < 500
    except Exception:
        try:
            urllib.request.urlopen(url, timeout=3, context=_CTX)
            return True
        except urllib.error.HTTPError:
            return True
        except Exception:
            return False


@app.get("/console/wa/status")
def console_wa_status():
    """Session state of THE WhatsApp instance (S10 / O4-1)."""
    try:
        raw = _evo_get(f"/instance/connectionState/{INSTANCE}")
        state = (raw.get("instance") or {}).get("state", "unknown")
    except Exception as e:
        return {"state": "unreachable", "instance": INSTANCE, "detail": str(e)}
    return {"state": state, "instance": INSTANCE}


@app.get("/console/wa/qr")
def console_wa_qr():
    """Base64 QR for (re)linking — poll while state != open."""
    try:
        raw = _evo_get(f"/instance/connect/{INSTANCE}")
    except Exception as e:
        return {"qr": None, "detail": str(e)}
    b64 = raw.get("base64") or ""
    if b64 and not b64.startswith("data:"):
        b64 = f"data:image/png;base64,{b64}"
    return {"qr": b64 or None, "state": (raw.get("instance") or {}).get("state")}


@app.post("/console/wa/logout")
def console_wa_logout():
    """Drop the session deliberately (console danger-zone)."""
    detail = ""
    try:
        raw = _post(f"{EVO_URL}/instance/logout/{INSTANCE}", {},
                    headers={"apikey": EVO_KEY}, timeout=30)
        detail = json.dumps(raw)[:200]
    except Exception as e:
        detail = str(e)
    try:
        _post(f"{SPINE_URL}/events", {
            "kind": "session_drop",
            "detail_json": json.dumps({"source": "console", "result": detail})},
            timeout=10)
    except Exception:
        pass
    return {"ok": "error" not in detail.lower(), "detail": detail}


@app.get("/console/organs")
def console_organs():
    """Reachability chips for the stamp's UIs (X1 pointers, not rebuilds)."""
    organs = {
        "evo": EVO_URL,
        "dify": DIFY_URL,
        "chatwoot": CW_URL,
        "n8n": cfg("N8N_URL", "http://localhost:5678").rstrip("/"),
        "postiz": POSTIZ_URL,
        "calc": CALC_URL,
        "spine": SPINE_URL,
    }
    items = []
    for name, base in organs.items():
        items.append({"name": name, "url": base, "up": _probe(base)})
    return {"items": items}


# ------------------------------------------------- console KB + O2 gate ----
# Knowledge-base management (O2-1) and the verification quiz (O2-2) behind
# thin endpoints. Reuses glue/knowledge_ingest.py — one dify dialect, one
# implementation. Client variation stays DATA: KB docs in KNOWLEDGE_DIR,
# quiz overrides in data/o2_quiz.json.

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parent))
import knowledge_ingest as ki  # noqa: E402

KB_DIR = cfg("KNOWLEDGE_DIR", str(ROOT / "data" / "example" / "knowledge"))
KB_DATASET = cfg("DIFY_DATASET", "mjcx-knowledge")

_JOBS: dict[str, dict] = {}

_QUIZ_DEFAULT = [
    ("What is the fuel tank size of the DG-50?", ["120"]),
    ("How noisy is the DG-30?", ["68"]),
    ("What certifications does the DG-100 carry?", ["CE", "ISO"]),
    ("What engine does the DG-50 use?", ["turbo", "4-cylinder"]),
    ("Weight of the DG-30?", ["720"]),
    ("Voltage options of the DG-100?", ["400", "220/380"]),
    ("Controller model on the DG-100?", ["DSE6120", "DeepSea"]),
    ("DG-50 dimensions?", ["2150"]),
    ("What fits inside the STS-200 container?", ["200kVA", "200 kVA"]),
    ("Noise level of the STS-200?", ["75"]),
    ("ATS-50 transfer time?", ["5s", "5 s", "under 5"]),
    ("MOQ for the DG-50?", ["1"]),
    ("HS code for the DG-100 generator?", ["8502"]),
    ("Certifications for the ATS-50?", ["CE"]),
    ("Functions of the ATS panel?", ["start/stop", "auto", "alarm"]),
    ("Material of the STS-200?", ["galvanized", "steel"]),
    ("Is the DG-100 engine turbocharged and intercooled?", ["intercooled", "turbo"]),
    ("Power output of the DG-30?", ["30kVA", "30 kVA", "24kW"]),
    ("Frequency/voltage of the DG-50?", ["50Hz", "380"]),
    ("Does the DG-30 come silent?", ["silent", "silent type", "68dB"]),
]


def _allowed_digits() -> set:
    """Every numeral that appears in the source facts is legal in answers."""
    toks = set()
    for p in sorted(Path(KB_DIR).iterdir()):
        if p.suffix.lower() not in (".md", ".txt"):
            continue
        try:
            content = p.read_text()
        except Exception:
            continue
        for tok in _NUM.findall(content):
            for part in re.split(r"[.,]", tok):
                toks.add(part.lstrip("0") or "0")
                toks.add(part)
    return toks


def _score_answer(ans: str, want_any: list, allowed: set) -> tuple[bool, bool]:
    low = ans.lower()
    hit = any(w.lower() in low for w in want_any)

    def tok_ok(tok: str) -> bool:
        return all(((p.lstrip("0") or "0") in allowed or p in allowed)
                   for p in re.split(r"[.,]", tok))

    bad = {t.replace(",", "") for t in _NUM.findall(ans)}
    bad = {t for t in bad if len(t) > 1 and not tok_ok(t)}
    return bool(hit and not bad), bool(bad)


def _kb_dataset_or_404():
    ds = ki.find_dataset(KB_DATASET)
    if not ds:
        raise HTTPException(404, f"dataset '{KB_DATASET}' does not exist yet")
    return ds


def _dify_delete(path: str) -> None:
    """Dify DELETE answers 204 with an empty body — don't try to JSON it."""
    import urllib.request as _u
    req = _u.Request(f"{ki.BASE}/v1{path}", method="DELETE", headers={
        "Authorization": f"Bearer {ki.KEY}"})
    with _u.urlopen(req, timeout=60, context=_CTX) as r:
        r.read()


@app.get("/console/kb/docs")
def console_kb_docs():
    try:
        ds = ki.find_dataset(KB_DATASET)
        if not ds:
            return {"dataset": None, "items": []}
        docs, page = [], 1
        while True:
            res = ki.api("GET", f"/datasets/{ds['id']}/documents?page={page}&limit=100")
            for d in res.get("data", []):
                docs.append({"id": d["id"], "name": d.get("name", ""),
                             "status": d.get("indexing_status", "unknown"),
                             "enabled": d.get("enabled", True)})
            if page >= res.get("total_pages", 1):
                break
            page += 1
        return {"dataset": {"id": ds["id"], "name": ds["name"]}, "items": docs}
    except Exception as e:
        return {"dataset": None, "items": [], "error": str(e)}


@app.post("/console/kb/ingest")
async def console_kb_ingest(request: Request):
    """Body = raw file bytes; X-Filename header carries the name. Same-name
    upload replaces the old doc (--replace semantics from the CLI)."""
    name = request.headers.get("x-filename", "")
    if not name.lower().endswith((".md", ".txt")):
        raise HTTPException(400, "only .md / .txt files (convert PDFs first)")
    text = (await request.body()).decode("utf-8", errors="replace").strip()
    if not text:
        raise HTTPException(400, "empty file")
    ds = ki.ensure_dataset(KB_DATASET)
    existing = ki.list_docs(ds["id"])
    replaced = False
    if name in existing:
        _dify_delete(f"/datasets/{ds['id']}/documents/{existing[name]}")
        replaced = True
    res = ki.api("POST", f"/datasets/{ds['id']}/document/create-by-text", {
        "name": name, "text": text,
        "indexing_technique": ki.INDEXING,
        "process_rule": {"mode": "automatic"}})
    ki.wait_indexed(ds["id"], res["batch"], name)
    return {"ok": True, "replaced": replaced, "batch": res.get("batch"),
            "document_id": res.get("document_id") or res.get("batch")}


@app.delete("/console/kb/docs/{doc_id}")
def console_kb_doc_delete(doc_id: str):
    ds = _kb_dataset_or_404()
    _dify_delete(f"/datasets/{ds['id']}/documents/{doc_id}")
    return {"ok": True}


@app.post("/console/gates/o2_quiz")
def console_o2_quiz_start():
    qpath = ROOT / "data" / "o2_quiz.json"
    if qpath.exists():
        quiz = [(q["q"], q.get("want_any", []))
                for q in json.loads(qpath.read_text())]
    else:
        quiz = _QUIZ_DEFAULT
    allowed = _allowed_digits()
    jid = uuid.uuid4().hex[:8]
    _JOBS[jid] = {"kind": "o2_quiz", "status": "running",
                  "progress": f"0/{len(quiz)}"}

    def run():
        results, passed, fabricated = [], 0, 0
        for i, (q, want) in enumerate(quiz, 1):
            try:
                ans = spec_answer(q) or ""
            except Exception as e:
                ans = f"(spec workflow error: {e})"
            ok, fab = _score_answer(ans, want, allowed)
            passed += ok
            fabricated += fab
            results.append({"q": q, "answer": ans[:160], "hit": ok, "fabricated": fab})
            _JOBS[jid]["progress"] = f"{i}/{len(quiz)}"
        total = len(quiz)
        required = max(1, math.ceil(90 * total / 100))
        gate = passed >= required and fabricated == 0
        _JOBS[jid].update(status="done", passed=passed, total=total,
                          required=required, fabricated=fabricated,
                          gate_pass=gate, results=results)
        try:
            _post(f"{SPINE_URL}/events", {
                "kind": "gate_o2",
                "detail_json": json.dumps({
                    "passed": passed, "total": total, "required": required,
                    "fabricated": fabricated, "gate_pass": gate})},
                timeout=10)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()
    return {"job_id": jid}


@app.get("/console/gates/o2_quiz/{jid}")
def console_o2_quiz_job(jid: str):
    job = _JOBS.get(jid)
    if not job:
        raise HTTPException(404, "unknown job")
    return {k: v for k, v in job.items() if k != "thread"}


@app.get("/console/gates/last")
def console_gate_last(kind: str = "gate_o2"):
    """Latest persisted verdict for a gate, read back from S8."""
    try:
        rows = _get(f"{SPINE_URL}/events?kind={kind}&limit=1").get("items", [])
    except Exception:
        return {"found": False}
    if not rows:
        return {"found": False}
    try:
        detail = json.loads(rows[0].get("detail_json") or "{}")
    except Exception:
        detail = {}
    detail.pop("thread", None)
    return {"found": True, "ts": rows[0].get("ts"), **detail}


# ---------------------------------------------- console pricing + O3 gate --
# S2 is readable here; it stays editable in git (config-as-code rule #6).
# The O3 backtest re-computes REAL past quotes through calc — ±2%, ≥90%
# gate, EXAMPLE mode never clears (flowchart O3-2: never live on unverified
# pricing).

_O3_TOL = 0.02
_O3_GATE = 0.90
_O3_MIN_QUOTES = 10   # flowchart O3-2: 10–20 REAL past quotes


@app.get("/console/pricing/rules")
def console_pricing_rules():
    return {"path": RULES_PATH, "currency": RULES.get("currency"),
            "validity_days": RULES.get("validity_days"), "rules": RULES,
            "schema_version": RULES.get("schema_version")}


@app.post("/console/pricing/rules")
async def console_pricing_rules_save(request: Request):
    """Console Edit-mode save (v1.1-B): validate -> .bak backup -> write
    RULES_PATH in place -> calc /rules/reload -> refresh this process' parse
    vocabulary. Failed reload restores the old file (calc self-restores from
    .bak too) and reports — no silent-stale state, no lost engine."""
    try:
        body = json.loads(await request.body())
        rules = body["rules"]
        if not isinstance(rules, dict):
            raise ValueError("rules must be an object")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f'body must be JSON {{"rules": {{...}}}} ({e})')

    # 1. calc is the validation authority (same code path that computes)
    try:
        verdict = _post(f"{CALC_URL}/rules/validate", {"rules": rules},
                        timeout=15)
    except Exception as e:
        raise HTTPException(502, f"calc unreachable, refusing blind write ({e})")
    if not verdict.get("ok"):
        return JSONResponse(status_code=400, content={
            "ok": False, "stage": "validate",
            "problems": verdict.get("problems", [])})

    # 2. backup + atomic-ish replace
    path = Path(RULES_PATH)
    old_text = path.read_text()
    bak = path.with_suffix(path.suffix + ".bak")
    new_text = json.dumps(rules, indent=2, ensure_ascii=False) + "\n"
    if new_text == old_text:
        return {"ok": True, "unchanged": True,
                "schema_version": rules.get("schema_version")}
    bak.write_text(old_text)
    path.write_text(new_text)
    print(f"[pricing] saved {path.name} (backup at {bak.name})", flush=True)

    # 3. hot reload into calc's engine
    try:
        res = _post(f"{CALC_URL}/rules/reload", {}, timeout=15)
    except Exception as e:
        res = {"ok": False, "error": f"reload call failed: {e}"}
    if not res.get("ok"):
        path.write_text(old_text)          # belt & braces (calc already rolled back)
        try:
            _post(f"{CALC_URL}/rules/reload", {}, timeout=15)
        except Exception:
            pass
        return JSONResponse(status_code=400, content={
            "ok": False, "stage": "reload", "error": str(res.get("error"))[:300],
            "rolled_back": True})
    # 4. glue's own B1 vocabulary follows the new rules — no restart needed
    _refresh_rules_vocab()
    return {"ok": True, "schema_version": res.get("schema_version"),
            "path": str(path), "backup": str(bak)}


def _run_backtest(history: list) -> dict:
    results, match, errors = [], 0, 0
    for h in history:
        ref = h.get("ref", "?")
        try:
            r = _post(f"{CALC_URL}/quote", {
                "customer_id": "o3-backtest",
                "customer_tier": h["customer_tier"],
                "lines": h["lines"]}, timeout=30)
            if r.get("status") != "OK":
                raise RuntimeError(str(r.get("gaps") or r.get("detail") or r)[:120])
            got = float(r["quote"]["total"])
            want = float(h["quoted_total"])
            delta = (got - want) / want if want else 1.0
            ok = abs(delta) <= _O3_TOL
            match += ok
            results.append({"ref": ref, "got": round(got, 2), "want": want,
                            "delta_pct": round(delta * 100, 2), "ok": ok})
        except Exception as e:
            errors += 1
            results.append({"ref": ref, "error": str(e)[:140], "ok": False})
    total = len(history)
    rate = match / total if total else 0.0
    enough = total >= _O3_MIN_QUOTES
    return {"total": total, "match": match, "errors": errors,
            "required": max(1, math.ceil(_O3_GATE * total)),
            "min_quotes": _O3_MIN_QUOTES,
            "rate_pct": round(rate * 100, 1),
            "note": None if enough else f"needs ≥{_O3_MIN_QUOTES} historical quotes",
            "gate_pass": bool(enough and rate >= _O3_GATE and errors == 0),
            "results": results}


def _persist_gate(kind: str, detail: dict) -> None:
    try:
        _post(f"{SPINE_URL}/events",
              {"kind": kind, "detail_json": json.dumps(detail)}, timeout=10)
    except Exception:
        pass


@app.post("/console/gates/o3_backtest")
async def console_o3_backtest(request: Request):
    """Body optional: {"history":[...]} uploads REAL history. Empty body runs
    data/o3_history.json if present, else the example file in EXAMPLE mode
    (machinery proof only — never clears the gate)."""
    body = await request.body()
    if body.strip():
        try:
            payload = json.loads(body)
            history = payload.get("history", payload)
            if not isinstance(history, list):
                raise ValueError
        except Exception:
            raise HTTPException(400, "body must be JSON: {\"history\":[...]} or [...] ")
        mode, source = "REAL", "console-upload"
    else:
        real = ROOT / "data" / "o3_history.json"
        example = ROOT / "data" / "o3_history.example.json"
        if real.exists() and json.loads(real.read_text() or "[]"):
            history = json.loads(real.read_text())
            mode, source = "REAL", "data/o3_history.json"
        else:
            history = json.loads(example.read_text())
            mode, source = "EXAMPLE", "data/o3_history.example.json"
    if not history:
        raise HTTPException(400, "no history rows")
    res = _run_backtest(history)
    if mode == "EXAMPLE":
        res["gate_pass"] = False
    res.update({"mode": mode, "source": source})
    _persist_gate("gate_o3", {
        "passed": res["match"], "total": res["total"], "errors": res["errors"],
        "gate_pass": res["gate_pass"], "mode": mode})
    return res


@app.get("/console/gates/summary")
def console_gates_summary():
    wa = {"found": False}
    try:
        st = _evo_get(f"/instance/connectionState/{INSTANCE}")
        wa = {"found": True, "state": (st.get("instance") or {}).get("state")}
    except Exception:
        pass
    return {
        "o2": console_gate_last("gate_o2"),
        "o3": console_gate_last("gate_o3"),
        "go_live": console_gate_last("go_live"),
        "whatsapp": wa,
        "postiz_key_set": bool(POSTIZ_API_KEY),
    }


@app.post("/console/gates/go_live")
async def console_go_live(request: Request):
    """Hard gates are enforced SERVER-SIDE (no partial go-lives, O5-1)."""
    try:
        body = json.loads((await request.body()) or "{}")
    except Exception:
        body = {}
    manual = body.get("manual_confirmed", [])
    s = console_gates_summary()
    blockers = []
    if s["whatsapp"].get("state") != "open":
        blockers.append("WhatsApp session is not open")
    o2, o3 = s["o2"], s["o3"]
    if not (o2.get("found") and o2.get("gate_pass")):
        blockers.append("O2 verification quiz not passed")
    if not (o3.get("found") and o3.get("gate_pass") and o3.get("mode") == "REAL"):
        blockers.append("O3 backtest not passed against REAL history")
    if blockers:
        return {"ok": False, "blockers": blockers}
    _persist_gate("go_live", {"go_live": True,
                              "manual_confirmed": manual})
    return {"ok": True}


# -------------------------------------------- console inbox (v1.1-A) -------
# The console is a second CLIENT of chatwoot's API — never a second store
# (X1: chatwoot stays S4; nothing transcript-shaped persists outside it).
# Take-over replies go out under the ADMIN api-token identity (CW_TOKEN),
# deliberately NOT the evo-bridge bot identity, so /a6/sla_tick sees a
# non-bridge human sender and stops beaconing that conversation (trap #21).

def _require_cw() -> None:
    if not CW_TOKEN:
        raise HTTPException(503, "CHATWOOT_API_TOKEN not configured")


def _cw_or_502(method: str, path: str, payload: dict | None = None) -> dict:
    try:
        return _cw(method, path, payload)
    except urllib.error.HTTPError as e:
        code = 404 if e.code == 404 else 502
        raise HTTPException(code, f"chatwoot {e.code} on {path.split('?')[0]}")
    except Exception as e:
        raise HTTPException(502, f"chatwoot unreachable: {e}")


@app.get("/console/inbox/conversations")
def console_inbox_conversations(status: str = "open"):
    """All chats (open first), proxied live from chatwoot. Also feeds the
    nav unread badge via total_unread."""
    _require_cw()
    raw = _cw_or_502("GET", f"/conversations?status={urllib.parse.quote(status)}")
    items = []
    for c in raw.get("data", {}).get("payload", []):
        contact = ((c.get("meta") or {}).get("sender")) or {}
        last_buyer = ""
        for m in reversed(c.get("messages") or []):
            if m.get("message_type") == 0 and not m.get("private"):
                last_buyer = str(m.get("content") or "")[:140]
                break
        items.append({
            "id": c["id"], "status": c.get("status"),
            "contact_name": contact.get("name")
                            or contact.get("identifier") or f"#{c['id']}",
            "identifier": contact.get("identifier") or "",
            "unread_count": c.get("unread_count") or 0,
            "priority": c.get("priority"),
            "created_at": c.get("created_at"),
            "last_activity_at": c.get("last_activity_at"),
            "last_buyer_line": last_buyer,
        })
    items.sort(key=lambda x: x["last_activity_at"] or 0, reverse=True)
    return {"items": items, "total_unread": sum(i["unread_count"] for i in items)}


@app.get("/console/inbox/{cid}/messages")
def console_inbox_messages(cid: int):
    """Thread + contact meta + agent map. Sender resolution happens against
    /agents emails every call — ids are never hardcoded (trap #21)."""
    _require_cw()
    conv = _cw_or_502("GET", f"/conversations/{cid}")
    raw_msgs = _cw_or_502("GET", f"/conversations/{cid}/messages")
    agents = _cw_or_502("GET", "/agents")
    if isinstance(agents, dict):
        agents = agents.get("payload", [])
    bot_ids = [a["id"] for a in agents
               if str(a.get("email", "")).lower() == CW_BRIDGE_EMAIL.lower()]
    msgs = []
    for m in raw_msgs.get("payload", []):
        sender = m.get("sender") or {}
        msgs.append({
            "id": m["id"],
            "content": m.get("content"),
            "message_type": m.get("message_type"),   # 0 buyer / 1 agent-side
            "private": bool(m.get("private")),
            "created_at": m.get("created_at"),
            "sender_type": m.get("sender_type") or sender.get("type"),
            "sender_id": sender.get("id") if sender else m.get("sender_id"),
            "sender_name": (sender.get("available_name") or sender.get("name"))
                           if sender else "",
        })
    inner = conv.get("data") or conv
    contact = ((inner.get("meta") or {}).get("sender")) or {}
    return {
        "conversation_id": inner.get("id", cid),
        "status": inner.get("status"),
        "contact": {"name": contact.get("name") or f"#{cid}",
                    "identifier": contact.get("identifier") or ""},
        "bot_sender_ids": bot_ids,
        "agents": {str(a["id"]): a.get("available_name") or a.get("name", "?")
                   for a in agents},
        "messages": sorted(msgs, key=lambda m: m["created_at"] or 0),
    }


@app.post("/console/inbox/{cid}/reply")
async def console_inbox_reply(cid: int, request: Request):
    """Take-over: free-edit PUBLIC outgoing message through chatwoot under
    the ADMIN api-token identity (NOT the evo-bridge bot — trap #28). evo
    mirrors it to WhatsApp; its non-bridge sender marks the conversation
    human-handled for /a6/sla_tick."""
    _require_cw()
    reply_token = CW_ADMIN_TOKEN or CW_TOKEN
    if not reply_token:
        raise HTTPException(503,
            "no admin token: set CHATWOOT_ADMIN_TOKEN (bridge token would "
            "post as the bot and never stop the SLA beacon)")
    try:
        body = json.loads(await request.body())
        content = str(body.get("content", "")).strip()
    except Exception:
        raise HTTPException(400, 'body must be JSON {"content": "..."}')
    if not content:
        raise HTTPException(400, "content is empty")
    res = _cw("POST", f"/conversations/{cid}/messages",
              {"content": content, "message_type": "outgoing",
               "private": False}, token=reply_token)
    return {"ok": True, "id": res.get("id"), "created_at": res.get("created_at")}


# ------------------------------------------------- v1.2 threads (S4 spine) --

@app.post("/console/threads/{cid}/reply")
async def console_thread_reply(cid: int, request: Request):
    """v1.2 take-over: free-edit staff message sent to the buyer over
    WhatsApp via evo DIRECTLY — no chatwoot, no bridge identity. Mirrored
    into spine as a HUMAN outbound, which clears any armed escalation and
    marks the thread handled for /a6/sla_tick."""
    try:
        body = json.loads(await request.body())
        content = str(body.get("content", "")).strip()
    except Exception:
        raise HTTPException(400, 'body must be JSON {"content": "..."}')
    if not content:
        raise HTTPException(400, "content is empty")
    convo = await asyncio.to_thread(
        _get, f"{SPINE_URL}/conversations/{cid}/messages")
    jid = convo["conversation"]["wa_jid"]
    try:
        await asyncio.to_thread(send_text, jid, content)
    except Exception as e:
        # never mirror an unsent message — staff must know delivery failed
        raise HTTPException(502, f"send failed ({'email' if jid.startswith('email:') else 'evo'}): {str(e)[:200]}")
    await asyncio.to_thread(
        _post, f"{SPINE_URL}/conversations/{cid}/messages",
        {"direction": "out", "sender_kind": "human", "body": content[:4000]})
    return {"ok": True, "conversation_id": cid, "to": jid}


# ------------------------------------------------- console voice samples ---
# O4-2: the client's 5-10 real messages become the tone anchor. This edits
# ONLY the Samples section of dify/prompts/voice_guide.md — config-as-code
# stays true (the file lives in git; a .bak lands next to every write).

VOICE_GUIDE = ROOT / "dify" / "prompts" / "voice_guide.md"
_SAMPLES_HEAD = "## Samples"
_SAMPLES_NEXT = "## Reply-generation contract"


def _samples_span(text: str) -> tuple[int, int, int]:
    """(section start, end of the HEADING LINE, start of next section)."""
    start = text.index(_SAMPLES_HEAD)
    line_end = text.index("\n", start) + 1
    end = text.index(_SAMPLES_NEXT)
    return start, line_end, end


@app.get("/console/voice/samples")
def console_voice_samples_get():
    text = VOICE_GUIDE.read_text()
    _, line_end, end = _samples_span(text)
    return {"text": text[line_end:end].strip()}


@app.post("/console/voice/samples")
async def console_voice_samples_set(request: Request):
    try:
        body = json.loads(await request.body())
        new_block = str(body.get("text", ""))
    except Exception:
        raise HTTPException(400, "body must be JSON {\"text\": ...}")
    if _SAMPLES_NEXT.lower() in new_block.lower() or _SAMPLES_HEAD.lower() in new_block.lower():
        raise HTTPException(400, "sample text must not contain section headings")
    text = VOICE_GUIDE.read_text()
    _, line_end, end = _samples_span(text)
    rebuilt = text[:line_end] + "\n" + new_block.strip() + "\n\n" + text[end:]
    VOICE_GUIDE.with_suffix(".md.bak").write_text(text)
    VOICE_GUIDE.write_text(rebuilt)
    print("[voice] samples updated (backup at voice_guide.md.bak)", flush=True)
    return {"ok": True}


def _extract_text(message: dict) -> str:
    for key in ("conversation",):
        if message.get(key):
            return message[key]
    for key in ("extendedTextMessage", "imageMessage", "documentMessage", "videoMessage"):
        sub = message.get(key) or {}
        if sub.get("text") or sub.get("caption"):
            return sub.get("text") or sub.get("caption")
    return ""


def route(customer: dict, text: str, remote: str = "") -> str | None:
    """A3-2 + Phase B. Returns the buyer-facing reply, or None for silence."""
    # Obvious-noise gate (deterministic): keyboard mash, emoji-only, symbol
    # spam. The triage model wavers on these (SPAM 0.95 one run, OTHER 0.3
    # the next — O5-S8 flake) and low-confidence then escalates GIBBERISH to
    # a human. Letters < half the message => nothing to say, be silent.
    stripped = text.strip()
    if len(stripped) >= 4:
        alpha = sum(ch.isalpha() for ch in stripped)
        if alpha / len(stripped) < 0.5:
            print("[a3] obvious noise -> polite silence", flush=True)
            return None
    # Pricing continuation (thread state, BEFORE classify): when WE asked
    # for quantity in a pending offer and the buyer replies with one, feed
    # the canonical ask into the normal pipeline — classifying "probably
    # like 10 units" statelessly routes it to a human and breaks the
    # conversation exactly where a sale was closing (live test 01:05).
    th0 = _THREAD.get(remote) or {}
    offer = th0.get("offer_pending")
    forced_price = False
    if offer:
        about = offer.get("about") or ""
        if re.fullmatch(r"[A-Z]{2,3}-\d+", about) \
                and not re.search(r"\b(DG-\d+|ATS-\d+|STS-\d+)\b", text.upper()):
            qm = re.search(
                r"\b(\d+)\s*(?:units?|pcs|pieces|sets?|unit|台|个|件)\b"
                r"|^\s*(?:like |around |approx\.? |~)?(\d{1,4})\s*$",
                text, re.I)
            if qm:
                qty = qm.group(1) or qm.group(2)
                print(f"[thread] pricing continuation: {qty}x {about}",
                      flush=True)
                text = f"{qty} units of {about} STD"
                _THREAD.get(remote, {}).pop("offer_pending", None)
                forced_price = True
    if forced_price:
        # The canonical ask IS a price request — no classifier needed (the
        # live triage app calls bare 'quantity + SKU' messages OTHER).
        cls = {"intent": "PRICE_Q", "language": th0.get("lang") or "en",
               "urgency": "normal", "sentiment": "neutral",
               "confidence": 0.99, "route": "price"}
    else:
        cls = classify(text)
    intent = cls.get("intent")
    lang = (cls.get("language") or "en")[:2]
    _THREAD.setdefault(remote, {})["lang"] = lang
    if cls.get("route") != "human":
        # a successfully-routed exchange re-arms the closer's clarify budget
        _THREAD.get(remote, {}).pop("clarified", None)
    print(f"[a3] intent={intent} lang={lang} conf={cls.get('confidence')} "
          f"urgency={cls.get('urgency')} sentiment={cls.get('sentiment')} "
          f"route={cls.get('route')}", flush=True)

    tier = customer.get("tier") or "new"
    cid = customer.get("customer_id")

    if intent == "SPAM":
        return None  # polite silence (O5 scenario 8)

    th = _THREAD.get(remote) or {}
    if _is_agreement(text):
        offer = th.get("offer_pending")
        if offer:
            # The bot offered something one message ago and the buyer
            # accepted — breaking that promise into a human handoff is the
            # single most unnatural thing a sales bot can do (live test
            # 2026-08-25: "yes please" -> escalation). Fulfill it instead.
            if offer.get("kind") == "pdf":
                print(f"[thread] buyer accepted PDF offer "
                      f"({offer.get('quote_id')})", flush=True)
                threading.Thread(
                    target=b4_deliver,
                    args=(remote, offer["customer"], offer["quote"],
                          offer["quote_id"]),
                    daemon=True).start()
                return tt(lang, "formal_offer")
            print(f"[thread] fulfilling pending offer about "
                  f"{offer.get('about')}", flush=True)
            return (compose(
                "in your previous message you offered more information and "
                "the buyer just accepted — DELIVER IT NOW from the facts: "
                "concrete details, no hedging, no handoff, no 'let me "
                "check'; end by inviting the next concrete step (quantity "
                "for pricing, or their application)", lang, text,
                facts=list(offer["facts"]) + _company_line(), remote=remote)
                or tt(lang, "welcome"))
        # agreement with nothing pending: treat as light acknowledgment and
        # keep the door open rather than escalating small talk
        if th.get("greeted"):
            return (compose(
                "the buyer sent a short agreement/acknowledgment mid-thread "
                "with no open question on your side — acknowledge warmly in "
                "one line and invite their next need; do NOT escalate or "
                "hand off", lang, text, facts=_company_line(), remote=remote)
                or tt(lang, "welcome"))
    else:
        # any substantive message invalidates a stale pending offer
        _THREAD.get(remote, {}).pop("offer_pending", None)

    if (intent in ("GREETING", "OTHER") and not th.get("greeted")
            and _is_engage(text)):
        # "so okay, lets go" as the FIRST message: a buyer leaning in gets
        # the anchored welcome, not a cold handoff (live test 2026-08-25).
        _THREAD.setdefault(remote, {})["greeted"] = True
        return (compose("the buyer signals they are ready to start talking "
                        "business — welcome them warmly and anchor your "
                        "reply in what the company actually makes (facts "
                        "below), then ask ONE opening question about their "
                        "need", lang, text, facts=_company_line(),
                        remote=remote)
                or tt(lang, "greet"))

    if intent in ("GREETING", "OTHER") and _match_any(text, _CAPABILITY_RES):
        # "so what do u do?" deserves the real product line, not an invented
        # 'wide range of products' pitch. Deterministic detector, grounded
        # facts, still zero arithmetic. Checked BEFORE the greeting branches
        # so an identity question never gets a generic welcome.
        _THREAD.setdefault(remote, {})["greeted"] = True
        line_facts = _company_line()
        _set_offer(remote, "the product line / other accessories", line_facts)
        return (compose(
            "the buyer asks what this company actually does or sells — "
            "answer concretely from the facts: name the real product line, "
            "then ask ONE question about their application or required "
            "power range; no generic 'we do everything' claims beyond the "
            "facts", lang, text, facts=line_facts, remote=remote)
            or tt(lang, "capability").format(
                line=", ".join(MATERIALS) or "generator sets"))

    if intent == "GREETING":
        th = _THREAD.get(remote) or {}
        if th.get("greeted"):
            # ongoing thread: a second "hi" is small talk, not an opener.
            # Re-welcoming here is how the bot looked broken (conv #3).
            return (compose(
                "a mid-conversation hello/small-talk from a buyer you are "
                "already talking to — answer warmly in one line WITHOUT "
                "re-introducing yourself or re-welcoming, then gently steer "
                "back to what they need (at most ONE question)", lang, text,
                facts=_company_line(), remote=remote)
                or tt(lang, "welcome"))
        _THREAD.setdefault(remote, {})["greeted"] = True
        return (compose("a first greeting from a new buyer who just said hi — "
                        "welcome them and anchor your reply in what the "
                        "company actually makes (facts below), then invite "
                        "their first question",
                        lang, text, facts=_company_line(), remote=remote)
                or tt(lang, "greet"))

    if intent == "THANKS":
        return (compose("the buyer is thanking you / closing the chat — "
                        "acknowledge warmly and leave the door open",
                        lang, text, remote=remote)
                or tt(lang, "welcome"))

    if intent == "SPEC_Q":
        # Deterministic S1 read when the message names a product — exact SKU
        # token OR a natural-name alias ("the ats panel" -> ATS-50). Buyers
        # rarely type SKUs; without aliasing they fall into RAG, whose
        # KB-miss behaviour is the fake "let me check" (traps #34/#37).
        m = re.search(r"\b(DG-\d+|ATS-\d+|STS-\d+)\b", text.upper())
        sku = m.group(1) if m else _alias_sku(text)
        if sku:
            try:
                return _catalog_reply(
                    _get(f"{SPINE_URL}/catalog/{sku}"), lang, text, remote)
            except Exception as e:
                print(f"[a3-spec] catalog lookup {sku} failed: {e}",
                      flush=True)
        # Availability probe ("do you have kaolin?") with NO catalog hit:
        # answer the grounded negative plainly + pivot to the real line.
        # A human sales thread never stalls with a fake "let me check" —
        # 没有就说没有. Only OUT-of-domain probes take this path; an
        # in-domain availability ask ("do you have a 50kVA silent genset?")
        # still goes to RAG below, because we likely DO carry it.
        if _match_any(text, _AVAILABILITY_RES) and not _in_domain(text):
            print("[a3-spec] availability probe, no S1 hit -> plain "
                  "'not our line' + pivot", flush=True)
            reply = (compose(
                "the buyer asks whether you carry something that is NOT in "
                "your product facts — say briefly and honestly that it is "
                "not your line (a plain 'no' grounded in the catalog is "
                "allowed here), then name what you DO make from the facts "
                "and invite their power-equipment need with at most ONE "
                "question; do NOT promise to check or come back later",
                lang, text, facts=_company_line(), remote=remote)
                or tt(lang, "not_ours").format(
                    line=", ".join(MATERIALS) or "generator sets"))
            escalate_to_chatwoot(remote, text, "SPEC_Q", lang, customer,
                                 reply,
                                 "Out-of-catalog availability probe — answered "
                                 "plainly 'not our line' + pivoted to the real "
                                 "line; demand signal for staff.\n")
            return reply
        rag = spec_answer(text)
        if rag and not _looks_like_stall(rag):
            print("[a3-spec] answered from knowledge base", flush=True)
            # the RAG reply usually ends in an offer ("want more details?")
            # — arm it so "yes please" fulfills instead of dead-ending.
            # The answer itself is the fact source: the subset-number guard
            # lets the model reuse anything in it but invent nothing new.
            _set_offer(remote, "the topic just discussed", [rag])
            return rag
        if rag:  # stall signature — repair instead of relaying the lie
            print("[a3-spec] RAG stalled ('check with team') -> repairing",
                  flush=True)
            sku = _alias_sku(text)
            if sku:
                try:
                    return _catalog_reply(
                        _get(f"{SPINE_URL}/catalog/{sku}"), lang, text,
                        remote)
                except Exception:
                    pass
        # Nothing deterministic worked. The holding line below now tells the
        # TRUTH because this escalation arms a real staff follow-up.
        reply = tt(lang, "spec_stub")
        escalate_to_chatwoot(remote, text, "SPEC_Q", lang, customer, reply,
                             "Knowledge-base miss — A4 low-confidence path, "
                             "never guess specs.\n")
        return reply

    if intent == "PRICE_Q":
        if AUTONOMY == "assistant":
            # dial = assistant: the AI never touches money. Human prepares
            # the numbers; buyer hears the honest holding line.
            print("[policy] autonomy=assistant -> price ask to human",
                  flush=True)
            reply = (compose(
                "the buyer asks for pricing — say the team is preparing a "
                "quotation for them and a colleague will send the numbers "
                "here shortly; do NOT give any price, figure or discount",
                lang, text, remote=remote)
                or tt(lang, "manual_quote"))
            escalate_to_chatwoot(remote, text, "PRICE_Q", lang, customer,
                                 reply,
                                 "Autonomy=assistant — AI does not quote; "
                                 "human prepares the quotation.\n")
            return reply
        parsed = glm(PARSE_PROMPT, text)
        action = parsed.get("action")
        print(f"[b1] parse action={action} lines={parsed.get('lines')}", flush=True)
        if action == "custom":
            reason = parsed.get("reason", "outside standard rules")
            reply = (compose("the buyer's ask needs a tailored quotation from an "
                             "engineer (reason: {reason}) — say it is flagged "
                             "for a tailored quote and a human follows up; do "
                             "NOT mention prices", lang, text, remote=remote)
                     or tt(lang, "custom").format(reason=reason))
            escalate_to_chatwoot(remote, text, "CUSTOM_ODM", lang, customer,
                                 reply, f"Tailored-quote reason: {reason}\n")
            return reply
        if action == "clarify":
            return parsed.get("question") or "How many units do you need?"
        # S2 v3 structural no-leak: ANY internal_only material in the request
        # skips inline computation entirely -> B5 human quote. calc is never
        # called on this path, so there is no number to leak (X4 keeps staff
        # free to compute manually). Same philosophy as removing the PDF CTA.
        hidden = hidden_materials(parsed.get("lines", []))
        if hidden:
            mats = ", ".join(hidden)
            print(f"[b-path] internal_only materials [{mats}] -> B5, no calc call",
                  flush=True)
            reply = (compose(
                "the buyer asked about items that are quoted by the team only — "
                "say their request was passed to a colleague who will confirm "
                "the numbers here shortly; do NOT give any price or number",
                lang, text, remote=remote)
                or tt(lang, "internal_price"))
            escalate_to_chatwoot(remote, text, "PRICE_INTERNAL", lang, customer,
                                 reply,
                                 f"Price visibility: {mats} is internal_only "
                                 "(S2 v3) — buyer hears 'team will confirm'; "
                                 "human quote required.\n")
            return reply
        try:
            res = _post(f"{CALC_URL}/quote", {
                "customer_id": cid, "customer_tier": tier,
                "currency": RULES.get("currency", "USD"),
                "lines": parsed.get("lines", [])})
        except Exception as e:
            print(f"[b2] calc unreachable: {e}", flush=True)
            reply = tt(lang, "calc_down")
            escalate_to_chatwoot(remote, text, "CALC_DOWN", lang, customer,
                                 reply, f"calc :8100 unreachable: {e}\n")
            return reply
        if res.get("status") != "OK":
            gaps = "; ".join(res.get("gaps", []))
            print(f"[b5] escalate, gaps={gaps}", flush=True)
            reply = (compose("this request falls outside standard pricing rules "
                             "so a human must calculate it manually — reassure, "
                             "promise a person will reply with numbers; do NOT "
                             "give any price or timeline", lang, text,
                             remote=remote)
                     or tt(lang, "escalate_gaps"))
            escalate_to_chatwoot(remote, text, "PRICE_GAPS", lang, customer,
                                 reply, f"Pricing-rules gap: {gaps}\n")
            return reply
        q = res["quote"]
        # save to S5 then mark sent — same chain as the spike E2E test
        saved = None
        try:
            saved = _post(f"{SPINE_URL}/quotes", {
                "customer_id": cid, "request_json": parsed, "result_json": res,
                "total": q["total"], "currency": q["currency"]})
            _post(f"{SPINE_URL}/quotes/{saved['quote_id']}/status",
                  {"status": "sent"})
            print(f"[s5] {saved['quote_id']} saved+sent", flush=True)
        except Exception as e:
            print(f"[s5] save failed (price already computed): {e}", flush=True)
        # B4-1/2: explicit formal ask -> render PDF in the background so the
        # inline price text goes out immediately; the document follows here.
        if parsed.get("formal") and saved is not None:
            threading.Thread(
                target=b4_deliver,
                args=(remote, customer, q, saved["quote_id"]),
                daemon=True).start()
        bullets = [
            f"• {l['description']} ×{l['qty']} — {q['currency']} {l['line_total']:,.2f}"
            for l in q["lines"]]
        facts = bullets + [f"Total: {q['currency']} {q['total']:,.2f}",
                           f"Valid until {q['valid_until']}",
                           f"{q['discount_pct']:.0f}% quantity discount included"]
        body = compose(
            "delivering an indicative price in chat after computing it — keep "
            "a short bullet list for line items, then the total, the discount "
            "note and the validity date",
            lang, text, facts=facts, remote=remote, numbers="exact",
            final_note=PRICE_FINAL_NOTE)
        tail = tt(lang, "formal_offer") if parsed.get("formal") \
            else tt(lang, "pdf_offer")
        if saved is not None:
            # "Want a formal PDF?" is an offer; if the buyer answers
            # "yes please", deliver the PDF instead of dead-ending (thread
            # fulfillment, same mechanism as spec-answer offers).
            _set_offer(remote, f"{saved['quote_id']} formal pdf",
                       facts + [tail], kind="pdf", quote=q,
                       quote_id=saved["quote_id"], customer=dict(customer))
        if body:
            # exact-mode guards the date DIGITS, not the phrasing — the
            # model occasionally rewords it away (O5-S3 flake). Validity is
            # contractual; normalize structurally.
            if "Valid until" not in body and "有效期" not in body:
                body += (f"\n\n报价有效期至 {q['valid_until']}。"
                         if lang.startswith("zh")
                         else f"\n\nValid until {q['valid_until']}.")
            return f"{body}\n\n{tail}"
        return tt(lang, "price_ok").format(
            lines="\n".join(bullets), currency=q["currency"],
            total=q["total"], discount=q["discount_pct"],
            valid_until=q["valid_until"])

    # COMPLAINT / CUSTOM_ODM / SHIPPING / OTHER -> always-human paths (A6/B5)
    if intent == "COMPLAINT":
        print(f"[a6] escalate intent={intent}", flush=True)
        reply = (compose("an angry complaint — acknowledge once, apologize once, "
                         "say it is flagged URGENT and a human will reply here "
                         "shortly; no excuses, no defensiveness, never promise "
                         "a timeframe or hours", lang, text,
                         remote=remote)
                 or tt(lang, "complaint"))
        escalate_to_chatwoot(
            remote, text, intent, lang, customer, reply,
            f"Urgency {cls.get('urgency')}, sentiment {cls.get('sentiment')} — "
            "always-human list, priority complaint.\n")
        return reply
    # dial = closer: ONE clarifying question before giving an ambiguous
    # message to a human. Commits to nothing, so it stays inside the safety
    # envelope; once per thread, then the normal handoff applies.
    th_c = _THREAD.get(remote) or {}
    if AUTONOMY == "closer" and not th_c.get("clarified") and th_c.get("greeted"):
        _THREAD.setdefault(remote, {})["clarified"] = True
        print("[policy] autonomy=closer -> clarify instead of handoff",
              flush=True)
        reply = (compose(
            "the buyer's message is unclear — ask ONE short, friendly "
            "clarifying question to understand what they need; commit to "
            "NOTHING: no capabilities, no prices, no opinions on their "
            "plans", lang, text, facts=_company_line(), remote=remote)
            or tt(lang, "human"))
        escalate_to_chatwoot(remote, text, intent or "OTHER", lang, customer,
                             reply,
                             f"Autonomy=closer — AI asked a clarifying "
                             f"question first (conf {cls.get('confidence')}). "
                             "Escalation armed as fallback.\n")
        return reply
    print(f"[a6] escalate intent={intent}", flush=True)
    reply = (compose("the message is outside what you can answer — do NOT "
                     "engage with its content, do NOT confirm, deny or "
                     "comment on any service, product or capability, and do "
                     "NOT react to the buyer's plans; write ONLY a neutral "
                     "holding line: this needs personal attention from the "
                     "team and a colleague will follow up here shortly",
                     lang, text, remote=remote)
             or tt(lang, "human"))
    escalate_to_chatwoot(remote, text, intent or "OTHER", lang, customer, reply,
                         f"Confidence {cls.get('confidence')} — below threshold "
                         "or always-human intent.\n")
    return reply


@app.post("/webhook/evo")
async def webhook(request: Request):
    body = await request.json()
    event = body.get("event")
    if event != "messages.upsert":
        return {"ignored": event}

    data = body.get("data") or {}
    key = data.get("key") or {}
    msg_id = key.get("id") or ""
    remote = key.get("remoteJid") or ""
    if key.get("fromMe"):
        return {"skipped": "fromMe"}
    if not remote or remote.endswith("@g.us") or remote.startswith("status@"):
        return {"skipped": "group/status"}

    text = _extract_text(data.get("message") or {})
    if not text.strip():
        return {"skipped": "no text"}

    if msg_id in _seen:  # A1 idempotency — webhook retries happen
        return {"deduped": msg_id}
    _seen.add(msg_id)
    if len(_seen) > 5000:
        _seen.clear()

    print(f"[a1] {remote}: {text[:120]}", flush=True)

    # Approval shortcuts — staff approves quote follow-ups, boss approves
    # social posts. Checked BEFORE routing; wrong sender never reaches them.
    m = re.match(r"^(APPROVE|REJECT)\s+([QP]-[A-Z0-9]+)\s*$", text.strip(), re.I)
    if m:
        action, ref = m.group(1).upper(), m.group(2).upper()
        if ref.startswith("Q-"):
            allowed, handler = (cfg("STAFF_WHATSAPP", STAFF_WHATSAPP),
                                _approve_followup if action == "APPROVE" else None)
        else:
            allowed, handler = (cfg("BOSS_WHATSAPP", BOSS_WHATSAPP),
                                _approve_post if action == "APPROVE"
                                else _reject_post)
        if handler and remote.split("@")[0].lstrip("+") == \
                allowed.lstrip("+"):
            try:
                send_text(remote, str(handler(ref)))
            except Exception as e:
                print(f"[approval] {ref} failed: {e}", flush=True)
            return {"ok": True, "action": action, "ref": ref}

    try:
        resolved = _post(f"{SPINE_URL}/resolve",
                         {"wa_jid": remote, "name": data.get("pushName") or None})
        customer = resolved["customer"]
        print(f"[a2] {resolved['status']} customer={customer['customer_id']} "
              f"tier={customer.get('tier')}", flush=True)
    except Exception as e:
        print(f"[a2] spine down, anonymous fallback: {e}", flush=True)
        customer = {"customer_id": "anonymous", "tier": "new"}

    # S4 mirror: the buyer's line lands in the spine transcript BEFORE
    # routing, so staff see the thread even if routing dies mid-flight.
    _mirror(remote, data.get("pushName") or None, "in", "buyer", text)

    try:
        # route() makes blocking LLM/spine HTTP calls (classify alone can
        # take seconds; dify timeout 90s). Running it inline inside an
        # async handler BLOCKED the event loop — every console poll hung
        # whenever a WhatsApp message arrived. Offload to a worker thread.
        reply = await asyncio.to_thread(route, customer, text, remote)
    except Exception as e:
        print(f"[err] routing failed, graceful dumb mode: {e}", flush=True)
        reply = ("Thanks for your message! Our assistant hiccupped — a human "
                 "will follow up here shortly.")
    if reply:
        try:
            await asyncio.to_thread(send_text, remote, reply)
            _remember(remote, reply, buyer_text=text)
            _mirror(remote, data.get("pushName") or None, "out", "bot", reply)
        except Exception as e:
            # delivery failure must not 500 the webhook (X2: log and move on;
            # in production a dead session alerts via the health digest)
            print(f"[send] FAILED to {remote}: {e}", flush=True)
    return {"ok": True, "replied": bool(reply)}
