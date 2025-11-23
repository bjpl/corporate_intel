# Production Monitoring Dashboard Requirements

## Dashboard Overview

This document defines the required monitoring dashboards for production operations, SLO tracking, and incident response.

## 1. Executive Dashboard (High-Level KPIs)

### Purpose
Real-time business and operational health at a glance for stakeholders.

### Metrics

**System Health**
- Overall system uptime (monthly %)
- Active users (current, daily, monthly)
- Request volume (requests/minute)
- Error rate (% of total requests)
- Average response time (95th percentile)

**Business KPIs**
- Data ingestion rate (records/hour)
- API calls by endpoint (top 10)
- Active companies tracked
- Reports generated (daily)
- Search queries performed

**Resource Utilization**
- CPU usage (% across all services)
- Memory usage (% across all services)
- Disk space remaining (%)
- Network throughput (MB/s)

### Panels

```
┌────────────────────────────────────────────────────────────────┐
│ CORPORATE INTEL PLATFORM - EXECUTIVE DASHBOARD                 │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Uptime: 99.95%    Active Users: 127    Requests: 1.2K/min    │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Error Rate   │  │ Response Time│  │ Data Ingestion       │ │
│  │              │  │              │  │                      │ │
│  │    0.2%      │  │   245ms      │  │  15K records/hour    │ │
│  │  (24h avg)   │  │  (p95)       │  │                      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                 │
│  Request Volume (24h)                                           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │                          /\                             │   │
│  │                    /\   /  \      /\                    │   │
│  │               /\  /  \ /    \    /  \                   │   │
│  │          /\  /  \/    ´      \  /    \    /\            │   │
│  │    /\   /  \/                 \/      \  /  \     /\    │   │
│  │___/  \_/                               \/    \___/  \___│   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Top API Endpoints (by volume)                                 │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ 1. /api/v1/companies/search       45%  ████████████    │   │
│  │ 2. /api/v1/financial-metrics      22%  ██████          │   │
│  │ 3. /api/v1/news/company           18%  █████           │   │
│  │ 4. /api/v1/reports/generate       10%  ███             │   │
│  │ 5. /api/v1/auth/login             5%   █               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Service Status                                                 │
│  ┌─────────────┬─────────────┬─────────────┬────────────────┐ │
│  │ API         │ Database    │ Cache       │ Storage        │ │
│  │ ✓ Healthy   │ ✓ Healthy   │ ✓ Healthy   │ ✓ Healthy      │ │
│  │ 3 instances │ Primary+2   │ Master+2    │ 3 nodes        │ │
│  └─────────────┴─────────────┴─────────────┴────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

### Grafana Configuration

```json
{
  "dashboard": {
    "title": "Executive Dashboard",
    "refresh": "30s",
    "panels": [
      {
        "title": "System Uptime",
        "type": "stat",
        "targets": [
          {
            "expr": "avg_over_time(up{job=\"corporate-intel-api\"}[30d]) * 100"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m])) * 100"
          }
        ],
        "thresholds": [
          { "value": 1, "color": "green" },
          { "value": 5, "color": "yellow" },
          { "value": 10, "color": "red" }
        ]
      }
    ]
  }
}
```

## 2. API Performance Dashboard

### Purpose
Detailed API performance metrics for troubleshooting and optimization.

### Metrics

**Request Metrics**
- Requests per second (by endpoint)
- Response time distribution (p50, p90, p95, p99)
- Error rates (by status code)
- Request size distribution
- Response size distribution

**Performance Breakdown**
- Database query time
- Cache hit/miss ratio
- External API call duration
- Data processing time
- Queue wait time

### Queries

```promql
# Request rate by endpoint
sum(rate(http_requests_total[5m])) by (path)

# Response time (95th percentile)
histogram_quantile(0.95,
  sum(rate(http_request_duration_seconds_bucket[5m])) by (le, path)
)

# Error rate by status code
sum(rate(http_requests_total{status=~"4..|5.."}[5m])) by (status)

# Cache hit ratio
sum(rate(redis_keyspace_hits_total[5m])) /
(sum(rate(redis_keyspace_hits_total[5m])) + sum(rate(redis_keyspace_misses_total[5m])))

# Database query performance
rate(pg_stat_statements_total_time[5m]) / rate(pg_stat_statements_calls[5m])
```

## 3. Infrastructure Dashboard

### Purpose
Monitor system resources and capacity planning.

### Metrics

**Compute Resources**
- CPU usage (per container, per host)
- Memory usage (per container, per host)
- Disk I/O (read/write IOPS)
- Network I/O (bytes in/out)

**Container Metrics**
- Container count (running, stopped)
- Container restart count
- Container CPU throttling
- Container memory limits

**Host Metrics**
- Load average (1m, 5m, 15m)
- Disk space usage
- Inode usage
- Network connections

### Panels

```
┌────────────────────────────────────────────────────────────────┐
│ INFRASTRUCTURE METRICS                                          │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CPU Usage by Service                                           │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ API          ████████████████░░░░░░  65%               │   │
│  │ PostgreSQL   ████████████░░░░░░░░░░  55%               │   │
│  │ Redis        ████░░░░░░░░░░░░░░░░░░  20%               │   │
│  │ Prometheus   ██████░░░░░░░░░░░░░░░░  30%               │   │
│  │ NGINX        ██░░░░░░░░░░░░░░░░░░░░  10%               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Memory Usage by Service                                        │
│  ┌────────────────────────────────────────────────────────┐   │
│  │ API          ████████████████████░░░  75% (3.0/4.0 GB) │   │
│  │ PostgreSQL   ████████████████░░░░░░░  70% (2.8/4.0 GB) │   │
│  │ Redis        ████████████░░░░░░░░░░░  60% (2.4/4.0 GB) │   │
│  │ MinIO        ███████░░░░░░░░░░░░░░░░  35% (0.7/2.0 GB) │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Disk I/O                                Network I/O            │
│  ┌─────────────────────┐  ┌──────────────────────────────┐   │
│  │ Read:  125 MB/s     │  │ In:  45 Mbps   Out: 32 Mbps  │   │
│  │ Write: 85 MB/s      │  │ Connections: 432              │   │
│  └─────────────────────┘  └──────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

