# Corporate Intelligence Platform - Complete Deployment Plan

**Created:** 2025-10-03
**For:** Personal Use → Commercial SaaS Offering
**Current Status:** Production-Ready (8.2/10 health score)

---

## Executive Summary

Your platform is **production-ready** for personal use and can be running in **~2 hours**. Converting to a commercial SaaS offering will require **4-8 weeks** of development for multi-tenancy, billing, and infrastructure.

### Two-Path Approach

**Path A: Personal Use (TODAY)**
- Get it running for your own EdTech analysis
- Time: 2-4 hours
- Cost: $0-50/month (cloud hosting)

**Path B: Commercial SaaS (4-8 WEEKS)**
- Multi-tenant platform
- Subscription billing
- Public marketplace offering
- Time: 160-320 hours development
- Cost: $100-500/month infrastructure

---

## Path A: Personal Use Deployment (2-4 Hours)

### Quick Start Overview

```bash
# 1. Get API keys (30 min)
# 2. Configure environment (15 min)
# 3. Start Docker (10 min)
# 4. Verify deployment (15 min)
# Total: ~70 minutes
```

### Step 1: Obtain API Keys (30 minutes)

**Required (Free):**

1. **Alpha Vantage** (Stock market data)
   - Visit: https://www.alphavantage.co/support/#api-key
   - Free tier: 5 API calls/minute, 500 calls/day
   - Use: Real-time stock quotes for EdTech companies
   - Copy your API key → save it

2. **NewsAPI** (News aggregation)
   - Visit: https://newsapi.org/register
   - Free tier: 100 requests/day
   - Use: Sentiment analysis from news articles
   - Copy your API key → save it

3. **SEC EDGAR** (No API key needed)
   - Just need: Your email address
   - Format: `YourName/1.0 (your-email@example.com)`
   - Free and unlimited

**Optional (Paid/Free tiers):**
- GitHub Token: https://github.com/settings/tokens (free)
- Crunchbase: https://data.crunchbase.com (paid)

### Step 2: Configure Environment (15 minutes)

```bash
# Navigate to project
cd C:\Users\brand\Development\Project_Workspace\active-development\corporate_intel

# Copy example environment file
cp .env.example .env

# Generate secure passwords
# Run these commands to get random passwords:
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -base64 32  # For REDIS_PASSWORD
openssl rand -hex 32     # For SECRET_KEY
```

**Edit `.env` file:**

```env
# Environment
ENVIRONMENT=development
DEBUG=false

# Security (use generated passwords above)
SECRET_KEY=<your-generated-hex-key-64-chars>
POSTGRES_PASSWORD=<your-generated-password>
REDIS_PASSWORD=<your-generated-password>

# API Keys (from Step 1)
ALPHA_VANTAGE_API_KEY=<your-alpha-vantage-key>
NEWSAPI_KEY=<your-newsapi-key>
SEC_USER_AGENT=YourName/1.0 (your-email@example.com)

# Database
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_USER=intel_user
POSTGRES_DB=corporate_intel

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# MinIO
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minio_admin
MINIO_SECRET_KEY=<your-generated-password>
```

### Step 3: Start Docker Services (10 minutes)

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps

# Expected output: All services "Up (healthy)"
```

**Services Started:**
- PostgreSQL (TimescaleDB) → Port 5432
- Redis → Port 6379
- MinIO → Port 9000
- FastAPI → Port 8000
- Optional: Jaeger, Prometheus, Grafana

### Step 4: Initialize Database (5 minutes)

```bash
# Run migrations
docker exec corporate-intel-api alembic upgrade head

# Verify database
docker exec -it corporate-intel-postgres psql -U intel_user -d corporate_intel -c "\dt"
```

### Step 5: Verify Deployment (15 minutes)

```bash
# Check API health
curl http://localhost:8000/health

# Expected: {"status":"healthy","version":"1.0.0","environment":"development"}

# Test authentication
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"SecurePassword123!"}'

# Access interactive API docs
# Open browser: http://localhost:8000/api/v1/docs
```

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/v1/docs
- MinIO Console: http://localhost:9001
- Grafana (optional): http://localhost:3000

### Step 6: First Data Ingestion (30 minutes)

```bash
# Ingest EdTech companies from your watchlist
# Companies: CHGG, COUR, DUOL, TWOU, etc.

