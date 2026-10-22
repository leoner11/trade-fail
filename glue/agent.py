#!/usr/bin/env python3
"""▣ glue agent — conversation core v2: ONE stateful tool-calling loop.

Replaces v1's classify→regex→RAG→compose cascade (docs/design-
conversation-core-v2.md). Organs stay untouched — every tool below is a
thin HTTP call to an existing service (spine S1, dify spec workflow,
calc, escalation store). This module is reached ONLY through
mock_responder.route() when CONVERSATION_CORE=v2; v1 stays frozen and
remains the default until the soak flips it.

Shape (per the design doc):

    msg → deterministic pre-guards (noise, complaint/anger, spam,
          pure-agreement offer fulfillment — NO LLM on these paths)
        → AGENT LOOP (CONVERSATION_MODEL, default glm-4.5-air; trap #48:
          premium tiers are unbillable on this endpoint)
    tools:  catalog_lookup(q)   S1 fuzzy: SKU / hyphenless / alias / kVA
            list_models()       S1 line + company facts
            kb_search(q)        dify spec workflow ([[KB_NOT_FOUND]] trap #34)
            price_quote(lines)  B1 validation → calc → S5 → (B4 PDF);
                                numbers ONLY from the calc result
            escalate(reason)    arms the SAME spine store as v1
        → deterministic post-guards (digits ⊆ tool facts, link guard;
          deterministic fallbacks — NEVER a wrong-template goodbye)
        → state save (spine agent_state column — restart-proof memory)

Shared machinery (HTTP helpers, guards, compose, escalation, B4, S2
vocabulary) is IMPORTED from mock_responder — single source, nothing
rewritten. v2 thread state lives in spine (S4 history + agent_state),
never in process RAM.

Run:  same uvicorn as v1 (mock_responder:app, glue dir, :8102) — this
      module is only imported lazily under the flag.
Env:  CONVERSATION_CORE=v2 (route seam) · CONVERSATION_MODEL (default
      glm-4.5-air) · everything else inherited from .env via mock_responder.
"""
import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))
import mock_responder as mr  # noqa: E402  (frozen v1 = canonical helpers)

HISTORY_N = 20          # resolved open question #3: last 20 messages
MAX_TOOL_ROUNDS = 4     # design doc: max 4 tool calls per message
KB_MARKER = "[[KB_NOT_FOUND]]"

AGENT_CORE = (mr.ROOT / "dify" / "prompts" /
              "agent_core_v2.md").read_text().split("\n---\n", 1)[1].strip()

_ESC_TAGS = {"SPEC_Q", "PRICE_Q", "PRICE_GAPS", "PRICE_INTERNAL",
             "CUSTOM_ODM", "COMPLAINT", "SHIPPING", "CALC_DOWN", "OTHER"}

_AUTONOMY_SUFFIX = {
    "assistant": ("\n\nAUTONOMY=assistant: you never touch money. The "
                  "price_quote tool is NOT available to you. For ANY pricing "
                  "ask, say the team is preparing a quotation and a "
                  "colleague will send the numbers here shortly — then call "
                  "escalate with tag PRICE_Q. Never state, hint at, or "
                  "approximate a price, discount or total."),
    "closer": ("\n\nAUTONOMY=closer: for an ambiguous off-script message you "
               "may ask ONE short clarifying question (committing to "
               "nothing) before escalating; if the clarification budget is "
               "already spent, escalate directly."),
}


def _put(url: str, payload: dict, timeout: int = 10) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 method="PUT",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=mr._CTX) as r:
        return json.loads(r.read() or b"{}")


# ----------------------------------------------------------------- state ----

def _lang_of(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text or "") else "en"


def _convo_id(remote: str) -> int | None:
    try:
        return mr._get(f"{mr.SPINE_URL}/conversations/by_jid/"
                       f"{urllib.parse.quote(remote)}",
                       timeout=5)["conversation_id"]
    except Exception:
        return None


def _state_load(remote: str) -> tuple[int | None, dict]:
    """(conversation_id, agent_state). Missing conversation -> (None, {});
    the buyer's line is mirrored to S4 BEFORE routing in the live path, so
    a missing row only happens on direct offline gate calls."""
    cid = _convo_id(remote)
    if cid is None:
        return None, {}
    try:
        state = mr._get(f"{mr.SPINE_URL}/conversations/{cid}/agent_state",
                        timeout=5).get("agent_state") or {}
        return cid, (state if isinstance(state, dict) else {})
    except Exception:
        return cid, {}


def _state_save(remote: str, cid: int | None, state: dict) -> None:
    try:
        if cid is None:
            cid = mr._post(f"{mr.SPINE_URL}/conversations/upsert",
                           {"wa_jid": remote}, timeout=5)["conversation_id"]
        _put(f"{mr.SPINE_URL}/conversations/{cid}/agent_state", state,
             timeout=5)
    except Exception as e:
        print(f"[v2-state] save skipped ({e})", flush=True)


