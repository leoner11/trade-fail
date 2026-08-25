#!/usr/bin/env python3
"""O5 Scenario 10 — WhatsApp QR-drop drill (session health, flowchart X2).

Default (safe): verifies evo is reachable + reports current session state +
prints the drill checklist. Nothing is touched.

--execute: performs the REAL drill — logs the instance out, waits for you
to re-scan with runbooks/whatsapp-qr-rescan.md, polls until state=open.
Requires Leonard's phone. Only run when a dropped session is acceptable.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_o5_s10_qr_drill.py
      env -u PYTHONPATH calc/.venv/bin/python tests/test_o5_s10_qr_drill.py --execute
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

EVO = "http://127.0.0.1:8080"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))
import mock_responder as mr  # noqa: E402

INSTANCE = mr.INSTANCE
KEY = mr.EVO_KEY
EXECUTE = "--execute" in sys.argv

passed = failed = 0


def check(name, cond, detail=""):
    global passed, failed
    print(f"  {'✓' if cond else '✗'} {name}" +
          (f"  [{detail}]" if detail and not cond else ""))
    passed += bool(cond)
    failed += not cond


def state():
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request(
                f"{EVO}/instance/connectionState/{INSTANCE}",
                headers={"apikey": KEY}), timeout=15).read())
        return r["instance"]["state"]
    except Exception as e:
        return f"unreachable ({e})"


print("== S10a: evo reachable ==")
st = state()
check(f"instance '{INSTANCE}' answers", not st.startswith("unreachable"), st)

print(f"== S10b: current session state == {st} ==")
check("session open", st == "open", st)
if st != "open" and not EXECUTE:
    print("\nSession NOT open -> run the rescan runbook now, then re-run:")
    print(f"  open http://localhost:8080/instance/connect/{INSTANCE}")
    print("  (render the base64 QR; phone: WhatsApp → Linked devices → Link)")
    sys.exit(1)

print("== S10c: rescan runbook exists ==")
rb = ROOT / "runbooks" / "whatsapp-qr-rescan.md"
check(str(rb.relative_to(ROOT)), rb.exists())

if not EXECUTE:
    print("\nDRILL MODE (dry): nothing was touched. To perform the real drop:")
    print(f"  {sys.argv[0]} --execute")
    print("  → logs out, prints QR URL, polls until you re-scan (10 min cap).")
    sys.exit(0 if failed == 0 else 1)

# ---------------- real drill ----------------
print("\n== REAL DRILL: dropping session ==")
mr._post(f"{EVO}/instance/logout/{INSTANCE}", {}, headers={"apikey": KEY},
         timeout=30)
time.sleep(5)
print("state now:", state())
print(f"\n👉 Scan to relink: http://localhost:8080/instance/connect/{INSTANCE}")
print("   (open in browser → renders base64 QR; phone: WhatsApp →")
print("    Linked devices → Link a device)\n")

deadline = time.time() + 600
while time.time() < deadline:
    s = state()
    if s == "open":
        check("re-scan successful within 10 min", True)
        break
    print(f"   waiting... ({s})", end="\r")
    time.sleep(10)
else:
    check("re-scan successful within 10 min", False, "timeout")

# proof of life: glue still answers and can send via evo
try:
    health = mr._get("http://127.0.0.1:8102/health")
    check("glue healthy after reconnect", bool(health.get("ok")))
except Exception as e:
    check("glue healthy after reconnect", False, str(e))

print(f"\nS10 RESULT: {passed} passed, {failed} failed "
      f"(target < 5 min self-serve per X2)")
sys.exit(1 if failed else 0)
