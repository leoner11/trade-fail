# Eval Log — A3-1 Triage Classifier

Date: 2026-08-24
Harness: `tests/test_classify.py` (14 labelled cases; 10 mirror O5-1 acceptance scenarios + the two flowchart override edges)
Model: `glm-4-flash` (free tier; 4.x paid models unavailable on this key)
Prompt under test: `dify/prompts/a3_classify.md` (used verbatim as system prompt)
Gate (same bar as O2-2): **≥90% intent accuracy AND 100% parseable JSON**

## Result — PASS on first execution, no prompt changes needed

| Metric | Score | Gate |
|---|---|---|
| valid JSON | 14/14 | 100% ✅ |
| intent | 14/14 (100%) | ≥90% ✅ |
| language | 14/14 (100%) | — |

Both override rules held:
- Rule 1 (price+custom → CUSTOM_ODM): "How much for 200 units if you redesign the control panel to our drawing?" → CUSTOM_ODM ✅
- Rule 2 (any anger → COMPLAINT even with a question): "The unit you sent is faulty… also what is the warranty period?" → COMPLAINT ✅

Secondary signals behaved correctly too (not gated but part of the schema):
- COMPLAINT case → `urgency=high`, `sentiment=negative`
- Discount ultimatum ("40% off or I walk") → `urgency=high`, `sentiment=negative`, intent stayed PRICE_Q (correct — within-cap discount is a price path; beyond-cap is enforced downstream by calc authority caps, not by the classifier)
- Container-chase → `urgency=high` (rule 4)

## Raw model outputs

```
{"msg": "Hi, what is the power output and fuel tank size of your DG-50?", "want": "SPEC_Q/en", "got": {"language": "en", "intent": "SPEC_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "Halo, berapa kapasitas tangki bahan bakar untuk DG-50?", "want": "SPEC_Q/id", "got": {"language": "id", "intent": "SPEC_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "What's the price for 100 units of the 30kVA silent genset?", "want": "PRICE_Q/en", "got": {"language": "en", "intent": "PRICE_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "Please send me a formal quotation for 20 units DG-100, FOB Shanghai.", "want": "PRICE_Q/en", "got": {"language": "en", "intent": "PRICE_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "We want 500 units with our own logo cast into the housing and a custom voltage.", "want": "CUSTOM_ODM/en", "got": {"language": "en", "intent": "CUSTOM_ODM", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "Your generator exploded and destroyed my warehouse. This is unacceptable!", "want": "COMPLAINT/en", "got": {"language": "en", "intent": "COMPLAINT", "urgency": "high", "sentiment": "negative", "confidence": 0.98}}
{"msg": "I need 40% off or I walk. Your competitor gives me better.", "want": "PRICE_Q/en", "got": {"language": "en", "intent": "PRICE_Q", "urgency": "high", "sentiment": "negative", "confidence": 0.95}}
{"msg": "🔥🔥 CRYPTO SIGNALS 1000x GUARANTEED JOIN NOW t.me/scam", "want": "SPAM/en", "got": {"language": "en", "intent": "SPAM", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "Good morning!", "want": "GREETING/en", "got": {"language": "en", "intent": "GREETING", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "Where is my container? It was due last week and tracking shows nothing.", "want": "SHIPPING/en", "got": {"language": "en", "intent": "SHIPPING", "urgency": "high", "sentiment": "negative", "confidence": 0.95}}
{"msg": "How much for 200 units if you redesign the control panel to our drawing?", "want": "CUSTOM_ODM/en", "got": {"language": "en", "intent": "CUSTOM_ODM", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "The unit you sent is faulty and leaking oil. Also what is the warranty period?", "want": "COMPLAINT/en", "got": {"language": "en", "intent": "COMPLAINT", "urgency": "normal", "sentiment": "negative", "confidence": 0.95}}
{"msg": "你们的50kVA静音发电机组多少钱?要100台。", "want": "PRICE_Q/zh", "got": {"language": "zh", "intent": "PRICE_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
{"msg": "请问DG-100的额定电压是多少?", "want": "SPEC_Q/zh", "got": {"language": "zh", "intent": "SPEC_Q", "urgency": "normal", "sentiment": "neutral", "confidence": 0.95}}
```

Run command (PYTHONPATH-leak discipline, spike-log trap #6):
```bash
env -u PYTHONPATH calc/.venv/bin/python tests/test_classify.py
```

## Notes / observations

- glm-4-flash returned clean JSON every time despite the fence-stripping
  regex being in place; confidence values are flat-ish (0.95 everywhere
  except the explosion complaint at 0.98). Fine for triage; revisit if we
  ever gate auto-send on confidence.
- No need to try `glm-4.5-air` — flash passed outright.
- Verdict: this exact prompt is cleared to be wired into Task 2's mock
  router and later into the dify A3-1 workflow node.
