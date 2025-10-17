# DNS Configuration Guide

## Overview

This guide provides step-by-step instructions for configuring DNS records for the Corporate Intelligence Platform production deployment.

## Prerequisites

- Domain name registered with a registrar
- Access to DNS management panel (Route53, CloudFlare, or registrar's DNS)
- Production server IP address or load balancer endpoint
- SSL certificate ready (or will use Let's Encrypt)

## DNS Provider Options

### Option 1: AWS Route53 (Recommended for AWS Deployments)

**Advantages:**
- Integrated with AWS services
- Health checks and failover
- Geolocation routing
- Low latency
- Programmable via API/CLI

### Option 2: CloudFlare (Recommended for CDN/DDoS Protection)

**Advantages:**
- Free tier available
- Built-in CDN
- DDoS protection
- SSL/TLS management
- Analytics and monitoring

### Option 3: Traditional DNS Provider

Use your domain registrar's DNS or a dedicated DNS provider.

## DNS Records Configuration

### Required DNS Records

#### 1. A Record (IPv4)

```text
Type: A
Name: @ (or your domain)
Value: YOUR_SERVER_IP_ADDRESS
TTL: 300 (5 minutes for initial setup, increase to 3600 after verification)
```

**Example:**
```text
corporate-intel.com -> 203.0.113.45
```

#### 2. AAAA Record (IPv6) - Optional but Recommended

```text
Type: AAAA
Name: @ (or your domain)
Value: YOUR_SERVER_IPV6_ADDRESS
TTL: 300
```

#### 3. CNAME for www Subdomain

```text
Type: CNAME
Name: www
Value: corporate-intel.com (or @ or your root domain)
TTL: 300
```

#### 4. API Subdomain (Optional)

```text
Type: A or CNAME
Name: api
Value: YOUR_SERVER_IP or corporate-intel.com
TTL: 300
```

#### 5. Wildcard Certificate Support (If Using Wildcard SSL)

```text
Type: A
Name: *
Value: YOUR_SERVER_IP_ADDRESS
TTL: 300
```

## Step-by-Step Configuration

### AWS Route53 Configuration

#### Using AWS Console

1. Navigate to Route53 in AWS Console
2. Select "Hosted Zones"
3. Click "Create Hosted Zone"
   - Domain name: `corporate-intel.com`
   - Type: Public Hosted Zone
4. Click "Create"

5. Create A Record:
   - Click "Create Record"
   - Record name: (leave empty for root domain)
   - Record type: A
   - Value: Your EC2 instance IP or ALB DNS name
   - Routing policy: Simple routing
   - TTL: 300

6. Create CNAME for www:
   - Click "Create Record"
   - Record name: `www`
   - Record type: CNAME
   - Value: `corporate-intel.com`
   - TTL: 300

7. Update nameservers at your registrar with Route53 NS records

#### Using AWS CLI

```bash
# Create hosted zone
aws route53 create-hosted-zone \
  --name corporate-intel.com \
  --caller-reference $(date +%s) \
  --hosted-zone-config Comment="Corporate Intel Production"

# Get hosted zone ID
HOSTED_ZONE_ID=$(aws route53 list-hosted-zones-by-name \
  --dns-name corporate-intel.com \
  --query 'HostedZones[0].Id' \
  --output text)

# Create A record
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "corporate-intel.com",
        "Type": "A",
        "TTL": 300,
        "ResourceRecords": [{"Value": "203.0.113.45"}]
      }
    }]
  }'

# Create CNAME for www
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "www.corporate-intel.com",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{"Value": "corporate-intel.com"}]
      }
    }]
  }'
```

### CloudFlare Configuration

#### Using CloudFlare Dashboard

1. Log in to CloudFlare
2. Click "Add Site"
3. Enter your domain: `corporate-intel.com`
4. Select a plan (Free tier is sufficient for most use cases)
5. CloudFlare will scan existing DNS records

6. Add/Verify A Record:
   - Type: A
   - Name: @ (or corporate-intel.com)
   - IPv4 address: YOUR_SERVER_IP
   - Proxy status: Proxied (orange cloud) for DDoS protection
   - TTL: Auto

7. Add CNAME for www:
   - Type: CNAME
   - Name: www
   - Target: corporate-intel.com
   - Proxy status: Proxied
   - TTL: Auto

8. Update nameservers at registrar:
   - CloudFlare will provide nameservers (e.g., `ava.ns.cloudflare.com`)
   - Update at your domain registrar

#### Using CloudFlare API

```bash
# Set CloudFlare credentials
CF_API_TOKEN="your_api_token"
CF_ZONE_ID="your_zone_id"

# Create A record
curl -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "corporate-intel.com",
    "content": "203.0.113.45",
    "ttl": 300,
    "proxied": true
  }'

# Create CNAME record
curl -X POST "https://api.cloudflare.com/client/v4/zones/${CF_ZONE_ID}/dns_records" \
  -H "Authorization: Bearer ${CF_API_TOKEN}" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "CNAME",
    "name": "www",
    "content": "corporate-intel.com",
    "ttl": 300,
    "proxied": true
  }'
```

## DNS Verification

### Check DNS Propagation

```bash
# Using dig (Linux/Mac)
dig corporate-intel.com A
dig www.corporate-intel.com CNAME

# Using nslookup (Windows/Linux/Mac)
nslookup corporate-intel.com
nslookup www.corporate-intel.com

# Using host (Linux/Mac)
host corporate-intel.com
host www.corporate-intel.com

# Check from multiple locations
curl https://www.whatsmydns.net/api/check?server=google&query=corporate-intel.com&type=A
```

### Verify DNS Resolution from Different Geographic Locations

Use online tools:
- https://www.whatsmydns.net/
- https://dnschecker.org/
- https://mxtoolbox.com/SuperTool.aspx

### Expected Output

```text
corporate-intel.com. 300 IN A 203.0.113.45
www.corporate-intel.com. 300 IN CNAME corporate-intel.com.
```

## Advanced DNS Configuration

### Health Checks (AWS Route53)

```bash
# Create health check
aws route53 create-health-check \
  --type HTTPS \
  --resource-path "/health" \
  --fully-qualified-domain-name "corporate-intel.com" \
  --port 443 \
  --request-interval 30 \
  --failure-threshold 3
```

### Failover Configuration (Route53)

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "corporate-intel.com",
      "Type": "A",
      "SetIdentifier": "Primary",
      "Failover": "PRIMARY",
      "TTL": 60,
      "ResourceRecords": [{"Value": "203.0.113.45"}],
      "HealthCheckId": "your-health-check-id"
    }
  }]
}
```

### CDN Configuration (CloudFlare)

Enable CloudFlare CDN features:
1. SSL/TLS: Set to "Full (strict)"
2. Auto HTTPS Rewrites: On
3. Always Use HTTPS: On
4. HTTP Strict Transport Security (HSTS): Enable
5. Minimum TLS Version: TLS 1.2
6. Automatic HTTPS Rewrites: On

## Security Best Practices

### DNSSEC (Domain Name System Security Extensions)

#### Enable DNSSEC in Route53

```bash
# Enable DNSSEC
aws route53 enable-hosted-zone-dnssec \
  --hosted-zone-id $HOSTED_ZONE_ID

