FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/models /app/ai/models
COPY ai/services/media-intelligence-service /app/ai/services/media-intelligence-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/media-intelligence-service/src
WORKDIR /app/ai/services/media-intelligence-service

CMD ["python", "-m", "courseflow_media_intelligence_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-media-ops", "health"]
