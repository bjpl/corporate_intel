#!/bin/bash
################################################################################
# API Deployment Script
# Corporate Intelligence Platform
################################################################################
# Version: 1.0.0
# Last Updated: October 17, 2025
#
# DESCRIPTION:
#   Deploys the Corporate Intelligence API and supporting services including
#   Nginx reverse proxy, monitoring stack (Prometheus, Grafana, Jaeger), and
#   alerting (Alertmanager).
#
# USAGE:
#   ./scripts/deploy-api.sh [OPTIONS]
#
# OPTIONS:
#   --version VERSION        Deployment version tag
#   --skip-health-checks    Skip health check validation
#   --rolling-update        Perform rolling update (zero-downtime)
#   --help                  Show this help message
#
# DEPLOYED SERVICES:
#   - Nginx reverse proxy (SSL termination)
#   - Corporate Intelligence API
#   - Prometheus (metrics)
#   - Grafana (dashboards)
#   - Jaeger (distributed tracing)
#   - Alertmanager (alert routing)
#   - Node Exporter (system metrics)
#   - cAdvisor (container metrics)
################################################################################

set -euo pipefail
IFS=$'\n\t'

# ==============================================================================
# CONFIGURATION
# ==============================================================================

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly COMPOSE_FILE="${PROJECT_ROOT}/config/production/docker-compose.production.yml"
readonly ENV_FILE="${PROJECT_ROOT}/config/production/.env.production"

# Deployment settings
DEPLOYMENT_VERSION="${DEPLOYMENT_VERSION:-latest}"
SKIP_HEALTH_CHECKS=false
ROLLING_UPDATE=false

# Health check configuration
readonly API_HEALTH_TIMEOUT=120
readonly MONITORING_HEALTH_TIMEOUT=60

# Colors
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly RED='\033[0;31m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m'

# ==============================================================================
# LOGGING
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} ✅ $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} ⚠️  $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} ❌ $*"
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

