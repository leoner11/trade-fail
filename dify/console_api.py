#!/usr/bin/env python3
"""▣ dify console-api helper — config-as-code plumbing (S7).

The dify 1.16 console is cookie-authenticated and CSRF-guarded (see
spike-log "Console-API traps"): login wants the password base64-encoded,
returns NO token in the body, and every mutating call needs the
X-CSRF-Token header. This wraps that dance so prompts/DSL/graph edits are
scripted, repeatable, and never hand-poked in a browser.

Subcommands:
  whoami                      verify login works
  apps                        list apps (id / name / mode)
  get-draft APP_ID            dump the draft workflow JSON to stdout
  put-draft APP_ID FILE       upload a draft workflow JSON from FILE
  publish APP_ID              publish the current draft
  export APP_ID               print the exported DSL yaml to stdout
  patch-node APP_ID NODE_ID FIELD FILE
                              replace a draft node's field (FIELD: code |
                              prompt) with the contents of FILE, then save
                              the draft (publish separately)
  dataset-key ENV_NAME        ensure a dataset API key exists; store it in
                              .env under ENV_NAME (never printed)
  app-key APP_ID ENV_NAME     ensure an app service key exists; store in
                              .env under ENV_NAME (never printed)

Env: reads .env (DIFY_BASE_URL, DIFY_ADMIN_EMAIL, DIFY_ADMIN_PASSWORD).
"""
import base64
import http.cookiejar
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
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
BASE = ENV["DIFY_BASE_URL"].rstrip("/")
EMAIL = ENV["DIFY_ADMIN_EMAIL"]
PASSWORD = ENV["DIFY_ADMIN_PASSWORD"]

_CTX = ssl.create_default_context(
    cafile="/etc/ssl/cert.pem" if os.path.exists("/etc/ssl/cert.pem") else None)


