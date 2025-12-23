# Makefile for audiobook-dev project

.PHONY: help install install-dev test lint format type-check clean run pre-commit ci

help:
	@echo "Available commands:"
	@echo "  make install        - Install production dependencies"
	@echo "  make install-dev    - Install development dependencies"
	@echo "  make test           - Run tests with coverage"
	@echo "  make test-fast      - Run tests without coverage"
	@echo "  make lint           - Run ruff linter"
	@echo "  make format         - Format code with ruff"
	@echo "  make type-check     - Run mypy type checking"
	@echo "  make pre-commit     - Run pre-commit hooks on all files"
	@echo "  make clean          - Clean cache and build files"
	@echo "  make run            - Run the application"
	@echo "  make ci             - Run all CI checks locally"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest --cov=src --cov-branch --cov-report=term-missing --cov-report=html --cov-fail-under=65 -v

test-fast:
	pytest -v

test-integration:
	pytest -v -m integration

lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

format:
	ruff format src/ tests/

format-check:
	ruff format --check src/ tests/

type-check:
	mypy src/ --ignore-missing-imports

pre-commit:
	pre-commit run --all-files

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	find . -type f -name "coverage.xml" -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

run:
	python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

ci: lint format-check type-check test
	@echo "✅ All CI checks passed!"

.DEFAULT_GOAL := help
