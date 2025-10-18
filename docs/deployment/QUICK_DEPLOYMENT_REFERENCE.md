# Quick Deployment Reference - Production

**Version:** v1.0.0 | **Last Updated:** October 17, 2025 | **Status:** ✅ Validated

---

## 🚀 Quick Start - Master Command

```bash
# Complete production deployment (automated)
./scripts/deploy-production.sh --version v1.0.0

# Dry run (simulation only)
./scripts/deploy-production.sh --version v1.0.0 --dry-run
```

**Expected Duration:** 38-60 minutes | **Downtime:** 5-10 minutes

---

## 📋 Pre-Deployment Checklist (5 Minutes)

```bash
# 1. Verify prerequisites
docker --version                     # ✅ Docker 20.10+
docker-compose --version             # ✅ Docker Compose v2.39+

# 2. Check required files
ls -l config/production/docker-compose.production.yml  # ✅ Exists
ls -l config/production/.env.production                # ✅ Exists
ls -l scripts/deploy-*.sh                              # ✅ All 6 scripts

# 3. Validate environment
./scripts/validate-deployment.sh --pre-deploy

# 4. Create backups (automated in deployment script)
# Backups saved to: backups/deployments/

# 5. Go/No-Go decision
# ✅ All checks passed? → Proceed
# ❌ Any failures? → Fix before deploying
```

---

## 🎯 Deployment Phases

### Phase 1: Infrastructure (12 min)
```bash
# Automated by deploy-production.sh
# Deploys: PostgreSQL, Redis, MinIO
./scripts/deploy-infrastructure.sh --version v1.0.0
```

**Health Checks:**
- PostgreSQL: `docker-compose exec postgres pg_isready`
- Redis: `docker-compose exec redis redis-cli ping`
- MinIO: `curl http://localhost:9000/minio/health/live`

### Phase 2: Database Migration (8 min)
```bash
# Automated by deploy-production.sh
# Applies 15 migrations, creates schema
docker-compose run --rm api alembic upgrade head
```

**Validation:**
```bash
# Check current version
docker-compose run --rm api alembic current

# Verify tables created
docker-compose exec postgres psql -U intel_prod_user -d corporate_intel_prod -c "\dt"
```

### Phase 3: API Deployment (10 min)
```bash
# Automated by deploy-production.sh
# Deploys: API, Nginx, monitoring stack
./scripts/deploy-api.sh --version v1.0.0
```

**Health Checks:**
```bash
curl http://localhost:8000/health              # API health
curl http://localhost:9090/-/healthy           # Prometheus
curl http://localhost:3000/api/health          # Grafana
```

### Phase 4: Validation (8 min)
```bash
# Automated by deploy-production.sh
./scripts/validate-deployment.sh --post-deploy
```

---

## 🔍 Quick Health Checks

```bash
# All services status
docker-compose -f config/production/docker-compose.production.yml ps

# API health (detailed)
curl http://localhost:8000/health | jq .

# Database connectivity
docker-compose exec postgres pg_isready -U intel_prod_user

# Cache status
docker-compose exec redis redis-cli -a $REDIS_PASSWORD ping

# Monitoring
curl http://localhost:9090/-/healthy      # Prometheus
curl http://localhost:3000/api/health     # Grafana

# View logs
docker-compose logs -f api                # API logs
docker-compose logs --tail=100 postgres   # Database logs
```

---

## 🔥 Emergency Commands

### Immediate Rollback
```bash
# Execute if critical issues detected
./scripts/emergency-rollback.sh

# Or manual rollback
./scripts/rollback-production.sh --auto --reason "Critical error detected"
```

### Stop All Services
```bash
docker-compose -f config/production/docker-compose.production.yml down
```

### View Recent Logs
```bash
# Last 100 lines from all services
docker-compose logs --tail=100

# Specific service
docker-compose logs -f api
docker-compose logs -f postgres
```

### Database Emergency Restore
```bash
# List backups
ls -lh backups/postgres/

# Restore from backup
docker-compose exec postgres pg_restore \
  -U intel_prod_user -d corporate_intel_prod \
  -c /backups/postgres/corporate_intel_prod_TIMESTAMP.backup
```

---

## 📊 Performance Targets

| Metric | Target | Baseline | Status |
|--------|--------|----------|--------|
| Health endpoint | <10ms | 2.4ms | ✅ Excellent |
| API endpoints | <50ms | 5.8ms | ✅ Excellent |
| Database queries | <5ms | 2.1ms | ✅ Optimal |
| Cache hit ratio | >95% | 98.8% | ✅ Excellent |
| Success rate | >99.9% | 100% | ✅ Perfect |

