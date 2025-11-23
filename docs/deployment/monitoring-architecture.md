# Monitoring & Alerting Architecture

## Overview

The Corporate Intelligence Platform monitoring infrastructure is built on the Prometheus ecosystem with Grafana for visualization, providing comprehensive observability across all system components.

## Architecture Components

### 1. Metrics Collection (Prometheus)

**Primary Components:**
- **Prometheus Server**: Central metrics collection and storage
- **Alertmanager**: Alert routing and notification management
- **Exporters**: Specialized metric collectors for various services

**Configuration:**
- Location: `config/production/prometheus/`
- Retention: 60 days (configurable in prometheus.yml)
- Scrape Interval: 15-30s (varies by job)
- Storage: TSDB with 100GB limit

**Metrics Sources:**

| Service | Exporter | Port | Metrics |
|---------|----------|------|---------|
| API | Built-in /metrics | 8000 | HTTP requests, latency, errors |
| PostgreSQL | postgres-exporter | 9187 | Connections, queries, replication |
| Redis | redis-exporter | 9121 | Memory, cache hits, connections |
| System | node-exporter | 9100 | CPU, memory, disk, network |
| Containers | cAdvisor | 8080 | Container resources, health |
| Nginx | nginx-exporter | 9113 | HTTP traffic, upstream status |

### 2. Visualization (Grafana)

**Dashboards:**
1. **API Performance** - Request rates, latency percentiles, error rates
2. **Database Metrics** - Connection pools, query performance, replication lag
3. **Redis Metrics** - Cache hit ratios, memory usage, evictions
4. **System Overview** - CPU, memory, disk, network by host
5. **External APIs** - SEC, Yahoo Finance, Alpha Vantage health
6. **Data Pipelines** - Pipeline execution, data quality, freshness

**Configuration:**
- Location: `config/production/grafana/`
- Provisioning: Automated dashboard deployment
- Data Source: Prometheus
- Access: http://grafana:3000 (behind nginx proxy)

### 3. Distributed Tracing (Jaeger)

**Purpose:**
- End-to-end request tracing
- Performance bottleneck identification
- Service dependency mapping

**Integration:**
- OpenTelemetry SDK in API
- OTLP protocol (gRPC port 4317, HTTP port 4318)
- Storage: Badger (embedded DB)
- UI: http://jaeger:16686

### 4. Error Tracking (Sentry)

**Purpose:**
- Application error tracking
- Stack trace analysis
- Release tracking

**Configuration:**
- Environment variable: `SENTRY_DSN`
- Release tracking enabled
- Error sampling: 100% in production

## Alert Rules

### Alert Categories

**1. API Alerts** (`config/production/prometheus/alerts/api-alerts.yml`)
- High error rate (>1% for 5m) - Critical
- High latency P99 (>100ms for 5m) - Critical
- Service down (>2m) - Critical (Page)
- High request rate (>1000 req/s) - Warning
- Low request rate (<1 req/s for 15m) - Warning

**2. Database Alerts** (`config/production/prometheus/alerts/database-alerts.yml`)
- Connection pool usage (>80% for 5m) - Critical
- Slow queries (>1s for 10m) - Warning
- Replication lag (>30s for 5m) - Critical
- Database down (>2m) - Critical (Page)
- Low cache hit ratio (<90% for 15m) - Warning

**3. Redis Alerts** (`config/production/prometheus/alerts/redis-alerts.yml`)
- High memory usage (>90% for 5m) - Critical
- Low cache hit ratio (<80% for 15m) - Warning
- Redis down (>2m) - Critical (Page)
- Replication broken (>5m) - Critical
- Persistence failure (>1h) - Critical

**4. System Alerts** (`config/production/prometheus/alerts/system-alerts.yml`)
- High disk usage (>85% for 10m) - Critical
- High memory usage (>90% for 10m) - Critical
- High CPU usage (>85% for 15m) - Warning
- Node exporter down (>5m) - Warning

**5. External API Alerts** (`config/production/prometheus/alerts/external-api-alerts.yml`)
- SEC API error rate (>5% for 15m) - Critical
- SEC API rate limiting (>5 in 10m) - Warning
- Alpha Vantage quota exhausted (<10 calls) - Critical
- Circuit breaker open (>5m) - Critical

**6. Pipeline Alerts** (`config/production/prometheus/alerts/pipeline-alerts.yml`)
- Pipeline execution failure - Critical
- Missed schedule (>2h late) - Critical
- Data quality check failure - Critical
- Stale data (>24h old) - Warning

