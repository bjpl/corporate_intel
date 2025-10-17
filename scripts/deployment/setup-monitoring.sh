#!/bin/bash
# Monitoring Setup Script for Corporate Intelligence Platform
# Usage: ./setup-monitoring.sh [--environment staging|production] [--dry-run]
#
# Sets up comprehensive monitoring stack:
# - Prometheus for metrics collection
# - Grafana for visualization
# - Alertmanager for alerting
# - Log aggregation

set -euo pipefail
IFS=$'\n\t'

# Script metadata
SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOG_FILE="${PROJECT_ROOT}/logs/setup-monitoring-$(date +%Y%m%d_%H%M%S).log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
ENVIRONMENT="production"
DRY_RUN=false
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
ALERTMANAGER_PORT=9093

# Logging functions
log() {
    local level=$1
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() { log "INFO" "${BLUE}$*${NC}"; }
log_success() { log "SUCCESS" "${GREEN}✓ $*${NC}"; }
log_warning() { log "WARNING" "${YELLOW}⚠ $*${NC}"; }
log_error() { log "ERROR" "${RED}✗ $*${NC}"; }

# Error handler
handle_error() {
    local line_num=$1
    log_error "Monitoring setup failed at line ${line_num}"
    exit 1
}

trap 'handle_error ${LINENO}' ERR

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
}

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Setup monitoring stack for Corporate Intelligence Platform.

OPTIONS:
    --environment <env>     Environment (staging|production) [default: production]
    --dry-run              Preview changes without applying
    -h, --help             Show this help message

EXAMPLES:
    $0                                  # Setup production monitoring
    $0 --environment staging            # Setup staging monitoring
    $0 --dry-run                        # Preview setup

EOF
}

# Create monitoring configuration directory
create_monitoring_config_dir() {
    log_info "Creating monitoring configuration directories..."

    local dirs=(
        "${PROJECT_ROOT}/monitoring/prometheus"
        "${PROJECT_ROOT}/monitoring/grafana/dashboards"
        "${PROJECT_ROOT}/monitoring/grafana/datasources"
        "${PROJECT_ROOT}/monitoring/alertmanager"
    )

    for dir in "${dirs[@]}"; do
        if [ "${DRY_RUN}" = true ]; then
            log_info "[DRY RUN] Would create: ${dir}"
        else
            mkdir -p "${dir}"
            log_success "Created: ${dir}"
        fi
    done
}

# Configure Prometheus
configure_prometheus() {
    log_info "Configuring Prometheus..."

    local prometheus_config="${PROJECT_ROOT}/config/prometheus.yml"

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure Prometheus"
        return 0
    fi

    # Prometheus configuration already exists at config/prometheus.yml
    if [ -f "${prometheus_config}" ]; then
        log_success "Prometheus config exists: ${prometheus_config}"

        # Validate configuration
        if docker run --rm -v "${prometheus_config}:/etc/prometheus/prometheus.yml" prom/prometheus:latest promtool check config /etc/prometheus/prometheus.yml 2>&1 | grep -q "SUCCESS"; then
            log_success "Prometheus configuration is valid"
        else
            log_error "Prometheus configuration validation failed"
            return 1
        fi
    else
        log_error "Prometheus config not found: ${prometheus_config}"
        return 1
    fi
}

# Configure Grafana datasources
configure_grafana_datasources() {
    log_info "Configuring Grafana datasources..."

    local datasource_file="${PROJECT_ROOT}/monitoring/grafana/datasources/prometheus.yml"

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure Grafana datasources"
        return 0
    fi

    cat > "${datasource_file}" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: "5s"
      queryTimeout: "60s"
      httpMethod: "POST"
    version: 1

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: postgres:5432
    database: ${POSTGRES_DB}
    user: ${POSTGRES_USER}
    secureJsonData:
      password: ${POSTGRES_PASSWORD}
    jsonData:
      sslmode: "disable"
      postgresVersion: 1500
    editable: true
    version: 1
EOF

    log_success "Grafana datasources configured: ${datasource_file}"
}

# Configure Grafana dashboards
configure_grafana_dashboards() {
    log_info "Configuring Grafana dashboards..."

    local dashboard_provider="${PROJECT_ROOT}/monitoring/grafana/dashboards/dashboards.yml"

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure Grafana dashboards"
        return 0
    fi

    # Dashboard provider configuration
    cat > "${dashboard_provider}" << 'EOF'
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # Create application dashboard
    local app_dashboard="${PROJECT_ROOT}/monitoring/grafana/dashboards/corporate-intel-app.json"

    cat > "${app_dashboard}" << 'EOF'
{
  "dashboard": {
    "title": "Corporate Intelligence Platform",
    "tags": ["application", "corporate-intel"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{path}}"
          }
        ]
      },
      {
        "id": 2,
        "title": "Response Time (P95)",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "P95 latency"
          }
        ]
      },
      {
        "id": 3,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m])",
            "legendFormat": "5xx errors"
          }
        ]
      },
      {
        "id": 4,
        "title": "Database Connections",
        "type": "graph",
        "targets": [
          {
            "expr": "pg_stat_database_numbackends",
            "legendFormat": "Active connections"
          }
        ]
      },
      {
        "id": 5,
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes",
            "legendFormat": "Memory usage"
          }
        ]
      },
      {
        "id": 6,
        "title": "CPU Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(process_cpu_seconds_total[5m])",
            "legendFormat": "CPU usage"
          }
        ]
      }
    ]
  }
}
EOF

    log_success "Grafana dashboards configured"
}

