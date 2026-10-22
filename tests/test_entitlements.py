#!/usr/bin/env python3
"""Phase 1 gate — entitlement layer (platform plan Phase 1, flowchart v2 X6/L).

Verifies the license state machine end to end at the unit level:
  signature round-trip + tamper rejection · expiry → grace → expired modes ·
  shadow semantics (tamper/deletion honored from the signed last-known
  entitlement — never an upgrade, never a paid term cut short; expired
  license + deleted file = expired, no trial resurrection) ·
  route→agent gating (social/kb/pricing prefixes) · base-platform exemptions ·
  wildcard agents · open-mode back-compat · OAuth-finish + self-read exemptions.

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_entitlements.py
"""
import datetime
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

import entitlement  # noqa: E402

SECRET = "gate-test-secret"
NOW = datetime.datetime(2026, 9, 8, 12, 0, 0)

checks: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


def payload(**over) -> dict:
    p = {
        "v": 1,
        "alg": "hs256-v1",
        "appliance_id": "gate-box",
        "client": "ACME Trading",
        "agents": ["social", "quoting"],
        "issued_at": "2026-01-01T00:00:00",
        "expires_at": (NOW + datetime.timedelta(days=30)).isoformat(),
        "trial": False,
    }
    p.update(over)
    return p


def write_lic(root: Path, p: dict, sig: str | None = None,
              secret: str = SECRET) -> None:
    doc = dict(p)
    doc["sig"] = sig if sig is not None else entitlement.sign(p, secret)
    (root / "license.json").write_text(json.dumps(doc))


with tempfile.TemporaryDirectory() as td:
    root = Path(td)

    # 1 — open mode: never issued = everything on, nothing claimed
    st = entitlement._read_state(root, SECRET, NOW)
    check("open mode when never issued", st["mode"] == "open"
          and st["licensed"] is False)
    ok, agent = entitlement.enabled_for_path(
        "/console/social/posts", root=root, now=NOW, secret=SECRET)
    check("open mode: agent surface on", ok and agent == "social")
    check("open mode: base on", entitlement.enabled_for_path(
        "/console/threads/1/reply", root=root, now=NOW, secret=SECRET)[0])

    # 2 — licensed: listed agents on, unlisted off, base always on
    write_lic(root, payload())
    st = entitlement._read_state(root, SECRET, NOW)
    check("licensed mode", st["mode"] == "licensed"
          and st["client"] == "ACME Trading")
    check("social enabled", entitlement.enabled_for_path(
        "/console/social/posts", root=root, now=NOW, secret=SECRET)[0])
    check("quoting (pricing editor) enabled", entitlement.enabled_for_path(
        "/console/pricing/rules", root=root, now=NOW, secret=SECRET)[0])
    ok, agent = entitlement.enabled_for_path(
        "/console/kb/docs", root=root, now=NOW, secret=SECRET)
    check("kb (not licensed) -> 403 semantics", ok is False and agent == "kb")
    check("base threads never gated", entitlement.enabled_for_path(
        "/console/threads/1/reply", root=root, now=NOW, secret=SECRET)[0])
    check("license self-read exempt", entitlement.enabled_for_path(
        "/console/license", root=root, now=NOW, secret=SECRET)[0])
    check("oauth finish exempt", entitlement.enabled_for_path(
        "/console/social/finish/linkedin", root=root, now=NOW, secret=SECRET)[0])
    check("unknown console path = base", entitlement.enabled_for_path(
        "/console/gates/summary", root=root, now=NOW, secret=SECRET)[0])

    # 3 — tamper: bad signature falls back to the signed last-known shadow
    # (tampering must never UPGRADE entitlements), or open if never issued.
    write_lic(root, payload(), sig="0" * 64)
    st = entitlement._read_state(root, SECRET, NOW)
    check("tampered sig + valid shadow -> last-known licensed",
          st["mode"] == "licensed" and st["client"] == "ACME Trading")
    check("tampered sig: unlicensed agent still off",
          not entitlement.enabled_for_path(
              "/console/kb/docs", root=root, now=NOW, secret=SECRET)[0])
    with tempfile.TemporaryDirectory() as td2:
        root2 = Path(td2)
        write_lic(root2, payload(), sig="0" * 64)
        st2 = entitlement._read_state(root2, SECRET, NOW)
        check("tampered sig, never issued -> open", st2["mode"] == "open")

    # 4 — expiry then grace then expired
    write_lic(root, payload(
        expires_at=(NOW - datetime.timedelta(days=2)).isoformat()))
    st = entitlement._read_state(root, SECRET, NOW)
    check("within 7d grace -> still on (grace mode)", st["mode"] == "grace"
          and entitlement.enabled_for_path(
              "/console/social/posts", root=root, now=NOW, secret=SECRET)[0])
    write_lic(root, payload(
        expires_at=(NOW - datetime.timedelta(days=9)).isoformat()))
    st = entitlement._read_state(root, SECRET, NOW)
    check("beyond grace -> expired, gated off", st["mode"] == "expired"
          and not entitlement.enabled_for_path(
              "/console/social/posts", root=root, now=NOW, secret=SECRET)[0])
    check("expired: base platform still on", entitlement.enabled_for_path(
        "/console/threads/1/reply", root=root, now=NOW, secret=SECRET)[0])

    # 5 — shadow: the signed last-known entitlement is honored on its own
    # terms. Deleting the file mid-term gains nothing (they paid); deleting
    # an EXPIRED license gains nothing either (no trial resurrection); both
    # files gone -> open (back-compat).
    write_lic(root, payload())
    entitlement._read_state(root, SECRET, NOW)  # persists license.seen.json
    (root / "license.json").unlink()
    st = entitlement._read_state(root, SECRET, NOW)
    check("deleted mid-term -> honored from last-known", st["mode"] == "licensed"
          and entitlement.enabled_for_path(
              "/console/social/posts", root=root, now=NOW, secret=SECRET)[0])
    write_lic(root, payload(
        expires_at=(NOW - datetime.timedelta(days=9)).isoformat()))
    entitlement._read_state(root, SECRET, NOW)  # shadow = expired terms
    (root / "license.json").unlink()
    st = entitlement._read_state(root, SECRET, NOW)
    check("expired license + file deleted -> expired (no resurrection)",
          st["mode"] == "expired" and not entitlement.enabled_for_path(
              "/console/social/posts", root=root, now=NOW, secret=SECRET)[0])
    (root / "license.seen.json").unlink()
    st = entitlement._read_state(root, SECRET, NOW)
    check("both files gone -> open (back-compat)", st["mode"] == "open")

    # 6 — wildcard agents = everything on
    write_lic(root, payload(agents=["*"]))
    st = entitlement._read_state(root, SECRET, NOW)
    check("wildcard agents -> all agent surfaces on", st["mode"] == "licensed"
          and entitlement.enabled_for_path(
              "/console/kb/docs", root=root, now=NOW, secret=SECRET)[0])

    # 7 — signature round-trip via the issuer's own primitive
    p = payload()
    check("sign/verify round-trip", entitlement.verify(
        p, entitlement.sign(p, SECRET), SECRET))

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\nentitlements gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
