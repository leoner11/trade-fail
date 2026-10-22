#!/usr/bin/env python3
"""Doc-Gen gate — platform plan Phase 3 (Doc-Gen bundle).

Verifies: templates generated and structurally valid docx (zip + carbone
placeholders present) · glue wired (endpoint registered, template registry
matches manifest kinds) · entitlement route declared · live render against
carbone :8200 when it is reachable (SKIP notice otherwise — carbone is a
replaceable organ and may legitimately be down on a dev box).

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_docgen.py
Prereq: none for template/wiring checks; carbone :8200 for the live render.
"""
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

import urllib.request

import entitlement
import mock_responder as mr  # noqa: E402

checks: list[tuple[str, bool]] = []
skips: list[str] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


def skip(name: str) -> None:
    skips.append(name)
    print(f"SKIP {name}")


# 1 — templates generated and valid
tpl_dir = ROOT / "spine" / "templates"
for name in ("invoice_template.docx", "packing_list_template.docx",
             "proforma_template.docx"):
    p = tpl_dir / name
    if not p.exists():
        check(f"{name} exists", False)
        continue
    ok_zip = zipfile.is_zipfile(p)
    with zipfile.ZipFile(p) as z:
        xml = z.read("word/document.xml").decode()
    has_placeholders = "{d.doc_id}" in xml and "{d.lines_text}" in xml
    check(f"{name} valid docx with placeholders", ok_zip and has_placeholders)

# 2 — glue wiring: registry, endpoint, entitlement route
check("template registry covers invoice/packing_list/proforma",
      set(mr.DOCTEMPLATES) == {"invoice", "packing_list", "proforma"})
routes = [getattr(r, "path", "") for r in mr.app.routes]
check("/console/docgen/render registered",
      "/console/docgen/render" in routes)
check("entitlement route declared for docgen", any(
    agent == "docgen" for _, agent in entitlement.ROUTE_MAP))

# 3 — manifest gate list mentions this gate
manifest = json.loads((ROOT / "agents" / "manifest.json").read_text())
docgen = next(a for a in manifest["agents"] if a["id"] == "docgen")
check("manifest docgen gate includes tests/test_docgen.py",
      "tests/test_docgen.py" in docgen.get("gates", []))

# 4 — live render (only when carbone is up)
try:
    with urllib.request.urlopen(f"{mr.CARBONE_URL}/health", timeout=3) as r:
        carbone_up = r.status == 200
except Exception:
    carbone_up = False
if not carbone_up:
    skip("live render (carbone :8200 down — start the organ to exercise it)")
else:
    data = {"doc_id": "GATE-1", "date": "2026-09-08",
            "customer_name": "Gate", "quote_id": "Q-GATE", "total": 1,
            "currency": "USD", "lines_text": "line one",
            "valid_until": "2026-10-08"}
    try:
        out = mr._carbone_doc(
            data, tpl_dir / "invoice_template.docx", "invoice_template.docx")
        check("live carbone render returns docx", out.startswith(b"PK"))
    except Exception as e:
        check(f"live render raised: {str(e)[:80]}", False)

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\ndocgen gate: {len(checks) - len(failed)}/{len(checks)} passed, "
      f"{len(skips)} skipped")
sys.exit(1 if failed else 0)
