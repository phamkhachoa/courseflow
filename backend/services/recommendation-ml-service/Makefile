PYTHON ?= $(shell command -v python3.11 2>/dev/null || command -v python 2>/dev/null || command -v python3 2>/dev/null)

.PHONY: install test integration-test lint typecheck run migrate

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

integration-test:
	$(PYTHON) -m pytest tests/test_postgres_integration.py

lint:
	$(PYTHON) -m ruff check src tests

typecheck:
	$(PYTHON) -m mypy src tests

run:
	$(PYTHON) -m uvicorn courseflow_ml.main:app --host 0.0.0.0 --port $${SERVER_PORT:-8080} --reload

migrate:
	$(PYTHON) -m alembic upgrade head