def _history(remote: str, current_text: str) -> list[dict]:
    """Prior turns as chat messages. Live mode: last N S4 rows (the webhook
    mirrors the buyer's line BEFORE routing, so if the LAST row is exactly
    the current inbound it is not history). Offline gates run DRY_RUN=1,
    which does NOT mirror — there the _LOCAL_TURNS cache (below) supplies
    continuity; it is inert whenever spine has rows for the jid."""
    cid = _convo_id(remote)
    rows = []
    if cid is not None:
        try:
            rows = mr._get(f"{mr.SPINE_URL}/conversations/{cid}/messages",
                           timeout=5).get("items", [])
        except Exception:
            rows = []
    rows = [r for r in rows
            if r.get("sender_kind") in ("buyer", "bot", "human")]
    if rows and rows[-1].get("direction") == "in" \
            and (rows[-1].get("body") or "").strip() == current_text.strip():
        rows = rows[:-1]
    turns = []
    for r in rows[-HISTORY_N:]:
        body = (r["body"] or "").strip()
        if not body:
            continue
        if r["direction"] == "in":
            turns.append({"role": "user", "content": body})
        else:
            prefix = "[staff reply] " if r["sender_kind"] == "human" else ""
            turns.append({"role": "assistant", "content": prefix + body})
    if turns:
        return turns
    # DRY_RUN fallback: process-local transcript (no S4 mirror offline)
    cached = _LOCAL_TURNS.get(remote) or []
    return list(cached[-HISTORY_N:])


# Offline-gate continuity cache: filled ONLY with turns whose spine mirror
# was skipped (DRY_RUN). Never consulted when spine has rows — see
# _history. Process-local by design; live mode loses nothing.
_LOCAL_TURNS: dict[str, list[dict]] = {}


def _remember_local(remote: str, user_text: str, reply: str) -> None:
    if not reply:
        return
    turns = _LOCAL_TURNS.setdefault(remote, [])
    turns.append({"role": "user", "content": user_text})
    turns.append({"role": "assistant", "content": reply})
    del turns[:-2 * HISTORY_N]
    if len(_LOCAL_TURNS) > 2000:
        _LOCAL_TURNS.clear()


# ------------------------------------------------------------ pre-guards ----

# Complaint/anger (deterministic, PRE-model — house rule #2: the agent
# never sees these). Multilingual keyword net, generously sized: a false
# positive only costs a human handoff; a false negative costs the agent
# freelancing an angry thread — never acceptable.
_COMPLAINT_RES = [
    r"\b(exploded|caught fire|burned down|destroyed|damaged|broke|broken|"
    r"dead on arrival|stopped working|never arrived|not received)\b",
    r"\b(unacceptable|scam|fraud|cheat|rip[- ]?off|garbage service|"
    r"terrible|worst|useless|disgusted|furious|outraged)\b",
    r"\b(complain|complaint|refund|return my money|cancel my order|"
    r"lawyer|legal action|chargeback|bad review|report you)\b",
    r"\b(angry|very upset|so upset|disappointed)\b",
    r"(投诉|退货|退款|骗|垃圾|太差|差评|无法接受|不满意|报废|着火|爆炸|假货|起诉)",
    r"(kecewa|penipuan|uang kembali|komplain|rusak)",
]

# Obvious inbound marketing spam -> polite silence (conservative: only
# high-confidence patterns; anything else reaching the agent can still be
# escalated or answered by it).
_SPAM_RES = [
    r"https?://\S+\s*(buy|shop|order|join|promo|discount|casino|bet)",
    r"\b(join my (channel|group|team))\b",
    r"\b(forex|crypto|bitcoin)\s*(signal|profit|invest|trading)\b",
    r"\b(seo|marketing) services\b.*\b(contact|whatsapp|dm)\b",
    r"\bwork from home\b.*\b(earn|income|\$)\b",
]


def _pre_complaint(text: str) -> bool:
    return any(re.search(p, text, re.I) for p in _COMPLAINT_RES)


def _pre_spam(text: str) -> bool:
    return any(re.search(p, text, re.I) for p in _SPAM_RES)


def _neutral_holding(lang: str, text: str, remote: str) -> str:
    return (mr.compose("the message is outside what you can answer — do "
                       "NOT engage with its content, do NOT confirm, deny "
                       "or comment on any service, product or capability, "
                       "and do NOT react to the buyer's plans; write ONLY "
                       "a neutral holding line: this needs personal "
                       "attention from the team and a colleague will "
                       "follow up here shortly", lang, text, remote=remote)
            or mr.tt(lang, "human"))


def _complaint_path(customer: dict, text: str, remote: str, lang: str) -> str:
    reply = (mr.compose("an angry complaint — acknowledge once, apologize "
                        "once, say it is flagged URGENT and a human will "
                        "reply here shortly; no excuses, no defensiveness, "
                        "never promise a timeframe or hours",
                        lang, text, remote=remote)
             or mr.tt(lang, "complaint"))
    mr.escalate_to_chatwoot(remote, text, "COMPLAINT", lang, customer, reply,
                            "Deterministic pre-guard (v2): complaint/anger "
                            "detected before the agent — always-human list.\n")
    return reply


