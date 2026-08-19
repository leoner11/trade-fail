#!/usr/bin/env python3
"""A3-1 classifier eval — does the model actually triage correctly?

The flowchart routes on `intent` (A3-2), so a misclassification sends a
complaint to the RAG path or a custom-ODM ask to the pricing engine. This
harness pins that behaviour against labelled cases BEFORE the prompt is
wired into dify, so a bad model choice is caught here and not on a real
buyer's WhatsApp.

Cases 1-10 mirror the O5-1 acceptance scenarios. The rest are the edges
the flowchart calls out explicitly (rule 1 and rule 2 overrides).

Run: env -u PYTHONPATH calc/.venv/bin/python tests/test_classify.py
     MODEL=glm-4-flash (default) — set MODEL= to compare models.
"""
import json
import os
import re
import ssl
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# everything after the doc header (the first `---` rule) IS the system prompt
PROMPT = (ROOT / "dify" / "prompts" / "a3_classify.md").read_text().split("\n---\n", 1)[1].strip()

# .env is the appliance's config source; read it the same way the stack does.
env = {}
for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip()

BASE = env["GLM_BASE_URL"].rstrip("/")
KEY = env["GLM_API_KEY"]
MODEL = os.environ.get("MODEL", "glm-4-flash")

# This venv's python ships no CA bundle (no certifi, no pip, no uv on PATH),
# so urllib can't verify TLS out of the box even though curl can. Use the
# macOS system bundle. Never disable verification — we're sending an API key.
_CTX = ssl.create_default_context(
    cafile=next((p for p in ("/etc/ssl/cert.pem",) if os.path.exists(p)), None))

# (message, expected_intent, expected_language)
CASES = [
    # --- O5-1 acceptance scenarios ---
    ("Hi, what is the power output and fuel tank size of your DG-50?", "SPEC_Q", "en"),
    ("Halo, berapa kapasitas tangki bahan bakar untuk DG-50?", "SPEC_Q", "id"),
    ("What's the price for 100 units of the 30kVA silent genset?", "PRICE_Q", "en"),
    ("Please send me a formal quotation for 20 units DG-100, FOB Shanghai.", "PRICE_Q", "en"),
    ("We want 500 units with our own logo cast into the housing and a custom voltage.",
     "CUSTOM_ODM", "en"),
    ("Your generator exploded and destroyed my warehouse. This is unacceptable!",
     "COMPLAINT", "en"),
    ("I need 40% off or I walk. Your competitor gives me better.", "PRICE_Q", "en"),
    ("🔥🔥 CRYPTO SIGNALS 1000x GUARANTEED JOIN NOW t.me/scam", "SPAM", "en"),
    # --- flowchart edge rules ---
    ("Good morning!", "GREETING", "en"),
    ("Where is my container? It was due last week and tracking shows nothing.",
     "SHIPPING", "en"),
    # rule 1: price + custom -> CUSTOM_ODM (rules can't price custom)
    ("How much for 200 units if you redesign the control panel to our drawing?",
     "CUSTOM_ODM", "en"),
    # rule 2: complaint + question -> COMPLAINT (anger routes to human first)
    ("The unit you sent is faulty and leaking oil. Also what is the warranty period?",
     "COMPLAINT", "en"),
    # bilingual: CN buyer (the product is CN/EN by spec)
    ("你们的50kVA静音发电机组多少钱?要100台。", "PRICE_Q", "zh"),
    ("请问DG-100的额定电压是多少?", "SPEC_Q", "zh"),
]


def classify(msg: str) -> dict:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "system", "content": PROMPT},
                     {"role": "user", "content": msg}],
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(f"{BASE}/chat/completions", data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as r:
        raw = json.loads(r.read())["choices"][0]["message"]["content"]
    # small models like to wrap JSON in fences despite being told not to
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError(f"no JSON in response: {raw[:200]}")
    return json.loads(m.group(0))


def main() -> int:
    print(f"A3-1 classifier eval — model={MODEL}, {len(CASES)} cases\n")
    intent_ok = lang_ok = valid_json = 0
    failures = []
    for msg, want_intent, want_lang in CASES:
        try:
            got = classify(msg)
            valid_json += 1
        except Exception as e:
            failures.append((msg, f"PARSE FAIL: {e}"))
            print(f"  ✗ [parse] {msg[:52]}")
            continue
        gi, gl = got.get("intent"), (got.get("language") or "").lower()[:2]
        i_ok, l_ok = gi == want_intent, gl == want_lang
        intent_ok += i_ok
        lang_ok += l_ok
        mark = "✓" if (i_ok and l_ok) else "✗"
        print(f"  {mark} {msg[:50]:52s} intent={gi:<11}"
              f"{'' if i_ok else f'(want {want_intent}) '}"
              f"lang={gl}{'' if l_ok else f' (want {want_lang})'}"
              f" conf={got.get('confidence')}")
        if not (i_ok and l_ok):
            failures.append((msg, f"intent={gi} want={want_intent} lang={gl} want={want_lang}"))

    n = len(CASES)
    print(f"\n  valid JSON : {valid_json}/{n}")
    print(f"  intent     : {intent_ok}/{n}  ({100*intent_ok/n:.0f}%)")
    print(f"  language   : {lang_ok}/{n}  ({100*lang_ok/n:.0f}%)")
    # O2-2 sets the onboarding bar at >=90%; the same bar is fair for triage.
    ok = intent_ok / n >= 0.9 and valid_json == n
    print(f"\n  {'PASS' if ok else 'BELOW BAR'} — gate is 90% intent + 100% parseable JSON")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
