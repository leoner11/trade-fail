#!/usr/bin/env python3
"""▣ make_license — issue / verify appliance licenses (platform plan Phase 1).

The license file IS the fulfillment artifact: client pays -> MJCX runs this
script -> drops license.json next to the appliance .env. Payment rails
(invoice today, Stripe/Midtrans links later) only change how the order
arrives — enforcement always reads this file (decoupled by design).

Scheme: hs256-v1 — HMAC-SHA256 over canonical JSON with LICENSE_SECRET.
Ed25519 (signing key never on the client box) is the documented upgrade;
the "alg" field pins the scheme so the swap is non-breaking.

Usage:
  LICENSE_SECRET=$(openssl rand -hex 32) scripts/make_license.py issue \
      --client "ACME Trading" --agents inquiry,quoting [--days 365] \
      [--trial] [--appliance-id X] [--out license.json]
  scripts/make_license.py verify [--file license.json]

Agents are validated against agents/manifest.json: unknown ids are refused
and roadmap agents are refused unless --force (roadmap != menu).
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))
import entitlement  # noqa: E402 — sibling module (canonical + sign + verify)


def _manifest_ids() -> dict:
    p = ROOT / "agents" / "manifest.json"
    if not p.exists():
        return {}
    try:
        return {a["id"]: a.get("status", "roadmap")
                for a in json.loads(p.read_text()).get("agents", [])}
    except Exception:
        return {}


def _secret(args) -> str:
    s = args.secret or os.environ.get("LICENSE_SECRET") or ""
    if not s:
        sys.exit("LICENSE_SECRET missing (env or --secret). openssl rand -hex 32")
    return s


def _issue(args) -> None:
    secret = _secret(args)
    ids = [a.strip() for a in args.agents.split(",") if a.strip()]
    if not ids:
        sys.exit("--agents required (comma-separated ids, or '*')")
    manifest = _manifest_ids()
    for aid in ids:
        if aid == "*":
            continue
        status = manifest.get(aid)
        if status is None:
            sys.exit(f"unknown agent id '{aid}' (see agents/manifest.json)")
        if status != "available" and not args.force:
            sys.exit(f"agent '{aid}' is '{status}' — roadmap != menu "
                     f"(use --force to override)")
    now = datetime.datetime.now().replace(microsecond=0)
    expires = (now + datetime.timedelta(days=args.days)).isoformat() \
        if args.days else None
    payload = {
        "v": 1,
        "alg": "hs256-v1",
        "appliance_id": args.appliance_id or socket.gethostname(),
        "client": args.client,
        "agents": ids,
        "issued_at": now.isoformat(),
        "expires_at": expires,
        "trial": bool(args.trial),
    }
    doc = dict(payload)
    doc["sig"] = entitlement.sign(payload, secret)
    out = Path(args.out) if args.out else ROOT / "license.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"issued -> {out}")
    print(f"  client     : {payload['client']}")
    print(f"  appliance  : {payload['appliance_id']}")
    print(f"  agents     : {', '.join(payload['agents'])}")
    print(f"  trial      : {payload['trial']}")
    print(f"  expires_at : {payload['expires_at'] or 'never'}")


def _verify(args) -> None:
    path = Path(args.file) if args.file else ROOT / "license.json"
    if not path.exists():
        sys.exit(f"{path} not found")
    doc = json.loads(path.read_text())
    payload, sig = entitlement._split(doc)
    ok = payload is not None and entitlement.verify(
        payload, sig, _secret(args))
    mode, grace = entitlement._mode_for(payload, datetime.datetime.now()) \
        if ok else (None, None)
    print(json.dumps({
        "file": str(path),
        "signature_ok": ok,
        "mode": mode,
        "client": (payload or {}).get("client"),
        "agents": (payload or {}).get("agents", []),
        "expires_at": (payload or {}).get("expires_at"),
        "grace_until": grace.isoformat() if grace else None,
    }, indent=2))
    sys.exit(0 if ok else 1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("issue", help="sign and write a license file")
    p1.add_argument("--client", required=True)
    p1.add_argument("--agents", required=True,
                    help="comma-separated agent ids (see agents/manifest.json) or '*'")
    p1.add_argument("--days", type=int, default=365)
    p1.add_argument("--trial", action="store_true")
    p1.add_argument("--appliance-id", default="")
    p1.add_argument("--out", default="")
    p1.add_argument("--secret", default="")
    p1.add_argument("--force", action="store_true",
                    help="allow roadmap-status agents ( discouraged )")
    p1.set_defaults(func=_issue)

    p2 = sub.add_parser("verify", help="verify an existing license file")
    p2.add_argument("--file", default="")
    p2.add_argument("--secret", default="")
    p2.set_defaults(func=_verify)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
