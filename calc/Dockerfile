FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY calculator.py .
ENV RULES_PATH=/data/rules/pricing_rules.json
EXPOSE 8100
CMD ["sh", "-c", "uvicorn --host 0.0.0.0 --port 8100 calculator:get_app_factory() 2>/dev/null || uvicorn --host 0.0.0.0 --port 8100 calculator:app"]
