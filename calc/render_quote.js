#!/usr/bin/env node
/**
 * ▣ render_quote.js — Phase B4-1: quote → PDF via carbone CE (local node).
 *
 * Why local CE and not carbone-ee docker? The docker "carbone-ee" image
 * gates document CONVERSION (docx→pdf) behind a commercial license; the
 * open-source CE library does conversion free via LibreOffice. We verified
 * both paths during the 2026-08-19 spike (see docs/spike-log.md).
 *
 * Usage:
 *   node render_quote.js <calc_quote.json> <out.pdf>
 * Stdin default: /tmp/quote_result.json, out default: ./quote.pdf
 *
 * Depends: carbone (npm i carbone), LibreOffice on PATH (or set SOFFICE_PATH).
 */
const carbone = require("carbone");
const fs = require("fs");
const path = require("path");

const [,, inPath, outPath] = process.argv;
const calcOut = inPath || "/tmp/quote_result.json";
const out = outPath || path.join(__dirname, "quote.pdf");
const q = JSON.parse(fs.readFileSync(calcOut, "utf8"));

const data = {
  companyName: process.env.COMPANY_NAME || "MJCX Client Co",
  quoteId: q.request_id || q.quoteId,
  date: (q.computed_at || new Date().toISOString()).slice(0, 10),
  validUntil: q.valid_until || "",
  buyerName: q.buyer_name || process.env.BUYER_NAME || "Buyer",
  buyerCountry: q.buyer_country || "",
  incoterm: q.incoterm || "FOB",
  currency: q.currency || "USD",
  paymentTerms: q.payment_terms || "T/T 30% deposit",
  leadTime: q.lead_time || "20-30 days after PI",
  subtotal: q.subtotal,
  discountPct: q.discount_pct,
  total: q.total,
  lines: (q.lines || []).map((l) => ({
    description: l.description,
    qty: l.qty,
    unitPrice: l.unit_price ?? l.unitPrice,
    lineTotal: l.line_total ?? l.lineTotal,
  })),
};

const template = path.join(__dirname, "..", "spine", "templates", "quote_template.docx");

carbone.render(template, data, { convertTo: "pdf" }, (err, res) => {
  if (err) { console.error("RENDER ERR:", err.message); process.exit(1); }
  fs.writeFileSync(out, res);
  console.log(`PDF OK: ${out} (${res.length} bytes)`);
  process.exit(0);
});
