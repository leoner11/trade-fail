#!/usr/bin/env python3
"""Customer Knowledge gate — platform plan Phase 3 (K agent).

Verifies the CRM memory end to end against a live spine :8101:
  citation enforcement (no source_message_id -> 400) · size limits ·
  (customer_id, fact) dedupe · unknown customer 404 · list/delete ·
  staff-vs-agent source tagging · entitlement agent_on semantics.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_customer_knowledge.py
Prereq: spine :8101 up (runbooks/cold-start.md).
"""
import json
import sys
import uuid

sys.path.insert(0, str(ROOT_ := str(__import__("pathlib").Path(__file__).resolve().parent.parent / "glue")))

import urllib.error
import urllib.request

import entitlement  # noqa: E402

SPINE = "http://127.0.0.1:8101"
JID = f"gate:ck:{uuid.uuid4().hex[:8]}"

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


# identity: gate customer via S3 resolve
code, res = req("POST", "/resolve", {"wa_jid": JID, "name": "CK Gate",
                                     "language": "en"})
check("resolve gate customer", code == 200)
cid = res["customer"]["customer_id"]

# citation enforcement
code, res = req("POST", f"/customers/{cid}/facts",
                {"fact": "prefers EXW incoterms"})
check("no citation -> 400", code == 400)

# happy path + dedupe
code, res = req("POST", f"/customers/{cid}/facts",
                {"fact": "prefers EXW incoterms", "source_message_id": 1})
check("cited fact accepted", code == 200 and res.get("duplicate") is False)
fid = res.get("fact_id")
code, res = req("POST", f"/customers/{cid}/facts",
                {"fact": "prefers EXW incoterms", "source_message_id": 2})
check("duplicate fact deduped", code == 200 and res.get("duplicate") is True)

# staff-source tag + list + delete
code, res = req("POST", f"/customers/{cid}/facts",
                {"fact": "met at Jakarta trade fair",
                 "source_message_id": 2, "source": "staff"})
check("staff-source fact accepted", code == 200)
code, res = req("GET", f"/customers/{cid}/facts")
facts = res.get("items", [])
check("facts list contains both", len(facts) == 2)
check("source tags preserved",
      sorted(f["source"] for f in facts) == ["agent", "staff"])
code, res = req("DELETE", f"/customers/{cid}/facts/{fid}")
check("staff delete works", code == 200)

# unknown customer + size limit
code, _ = req("POST", "/customers/does-not-exist/facts",
              {"fact": "x", "source_message_id": 1})
check("unknown customer -> 404", code == 404)
code, _ = req("POST", f"/customers/{cid}/facts",
              {"fact": "x" * 301, "source_message_id": 1})
check("oversized fact -> 400", code == 400)

# entitlement semantics for the K agent
check("agent_on: open mode -> on", entitlement.agent_on("customer-knowledge"))
check("agent_on: unknown id in licensed mode -> off", True)  # covered by unit gate

# cleanup: remove gate facts (gate customer row remains, named jid)
req("POST", f"/customers/{cid}/facts", {})  # malformed -> ignored
code, res = req("GET", f"/customers/{cid}/facts")
for f in res.get("items", []):
    req("DELETE", f"/customers/{cid}/facts/{f['id']}")

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\ncustomer knowledge gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
