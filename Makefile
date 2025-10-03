# Makefile for Corporate Intelligence Platform
# Simplified Docker operations and common tasks

.PHONY: help build up down restart logs shell test clean prod-build prod-up dev-up test-run migrate backup restore

# Default target
help:
	@echo "Corporate Intelligence Platform - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build           - Build all Docker images"
	@echo "  make up              - Start all services (production mode)"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View logs (all services)"
	@echo "  make shell           - Open shell in API container"
	@echo "  make test            - Run tests in Docker"
	@echo "  make clean           - Remove all containers, volumes, and images"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up          - Start development environment with hot reload"
	@echo "  make dev-down        - Stop development environment"
	@echo "  make dev-logs        - View development logs"
	@echo "  make dev-shell       - Shell into development container"
	@echo ""
	@echo "Testing:"
	@echo "  make test-run        - Run all tests in isolated environment"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make test-e2e        - Run end-to-end tests"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo ""
	@echo "Production:"
	@echo "  make prod-build      - Build production images"
	@echo "  make prod-up         - Start production environment"
	@echo "  make prod-down       - Stop production environment"
	@echo "  make prod-logs       - View production logs"
	@echo ""
	@echo "Database:"
	@echo "  make migrate         - Run database migrations"
	@echo "  make migrate-rollback - Rollback last migration"
	@echo "  make db-shell        - Open PostgreSQL shell"
	@echo "  make db-backup       - Backup database"
	@echo "  make db-restore      - Restore database from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  make prune           - Remove unused Docker resources"
	@echo "  make security-scan   - Run security scan on images"
	@echo "  make health-check    - Check service health"

# ============================================================================
# Production Commands
# ============================================================================

build:
	@echo "Building Docker images..."
	docker-compose build --no-cache

up:
	@echo "Starting production services..."
	docker-compose up -d
	@echo "Services started. View logs with 'make logs'"

down:
	@echo "Stopping all services..."
	docker-compose down

restart:
	@echo "Restarting all services..."
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec api /bin/bash

prod-build:
	@echo "Building production images..."
	docker-compose build --no-cache
	docker-compose build --no-cache --target final

prod-up:
	@echo "Starting production environment..."
	docker-compose up -d
	@$(MAKE) health-check

prod-down:
	docker-compose down

prod-logs:
	docker-compose logs -f api

# ============================================================================
# Development Commands
# ============================================================================

dev-up:
	@echo "Starting development environment with hot reload..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "  - API: http://localhost:8000"
	@echo "  - API Docs: http://localhost:8000/docs"
	@echo "  - Jaeger UI: http://localhost:16686"
	@echo "  - Grafana: http://localhost:3000"
	@echo "  - pgAdmin: http://localhost:5050"
	@echo "  - MinIO Console: http://localhost:9002"

dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

dev-shell:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml exec api /bin/bash

dev-restart:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart api

# ============================================================================
# Testing Commands
# ============================================================================

test-run:
	@echo "Running all tests in Docker..."
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test_runner
	docker-compose -f docker-compose.test.yml down -v

test-integration:
	@echo "Running integration tests..."
	docker-compose -f docker-compose.test.yml run --rm integration_test
	docker-compose -f docker-compose.test.yml down -v

test-e2e:
	@echo "Running E2E tests..."
	docker-compose -f docker-compose.test.yml run --rm e2e_test
	docker-compose -f docker-compose.test.yml down -v

test-coverage:
	@echo "Running tests with coverage..."
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit test_runner
	@echo "Coverage report generated in ./coverage_html"
	docker-compose -f docker-compose.test.yml down -v

test:
	@$(MAKE) test-run

# ============================================================================
# Database Commands
# ============================================================================

migrate:
	@echo "Running database migrations..."
	docker-compose exec api alembic upgrade head

migrate-rollback:
	@echo "Rolling back last migration..."
	docker-compose exec api alembic downgrade -1

