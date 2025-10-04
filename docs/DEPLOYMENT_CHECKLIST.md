# Production Deployment Checklist

## Pre-Deployment

### Environment Setup
- [ ] Generate strong passwords for all services (PostgreSQL, Redis, MinIO, Grafana)
- [ ] Update `.env.production` with production credentials
- [ ] Store secrets in secure secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Configure SSL/TLS certificates (Let's Encrypt or commercial CA)
- [ ] Set up domain DNS records pointing to production server
- [ ] Configure firewall rules (allow ports 80, 443, block all others except SSH)

### Infrastructure Validation
- [ ] Verify Docker and Docker Compose are installed (latest stable versions)
- [ ] Check disk space: minimum 100GB free for data and backups
- [ ] Verify RAM: minimum 8GB, recommended 16GB+
- [ ] Check CPU: minimum 4 cores, recommended 8+ cores
- [ ] Set up backup storage location with adequate space
- [ ] Configure log rotation (logrotate) for application and Docker logs

### Security Hardening
- [ ] Enable UFW/iptables firewall
- [ ] Configure fail2ban for SSH protection
- [ ] Set up SSH key-based authentication (disable password auth)
- [ ] Install and configure auditd for security auditing
- [ ] Enable automatic security updates (unattended-upgrades)
- [ ] Review and apply CIS Docker benchmarks
- [ ] Configure SELinux or AppArmor policies

### Database Preparation
- [ ] Review database schema and migrations
- [ ] Plan database backup strategy (daily, weekly, monthly)
- [ ] Set up automated backup cron jobs
- [ ] Test database restore procedure
- [ ] Configure PostgreSQL performance tuning parameters
- [ ] Enable PostgreSQL logging and slow query logging

### Monitoring & Observability
- [ ] Set up Prometheus data retention policy
- [ ] Configure Grafana dashboards for key metrics
- [ ] Set up alerting rules (disk space, memory, CPU, API errors)
- [ ] Configure alert notification channels (email, Slack, PagerDuty)
- [ ] Enable distributed tracing with Jaeger
- [ ] Set up Sentry for error tracking
- [ ] Configure log aggregation (ELK stack or similar)

## Deployment

### Build & Test
- [ ] Build Docker images with production tags
- [ ] Run security scans on Docker images (Trivy, Grype)
- [ ] Verify image size and layers
- [ ] Test images locally with production-like environment
- [ ] Run full test suite (unit, integration, e2e)
- [ ] Perform load testing (Apache Bench, k6, Locust)

### Database Migration
- [ ] Backup current database (if upgrading existing deployment)
- [ ] Review migration scripts
- [ ] Run migrations in dry-run mode
- [ ] Execute migrations with rollback plan ready
- [ ] Verify migration success
- [ ] Create post-migration backup

### Service Deployment
- [ ] Pull latest production images: `docker-compose -f docker-compose.yml pull`
- [ ] Stop existing services: `docker-compose down`
- [ ] Start services: `docker-compose -f docker-compose.yml up -d`
- [ ] Verify all containers are running: `docker-compose ps`
- [ ] Check container logs for errors: `docker-compose logs -f`
- [ ] Wait for health checks to pass

### Reverse Proxy Configuration
- [ ] Copy nginx configuration to /etc/nginx/sites-available/
- [ ] Create symbolic link to sites-enabled
- [ ] Test nginx configuration: `nginx -t`
- [ ] Reload nginx: `systemctl reload nginx`
- [ ] Verify SSL certificate auto-renewal (certbot)
- [ ] Test HTTPS redirection
- [ ] Verify security headers with SSL Labs

## Post-Deployment

### Smoke Tests
- [ ] Test health endpoint: `curl https://domain.com/health`
- [ ] Verify API documentation: `https://domain.com/docs`
- [ ] Test authentication endpoints
- [ ] Verify database connectivity
- [ ] Test Redis caching
- [ ] Verify MinIO object storage access
- [ ] Check OpenTelemetry metrics collection

### Performance Validation
- [ ] Measure API response times (should be <200ms for most endpoints)
- [ ] Verify cache hit rates (Redis)
- [ ] Check database query performance
- [ ] Monitor CPU and memory usage
- [ ] Verify log levels are appropriate (INFO in production)
- [ ] Test rate limiting functionality

### Security Verification
- [ ] Scan for open ports: `nmap -p- domain.com`
- [ ] Test SQL injection protection
- [ ] Verify CORS configuration
- [ ] Test authentication and authorization
- [ ] Check for exposed secrets in logs
- [ ] Verify encrypted connections (TLS 1.2+ only)
- [ ] Test session timeout and logout

### Monitoring Setup Verification
- [ ] Verify Prometheus is scraping all targets
- [ ] Check Grafana dashboards are displaying data
- [ ] Test alert rules by triggering test alerts
- [ ] Verify alert notifications are being sent
- [ ] Check Jaeger traces are being collected
- [ ] Verify Sentry error reporting
- [ ] Test log aggregation and search

### Backup Verification
- [ ] Verify backup cron jobs are scheduled
- [ ] Test manual backup: `./scripts/backup.sh daily`
- [ ] Verify backup files are created
- [ ] Test restore procedure on staging environment
- [ ] Verify backup retention policy
- [ ] Test backup notification system

### Documentation
- [ ] Update deployment documentation
- [ ] Document any deployment issues and resolutions
- [ ] Create runbook for common operations
- [ ] Update disaster recovery procedures
- [ ] Document monitoring and alerting setup
- [ ] Share access credentials with team (via secure channel)

## Rollback Plan

### Immediate Rollback Steps
1. Stop current services: `docker-compose down`
2. Restore previous Docker images: `docker-compose -f docker-compose.yml.backup up -d`
3. Restore database from last backup: `./scripts/restore.sh /path/to/backup`
4. Verify application health
5. Notify team of rollback

### Post-Rollback
- [ ] Investigate deployment failure
- [ ] Document root cause
- [ ] Create action items for fixes
- [ ] Update deployment checklist with lessons learned

## Ongoing Maintenance

### Daily
- [ ] Check application logs for errors
- [ ] Monitor disk space usage
- [ ] Verify backup completion
- [ ] Review security alerts

### Weekly
- [ ] Review performance metrics
- [ ] Check for security updates
- [ ] Analyze error trends in Sentry
- [ ] Review slow query logs

### Monthly
- [ ] Update dependencies
- [ ] Review and optimize database queries
- [ ] Analyze resource usage trends
- [ ] Update documentation
- [ ] Conduct security audit
- [ ] Test disaster recovery procedures

## Emergency Contacts

- **DevOps Lead**: [contact info]
- **Database Admin**: [contact info]
- **Security Team**: [contact info]
- **On-Call Engineer**: [PagerDuty/phone]

## Useful Commands

```bash
# View logs
docker-compose logs -f api

# Restart service
docker-compose restart api

# Database backup
./scripts/backup.sh daily

# Database restore
./scripts/restore.sh /var/backups/corporate-intel/daily/20231201_120000

# Check container health
docker inspect --format='{{json .State.Health}}' corporate-intel-api

# Scale workers
docker-compose up -d --scale api=3

# Check resource usage
docker stats

# Access database
docker exec -it corporate-intel-postgres psql -U intel_prod_user -d corporate_intel_prod
```

## Success Criteria

Deployment is considered successful when:
- [ ] All health checks pass
- [ ] API response times are within SLA (<200ms p95)
- [ ] Error rate is below 0.1%
- [ ] All monitoring dashboards show green status
- [ ] Backup job completes successfully
- [ ] Security scans show no critical vulnerabilities
- [ ] Load test passes with acceptable performance
- [ ] No critical alerts for 24 hours post-deployment
