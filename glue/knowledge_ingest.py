#!/usr/bin/env python3
"""▣ knowledge ingest — client docs -> dify Knowledge (RAG home).

Onboarding rule #5: client variation lives in DATA. Drop a client's spec
sheets/FAQs under data/{client}/knowledge/, run this script, and dify's
Knowledge base is rebuilt — no code edits. The dataset feeds the A3-Spec
workflow (dify/dsl/spec_answer.yml), which glue calls for SPEC_Q traffic.

What it does:
  1. ensure the dataset exists (high-quality indexing, zhipuai embedding-3)
  2. upload every *.md|*.txt in DOCS_DIR as a document (create-by-text,
     automatic chunking); --replace re-uploads changed names instead of skip
  3. wait for indexing to finish and print the dataset_id (needed by the DSL)

Run:
  env -u PYTHONPATH calc/.venv/bin/python glue/knowledge_ingest.py \
      --dataset mjcx-knowledge --dir data/example/knowledge [--replace]

Env: .env (DIFY_BASE_URL, DIFY_DATASET_API_KEY). Stdlib only.
"""
import argparse
import json
import os
import ssl
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_file() -> dict:
    env = {}
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


ENV = {**_env_file(), **{k: v for k, v in os.environ.items()}}
BASE = ENV.get("DIFY_BASE_URL", "").rstrip("/")
KEY = ENV.get("DIFY_DATASET_API_KEY") or ""
# high_quality (vector) needs a PAID zhipuai embedding model — this key is
# glm-4-flash-only until Leonard tops up (GLM 1113 trap, see spike-log).
# economy = dify keyword indexing, free, works now. Switch back via
# KNOWLEDGE_INDEXING=high_quality after the top-up + full re-ingest.
INDEXING = os.environ.get("KNOWLEDGE_INDEXING", "economy")
EMBEDDING_PROVIDER = "langgenius/zhipuai/zhipuai"
EMBEDDING_MODEL = "embedding-3"

_CTX = ssl.create_default_context(
    cafile="/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)


def api(method: str, path: str, payload=None):
    req = urllib.request.Request(
        f"{BASE}/v1{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120, context=_CTX) as r:
        return json.loads(r.read())


def find_dataset(name: str) -> dict | None:
    page = 1
    while True:
        res = api("GET", f"/datasets?page={page}&limit=100")
        for ds in res.get("data", []):
            if ds["name"] == name:
                return ds
        if page >= res.get("total_pages", 1):
            return None
        page += 1


def ensure_dataset(name: str) -> dict:
    ds = find_dataset(name)
    if ds:
        print(f"[ds] found '{name}' id={ds['id']}")
        return ds
    payload = {"name": name, "permission": "only_me",
               "indexing_technique": INDEXING}
    if INDEXING == "high_quality":
        payload["embedding_model_provider"] = EMBEDDING_PROVIDER
        payload["embedding_model"] = EMBEDDING_MODEL
    ds = api("POST", "/datasets", payload)
    print(f"[ds] created '{name}' id={ds['id']} ({INDEXING})")
    return ds


def list_docs(ds_id: str) -> dict[str, str]:
    out, page = {}, 1
    while True:
        res = api("GET", f"/datasets/{ds_id}/documents?page={page}&limit=100")
        for d in res.get("data", []):
            out[d.get("name", "")] = d["id"]
        if page >= res.get("total_pages", 1):
            return out
        page += 1


def wait_indexed(ds_id: str, batch: str, name: str) -> None:
    for _ in range(120):  # ~2 min ceiling per doc
        st = api("GET", f"/datasets/{ds_id}/documents/{batch}/indexing-status")
        items = st.get("data", [])
        if items and items[0].get("indexing_status") == "completed":
            n = items[0].get("completed_segments")
            print(f"   indexed {name} ({n} segments)")
            return
        if items and items[0].get("error"):
            raise RuntimeError(f"indexing failed for {name}: {items[0]['error']}")
        time.sleep(1)
    raise RuntimeError(f"indexing timeout for {name}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--replace", action="store_true",
                    help="delete+reupload docs whose name already exists")
    a = ap.parse_args()

    if not KEY:
        print("DIFY_DATASET_API_KEY missing — run: "
              "dify/console_api.py dataset-key DIFY_DATASET_API_KEY")
        return 1

    ds = ensure_dataset(a.dataset)
    ds_id = ds["id"]
    existing = list_docs(ds_id)

    files = sorted(p for p in Path(a.dir).iterdir()
                   if p.suffix.lower() in (".md", ".txt"))
    if not files:
        print(f"[warn] no .md/.txt docs in {a.dir}")
        return 1

    for f in files:
        doc_name = f.name
        if doc_name in existing:
            if not a.replace:
                print(f"   skip (exists) {doc_name}")
                continue
            api("DELETE", f"/datasets/{ds_id}/documents/{existing[doc_name]}")
            print(f"   deleted old {doc_name}")
        res = api("POST", f"/datasets/{ds_id}/document/create-by-text", {
            "name": doc_name,
            "text": f.read_text(),
            "indexing_technique": INDEXING,
            "process_rule": {"mode": "automatic"}})
        wait_indexed(ds_id, res["batch"], doc_name)

    print(f"\ndone. dataset_id={ds_id}  (bake this into dify/dsl/spec_answer.yml)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