# Get DS records to add at registrar
aws route53 get-dnssec \
  --hosted-zone-id $HOSTED_ZONE_ID
```

#### Enable DNSSEC in CloudFlare

1. Navigate to DNS settings
2. Scroll to DNSSEC section
3. Click "Enable DNSSEC"
4. Add DS records to your registrar

### CAA Records (Certificate Authority Authorization)

```bash
# Allow Let's Encrypt to issue certificates
Type: CAA
Name: @ (or corporate-intel.com)
Value: 0 issue "letsencrypt.org"
TTL: 300

# Allow reporting of unauthorized certificate issuance
Type: CAA
Name: @ (or corporate-intel.com)
Value: 0 iodef "mailto:security@corporate-intel.com"
TTL: 300
```

#### Create CAA Record in Route53

```bash
aws route53 change-resource-record-sets \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "corporate-intel.com",
        "Type": "CAA",
        "TTL": 300,
        "ResourceRecords": [
          {"Value": "0 issue \"letsencrypt.org\""},
          {"Value": "0 iodef \"mailto:security@corporate-intel.com\""}
        ]
      }
    }]
  }'
```

## Monitoring DNS

### Set Up DNS Monitoring

```bash
# Create CloudWatch alarm for Route53 health check
aws cloudwatch put-metric-alarm \
  --alarm-name "dns-health-check-failed" \
  --alarm-description "Alert when DNS health check fails" \
  --metric-name HealthCheckStatus \
  --namespace AWS/Route53 \
  --statistic Minimum \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2