def _fulfill_offer(state: dict, customer: dict, text: str, remote: str,
                   lang: str) -> str | None:
    """Pure agreement to a pending offer — deterministic, NO loop (resolved
    open question #1). Mirrors v1's post-#15 semantics with the fallback
    ladder: catalog card -> offer facts verbatim -> honest escalate."""
    offer = state.get("offer_pending") or {}
    if offer.get("kind") == "pdf":
        print(f"[v2] buyer accepted PDF offer ({offer.get('quote_id')})",
              flush=True)
        threading.Thread(
            target=mr.b4_deliver,
            args=(remote, offer.get("customer") or dict(customer),
                  offer.get("quote") or {}, offer.get("quote_id") or ""),
            daemon=True).start()
        state.pop("offer_pending", None)
        return mr.tt(lang, "formal_offer")
    facts = [f for f in offer.get("facts", []) if f]
    print(f"[v2] fulfilling pending offer about {offer.get('about')}",
          flush=True)
    reply = mr.compose(
        "in your previous message you offered more information and the "
        "buyer just accepted — DELIVER IT NOW from the facts: concrete "
        "details, no hedging, no handoff, no 'let me check'; end by "
        "inviting the next concrete step (quantity for pricing, or their "
        "application)", lang, text, facts=facts + mr._company_line(),
        remote=remote, numbers="exact")
    state.pop("offer_pending", None)
    if reply:
        return reply
    # deterministic fallback: last-discussed SKU card, else facts verbatim —
    # NEVER a closing/goodbye template mid-sale (live 2026-08-26 22:53).
    sku = state.get("last_sku")
    if sku:
        try:
            return _card_text(mr._get(f"{mr.SPINE_URL}/catalog/{sku}"))
        except Exception:
            pass
    if facts:
        return "\n".join(f"• {f}" for f in facts)
    holding = _neutral_holding(lang, text, remote)
    mr.escalate_to_chatwoot(remote, text, "OTHER", lang, customer, holding,
                            "Offer fulfillment had no facts to deliver — "
                            "honest handoff instead of a guess.\n")
    return holding


def _card_facts(item: dict) -> list[str]:
    facts = [f"{item['name']} ({item['sku']})"] + [
        f"{k}: {v}" for k, v in item["specs"].items()]
    if item.get("moq"):
        facts.append(f"MOQ {item['moq']}")
    if item.get("certs"):
        facts.append(f"certifications: {item['certs']}")
    return facts


def _card_text(item: dict) -> str:
    specs = "; ".join(f"{k}: {v}" for k, v in item["specs"].items())
    moq = f" MOQ {item['moq']}." if item.get("moq") else ""
    certs = f" Certs: {item['certs']}." if item.get("certs") else ""
    return (f"{item['name']} ({item['sku']}): {specs}.{moq}{certs} "
            f"Ask me for a price any time.")


# ----------------------------------------------------------------- tools ----
# Each executor gets (state, ctx, args) and may mutate state — the
# deterministic post-tool layer (offer arming, last-SKU memory).

def _t_catalog_lookup(state, ctx, args):
    q = str(args.get("q") or "").strip() or ctx["text"]
    sku = mr._sku_token(q) or mr._alias_sku(q)
    item = None
    if sku:
        try:
            item = mr._get(f"{mr.SPINE_URL}/catalog/{sku}")
        except Exception:
            item = None
    if item is None:
        # last resort: S1 name/sku substring search (covers "30kva" etc.);
        # only an UNAMBIGUOUS single hit may answer — else not_found
        try:
            rows = mr._get(
                f"{mr.SPINE_URL}/catalog?q={urllib.parse.quote(q)}"
            ).get("items", [])
            if len(rows) == 1:
                item = mr._get(f"{mr.SPINE_URL}/catalog/{rows[0]['sku']}")
        except Exception:
            item = None
    if item is None:
        try:
            line = [r["sku"] for r in mr._get(
                f"{mr.SPINE_URL}/catalog").get("items", [])]
        except Exception:
            line = list(mr.MATERIALS)
        # Leonard's call (session #16): unknown product asks get the
        # NATURAL grounded-negative + pivot answer (real sales tone), and
        # the ask is STILL armed to staff in the background as a demand
        # signal — same pattern as v1's out-of-catalog availability probe.
        try:
            mr.escalate_to_chatwoot(
                ctx["remote"], ctx["text"], "SPEC_Q", ctx["lang"],
                ctx["customer"],
                "(buyer answered with a grounded 'not our line' + "
                "product-line pivot)",
                f"[v2 agent] Out-of-catalog product ask: \"{q[:160]}\" — "
                "demand signal for staff.\n")
        except Exception:
            pass
        return {"status": "not_found", "q": q[:120], "line_skus": line,
                "staff_notified": True,
                "hint": "the team was notified in the background — answer "
                        "the buyer NATURALLY: say plainly it is not your "
                        "line, then pivot to what you do make; do NOT "
                        "promise to check, do NOT mention any follow-up, "
                        "and never invent specs for the asked item"}
    facts = _card_facts(item)
    state["last_sku"] = item["sku"]
    state["offer_pending"] = {"about": item["sku"], "facts": facts}
    return {"status": "found", "sku": item["sku"], "name": item["name"],
            "specs": item.get("specs") or {}, "moq": item.get("moq"),
            "certs": item.get("certs"), "facts": facts}


