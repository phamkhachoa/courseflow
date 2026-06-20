FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/models /app/ai/models
COPY ai/services/payment-fraud-service /app/ai/services/payment-fraud-service

WORKDIR /app/ai/services/payment-fraud-service
ENV PYTHONPATH=/app/ai/services/payment-fraud-service/src:/app/ai/platform/src

RUN pip install --no-cache-dir -e .

EXPOSE 8096

CMD ["courseflow-payment-fraud", "--principal-id", "service:ai-platform-payment-fraud-ops", "serve", "--host", "0.0.0.0", "--port", "8096"]
