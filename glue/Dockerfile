FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir fastapi uvicorn
COPY mock_responder.py .
EXPOSE 8102
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8102", "mock_responder:app"]
