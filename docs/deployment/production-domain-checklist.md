# Production Domain Setup Checklist

## Pre-Deployment Phase

### DNS Configuration
- [ ] Domain registered and active
- [ ] A records configured for all subdomains
  - [ ] `api.corporate-intel.com` → Server IP
  - [ ] `metrics.corporate-intel.com` → Server IP
  - [ ] `docs.corporate-intel.com` → Server IP
- [ ] AAAA records configured (IPv6) - Optional
- [ ] CAA records added to restrict certificate authorities
- [ ] DNS propagation verified (use dnschecker.org)
- [ ] TTL set appropriately (300 seconds for testing, 3600 for production)
- [ ] DNS provider has API access configured (if using DNS challenge)

### Server Preparation
- [ ] Server accessible via SSH
- [ ] Firewall configured (ports 80, 443 open)
- [ ] Server timezone set correctly
- [ ] NTP configured for time synchronization
- [ ] Sufficient disk space (minimum 10GB free)
- [ ] Root or sudo access available

### SSL Prerequisites
- [ ] Port 80 accessible from internet (for ACME challenge)
- [ ] Port 443 accessible from internet (for HTTPS)
- [ ] Webroot directory created (`/var/www/certbot`)
- [ ] Email address configured for Let's Encrypt notifications
- [ ] No existing conflicting web servers on ports 80/443

---

## Installation Phase

### Reverse Proxy Setup
- [ ] Choose reverse proxy (Nginx or Traefik)
  - [ ] Nginx selected
  - [ ] Traefik selected
- [ ] Install reverse proxy
- [ ] Copy production configuration files
- [ ] Test configuration syntax
- [ ] Configure log rotation
- [ ] Set up monitoring/metrics collection

### SSL Certificate Installation
- [ ] Certbot installed
- [ ] DNS provider plugin installed (if using DNS challenge)
- [ ] SSL automation script downloaded
- [ ] Script permissions set (`chmod +x`)
- [ ] DH parameters generated (`dhparam.pem`)

### Certificate Acquisition
- [ ] Run SSL setup script
- [ ] Certificates obtained for all domains:
  - [ ] `api.corporate-intel.com`
  - [ ] `metrics.corporate-intel.com`
  - [ ] `docs.corporate-intel.com`
- [ ] Wildcard certificate obtained (if applicable)
- [ ] Certificate files verified in `/etc/letsencrypt/live/`
- [ ] Certificate chain validated
- [ ] Certificate expiration dates checked (90 days)

---

## Configuration Phase

### Nginx Configuration (if using Nginx)
- [ ] Main configuration file deployed
- [ ] Site-specific configuration in `sites-available/`
- [ ] Symbolic link created in `sites-enabled/`
- [ ] Default site disabled
- [ ] SSL certificates referenced correctly in config
- [ ] Security headers configured
- [ ] Rate limiting configured
- [ ] OCSP stapling enabled
- [ ] HTTP to HTTPS redirect configured
- [ ] Configuration syntax validated (`nginx -t`)
- [ ] Nginx reloaded successfully

### Traefik Configuration (if using Traefik)
- [ ] Static configuration deployed (`traefik.yml`)
- [ ] Dynamic configuration deployed (`traefik-dynamic.yml`)
- [ ] ACME storage file created (`acme.json` with 600 permissions)
- [ ] Entry points configured (web, websecure)
- [ ] Certificate resolver configured
- [ ] Middlewares configured (security headers, rate limit, etc.)
- [ ] Routers configured for each service
- [ ] Traefik dashboard secured with authentication
- [ ] Traefik systemd service configured
- [ ] Traefik started and enabled

### Backend Services
- [ ] API service running on configured port (8000)
- [ ] Metrics service running on configured port (3000)
- [ ] Health check endpoints responding
- [ ] Services configured to start on boot
- [ ] Service logs accessible and monitored

---

## Security Hardening

### SSL/TLS Security
- [ ] TLS 1.2 minimum enforced
- [ ] TLS 1.3 enabled and preferred
- [ ] Weak cipher suites disabled
- [ ] HSTS header configured (max-age=63072000)
- [ ] HSTS preload directive added
- [ ] OCSP stapling working
- [ ] Certificate transparency monitoring enabled
- [ ] SSL session caching configured

### Security Headers
- [ ] `Strict-Transport-Security` configured
- [ ] `X-Frame-Options: DENY` set
- [ ] `X-Content-Type-Options: nosniff` set
- [ ] `X-XSS-Protection` enabled
- [ ] `Referrer-Policy` configured
- [ ] `Content-Security-Policy` implemented
- [ ] `Permissions-Policy` configured
- [ ] Server tokens removed/hidden

### Access Control
- [ ] Rate limiting configured and tested
- [ ] Connection limits set
- [ ] Metrics endpoint protected with authentication
- [ ] Admin endpoints secured
- [ ] IP whitelisting configured (if applicable)
- [ ] Fail2ban installed and configured
- [ ] Firewall rules reviewed and optimized

### Application Security
- [ ] CORS configured appropriately
- [ ] Input validation on all endpoints
- [ ] SQL injection protection verified
- [ ] XSS protection verified
- [ ] CSRF protection enabled
- [ ] Authentication mechanisms tested
- [ ] Authorization rules verified

---

## Automation and Monitoring

### Certificate Renewal
- [ ] Systemd timer configured for auto-renewal
  - [ ] Service file created
  - [ ] Timer file created
  - [ ] Timer enabled and started
- [ ] OR Cron job configured for auto-renewal
  - [ ] Cron script deployed
  - [ ] Crontab entry added
- [ ] Renewal hooks configured (nginx/traefik reload)
- [ ] Dry-run renewal test successful
- [ ] Renewal logs configured and accessible