def _t_list_models(state, ctx, args):
    facts = mr._company_line()
    state["offer_pending"] = {"about": "the product line", "facts": facts}
    return {"status": "ok", "facts": facts}


def _t_kb_search(state, ctx, args):
    q = str(args.get("q") or "").strip() or ctx["text"]
    ans = mr.spec_answer(q)
    if not ans:
        try:
            mr._post(f"{mr.SPINE_URL}/events", {
                "kind": "kb_miss",
                "detail_json": json.dumps({"q": q[:200],
                                           "remote": ctx["remote"]})},
                timeout=5)
        except Exception:
            pass
        return {"status": "miss", "q": q[:120],
                "hint": "knowledge base has no answer — escalate so a human "
                        "answers honestly; do not promise to check yourself"}
    state["offer_pending"] = {"about": "the topic just discussed",
                              "facts": [ans]}
    return {"status": "found", "answer": ans}


def _t_price_quote(state, ctx, args):
    lang, text, remote = ctx["lang"], ctx["text"], ctx["remote"]
    customer = ctx["customer"]
    lines_in = args.get("lines") or []
    formal = bool(args.get("formal"))
    clean = []
    for ln in lines_in:
        if not isinstance(ln, dict):
            continue
        mat = str(ln.get("material") or "").strip()
        if not mat or mat not in mr.MATERIALS:
            return {"status": "need", "missing": "material",
                    "known_materials": mr.MATERIALS,
                    "hint": "material not in the pricing vocabulary — if "
                            "the buyer's product is genuinely outside this "
                            "list, call escalate (tailored quote)"}
        try:
            qty = int(ln.get("qty"))
        except (TypeError, ValueError):
            qty = 0
        if qty < 1:
            return {"status": "need", "missing": "quantity",
                    "hint": "ask the buyer how many units they need"}
        size = str(ln.get("size") or "STD").strip().upper() or "STD"
        if size not in mr.SIZES:
            return {"status": "need", "missing": "size",
                    "known_sizes": mr.SIZES}
        procs = [p for p in (ln.get("processes") or [])
                 if isinstance(p, str) and p in mr.PROCESSES]
        clean.append({"material": mat, "size": size, "qty": qty,
                      "processes": procs})
    if not clean:
        return {"status": "need", "missing": "lines",
                "hint": "what product and how many units?"}
    # S2 v3 structural no-leak: internal_only materials never reach calc
    hidden = mr.hidden_materials(clean)
    if hidden:
        mats = ", ".join(hidden)
        holding = (mr.compose(
            "the buyer asked about items that are quoted by the team only — "
            "say their request was passed to a colleague who will confirm "
            "the numbers here shortly; do NOT give any price or number",
            lang, text, remote=remote) or mr.tt(lang, "internal_price"))
        return {"status": "escalate", "tag": "PRICE_INTERNAL",
                "reason": f"price_visibility internal_only: {mats}",
                "holding_reply": holding}
    try:
        res = mr._post(f"{mr.CALC_URL}/quote", {
            "customer_id": customer.get("customer_id"),
            "customer_tier": customer.get("tier") or "new",
            "currency": mr.RULES.get("currency", "USD"),
            "lines": clean}, timeout=60)
    except Exception as e:
        print(f"[v2-quote] calc unreachable: {e}", flush=True)
        return {"status": "escalate", "tag": "CALC_DOWN",
                "reason": f"calc :8100 unreachable: {e}",
                "holding_reply": mr.tt(lang, "calc_down")}
    if res.get("status") != "OK":
        gaps = "; ".join(res.get("gaps", []))
        print(f"[v2-quote] escalate, gaps={gaps}", flush=True)
        holding = (mr.compose(
            "this request falls outside standard pricing rules so a human "
            "must calculate it manually — reassure, promise a person will "
            "reply with numbers; do NOT give any price or timeline",
            lang, text, remote=remote) or mr.tt(lang, "escalate_gaps"))
        return {"status": "escalate", "tag": "PRICE_GAPS",
                "reason": f"pricing-rules gap: {gaps}",
                "holding_reply": holding}
    q = res["quote"]
    saved = None
    try:
        saved = mr._post(f"{mr.SPINE_URL}/quotes", {
            "customer_id": customer.get("customer_id"),
            "request_json": {"lines": clean, "formal": formal,
                             "source": "v2-agent"},
            "result_json": res, "total": q["total"],
            "currency": q["currency"]})
        mr._post(f"{mr.SPINE_URL}/quotes/{saved['quote_id']}/status",
                 {"status": "sent"}, timeout=10)
        print(f"[v2-quote] {saved['quote_id']} saved+sent", flush=True)
    except Exception as e:
        print(f"[v2-quote] S5 save failed (price already computed): {e}",
              flush=True)
    if formal and saved is not None:
        threading.Thread(target=mr.b4_deliver,
                         args=(remote, customer, q, saved["quote_id"]),
                         daemon=True).start()
    bullets = [f"• {l['description']} ×{l['qty']} — {q['currency']} "
               f"{l['line_total']:,.2f}" for l in q["lines"]]
    tail = mr.tt(lang, "formal_offer") if formal else mr.tt(lang, "pdf_offer")
    block = mr.tt(lang, "price_ok").format(
        lines="\n".join(bullets), currency=q["currency"], total=q["total"],
        discount=q["discount_pct"], valid_until=q["valid_until"])
    facts = bullets + [f"Total: {q['currency']} {q['total']:,.2f}",
                       f"Valid until {q['valid_until']}",
                       f"{q['discount_pct']:.0f}% quantity discount included"]
    if saved is not None:
        state["offer_pending"] = {
            "about": f"{saved['quote_id']} formal pdf", "facts": facts + [tail],
            "kind": "pdf", "quote": q, "quote_id": saved["quote_id"],
            "customer": dict(customer)}
    state["last_sku"] = clean[0]["material"]
    return {"status": "ok", "quote_block": block, "tail": tail, "facts": facts,
            "hint": "deliver the quote_block faithfully: every line item, "
                    "the total, the discount note, the validity date, then "
                    "the tail offer line — adjust connective wording only"}