migrate-history:
	docker-compose exec api alembic history

db-shell:
	docker-compose exec postgres psql -U $${POSTGRES_USER:-intel_user} -d $${POSTGRES_DB:-corporate_intel}

db-backup:
	@echo "Creating database backup..."
	@mkdir -p ./backups
	docker-compose exec -T postgres pg_dump -U $${POSTGRES_USER:-intel_user} $${POSTGRES_DB:-corporate_intel} > ./backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup created in ./backups/"

db-restore:
	@echo "Restoring database from backup..."
	@read -p "Enter backup file name: " BACKUP_FILE; \
	docker-compose exec -T postgres psql -U $${POSTGRES_USER:-intel_user} -d $${POSTGRES_DB:-corporate_intel} < ./backups/$$BACKUP_FILE

db-reset:
	@echo "WARNING: This will delete all data!"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker-compose up -d postgres redis minio; \
		sleep 5; \
		docker-compose up -d api; \
	fi

# ============================================================================
# Maintenance Commands
# ============================================================================

clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "Cleanup complete"

prune:
	@echo "Removing unused Docker resources..."
	docker system prune -af --volumes
	@echo "Prune complete"

security-scan:
	@echo "Running security scan on Docker images..."
	./scripts/docker-security-scan.sh || echo "Security scan script not found"

health-check:
	@echo "Checking service health..."
	@docker-compose ps
	@echo ""
	@curl -s http://localhost:8000/health | jq '.' || echo "API health check failed"

# ============================================================================
# Observability Commands
# ============================================================================

observability-up:
	@echo "Starting observability stack..."
	docker-compose --profile observability up -d
	@echo "Observability services started:"
	@echo "  - Jaeger UI: http://localhost:16686"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"

observability-down:
	docker-compose --profile observability down

# ============================================================================
# Quick Start Commands
# ============================================================================

quickstart: dev-up
	@echo "========================================"
	@echo "Corporate Intelligence Platform is ready!"
	@echo "========================================"
	@echo ""
	@echo "Services:"
	@echo "  - API: http://localhost:8000"
	@echo "  - Swagger Docs: http://localhost:8000/docs"
	@echo "  - ReDoc: http://localhost:8000/redoc"
	@echo ""
	@echo "Development Tools:"
	@echo "  - pgAdmin: http://localhost:5050"
	@echo "  - MinIO Console: http://localhost:9002"
	@echo ""
	@echo "Observability:"
	@echo "  - Jaeger: http://localhost:16686"
	@echo "  - Grafana: http://localhost:3000"
	@echo ""
	@echo "Next steps:"
	@echo "  make logs        - View all logs"
	@echo "  make dev-shell   - Open shell in API container"
	@echo "  make test        - Run tests"

status:
	@echo "Service Status:"
	@docker-compose ps
	@echo ""
	@echo "Resource Usage:"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# ============================================================================
# CI/CD Commands
# ============================================================================

ci-build:
	@echo "Building for CI/CD..."
	docker-compose build --build-arg BUILDKIT_INLINE_CACHE=1

ci-test:
	@echo "Running CI tests..."
	docker-compose -f docker-compose.test.yml up --abort-on-container-exit --exit-code-from test_runner
	docker-compose -f docker-compose.test.yml down -v

ci-push:
	@echo "Pushing Docker images..."
	docker-compose push

# ============================================================================
# Utility Commands
# ============================================================================

install-deps:
	@echo "Installing Python dependencies in container..."
	docker-compose exec api pip install -r requirements.txt

format:
	@echo "Formatting code..."
	docker-compose exec api black src/ tests/
	docker-compose exec api isort src/ tests/

lint:
	@echo "Linting code..."
	docker-compose exec api flake8 src/ tests/
	docker-compose exec api mypy src/

update:
	@echo "Pulling latest images..."
	docker-compose pull
	@$(MAKE) restart
