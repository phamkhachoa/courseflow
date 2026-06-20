.PHONY: test lint manifest health

PYTHON ?= python3.11
PYTHONPATH := ../../platform/src:src

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff check

manifest:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m courseflow_sequence_risk_service.cli --ai-root ../.. manifest

health:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m courseflow_sequence_risk_service.cli --ai-root ../.. --principal-id service:ai-platform-sequence-ops health