def _t_escalate(state, ctx, args):
    reason = str(args.get("reason") or "").strip()[:300] or "agent escalation"
    tag = str(args.get("tag") or "OTHER").strip().upper()
    if tag not in _ESC_TAGS:
        tag = "OTHER"
    holding = _neutral_holding(ctx["lang"], ctx["text"], ctx["remote"])
    mr.escalate_to_chatwoot(ctx["remote"], ctx["text"], tag, ctx["lang"],
                            ctx["customer"], holding, f"[v2 agent] {reason}\n")
    state.pop("offer_pending", None)
    return {"status": "armed", "holding_reply": holding,
            "hint": "escalation is armed — your final reply IS the "
                    "holding_reply above, verbatim; do not add facts, "
                    "opinions or promises"}


TOOLS = [
    {"type": "function", "function": {
        "name": "catalog_lookup",
        "description": ("Look up ONE product in the company catalog by SKU "
                        "(exact or hyphenless like 'dg 30'), kVA rating, "
                        "name fragment or natural alias. Returns the full "
                        "spec card, or not_found."),
        "parameters": {"type": "object", "properties": {
            "q": {"type": "string",
                  "description": "what the buyer mentioned, verbatim"}},
            "required": ["q"]}}},
    {"type": "function", "function": {
        "name": "list_models",
        "description": ("The company's full product line with model names "
                        "and SKUs. Use for 'what do you do/sell/make', "
                        "'what models are there', industry/company "
                        "questions."),
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "kb_search",
        "description": ("Search the client knowledge base for product "
                        "knowledge: warranty policy, HS codes, how a "
                        "feature works, anything not in the catalog card. "
                        "Returns status=miss when the KB has no answer."),
        "parameters": {"type": "object", "properties": {
            "q": {"type": "string",
                  "description": "the buyer's question, verbatim"}},
            "required": ["q"]}}},
    {"type": "function", "function": {
        "name": "price_quote",
        "description": ("Compute a price quotation. ALL money numbers come "
                        "from this tool — never compute or estimate "
                        "anything yourself. Materials/sizes/processes must "
                        "come from the tool's own vocabulary answers."),
        "parameters": {"type": "object", "properties": {
            "lines": {"type": "array", "items": {"type": "object",
                "properties": {
                    "material": {"type": "string",
                                 "description": "exact catalog material name"},
                    "size": {"type": "string",
                             "description": "configuration size, default STD"},
                    "qty": {"type": "integer", "minimum": 1},
                    "processes": {"type": "array", "items": {
                        "type": "string"}}},
                "required": ["material", "qty"]}},
            "formal": {"type": "boolean", "description": (
                "true ONLY when the buyer explicitly asks for an official/"
                "formal/written/PDF quotation or proforma invoice")}},
            "required": ["lines"]}}},
    {"type": "function", "function": {
        "name": "escalate",
        "description": ("Hand this conversation to a human colleague (arms "
                        "the staff thread). Use for: off-script business "
                        "(payment terms, legal, shipping disputes, custom/"
                        "ODM engineering, discount negotiation), knowledge-"
                        "base misses, or anything you cannot ground in "
                        "tools. Returns the neutral holding reply to send."),
        "parameters": {"type": "object", "properties": {
            "reason": {"type": "string",
                       "description": "short staff-facing reason"},
            "tag": {"type": "string", "enum": sorted(_ESC_TAGS)}},
            "required": ["reason"]}}},
]

