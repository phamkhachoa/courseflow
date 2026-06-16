.PHONY: validate test check

PYTHON ?= python3.11

validate:
	PYTHONPATH=src $(PYTHON) -m enterprise_df.cli validate --root .

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests

check: validate test

