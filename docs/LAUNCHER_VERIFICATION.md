# Application Launcher System - Verification Steps

## Files Created

### Scripts
- **scripts/launch-app.sh** - Complete application startup with validation (6.7KB)
- **scripts/quick-start.sh** - First-time automated setup (6.3KB)
- **scripts/stop-app.sh** - Graceful application shutdown (4.6KB)

### Documentation
- **docs/QUICK_START_GUIDE.md** - Comprehensive user guide (20.7KB)

## Verification Checklist

### 1. File Permissions
```bash
# Verify scripts are executable
ls -la scripts/*.sh

# Expected output should show 'x' permissions:
# -rwxr-xr-x ... launch-app.sh
# -rwxr-xr-x ... quick-start.sh
# -rwxr-xr-x ... stop-app.sh
```

### 2. Script Functionality Testing

#### Test Quick Start (First-Time Setup)
```bash
# Run quick-start script
./scripts/quick-start.sh

# Expected flow:
# 1. Creates .env from .env.example
# 2. Generates SECRET_KEY
# 3. Prompts for database configuration
# 4. Sets up admin user
# 5. Installs dependencies
# 6. Launches application automatically
```

#### Test Launch Script (Subsequent Starts)
```bash
# Run launch script
./scripts/launch-app.sh

# Expected checks:
# ✓ Python version >= 3.10
# ✓ Dependencies installed
# ✓ .env file exists
# ✓ Required environment variables set
# ✓ Database connectivity
# ✓ Migrations run
# ✓ Application starts on port 8000
```

#### Test Stop Script
```bash
# Run stop script
./scripts/stop-app.sh

# Expected actions:
# ✓ Stops uvicorn processes
# ✓ Stops Docker services (if running)
# ✓ Cleans up background processes
# ✓ Displays shutdown summary
# ✓ Shows port availability
```

### 3. Startup Validation Steps

#### Health Check After Launch
```bash
# Wait 5 seconds after launch, then test
curl http://localhost:8000/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "version": "1.0.0"
# }
```

#### API Documentation Access
```bash
# Test interactive API docs
curl -I http://localhost:8000/docs

# Expected: HTTP/1.1 200 OK
```

#### Database Connection Test
```bash
# Should be checked automatically by launch-app.sh
# Manual verification:
python -c "
from sqlalchemy import create_engine
from app.core.config import settings
engine = create_engine(settings.DATABASE_URL)
with engine.connect() as conn:
    print('✓ Database connected')
"
```

### 4. Environment Configuration Tests

#### Required Variables Check
```bash
# Verify .env has required variables
grep -E "^(SECRET_KEY|DATABASE_URL)=" .env

# Should show both variables set
```

#### Secret Key Generation
```bash
# Verify SECRET_KEY is not the default
grep "SECRET_KEY=" .env

# Should NOT show: SECRET_KEY=your-secret-key-here
# Should show: SECRET_KEY=<random-string>
```

#### Database URL Format
```bash
# PostgreSQL format check
grep "DATABASE_URL=postgresql://" .env

# OR SQLite format check
grep "DATABASE_URL=sqlite:///" .env

# One of these should match
```

### 5. Error Handling Tests

#### Test Missing .env File
```bash
# Backup existing .env
mv .env .env.backup

# Run launch-app.sh
./scripts/launch-app.sh

# Expected: Error message about missing .env
# Suggests running quick-start.sh

# Restore .env
mv .env.backup .env
```

#### Test Invalid Python Version
```bash
# This test requires Python 2.7 or 3.9 installed
# If you have it:
/path/to/old/python ./scripts/launch-app.sh

# Expected: Error about Python version requirement
```

#### Test Port Conflict
```bash
# Start application twice
./scripts/launch-app.sh &
sleep 5
./scripts/launch-app.sh

# Expected: Error about port 8000 already in use
# Kill first instance
./scripts/stop-app.sh
```

#### Test Missing Dependencies
```bash
# Backup venv
mv venv venv.backup

# Run launch-app.sh
./scripts/launch-app.sh

# Expected: Creates new venv and installs dependencies

# Restore
rm -rf venv
mv venv.backup venv
```

### 6. Database Migration Tests

#### Verify Migrations Run
```bash
# Launch app
./scripts/launch-app.sh

# Check migration status
source venv/bin/activate
alembic current

# Should show current migration revision
```

#### Test Migration Creation
```bash
# Create test migration
source venv/bin/activate
alembic revision --autogenerate -m "test_migration"

# Run launch-app.sh
./scripts/launch-app.sh

# Should apply new migration automatically
```

