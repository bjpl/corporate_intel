# Corporate Intelligence Platform - Complete Deployment Walkthrough

**Last Updated**: 2025-10-03
**Estimated Total Time**: 2-4 hours (depending on experience level)

This guide separates **MANUAL** actions (you must do) from **AUTOMATED** tasks (I can do programmatically).

---

## Table of Contents

1. [Prerequisites & Setup (30 min)](#phase-1-prerequisites--setup)
2. [Local Environment Configuration (15 min)](#phase-2-local-environment-configuration)
3. [Security & Secrets Setup (45 min)](#phase-3-security--secrets-setup)
4. [Development Testing (30 min)](#phase-4-development-testing)
5. [Production Deployment (60 min)](#phase-5-production-deployment)
6. [Post-Deployment Verification (30 min)](#phase-6-post-deployment-verification)

---

## Phase 1: Prerequisites & Setup (30 min)

### 🔴 MANUAL - Install Required Tools

You need to install these tools on your deployment server/machine:

#### 1.1 Install Docker & Docker Compose
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

**Expected Output**:
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

#### 1.2 Install Certbot (for SSL certificates)
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y certbot

# Verify
certbot --version
```

#### 1.3 Install HashiCorp Vault (OPTIONAL - for secrets management)
```bash
# Install Vault
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install vault

# Verify
vault version
```

#### 1.4 Set Up Firewall Rules
```bash
# Ubuntu/Debian with UFW
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw enable

# Verify
sudo ufw status
```

**Expected Output**:
```
Status: active
To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### 🟢 AUTOMATED - I Can Help With

I can create automated installation scripts for you:
- ✅ Script to check if all prerequisites are installed
- ✅ Script to install missing dependencies
- ✅ Script to validate server resources (CPU, RAM, disk)

**Would you like me to create these now?** (Say "yes" to proceed)

---

## Phase 2: Local Environment Configuration (15 min)

### 🔴 MANUAL - Obtain External API Keys

You need to manually register and obtain API keys from these services:

#### 2.1 Alpha Vantage (Stock Market Data)
1. Go to: https://www.alpha vantage.co/support/#api-key
2. Fill out the form with your email
3. Copy your API key
4. **SAVE IT** - You'll add it to `.env` later

#### 2.2 NewsAPI (News Articles)
1. Go to: https://newsapi.org/register
2. Create a free account
3. Copy your API key from the dashboard
4. **SAVE IT** - You'll add it to `.env` later

#### 2.3 SEC EDGAR User Agent
1. Use this format: `YourCompanyName/1.0 (your-email@example.com)`
2. Example: `Acme Corp/1.0 (admin@acmecorp.com)`
3. **SAVE IT** - You'll add it to `.env` later

### 🟢 AUTOMATED - I Can Configure

I can programmatically:
- ✅ Generate a `.env` file template with placeholders
- ✅ Generate secure random passwords for databases
- ✅ Create a `.env.production` file with Vault integration
- ✅ Add validation to ensure no placeholder values remain

**Would you like me to create these configuration files now?** (Say "yes" to proceed)

---

## Phase 3: Security & Secrets Setup (45 min)

### 🔴 MANUAL - Generate Production Secrets

You need to generate secure secrets for production:

#### 3.1 Generate Random Passwords
Run these commands **on your local machine** (don't run on production server yet):

```bash
# Generate PostgreSQL password
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)"

# Generate Redis password
echo "REDIS_PASSWORD=$(openssl rand -base64 32)"

# Generate MinIO credentials
echo "MINIO_ROOT_PASSWORD=$(openssl rand -base64 32)"

# Generate JWT secret key (64 characters minimum)
echo "SECRET_KEY=$(openssl rand -hex 32)"

# Generate Grafana admin password
echo "GRAFANA_PASSWORD=$(openssl rand -base64 16)"
```

**IMPORTANT**: Copy these outputs to a **secure password manager** or encrypted file. You'll need them next.

#### 3.2 Update Environment Files

Open `.env.production` and replace these placeholders:

```bash
# Use a secure text editor
nano .env.production

# Replace these values with the passwords you just generated:
POSTGRES_PASSWORD=REPLACE_WITH_YOUR_GENERATED_PASSWORD
REDIS_PASSWORD=REPLACE_WITH_YOUR_GENERATED_REDIS_PASSWORD
MINIO_ROOT_PASSWORD=REPLACE_WITH_YOUR_GENERATED_MINIO_PASSWORD
SECRET_KEY=REPLACE_WITH_YOUR_GENERATED_SECRET_KEY
GRAFANA_PASSWORD=REPLACE_WITH_YOUR_GENERATED_GRAFANA_PASSWORD

# Add your API keys from Phase 2:
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key_here
NEWSAPI_KEY=your_newsapi_key_here
SEC_USER_AGENT=YourCompany/1.0 (your-email@example.com)
```

**Save and close the file** (Ctrl+X, then Y, then Enter in nano)

### 🟢 AUTOMATED - I Can Set Up

I can programmatically:
- ✅ Generate all random passwords and save them to a secure file
- ✅ Create a secrets validation script
- ✅ Set up Vault configuration files
- ✅ Create scripts to migrate secrets to Vault
- ✅ Generate backup encryption keys

**Would you like me to create automated secret generation scripts?** (Say "yes" to proceed)

---

## Phase 4: Development Testing (30 min)

### 🔴 MANUAL - Test Locally First

Before deploying to production, test everything locally:

#### 4.1 Start Development Environment
```bash
# Make sure you're in the project directory
cd /mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel

# Start all services
docker-compose up -d

# Watch the logs
docker-compose logs -f api
```

**Expected Output**:
```
corporate-intel-api    | INFO:     Started server process
corporate-intel-api    | INFO:     Waiting for application startup.
corporate-intel-api    | INFO:     Application startup complete.
corporate-intel-api    | INFO:     Uvicorn running on http://0.0.0.0:8000
```

Press `Ctrl+C` to stop watching logs.

#### 4.2 Test API Health
```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected output:
# {"status":"healthy","version":"1.0.0","database":"connected"}
```

#### 4.3 Test Database Connection
```bash
# Connect to PostgreSQL
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel

# Run a test query
\dt  # List tables

# Exit
\q
```

### 🟢 AUTOMATED - I Can Test

I can programmatically:
- ✅ Run automated health checks on all services
- ✅ Execute database migration tests
- ✅ Run API endpoint integration tests
- ✅ Generate test reports
- ✅ Validate all configurations

**Would you like me to run automated tests now?** (Say "yes" to proceed)

---

## Phase 5: Production Deployment (60 min)

### 🔴 MANUAL - Server Preparation

#### 5.1 Set Up Production Server

**If using a cloud provider (AWS/DigitalOcean/Linode)**:

1. Create a new VM instance:
   - **OS**: Ubuntu 22.04 LTS
   - **RAM**: 8GB minimum (16GB recommended)
   - **CPU**: 4 cores minimum
   - **Disk**: 100GB SSD minimum
   - **Network**: Static IP address

2. SSH into your server:
   ```bash
   ssh root@your-server-ip
   ```

3. Create a non-root user:
   ```bash
   adduser deploy
   usermod -aG sudo deploy
   usermod -aG docker deploy

   # Switch to deploy user
   su - deploy
   ```

#### 5.2 Clone Repository to Production Server
```bash
# On production server as deploy user
cd ~
git clone https://github.com/YOUR_USERNAME/corporate_intel.git
cd corporate_intel
```

#### 5.3 Copy Environment Files
```bash
# On your LOCAL machine, copy .env.production to server
scp .env.production deploy@your-server-ip:~/corporate_intel/.env.production

# Verify file was copied
ssh deploy@your-server-ip "cat ~/corporate_intel/.env.production | head -5"
```

### 🔴 MANUAL - SSL Certificate Setup

#### 5.4 Generate SSL Certificates

**Option A: Let's Encrypt (Recommended - Free)**

```bash
# On production server
# Replace your-domain.com with your actual domain

# Stop nginx if running
sudo systemctl stop nginx 2>/dev/null || true

# Generate certificate
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --non-interactive \
  --agree-tos \
  --email your-email@example.com

# Certificates will be saved to:
# /etc/letsencrypt/live/your-domain.com/fullchain.pem
# /etc/letsencrypt/live/your-domain.com/privkey.pem
```

**Option B: Self-Signed Certificate (Testing Only)**

```bash
# On production server
sudo mkdir -p /etc/ssl/corporate-intel
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/corporate-intel/privkey.pem \
  -out /etc/ssl/corporate-intel/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

#### 5.5 Update Nginx Configuration

Edit the nginx configuration to point to your certificates:

```bash
# On production server
cd ~/corporate_intel
nano config/nginx.conf

# Update these lines (around line 15-16):
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

# Save and exit (Ctrl+X, Y, Enter)
```

### 🟢 AUTOMATED - I Can Deploy

I can programmatically:
- ✅ Create deployment automation scripts
- ✅ Generate Docker Compose production configurations
- ✅ Set up automated SSL renewal
- ✅ Create rollback scripts
- ✅ Generate deployment checklists

**Would you like me to create production deployment scripts?** (Say "yes" to proceed)

---

## Phase 6: Post-Deployment Verification (30 min)

### 🔴 MANUAL - Verify Deployment

#### 6.1 Start Production Services
```bash
# On production server
cd ~/corporate_intel

# Start all services in production mode
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

# Check status
docker-compose -f docker-compose.prod.yml ps
```

**Expected Output**: All services should show "Up" status.

#### 6.2 Check Service Health
```bash
# Check API health (internal)
docker exec corporate-intel-api curl -f http://localhost:8000/health

# Check API health (external via nginx)
curl https://your-domain.com/health

# Check database
docker exec corporate-intel-postgres pg_isready -U intel_user

# Check Redis
docker exec corporate-intel-redis redis-cli ping
```

**Expected Outputs**:
- API: `{"status":"healthy",...}`
- Database: `postgres (intel_user) - accepting connections`
- Redis: `PONG`

#### 6.3 Test SSL Certificate
```bash
# Check SSL certificate validity
curl -vI https://your-domain.com 2>&1 | grep "SSL certificate verify"

# Or use online tool:
# Visit: https://www.ssllabs.com/ssltest/analyze.html?d=your-domain.com
```

**Expected**: SSL certificate verify ok

#### 6.4 Set Up Automated Backups
```bash
# On production server
# Make scripts executable
chmod +x ~/corporate_intel/scripts/backup.sh
chmod +x ~/corporate_intel/scripts/restore.sh

# Add to crontab
crontab -e

# Add these lines:
0 2 * * * /home/deploy/corporate_intel/scripts/backup.sh daily >> /var/log/backup.log 2>&1
0 3 * * 0 /home/deploy/corporate_intel/scripts/backup.sh weekly >> /var/log/backup.log 2>&1
0 4 1 * * /home/deploy/corporate_intel/scripts/backup.sh monthly >> /var/log/backup.log 2>&1

# Save and exit
```

#### 6.5 Configure Monitoring Alerts
```bash
# Access Grafana
# Open browser: https://your-domain.com/grafana
# Username: admin
# Password: (from your .env.production GRAFANA_PASSWORD)

# Import dashboards:
# 1. Go to Dashboards > Import
# 2. Upload JSON files from monitoring/grafana/dashboards/
```

### 🟢 AUTOMATED - I Can Monitor

I can programmatically:
- ✅ Run comprehensive deployment validation
- ✅ Set up automated health monitoring
- ✅ Configure alerting rules
- ✅ Generate deployment reports
- ✅ Create monitoring dashboards

**Would you like me to run automated validation?** (Say "yes" to proceed)

---

## Quick Command Reference

### Common Operations

**Start Services**:
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d
```

**Stop Services**:
```bash
docker-compose -f docker-compose.prod.yml down
```

**View Logs**:
```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

**Restart API Only**:
```bash
docker-compose -f docker-compose.prod.yml restart api
```

**Run Database Migrations**:
```bash
docker exec corporate-intel-api alembic upgrade head
```

**Create Database Backup**:
```bash
./scripts/backup.sh daily
```

**Restore from Backup**:
```bash
./scripts/restore.sh /path/to/backup/directory
```

---

## Troubleshooting

### Services Won't Start

**Symptom**: Docker containers exit immediately

**Solution**:
```bash
# Check logs for errors
docker-compose -f docker-compose.prod.yml logs api

# Common issues:
# 1. Database connection failed → Check POSTGRES_* credentials
# 2. Redis connection failed → Check REDIS_PASSWORD
# 3. Port already in use → Check if another service is using port 8000
```

### SSL Certificate Errors

**Symptom**: Browser shows "Not Secure" warning

**Solution**:
```bash
# Verify certificate files exist
sudo ls -la /etc/letsencrypt/live/your-domain.com/

# Renew certificate
sudo certbot renew

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

### Database Connection Issues

**Symptom**: API can't connect to database

**Solution**:
```bash
# Check if database is running
docker ps | grep postgres

# Check database logs
docker logs corporate-intel-postgres

# Test connection manually
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel -c "SELECT 1;"
```

---

## Next Steps After Deployment

1. **Set Up Monitoring Alerts**
   - Configure Prometheus alert rules
   - Set up Slack/email notifications

2. **Performance Tuning**
   - Review PostgreSQL query performance
   - Adjust Redis cache hit rates
   - Optimize API response times

3. **Security Hardening**
   - Enable Vault for secrets rotation
   - Set up fail2ban for SSH protection
   - Configure backup encryption

4. **Documentation**
   - Document custom configurations
   - Create runbooks for common operations
   - Train team on deployment procedures

---

## Summary: What's Manual vs Automated

### 🔴 YOU MUST DO MANUALLY:
1. Install Docker, Certbot, Vault on servers
2. Obtain external API keys (Alpha Vantage, NewsAPI)
3. Generate production passwords
4. Update `.env.production` with real credentials
5. Set up production server (VM creation, SSH)
6. Generate SSL certificates
7. Start production services
8. Configure monitoring dashboards
9. Set up cron jobs for backups

### 🟢 I CAN DO PROGRAMMATICALLY:
1. Create installation validation scripts
2. Generate `.env` templates with placeholders
3. Create automated secret generation scripts
4. Run health checks and integration tests
5. Create deployment automation scripts
6. Generate deployment checklists
7. Run automated validation suites
8. Create monitoring configurations
9. Generate documentation and reports

---

**Ready to begin?** Let me know which automated tasks you'd like me to create first!