```

### DNS Query Logging (Route53)

```bash
# Enable query logging
aws route53 create-query-logging-config \
  --hosted-zone-id $HOSTED_ZONE_ID \
  --cloud-watch-logs-log-group-arn arn:aws:logs:us-east-1:123456789012:log-group:/aws/route53/corporate-intel.com
```

## Troubleshooting

### Common Issues

#### DNS Not Resolving

```bash
# Check nameservers
dig NS corporate-intel.com

# Verify nameservers are correct at registrar
whois corporate-intel.com | grep "Name Server"
```

#### DNS Propagation Delays

- DNS changes can take 24-48 hours to propagate globally
- Lower TTL values (300 seconds) before making changes
- Use `dig +trace` to see propagation path

```bash
dig +trace corporate-intel.com
```

#### SSL Certificate Issues with Let's Encrypt

```bash
# Verify DNS resolution
dig corporate-intel.com A

# Test ACME challenge accessibility
curl http://corporate-intel.com/.well-known/acme-challenge/test
```

## DNS Configuration Checklist

- [ ] Domain registered and accessible
- [ ] A record created pointing to server IP
- [ ] AAAA record created (if using IPv6)
- [ ] CNAME record for www subdomain
- [ ] Nameservers updated at registrar
- [ ] DNS propagation verified (whatsmydns.net)
- [ ] CAA records configured for Let's Encrypt
- [ ] DNSSEC enabled (optional but recommended)
- [ ] Health checks configured (Route53)
- [ ] DNS monitoring alerts set up
- [ ] TTL optimized (300s initially, 3600s after stabilization)
- [ ] Reverse DNS (PTR) configured (if applicable)

## Post-Configuration Verification

```bash
# Run comprehensive DNS check
dig corporate-intel.com A +short
dig corporate-intel.com AAAA +short
dig www.corporate-intel.com CNAME +short
dig corporate-intel.com CAA +short
dig corporate-intel.com NS +short

# Test SSL certificate after DNS is live
openssl s_client -connect corporate-intel.com:443 -servername corporate-intel.com < /dev/null

# Verify HTTP to HTTPS redirect
curl -I http://corporate-intel.com
```

## Automation Script

Create a DNS verification script:

```bash
#!/bin/bash
# scripts/deployment/verify-dns.sh

DOMAIN="$1"

echo "Verifying DNS configuration for $DOMAIN"

echo "1. Checking A record..."
dig "$DOMAIN" A +short

echo "2. Checking www CNAME..."
dig "www.$DOMAIN" CNAME +short

echo "3. Checking nameservers..."
dig "$DOMAIN" NS +short

echo "4. Checking CAA records..."
dig "$DOMAIN" CAA +short

echo "5. Testing HTTP connection..."
curl -I "http://$DOMAIN" 2>&1 | head -5

echo "DNS verification complete!"
```

## Support Resources

- AWS Route53 Documentation: https://docs.aws.amazon.com/route53/
- CloudFlare Documentation: https://developers.cloudflare.com/dns/
- Let's Encrypt Documentation: https://letsencrypt.org/docs/
- DNSSEC Information: https://www.icann.org/resources/pages/dnssec-what-is-it-why-important-2019-03-05-en

## Contact

For DNS configuration support:
- DevOps Team: devops@corporate-intel.com
- Emergency: Refer to runbook in `/docs/deployment/RUNBOOKS.md`