# Option A: Use the API
curl -X POST http://localhost:8000/api/v1/companies/ingest \
  -H "Authorization: Bearer <your-token>" \
  -H "Content-Type: application/json" \
  -d '{"tickers": ["CHGG", "COUR", "DUOL"]}'

# Option B: Run script directly
docker exec corporate-intel-api python scripts/run_ingestion_simple.py
```

### Personal Use Maintenance

**Daily:**
- Monitor API health: `curl http://localhost:8000/health`

**Weekly:**
- Update market data (automatic via cron or manual API call)
- Review logs: `docker-compose logs -f api`

**Monthly:**
- Backup database: `./scripts/backup.sh daily`
- Update dependencies: `docker-compose pull && docker-compose up -d`

**Costs (Personal Use):**
- Local machine: $0/month
- Cloud VM (8GB RAM, 4 CPU): $40-80/month
- API calls: $0-20/month (free tiers)

---

## Path B: Commercial SaaS Offering (4-8 Weeks)

### Phase 1: Multi-Tenancy Architecture (Week 1-2)

**Objective:** Isolate customer data and implement tenant-aware routing

**Technical Implementation:**

1. **Database Schema Updates**
```sql
-- Add tenant table
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    subdomain VARCHAR(63) UNIQUE,
    plan_tier VARCHAR(50) NOT NULL, -- free, pro, enterprise
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Add tenant_id to all tables
ALTER TABLE companies ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE filings ADD COLUMN tenant_id UUID REFERENCES tenants(id);
ALTER TABLE metrics ADD COLUMN tenant_id UUID REFERENCES tenants(id);

-- Create indexes
CREATE INDEX idx_companies_tenant ON companies(tenant_id);
CREATE INDEX idx_filings_tenant ON filings(tenant_id);
```

2. **Middleware for Tenant Context**
```python
# src/middleware/tenant_context.py
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract tenant from subdomain or header
        tenant_id = self.extract_tenant(request)

        # Add to request state
        request.state.tenant_id = tenant_id

        # Verify tenant is active
        if not await self.is_tenant_active(tenant_id):
            raise HTTPException(status_code=403, detail="Tenant inactive")

        response = await call_next(request)
        return response
```

3. **Tenant-Aware Repository Pattern**
```python
# src/db/repositories/base.py
class TenantRepository:
    def __init__(self, session, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id

    def filter_by_tenant(self, query):
        return query.filter_by(tenant_id=self.tenant_id)
```

**Deliverables:**
- Multi-tenant database schema
- Tenant middleware
- Tenant-aware repositories
- Data isolation tests

**Time Estimate:** 40-60 hours

### Phase 2: Billing & Subscriptions (Week 2-3)

**Objective:** Stripe integration for subscription management

**Pricing Model:**

```yaml
Plans:
  Free:
    price: $0/month
    features:
      - 5 companies tracked
      - 100 API calls/day
      - 7 days data retention
      - Basic dashboard

  Pro:
    price: $49/month
    features:
      - 50 companies tracked
      - 10,000 API calls/day
      - 2 years data retention
      - Advanced analytics
      - Export to CSV/Excel
      - Email alerts

  Enterprise:
    price: $299/month
    features:
      - Unlimited companies
      - Unlimited API calls
      - Unlimited data retention
      - Custom integrations
      - White-label option
      - Dedicated support
      - SLA guarantee
```

**Technical Implementation:**

1. **Stripe Integration**
```python
# src/billing/stripe_service.py
import stripe
from src.core.config import get_settings

stripe.api_key = get_settings().STRIPE_SECRET_KEY

class BillingService:
    async def create_subscription(self, tenant_id: UUID, plan: str):
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=tenant.email,
            metadata={"tenant_id": str(tenant_id)}
        )

        # Create subscription
        subscription = stripe.Subscription.create(
            customer=customer.id,
            items=[{"price": self.get_price_id(plan)}],
            metadata={"tenant_id": str(tenant_id)}
        )

        return subscription

    async def handle_webhook(self, payload, signature):
        # Handle subscription events
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )

        if event.type == "invoice.payment_succeeded":
            await self.activate_subscription(event.data)
        elif event.type == "invoice.payment_failed":
            await self.suspend_subscription(event.data)
```

