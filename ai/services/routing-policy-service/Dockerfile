FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/models /app/ai/models
COPY ai/services/routing-policy-service /app/ai/services/routing-policy-service

WORKDIR /app/ai/services/routing-policy-service
ENV PYTHONPATH=/app/ai/services/routing-policy-service/src:/app/ai/platform/src

RUN pip install --no-cache-dir -e .

EXPOSE 8098

CMD ["courseflow-routing-policy", "--principal-id", "service:ai-platform-routing-ops", "serve", "--host", "0.0.0.0", "--port", "8098"]
