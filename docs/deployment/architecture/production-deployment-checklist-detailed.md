# Production Deployment Checklist

## Pre-Deployment Phase (1-2 Weeks Before)

### Infrastructure Preparation

- [ ] **Server Provisioning**
  - [ ] Provision production servers (minimum 8GB RAM, 4 CPU cores, 100GB disk)
  - [ ] Configure firewall rules (ports 80, 443 open)
  - [ ] Set up SSH key-based authentication
  - [ ] Disable password authentication
  - [ ] Configure automatic security updates
  - [ ] Set up backup storage (S3 or equivalent)

- [ ] **Domain & DNS Configuration**
  - [ ] Register/verify domain ownership
  - [ ] Configure DNS A records for main domain
  - [ ] Configure DNS CNAME for subdomains (api, grafana, minio)
  - [ ] Set up DNS monitoring
  - [ ] Configure low TTL (300s) for easy failover

- [ ] **SSL/TLS Certificates**
  - [ ] Install certbot or equivalent
  - [ ] Generate SSL certificates (Let's Encrypt)
  - [ ] Verify certificate installation
  - [ ] Configure auto-renewal
  - [ ] Test certificate chain
  - [ ] Set up expiration monitoring (30-day alert)

### Security Setup

- [ ] **Secrets Management**
  - [ ] Set up AWS Secrets Manager or HashiCorp Vault
  - [ ] Generate strong database password (32+ characters)
  - [ ] Generate strong Redis password (32+ characters)
  - [ ] Generate API secret key (64+ characters)
  - [ ] Generate session secret key (64+ characters)
  - [ ] Store external API keys securely
  - [ ] Configure secret rotation policy

- [ ] **Access Control**
  - [ ] Create dedicated service accounts
  - [ ] Set up SSH access for operations team
  - [ ] Configure sudo access with logging
  - [ ] Set up VPN access (if required)
  - [ ] Configure database user permissions
  - [ ] Set up API authentication

- [ ] **Security Hardening**
  - [ ] Enable UFW/iptables firewall
  - [ ] Configure fail2ban
  - [ ] Set up intrusion detection (AIDE/Tripwire)
  - [ ] Enable SELinux/AppArmor
  - [ ] Configure security headers in NGINX
  - [ ] Set up rate limiting

### Monitoring & Alerting

- [ ] **Monitoring Setup**
  - [ ] Configure Prometheus scrape targets
  - [ ] Import Grafana dashboards
  - [ ] Set up Prometheus data retention (30 days)
  - [ ] Configure Jaeger for distributed tracing
  - [ ] Set up log aggregation
  - [ ] Configure metrics exporters

- [ ] **Alert Configuration**
  - [ ] Configure Alertmanager routes
  - [ ] Set up email notifications
  - [ ] Configure Slack integration
  - [ ] Set up PagerDuty (if applicable)
  - [ ] Define alert severity levels
  - [ ] Test alert delivery

- [ ] **Dashboard Creation**
  - [ ] API performance dashboard
  - [ ] Database health dashboard
  - [ ] Infrastructure metrics dashboard
  - [ ] Business KPI dashboard
  - [ ] Error rate dashboard

### Backup & Recovery

- [ ] **Backup Strategy**
  - [ ] Configure automated database backups
  - [ ] Set up backup encryption
  - [ ] Configure backup retention (30 days)
  - [ ] Set up cross-region backup replication
  - [ ] Configure MinIO bucket versioning
  - [ ] Test backup restoration process

- [ ] **Disaster Recovery**
  - [ ] Document recovery procedures
  - [ ] Set up database replication
  - [ ] Configure automated failover
  - [ ] Create disaster recovery runbook
  - [ ] Test recovery time objective (RTO < 4 hours)
  - [ ] Test recovery point objective (RPO < 1 hour)

### Application Preparation

- [ ] **Code & Configuration**
  - [ ] Tag release version in Git
  - [ ] Build production Docker images
  - [ ] Push images to container registry
  - [ ] Update docker-compose.prod.yml with correct image tags
  - [ ] Validate environment configuration
  - [ ] Run security scan on Docker images

- [ ] **Database Migration**
  - [ ] Review migration scripts
  - [ ] Test migrations in staging
  - [ ] Create rollback scripts
  - [ ] Document migration steps
  - [ ] Plan migration downtime window
  - [ ] Prepare communication for stakeholders

- [ ] **Testing**
  - [ ] Complete integration tests
  - [ ] Run security penetration tests
  - [ ] Perform load testing
  - [ ] Validate API endpoints
  - [ ] Test error handling
  - [ ] Verify monitoring alerts

## Deployment Day

### Pre-Deployment Verification

- [ ] **System Health Check**
  - [ ] Verify server resources available
  - [ ] Check disk space (>50% free)
  - [ ] Verify network connectivity
  - [ ] Confirm DNS resolution
  - [ ] Test SSL certificate validity
  - [ ] Verify all secrets accessible

- [ ] **Team Readiness**
  - [ ] Deployment team on standby
  - [ ] Operations team notified
  - [ ] Stakeholders notified of deployment window
  - [ ] Rollback team ready
  - [ ] Communication channels open

### Deployment Execution

- [ ] **Step 1: Infrastructure Deployment**
  ```bash
  # Pull latest code
  git checkout production
  git pull origin production

  # Verify configuration
  ./scripts/validate-production-config.sh
  ```

- [ ] **Step 2: Database Setup**
  ```bash
  # Start database first
  docker-compose -f docker-compose.production.yml up -d postgres

  # Wait for health check
  docker-compose -f docker-compose.production.yml ps postgres

  # Run migrations
  docker-compose -f docker-compose.production.yml run --rm api alembic upgrade head
  ```

- [ ] **Step 3: Cache & Storage**
  ```bash
  # Start Redis
  docker-compose -f docker-compose.production.yml up -d redis

  # Start MinIO
  docker-compose -f docker-compose.production.yml up -d minio

  # Verify health
  docker-compose -f docker-compose.production.yml ps
  ```

- [ ] **Step 4: Application Deployment**
  ```bash
  # Start API services
  docker-compose -f docker-compose.production.yml up -d api

  # Verify API health
  curl -f https://api.corporate-intel.yourdomain.com/health
  ```

- [ ] **Step 5: Reverse Proxy**
  ```bash
  # Start NGINX
  docker-compose -f docker-compose.production.yml up -d nginx

  # Verify SSL
  curl -I https://corporate-intel.yourdomain.com
  ```

- [ ] **Step 6: Monitoring Stack**
  ```bash
  # Start monitoring services
  docker-compose -f docker-compose.production.yml up -d prometheus grafana jaeger

  # Access Grafana
  # https://grafana.corporate-intel.yourdomain.com
  ```

### Post-Deployment Verification

- [ ] **Smoke Tests**
  - [ ] API health endpoint responds (200 OK)
  - [ ] Database connectivity verified
  - [ ] Redis cache operational
  - [ ] MinIO storage accessible
  - [ ] SSL certificate valid
  - [ ] All containers healthy

- [ ] **Functional Tests**
  - [ ] User authentication works
  - [ ] API endpoints respond correctly
  - [ ] Data ingestion pipeline functional
  - [ ] Search functionality works
  - [ ] Reports generation successful

- [ ] **Performance Validation**
  - [ ] Response times < 500ms for 95th percentile
  - [ ] No memory leaks observed
  - [ ] CPU usage < 50% at normal load
  - [ ] Database query performance acceptable
  - [ ] Cache hit rate > 80%

- [ ] **Monitoring Verification**
  - [ ] Metrics appearing in Prometheus
  - [ ] Grafana dashboards displaying data
  - [ ] Alerts configured and active
  - [ ] Logs aggregating correctly
  - [ ] Traces visible in Jaeger

## Post-Deployment Phase

### Day 1 Monitoring

- [ ] **Hour 1-2: Critical Monitoring**
  - [ ] Monitor error rates (should be < 1%)
  - [ ] Check response times
  - [ ] Verify all services healthy
  - [ ] Review logs for errors
  - [ ] Monitor resource utilization

- [ ] **Hour 2-8: Active Monitoring**
  - [ ] Check database performance
  - [ ] Monitor cache effectiveness
  - [ ] Review API usage patterns
  - [ ] Check backup completion
  - [ ] Verify monitoring alerts working

- [ ] **Hour 8-24: Stability Verification**
  - [ ] Review 24-hour metrics
  - [ ] Check for memory leaks
  - [ ] Verify auto-scaling behavior
  - [ ] Review security logs
  - [ ] Confirm backup successful

### Week 1 Activities

- [ ] **Daily Tasks**
  - [ ] Review error logs
  - [ ] Check system metrics
  - [ ] Verify backup completion
  - [ ] Monitor user feedback
  - [ ] Review security alerts

- [ ] **Performance Optimization**
  - [ ] Analyze slow queries
  - [ ] Optimize cache configuration
  - [ ] Review database indexes
  - [ ] Tune connection pools
  - [ ] Optimize resource allocation

- [ ] **Documentation**
  - [ ] Document any issues encountered
  - [ ] Update runbooks based on learnings
  - [ ] Create troubleshooting guides
  - [ ] Document performance baselines
  - [ ] Update architecture diagrams

### Month 1 Review

- [ ] **Performance Review**
  - [ ] Analyze uptime (target: 99.9%)
  - [ ] Review response time trends
  - [ ] Check error rate patterns
  - [ ] Analyze resource utilization
  - [ ] Review cost vs. budget

- [ ] **Security Audit**
  - [ ] Review access logs
  - [ ] Check for security incidents
  - [ ] Verify certificate auto-renewal
  - [ ] Review firewall logs
  - [ ] Conduct vulnerability scan

- [ ] **Optimization Planning**
  - [ ] Identify performance bottlenecks
  - [ ] Plan capacity upgrades
  - [ ] Review auto-scaling rules
  - [ ] Optimize backup strategy
  - [ ] Plan feature releases

## Rollback Procedures

### When to Rollback

Trigger rollback if:
- [ ] Error rate > 5% for 10 minutes
- [ ] Critical API endpoints down
- [ ] Data corruption detected
- [ ] Security breach identified
- [ ] Database migration failure
- [ ] Cascading failures observed

### Rollback Steps

```bash
# 1. Stop current version
docker-compose -f docker-compose.production.yml down

# 2. Restore previous image version
docker pull ghcr.io/yourorg/corporate-intel:v1.0.0-rollback

# 3. Update docker-compose with rollback version
sed -i 's/:latest/:v1.0.0-rollback/g' docker-compose.production.yml

# 4. Rollback database if needed
docker-compose run --rm api alembic downgrade -1

# 5. Restart services
docker-compose -f docker-compose.production.yml up -d

# 6. Verify rollback successful
./scripts/smoke-tests.sh
```

## Contact Information

### Escalation Path

1. **Level 1: Operations Team**
   - Email: ops@yourdomain.com
   - Slack: #production-ops
   - Response time: 15 minutes

2. **Level 2: Engineering Lead**
   - Email: engineering-lead@yourdomain.com
   - Phone: [REDACTED]
   - Response time: 30 minutes

3. **Level 3: CTO/VP Engineering**
   - Email: cto@yourdomain.com
   - Phone: [REDACTED]
   - Response time: 1 hour

### External Vendors

- **SSL Provider**: Let's Encrypt (automated)
- **DNS Provider**: [Your DNS Provider]
- **Cloud Infrastructure**: [AWS/GCP/Azure]
- **Monitoring**: Grafana Cloud (optional)

## Sign-off

### Deployment Approval

- [ ] **Technical Lead**: _________________ Date: _________
- [ ] **Operations Manager**: _________________ Date: _________
- [ ] **Security Officer**: _________________ Date: _________
- [ ] **Product Owner**: _________________ Date: _________

### Post-Deployment Verification

- [ ] **Deployment Successful**: _________________ Date: _________
- [ ] **Smoke Tests Passed**: _________________ Date: _________
- [ ] **Monitoring Confirmed**: _________________ Date: _________
- [ ] **Production Ready**: _________________ Date: _________
