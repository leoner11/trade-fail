#!/usr/bin/env python3
"""▣ make_doctemplates — generate the Doc-Gen bundle templates (Phase 3).

Builds minimal, valid .docx files with carbone placeholders into
spine/templates/ (the carbone-ee container renders them — npm CE corrupts
templates, trap #1). Regenerate any time:
  env -u PYTHONPATH calc/.venv/bin/python scripts/make_doctemplates.py
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "spine" / "templates"

_CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _doc(paragraphs) -> str:
    body = "".join(
        f'<w:p><w:r><w:t xml:space="preserve">{p}</w:t></w:r></w:p>'
        for p in paragraphs
    )
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/'
            f'wordprocessingml/2006/main"><w:body>{body}'
            "<w:sectPr/></w:body></w:document>")


TEMPLATES = {
    "invoice_template.docx": _doc([
        "INVOICE {d.doc_id}",
        "Date: {d.date}",
        "Customer: {d.customer_name}",
        "Re quote: {d.quote_id}",
        "",
        "{d.lines_text}",
        "",
        "Total: {d.total} {d.currency}",
    ]),
    "packing_list_template.docx": _doc([
        "PACKING LIST {d.doc_id}",
        "Date: {d.date}",
        "Customer: {d.customer_name}",
        "Re quote: {d.quote_id}",
        "",
        "{d.lines_text}",
        "",
        "Verify quantities on receipt and report damage within 48h.",
    ]),
    "proforma_template.docx": _doc([
        "PROFORMA INVOICE {d.doc_id}",
        "Date: {d.date}",
        "Customer: {d.customer_name}",
        "Re quote: {d.quote_id}",
        "",
        "{d.lines_text}",
        "",
        "Total: {d.total} {d.currency}",
        "Valid until: {d.valid_until}",
    ]),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, doc in TEMPLATES.items():
        path = OUT / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", _CT)
            z.writestr("_rels/.rels", _RELS)
            z.writestr("word/document.xml", doc)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
