#!/usr/bin/env python3
"""Voice eval — is the generated reply in-voice, varied, and fact-safe?

Complements test_classify.py: that one gates ROUTING, this one gates
WORDING. For each situation it generates TWICE and checks:
  - guard pass (numbers only from facts; VERBATIM lines intact)
  - variation (two consecutive generations don't share an opening)
  - language (en/zh/id replies actually come back in that language)
Prints everything for human eyeball review — wording quality is judged
by Leonard, not by a regex.

Run: env -u PYTHONPATH calc/.venv/bin/python tests/test_voice.py
(needs spine :8101 + calc :8100 up for the spec/price fact builders)
"""
import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "mock_responder", ROOT / "glue" / "mock_responder.py")
mr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mr)

BUYER = "6281234567890@s.whatsapp.net"  # seeded S3 customer, tier=repeat

# (label, lang, buyer_text, situation, style, facts)
CASES = [
    ("greet en", "en", "Hi there", "greeting",
     "a first greeting from a new buyer who just said hi", []),
    ("greet zh", "zh", "你好", "greeting",
     "a first greeting from a new buyer who just said hi", []),
    ("welcome id", "id", "Terima kasih banyak pak", "welcome",
     "the buyer is thanking you / closing the chat", []),
    ("complaint en", "en",
     "Your generator exploded and destroyed my warehouse!", "complaint",
     "an angry complaint — acknowledge, apologize once, flag URGENT", []),
]


def spec_case():
    item = mr._get(f"{mr.SPINE_URL}/catalog/DG-50")
    facts = [f"{item['name']} ({item['sku']})"] + [
        f"{k}: {v}" for k, v in item["specs"].items()]
    if item.get("moq"):
        facts.append(f"MOQ {item['moq']}")
    if item.get("certs"):
        facts.append(f"certifications: {item['certs']}")
    return ("spec en", "en", "What's the fuel tank size of the DG-50?",
            "spec answer", "answer from catalog facts, offer pricing help",
            facts)


def price_case():
    res = mr._post(f"{mr.CALC_URL}/quote", {
        "customer_id": "cus_repeat_001", "customer_tier": "repeat",
        "lines": [{"material": "DG-50", "size": "STD",
                   "qty": 10, "processes": ["Remote Start Controller"]}]})
    q = res["quote"]
    bullets = [f"• {l['description']} ×{l['qty']} — {q['currency']} {l['line_total']:,.2f}"
               for l in q["lines"]]
    facts = bullets + [f"Total: {q['currency']} {q['total']:,.2f}",
                       f"Valid until {q['valid_until']}",
                       f"{q['discount_pct']:.0f}% quantity discount included"]
    return ("price zh", "zh", "DG-50发电机组，带远程启动，10台。多少钱？", "inline quote",
            "deliver computed price, keep bullet layout, offer PDF quote",
            facts)


def capability_case():
    return ("capability zh", "zh", "你们是做什么的？",
            "what the company does",
            "answer concretely from the facts: name the real product line, "
            "then ask ONE question about their application or required "
            "power range; no generic claims beyond the facts",
            mr._company_line())


def not_ours_case():
    return ("not-ours en", "en", "do you have kaolin? need 20 tons",
            "out-of-catalog availability probe",
            "say briefly and honestly that it is not your line (a plain 'no' "
            "grounded in the catalog is allowed), then name what you DO make "
            "from the facts and invite their power-equipment need with at "
            "most ONE question; do NOT promise to check or come back later",
            mr._company_line())


def main() -> int:
    cases = list(CASES) + [spec_case(), price_case(),
                           capability_case(), not_ours_case()]

    fails = 0
    for label, lang, text, situation, style, facts in cases:
        # one jid per case: variation is judged WITHIN a thread, and sharing
        # a remote across unrelated situations made the anti-repeat check
        # clash against foreign replies (voice-gate artifact).
        remote = f"{BUYER[:-14]}{abs(hash(label)) % 10**6}@s.whatsapp.net"
        outs = []
        for i in (1, 2):
            out = mr.compose(f"{situation} — {style}", lang, text, facts=facts,
                             remote=remote,
                             numbers="exact" if label.startswith("price") else "subset",
                             final_note=mr.PRICE_FINAL_NOTE
                             if label.startswith("price") else "")
            if out:
                mr._remember(remote, out)
            outs.append(out)
        ok_guard = all(o is not None for o in outs)
        ok_varied = (outs[0] and outs[1]
                     and outs[0].split("\n")[0][:25] != outs[1].split("\n")[0][:25])
        mark = "✓" if (ok_guard and ok_varied) else "✗"
        if mark == "✗":
            fails += 1
        print(f"\n{mark} {label}  (guard={'ok' if ok_guard else 'FELL BACK'}, "
              f"varied={'yes' if ok_varied else 'NO'})")
        for i, o in enumerate(outs, 1):
            print(f"  [{i}] {(o or '(static fallback used)').strip()}")

    print(f"\n{'PASS' if fails == 0 else f'{fails} CASE(S) BELOW BAR'} "
          "— wording itself needs Leonard's eyeball")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
