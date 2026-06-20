VENV = .venv
PYTHON = $(VENV)/bin/python

.PHONY: install run lint test

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -e ".[dev]"

run:
	$(PYTHON) -m bot

lint:
	$(VENV)/bin/python -m py_compile bot/*.py

test:
	$(VENV)/bin/pytest tests/ -v