2. **Usage Tracking & Rate Limiting**
```python
# src/middleware/usage_tracker.py
from redis import Redis
from datetime import datetime, timedelta

class UsageTracker:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def check_quota(self, tenant_id: UUID, plan: str):
        # Get usage for current billing period
        key = f"usage:{tenant_id}:{datetime.now().strftime('%Y-%m')}"
        usage = int(self.redis.get(key) or 0)

        # Get plan limits
        limit = self.get_plan_limit(plan)

        if usage >= limit:
            raise HTTPException(status_code=429, detail="Quota exceeded")

        # Increment usage
        self.redis.incr(key)
        self.redis.expire(key, timedelta(days=31))
```

**Deliverables:**
- Stripe integration
- Subscription management
- Usage tracking
- Billing webhooks
- Customer portal

**Time Estimate:** 50-70 hours

### Phase 3: User Management & Onboarding (Week 3-4)

**Objective:** Self-service signup and intuitive onboarding

**Features:**

1. **User Registration Flow**
```
Step 1: Email signup → Email verification
Step 2: Organization setup → Choose subdomain
Step 3: Plan selection → Payment (if paid)
Step 4: Initial configuration → API key generation
Step 5: Tutorial walkthrough → First data import
```

2. **Admin Dashboard**
```python
# New endpoints for tenant admins
@router.get("/admin/team")
async def list_team_members(tenant_id: UUID):
    """List all users in tenant organization"""
    pass

@router.post("/admin/team/invite")
async def invite_team_member(email: str, role: str, tenant_id: UUID):
    """Send email invitation to join organization"""
    pass

@router.get("/admin/usage")
async def get_usage_stats(tenant_id: UUID):
    """Get current billing period usage statistics"""
    pass

@router.get("/admin/billing")
async def get_billing_info(tenant_id: UUID):
    """Get subscription and payment information"""
    pass
```

3. **API Key Management**
```python
# src/auth/api_keys.py
class APIKeyService:
    async def create_api_key(self, tenant_id: UUID, name: str):
        # Generate secure API key
        key = secrets.token_urlsafe(32)
        hashed = bcrypt.hashpw(key.encode(), bcrypt.gensalt())

        # Store in database
        await self.db.api_keys.create({
            "tenant_id": tenant_id,
            "name": name,
            "key_hash": hashed,
            "created_at": datetime.now()
        })

        # Return key (only time it's visible)
        return f"ci_{key}"
```

**Deliverables:**
- User registration & verification
- Team management
- API key system
- Admin dashboard
- Onboarding tutorial

**Time Estimate:** 40-60 hours

### Phase 4: SaaS Infrastructure (Week 4-6)

**Objective:** Production deployment on cloud provider

**Infrastructure Architecture:**

```
┌─────────────────────────────────────────┐
│           Load Balancer (SSL)           │
│         (AWS ALB / CloudFlare)          │
└─────────────────┬───────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
┌─────▼──────┐        ┌──────▼──────┐
│  API Pod 1 │        │  API Pod 2  │
│  (ECS/K8s) │        │  (ECS/K8s)  │
└─────┬──────┘        └──────┬──────┘
      │                      │
      └──────────┬───────────┘
                 │
      ┌──────────▼─────────────┐
      │                        │
┌─────▼──────┐       ┌────────▼──────┐
│ PostgreSQL │       │  Redis Cache  │
│  (RDS/DO)  │       │  (ElastiCache)│
└────────────┘       └───────────────┘
```

**Deployment Options:**

**Option A: AWS (Recommended for Scale)**
- **Compute:** ECS Fargate (auto-scaling)
- **Database:** RDS PostgreSQL with TimescaleDB
- **Cache:** ElastiCache Redis
- **Storage:** S3 (instead of MinIO)
- **CDN:** CloudFront
- **Monitoring:** CloudWatch + Datadog
- **Cost:** ~$200-400/month base + usage

**Option B: DigitalOcean (Budget-Friendly)**
- **Compute:** App Platform (auto-deploy from GitHub)
- **Database:** Managed PostgreSQL
- **Cache:** Managed Redis
- **Storage:** Spaces (S3-compatible)
- **CDN:** Spaces CDN
- **Monitoring:** Built-in
- **Cost:** ~$100-200/month base

**Option C: Google Cloud Platform**
- **Compute:** Cloud Run (serverless)
- **Database:** Cloud SQL PostgreSQL
- **Cache:** Memorystore Redis
- **Storage:** Cloud Storage
- **CDN:** Cloud CDN
- **Monitoring:** Cloud Monitoring
- **Cost:** ~$150-350/month base

**Infrastructure as Code (Terraform):**

