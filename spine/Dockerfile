FROM python:3.12-slim
WORKDIR /app
COPY init_db.py .
COPY templates/ /app/templates/
COPY rules/ /app/rules/
RUN python init_db.py
RUN pip install --no-cache-dir fastapi uvicorn
COPY spine_api.py .
EXPOSE 8101
CMD ["uvicorn", "--host", "0.0.0.0", "--port", "8101", "spine_api:app"]
