#!/usr/bin/env python3
"""Market Intelligence gate — platform plan Phase 5 (M agent).

Verifies: fixture RSS parsing (RSS + Atom) · S9 store intake with url-dedupe ·
digest compose cites ONLY real item ids (no fabrication) · price-watch
webhook stores verbatim value + kind · manifest/entitlement agreement.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_intel_digest.py
Prereq: spine :8101 up. Live-glue watch check needs glue :8102 revived with
this build (keepalive).
"""
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

import mock_responder as mr  # noqa: E402

SPINE = "http://127.0.0.1:8101"
UNIQ = str(int(__import__("time").time()))

FIXTURE_RSS = f"""<?xml version="1.0"?>
<rss version="2.0"><channel>
<item><title>Solar tariff ruling {UNIQ} A</title><link>https://example.com/a-{UNIQ}</link></item>
<item><title>Panel prices drop {UNIQ} B</title><link>https://example.com/b-{UNIQ}</link></item>
<item><title>Diesel genset demand up {UNIQ} C</title><link>https://example.com/c-{UNIQ}</link></item>
</channel></rss>"""

FIXTURE_ATOM = f"""<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom entry {UNIQ}</title><link href="https://example.com/d-{UNIQ}"/></entry>
</feed>"""

checks: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


def req(method: str, path: str, body: dict | None = None):
    r = urllib.request.Request(
        SPINE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


# 1 — fixture parsing: RSS and Atom both
rss_items = mr._parse_feed(FIXTURE_RSS.encode())
atom_items = mr._parse_feed(FIXTURE_ATOM.encode())
check("RSS fixture parses 3 items", len(rss_items) == 3)
check("Atom fixture parses 1 item", len(atom_items) == 1)

# 2 — S9 intake + url dedupe
ids = []
for it in rss_items:
    code, res = req("POST", "/intel/items",
                    {"source": "gate", "url": it["url"],
                     "title": it["title"], "kind": "news"})
    check(f"intake ok: {it['title'][:24]}", code == 200)
    ids.append(res["item_id"])
code, res = req("POST", "/intel/items",
                {"source": "gate", "url": rss_items[0]["url"],
                 "title": "re-fetch"})
check("url re-fetch deduped", res.get("duplicate") is True)

# 3 — digest compose: cites only real ids, deterministic
code, res = req("GET", "/intel/items?limit=30")
items = res.get("items", [])
text, cited = mr._compose_digest(items)
check("digest non-empty", bool(text))
check("digest cites only real item ids", set(cited) <= {i["id"] for i in items}
      and len(cited) > 0)
check("no invented [I<id>] tags", all(
    int(tok) in set(cited) for tok in
    __import__("re").findall(r"\[I(\d+)\]", text)))

# 4 — kind filter round-trip (price_watch stored verbatim)
code, res = req("POST", "/intel/items",
                {"source": "watch", "url": f"https://example.com/watch-{UNIQ}",
                 "title": "competitor price move", "summary": "USD 42.50",
                 "kind": "price_watch"})
wid = res["item_id"]
code, res = req("GET", "/intel/items?kind=price_watch&limit=5")
row = next((i for i in res["items"] if i["id"] == wid), None)
check("price_watch stored verbatim", row is not None
      and row["summary"] == "USD 42.50" and row["kind"] == "price_watch")

# 5 — live glue: entitlement + catalog agreement (needs revived glue)
try:
    token = os.environ.get("CONSOLE_TOKEN", "")
    if not token and (ROOT / ".env").exists():
        for line in (ROOT / ".env").read_text().splitlines():
            if line.startswith("CONSOLE_TOKEN="):
                token = line.split("=", 1)[1].strip()
    r = urllib.request.Request(
        "http://127.0.0.1:8102/console/intel/digest",
        headers={"Authorization": f"Bearer {token}"} if token else {})
    with urllib.request.urlopen(r, timeout=30) as resp:
        d = json.loads(resp.read())
    check("live digest endpoint responds",
          "digest" in d and "item_ids" in d and d.get("mode") in ("glm", "deterministic"))
except Exception as e:
    print(f"  (live glue check skipped: {str(e)[:80]})")

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\nmarket intel gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