```hcl
# terraform/main.tf
module "vpc" {
  source = "./modules/vpc"
  name   = "corporate-intel"
  cidr   = "10.0.0.0/16"
}

module "database" {
  source          = "./modules/rds"
  instance_class  = "db.t3.medium"
  engine_version  = "15.3"
  multi_az        = true
}

module "ecs" {
  source         = "./modules/ecs"
  cluster_name   = "corporate-intel-prod"
  desired_count  = 2
  cpu            = 1024
  memory         = 2048
}

module "alb" {
  source          = "./modules/alb"
  certificate_arn = aws_acm_certificate.main.arn
  subnets         = module.vpc.public_subnets
}
```

**CI/CD Pipeline (GitHub Actions):**

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run Tests
        run: |
          docker-compose -f docker-compose.test.yml up --abort-on-container-exit

      - name: Build Docker Image
        run: |
          docker build -t corporate-intel:${{ github.sha }} .

      - name: Push to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin
          docker push corporate-intel:${{ github.sha }}

      - name: Deploy to ECS
        run: |
          aws ecs update-service --cluster prod --service api --force-new-deployment
```

**Deliverables:**
- Cloud infrastructure setup
- Auto-scaling configuration
- SSL certificates
- Monitoring & alerting
- CI/CD pipeline
- Disaster recovery plan

**Time Estimate:** 50-80 hours

### Phase 5: Marketing & Launch (Week 6-8)

**Objective:** Create public presence and acquire first customers

**1. Landing Page (Next.js/React)**

```jsx
// pages/index.tsx
export default function LandingPage() {
  return (
    <>
      <Hero>
        <h1>EdTech Intelligence Platform</h1>
        <p>Track, analyze, and predict trends in education technology companies</p>
        <CTAButton>Start Free Trial</CTAButton>
      </Hero>

      <Features>
        <Feature icon="📊">
          <h3>Real-Time Market Data</h3>
          <p>SEC filings, stock quotes, and news aggregation</p>
        </Feature>
        <Feature icon="🧠">
          <h3>AI-Powered Insights</h3>
          <p>Semantic search and sentiment analysis</p>
        </Feature>
        <Feature icon="📈">
          <h3>Custom Dashboards</h3>
          <p>Interactive visualizations and reports</p>
        </Feature>
      </Features>

      <Pricing />
      <Testimonials />
      <FAQ />
    </>
  );
}
```

**2. Documentation Site (Docusaurus/GitBook)**

```markdown
# Quick Start Guide

## 1. Sign Up
Create your account at https://app.corporate-intel.io

## 2. Get API Key
Navigate to Settings → API Keys → Create New Key

## 3. Make Your First Request
```bash
curl -X GET https://api.corporate-intel.io/v1/companies \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 4. Explore the Dashboard
Visit https://app.corporate-intel.io/dashboard
```

**3. Content Marketing**

- **Blog Posts:**
  - "Top 10 EdTech Companies to Watch in 2025"
  - "How to Analyze EdTech Company Fundamentals"
  - "Using APIs for Educational Technology Research"

- **Case Studies:**
  - "How VCs Use Our Platform for Due Diligence"
  - "Academic Researchers Track EdTech Trends"

- **Video Tutorials:**
  - Platform walkthrough (YouTube)
  - API integration guide
  - Dashboard customization

**4. Launch Checklist**

```markdown
Pre-Launch (2 weeks before):
- [ ] Beta test with 5-10 users
- [ ] Fix critical bugs
- [ ] Write launch announcement
- [ ] Prepare social media posts
- [ ] Set up customer support (Intercom/Zendesk)

Launch Day:
- [ ] Deploy to production
- [ ] Post on Product Hunt
- [ ] Share on LinkedIn, Twitter
- [ ] Send email to beta list
- [ ] Monitor for issues

Post-Launch (2 weeks after):
- [ ] Collect user feedback
- [ ] Fix reported bugs
- [ ] Iterate on onboarding
- [ ] Publish case studies
```

**5. Legal & Compliance**

```markdown
Required Documents:
- [ ] Terms of Service
- [ ] Privacy Policy
- [ ] Data Processing Agreement (GDPR)
- [ ] Cookie Policy
- [ ] SLA (for Enterprise plan)
- [ ] Acceptable Use Policy
```

**Deliverables:**
- Landing page
- Documentation site
- Pricing page
- Blog/content
- Legal documents
- Launch plan

**Time Estimate:** 30-50 hours

---

## Cost Breakdown