_TOOL_FN = {"catalog_lookup": _t_catalog_lookup, "list_models": _t_list_models,
            "kb_search": _t_kb_search, "price_quote": _t_price_quote,
            "escalate": _t_escalate}


# ------------------------------------------------------------ agent loop ----

def _chat(messages: list[dict], tools: list[dict] | None) -> dict:
    body = {"model": mr.cfg("CONVERSATION_MODEL", "glm-4.5-air"),
            "messages": messages, "temperature": 0.3}
    if tools:
        body["tools"] = tools
    req = urllib.request.Request(
        f"{mr.cfg('GLM_BASE_URL').rstrip('/')}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {mr.cfg('GLM_API_KEY')}"})
    with urllib.request.urlopen(req, timeout=120, context=mr._CTX) as r:
        return json.loads(r.read())["choices"][0]["message"]


def _run_agent(state: dict, ctx: dict) -> tuple[str, dict, list[dict]]:
    """One agent turn -> (reply, trace, messages). trace carries guard
    inputs: every tool's JSON, escalate status, forced-escalation demand,
    LLM call count."""
    autonomy = mr.AUTONOMY
    tools = [t for t in TOOLS
             if not (autonomy == "assistant" and t["function"]["name"]
                     == "price_quote")]
    sys_lines = [AGENT_CORE, "---", mr.VOICE_PROMPT]
    if autonomy in _AUTONOMY_SUFFIX:
        sys_lines.append(_AUTONOMY_SUFFIX[autonomy])
    if autonomy == "closer":
        sys_lines.append("Clarification budget used: "
                         f"{'yes' if state.get('clarified') else 'no'}.")
    # only assert the language when the deterministic regex knows it;
    # anything else (id, es, ...) — the model mirrors it itself (rule 10)
    if ctx["lang"] in ("zh",):
        sys_lines.append("Current buyer language for this reply: "
                         f"{mr.LANG_NAME[ctx['lang']]}.")
    else:
        sys_lines.append("Current buyer language for this reply: the "
                         "language of the buyer's LATEST message — detect "
                         "and mirror it yourself (it may not be English; "
                         "IGNORE the languages of older messages in the "
                         "thread history).")
    trace = {"reply": "", "tool_outputs": [], "escalated": False,
             "holding": "", "forced": None, "calls": 0, "tools_used": [],
             "history_text": ""}
    messages = [{"role": "system", "content": "\n\n".join(sys_lines)}]
    history = _history(ctx["remote"], ctx["text"])
    # numbers already stated in this thread (buyer's own words, our
    # previously-guarded replies, staff text) — relaying them is never
    # invention; only NEW numbers must come from this message's tools
    trace["history_text"] = "\n".join(t["content"] for t in history)
    messages += history
    messages.append({"role": "user", "content": ctx["text"]})
    for round_i in range(MAX_TOOL_ROUNDS + 1):
        msg = _chat(messages, tools if round_i < MAX_TOOL_ROUNDS else None)
        trace["calls"] += 1
        calls = msg.get("tool_calls") or []
        if not calls:
            trace["reply"] = (msg.get("content") or "").strip()
            return trace["reply"], trace, messages
        if round_i == MAX_TOOL_ROUNDS:
            break  # tool budget exhausted -> deterministic fallback upstream
        messages.append({"role": "assistant",
                         "content": msg.get("content") or "",
                         "tool_calls": calls})
        for call in calls:
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
                if not isinstance(args, dict):
                    args = {}
            except Exception:
                args = {}
            if name not in _TOOL_FN or (name == "price_quote"
                                        and autonomy == "assistant"):
                out = {"status": "error",
                       "hint": f"tool {name} is not available"}
            else:
                try:
                    out = _TOOL_FN[name](state, ctx, args)
                except Exception as e:
                    out = {"status": "error", "error": str(e)[:200]}
            trace["tools_used"].append(name)
            trace["tool_outputs"].append(out)
            if name == "escalate" and out.get("status") == "armed":
                trace["escalated"] = True
                trace["holding"] = out["holding_reply"]
            if out.get("status") == "escalate" and not trace["forced"]:
                trace["forced"] = (out["tag"], out["holding_reply"],
                                   out["reason"])
            messages.append({"role": "tool", "tool_call_id": call.get("id"),
                             "content": json.dumps(out, ensure_ascii=False)})
        if trace["escalated"]:
            break  # escalate is terminal: holding reply is final
    return trace["reply"], trace, messages


# --------------------------------------------------------- post-guards ------

def _guard_ok(reply: str, allowed: set, exact: set | None) -> bool:
    if not reply:
        return False
    have = mr._nums(reply)
    if exact is not None:
        if have != exact:
            return False
    elif not have <= allowed:
        return False
    return not mr._LINKY.search(reply)


