# Production Monitoring Setup Guide

## Overview

This document describes the production monitoring setup for Corporate Intel API using Prometheus and Grafana.

## Architecture

```
┌─────────────┐
│   Grafana   │ ← User Dashboard Access
└──────┬──────┘
       │
       ↓
┌─────────────┐     ┌──────────────┐
│ Prometheus  │────→│ Alertmanager │
└──────┬──────┘     └──────┬───────┘
       │                   │
       ├───────────────────┼──────────────────┐
       ↓                   ↓                  ↓
┌──────────┐      ┌─────────────┐    ┌──────────┐
│   API    │      │  PostgreSQL │    │  Redis   │
│ Servers  │      │   Exporter  │    │ Exporter │
└──────────┘      └─────────────┘    └──────────┘
```

## Components

### 1. Prometheus

**Purpose**: Metrics collection and storage

**Configuration**: `config/production/prometheus/prometheus.production.yml`

**Key Features**:
- 30-second scrape interval for most metrics
- 15-second interval for API metrics (critical path)
- 60-day retention period
- 100GB storage limit
- Metric relabeling to reduce cardinality
- Support for remote write (optional)

**Scraped Services**:
- Corporate Intel API (3 instances)
- PostgreSQL (primary + replica)
- Redis (master + 2 replicas)
- Node Exporter (system metrics)
- cAdvisor (container metrics)
- Nginx (load balancer)

### 2. Grafana

**Purpose**: Visualization and dashboards

**Configuration**: `config/production/grafana/`

**Pre-configured Dashboards**:

#### API Performance Dashboard
- **Location**: `dashboards/api-performance.json`
- **Metrics**:
  - Response time percentiles (P50, P95, P99)
  - Request rate by status code
  - Error rate percentage
  - Success rate percentage
  - Top 10 endpoints by traffic
  - Status code distribution
- **Refresh**: 30 seconds
- **Time Range**: Last 1 hour (default)

#### Database Metrics Dashboard
- **Location**: `dashboards/database-metrics.json`
- **Metrics**:
  - Connection pool usage
  - Cache hit ratio
  - Replication lag
  - Active connections
  - Transaction rate (commits/rollbacks)
  - Database size growth
  - Deadlock detection
- **Refresh**: 30 seconds

#### Redis Metrics Dashboard
- **Location**: `dashboards/redis-metrics.json`
- **Metrics**:
  - Memory usage
  - Cache hit ratio
  - Connected clients
  - Operations rate
  - Keys per database
  - Evictions and expirations
- **Refresh**: 30 seconds

### 3. Alertmanager

**Purpose**: Alert routing and notification

**Configuration**: `config/production/prometheus/alertmanager.yml`

**Notification Channels**:
- **Email**: Default catch-all (devops@corporate-intel.com)
- **PagerDuty**: Critical alerts only
- **Slack Channels**:
  - `#alerts-critical` - Critical alerts
  - `#alerts-warnings` - Warning-level alerts
  - `#team-api` - API-specific alerts
  - `#team-database` - Database alerts
  - `#team-devops` - System/infrastructure alerts

**Alert Routing**:
- Critical alerts → PagerDuty + Slack (immediate)
- Warning alerts → Slack only (grouped)
- Component-specific routing to team channels

**Inhibition Rules**:
- Suppress component alerts when service is down
- Suppress memory alerts when node is unreachable

## Alert Rules

### API Alerts (`alerts/api-alerts.yml`)

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighAPIErrorRate | >1% | 5 min | Critical |
| HighAPIClientErrorRate | >5% | 10 min | Warning |
| HighAPILatencyP99 | >100ms | 5 min | Critical |
| HighAPILatencyP95 | >75ms | 10 min | Warning |
| APIServiceDown | Service unreachable | 2 min | Critical |
| HighAPIRequestRate | >1000 req/s | 5 min | Warning |
| LowAPIRequestRate | <1 req/s | 15 min | Warning |
| SlowAPIEndpoint | P50 >50ms | 15 min | Warning |
| HighAPIMemoryUsage | >2GB | 10 min | Warning |
| APIRestarted | Process restart detected | - | Warning |

### Database Alerts (`alerts/database-alerts.yml`)

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighDatabaseConnectionPoolUsage | >80% | 5 min | Critical |
| DatabaseConnectionPoolWarning | >60% | 10 min | Warning |
| SlowDatabaseQueries | >1s avg | 10 min | Warning |
| HighDatabaseCPU | >80% | 10 min | Warning |
| DatabaseReplicationLag | >30s | 5 min | Critical |
| DatabaseDown | Service unreachable | 2 min | Critical |
| HighDatabaseTransactionRate | >10000 tx/s | 10 min | Warning |
| HighDatabaseRollbackRate | >5% | 10 min | Warning |
| DatabaseDeadlocks | >5 in 10 min | - | Warning |
| LowDatabaseCacheHitRatio | <90% | 15 min | Warning |
| HighDatabaseStorageUsage | >50GB | 1 hour | Warning |

