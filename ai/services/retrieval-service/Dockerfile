FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/services/retrieval-service /app/ai/services/retrieval-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/retrieval-service/src
WORKDIR /app/ai/services/retrieval-service

CMD ["python", "-m", "courseflow_retrieval_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-retrieval-ops", "health"]