## 4. Database Dashboard

### Purpose
Monitor database health, performance, and capacity.

### Metrics

**Connection Metrics**
- Active connections
- Idle connections
- Connection pool saturation
- Connection errors
- Long-running queries

**Query Performance**
- Query execution time (by query)
- Slow query count (>1s)
- Lock wait time
- Transaction rate
- Rollback rate

**Storage Metrics**
- Database size
- Table sizes (top 10)
- Index usage
- Bloat estimation
- WAL generation rate

**Replication**
- Replication lag (seconds)
- Replication slot status
- WAL sender/receiver status

### Critical Queries

```sql
-- Active connections by state
SELECT state, count(*)
FROM pg_stat_activity
WHERE datname = 'corporate_intel_prod'
GROUP BY state;

-- Slow queries (>1s)
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;

-- Table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;

-- Index usage
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan,
  idx_tup_read,
  idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

## 5. Alert Dashboard

### Purpose
Centralized view of all active alerts and their history.

### Sections

**Active Alerts**
- Alert name
- Severity (critical, warning, info)
- Service affected
- Duration
- Description
- Runbook link

**Alert History**
- Alerts fired (last 24h)
- Mean time to resolution
- Alert frequency
- Most common alerts

**Alert Performance**
- False positive rate
- Alert response time
- Escalation rate

### Alert Rules Priority

```yaml
Priority 1 - Critical (Page immediately):
  - API down (all instances)
  - Database down
  - Data loss detected
  - Security breach

Priority 2 - High (Page during business hours):
  - High error rate (>5%)
  - High latency (>1s p95)
  - Memory usage >90%
  - Disk space <10%

Priority 3 - Medium (Email/Slack):
  - Cache evictions
  - Slow queries
  - High CPU usage
  - Replication lag

Priority 4 - Low (Daily digest):
  - Certificate expiring (>7 days)
  - Backup completed
  - Info notifications
```

## 6. Business Metrics Dashboard

### Purpose
Track business-relevant metrics and usage patterns.

### Metrics

**Usage Metrics**
- Daily active users
- API calls per user
- Popular endpoints
- Search patterns
- Report generation frequency

**Data Metrics**
- Companies tracked
- Financial records ingested
- News articles indexed
- SEC filings processed
- Data freshness (age of latest data)

**Performance Indicators**
- Search quality (click-through rate)
- Data accuracy (validation pass rate)
- User engagement (session duration)
- Feature adoption (new vs. existing features)

## 7. SLO Dashboard

### Purpose
Track Service Level Objectives and error budgets.

### SLOs Defined

```yaml
API Availability:
  Target: 99.9% uptime
  Measurement Window: 30 days
  Error Budget: 43.2 minutes/month

API Latency:
  Target: 95% of requests < 500ms
  Measurement Window: 7 days

Error Rate:
  Target: < 1% of requests
  Measurement Window: 24 hours

Data Freshness:
  Target: < 1 hour data lag
  Measurement Window: Real-time
```

### Burn Rate Alerts

```promql
# Fast burn (alerts in 1 hour)
(1 - (sum(rate(http_requests_total{status!~"5.."}[1h])) /
      sum(rate(http_requests_total[1h])))) > 14.4 * 0.001

# Slow burn (alerts in 6 hours)
(1 - (sum(rate(http_requests_total{status!~"5.."}[6h])) /
      sum(rate(http_requests_total[6h])))) > 6 * 0.001
```

## 8. Security Dashboard

### Purpose
Monitor security events and compliance.

### Metrics

**Authentication**
- Failed login attempts
- Successful logins
- Token generations
- Session expirations
- Password resets

**Access Patterns**
- Unusual access times
- Geographic anomalies
- High-frequency requests
- Privilege escalations

**Security Events**
- Firewall blocks
- Rate limit violations
- SQL injection attempts
- XSS attempts
- Suspicious queries

## Dashboard Access & Permissions

### Role-Based Access

```yaml
Executive:
  - Executive Dashboard
  - Business Metrics Dashboard
  - SLO Dashboard

Operations:
  - All Dashboards
  - Edit Permissions

Engineering:
  - API Performance Dashboard
  - Infrastructure Dashboard
  - Database Dashboard
  - Alert Dashboard

Security:
  - Security Dashboard
  - Alert Dashboard

Read-Only:
  - Executive Dashboard
  - SLO Dashboard
```

## Dashboard Maintenance

### Update Schedule
- Daily: Review and adjust alert thresholds
- Weekly: Add new metrics based on incidents
- Monthly: Archive unused dashboards
- Quarterly: Review SLOs and adjust targets

### Best Practices
1. Keep dashboards focused (max 12 panels)
2. Use consistent color schemes
3. Add descriptions to all panels
4. Include runbook links
5. Set appropriate refresh intervals
6. Use template variables for flexibility
7. Document query logic
8. Test alerts before deployment
