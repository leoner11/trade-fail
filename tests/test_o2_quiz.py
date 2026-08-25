#!/usr/bin/env python3
"""O2-2 — Catalog Verification Quiz (flowchart gate).

The agent asks itself 20 questions against the ingested knowledge base via
the A3-Spec dify workflow. Pass = >=90% correct AND zero fabricated numbers
(answers may only reuse digits that appear in the source facts).

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_o2_quiz.py
Prereq: dify :8180 + spec dataset indexed (glue/knowledge_ingest.py done).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("DRY_RUN", "1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

import re

# digits actually present in data/example/knowledge/*.md — anything else in
# an answer is fabrication
ALLOWED_DIGITS = set("50 40 30 100 200 1 8502 13 9001 4 220 380 400 70 2150 "
                     "900 1350 980 24 80 120 68 1800 800 1300 720 1600 6120 "
                     "75 5 3 2".split())
ALLOWED = set()
for tok in ALLOWED_DIGITS:
    ALLOWED.add(tok.lstrip("0") or "0")

QUIZ = [
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

passed, failed, fabricated = 0, 0, 0


def nums(s):
    return {t.replace(",", "").lstrip("0") or "0"
            for t in re.findall(r"\d+(?:[.,]\d+)*", s)}


from mock_responder import spec_answer  # noqa: E402  (dify A3-Spec path)

for i, (q, want_any) in enumerate(QUIZ, 1):
    ans = spec_answer(q) or ""
    low = ans.lower()
    hit = any(w.lower() in low for w in want_any)

    def tok_ok(tok):
        # dotted/comma'd numbers pass if EVERY part is a known fact digit
        return all((p.lstrip("0") or "0") in ALLOWED or p in ALLOWED
                   for p in re.split(r"[.,]", tok))

    bad_digits = {t for t in nums(ans)
                  if len(t) > 1 and not tok_ok(t)}
    fab = bool(bad_digits)
    ok = hit and not fab
    passed += ok
    failed += not ok
    fabricated += fab
    print(f"  {'✓' if ok else '✗'} Q{i:02d} {q[:44]:46}"
          f" [{('hit' if hit else 'MISS')}{'+FAB' if fab else ''}] {ans[:60]}")

print(f"\n{passed}/20 correct, {fabricated} fabrications "
      f"(gate: >=18/20 AND 0 fabricated)")
sys.exit(0 if (passed >= 18 and fabricated == 0) else 1)
