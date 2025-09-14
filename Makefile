# Document Converter API Makefile

.PHONY: help build run dev test clean docker-build docker-run docker-stop lint format install install-dev sync lock

# Default target
help:
	@echo "Document Converter API - Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  dev          Run development server"
	@echo "  test         Run tests"
	@echo "  lint         Run linting"
	@echo "  format       Format code"
	@echo ""
	@echo "Dependencies:"
	@echo "  install      Install production dependencies with uv"
	@echo "  install-dev  Install development dependencies with uv"
	@echo "  sync         Sync dependencies from lock file"
	@echo "  lock         Update lock file"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build Build Docker image with tags"
	@echo "  docker-run   Run Docker container"
	@echo "  docker-stop  Stop Docker container"
	@echo "  docker-images List built Docker images"
	@echo "  docker-dev   Run development with Docker Compose"
	@echo "  docker-prod  Run production with Docker Compose"
	@echo ""
	@echo "Utilities:"
	@echo "  clean        Clean up temporary files"

# Development
dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Dependencies
install:
	uv sync --no-dev --no-install-project

install-dev:
	uv sync --no-install-project

sync:
	uv sync --frozen --no-install-project

lock:
	uv lock

# Testing and Quality
test:
	uv run pytest tests/ -v --cov=app

lint:
	uv run flake8 app/
	uv run mypy app/
	uv run bandit -r app/

format:
	uv run black app/
	uv run isort app/

# Docker commands
docker-build: lock
	$(eval GIT_COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown"))
	$(eval BUILD_DATE := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown"))
	docker build \
		-t document-converter-api:latest \
		-t document-converter-api:1.0.0 \
		-t document-converter-api:$(GIT_COMMIT) \
		--build-arg BUILD_DATE=$(BUILD_DATE) \
		--build-arg GIT_COMMIT=$(GIT_COMMIT) \
		.

docker-run:
	docker run -d \
		--name document-converter-api \
		-p 8000:8000 \
		-v $(PWD)/data:/app/data \
		document-converter-api:latest

docker-stop:
	docker stop document-converter-api
	docker rm document-converter-api

docker-images:
	docker images document-converter-api

docker-dev:
	docker-compose up --build

docker-prod:
	docker-compose --profile production up --build -d

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf .uv/

# Production deployment
deploy:
	@echo "Deploying to production..."
	docker-compose --profile production up --build -d
	@echo "Deployment complete!"

# Health check
health:
	curl -f http://localhost:8000/api/v1/health || echo "Service is not running"

# Logs
logs:
	docker-compose logs -f document-converter