# Configure Alertmanager
configure_alertmanager() {
    log_info "Configuring Alertmanager..."

    local alertmanager_config="${PROJECT_ROOT}/monitoring/alertmanager/alertmanager.yml"

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure Alertmanager"
        return 0
    fi

    cat > "${alertmanager_config}" << 'EOF'
global:
  resolve_timeout: 5m
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@corporate-intel.example.com'
  smtp_auth_username: ''
  smtp_auth_password: ''

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: 'critical'
      continue: true
    - match:
        severity: warning
      receiver: 'warning'

receivers:
  - name: 'default'
    webhook_configs:
      - url: 'http://localhost:5001/alerts'

  - name: 'critical'
    email_configs:
      - to: 'oncall@corporate-intel.example.com'
        headers:
          Subject: '[CRITICAL] Corporate Intel Alert'
    webhook_configs:
      - url: 'http://localhost:5001/alerts/critical'

  - name: 'warning'
    email_configs:
      - to: 'team@corporate-intel.example.com'
        headers:
          Subject: '[WARNING] Corporate Intel Alert'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'cluster', 'service']
EOF

    log_success "Alertmanager configured: ${alertmanager_config}"
}

# Configure alert rules
configure_alert_rules() {
    log_info "Configuring Prometheus alert rules..."

    local rules_file="${PROJECT_ROOT}/monitoring/prometheus/alerts.yml"

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would configure alert rules"
        return 0
    fi

    cat > "${rules_file}" << 'EOF'
groups:
  - name: corporate_intel_alerts
    interval: 30s
    rules:
      # API Health Alerts
      - alert: APIDown
        expr: up{job="corporate-intel-api"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "API is down"
          description: "Corporate Intelligence API has been down for more than 1 minute."

      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} over the last 5 minutes."

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times"
          description: "P95 response time is {{ $value }}s (threshold: 1s)."

      # Database Alerts
      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
          description: "PostgreSQL database has been down for more than 1 minute."

      - alert: HighDatabaseConnections
        expr: pg_stat_database_numbackends > 180
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High database connection count"
          description: "Database has {{ $value }} active connections (threshold: 180)."

      - alert: DatabaseSlowQueries
        expr: rate(pg_stat_statements_mean_time_seconds[5m]) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Slow database queries detected"
          description: "Average query time is {{ $value }}s."

      # Resource Alerts
      - alert: HighMemoryUsage
        expr: (process_resident_memory_bytes / 1e9) > 4
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value }}GB (threshold: 4GB)."

      - alert: HighCPUUsage
        expr: rate(process_cpu_seconds_total[5m]) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
          description: "CPU usage is {{ $value | humanizePercentage }}."

      # Disk Alerts
      - alert: LowDiskSpace
        expr: (node_filesystem_avail_bytes / node_filesystem_size_bytes) < 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Low disk space"
          description: "Disk space is below 10% ({{ $value | humanizePercentage }} free)."

      # Redis Alerts
      - alert: RedisDown
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Redis is down"
          description: "Redis cache has been down for more than 1 minute."

      # Container Alerts
      - alert: ContainerRestarting
        expr: rate(container_restart_count[15m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container is restarting"
          description: "Container {{ $labels.name }} is restarting frequently."
EOF

    log_success "Alert rules configured: ${rules_file}"
}

# Start monitoring services
start_monitoring_services() {
    log_info "Starting monitoring services..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would start monitoring services"
        return 0
    fi

    local compose_file="docker-compose.${ENVIRONMENT}.yml"

    if [ ! -f "${PROJECT_ROOT}/${compose_file}" ]; then
        log_error "Compose file not found: ${compose_file}"
        return 1
    fi

    cd "${PROJECT_ROOT}"

    # Start monitoring stack
    log_info "Starting Prometheus, Grafana, and Alertmanager..."
    docker-compose -f "${compose_file}" up -d prometheus grafana alertmanager

    # Wait for services
    sleep 10

    # Check if services are running
    local services=("prometheus" "grafana")
    for service in "${services[@]}"; do
        if docker-compose -f "${compose_file}" ps "${service}" | grep -q "Up"; then
            log_success "${service} is running"
        else
            log_error "${service} failed to start"
            return 1
        fi
    done
}

# Validate monitoring setup
validate_monitoring() {
    log_info "Validating monitoring setup..."

    if [ "${DRY_RUN}" = true ]; then
        log_info "[DRY RUN] Would validate monitoring"
        return 0
    fi

    local validation_failures=0

    # Check Prometheus
    log_info "Checking Prometheus..."
    if curl -sf "http://localhost:${PROMETHEUS_PORT}/-/healthy" > /dev/null; then
        log_success "Prometheus is healthy"

        # Check targets
        local targets=$(curl -s "http://localhost:${PROMETHEUS_PORT}/api/v1/targets" | grep -o '"health":"up"' | wc -l)
        log_info "Prometheus has ${targets} healthy targets"
    else
        log_error "Prometheus health check failed"
        validation_failures=$((validation_failures + 1))
    fi

    # Check Grafana
    log_info "Checking Grafana..."
    if curl -sf "http://localhost:${GRAFANA_PORT}/api/health" > /dev/null; then
        log_success "Grafana is healthy"
    else
        log_error "Grafana health check failed"
        validation_failures=$((validation_failures + 1))
    fi

    # Check Alertmanager (if configured)
    if [ -f "${PROJECT_ROOT}/monitoring/alertmanager/alertmanager.yml" ]; then
        log_info "Checking Alertmanager..."
        if curl -sf "http://localhost:${ALERTMANAGER_PORT}/-/healthy" > /dev/null 2>&1; then
            log_success "Alertmanager is healthy"
        else
            log_warning "Alertmanager health check failed (may not be deployed)"
        fi
    fi

    if [ ${validation_failures} -gt 0 ]; then
        log_error "Monitoring validation failed: ${validation_failures} issues"
        return 1
    fi

    log_success "Monitoring setup validated successfully"
}

# Generate monitoring setup report
generate_monitoring_report() {
    log_info "Generating monitoring setup report..."

    local report_file="${PROJECT_ROOT}/logs/monitoring-setup-report-$(date +%Y%m%d_%H%M%S).txt"

    cat > "${report_file}" << EOF
===============================================================================
MONITORING SETUP REPORT
===============================================================================

Setup Date: $(date '+%Y-%m-%d %H:%M:%S %Z')
Script Version: ${SCRIPT_VERSION}
Environment: ${ENVIRONMENT}

SERVICES
--------
Prometheus:     http://localhost:${PROMETHEUS_PORT}
Grafana:        http://localhost:${GRAFANA_PORT}
Alertmanager:   http://localhost:${ALERTMANAGER_PORT}

CONFIGURATION FILES
-------------------
Prometheus Config:      ${PROJECT_ROOT}/config/prometheus.yml
Alert Rules:            ${PROJECT_ROOT}/monitoring/prometheus/alerts.yml
Grafana Datasources:    ${PROJECT_ROOT}/monitoring/grafana/datasources/
Grafana Dashboards:     ${PROJECT_ROOT}/monitoring/grafana/dashboards/
Alertmanager Config:    ${PROJECT_ROOT}/monitoring/alertmanager/alertmanager.yml

GRAFANA CREDENTIALS
-------------------
Username: admin
Password: \${GRAFANA_PASSWORD} (from environment)

NEXT STEPS
----------
1. Access Grafana at http://localhost:${GRAFANA_PORT}
2. Login with admin credentials
3. Verify datasources are connected
4. Review dashboards
5. Configure alert notification channels
6. Test alert rules

MONITORING CHECKLIST
--------------------
☐ Verify Prometheus is scraping all targets
☐ Import additional Grafana dashboards if needed
☐ Configure email/Slack for Alertmanager
☐ Set up alert notification channels
☐ Test alert firing and notifications
☐ Review and adjust alert thresholds
☐ Set up log aggregation (if not configured)

===============================================================================
EOF

    log_success "Monitoring setup report: ${report_file}"
    cat "${report_file}"
}

# Main setup flow
main() {
    log_info "=========================================="
    log_info "Monitoring Setup"
    log_info "Corporate Intelligence Platform"
    log_info "=========================================="
    log_info ""

    mkdir -p "$(dirname "${LOG_FILE}")"

    parse_args "$@"

    log_info "Setting up monitoring for ${ENVIRONMENT} environment..."
    log_info ""

    create_monitoring_config_dir
    configure_prometheus
    configure_grafana_datasources
    configure_grafana_dashboards
    configure_alertmanager
    configure_alert_rules
    start_monitoring_services
    validate_monitoring

    log_info ""
    log_success "=========================================="
    log_success "MONITORING SETUP COMPLETE"
    log_success "=========================================="
    log_info ""

    if [ "${DRY_RUN}" = false ]; then
        generate_monitoring_report
    fi

    log_info "Access monitoring services:"
    log_info "  Prometheus: http://localhost:${PROMETHEUS_PORT}"
    log_info "  Grafana: http://localhost:${GRAFANA_PORT}"
    log_info "  Alertmanager: http://localhost:${ALERTMANAGER_PORT}"
}

main "$@"
