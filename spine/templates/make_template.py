#!/usr/bin/env python3
"""Build the carbone quote template (.docx with {d.*} markers).

Run inside calc venv (python-docx installed there):
  env -u PYTHONPATH ../calc/.venv/bin/python make_template.py
"""
from pathlib import Path

from docx import Document
from docx.shared import Pt

OUT = Path(__file__).parent / "quote_template.docx"

doc = Document()

h = doc.add_heading("{d.companyName} — QUOTATION", 0)
p = doc.add_paragraph()
p.add_run(f"Quote No: {{d.quoteId}}    Date: {{d.date}}    Valid until: {{d.validUntil}}").bold = False
doc.add_paragraph("Buyer: {d.buyerName} ({d.buyerCountry})    Incoterm: {d.incoterm}    Currency: {d.currency}")

table = doc.add_table(rows=1, cols=5)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
for i, t in enumerate(["Description", "Qty", "Unit price", "Line total", "Notes"]):
    hdr[i].text = t

# row iterator marker — carbone syntax: [i] first row, [i+1] repeats
row = table.add_row().cells
row[0].text = "{d.lines[i].description} {d.lines[i+1].description}"
row[1].text = "{d.lines[i].qty} {d.lines[i+1].qty}"
row[2].text = "{d.lines[i].unitPrice} {d.lines[i+1].unitPrice}"
row[3].text = "{d.lines[i].lineTotal} {d.lines[i+1].lineTotal}"
row[4].text = ""

doc.add_paragraph()
doc.add_paragraph("Subtotal: {d.subtotal}")
doc.add_paragraph("Quantity discount: {d.discountPct}%")
doc.add_paragraph("TOTAL: {d.total}").runs[0].bold = True
doc.add_paragraph("Payment terms: {d.paymentTerms}")
doc.add_paragraph("Lead time: {d.leadTime}")
doc.add_paragraph("Thank you for your inquiry — {d.companyName} sales team")

OUT.parent.mkdir(parents=True, exist_ok=True)
doc.save(OUT)
print(f"template written: {OUT}")
