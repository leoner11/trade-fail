#!/usr/bin/env python3
"""▣ spine — init SQLite stores S1/S3/S5 (+S2 pointer).

Run: env -u PYTHONPATH .venv/bin/python ../spine/init_db.py   (from calc/)
     or: python3 init_db.py  (stdlib only — no deps needed)
"""
import json
import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).parent / "spine.db"

SCHEMA = """
-- S1: catalog (structured product facts; raw PDFs live in dify KB)
CREATE TABLE IF NOT EXISTS catalog (
    sku TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    specs_json TEXT,            -- {power:"50kVA", voltage:"380V", ...}
    moq INTEGER DEFAULT 1,
    hs_code TEXT,
    certs TEXT,                 -- "CE, ISO9001"
    photo_paths TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- S3: customer identity map — THE source of truth (flowchart X1)
CREATE TABLE IF NOT EXISTS customers (
    customer_id TEXT PRIMARY KEY,
    wa_jid TEXT UNIQUE,         -- e.g. 6281234567890@s.whatsapp.net
    email TEXT,
    name TEXT,
    country TEXT,
    language TEXT DEFAULT 'en',
    tier TEXT DEFAULT 'new',    -- new | repeat | distributor
    first_seen TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

-- S5: quotes
CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    customer_id TEXT REFERENCES customers(customer_id),
    request_json TEXT,          -- parsed request from dify
    result_json TEXT,           -- calc output
    status TEXT DEFAULT 'draft',-- draft|sent|viewed|accepted|rejected|negotiating
    pdf_path TEXT,
    currency TEXT DEFAULT 'USD',
    total REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- S8: audit & alert log
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    kind TEXT,                  -- escalation|session_drop|quote_sent|...
    detail_json TEXT
);
"""

# Seed: generator-style catalog (Ducotti-flavored for the spike)
CATALOG = [
    ("DG-30",  "Diesel Genset 30kVA Silent", "generator",
     json.dumps({"power": "30kVA / 24kW", "engine": "4-cylinder water-cooled", "voltage": "220/380V 50Hz",
                 "tank": "80L", "noise": "68dB @ 7m", "dim": "1800×800×1300mm", "weight": "720kg"}), 1,
     "8502.13", "CE, ISO9001", None),
    ("DG-50",  "Diesel Genset 50kVA Silent", "generator",
     json.dumps({"power": "50kVA / 40kW", "engine": "4-cylinder turbo water-cooled", "voltage": "220/380V 50Hz",
                 "tank": "120L", "noise": "70dB @ 7m", "dim": "2150×900×1350mm", "weight": "980kg"}), 1,
     "8502.13", "CE, ISO9001", None),
    ("DG-100", "Diesel Genset 100kVA Open", "generator",
     json.dumps({"power": "100kVA / 80kW", "engine": "6-cylinder turbo intercooled", "voltage": "400V 50Hz",
                 "tank": "200L", "controller": "DeepSea DSE6120", "weight": "1600kg"}), 1,
     "8502.13", "CE, ISO9001", None),
    ("ATS-50", "ATS Panel 50A", "accessory",
     json.dumps({"rated_current": "50A", "transfer_time": "<5s", "funcs": "auto start/stop, fault alarm"}), 2,
     "8537.10", "CE", None),
    ("STS-200","Soundproof Container 20ft", "accessory",
     json.dumps({"fits": "up to 200kVA genset", "noise": "<75dB @ 1m", "material": "galvanized steel"}), 1,
     "9406.00", None, None),
]

CUSTOMERS = [
    ("cus_new_001",   None,                    None,                       "Test Buyer",      "ID", "id", "new"),
    ("cus_repeat_001","6281234567890@s.whatsapp.net", "buyer@legian.test","PT Contoh Repeat", "ID", "id", "repeat"),
    ("cus_dist_001",  None,                    "dist@example.com",         "Sample Dist Ltd", "SG", "en", "distributor"),
]


def main() -> None:
    if DB.exists():
        DB.unlink()            # spike: fresh DB each init
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    con.executemany(
        "INSERT INTO catalog (sku,name,category,specs_json,moq,hs_code,certs,photo_paths) "
        "VALUES (?,?,?,?,?,?,?,?)", CATALOG)
    con.executemany(
        "INSERT INTO customers (customer_id, wa_jid, email, name, country, language, tier) VALUES (?,?,?,?,?,?,?)",
        CUSTOMERS)
    con.commit()

    n_cat = con.execute("SELECT count(*) FROM catalog").fetchone()[0]
    n_cus = con.execute("SELECT count(*) FROM customers").fetchone()[0]
    print(f"spine.db ready: {n_cat} catalog rows, {n_cus} customers, 4 stores (S1/S3/S5/S8)")
    print(f"  rules (S2) live at: {Path(__file__).parent / 'rules' / 'pricing_rules.example.json'}")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