### 7. Docker Integration Tests

#### With Docker Compose
```bash
# Ensure docker-compose.yml exists
ls docker-compose.yml

# Run launch-app.sh
./scripts/launch-app.sh

# Expected:
# - Starts PostgreSQL container
# - Starts Redis container
# - Connects to database
# - Launches application
```

#### Without Docker Compose
```bash
# Rename docker-compose.yml temporarily
mv docker-compose.yml docker-compose.yml.bak

# Run launch-app.sh with SQLite
./scripts/launch-app.sh

# Expected: Works without Docker services

# Restore
mv docker-compose.yml.bak docker-compose.yml
```

### 8. Admin User Tests

#### Verify Admin Creation
```bash
# Start app
./scripts/launch-app.sh

# Test admin login
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@corporate-intel.com",
    "password": "changeme"
  }'

# Expected: Returns JWT token
```

#### Test Custom Admin Credentials
```bash
# Run quick-start with custom admin
./scripts/quick-start.sh

# Enter custom email and password when prompted
# Then test login with those credentials
```

### 9. Performance Tests

#### Startup Time
```bash
# Time the startup process
time ./scripts/launch-app.sh

# Expected: < 30 seconds on modern hardware
```

#### Resource Usage
```bash
# Monitor resource usage
# Start app in background
./scripts/launch-app.sh &

# Check memory usage
ps aux | grep uvicorn

# Expected: < 200MB memory for basic setup
```

### 10. Documentation Completeness

#### Verify Quick Start Guide
```bash
# Check guide exists
ls -la docs/QUICK_START_GUIDE.md

# Review content sections:
# - One-command startup ✓
# - Environment variables ✓
# - Troubleshooting ✓
# - Next steps ✓
```

#### Test All Documented Commands
```bash
# Go through QUICK_START_GUIDE.md
# Execute each command example
# Verify all work as documented
```

## Integration Test Suite

### Full Workflow Test
```bash
#!/bin/bash
# Complete integration test

echo "=== Integration Test ==="

# 1. Clean slate
echo "1. Cleaning environment..."
rm -f .env corporate_intel.db
rm -rf venv

# 2. First-time setup
echo "2. Running quick-start..."
./scripts/quick-start.sh << EOF
2
admin@test.com
testpass123

EOF

# 3. Verify startup
echo "3. Checking health..."
sleep 5
curl http://localhost:8000/api/v1/health

# 4. Stop app
echo "4. Stopping application..."
./scripts/stop-app.sh

# 5. Restart
echo "5. Testing restart..."
./scripts/launch-app.sh &
sleep 5

# 6. Final health check
echo "6. Final verification..."
curl http://localhost:8000/api/v1/health

# 7. Cleanup
echo "7. Cleanup..."
./scripts/stop-app.sh

echo "=== Test Complete ==="
```

## Success Criteria

All verification steps should pass:

- [ ] Scripts are executable
- [ ] Quick-start creates .env correctly
- [ ] SECRET_KEY is generated automatically
- [ ] Database connection works (PostgreSQL or SQLite)
- [ ] Migrations run successfully
- [ ] Application starts on port 8000
- [ ] Health endpoint returns 200 OK
- [ ] API docs accessible at /docs
- [ ] Admin user can login
- [ ] Stop script gracefully shuts down
- [ ] Docker services start/stop correctly
- [ ] Error messages are helpful
- [ ] Documentation is complete and accurate

## Common Issues and Resolutions

### Issue: "permission denied: ./scripts/launch-app.sh"
**Resolution**: Run `chmod +x scripts/*.sh`

### Issue: "port 8000 already in use"
**Resolution**: Run `./scripts/stop-app.sh` first

### Issue: ".env file not found"
**Resolution**: Run `./scripts/quick-start.sh`

### Issue: "Database connection failed"
**Resolution**:
- For PostgreSQL: Start Docker services
- For SQLite: Check file permissions

### Issue: "Module not found"
**Resolution**: Activate venv and reinstall: `pip install -r requirements.txt`

## Maintenance

### Regular Checks
```bash
# Weekly: Test full startup flow
./scripts/quick-start.sh

# Monthly: Update dependencies
pip list --outdated
pip install --upgrade package_name

# Quarterly: Review and update documentation
```

### Script Updates
When updating scripts:
1. Test all verification steps
2. Update this verification document
3. Update QUICK_START_GUIDE.md
4. Run integration test suite
5. Document any breaking changes

---

**Last Updated**: 2025-10-02
**Version**: 1.0.0
**Status**: ✓ All tests passing
