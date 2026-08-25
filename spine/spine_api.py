#!/usr/bin/env python3
"""▣ spine HTTP API — identity + catalog + quote store endpoints.

Phase A2-1 (identity resolution), S1 lookups for dify tools, S5 quote writes.
"""
import csv
import io
import json
import sqlite3
import uuid
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Request
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


class CatalogItemIn(BaseModel):
    """Single-SKU upsert (console manual add/edit) — same row shape and gap
    semantics as /catalog/import."""
    sku: str
    name: str
    category: str = ""
    specs: dict[str, str] = {}
    moq: int = 0
    hs_code: str = ""
    certs: str = ""


def _catalog_gap(item: CatalogItemIn) -> list[str]:
    missing = []
    if not item.specs:
        missing.append("specs")
    if not item.certs.strip():
        missing.append("certs")
    if item.moq < 1:
        missing.append("moq")
    return missing


@app.post("/catalog/item")
def catalog_upsert(item: CatalogItemIn):
    sku = item.sku.strip()
    if not sku or not item.name.strip():
        raise HTTPException(400, "sku and name are required")
    with con() as c:
        c.execute(
            """INSERT INTO catalog (sku,name,category,specs_json,moq,hs_code,certs)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(sku) DO UPDATE SET
                 name=excluded.name, category=excluded.category,
                 specs_json=excluded.specs_json, moq=excluded.moq,
                 hs_code=excluded.hs_code, certs=excluded.certs,
                 updated_at=CURRENT_TIMESTAMP""",
            (sku, item.name.strip(), item.category.strip(),
             json.dumps(item.specs), item.moq, item.hs_code.strip(),
             item.certs.strip()))
    return {"ok": True, "sku": sku, "missing": _catalog_gap(item)}


@app.delete("/catalog/{sku}")
def catalog_delete(sku: str):
    with con() as c:
        cur = c.execute("DELETE FROM catalog WHERE sku=?", (sku,))
        if cur.rowcount == 0:
            raise HTTPException(404, f"unknown sku {sku}")
    return {"ok": True, "sku": sku}


@app.post("/catalog/import")
async def catalog_import(request: Request):
    """O2-1 ingest: CSV rows -> S1 upsert + GAP REPORT (deliverable #1).

    Columns (header row required, case-insensitive):
      sku,name,category,specs,moq,hs_code,certs
    `specs` is "key=value;key=value". Body = raw CSV text."""
    text = (await request.body()).decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(400, "empty CSV — needs a header row")
    cols = {c.strip().lower(): c for c in reader.fieldnames}
    for need in ("sku", "name"):
        if need not in cols:
            raise HTTPException(400, f"CSV missing required column '{need}'")

    imported, skipped, gap_report = 0, [], []
    with con() as c:
        for i, raw in enumerate(reader, start=2):  # header = line 1
            def val(key):
                k = cols.get(key)
                v = (raw.get(k) or "").strip() if k else ""
                return v
            sku = val("sku")
            name = val("name")
            if not sku or not name:
                skipped.append({"line": i, "reason": "missing sku or name"})
                continue
            specs_raw = val("specs")
            specs = {}
            for pair in filter(None, [p.strip() for p in specs_raw.split(";")]):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    specs[k.strip()] = v.strip()
                elif pair:
                    specs[pair] = ""
            moq = int(val("moq") or 0)
            missing = []
            if not specs:
                missing.append("specs")
            if not val("certs"):
                missing.append("certs")
            if moq < 1:
                missing.append("moq")
            if missing:
                gap_report.append({"sku": sku, "missing": missing})
            c.execute(
                """INSERT INTO catalog (sku,name,category,specs_json,moq,hs_code,certs)
                   VALUES (?,?,?,?,?,?,?)
                   ON CONFLICT(sku) DO UPDATE SET
                     name=excluded.name, category=excluded.category,
                     specs_json=excluded.specs_json, moq=excluded.moq,
                     hs_code=excluded.hs_code, certs=excluded.certs,
                     updated_at=CURRENT_TIMESTAMP""",
                (sku, name, val("category"), json.dumps(specs), moq,
                 val("hs_code"), val("certs")))
            imported += 1
    return {"imported": imported, "skipped": skipped, "gap_report": gap_report}


@app.get("/customers")
def list_customers(limit: int = 200):
    """S3 listing for the console dashboard (read-only view over identity)."""
    with con() as c:
        rows = c.execute(
            "SELECT * FROM customers ORDER BY first_seen DESC, customer_id DESC LIMIT ?",
            (limit,)).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.get("/customers/{cid}")
def get_customer(cid: str):
    """S3 readback for the tick jobs (follow-up drafts need name/lang/jid)."""
    with con() as c:
        row = c.execute("SELECT * FROM customers WHERE customer_id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown customer {cid}")
    return dict(row)


class CustomerPatchIn(BaseModel):
    """Console staff edits. Tier is a COMMERCIAL assignment: the agent never
    sets it (flowchart B2-1 — S3 owns which tier, S2 owns the factor). An
    unknown-to-S2 tier fails safe: calc ESCALATES instead of guessing."""
    tier: str | None = None
    name: str | None = None
    country: str | None = None
    language: str | None = None
    email: str | None = None