### Certificate Monitoring
- [ ] Certificate expiration monitoring script installed
- [ ] Monitoring cron job configured (daily check)
- [ ] Alert notifications configured
- [ ] Email/Slack/PagerDuty integration set up
- [ ] Monitoring dashboard configured
- [ ] SSL Labs monitoring enabled (optional)

### Log Management
- [ ] Access logs configured and rotating
- [ ] Error logs configured and rotating
- [ ] SSL/certificate logs accessible
- [ ] Log aggregation configured (optional)
- [ ] Log retention policy defined
- [ ] Log monitoring alerts configured

### Backup Strategy
- [ ] SSL certificate backup script created
- [ ] Backup schedule configured (daily/weekly)
- [ ] Backup storage configured (encrypted)
- [ ] Backup restoration tested
- [ ] Configuration files backed up
- [ ] Disaster recovery plan documented

---

## Testing and Validation

### DNS Testing
- [ ] DNS resolution verified from multiple locations
- [ ] A/AAAA records resolving correctly
- [ ] CAA records verified
- [ ] DNS propagation complete worldwide

### SSL/TLS Testing
- [ ] HTTPS accessible on all domains
- [ ] HTTP redirects to HTTPS verified
- [ ] SSL Labs test run (target: A or A+)
  - [ ] `api.corporate-intel.com` grade: _____
  - [ ] `metrics.corporate-intel.com` grade: _____
  - [ ] `docs.corporate-intel.com` grade: _____
- [ ] Certificate chain validated
- [ ] OCSP stapling verified
- [ ] Browser trust verified (no warnings)
- [ ] Mobile device testing completed

### Functionality Testing
- [ ] API endpoints accessible and responding
- [ ] Metrics dashboard accessible (with auth)
- [ ] Documentation site accessible
- [ ] Health check endpoints responding
- [ ] WebSocket connections working (if applicable)
- [ ] File uploads working (if applicable)
- [ ] Session management working correctly

### Performance Testing
- [ ] Page load times acceptable
- [ ] API response times within SLA
- [ ] Rate limiting tested and working
- [ ] Load balancing verified (if applicable)
- [ ] Connection pooling optimized
- [ ] Compression working (gzip/brotli)

### Security Testing
- [ ] Penetration testing completed
- [ ] Vulnerability scan run (e.g., OWASP ZAP)
- [ ] Security headers verified (securityheaders.com)
- [ ] Rate limiting tested (confirm blocks)
- [ ] Authentication bypass attempts blocked
- [ ] SQL injection attempts blocked
- [ ] XSS attempts blocked

---

## Documentation

### Technical Documentation
- [ ] Architecture diagram created
- [ ] Network diagram created
- [ ] DNS configuration documented
- [ ] SSL certificate locations documented
- [ ] Reverse proxy configuration documented
- [ ] Renewal process documented
- [ ] Troubleshooting guide created

### Operational Documentation
- [ ] Runbooks created for common tasks
- [ ] Incident response plan documented
- [ ] Escalation procedures defined
- [ ] Contact information current
- [ ] Service dependencies mapped
- [ ] Recovery time objectives (RTO) defined
- [ ] Recovery point objectives (RPO) defined

### Compliance Documentation
- [ ] Security policy documented
- [ ] Data handling procedures documented
- [ ] Privacy policy reviewed
- [ ] Compliance requirements verified (GDPR, etc.)
- [ ] Audit logs configured and accessible
- [ ] Certificate management policy defined

---

## Post-Deployment

### Monitoring Setup
- [ ] Uptime monitoring configured (UptimeRobot, Pingdom, etc.)
- [ ] SSL certificate monitoring active
- [ ] Performance monitoring configured (APM)
- [ ] Error tracking configured (Sentry, Rollbar, etc.)
- [ ] Metrics collection verified (Prometheus, etc.)
- [ ] Alerting rules configured
- [ ] Dashboard access granted to team

### Team Handoff
- [ ] Knowledge transfer session completed
- [ ] Access credentials shared securely
- [ ] Documentation reviewed with team
- [ ] Support procedures explained
- [ ] Escalation paths communicated
- [ ] On-call rotation established

### Compliance and Governance
- [ ] Security review completed
- [ ] Compliance requirements met
- [ ] Change management process followed
- [ ] Service catalog updated
- [ ] Asset inventory updated
- [ ] License compliance verified

---

## Ongoing Maintenance

### Daily Tasks
- [ ] Monitor uptime and availability
- [ ] Review error logs for anomalies
- [ ] Check certificate expiration status
- [ ] Verify backup completion
- [ ] Monitor performance metrics

### Weekly Tasks
- [ ] Review access logs for suspicious activity
- [ ] Check SSL Labs grade
- [ ] Verify auto-renewal timer/cron
- [ ] Review and rotate logs
- [ ] Test alerting system

### Monthly Tasks
- [ ] Security updates applied
- [ ] Configuration review
- [ ] Backup restoration test
- [ ] Performance optimization review
- [ ] Documentation updates

### Quarterly Tasks
- [ ] Full security audit
- [ ] Disaster recovery drill
- [ ] Capacity planning review
- [ ] SLA compliance review
- [ ] Certificate rotation (optional)
- [ ] Team training/refresher

---

## Emergency Contacts

| Role | Name | Email | Phone |
|------|------|-------|-------|
| DevOps Lead | | | |
| Security Team | | | |
| On-Call Engineer | | | |
| DNS Provider Support | | | |
| Hosting Provider Support | | | |

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DevOps Engineer | | | |
| Security Lead | | | |
| Tech Lead | | | |
| Product Owner | | | |

---

**Checklist Version**: 1.0
**Last Updated**: 2025-10-17
**Next Review**: 2026-01-17
**Status**: ☐ In Progress  ☐ Completed  ☐ Production Ready
