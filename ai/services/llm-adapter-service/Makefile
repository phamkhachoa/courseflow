PYTHON ?= python3.11
PYTHONPATH := ../../platform/src:src

.PHONY: test lint manifest health

test:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m pytest -q

lint:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m ruff check

manifest:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m courseflow_llm_adapter_service.cli manifest

health:
	PYTHONPATH=$(PYTHONPATH) $(PYTHON) -m courseflow_llm_adapter_service.cli --ai-root ../.. --principal-id service:ai-platform-llm-ops health
