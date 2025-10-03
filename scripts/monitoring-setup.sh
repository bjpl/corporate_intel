#!/bin/bash

################################################################################
# Corporate Intelligence Platform - Monitoring Setup Script
################################################################################
# Description: Configure monitoring, alerting, and observability for staging
# Version: 1.0.0
# Author: Staging Deployment Specialist Agent
# Date: 2025-10-02
################################################################################

set -euo pipefail

# Color codes for output
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly RED='\033[0;31m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
readonly MONITORING_DIR="${PROJECT_ROOT}/monitoring"
readonly GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
readonly PROMETHEUS_URL="${PROMETHEUS_URL:-http://localhost:9090}"
readonly GRAFANA_USER="${GRAFANA_USER:-admin}"
readonly GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"

################################################################################
# Utility Functions
################################################################################

log_info() {
  echo -e "${BLUE}ℹ${NC} $@"
}

log_success() {
  echo -e "${GREEN}✓${NC} $@"
}

log_warning() {
  echo -e "${YELLOW}⚠${NC} $@"
}

log_error() {
  echo -e "${RED}✗${NC} $@"
}

check_service() {
  local service_name=$1
  local service_url=$2

  log_info "Checking ${service_name}..."

  if curl -sf "${service_url}" >/dev/null 2>&1; then
    log_success "${service_name} is accessible"
    return 0
  else
    log_error "${service_name} is not accessible at ${service_url}"
    return 1
  fi
}

################################################################################
# Create Monitoring Directories
################################################################################

create_monitoring_structure() {
  log_info "=== Creating Monitoring Directory Structure ==="

  mkdir -p "${MONITORING_DIR}"/{grafana,prometheus,alertmanager,dashboards}
  mkdir -p "${MONITORING_DIR}"/grafana/{dashboards,datasources,provisioning}

  log_success "Directory structure created"
}

################################################################################
# Configure Prometheus
################################################################################

configure_prometheus() {
  log_info "=== Configuring Prometheus ==="

  cat > "${MONITORING_DIR}/prometheus.yml" <<'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: staging
    cluster: corporate-intel

rule_files:
  - '/etc/prometheus/rules/*.yml'

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'

scrape_configs:
  # Corporate Intel API
  - job_name: 'corporate-intel-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  # PostgreSQL
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres:5432']

  # Redis
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  # MinIO
  - job_name: 'minio'
    static_configs:
      - targets: ['minio:9000']
    metrics_path: '/minio/v2/metrics/cluster'

  # Docker containers
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']

  # Node exporter (system metrics)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']
EOF

  log_success "Prometheus configuration created"
}

################################################################################
# Configure Alert Rules
################################################################################

