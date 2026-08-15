.PHONY: install test lint build run validate

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

lint:
	python -m ruff check .

build:
	python -m healthcare_di.pipeline

run:
	streamlit run dashboard/app.py

validate: lint test build