def _deterministic_fallback(state: dict, ctx: dict, trace: dict) -> str:
    """Guaranteed-safe reply built ONLY from tool facts (design doc rule 1:
    rejected generations fall back to DETERMINISTIC tool output — never a
    wrong-template goodbye)."""
    quote = next((o for o in trace["tool_outputs"]
                  if o.get("status") == "ok" and o.get("quote_block")), None)
    if quote:
        return quote["quote_block"]
    found = [o for o in trace["tool_outputs"] if o.get("status") == "found"
             and o.get("sku")]
    if found:
        try:
            return _card_text(
                mr._get(f"{mr.SPINE_URL}/catalog/{found[-1]['sku']}"))
        except Exception:
            pass
    kb = [o for o in trace["tool_outputs"]
          if o.get("status") == "found" and o.get("answer")]
    if kb:
        return kb[-1]["answer"]
    line = [o for o in trace["tool_outputs"]
            if o.get("status") == "ok" and o.get("facts")]
    if line:
        return "\n".join(f"• {f}" for f in line[-1]["facts"][:8])
    # nothing grounded at all: honest handoff, never a fabricated answer
    holding = _neutral_holding(ctx["lang"], ctx["text"], ctx["remote"])
    if not trace["escalated"]:
        mr.escalate_to_chatwoot(ctx["remote"], ctx["text"], "OTHER",
                                ctx["lang"], ctx["customer"], holding,
                                "[v2] guard fallback with no grounded "
                                "facts — honest handoff.\n")
    return holding


def _last_inbound_id(remote: str) -> int | None:
    try:
        conv = mr._get(f"{mr.SPINE_URL}/conversations/by_jid/{remote}")
        cid2 = conv.get("conversation_id")
        if not cid2:
            return None
        msgs = mr._get(f"{mr.SPINE_URL}/conversations/{cid2}/messages"
                       f"?limit=5").get("items", [])
        for m in reversed(msgs):
            if m.get("direction") == "in":
                return m.get("id")
    except Exception as e:
        print(f"[k] message lookup failed: {e}", flush=True)
    return None


def _capture_facts(customer: dict, cid: int | None, remote: str,
                   text: str) -> None:
    """⊞ Customer Knowledge memory write. Extract-not-infer: GLM may only
    copy durable facts the buyer explicitly stated; spine enforces the
    citation (source_message_id) and dedupes. Failures are swallowed —
    capture must never break the reply path."""
    cus_id = customer.get("customer_id")
    if not cid or not cus_id or not text:
        return
    try:
        known = [f.get("fact") for f in mr._get(
            f"{mr.SPINE_URL}/customers/{cus_id}/facts").get("items", [])]
    except Exception as e:
        print(f"[k] facts fetch failed: {e}", flush=True)
        return
    try:
        out = mr.glm(
            "You extract DURABLE customer facts for a CRM memory. From the "
            "buyer message ONLY, list facts the buyer explicitly stated "
            "(preferences, constraints, payment/shipment terms, company "
            "details). Copy, never infer; skip small talk. Max 3, each "
            '<200 chars. Output JSON: {"facts": ["..."]}.',
            json.dumps({"buyer_message": text, "already_known": known},
                       ensure_ascii=False))
    except Exception as e:
        print(f"[k] fact extraction unavailable: {e}", flush=True)
        return
    msg_id = _last_inbound_id(remote)
    if not msg_id:
        print("[k] no inbound message id — facts skipped", flush=True)
        return
    added = 0
    for fact in (out.get("facts") or [])[:3]:
        fact = (fact or "").strip()
        if not fact:
            continue
        try:
            r = mr._post(f"{mr.SPINE_URL}/customers/{cus_id}/facts",
                         {"fact": fact, "source_message_id": msg_id})
            added += 0 if r.get("duplicate") else 1
        except Exception as e:
            print(f"[k] fact write failed: {e}", flush=True)
    if added:
        print(f"[k] +{added} customer fact(s)", flush=True)


