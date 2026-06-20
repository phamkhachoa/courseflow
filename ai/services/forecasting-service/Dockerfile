FROM python:3.11-slim

WORKDIR /app

COPY ai/platform /app/ai/platform
COPY ai/models /app/ai/models
COPY ai/services/forecasting-service /app/ai/services/forecasting-service

WORKDIR /app/ai/services/forecasting-service
ENV PYTHONPATH=/app/ai/services/forecasting-service/src:/app/ai/platform/src

RUN pip install --no-cache-dir -e .

EXPOSE 8097

CMD ["courseflow-forecasting", "--principal-id", "service:ai-platform-forecasting-ops", "serve", "--host", "0.0.0.0", "--port", "8097"]