### Redis Alerts (`alerts/redis-alerts.yml`)

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighRedisMemoryUsage | >90% | 5 min | Critical |
| RedisMemoryWarning | >75% | 10 min | Warning |
| LowRedisCacheHitRatio | <80% | 15 min | Warning |
| RedisDown | Service unreachable | 2 min | Critical |
| HighRedisConnections | >1000 clients | 10 min | Warning |
| RedisEvictions | >100 in 10 min | 5 min | Warning |
| RedisReplicationBroken | No replicas | 5 min | Critical |
| RedisReplicationLag | >10s | 5 min | Warning |
| HighRedisCPU | >80% | 10 min | Warning |
| RedisBlockedClients | >10 | 5 min | Warning |
| RedisPersistenceFailure | No save in 1 hour | 10 min | Critical |

### System Alerts (`alerts/system-alerts.yml`)

| Alert | Threshold | Duration | Severity |
|-------|-----------|----------|----------|
| HighDiskUsage | <15% free | 10 min | Critical |
| DiskUsageWarning | <25% free | 30 min | Warning |
| HighCPUUsage | >85% | 15 min | Warning |
| HighMemoryUsage | <10% available | 10 min | Critical |
| MemoryUsageWarning | <20% available | 15 min | Warning |
| HighDiskIO | >90% utilization | 10 min | Warning |
| HighNetworkTraffic | >100MB/s | 15 min | Warning |
| HighSystemLoad | >2x CPU cores | 15 min | Warning |
| NodeExporterDown | Exporter unreachable | 5 min | Warning |
| ClockSkew | >50ms offset | 10 min | Warning |
| HighFileDescriptorUsage | >80% | 10 min | Warning |

## Deployment

### Prerequisites

1. Docker and Docker Compose installed
2. Environment variables configured:
   - `SMTP_PASSWORD` - Email notification credentials
   - `PAGERDUTY_SERVICE_KEY` - PagerDuty integration key
   - `SLACK_WEBHOOK_CRITICAL` - Slack webhook for critical alerts
   - `SLACK_WEBHOOK_WARNINGS` - Slack webhook for warnings
   - `SLACK_WEBHOOK_API` - Slack webhook for API team
   - `SLACK_WEBHOOK_DATABASE` - Slack webhook for database team
   - `SLACK_WEBHOOK_DEVOPS` - Slack webhook for DevOps team

### Docker Compose Setup

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: prometheus
    volumes:
      - ./config/production/prometheus/prometheus.production.yml:/etc/prometheus/prometheus.yml
      - ./config/production/prometheus/alerts:/etc/prometheus/alerts
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=60d'
      - '--storage.tsdb.retention.size=100GB'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    restart: unless-stopped
    networks:
      - monitoring

  alertmanager:
    image: prom/alertmanager:v0.26.0
    container_name: alertmanager
    volumes:
      - ./config/production/prometheus/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - alertmanager-data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    restart: unless-stopped
    networks:
      - monitoring
    environment:
      - SMTP_PASSWORD=${SMTP_PASSWORD}
      - PAGERDUTY_SERVICE_KEY=${PAGERDUTY_SERVICE_KEY}
      - SLACK_WEBHOOK_CRITICAL=${SLACK_WEBHOOK_CRITICAL}
      - SLACK_WEBHOOK_WARNINGS=${SLACK_WEBHOOK_WARNINGS}
      - SLACK_WEBHOOK_API=${SLACK_WEBHOOK_API}
      - SLACK_WEBHOOK_DATABASE=${SLACK_WEBHOOK_DATABASE}
      - SLACK_WEBHOOK_DEVOPS=${SLACK_WEBHOOK_DEVOPS}

  grafana:
    image: grafana/grafana:10.0.0
    container_name: grafana
    volumes:
      - ./config/production/grafana/provisioning:/etc/grafana/provisioning
      - ./config/production/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_SERVER_ROOT_URL=https://grafana.corporate-intel.com
      - GF_INSTALL_PLUGINS=grafana-piechart-panel
    ports:
      - "3000:3000"
    restart: unless-stopped
    networks:
      - monitoring
    depends_on:
      - prometheus

  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.13.0
    container_name: postgres-exporter-primary
    environment:
      - DATA_SOURCE_NAME=postgresql://${DB_USER}:${DB_PASSWORD}@postgres-primary:5432/${DB_NAME}?sslmode=disable
    ports:
      - "9187:9187"
    restart: unless-stopped
    networks:
      - monitoring

  redis-exporter:
    image: oliver006/redis_exporter:v1.52.0
    container_name: redis-exporter-master
    environment:
      - REDIS_ADDR=redis-master:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "9121:9121"
    restart: unless-stopped
    networks:
      - monitoring

  node-exporter:
    image: prom/node-exporter:v1.6.0
    container_name: node-exporter
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
      - '--path.rootfs=/rootfs'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    ports:
      - "9100:9100"
    restart: unless-stopped
    networks:
      - monitoring