wait_for_api() {
    log_info "Waiting for API to be ready..."

    local retries=0
    local max_retries=$((API_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if curl -sf http://localhost:8000/health &> /dev/null; then
            log_success "API is ready"

            # Display health check response
            log_info "Health check response:"
            curl -s http://localhost:8000/health | jq '.' || echo "  (JSON parsing not available)"

            return 0
        fi

        ((retries++))
        log_info "Waiting for API... (${retries}/${max_retries})"
        sleep 5
    done

    log_error "API failed to become ready within ${API_HEALTH_TIMEOUT} seconds"

    # Show recent logs for debugging
    log_error "Recent API logs:"
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" logs --tail=50 api

    return 1
}

wait_for_nginx() {
    log_info "Waiting for Nginx to be ready..."

    local retries=0
    local max_retries=12

    while [[ ${retries} -lt ${max_retries} ]]; do
        if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" \
            exec -T nginx nginx -t &> /dev/null; then
            log_success "Nginx configuration is valid"
            return 0
        fi

        ((retries++))
        log_info "Waiting for Nginx... (${retries}/${max_retries})"
        sleep 5
    done

    log_error "Nginx failed to become ready"
    return 1
}

wait_for_prometheus() {
    log_info "Waiting for Prometheus to be ready..."

    local retries=0
    local max_retries=$((MONITORING_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if curl -sf http://localhost:9090/-/healthy &> /dev/null; then
            log_success "Prometheus is ready"
            return 0
        fi

        ((retries++))
        log_info "Waiting for Prometheus... (${retries}/${max_retries})"
        sleep 5
    done

    log_warning "Prometheus failed to become ready within ${MONITORING_HEALTH_TIMEOUT} seconds"
    return 1
}

wait_for_grafana() {
    log_info "Waiting for Grafana to be ready..."

    local retries=0
    local max_retries=$((MONITORING_HEALTH_TIMEOUT / 5))

    while [[ ${retries} -lt ${max_retries} ]]; do
        if curl -sf http://localhost:3000/api/health &> /dev/null; then
            log_success "Grafana is ready"
            return 0
        fi

        ((retries++))
        log_info "Waiting for Grafana... (${retries}/${max_retries})"
        sleep 5
    done

    log_warning "Grafana failed to become ready within ${MONITORING_HEALTH_TIMEOUT} seconds"
    return 1
}

# ==============================================================================
# DEPLOYMENT FUNCTIONS
# ==============================================================================

pull_images() {
    log_info "Pulling latest Docker images..."

    # Pull API image
    if [[ "${DEPLOYMENT_VERSION}" != "latest" ]]; then
        log_info "Pulling API image version: ${DEPLOYMENT_VERSION}"
        # docker pull "${DOCKER_REGISTRY}/${DOCKER_IMAGE_NAME}:${DEPLOYMENT_VERSION}"
    fi

    # Pull all other images
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" pull || log_warning "Some images failed to pull"

    log_success "Images pulled"
}

deploy_api() {
    log_info "Deploying Corporate Intelligence API..."

    if [[ "${ROLLING_UPDATE}" == true ]]; then
        log_info "Performing rolling update (zero-downtime)..."

        # Scale up new version
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --scale api=2 api
        sleep 10

        # Wait for new instance to be healthy
        wait_for_api

        # Scale down old version
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d --scale api=1 api
    else
        docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d api
    fi

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_api
    fi

    log_success "API deployment complete"
}

deploy_nginx() {
    log_info "Deploying Nginx reverse proxy..."

    # Check if SSL certificates exist (warning only)
    if [[ ! -f "/etc/letsencrypt/live/*/fullchain.pem" ]]; then
        log_warning "SSL certificates not found - HTTPS may not work"
    fi

    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d nginx

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_nginx
    fi

    log_success "Nginx deployment complete"
}

deploy_monitoring() {
    log_info "Deploying monitoring stack..."

    # Deploy Prometheus
    log_info "Deploying Prometheus..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d prometheus

    # Deploy Grafana
    log_info "Deploying Grafana..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d grafana

    # Deploy Jaeger
    log_info "Deploying Jaeger..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d jaeger

    # Deploy Alertmanager
    log_info "Deploying Alertmanager..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d alertmanager

    # Deploy exporters
    log_info "Deploying metric exporters..."
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" up -d node-exporter cadvisor

    if [[ "${SKIP_HEALTH_CHECKS}" != true ]]; then
        wait_for_prometheus
        wait_for_grafana
    fi

    log_success "Monitoring stack deployment complete"
}

verify_api_deployment() {
    log_info "Verifying API deployment..."

    # Check container status
    log_info "Container status:"
    docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps api nginx

    # Test API endpoints
    log_info "Testing API endpoints..."

    # Health endpoint
    if curl -sf http://localhost:8000/health &> /dev/null; then
        log_success "Health endpoint: OK"
    else
        log_error "Health endpoint: FAILED"
        return 1
    fi

    # API v1 health
    if curl -sf http://localhost:8000/api/v1/health &> /dev/null; then
        log_success "API v1 health endpoint: OK"
    else
        log_warning "API v1 health endpoint: FAILED (may not be implemented yet)"
    fi

    # Test sample endpoint (if database is populated)
    if curl -sf "http://localhost:8000/api/v1/companies?limit=1" &> /dev/null; then
        log_success "Companies endpoint: OK"
    else
        log_info "Companies endpoint: Not tested (database may be empty)"
    fi

    log_success "API verification complete"
}

verify_monitoring() {
    log_info "Verifying monitoring deployment..."

    # Prometheus
    if curl -sf http://localhost:9090/-/healthy &> /dev/null; then
        log_success "Prometheus: Healthy"

        # Check if scraping targets
        local up_targets
        up_targets=$(curl -s http://localhost:9090/api/v1/query?query=up | jq -r '.data.result | length')
        log_info "Prometheus monitoring ${up_targets} targets"
    else
        log_warning "Prometheus: Not healthy"
    fi

    # Grafana
    if curl -sf http://localhost:3000/api/health &> /dev/null; then
        log_success "Grafana: Healthy"
    else
        log_warning "Grafana: Not healthy"
    fi

    # Jaeger
    if docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" ps jaeger | grep -q "Up"; then
        log_success "Jaeger: Running"
    else
        log_warning "Jaeger: Not running"
    fi

    log_success "Monitoring verification complete"
}

warm_up_cache() {
    log_info "Warming up application cache..."

    # Make requests to populate cache
    local endpoints=(
        "/health"
        "/api/v1/health"
    )

    for endpoint in "${endpoints[@]}"; do
        curl -sf "http://localhost:8000${endpoint}" &> /dev/null || log_warning "Failed to warm cache for: ${endpoint}"
    done

    # Check cache statistics
    local cache_keys
    cache_keys=$(docker-compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T redis redis-cli DBSIZE 2>/dev/null || echo "0")
    log_info "Cache contains ${cache_keys} keys"

    log_success "Cache warm-up complete"
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                DEPLOYMENT_VERSION="$2"
                shift 2
                ;;
            --skip-health-checks)
                SKIP_HEALTH_CHECKS=true
                shift
                ;;
            --rolling-update)
                ROLLING_UPDATE=true
                shift
                ;;
            --help)
                cat << EOF
API Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --version VERSION        Deployment version tag
    --skip-health-checks    Skip health check validation
    --rolling-update        Perform rolling update (zero-downtime)
    --help                  Show this help message

DEPLOYED SERVICES:
    - Nginx reverse proxy (SSL termination)
    - Corporate Intelligence API
    - Prometheus (metrics)
    - Grafana (dashboards)
    - Jaeger (distributed tracing)
    - Alertmanager (alert routing)
    - Node Exporter (system metrics)
    - cAdvisor (container metrics)
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    echo "================================================================================"
    echo "API Deployment"
    echo "================================================================================"
    echo "Version: ${DEPLOYMENT_VERSION}"
    echo "Timestamp: $(date)"
    echo ""

    # Execute deployment
    pull_images
    deploy_api
    deploy_nginx
    deploy_monitoring

    # Verify deployment
    verify_api_deployment
    verify_monitoring

    # Warm up cache
    warm_up_cache

    echo ""
    echo "================================================================================"
    log_success "API deployment complete!"
    echo "================================================================================"
    echo ""
    echo "Services available:"
    echo "  - API: http://localhost:8000"
    echo "  - Prometheus: http://localhost:9090"
    echo "  - Grafana: http://localhost:3000"
    echo "  - Jaeger UI: http://localhost:16686"
    echo "  - Alertmanager: http://localhost:9093"
    echo ""
    echo "Next steps:"
    echo "  1. Run smoke tests: ./scripts/validate-deployment.sh --post-deploy"
    echo "  2. Monitor logs: docker-compose -f ${COMPOSE_FILE} logs -f api"
    echo "  3. Check Grafana dashboards for metrics"
    echo ""

    exit 0
}

main "$@"