---

## 🔐 Security Checklist

- ✅ Secrets in environment variables (not hardcoded)
- ✅ Database password-protected
- ✅ Redis password-protected
- ✅ .env.production permissions: 600
- ✅ Security headers configured
- ⚠️ SSL certificates (install within 24h)

---

## 📈 Monitoring Dashboards

```bash
# Access monitoring services
Prometheus:    http://localhost:9090
Grafana:       http://localhost:3000   (admin/admin)
Jaeger:        http://localhost:16686
Alertmanager:  http://localhost:9093
MinIO Console: http://localhost:9001
```

---

## 🎯 Success Criteria

**Deployment is successful if:**
- [ ] All 13 containers running and healthy
- [ ] All 28 smoke tests passing (100%)
- [ ] API responding at http://localhost:8000
- [ ] Health endpoint: 200 OK
- [ ] Database queries: <5ms
- [ ] Cache hit ratio: >95%
- [ ] Zero critical errors in logs
- [ ] Prometheus scraping 8 targets
- [ ] Grafana dashboards accessible

---

## 🚨 Rollback Criteria

**Initiate rollback if:**
- ❌ Critical errors preventing service operation
- ❌ Performance degradation >50%
- ❌ Success rate drops below 95%
- ❌ Data corruption detected
- ❌ Security breach detected

**Rollback Command:**
```bash
./scripts/rollback-production.sh --auto --reason "Critical issue detected"
```

---

## 📞 Emergency Contacts

**Deployment Team:**
- On-Call Engineer: Check PagerDuty schedule
- DevOps Lead: @devops-lead (Slack)
- Database Admin: @dba-oncall (PagerDuty)
- Security Team: @security-team (Slack)

**Escalation Path:**
1. On-Call Engineer (0-15 min)
2. DevOps Lead (15-30 min)
3. Platform Lead (30-60 min)
4. CTO (critical incidents)

**Incident Channel:** #incident-YYYYMMDD (create as needed)

---

## 📝 Post-Deployment Tasks

**Within 1 Hour:**
- [ ] Monitor system stability
- [ ] Check Grafana dashboards
- [ ] Review error logs
- [ ] Update status page

**Within 24 Hours:**
- [ ] Install SSL certificates
- [ ] Configure backup cron
- [ ] Send deployment summary
- [ ] Schedule post-deployment review

**Within 1 Week:**
- [ ] Post-deployment retrospective
- [ ] Analyze performance trends
- [ ] Document lessons learned

---

## 🔧 Troubleshooting Quick Reference

### Container Won't Start
```bash
# Check logs
docker-compose logs container-name

# Check resource usage
docker stats

# Restart specific service
docker-compose restart container-name
```

### Database Connection Issues
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Check connections
docker-compose exec postgres psql -U intel_prod_user -d corporate_intel_prod -c "SELECT count(*) FROM pg_stat_activity;"

# Reset connection pool
docker-compose restart api
```

### Cache Issues
```bash
# Check Redis status
docker-compose exec redis redis-cli ping

# Flush cache
docker-compose exec redis redis-cli -a $REDIS_PASSWORD FLUSHDB

# View cache keys
docker-compose exec redis redis-cli -a $REDIS_PASSWORD KEYS '*'
```

### Performance Degradation
```bash
# Check resource usage
docker stats

# Check slow queries
docker-compose exec postgres psql -U intel_prod_user -d corporate_intel_prod -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Check cache hit ratio
docker-compose exec redis redis-cli -a $REDIS_PASSWORD INFO stats | grep keyspace
```

---

## 📚 Full Documentation

**Deployment Procedures:**
- `docs/deployment/production-deployment-runbook.md` - Complete runbook
- `docs/deployment/PRODUCTION_DEPLOYMENT_LOG_DAY4.md` - Deployment simulation log
- `docs/deployment/DEPLOYMENT_SUMMARY_DAY4.md` - Summary and results

**Scripts:**
- `scripts/deploy-production.sh` - Master orchestrator
- `scripts/deploy-infrastructure.sh` - Infrastructure deployment
- `scripts/deploy-api.sh` - API deployment
- `scripts/validate-deployment.sh` - Validation
- `scripts/rollback-production.sh` - Rollback procedures

**Baselines:**
- `docs/PLAN_A_DAY1_PERFORMANCE_BASELINE.md` - Performance baseline (9.2/10)
- `docs/security_validation_day1_results.json` - Security baseline (9.2/10)

---

**Quick Reference Version:** 1.0.0
**Last Validated:** October 17, 2025
**Deployment Score:** 9.3/10 ⭐
**Production Ready:** ✅ Yes

---