volumes:
  prometheus-data:
  alertmanager-data:
  grafana-data:

networks:
  monitoring:
    driver: bridge
```

### Startup Commands

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Check service status
docker-compose -f docker-compose.monitoring.yml ps

# View logs
docker-compose -f docker-compose.monitoring.yml logs -f prometheus
docker-compose -f docker-compose.monitoring.yml logs -f grafana
docker-compose -f docker-compose.monitoring.yml logs -f alertmanager

# Reload Prometheus configuration (no downtime)
curl -X POST http://localhost:9090/-/reload

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check active alerts
curl http://localhost:9090/api/v1/alerts
```

## Accessing Dashboards

### Prometheus
- **URL**: http://localhost:9090 (or https://prometheus.corporate-intel.com)
- **Features**:
  - Query interface (PromQL)
  - Target health status
  - Alert rule status
  - Configuration viewer

### Grafana
- **URL**: http://localhost:3000 (or https://grafana.corporate-intel.com)
- **Default Credentials**: admin / (set via GRAFANA_ADMIN_PASSWORD)
- **Dashboards**:
  - Production → Corporate Intel - API Performance
  - Production → Corporate Intel - Database Metrics
  - Production → Corporate Intel - Redis Metrics

### Alertmanager
- **URL**: http://localhost:9093 (or https://alertmanager.corporate-intel.com)
- **Features**:
  - Active alerts view
  - Silence management
  - Configuration status

## Monitoring Endpoints

### API Metrics Endpoint
```
http://api-instance:8000/metrics
```

**Exposed Metrics**:
- `http_request_duration_seconds` - Request latency histogram
- `http_requests_total` - Total request counter
- `http_request_size_bytes` - Request size histogram
- `http_response_size_bytes` - Response size histogram
- `api_business_metrics_*` - Custom business metrics
- `db_query_duration_seconds` - Database query performance
- `cache_hit_ratio` - Redis cache effectiveness

### Database Metrics
```
http://postgres-exporter:9187/metrics
```

### Redis Metrics
```
http://redis-exporter:9121/metrics
```

### System Metrics
```
http://node-exporter:9100/metrics
```

## Troubleshooting

### Prometheus Not Scraping Targets

```bash
# Check target status
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Verify network connectivity
docker exec prometheus wget -O- http://api-1:8000/metrics

# Check Prometheus logs
docker logs prometheus --tail 100
```

### Alerts Not Firing

```bash
# Check alert rules
curl http://localhost:9090/api/v1/rules | jq

# Verify Alertmanager connectivity
curl http://localhost:9090/api/v1/alertmanagers

# Test alert expression
curl -G http://localhost:9090/api/v1/query --data-urlencode 'query=up{job="corporate-intel-api"}'
```

### Grafana Dashboard Not Loading

```bash
# Check datasource
curl http://localhost:3000/api/datasources

# Verify Prometheus connectivity from Grafana
docker exec grafana wget -O- http://prometheus:9090/api/v1/query?query=up

# Re-provision dashboards
docker exec grafana ls -la /etc/grafana/provisioning/dashboards
```

## Best Practices

1. **Regular Review**: Review dashboards and alerts weekly
2. **Alert Tuning**: Adjust thresholds based on actual performance patterns
3. **Capacity Planning**: Monitor trends to predict scaling needs
4. **Retention**: Adjust retention period based on storage capacity
5. **Backups**: Regularly backup Prometheus data and Grafana configurations
6. **Security**: Use TLS for all monitoring endpoints in production
7. **Authentication**: Enable authentication for all monitoring UIs
8. **Documentation**: Keep runbooks updated for alert responses

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [PromQL Tutorial](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)

## Support

For monitoring-related issues:
- DevOps Team: devops@corporate-intel.com
- Slack: #team-devops
- On-call: PagerDuty escalation policy