class Console:
    """Cookie session against the dify console API."""

    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar),
            urllib.request.HTTPSHandler(context=_CTX))

    def _req(self, method: str, path: str, payload=None, retry_auth=True):
        url = f"{BASE}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        headers = {"Content-Type": "application/json"}
        csrf = next((c.value for c in self.jar if c.name == "csrf_token"), None)
        if csrf:
            headers["X-CSRF-Token"] = csrf
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self.opener.open(req, timeout=60) as r:
                raw = r.read().decode()
                return json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:300]
            if e.code == 401 and retry_auth:
                self.login()
                return self._req(method, path, payload, retry_auth=False)
            raise RuntimeError(f"{method} {path} -> {e.code}: {body}") from None

    def login(self) -> None:
        # password travels base64-encoded (trap); response body has no token,
        # auth lives in the access_token/csrf_token cookies it sets.
        body = json.dumps({
            "email": EMAIL,
            "password": base64.b64encode(PASSWORD.encode()).decode(),
            "remember_me": True})
        req = urllib.request.Request(
            f"{BASE}/console/api/login", data=body.encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with self.opener.open(req, timeout=60) as r:
            res = json.loads(r.read())
        if res.get("result") != "success":
            raise RuntimeError(f"login failed: {res}")

    def get(self, path):
        return self._req("GET", path)

    def post(self, path, payload=None):
        return self._req("POST", path, payload or {})

    # NOTE: dify 1.16 saves the draft via POST (sync_draft_workflow), not PUT
    def post(self, path, payload=None):
        return self._req("POST", path, payload or {})


def upsert_env(name: str, value: str) -> None:
    """Store KEY=value in .env without ever printing the value."""
    p = ROOT / ".env"
    lines = p.read_text().splitlines() if p.exists() else []
    hit = False
    for i, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == name:
            lines[i] = f"{name}={value}"
            hit = True
    if not hit:
        lines.append(f"{name}={value}")
    p.write_text("\n".join(lines) + "\n")
    print(f"[env] {name} stored ({len(value)} chars)")


def cmd_apps(c: Console):
    apps = c.get("/console/api/apps?page=1&limit=100").get("data", [])
    for a in apps:
        print(f"{a['id']}  {a['mode']:<10} {a['name']}")


def cmd_get_draft(c: Console, app_id: str):
    print(json.dumps(c.get(f"/console/api/apps/{app_id}/workflows/draft"), indent=2))


def cmd_put_draft(c: Console, app_id: str, file: str):
    d = json.loads(Path(file).read_text())
    payload = {"hash": d.get("hash"), **{k: d[k] for k in (
        "graph", "features", "environment_variables",
        "conversation_variables") if k in d}}
    res = c.post(f"/console/api/apps/{app_id}/workflows/draft", payload)
    print(json.dumps(res))


def cmd_publish(c: Console, app_id: str):
    res = c.post(f"/console/api/apps/{app_id}/workflows/publish")
    print(json.dumps(res)[:400])


def cmd_export(c: Console, app_id: str):
    res = c.get(f"/console/api/apps/{app_id}/export?include_secret=false")
    print(res.get("data", ""))


def cmd_import(c: Console, file: str):
    """Import a DSL yaml as a NEW app (POST apps/imports, spike-log trap)."""
    res = c.post("/console/api/apps/imports", {
        "mode": "yaml-content", "yaml_content": Path(file).read_text()})
    print(json.dumps(res))


def cmd_patch_node(c: Console, app_id: str, node_id: str, field: str, file: str):
    """field=prompt -> replaces the SYSTEM prompt_template text of an llm node;
    field=code  -> replaces the code of a code node."""
    new_text = Path(file).read_text()
    d = c.get(f"/console/api/apps/{app_id}/workflows/draft")
    graph = d["graph"]
    node = next((n for n in graph["nodes"] if n["id"] == node_id), None)
    if not node:
        sys.exit(f"node {node_id} not in draft; nodes="
                 f"{[n['id'] for n in graph['nodes']]}")
    if field == "code":
        node["data"]["code"] = new_text
    elif field == "prompt":
        tpl = node["data"]["prompt_template"]
        tpl[0]["text"] = new_text
    else:
        sys.exit("field must be 'code' or 'prompt'")
    payload = {"hash": d.get("hash"), **{k: d[k] for k in (
        "graph", "features", "environment_variables",
        "conversation_variables") if k in d}}
    res = c.post(f"/console/api/apps/{app_id}/workflows/draft", payload)
    print(json.dumps(res))


def cmd_dataset_key(c: Console, env_name: str):
    keys = c.get("/console/api/datasets/api-keys").get("data", [])
    if keys:
        upsert_env(env_name, keys[0]["token"])
        return
    res = c.post("/console/api/datasets/api-keys")
    upsert_env(env_name, res["token"])


def cmd_app_key(c: Console, app_id: str, env_name: str):
    keys = c.get(f"/console/api/apps/{app_id}/api-keys").get("data", [])
    if not keys:
        created = c.post(f"/console/api/apps/{app_id}/api-keys")
        keys = created.get("data") or [created]
    if isinstance(keys, dict):
        keys = [keys]
    upsert_env(env_name, keys[0]["token"])
    print(f"[app] {app_id} key bound")


def main():
    args = sys.argv[1:]
    cmds = {
        "whoami": lambda: print("login ok"),
        "apps": lambda: cmd_apps(c),
        "get-draft": lambda: cmd_get_draft(c, args[1]),
        "put-draft": lambda: cmd_put_draft(c, args[1], args[2]),
        "publish": lambda: cmd_publish(c, args[1]),
        "export": lambda: cmd_export(c, args[1]),
        "import": lambda: cmd_import(c, args[1]),
        "patch-node": lambda: cmd_patch_node(c, args[1], args[2], args[3], args[4]),
        "dataset-key": lambda: cmd_dataset_key(c, args[1]),
        "app-key": lambda: cmd_app_key(c, args[1], args[2]),
    }
    if not args or args[0] not in cmds:
        sys.exit(__doc__)
    c = Console()
    c.login()
    cmds[args[0]]()


if __name__ == "__main__":
    main()
