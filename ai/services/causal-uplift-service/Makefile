.PHONY: test lint manifest

test:
	PYTHONPATH=src:../../platform/src python3.11 -m pytest

lint:
	PYTHONPATH=src:../../platform/src python3.11 -m ruff check .

manifest:
	PYTHONPATH=src:../../platform/src python3.11 -m courseflow_causal_uplift_service manifest
