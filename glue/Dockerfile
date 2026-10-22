FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
# Repo-root build context (compose: context .., dockerfile glue/Dockerfile) so
# ROOT/ (parent of glue/) resolves inside the container: dify prompts and the
# agents manifest ride along. Fixes audit finding D1 — containerized glue used
# to crash on `import agent` with CONVERSATION_CORE=v2 (agent.py was missing).
COPY glue/mock_responder.py glue/agent.py glue/entitlement.py glue/knowledge_ingest.py glue/
COPY dify/prompts dify/prompts
ENV PRICING_RULES=/data/rules/pricing_rules.example.json
COPY agents agents
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8102", "--app-dir", "glue", "mock_responder:app"]
