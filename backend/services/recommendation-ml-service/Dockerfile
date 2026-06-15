FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RECOMMENDATION_ML_RUN_MIGRATIONS=false

WORKDIR /app

RUN addgroup --system courseflow && adduser --system --ingroup courseflow courseflow

COPY services/recommendation-ml-service/pyproject.toml ./pyproject.toml
COPY services/recommendation-ml-service/README.md ./README.md
COPY services/recommendation-ml-service/src ./src
COPY services/recommendation-ml-service/alembic.ini ./alembic.ini
COPY services/recommendation-ml-service/migrations ./migrations

RUN pip install --upgrade pip \
    && pip install .

USER courseflow

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import os, urllib.request; port = os.getenv('SERVER_PORT', '8080'); urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).read()"

CMD ["sh", "-c", "if [ \"${RECOMMENDATION_ML_RUN_MIGRATIONS:-false}\" = \"true\" ]; then alembic upgrade head; fi; exec uvicorn courseflow_ml.main:app --host 0.0.0.0 --port ${SERVER_PORT:-8080}"]
