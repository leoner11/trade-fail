#!/usr/bin/env python3
"""▣ spine HTTP API — identity + catalog + quote store endpoints.

Phase A2-1 (identity resolution), S1 lookups for dify tools, S5 quote writes.
"""
import json
import sqlite3
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from pydantic import BaseModel

DB = Path("/data/spine.db") if Path("/data/spine.db").exists() else Path(__file__).parent / "spine.db"

app = FastAPI(title="MJCX spine", version="0.1.0")


def con():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


# ---------- S3: identity (flowchart A2-1) ----------

class IdentityIn(BaseModel):
    wa_jid: str | None = None
    email: str | None = None
    name: str | None = None
    country: str | None = None
    language: str = "en"


@app.post("/resolve")
def resolve(inp: IdentityIn):
    """Who is this? -> existing customer or create-new. THE S3 endpoint."""
    with con() as c:
        if inp.wa_jid:
            row = c.execute("SELECT * FROM customers WHERE wa_jid=?", (inp.wa_jid,)).fetchone()
            if row:
                return {"status": "known", "customer": dict(row)}
        if inp.email:
            row = c.execute("SELECT * FROM customers WHERE email=?", (inp.email,)).fetchone()
            if row:
                return {"status": "known", "customer": dict(row)}
        cid = f"cus_{uuid.uuid4().hex[:10]}"
        c.execute(
            "INSERT INTO customers (customer_id, wa_jid, email, name, country, language) VALUES (?,?,?,?,?,?)",
            (cid, inp.wa_jid, inp.email, inp.name, inp.country, inp.language))
        row = c.execute("SELECT * FROM customers WHERE customer_id=?", (cid,)).fetchone()
        return {"status": "new", "customer": dict(row)}


# ---------- S1: catalog ----------

@app.get("/catalog/{sku}")
def catalog_sku(sku: str):
    with con() as c:
        row = c.execute("SELECT * FROM catalog WHERE sku=?", (sku,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown sku {sku}")
        d = dict(row)
        d["specs"] = json.loads(d.pop("specs_json") or "{}")
        return d


@app.get("/catalog")
def catalog_all(q: str = ""):
    with con() as c:
        rows = c.execute(
            "SELECT sku,name,category FROM catalog WHERE name LIKE ? OR sku LIKE ?",
            (f"%{q}%", f"%{q}%")).fetchall()
        return {"items": [dict(r) for r in rows]}


# ---------- S5: quotes ----------

class QuoteSaveIn(BaseModel):
    customer_id: str
    request_json: dict
    result_json: dict
    total: float
    currency: str = "USD"


@app.post("/quotes")
def save_quote(inp: QuoteSaveIn):
    qid = f"Q-{uuid.uuid4().hex[:6].upper()}"
    with con() as c:
        c.execute(
            "INSERT INTO quotes (quote_id, customer_id, request_json, result_json, total, currency, status) "
            "VALUES (?,?,?,?,?,?, 'draft')",
            (qid, inp.customer_id, json.dumps(inp.request_json), json.dumps(inp.result_json),
             inp.total, inp.currency))
    return {"quote_id": qid, "status": "draft"}


@app.post("/quotes/{qid}/status")
def set_status(qid: str, status: str = Body(..., embed=True)):
    valid = {"draft", "sent", "viewed", "accepted", "rejected", "negotiating"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    with con() as c:
        c.execute("UPDATE quotes SET status=?, updated_at=CURRENT_TIMESTAMP WHERE quote_id=?", (status, qid))
        return {"quote_id": qid, "status": status}


@app.get("/health")
def health():
    return {"ok": True, "store": str(DB)}