def _handle(customer: dict, text: str, remote: str) -> str | None:
    """v2 route body: pre-guards → loop → post-guards → state save."""
    stripped = text.strip()
    # noise gate (v1 logic verbatim): keyboard mash never reaches anyone
    if len(stripped) >= 4:
        alpha = sum(ch.isalpha() for ch in stripped)
        if alpha / len(stripped) < 0.5:
            print("[v2] obvious noise -> polite silence", flush=True)
            return None
    lang = _lang_of(stripped)
    cid, state = _state_load(remote)
    ctx = {"customer": customer, "text": stripped, "remote": remote,
           "lang": lang}

    if _pre_complaint(stripped):
        print("[v2] complaint pre-guard -> always-human path", flush=True)
        return _complaint_path(customer, stripped, remote, lang)
    if _pre_spam(stripped):
        print("[v2] spam pre-guard -> silence", flush=True)
        return None

    # pure agreement to OUR pending offer: deterministic fulfillment
    if mr._is_agreement(stripped):
        if state.get("offer_pending"):
            reply = _fulfill_offer(state, customer, stripped, remote, lang)
            _state_save(remote, cid, state)
            return reply
        if state.get("had_interaction"):
            reply = (mr.compose(
                "the buyer sent a short agreement/acknowledgment mid-thread "
                "with no open question on your side — acknowledge warmly in "
                "one line and invite their next need; do NOT escalate or "
                "hand off", lang, stripped, facts=mr._company_line(),
                remote=remote) or mr.tt(lang, "welcome"))
            _state_save(remote, cid, state)
            return reply
        # cold agreement, no history: let the agent respond naturally

    # a substantive message invalidates any stale offer; tools re-arm below
    state.pop("offer_pending", None)
    state["had_interaction"] = True

    t0 = time.time()
    try:
        reply, trace, messages = _run_agent(state, ctx)
    except Exception as e:
        print(f"[v2] agent loop failed: {e}", flush=True)
        holding = mr.tt(lang, "human")
        mr.escalate_to_chatwoot(remote, stripped, "OTHER", lang, customer,
                                holding, f"[v2] agent loop error: {e}\n")
        state.pop("offer_pending", None)
        _state_save(remote, cid, state)
        return holding

    # tool-forced escalation enforcement (calc gaps / internal-only / down)
    if trace["forced"] and not trace["escalated"]:
        tag, holding, reason = trace["forced"]
        mr.escalate_to_chatwoot(remote, stripped, tag, lang, customer,
                                holding, f"[v2 enforced] {reason}\n")
        trace["escalated"] = True
        trace["holding"] = holding
    if trace["escalated"]:
        reply = trace["holding"]  # the sacred path is deterministic verbatim
        state.pop("offer_pending", None)
    else:
        # grounding guards: digits must come from tool facts, the buyer's
        # own words, or numbers already established (guarded) in-thread
        tool_text = "\n".join(json.dumps(o, ensure_ascii=False)
                              for o in trace["tool_outputs"])
        allowed = (mr._nums(tool_text) | mr._nums(stripped)
                   | mr._nums(trace.get("history_text") or ""))
        quote = next((o for o in trace["tool_outputs"]
                      if o.get("status") == "ok" and o.get("quote_block")),
                     None)
        exact = mr._nums("\n".join(quote["facts"])) if quote else None
        if not _guard_ok(reply, allowed, exact):
            print(f"[v2] guard rejected agent reply\n[v2] was: "
                  f"{(reply or '')[:200]}", flush=True)
            # one repair round with the correction spelled out, then the
            # deterministic fallback — never a wrong-template goodbye
            try:
                messages = messages + [
                    {"role": "assistant", "content": reply or "(empty)"},
                    {"role": "system", "content": (
                        "Your previous reply violated the grounding rules (a "
                        "number not present in the tool facts, a forbidden "
                        "link/file mention, or a dropped contractual "
                        "figure). Rewrite it using ONLY the facts from the "
                        "tool results above. Copy every number "
                        "digit-for-digit. No links, no attachments. Output "
                        "the message text only.")}]
                msg = _chat(messages, None)
                reply2 = (msg.get("content") or "").strip()
                if _guard_ok(reply2, allowed, exact):
                    reply = reply2
                else:
                    reply = _deterministic_fallback(state, ctx, trace)
            except Exception as e:
                print(f"[v2] repair failed ({e}) -> deterministic fallback",
                      flush=True)
                reply = _deterministic_fallback(state, ctx, trace)

    # closer clarify-budget bookkeeping (soft approximation of v1 semantics)
    if mr.AUTONOMY == "closer":
        if trace.get("tools_used"):
            state.pop("clarified", None)
        elif reply.rstrip().endswith("?"):
            state["clarified"] = True

    state["lang"] = lang
    _state_save(remote, cid, state)
    # ⊞ Customer Knowledge: guarded memory capture — background thread,
    # never blocks or breaks the reply path.
    if mr.KNOWLEDGE_CAPTURE and not mr.DRY_RUN:
        try:
            threading.Thread(target=_capture_facts, daemon=True,
                             args=(customer, cid, remote, stripped)).start()
        except Exception as e:
            print(f"[v2] fact capture skipped: {e}", flush=True)
    print(f"[v2] done in {time.time()-t0:.1f}s calls={trace.get('calls')} "
          f"tools={trace.get('tools_used')} "
          f"escalated={trace.get('escalated')}", flush=True)
    return reply or _deterministic_fallback(state, ctx, trace)


def handle(customer: dict, text: str, remote: str = "") -> str | None:
    """route() seam entry (mirror of v1 route's signature)."""
    reply = _handle(customer, text, remote or "")
    if reply:
        # offline-gate continuity (DRY_RUN has no S4 mirror; live mode's
        # spine rows always win in _history, so this cache is inert there)
        _remember_local(remote or "", text.strip(), reply)
    return reply