**7. Backup Alerts** (`config/production/prometheus/alerts/backup-alerts.yml`)
- Backup failure (>24h since last) - Critical (Page)
- Backup storage low (<20% free) - Critical
- Backup verification failure - Critical

### Alert Severity Levels

| Severity | Response Time | Notification | Examples |
|----------|--------------|--------------|----------|
| **Critical** | Immediate | PagerDuty + Slack | Service down, data loss risk |
| **Warning** | 1 hour | Slack | High resource usage, degraded performance |
| **Info** | Best effort | Slack | Deployment notifications, non-urgent issues |

## Alerting Workflow

### Alert Routing

```yaml
Route Hierarchy:
├── Critical (severity: critical)
│   ├── PagerDuty (page on-call)
│   └── Slack #alerts-critical
├── Warning (severity: warning)
│   └── Slack #alerts-warnings
├── Component-specific
│   ├── API → #team-api
│   ├── Database → #team-database
│   └── System → #team-devops
```

### Notification Channels

**PagerDuty:**
- Service Key: `${PAGERDUTY_SERVICE_KEY}`
- Used for: Critical alerts only
- Escalation: On-call engineer → Senior engineer → CTO

**Slack:**
- `#alerts-critical` - Critical severity, all hands
- `#alerts-warnings` - Warning severity, team awareness
- `#team-api` - API-specific issues
- `#team-database` - Database-specific issues
- `#team-devops` - System/infrastructure issues

**Email:**
- Default fallback: devops@corporate-intel.com
- Used when other channels fail

### Alert Inhibition

Configured to prevent alert storms:

```yaml
# Don't alert on service components if entire service is down
APIServiceDown → Suppresses all API component alerts
DatabaseDown → Suppresses all database alerts
RedisDown → Suppresses all Redis alerts

# Don't alert on metrics if exporter is down
NodeExporterDown → Suppresses system metric alerts for that node
```

## Metrics Cardinality Management

### High-Cardinality Labels (Avoid)
- ❌ User IDs
- ❌ Request IDs
- ❌ Session tokens
- ❌ Timestamps
- ❌ Full URLs with query parameters

### Good Labels (Use)
- ✅ Service name
- ✅ Environment (prod, staging)
- ✅ HTTP method
- ✅ Status code (grouped: 2xx, 4xx, 5xx)
- ✅ Endpoint (route template, not full path)
- ✅ Instance/host

### Label Best Practices

```python
# ❌ BAD - High cardinality
http_requests_total{user_id="12345", request_id="abc-def-ghi", timestamp="1234567890"}

# ✅ GOOD - Bounded cardinality
http_requests_total{service="api", method="GET", status="200", endpoint="/api/companies"}
```

## Performance Considerations

### Prometheus Query Optimization

**Avoid:**
```promql
# Slow - High cardinality aggregation
sum(rate(http_requests_total[5m])) by (path, user_id, session_id)

# Slow - Long time ranges without aggregation
http_requests_total[30d]
```

**Prefer:**
```promql
# Fast - Bounded cardinality
sum(rate(http_requests_total[5m])) by (service, status)

# Fast - Pre-aggregated over time
sum(rate(http_requests_total[5m]))
```

### Storage Management

**Retention Strategy:**
- **Raw metrics**: 60 days in Prometheus
- **Aggregated metrics**: 1 year (via remote write to long-term storage)
- **Alert history**: 90 days in Alertmanager

**Disk Space Requirements:**
- Prometheus: ~1-2GB per day (estimated)
- Grafana: ~500MB (dashboards, users, settings)
- Jaeger: ~5GB per week (traces)

## Service Level Objectives (SLOs)

### API SLOs

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Availability | 99.9% | 30 days |
| P95 Latency | < 75ms | 5 minutes |
| P99 Latency | < 100ms | 5 minutes |
| Error Rate | < 0.1% | 5 minutes |

### Data Pipeline SLOs

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Pipeline Success Rate | 99.5% | 30 days |
| Data Freshness | < 4 hours | Real-time |
| Data Quality | > 99.9% | Per run |

### Database SLOs

| Metric | Target | Measurement Window |
|--------|--------|-------------------|
| Query Latency (P95) | < 10ms | 5 minutes |
| Connection Pool Availability | > 20% free | 5 minutes |
| Replication Lag | < 5 seconds | Real-time |

## Monitoring Best Practices

### 1. Instrument Everything
- Add metrics at service boundaries
- Measure business KPIs, not just technical metrics
- Include both RED (Rate, Errors, Duration) and USE (Utilization, Saturation, Errors) metrics

