# ═══════════════════════════════════════════════════════════════
# F1 Race Replay - Makefile for common development tasks
# ═══════════════════════════════════════════════════════════════

.PHONY: help install dev-install test lint format type-check clean run

# Default target - show help
help:
	@echo "F1 Race Replay - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make dev-install    Install all dependencies (including dev)"
	@echo ""
	@echo "Quality:"
	@echo "  make test           Run tests with coverage"
	@echo "  make lint           Run ruff linter"
	@echo "  make format         Format code with ruff"
	@echo "  make type-check     Run mypy type checking"
	@echo "  make check-all      Run all quality checks (lint + type + test)"
	@echo ""
	@echo "Cleaning:"
	@echo "  make clean          Remove cache and build artifacts"
	@echo "  make clean-all      Deep clean (including venv)"
	@echo ""
	@echo "Running:"
	@echo "  make run            Run the application (default race)"
	@echo ""

# ─────────────────────────────────────────────────────────────
# Installation
# ─────────────────────────────────────────────────────────────
install:
	pip install -e .

dev-install:
	pip install -e ".[dev,types]"
	pre-commit install

# ─────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────
test:
	pytest -v --cov=src --cov-report=term-missing --cov-report=html

test-fast:
	pytest -v -m "not slow"

test-integration:
	pytest -v -m integration

# ─────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────
lint:
	ruff check src/ tests/

lint-fix:
	ruff check --fix src/ tests/

format:
	ruff format src/ tests/

format-check:
	ruff format --check src/ tests/

type-check:
	mypy src/

check-all: lint type-check test

# ─────────────────────────────────────────────────────────────
# Cleaning
# ─────────────────────────────────────────────────────────────
clean:
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete

clean-all: clean
	rm -rf .venv/
	rm -rf f1-prediction-venv/

# ─────────────────────────────────────────────────────────────
# Running
# ─────────────────────────────────────────────────────────────
run:
	python main.py --year 2025 --round 12

run-qualifying:
	python main.py --year 2025 --round 12 --qualifying

run-sprint:
	python main.py --year 2025 --round 12 --sprint

# ─────────────────────────────────────────────────────────────
# Pre-commit
# ─────────────────────────────────────────────────────────────
pre-commit-all:
	pre-commit run --all-files

pre-commit-update:
	pre-commit autoupdate
