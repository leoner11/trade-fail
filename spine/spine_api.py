#!/usr/bin/env python3
"""▣ spine HTTP API — identity + catalog + quote store endpoints.

Phase A2-1 (identity resolution), S1 lookups for dify tools, S5 quote writes.
"""
import csv
import io
import json
import re
import sqlite3
import statistics
import uuid
from datetime import datetime, timedelta
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


def _ensure_post_images_column():
    """Session #14 live migration: attached images for social drafts
    (v1.5 editor). Idempotent."""
    with con() as c:
        cols = {r["name"] for r in c.execute(
            "PRAGMA table_info(social_posts)").fetchall()}
        if "images_json" not in cols:
            c.execute("ALTER TABLE social_posts ADD COLUMN images_json "
                      "TEXT NOT NULL DEFAULT '[]'")


_ensure_post_images_column()


class PostEditIn(BaseModel):
    caption: str | None = None
    hashtags: str | None = None
    scheduled_at: str | None = None


@app.patch("/posts/{pid}")
def edit_post(pid: str, inp: PostEditIn):
    """Draft editor (v1.5): caption/hashtags/schedule editable while the
    post is still PENDING — after approval it belongs to postiz."""
    fields = {k: v for k, v in inp.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(400, "nothing to edit")
    with con() as c:
        row = c.execute("SELECT status FROM social_posts WHERE post_id=?",
                        (pid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown post {pid}")
        if row["status"] != "pending":
            raise HTTPException(409, f"post is {row['status']}, not pending "
                                     "— only pending drafts are editable")
        sets = ", ".join(f"{k}=?" for k in fields)
        c.execute(f"UPDATE social_posts SET {sets}, "
                  "updated_at=CURRENT_TIMESTAMP WHERE post_id=?",
                  (*fields.values(), pid))
        out = dict(c.execute("SELECT * FROM social_posts WHERE post_id=?",
                             (pid,)).fetchone())
    return {"ok": True, "post": out}


class PostImageIn(BaseModel):
    path: str


@app.post("/posts/{pid}/images")
def append_post_image(pid: str, inp: PostImageIn):
    """Glue stores the file; spine records its path on the draft (order =
    display order). Pending only."""
    with con() as c:
        row = c.execute("SELECT status, images_json FROM social_posts "
                        "WHERE post_id=?", (pid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown post {pid}")
        if row["status"] != "pending":
            raise HTTPException(409, "only pending drafts take images")
        imgs = json.loads(row["images_json"] or "[]")
        imgs.append(inp.path)
        c.execute("UPDATE social_posts SET images_json=?, "
                  "updated_at=CURRENT_TIMESTAMP WHERE post_id=?",
                  (json.dumps(imgs), pid))
    return {"ok": True, "images": imgs}


@app.delete("/posts/{pid}/images/{idx}")
def remove_post_image(pid: str, idx: int):
    with con() as c:
        row = c.execute("SELECT images_json FROM social_posts WHERE post_id=?",
                        (pid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown post {pid}")
        imgs = json.loads(row["images_json"] or "[]")
        if not (0 <= idx < len(imgs)):
            raise HTTPException(404, "image index out of range")
        removed = imgs.pop(idx)
        c.execute("UPDATE social_posts SET images_json=?, "
                  "updated_at=CURRENT_TIMESTAMP WHERE post_id=?",
                  (json.dumps(imgs), pid))
    return {"ok": True, "removed": removed, "images": imgs}


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


# ---------- S4: conversations (v1.2 — chatwoot-replacement store) ----------

def _ensure_convo_tables():
    """Live migration for the running spike DB (init_db wipes; this must not).
    Safe to call repeatedly."""
    with con() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wa_jid TEXT UNIQUE NOT NULL,
            contact_name TEXT,
            status TEXT DEFAULT 'open',
            escalation_tag TEXT,
            escalated_at TEXT,
            sla_beacon_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            direction TEXT NOT NULL,
            sender_kind TEXT NOT NULL,
            body TEXT NOT NULL,
            ts TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """)


_ensure_convo_tables()


class ConvoUpsertIn(BaseModel):
    wa_jid: str
    name: str | None = None


@app.post("/conversations/upsert")
def conversation_upsert(inp: ConvoUpsertIn):
    with con() as c:
        row = c.execute("SELECT * FROM conversations WHERE wa_jid=?",
                        (inp.wa_jid,)).fetchone()
        if row:
            if inp.name and inp.name != row["contact_name"]:
                c.execute("UPDATE conversations SET contact_name=?, "
                          "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                          (inp.name, row["id"]))
            return {"conversation_id": row["id"], "created": False}
        cur = c.execute(
            "INSERT INTO conversations (wa_jid, contact_name) VALUES (?,?)",
            (inp.wa_jid, inp.name))
        return {"conversation_id": cur.lastrowid, "created": True}


class MessageIn(BaseModel):
    direction: str            # in | out
    sender_kind: str          # buyer | bot | human | system
    body: str


@app.post("/conversations/{cid}/messages")
def append_message(cid: int, inp: MessageIn):
    if inp.direction not in ("in", "out"):
        raise HTTPException(400, "direction must be in|out")
    if inp.sender_kind not in ("buyer", "bot", "human", "system"):
        raise HTTPException(400, "sender_kind must be buyer|bot|human|system")
    if not inp.body.strip():
        raise HTTPException(400, "empty body")
    with con() as c:
        row = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown conversation {cid}")
        cur = c.execute(
            "INSERT INTO messages (conversation_id, direction, sender_kind, body) "
            "VALUES (?,?,?,?)",
            (cid, inp.direction, inp.sender_kind, inp.body))
        # a HUMAN outbound = handled-by-person: clears any armed escalation.
        sets = "updated_at=CURRENT_TIMESTAMP"
        args: list = []
        if inp.sender_kind == "human" and row["escalation_tag"]:
            sets += ", escalation_tag=NULL, escalated_at=NULL"
        if inp.direction == "in" and row["status"] == "resolved":
            sets += ", status='open'"
        c.execute(f"UPDATE conversations SET {sets} WHERE id=?",
                  (*args, cid))
        return {"message_id": cur.lastrowid}


@app.get("/conversations")
def list_conversations(status: str = "open", include_last: int = 1,
                       limit: int = 100):
    """Console threads feed. include_last=1 adds per-conversation last
    activity timestamps so the SLA tick can filter WITHOUT N+1 queries."""
    sql = "SELECT * FROM conversations"
    args: list = []
    if status:
        sql += " WHERE status=?"
        args.append(status)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    args.append(limit)
    with con() as c:
        items = []
        for r in c.execute(sql, args).fetchall():
            d = dict(r)
            if include_last:
                agg = c.execute(
                    """SELECT MAX(CASE WHEN direction='in' THEN ts END) AS last_in_at,
                              MAX(CASE WHEN sender_kind='human' THEN ts END) AS last_human_out_at
                       FROM messages WHERE conversation_id=?""",
                    (r["id"],)).fetchone()
                d["last_in_at"] = agg["last_in_at"]
                d["last_human_out_at"] = agg["last_human_out_at"]
                prev = c.execute(
                    "SELECT body FROM messages WHERE conversation_id=? "
                    "ORDER BY id DESC LIMIT 1", (r["id"],)).fetchone()
                d["preview"] = (prev["body"][:120] if prev else "")
            items.append(d)
    return {"items": items}


@app.get("/conversations/{cid}/messages")
def thread_messages(cid: int):
    with con() as c:
        row = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown conversation {cid}")
        msgs = [dict(m) for m in c.execute(
            "SELECT id, direction, sender_kind, body, ts FROM messages "
            "WHERE conversation_id=? ORDER BY id", (cid,)).fetchall()]
    return {"conversation": dict(row), "items": msgs}


class EscalateIn(BaseModel):
    tag: str
    note: str = ""


@app.post("/conversations/{cid}/escalate")
def escalate_conversation(cid: int, inp: EscalateIn):
    """Arm the escalation flag + write the S8 event. The staff-facing note
    is stored as a system message so the console thread shows WHY."""
    with con() as c:
        row = c.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        if not row:
            raise HTTPException(404, f"unknown conversation {cid}")
        c.execute(
            "UPDATE conversations SET escalation_tag=?, escalated_at=CURRENT_TIMESTAMP, "
            "status='open', sla_beacon_at=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (inp.tag, cid))
        if inp.note.strip():
            c.execute(
                "INSERT INTO messages (conversation_id, direction, sender_kind, body) "
                "VALUES (?,?,?,?)",
                (cid, "out", "system", f"[ESCALATION {inp.tag}] {inp.note}"))
        c.execute("INSERT INTO events (kind, detail_json) VALUES (?,?)",
                  ("escalation", json.dumps({
                      "conversation_id": cid, "wa_jid": row["wa_jid"],
                      "tag": inp.tag, "note": inp.note[:500]})))
    return {"ok": True, "tag": inp.tag}


@app.post("/conversations/{cid}/sla_beacon")
def mark_sla_beacon(cid: int):
    with con() as c:
        cur = c.execute(
            "UPDATE conversations SET sla_beacon_at=CURRENT_TIMESTAMP, "
            "updated_at=CURRENT_TIMESTAMP WHERE id=?", (cid,))
        if cur.rowcount == 0:
            raise HTTPException(404, f"unknown conversation {cid}")
    return {"ok": True}


@app.post("/conversations/{cid}/status")
def set_conversation_status(cid: int, status: str = Body(..., embed=True)):
    valid = {"open", "resolved"}
    if status not in valid:
        raise HTTPException(400, f"status must be one of {sorted(valid)}")
    with con() as c:
        cur = c.execute(
            "UPDATE conversations SET status=?, escalation_tag=NULL, "
            "escalated_at=NULL, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, cid))
        if cur.rowcount == 0:
            raise HTTPException(404, f"unknown conversation {cid}")
    return {"conversation_id": cid, "status": status}


@app.get("/reports/x5")
def report_x5(days: float = 30):
    """X5 monthly report, full depth (session #14). Spine is the data owner:
    glue/console/delivery all render from this one computation.

    - AI-handled vs escalated vs human-only conversations
    - median first-response time (buyer in -> next bot/human out)
    - top asked products (quote lines + SKU/name mentions in buyer text)
    - KB misses (SPEC_Q escalations = unanswerable questions)
    - escalation reason breakdown + tier changes (S8)
    - quote money stats + SLA beacons + social counts
    """
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime(
        "%Y-%m-%d %H:%M:%S")
    with con() as c:
        convs = c.execute(
            "SELECT * FROM conversations "
            "WHERE created_at >= ? OR updated_at >= ? OR escalated_at >= ?",
            (cutoff, cutoff, cutoff)).fetchall()
        conv_by_id = {r["id"]: r for r in convs}

        msgs: list[sqlite3.Row] = []
        if conv_by_id:
            marks = ",".join("?" * len(conv_by_id))
            msgs = c.execute(
                "SELECT m.* FROM messages m WHERE m.ts >= ? AND "
                f"m.conversation_id IN ({marks}) ORDER BY m.ts",
                (cutoff, *conv_by_id.keys())).fetchall()

        # --- AI vs human vs escalation -----------------------------------
        has_bot: dict[int, bool] = {i: False for i in conv_by_id}
        for m in msgs:
            if m["sender_kind"] == "bot":
                has_bot[m["conversation_id"]] = True
        escalated_ids = [i for i, r in conv_by_id.items()
                         if r["escalation_tag"]]
        ai_handled = sum(1 for i in conv_by_id
                         if has_bot[i] and i not in set(escalated_ids))
        human_only = len(convs) - ai_handled - len(escalated_ids)

        # --- response times (buyer in -> next out by bot or human) -------
        deltas: list[float] = []
        last_in: datetime | None = None
        fmt = "%Y-%m-%d %H:%M:%S"
        for m in msgs:
            ts = datetime.strptime(m["ts"].split(".")[0], fmt)
            if m["direction"] == "in" and m["sender_kind"] == "buyer":
                last_in = ts
            elif m["direction"] == "out" and m["sender_kind"] in (
                    "bot", "human") and last_in is not None:
                d = (ts - last_in).total_seconds()
                if 0 <= d < 7 * 86400:  # ignore clock artifacts
                    deltas.append(d)
                last_in = None
        median_s = statistics.median(deltas) if deltas else None

        # --- top products -------------------------------------------------
        freq: dict[str, int] = {}
        for q in c.execute(
                "SELECT request_json FROM quotes WHERE created_at >= ?",
                (cutoff,)).fetchall():
            try:
                req = json.loads(q["request_json"] or "{}")
                for line in req.get("lines", []):
                    mat = str(line.get("material") or "?").upper()
                    if mat != "?":
                        freq[mat] = freq.get(mat, 0) + int(
                            line.get("qty") or 1)
            except Exception:
                pass
        tokens: list[str] = []
        for item in c.execute("SELECT sku, name FROM catalog").fetchall():
            tokens += [item["sku"], item["name"]]
        tok_re = re.compile(
            r"\b(" + "|".join(re.escape(t) for t in sorted(
                {t.upper() for t in tokens if len(t) >= 3},
                key=len, reverse=True)) + r")\b") if tokens else None
        for m in msgs:
            if m["direction"] == "in" and tok_re:
                for hit in tok_re.findall(m["body"].upper()):
                    freq[hit] = freq.get(hit, 0) + 1
        top_products = sorted(freq.items(), key=lambda kv: -kv[1])[:8]

        # --- KB misses + reasons + tier changes ---------------------------
        kb_misses, reasons = [], {}
        for e in c.execute(
                "SELECT ts, detail_json FROM events WHERE kind='escalation' "
                "AND ts >= ? ORDER BY ts DESC", (cutoff,)).fetchall():
            try:
                d = json.loads(e["detail_json"] or "{}")
            except Exception:
                continue
            tag = str(d.get("tag") or d.get("intent") or "?")
            reasons[tag] = reasons.get(tag, 0) + 1
            if tag == "SPEC_Q":  # KB misses ONLY — OTHER is ambiguity, not a
                # knowledge gap; the dify #34 marker will refine this later.
                wa = str(d.get("wa_jid") or d.get("remote") or "?")
                snippet = ""
                m = re.search(r"Buyer wrote: \"(.{0,200})", d.get("note") or "")
                if m:
                    snippet = m.group(1).split("\"")[0]
                else:
                    # legacy events carry no note — fall back to the
                    # conversation's last buyer line (close enough for a
                    # report; the exact trigger lives in the thread)
                    row2 = c.execute(
                        "SELECT id FROM conversations WHERE wa_jid=?",
                        (wa,)).fetchone() if wa != "?" else None
                    if row2:
                        m3 = c.execute(
                            "SELECT body FROM messages WHERE "
                            "conversation_id=? AND direction='in' AND "
                            "sender_kind='buyer' ORDER BY ts DESC LIMIT 1",
                            (row2["id"],)).fetchone()
                        if m3:
                            snippet = m3["body"][:120]
                kb_misses.append({
                    "ts": e["ts"], "contact": wa,
                    "tag": tag, "snippet": snippet})
        tier_changes = [json.loads(r["detail_json"]) | {"ts": r["ts"]}
                        for r in c.execute(
                            "SELECT ts, detail_json FROM events "
                            "WHERE kind='tier_change' AND ts >= ? "
                            "ORDER BY ts DESC", (cutoff,)).fetchall()]

        # --- money / beacons / social -------------------------------------
        quotes = c.execute(
            "SELECT status, total, currency FROM quotes WHERE created_at >= ?",
            (cutoff,)).fetchall()
        accepted = sum(1 for q in quotes if q["status"] == "accepted")
        rejected = sum(1 for q in quotes if q["status"] == "rejected")
        closed = accepted + rejected
        value = sum(q["total"] or 0 for q in quotes)
        beacons = c.execute(
            "SELECT COUNT(*) n FROM events WHERE kind='sla_beacon' "
            "AND ts >= ?", (cutoff,)).fetchone()["n"]
        posted = c.execute(
            "SELECT COUNT(*) n FROM social_posts WHERE status IN "
            "('posted','scheduled') AND updated_at >= ?",
            (cutoff,)).fetchone()["n"]
        pending_posts = c.execute(
            "SELECT COUNT(*) n FROM social_posts WHERE status='pending' "
            "AND updated_at >= ?", (cutoff,)).fetchone()["n"]

    return {
        "days": days,
        "conversations": {"total": len(convs), "ai_handled": ai_handled,
                          "escalated": len(escalated_ids),
                          "human_only": max(human_only, 0)},
        "median_response_seconds": median_s,
        "responses_measured": len(deltas),
        "top_products": [{"name": k, "count": v} for k, v in top_products],
        "kb_misses": kb_misses,
        "escalation_reasons": reasons,
        "tier_changes": tier_changes,
        "quotes": {"sent": len(quotes), "accepted": accepted,
                   "rejected": rejected,
                   "win_rate_pct": round(100 * accepted / closed)
                   if closed else None,
                   "value_sent": value},
        "sla_beacons": beacons,
        "social": {"posted_or_scheduled": posted, "pending": pending_posts},
    }


@app.get("/health")
def health():
    return {"ok": True, "store": str(DB)}
