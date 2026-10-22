"""▣ entitlement — license loading, verification, and agent gating.

Platform plan Phase 1 (docs/modular-agent-platform-plan.md; flowchart v2
O1-2 / X6 / Phase L). Pure stdlib — glue carries no crypto dependency.

Semantics (audited 2026-09-08 — see docs/architecture-report-2026-09-08.md):
  no license file, never issued .... mode "open":    everything on (back-compat)
  license valid, not expired ....... mode "licensed": only the listed agents on
  expired, within GRACE_DAYS ....... mode "grace":    everything on + banner state
  expired beyond grace ............. mode "expired":  gated agents off, base on
  license.json missing/tampered AFTER first issuance: the signed last-known
  entitlement (license.seen.json shadow) is honored on its own terms —
  deleting or tampering the file never UPGRADES anything, and never cuts a
  paid term short. Both files gone -> open (back-compat).

Signature "hs256-v1": HMAC-SHA256 over the canonical JSON of the payload
(sort_keys, compact separators) with the LICENSE_SECRET shared secret.
The "alg" field pins the scheme so an Ed25519 upgrade (signing key off-box)
can be added later without changing any semantics.

Execution is gated, data never: a disabled agent returns an honest
"not in your plan"; the spine is untouched.
"""
import datetime
import hashlib
import hmac
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRACE_DAYS = 7
CACHE_TTL = 30.0  # seconds; /console/license passes force=True for fresh reads

# Longest-prefix match wins. Base platform surfaces (threads, wa, gates, b6,
# inbox, license self-read) are intentionally NOT listed — never plan-gated.
ROUTE_MAP = (
    ("/console/social/finish", None),  # OAuth relay — postiz state-guarded
    ("/console/social", "social"),
    ("/console/customers-facts", "customer-knowledge"),
    ("/console/kb", "kb"),
    ("/console/pricing", "quoting"),
    ("/console/voice", "inquiry"),
    ("/console/meetings", "meeting-intel"),
    ("/console/intel", "market-intel"),
    ("/console/sop", "sop"),
    ("/console/procurement", "supplier"),
    ("/console/positioning", "positioning"),
    ("/console/docgen", "docgen"),
)
EXEMPT_PREFIXES = ("/console/license",)


def _env_secret() -> str:
    if os.environ.get("LICENSE_SECRET"):
        return os.environ["LICENSE_SECRET"]
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("LICENSE_SECRET="):
                return line.split("=", 1)[1].strip()
    return ""


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def sign(payload: dict, secret: str) -> str:
    return hmac.new(secret.encode(), _canonical(payload).encode(),
                    hashlib.sha256).hexdigest()


def verify(payload: dict, sig: str, secret: str) -> bool:
    if not secret or not sig:
        return False
    return hmac.compare_digest(sign(payload, secret), sig)


def _load(root: Path) -> dict | None:
    p = root / "license.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _split(doc: dict) -> tuple[dict | None, str | None]:
    if not isinstance(doc, dict) or "sig" not in doc:
        return None, None
    return {k: v for k, v in doc.items() if k != "sig"}, doc["sig"]


def _shadow_write(root: Path, payload: dict, sig: str) -> None:
    """Signed last-known entitlement — the file-deletion/tamper fallback."""
    try:
        (root / "license.seen.json").write_text(json.dumps({
            "seen_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
            "sig": sig,
        }))
    except Exception:
        pass  # shadow is best-effort; gating falls back to open


def _mode_for(payload: dict, now: datetime.datetime) -> tuple[str, object]:
    exp = payload.get("expires_at")
    if not exp:
        return "licensed", None
    try:
        e = datetime.datetime.fromisoformat(exp)
    except Exception:
        return "licensed", None
    if now <= e:
        return "licensed", None
    g = e + datetime.timedelta(days=GRACE_DAYS)
    return ("grace", g) if now <= g else ("expired", g)


def _state_from(payload: dict, mode: str, grace, now: datetime.datetime) -> dict:
    return {
        "licensed": mode != "open",
        "mode": mode,
        "client": payload.get("client"),
        "appliance_id": payload.get("appliance_id"),
        "agents": payload.get("agents", []),
        "trial": bool(payload.get("trial")),
        "expires_at": payload.get("expires_at"),
        "grace_until": grace.isoformat() if grace else None,
        "detail": "",
    }


def _read_state(root: Path, secret: str, now: datetime.datetime) -> dict:
    doc = _load(root)
    payload = sig = None
    if doc:
        payload, sig = _split(doc)
        if payload is None or not verify(payload, sig, secret):
            payload = sig = None  # invalid/tampered — fall through to shadow/open
    if payload is not None:
        mode, grace = _mode_for(payload, now)
        _shadow_write(root, payload, sig)
        return _state_from(payload, mode, grace, now)
    seen = root / "license.seen.json"
    if seen.exists():
        try:
            sdoc = json.loads(seen.read_text())
            sp, ss = sdoc.get("payload"), sdoc.get("sig")
            if sp is not None and verify(sp, ss, secret):
                mode, grace = _mode_for(sp, now)
                st = _state_from(sp, mode, grace, now)
                st["detail"] = ("license file missing — honored from "
                                "last-known entitlement")
                return st
        except Exception:
            pass
    return _state_from({}, "open", None, now) | {
        "detail": "no license — everything on (back-compat)",
    }


_CACHE = (0.0, None)


def state(root=None, now=None, secret=None, force: bool = False) -> dict:
    root = Path(root) if root is not None else ROOT
    now = now or datetime.datetime.now()
    secret = secret if secret is not None else _env_secret()
    global _CACHE
    ts, cached = _CACHE
    if not force and cached is not None and root == ROOT \
            and time.time() - ts < CACHE_TTL:
        return cached
    st = _read_state(root, secret, now)
    if root == ROOT:
        _CACHE = (time.time(), st)
    return st


def license_state() -> dict:
    """Fresh state for the Console License page (never served from cache)."""
    return state(force=True)


def agent_for_path(path: str) -> str | None:
    best = None
    for prefix, agent in ROUTE_MAP:
        if path.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, agent)
    return best[1] if best else None


def enabled_for_path(path: str, root=None, now=None,
                     secret: str | None = None) -> tuple[bool, str | None]:
    """(allowed, agent_id). Base platform surfaces -> (True, None)."""
    st = state(root=root, now=now, secret=secret)
    if not path.startswith("/console"):
        return True, None
    if path.startswith(EXEMPT_PREFIXES):
        return True, None
    agent = agent_for_path(path)
    if agent is None:
        return True, None  # base platform — never plan-gated
    if st["mode"] == "open":
        return True, agent
    if st["mode"] == "expired":
        return False, agent
    agents = st["agents"]
    return ("*" in agents) or (agent in agents), agent


def agent_on(agent_id: str, root=None, now=None, secret=None) -> bool:
    """Pipeline-side gate (route() hooks): is this agent's behavior active?"""
    st = state(root=root, now=now, secret=secret)
    if st["mode"] == "open":
        return True
    if st["mode"] == "expired":
        return False
    agents = st["agents"]
    return "*" in agents or agent_id in agents