configure_alert_rules() {
  log_info "=== Configuring Prometheus Alert Rules ==="

  mkdir -p "${MONITORING_DIR}/prometheus/rules"

  cat > "${MONITORING_DIR}/prometheus/rules/corporate-intel-alerts.yml" <<'EOF'
groups:
  - name: corporate_intel_api
    interval: 30s
    rules:
      # API Health
      - alert: APIDown
        expr: up{job="corporate-intel-api"} == 0
        for: 1m
        labels:
          severity: critical
          component: api
        annotations:
          summary: "Corporate Intel API is down"
          description: "API has been down for more than 1 minute"

      # High Error Rate
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "High API error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes"

      # Slow Response Time
      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
          component: api
        annotations:
          summary: "Slow API response time"
          description: "95th percentile response time is {{ $value }}s"

      # High Memory Usage
      - alert: HighMemoryUsage
        expr: (container_memory_usage_bytes{name="corporate-intel-api"} / container_spec_memory_limit_bytes{name="corporate-intel-api"}) > 0.9
        for: 5m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "High memory usage on API container"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      # High CPU Usage
      - alert: HighCPUUsage
        expr: rate(container_cpu_usage_seconds_total{name="corporate-intel-api"}[5m]) > 0.8
        for: 10m
        labels:
          severity: warning
          component: infrastructure
        annotations:
          summary: "High CPU usage on API container"
          description: "CPU usage is {{ $value | humanizePercentage }}"

  - name: database
    interval: 30s
    rules:
      # Database Down
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
          component: database
        annotations:
          summary: "PostgreSQL database is down"
          description: "Database has been down for more than 1 minute"

      # Too Many Connections
      - alert: TooManyConnections
        expr: pg_stat_database_numbackends{datname="corporate_intel_staging"} > 80
        for: 5m
        labels:
          severity: warning
          component: database
        annotations:
          summary: "Too many database connections"
          description: "Number of connections: {{ $value }}"

      # Slow Queries
      - alert: SlowQueries
        expr: rate(pg_stat_statements_mean_exec_time_seconds[5m]) > 1
        for: 5m
        labels:
          severity: warning
          component: database
        annotations:
          summary: "Database queries are slow"
          description: "Average query time: {{ $value }}s"

  - name: redis
    interval: 30s
    rules:
      # Redis Down
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: critical
          component: cache
        annotations:
          summary: "Redis cache is down"
          description: "Redis has been down for more than 1 minute"

      # High Memory Usage
      - alert: RedisMemoryHigh
        expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.9
        for: 5m
        labels:
          severity: warning
          component: cache
        annotations:
          summary: "Redis memory usage is high"
          description: "Memory usage: {{ $value | humanizePercentage }}"

      # Low Hit Rate
      - alert: LowCacheHitRate
        expr: rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) < 0.8
        for: 10m
        labels:
          severity: info
          component: cache
        annotations:
          summary: "Redis cache hit rate is low"
          description: "Hit rate: {{ $value | humanizePercentage }}"

  - name: storage
    interval: 30s
    rules:
      # MinIO Down
      - alert: MinIODown
        expr: up{job="minio"} == 0
        for: 1m
        labels:
          severity: critical
          component: storage
        annotations:
          summary: "MinIO object storage is down"
          description: "MinIO has been down for more than 1 minute"

      # High Disk Usage
      - alert: HighDiskUsage
        expr: (minio_cluster_capacity_usable_free_bytes / minio_cluster_capacity_usable_total_bytes) < 0.1
        for: 5m
        labels:
          severity: warning
          component: storage
        annotations:
          summary: "MinIO disk usage is high"
          description: "Free space: {{ $value | humanizePercentage }}"
EOF

  log_success "Alert rules configured"
}

################################################################################
# Configure Grafana Datasources
################################################################################

configure_grafana_datasources() {
  log_info "=== Configuring Grafana Datasources ==="

  mkdir -p "${MONITORING_DIR}/grafana/datasources"

  cat > "${MONITORING_DIR}/grafana/datasources/prometheus.yml" <<EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: ${PROMETHEUS_URL}
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "15s"
      httpMethod: POST
EOF

  log_success "Grafana datasources configured"
}

################################################################################
# Create Grafana Dashboards
################################################################################