### Personal Use
- **Development:** 2-4 hours (your time)
- **Hosting:** $0-80/month
  - Local: $0
  - Cloud VM (DigitalOcean): $40/month
  - Cloud VM (AWS EC2): $60-80/month
- **API Costs:** $0-20/month (free tiers)
- **Total:** $0-100/month

### Commercial SaaS

**Development (One-Time):**
- Phase 1 (Multi-tenancy): 40-60 hours @ $100-150/hr = $4,000-9,000
- Phase 2 (Billing): 50-70 hours @ $100-150/hr = $5,000-10,500
- Phase 3 (User Management): 40-60 hours @ $100-150/hr = $4,000-9,000
- Phase 4 (Infrastructure): 50-80 hours @ $100-150/hr = $5,000-12,000
- Phase 5 (Marketing): 30-50 hours @ $100-150/hr = $3,000-7,500
- **Total Development:** $21,000-48,000

**OR Self-Development:** 210-320 hours over 8-12 weeks

**Monthly Operating Costs:**
- Infrastructure (AWS/DO): $200-500/month
- Monitoring (Datadog/New Relic): $50-200/month
- Customer Support (Intercom): $65/month
- Email (SendGrid): $20-100/month
- Domain + SSL: $15/month
- Stripe fees: 2.9% + $0.30 per transaction
- **Total:** $350-880/month base

**Break-Even Analysis:**

```
Monthly Costs: $500/month
Pro Plan: $49/month

Break-even: 11 customers
Good traction: 50 customers = $2,450/month revenue
Sustainable: 100 customers = $4,900/month revenue
Success: 500 customers = $24,500/month revenue
```

---

## Recommended Next Steps

### For Personal Use (Do This Week):

1. **Day 1 (2 hours):**
   - Get API keys (Alpha Vantage, NewsAPI)
   - Configure .env file
   - Start Docker containers
   - Run migrations

2. **Day 2 (1 hour):**
   - Test API endpoints
   - Import first company data
   - Explore dashboard

3. **Day 3 onwards:**
   - Use regularly for EdTech analysis
   - Track companies of interest
   - Generate reports

### For Commercial Offering (8-Week Plan):

**Week 1-2:** Multi-tenancy architecture
**Week 3-4:** Billing & subscriptions
**Week 5-6:** Infrastructure & deployment
**Week 7:** Marketing materials
**Week 8:** Beta testing & launch

**OR Hire Development:**
- Budget: $25,000-50,000
- Timeline: 8-12 weeks
- Outcome: Fully operational SaaS

---

## Questions to Consider

**Before Going Commercial:**

1. **Market Validation:**
   - Who is your target customer? (VCs, researchers, financial analysts?)
   - What's your unique value proposition?
   - Are competitors offering similar services?
   - What's your pricing strategy?

2. **Business Model:**
   - B2B or B2C or both?
   - Freemium or paid-only?
   - Annual vs monthly pricing?
   - Enterprise custom pricing?

3. **Resources:**
   - Full-time or side project?
   - Solo or team?
   - Bootstrap or fundraise?
   - Marketing budget?

4. **Legal:**
   - Business entity (LLC/Corp)?
   - Data compliance (GDPR, CCPA)?
   - Liability insurance?
   - Terms of service?

---

## Conclusion

**For Personal Use:**
- You can be up and running **TODAY** in 2-4 hours
- Cost: $0-100/month
- Perfect for: Personal research, learning, portfolio

**For Commercial SaaS:**
- Realistic timeline: **8-12 weeks**
- Development: 210-320 hours OR $21k-48k to hire
- Monthly costs: $350-880
- Break-even: ~11 paying customers
- Potential: $10k-100k+ MRR at scale

**My Recommendation:**

1. **Start with personal use this week** to:
   - Validate the platform works
   - Understand user workflows
   - Identify what features matter most
   - Get comfortable with the stack

2. **While using it personally**, research:
   - Potential customers (talk to 20-30)
   - Competitors (what they charge, features)
   - Market size and demand
   - Marketing channels

3. **After 1-2 months of validation**, decide:
   - Build commercial version yourself (8-12 weeks)
   - Hire developers ($25k-50k)
   - Keep as personal tool
   - Open source it

**Want me to help with any specific phase?** I can:
- Generate the multi-tenancy code
- Create Stripe integration
- Build Terraform infrastructure
- Design pricing tiers
- Write marketing copy
- Whatever you need next!
