# calc container entrypoint: builds FastAPI app from env RULES_PATH
import os

from calculator import build_app

app = build_app(os.environ.get("RULES_PATH", "/data/rules/pricing_rules.example.json"))
