# Get Corporate Intel Running TODAY

**Goal:** Working API with database in 2-3 hours

---

## Quick Start (Choose Your Path)

### Path 1: Automated (Recommended) ⚡

**Run one command, get coffee, come back to working system:**

```bash
# Linux/Mac/Git Bash
./scripts/quick-startup.sh

# Windows Command Prompt
scripts\quick-startup.bat
```

**Time:** 30-45 minutes (mostly automated waiting)

---

### Path 2: Manual (Step-by-Step) 📋

Follow the checklist for complete control:

**[→ View Startup Checklist](./STARTUP_CHECKLIST.md)**

**Time:** 2-3 hours (includes troubleshooting time)

---

### Path 3: Detailed Plan (Deep Dive) 📖

For those who want to understand every step:

**[→ View Detailed Quick Start Plan](./QUICK_START_PLAN.md)**

**Time:** 2-3 hours (detailed explanations)

---

## Prerequisites

Before starting, make sure you have:

- [ ] Docker installed and running
- [ ] Docker Compose installed
- [ ] `.env` file in project root (copy from `.env.example` if needed)
- [ ] Git Bash or WSL (on Windows)

---

## The Fastest Path to Success

**60-Second Version:**

```bash
# 1. Start infrastructure
docker-compose up -d postgres redis

# 2. Wait 30 seconds
sleep 30

# 3. Build and migrate
docker-compose build api
docker-compose run --rm api alembic upgrade head

# 4. Start API
docker-compose up -d api

# 5. Test it works
curl http://localhost:8002/health
```

**Open:** http://localhost:8002/api/v1/docs

---

## What You'll Have When Done

**Running Services:**
- PostgreSQL with TimescaleDB (database)
- Redis (caching)
- FastAPI (REST API)

**Available at:**
- API Documentation: http://localhost:8002/api/v1/docs
- Health Check: http://localhost:8002/health
- Metrics: http://localhost:8002/metrics

**Can Do:**
- Register and authenticate users
- Query company data
- Access SEC filings
- Analyze financial metrics
- Generate intelligence reports

---

## If Something Goes Wrong

**[→ Troubleshooting Guide](./TROUBLESHOOTING.md)**

Common fixes:
- Port conflicts → Change ports in `.env`
- Database errors → Wait 30s and retry
- Build errors → `docker-compose build --no-cache api`
- Any errors → Check `docker-compose logs -f`

---

## File Guide

| File | Purpose | When to Use |
|------|---------|-------------|
| `GET_STARTED_TODAY.md` | This file - quick overview | Starting point |
| `STARTUP_CHECKLIST.md` | Step-by-step manual checklist | Manual startup |
| `QUICK_START_PLAN.md` | Detailed phased plan | Deep understanding |
| `TROUBLESHOOTING.md` | Problem solutions | When stuck |
| `scripts/quick-startup.sh` | Automated script | Fast automated startup |
| `scripts/quick-startup.bat` | Windows batch script | Windows users |

---

## Success Checklist

You're done when all of these work:

```bash
# 1. Health check
curl http://localhost:8002/health
# → {"status": "healthy"}

# 2. Database health
curl http://localhost:8002/health/database
# → {"status": "healthy", "database": "connected"}

# 3. API docs load
open http://localhost:8002/api/v1/docs
# → Interactive API documentation

# 4. Register a user
curl -X POST http://localhost:8002/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!","full_name":"Test User"}'
# → Returns user object

# 5. Query companies
curl http://localhost:8002/api/v1/companies \
  -H "Authorization: Bearer YOUR_TOKEN"
# → Returns company list
```

---

## Quick Commands

```bash
# View status
docker-compose ps

# View logs
docker-compose logs -f api

# Restart API
docker-compose restart api

# Stop everything
docker-compose down

# Emergency reset (deletes data!)
docker-compose down -v
```

---

## What Can Wait (Not Needed Today)

**Skip these for initial startup:**
- MinIO (object storage)
- Jaeger (tracing)
- Prometheus/Grafana (monitoring)
- Data ingestion scripts
- SSL certificates
- Production optimizations

**Focus on:**
- Database up and running
- API responding
- Basic CRUD operations

---

## Time Budget

**Automated Path:**
- Setup: 5 min
- Waiting: 30 min
- Testing: 10 min
- **Total: ~45 min**

**Manual Path:**
- Infrastructure: 30 min
- Database: 20 min
- API: 20 min
- Testing: 30 min
- **Total: ~100 min (1.5 hours)**

**With Troubleshooting:**
- Add 30-60 min buffer
- **Total: 2-3 hours**

---

## Next Steps After Startup

Once you have a working system:

1. **Explore the API**
   - Try all endpoints in the docs
   - Test authentication flow
   - Query company data

2. **Add Your Data**
   - Import company listings
   - Fetch SEC filings
   - Ingest financial metrics

3. **Customize**
   - Add your API keys to `.env`
   - Configure data sources
   - Set up scheduled tasks

4. **Deploy**
   - Set up staging environment
   - Configure production settings
   - Deploy to cloud

---

## Support

**Documentation:**
- [Startup Checklist](./STARTUP_CHECKLIST.md) - Manual steps
- [Quick Start Plan](./QUICK_START_PLAN.md) - Detailed phases
- [Troubleshooting](./TROUBLESHOOTING.md) - Problem solutions

**Quick Help:**
```bash
# Check logs
docker-compose logs -f

# Check status
docker-compose ps

# Test health
curl http://localhost:8002/health
```

---

## TL;DR - Just Get It Running

**Shortest possible path:**

```bash
./scripts/quick-startup.sh
```

**Or manually:**

```bash
docker-compose up -d postgres redis && \
sleep 30 && \
docker-compose build api && \
docker-compose run --rm api alembic upgrade head && \
docker-compose up -d api && \
sleep 20 && \
curl http://localhost:8002/health
```

**Then visit:** http://localhost:8002/api/v1/docs

---

**Ready? Pick a path above and get started! 🚀**
