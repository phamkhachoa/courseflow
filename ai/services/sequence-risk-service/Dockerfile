FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/models /app/ai/models
COPY ai/services/sequence-risk-service /app/ai/services/sequence-risk-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/sequence-risk-service/src
WORKDIR /app/ai/services/sequence-risk-service

CMD ["python", "-m", "courseflow_sequence_risk_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-sequence-ops", "health"]
