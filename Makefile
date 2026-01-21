# Makefile for Lark Service project

.PHONY: help install test lint format docs clean

help:
	@echo "Lark Service - Makefile Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install        Install dependencies"
	@echo "  make test           Run tests"
	@echo "  make lint           Run linters"
	@echo "  make format         Format code"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs           Build documentation"
	@echo "  make docs-serve     Build and serve documentation"
	@echo "  make docs-clean     Clean documentation build"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build Docker image"
	@echo "  make docker-up      Start services"
	@echo "  make docker-down    Stop services"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate     Run database migrations"
	@echo "  make db-rollback    Rollback last migration"

install:
	pip install -r requirements.txt

test:
	pytest tests/unit tests/contract -v

lint:
	ruff check src/ tests/
	mypy src/

format:
	ruff format src/ tests/

docs:
	cd docs && sphinx-build -b html . _build/html
	@echo ""
	@echo "✅ Documentation built successfully!"
	@echo "📂 Open: docs/_build/html/index.html"

docs-serve: docs
	cd docs/_build/html && python -m http.server 8080
	@echo "📖 Documentation server running at http://localhost:8080"

docs-clean:
	rm -rf docs/_build docs/api/*.rst

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

db-migrate:
	alembic upgrade head

db-rollback:
	alembic downgrade -1

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf docs/_build
