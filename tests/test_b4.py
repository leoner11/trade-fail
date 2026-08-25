#!/usr/bin/env python3
"""B4 gate — formal-quote PDF chain, no WhatsApp needed.

resolve (S3) → calc quote → spine save+sent → carbone render → soffice PDF
→ assert artifact + S5.pdf_path recorded. DRY_RUN is forced on, so nothing
reaches evo. To also exercise the real document send:

  SEND_JID=628xxx@s.whatsapp.net env -u PYTHONPATH ... tests/test_b4.py

Run: env -u PYTHONPATH calc/.venv/bin/python tests/test_b4.py
Prereqs: spine :8101 · calc :8100 · carbone container on :8200.
First soffice conversion can take ~2 min (cold start) — expected.
"""
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

os.environ["DRY_RUN"] = "1"          # never hit evo unless explicitly asked

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

CALC = "http://127.0.0.1:8100"
SPINE = "http://127.0.0.1:8101"

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} {name}" +
          (f"  [{detail}]" if detail and not cond else ""))
    passed += bool(cond)
    failed += (not cond)


def post(url, payload, timeout=90):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())


print("== B4-0: prerequisites ==")
for name, url in [("spine :8101", f"{SPINE}/health"), ("calc :8100", f"{CALC}/health"),
                  ("carbone :8200", "http://127.0.0.1:8200/status")]:
    try:
        get(url)
        check(name, True)
    except Exception as e:
        check(name, False, str(e))

print("== B4-1: resolve -> calc quote -> S5 save+sent ==")
try:
    who = post(f"{SPINE}/resolve", {"email": "dist@example.com"})
    check("distributor resolved", who["customer"]["tier"] == "distributor",
          str(who)[:100])
    qr = post(f"{CALC}/quote", {
        "customer_id": who["customer"]["customer_id"],
        "customer_tier": who["customer"]["tier"],
        # aligned generator line (S1 = S2 = KB): DG-50 + real process fee.
        # (pre-#12 this quoted trophy vocab 'Crystal/Glass' — stale after
        # the generator alignment, see spike-log trap #29)
        "lines": [{"material": "DG-50", "size": "STD", "qty": 12,
                   "processes": ["Remote Start Controller"]}],
    })
    check("calc OK", qr.get("status") == "OK", json.dumps(qr)[:120])
    saved = post(f"{SPINE}/quotes", {
        "customer_id": who["customer"]["customer_id"],
        "request_json": {"note": "b4-gate"},
        "result_json": qr, "total": qr["quote"]["total"],
        "currency": qr["quote"]["currency"]})
    post(f"{SPINE}/quotes/{saved['quote_id']}/status", {"status": "sent"})
    check("S5 save+sent", saved["quote_id"].startswith("Q-"),
          json.dumps(saved))
except Exception as e:
    check("chain", False, str(e))
    sys.exit(1)

print("== B4-2: carbone render -> soffice pdf (cold soffice can take ~2 min)")
from mock_responder import b4_deliver, PDF_DIR, _quote_render_data  # noqa: E402

qid = saved["quote_id"]
try:
    data = _quote_render_data(qr["quote"], who["customer"], qid)
    check("render data has calc digits",
          f"{qr['quote']['total']:,.2f}" in data["total"]
          and data["validUntil"] == qr["quote"]["valid_until"])
except Exception as e:
    check("render data", False, str(e))

t0 = time.time()
ok = b4_deliver("dry-run-jid@s.whatsapp.net", who["customer"],
                qr["quote"], qid)
check(f"render+deliver pipeline ({time.time()-t0:.0f}s)", ok)
pdf = PDF_DIR / f"{qid}.pdf"
check("PDF artifact exists", pdf.exists())
if pdf.exists():
    check("PDF magic bytes", pdf.read_bytes()[:5] == b"%PDF-")
    check("PDF size sane (>10KB)", pdf.stat().st_size > 10_000,
          f"{pdf.stat().st_size} bytes")

try:
    rec = get(f"{SPINE}/quotes/{qid}")
    check("S5.pdf_path recorded", rec.get("pdf_path") == str(pdf),
          str(rec.get("pdf_path")))
except Exception as e:
    check("S5 readback", False, str(e))

if os.environ.get("SEND_JID"):
    import mock_responder as mr
    mr.DRY_RUN = False
    mr.send_document(os.environ["SEND_JID"], pdf,
                     f"[b4 gate] {qid} live document-send probe")
    check("live sendMedia attempted (watch the phone)", True)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
