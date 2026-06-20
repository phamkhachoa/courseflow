FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/services/prompt-gateway-service /app/ai/services/prompt-gateway-service

ENV PYTHONPATH=/app/ai/platform/src:/app/ai/services/prompt-gateway-service/src
WORKDIR /app/ai/services/prompt-gateway-service

CMD ["python", "-m", "courseflow_prompt_gateway_service.cli", "--ai-root", "../..", "--principal-id", "service:ai-platform-prompt-ops", "health"]
