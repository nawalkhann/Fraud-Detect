FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY configs ./configs
COPY app ./app
ENV PYTHONPATH=/app/src FRAUD_DATA_DIR=/data FRAUD_MODEL_DIR=/app/models
# models/ and data/ are mounted at runtime (see docker-compose.yml), not baked into the image
EXPOSE 8000 8501
CMD ["uvicorn", "fraud.api:app", "--host", "0.0.0.0", "--port", "8000"]
