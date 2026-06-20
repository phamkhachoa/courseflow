FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/services/model-serving-service /app/ai/services/model-serving-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/model-serving-service/src
WORKDIR /app/ai/services/model-serving-service

CMD ["python", "-m", "courseflow_model_serving_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-ops", "health"]
