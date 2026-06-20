.PHONY: test lint manifest health

test:
	PYTHONPATH=src:../../platform/src python3.11 -m pytest

lint:
	PYTHONPATH=src:../../platform/src python3.11 -m ruff check .

manifest:
	PYTHONPATH=src:../../platform/src python3.11 -m courseflow_governance_evaluation_service manifest

health:
	PYTHONPATH=src:../../platform/src python3.11 -m courseflow_governance_evaluation_service \
		--ai-root ../.. \
		--principal-id service:ai-platform-governance-evaluation-ops \
		health
