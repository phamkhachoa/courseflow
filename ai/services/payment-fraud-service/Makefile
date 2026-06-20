.PHONY: test lint manifest

PYTHONPATH := src:../../platform/src

test:
	PYTHONPATH=$(PYTHONPATH) python3.11 -m pytest

lint:
	PYTHONPATH=$(PYTHONPATH) python3.11 -m ruff check .

manifest:
	PYTHONPATH=$(PYTHONPATH) python3.11 -m courseflow_payment_fraud_service manifest
