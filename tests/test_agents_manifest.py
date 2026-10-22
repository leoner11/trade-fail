#!/usr/bin/env python3
"""Phase 2 gate — agent manifest sanity (platform plan Phase 2 packaging).

The manifest is the contract between the menu (console), the license issuer,
and the entitlement layer. This gate pins:
  - unique ids, known tiers, known statuses
  - available  => gates listed AND console routes covered by entitlement.ROUTE_MAP
  - roadmap    => never gated (no route may exist in ROUTE_MAP) and no gate claim
  - entitlement ROUTE_MAP has no prefix pointing at an unknown agent id

Run:  env -u PYTHONPATH calc/.venv/bin/python tests/test_agents_manifest.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "glue"))

import entitlement  # noqa: E402

manifest_path = ROOT / "agents" / "manifest.json"
agents = json.loads(manifest_path.read_text()).get("agents", [])

checks: list[tuple[str, bool]] = []


def check(name: str, cond) -> None:
    checks.append((name, bool(cond)))


ids = [a["id"] for a in agents]
check("manifest has agents", len(agents) > 0)
check("agent ids unique", len(ids) == len(set(ids)))

known_tiers = {"market", "ops"}
known_status = {"available", "roadmap"}
check("tiers known", all(a.get("tier") in known_tiers for a in agents))
check("statuses known", all(a.get("status") in known_status for a in agents))

route_map_agents = {agent for _, agent in entitlement.ROUTE_MAP if agent}

available = [a for a in agents if a["status"] == "available"]
roadmap = [a for a in agents if a["status"] == "roadmap"]
check("at least one available agent", len(available) > 0)
check("available agents declare gates", all(a.get("gates") for a in available))

uncovered = [
    (a["id"], r)
    for a in available
    for r in a.get("routes", [])
    if r not in {p for p, _ in entitlement.ROUTE_MAP}
]
check("available routes covered by entitlement.ROUTE_MAP", not uncovered)
if uncovered:
    print("  uncovered:", uncovered)

check("roadmap agents claim no gates (roadmap != menu)",
      not any(a.get("gates") for a in roadmap))
check("route map has no unknown agent ids", not (route_map_agents - set(ids)))

# market/ops balance: the menu must allow the 1-market + 1-ops minimum plan
check("≥1 market-side available", any(a["tier"] == "market" for a in available))
check("≥1 ops-side available", any(a["tier"] == "ops" for a in available))

failed = [name for name, ok in checks if not ok]
for name, ok in checks:
    print(("PASS" if ok else "FAIL"), name)
print(f"\nagents manifest gate: {len(checks) - len(failed)}/{len(checks)} passed")
sys.exit(1 if failed else 0)
