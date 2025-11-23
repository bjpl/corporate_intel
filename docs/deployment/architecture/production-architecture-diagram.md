# Corporate Intelligence Platform - Production Architecture

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         INTERNET / PUBLIC NETWORK                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ HTTPS (443)
                                 │ HTTP (80) → Redirect to HTTPS
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         EDGE / LOAD BALANCER LAYER                       │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────────┐     │
│  │  NGINX Reverse Proxy (SSL/TLS Termination)                     │     │
│  │  - Rate Limiting (100 req/min)                                 │     │
│  │  - SSL Certificate Management (Let's Encrypt)                  │     │
│  │  - Static Asset Caching                                        │     │
│  │  - Request Routing & Load Distribution                         │     │
│  │  - Security Headers (HSTS, CSP, X-Frame-Options)               │     │
│  └────────────────────────────────────────────────────────────────┘     │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ Internal Network (172.20.1.0/24)
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER (Frontend)                      │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  Corporate Intel API (FastAPI)                              │        │
│  │  ┌──────────────┬──────────────┬──────────────────────┐     │        │
│  │  │ API Instance │ API Instance │ API Instance         │     │        │
│  │  │   (Primary)  │  (Secondary) │  (Auto-scaled)       │     │        │
│  │  │   Port 8000  │  Port 8000   │  Port 8000           │     │        │
│  │  │              │              │                      │     │        │
│  │  │ Features:                                          │     │        │
│  │  │ - REST API Endpoints                               │     │        │
│  │  │ - Real-time Data Ingestion                         │     │        │
│  │  │ - Data Quality Validation                          │     │        │
│  │  │ - Anomaly Detection                                │     │        │
│  │  │ - OpenTelemetry Tracing                            │     │        │
│  │  └──────────────┴──────────────┴──────────────────────┘     │        │
│  └─────────────────────────────────────────────────────────────┘        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      DATA / BACKEND LAYER (172.20.2.0/24)               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌───────────────────────────┐  ┌──────────────────────────────────┐   │
│  │  PostgreSQL 15            │  │  Redis 7                         │   │
│  │  + TimescaleDB            │  │  (Distributed Cache)             │   │
│  │                           │  │                                  │   │
│  │  - Primary Database       │  │  - API Response Cache            │   │
│  │  - Time-series Data       │  │  - Session Management            │   │
│  │  - Financial Metrics      │  │  - Rate Limit Counters           │   │
│  │  - News & SEC Filings     │  │  - Task Queue Backend            │   │
│  │  - Vector Embeddings      │  │                                  │   │
│  │    (pgvector)             │  │  Max Memory: 4GB                 │   │
│  │                           │  │  Eviction: allkeys-lru           │   │
│  │  Connections: 200         │  │  Persistence: AOF + RDB          │   │
│  │  Shared Buffers: 2GB      │  │                                  │   │
│  │  Effective Cache: 6GB     │  └──────────────────────────────────┘   │
│  │                           │                                          │
│  │  Backup: Daily            │  ┌──────────────────────────────────┐   │
│  │  Retention: 30 days       │  │  MinIO (S3-Compatible Storage)   │   │
│  │  Replication: WAL         │  │                                  │   │
│  └───────────────────────────┘  │  - Document Storage              │   │
│                                  │  - Report Archives               │   │
│                                  │  - Model Artifacts               │   │
│                                  │  - Backup Storage                │   │
│                                  │                                  │   │
│                                  │  Buckets:                        │   │
│                                  │  - corporate-documents           │   │
│                                  │  - analysis-reports              │   │
│                                  │  - model-artifacts               │   │
│                                  │  - database-backups              │   │
│                                  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
                                 │
┌─────────────────────────────────────────────────────────────────────────┐
│                  MONITORING LAYER (172.20.3.0/24)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Prometheus      │  │  Grafana         │  │  Jaeger             │  │
│  │                  │  │                  │  │                      │  │
│  │  - Metrics       │  │  - Dashboards    │  │  - Distributed      │  │
│  │    Collection    │  │  - Alerting UI   │  │    Tracing          │  │
│  │  - Alert Rules   │  │  - Visualizations│  │  - Performance      │  │
│  │  - Time-series   │  │  - User Access   │  │    Analysis         │  │
│  │    Storage       │  │                  │  │  - Trace Search     │  │
│  │                  │  │  Data Sources:   │  │                      │  │
│  │  Retention: 30d  │  │  - Prometheus    │  │  Storage: 30d       │  │
│  │  Port: 9090      │  │  - PostgreSQL    │  │  Port: 16686        │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
│           │                     │                       │               │
│           └─────────────────────┼───────────────────────┘               │
│                                 │                                       │
│                    ┌────────────▼────────────┐                          │
│                    │  Alertmanager           │                          │
│                    │                         │                          │
│                    │  - Alert Routing        │                          │
│                    │  - Notification Engine  │                          │
│                    │  - Deduplication        │                          │
│                    │  - Silencing            │                          │
│                    │                         │                          │
│                    │  Channels:              │                          │
│                    │  - Email                │                          │
│                    │  - Slack                │                          │
│                    │  - PagerDuty            │                          │
│                    └─────────────────────────┘                          │
└─────────────────────────────────────────────────────────────────────────┘
                                 │
┌─────────────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE MONITORING                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Node Exporter   │  │  cAdvisor        │  │  Service Exporters  │  │
│  │                  │  │                  │  │                      │  │
│  │  - CPU Metrics   │  │  - Container     │  │  - PostgreSQL       │  │
│  │  - Memory Usage  │  │    Metrics       │  │  - Redis            │  │
│  │  - Disk I/O      │  │  - Resource      │  │  - MinIO            │  │
│  │  - Network Stats │  │    Usage         │  │                      │  │
│  │  - Filesystem    │  │  - Performance   │  │  Port: 9187, 9121   │  │
│  │                  │  │                  │  │                      │  │
│  │  Port: 9100      │  │  Port: 8080      │  │                      │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Network Architecture

### Network Segmentation

```
┌────────────────────────────────────────────────────────────────┐
│ Frontend Network (172.20.1.0/24)                               │
│ - NGINX Reverse Proxy                                          │
│ - API Containers                                               │
│ - Direct internet access for external API calls                │
└────────────────────────────────────────────────────────────────┘
                          │
                          │ Internal Communication Only
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ Backend Network (172.20.2.0/24)                                │
│ - PostgreSQL Database                                          │
│ - Redis Cache                                                  │
│ - MinIO Object Storage                                         │
│ - No direct internet access (internal only)                    │
└────────────────────────────────────────────────────────────────┘
                          │
                          │ Metrics Collection Only
                          ▼
┌────────────────────────────────────────────────────────────────┐
│ Monitoring Network (172.20.3.0/24)                             │
│ - Prometheus                                                   │
│ - Grafana                                                      │
│ - Jaeger                                                       │
│ - Alertmanager                                                 │
│ - Limited internet access for alerting                         │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow Architecture

```
┌──────────────┐
│ External APIs│
│  - SEC EDGAR │
│  - Alpha     │
│    Vantage   │
│  - NewsAPI   │
└──────┬───────┘
       │
       │ HTTPS
       ▼
┌─────────────────────────────────────────────────┐
│ API Layer - Data Ingestion Pipeline             │
│                                                  │
│  ┌────────────┐    ┌──────────────┐             │
│  │ Rate       │───▶│ Data Quality │             │
│  │ Limiter    │    │ Validation   │             │
│  └────────────┘    └──────┬───────┘             │
│                           │                      │
│                           ▼                      │
│                    ┌──────────────┐              │
│                    │ Anomaly      │              │
│                    │ Detection    │              │
│                    └──────┬───────┘              │
└───────────────────────────┼──────────────────────┘
                            │
                            │ Validated Data
                            ▼
┌─────────────────────────────────────────────────┐
│ Data Storage Layer                              │
│                                                  │
│  ┌──────────────────┐    ┌───────────────────┐  │
│  │ PostgreSQL       │    │ Redis Cache       │  │
│  │ + TimescaleDB    │◀───│ (Read-through)    │  │
│  │                  │    │                   │  │
│  │ - Structured Data│───▶│ - Hot Data        │  │
│  │ - Time-series    │    │ - API Responses   │  │
│  │ - Vector Search  │    │ - Session State   │  │
│  └──────────────────┘    └───────────────────┘  │
│           │                                      │
│           │ Backups                              │
│           ▼                                      │
│  ┌──────────────────┐                            │
│  │ MinIO            │                            │
│  │ - DB Backups     │                            │
│  │ - Documents      │                            │
│  │ - Reports        │                            │
│  └──────────────────┘                            │
└─────────────────────────────────────────────────┘
```

## Deployment Model

### Container Resource Allocation

| Service | CPU Limit | Memory Limit | CPU Reserve | Memory Reserve |
|---------|-----------|--------------|-------------|----------------|
| NGINX | 1.0 | 512M | 0.5 | 256M |
| API (each) | 2.0 | 4G | 1.0 | 2G |
| PostgreSQL | 2.0 | 4G | 1.0 | 2G |
| Redis | 1.0 | 4G | 0.5 | 2G |
| MinIO | 1.0 | 2G | 0.5 | 1G |
| Prometheus | 1.0 | 2G | 0.5 | 1G |
| Grafana | 0.5 | 512M | 0.25 | 256M |
| Jaeger | 1.0 | 1G | 0.5 | 512M |

### High Availability Configuration

```
API Tier:
- 3 instances minimum
- Auto-scaling based on CPU (>70%)
- Health checks every 30s
- Graceful shutdown (30s timeout)

Database Tier:
- Primary-replica setup
- Automated failover
- Point-in-time recovery
- WAL archiving

Cache Tier:
- Redis Sentinel for HA
- Master-replica replication
- Automatic failover

Storage Tier:
- MinIO distributed mode
- Erasure coding
- Object versioning
```

## Security Architecture

```
┌────────────────────────────────────────────────────────────┐
│ Security Layers                                            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Layer 1: Edge Security                                   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ - SSL/TLS 1.3 encryption                           │   │
│  │ - HTTP Strict Transport Security (HSTS)            │   │
│  │ - Rate limiting (100 req/min per IP)               │   │
│  │ - DDoS protection                                  │   │
│  │ - Geographic filtering (optional)                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  Layer 2: Application Security                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │ - JWT authentication                               │   │
│  │ - Role-based access control (RBAC)                 │   │
│  │ - Input validation & sanitization                  │   │
│  │ - SQL injection prevention                         │   │
│  │ - XSS protection                                   │   │
│  │ - CSRF tokens                                      │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  Layer 3: Data Security                                   │
│  ┌────────────────────────────────────────────────────┐   │
│  │ - Encryption at rest (database)                    │   │
│  │ - Encrypted backups                                │   │
│  │ - Secrets management (AWS Secrets Manager/Vault)   │   │
│  │ - No plaintext credentials                         │   │
│  │ - Password hashing (bcrypt)                        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  Layer 4: Network Security                                │
│  ┌────────────────────────────────────────────────────┐   │
│  │ - Network segmentation                             │   │
│  │ - Firewall rules (iptables/nftables)               │   │
│  │ - Private subnets for backend                      │   │
│  │ - VPC peering (cloud deployments)                  │   │
│  │ - Security groups                                  │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  Layer 5: Monitoring & Audit                              │
│  ┌────────────────────────────────────────────────────┐   │
│  │ - Access logging                                   │   │
│  │ - Audit trails                                     │   │
│  │ - Intrusion detection                              │   │
│  │ - Security event alerting                          │   │
│  │ - Compliance monitoring                            │   │
│  └────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

## Scaling Strategy

### Horizontal Scaling

```
Traffic Thresholds:
├─ 0-100 requests/sec    → 1 API instance
├─ 100-500 requests/sec  → 3 API instances
├─ 500-1000 requests/sec → 5 API instances
└─ 1000+ requests/sec    → 7+ API instances

Auto-scaling Triggers:
├─ CPU > 70% for 5 minutes     → Scale up
├─ Memory > 80% for 5 minutes  → Scale up
├─ CPU < 30% for 15 minutes    → Scale down
└─ Memory < 40% for 15 minutes → Scale down
```

### Vertical Scaling

```
Database Growth Plan:
├─ < 50GB data   → 4GB RAM, 2 CPU
├─ 50-200GB data → 8GB RAM, 4 CPU
├─ 200-500GB data → 16GB RAM, 8 CPU
└─ > 500GB data  → 32GB RAM, 16 CPU
```

## Disaster Recovery

```
Recovery Point Objective (RPO): 1 hour
Recovery Time Objective (RTO): 4 hours

Backup Strategy:
├─ Database: Full daily + WAL continuous
├─ Object Storage: Cross-region replication
├─ Configuration: Git repository
└─ Secrets: AWS Secrets Manager backup

Failover Plan:
├─ Database: Automated replica promotion (5 min)
├─ Application: DNS failover to standby (10 min)
├─ Cache: Redis Sentinel automatic (< 1 min)
└─ Storage: MinIO erasure coding self-heal
```