### 2. Use the Four Golden Signals
- **Latency**: How long it takes to service a request
- **Traffic**: How much demand is placed on your system
- **Errors**: The rate of requests that fail
- **Saturation**: How "full" your service is

### 3. Alert on Symptoms, Not Causes
- ✅ "API error rate is high" (symptom, user-facing)
- ❌ "CPU is at 80%" (cause, may not impact users)

### 4. Write Runbooks for All Alerts
- Every alert should have an associated runbook
- Runbooks should include:
  - What the alert means
  - How to verify the issue
  - Common causes and solutions
  - Escalation procedures

### 5. Test Your Monitoring
- Regularly trigger test alerts
- Verify alert routing works
- Conduct failure injection tests
- Review and update dashboards quarterly

## Troubleshooting

### Common Issues

**1. Prometheus Not Scraping Targets**
```bash
# Check targets status
curl http://prometheus:9090/api/v1/targets

# Check Prometheus logs
docker logs corporate-intel-prometheus

# Verify network connectivity
docker exec corporate-intel-prometheus nc -zv postgres-exporter 9187
```

**2. Grafana Dashboard Not Loading**
```bash
# Check Grafana logs
docker logs corporate-intel-grafana

# Verify Prometheus data source
curl http://grafana:3000/api/datasources

# Test Prometheus query
curl 'http://prometheus:9090/api/v1/query?query=up'
```

**3. Alerts Not Firing**
```bash
# Check Prometheus rules
curl http://prometheus:9090/api/v1/rules

# Check Alertmanager status
curl http://alertmanager:9093/api/v2/status

# View active alerts
curl http://alertmanager:9093/api/v2/alerts
```

**4. High Prometheus Memory Usage**
```bash
# Check TSDB stats
curl http://prometheus:9090/api/v1/status/tsdb

# Reduce retention period (edit prometheus.yml)
--storage.tsdb.retention.time=30d

# Add metric relabeling to drop unused metrics
```

## Security Considerations

### Authentication & Authorization
- Grafana: Username/password authentication, LDAP integration available
- Prometheus: Network isolation (only accessible via Grafana and localhost)
- Alertmanager: API authentication via bearer tokens

### Network Security
- All monitoring services on isolated Docker network
- Prometheus and Grafana only exposed via nginx reverse proxy
- TLS encryption for external connections
- Internal services use HTTP (network isolation provides security)

### Secrets Management
- Alert notification credentials stored in environment variables
- Loaded from `.env` file (not committed to git)
- Production secrets managed via HashiCorp Vault or AWS Secrets Manager

## Disaster Recovery

### Backing Up Monitoring Data

**Prometheus:**
```bash
# Snapshot Prometheus data
curl -XPOST http://prometheus:9090/api/v1/admin/tsdb/snapshot

# Backup snapshot
tar -czf prometheus-snapshot-$(date +%Y%m%d).tar.gz \
  /var/lib/docker/volumes/corporate-intel-prometheus-data/_data/snapshots/
```

**Grafana:**
```bash
# Export dashboards
for dashboard in $(curl -s 'http://admin:password@grafana:3000/api/search?query=&' | jq -r '.[].uid'); do
  curl -s "http://admin:password@grafana:3000/api/dashboards/uid/$dashboard" | jq . > "dashboard-$dashboard.json"
done

# Backup Grafana database
docker exec corporate-intel-grafana sqlite3 /var/lib/grafana/grafana.db ".backup '/tmp/grafana-backup.db'"
docker cp corporate-intel-grafana:/tmp/grafana-backup.db ./grafana-backup-$(date +%Y%m%d).db
```

### Recovery Procedures

See: [Disaster Recovery Plan](./disaster-recovery.md)

## Maintenance

### Regular Tasks

**Daily:**
- Review critical alerts
- Check dashboard for anomalies
- Verify backup monitoring alerts

**Weekly:**
- Review alert noise and adjust thresholds
- Check Prometheus storage usage
- Review slow queries and optimize

**Monthly:**
- Test alert routing and escalation
- Review and update dashboards
- Audit metric cardinality
- Clean up unused metrics

**Quarterly:**
- Full disaster recovery test
- Review and update SLOs
- Audit monitoring coverage
- Update runbooks with learnings

## Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Alertmanager Documentation](https://prometheus.io/docs/alerting/latest/alertmanager/)
- [Site Reliability Engineering Book](https://sre.google/books/)
- [Runbooks](../runbooks/)
- [Alert Configurations](../../config/production/prometheus/alerts/)

---

**Last Updated:** 2025-10-25
**Owner:** DevOps Team
**Reviewers:** SRE Team, Backend Team
