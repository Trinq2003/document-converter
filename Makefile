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
	@echo ""
	@echo "Docker Compose:"
	@echo "  docker-compose-up     Start services with Docker Compose"
	@echo "  docker-compose-down   Stop and remove services"
	@echo "  docker-compose-logs   View logs from all services"
	@echo "  docker-compose-restart Restart all services"
	@echo "  docker-compose-ps     List running services"
	@echo ""
	@echo "Environments:"
	@echo "  docker-dev           Run development environment"
	@echo "  docker-dev-detached  Run development environment in background"
	@echo "  docker-prod          Run production environment"
	@echo "  docker-prod-down     Stop production environment"
	@echo ""
	@echo "Cleanup:"
	@echo "  docker-clean         Clean up Docker resources"
	@echo "  docker-clean-all     Clean up all Docker resources (aggressive)"
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

# Docker Compose commands
docker-compose-up:
	docker-compose --profile development up --build

docker-compose-down:
	docker-compose down

docker-compose-logs:
	docker-compose logs -f

docker-compose-restart:
	docker-compose restart

docker-compose-ps:
	docker-compose ps

# Development and production environments
docker-dev:
	docker-compose --profile development up --build

docker-dev-detached:
	docker-compose --profile development up --build -d

docker-prod:
	docker-compose --profile production up --build -d

docker-prod-down:
	docker-compose --profile production down

# Docker cleanup
docker-clean:
	docker-compose down --volumes --remove-orphans

docker-clean-all:
	docker-compose down --volumes --remove-orphans

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