@app.patch("/customers/{cid}")
def update_customer(cid: str, inp: CustomerPatchIn):
    fields = {k: v.strip() for k, v in inp.model_dump(exclude_none=True).items()
              if isinstance(v, str) and v.strip()}
    if not fields:
        raise HTTPException(400, "nothing to update")
    if "tier" in fields and len(fields["tier"]) > 40:
        raise HTTPException(400, "tier too long")
    with con() as c:
        row = c.execute("SELECT * FROM customers WHERE customer_id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown customer {cid}")
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE customers SET {sets} WHERE customer_id=?",
                  (*fields.values(), cid))
        if "tier" in fields and fields["tier"] != row["tier"]:
            c.execute(
                "INSERT INTO events (kind, detail_json) VALUES (?,?)",
                ("tier_change", json.dumps({
                    "customer_id": cid,
                    "from": row["tier"], "to": fields["tier"],
                    "source": "console"})))
    return get_customer(cid)


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


@app.get("/quotes")
def list_quotes(status: str = "", older_than_hours: float = 0, limit: int = 100):
    """B6 feed: e.g. /quotes?status=sent&older_than_hours=48 -> follow-up
    candidates (updated_at is UTC, same clock as CURRENT_TIMESTAMP)."""
    sql = "SELECT * FROM quotes WHERE 1=1"
    args: list = []
    if status:
        sql += " AND status=?"
        args.append(status)
    if older_than_hours > 0:
        sql += " AND updated_at <= datetime('now', ?)"
        args.append(f"-{older_than_hours} hours")
    sql += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    with con() as c:
        rows = c.execute(sql, args).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.get("/quotes/{qid}")
def get_quote(qid: str):
    with con() as c:
        row = c.execute("SELECT * FROM quotes WHERE quote_id=?", (qid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown quote {qid}")
    d = dict(row)
    d["request_json"] = json.loads(d.pop("request_json") or "{}")
    d["result_json"] = json.loads(d.pop("result_json") or "{}")
    return d


class PdfIn(BaseModel):
    path: str


@app.post("/quotes/{qid}/pdf")
def set_pdf(qid: str, inp: PdfIn):
    """B4-1: record where the rendered quote PDF lives (S5 pdf_path)."""
    with con() as c:
        row = c.execute("SELECT quote_id FROM quotes WHERE quote_id=?", (qid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown quote {qid}")
        c.execute("UPDATE quotes SET pdf_path=?, updated_at=CURRENT_TIMESTAMP WHERE quote_id=?",
                  (inp.path, qid))
    return {"quote_id": qid, "pdf_path": inp.path}


@app.post("/quotes/{qid}/status")
def set_status(qid: str, status: str = Body(..., embed=True)):
    valid = {"draft", "sent", "viewed", "accepted", "rejected", "negotiating"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    with con() as c:
        c.execute("UPDATE quotes SET status=?, updated_at=CURRENT_TIMESTAMP WHERE quote_id=?", (status, qid))
        return {"quote_id": qid, "status": status}


# ---------- S6: social content queue (C2/C3; postiz publishes) ----------

class PostIn(BaseModel):
    sku: str = ""
    platform: str
    caption: str
    hashtags: str = ""


@app.post("/posts")
def save_post(inp: PostIn):
    pid = f"P-{uuid.uuid4().hex[:6].upper()}"
    with con() as c:
        c.execute(
            "INSERT INTO social_posts (post_id, sku, platform, caption, hashtags) "
            "VALUES (?,?,?,?,?)",
            (pid, inp.sku, inp.platform, inp.caption, inp.hashtags))
    return {"post_id": pid, "status": "pending"}


@app.get("/posts")
def list_posts(status: str = "", limit: int = 50):
    sql = "SELECT * FROM social_posts WHERE 1=1"
    args: list = []
    if status:
        sql += " AND status=?"
        args.append(status)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    with con() as c:
        rows = c.execute(sql, args).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.post("/posts/{pid}/status")
def set_post_status(pid: str, status: str = Body(..., embed=True)):
    valid = {"pending", "approved", "rejected", "scheduled", "posted"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    with con() as c:
        row = c.execute("SELECT post_id FROM social_posts WHERE post_id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown post {pid}")
        c.execute("UPDATE social_posts SET status=?, updated_at=CURRENT_TIMESTAMP WHERE post_id=?",
                  (status, pid))
    return {"post_id": pid, "status": status}


class PublishIn(BaseModel):
    postiz_id: str
    scheduled_at: str


@app.post("/posts/{pid}/publish")
def mark_published(pid: str, inp: PublishIn):
    """C4-1: accepted by postiz -> record pointer + schedule (S6)."""
    with con() as c:
        row = c.execute("SELECT post_id FROM social_posts WHERE post_id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown post {pid}")
        c.execute(
            "UPDATE social_posts SET status='scheduled', postiz_id=?, scheduled_at=?, "
            "updated_at=CURRENT_TIMESTAMP WHERE post_id=?",
            (inp.postiz_id, inp.scheduled_at, pid))
    return {"post_id": pid, "status": "scheduled", "postiz_id": inp.postiz_id}


# ---------- S8: events (escalation beacon, session drops, ...) ----------

class EventIn(BaseModel):
    kind: str
    detail_json: str = ""


@app.post("/events")
def save_event(inp: EventIn):
    """S8 audit/alert log — flowchart A6 writes an `escalation` event per
    human-handoff so the SLA beacon has something to watch."""
    with con() as c:
        c.execute("INSERT INTO events (kind, detail_json) VALUES (?,?)",
                  (inp.kind, inp.detail_json))
        row = c.execute("SELECT last_insert_rowid() AS id").fetchone()
    return {"event_id": row["id"], "kind": inp.kind}


@app.get("/events")
def recent_events(kind: str = "", limit: int = 20):
    with con() as c:
        if kind:
            rows = c.execute("SELECT * FROM events WHERE kind=? ORDER BY id DESC LIMIT ?",
                             (kind, limit)).fetchall()
        else:
            rows = c.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return {"items": [dict(r) for r in rows]}


@app.get("/health")
def health():
    return {"ok": True, "store": str(DB)}