create_grafana_dashboards() {
  log_info "=== Creating Grafana Dashboards ==="

  mkdir -p "${MONITORING_DIR}/grafana/dashboards"

  # Application Overview Dashboard
  cat > "${MONITORING_DIR}/grafana/dashboards/app-overview.json" <<'EOF'
{
  "dashboard": {
    "title": "Corporate Intel - Application Overview",
    "tags": ["corporate-intel", "staging", "overview"],
    "timezone": "browser",
    "refresh": "30s",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Response Time (p95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "p95"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
EOF

  log_success "Grafana dashboards created"
}

################################################################################
# Import Dashboards to Grafana
################################################################################

import_grafana_dashboards() {
  log_info "=== Importing Dashboards to Grafana ==="

  # Wait for Grafana to be ready
  local retry=0
  while [ $retry -lt 30 ]; do
    if curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1; then
      break
    fi
    retry=$((retry + 1))
    sleep 2
  done

  # Import each dashboard
  for dashboard_file in "${MONITORING_DIR}"/grafana/dashboards/*.json; do
    if [ -f "${dashboard_file}" ]; then
      log_info "Importing $(basename ${dashboard_file})..."

      curl -X POST \
        "${GRAFANA_URL}/api/dashboards/db" \
        -H "Content-Type: application/json" \
        -u "${GRAFANA_USER}:${GRAFANA_PASSWORD}" \
        -d @"${dashboard_file}" \
        >/dev/null 2>&1 && log_success "Imported $(basename ${dashboard_file})" || log_warning "Failed to import $(basename ${dashboard_file})"
    fi
  done
}

################################################################################
# Configure Health Checks
################################################################################

configure_health_checks() {
  log_info "=== Configuring Health Check Monitoring ==="

  cat > "${MONITORING_DIR}/health-check-cron.sh" <<'EOF'
#!/bin/bash
# Continuous health check script for Corporate Intel staging

API_URL="${API_URL:-http://localhost:8000}"
ALERT_EMAIL="${ALERT_EMAIL:-devops@corporate-intel.example.com}"

check_health() {
  local endpoint=$1

  if ! curl -sf "${API_URL}${endpoint}" >/dev/null 2>&1; then
    echo "ALERT: Health check failed for ${endpoint}" | mail -s "Staging Health Check Failed" ${ALERT_EMAIL}
    return 1
  fi

  return 0
}

# Check main health endpoint
check_health "/health"

# Check database health
check_health "/api/v1/health/database"

# Check Redis health
check_health "/api/v1/health/redis"

# Check MinIO health
check_health "/api/v1/health/minio"
EOF

  chmod +x "${MONITORING_DIR}/health-check-cron.sh"

  log_success "Health check script created"
  log_info "To schedule: */5 * * * * ${MONITORING_DIR}/health-check-cron.sh"
}

################################################################################
# Verify Monitoring Stack
################################################################################

verify_monitoring() {
  log_info "=== Verifying Monitoring Stack ==="

  # Check Prometheus
  check_service "Prometheus" "${PROMETHEUS_URL}/-/healthy"

  # Check Grafana
  check_service "Grafana" "${GRAFANA_URL}/api/health"

  # Check Jaeger
  check_service "Jaeger" "http://localhost:16686"

  # Verify Prometheus targets
  log_info "Checking Prometheus targets..."
  local targets=$(curl -s "${PROMETHEUS_URL}/api/v1/targets" | jq -r '.data.activeTargets | length')
  log_info "Prometheus is scraping ${targets} targets"

  log_success "Monitoring stack verification complete"
}

################################################################################
# Display Monitoring URLs
################################################################################

display_monitoring_info() {
  log_info "========================================="
  log_info "  Monitoring Setup Complete"
  log_info "========================================="
  echo ""
  log_success "Prometheus: ${PROMETHEUS_URL}"
  log_success "Grafana: ${GRAFANA_URL} (${GRAFANA_USER}/${GRAFANA_PASSWORD})"
  log_success "Jaeger: http://localhost:16686"
  echo ""
  log_info "Key Metrics:"
  echo "  - API request rate and latency"
  echo "  - Database performance"
  echo "  - Cache hit rate"
  echo "  - Infrastructure resources"
  echo "  - Error rates and alerts"
  echo ""
  log_info "Alert Rules: ${MONITORING_DIR}/prometheus/rules/"
  log_info "Dashboards: ${MONITORING_DIR}/grafana/dashboards/"
  echo ""
}

################################################################################
# Main Execution
################################################################################

main() {
  log_info "========================================="
  log_info "  Corporate Intel Monitoring Setup"
  log_info "========================================="
  echo ""

  create_monitoring_structure
  configure_prometheus
  configure_alert_rules
  configure_grafana_datasources
  create_grafana_dashboards
  configure_health_checks

  # If Grafana is running, import dashboards
  if curl -sf "${GRAFANA_URL}/api/health" >/dev/null 2>&1; then
    import_grafana_dashboards
  else
    log_warning "Grafana is not running. Start services and run this script again to import dashboards."
  fi

  verify_monitoring
  display_monitoring_info

  log_success "Monitoring setup completed successfully"
}

main "$@"
