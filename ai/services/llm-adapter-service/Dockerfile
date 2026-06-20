FROM python:3.11-slim

WORKDIR /app/ai/services/llm-adapter-service

COPY ai/platform /app/ai/platform
COPY ai/services/llm-adapter-service /app/ai/services/llm-adapter-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/llm-adapter-service/src

CMD ["python", "-m", "courseflow_llm_adapter_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-llm-ops", "health"]
