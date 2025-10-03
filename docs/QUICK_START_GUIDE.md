# Corporate Intelligence Platform - Quick Start Guide

## One-Command Startup

Get up and running in under 2 minutes!

### First-Time Setup

```bash
# Run the automated quick-start script
./scripts/quick-start.sh
```

This script will:
- Create and configure your `.env` file
- Generate a secure `SECRET_KEY`
- Set up database connection
- Install Python dependencies
- Create admin user
- Launch the application

### Subsequent Launches

```bash
# Just run the launcher
./scripts/launch-app.sh
```

### Stop the Application

```bash
# Graceful shutdown
./scripts/stop-app.sh
```

---

## Environment Variables Explained

### Required Variables

#### `SECRET_KEY`
- **Purpose**: Cryptographic key for JWT tokens and session security
- **Generated**: Automatically by quick-start script
- **Example**: `your-secret-key-here-change-in-production`
- **Security**: Never commit this to version control!

#### `DATABASE_URL`
- **Purpose**: Connection string for your database
- **Format (PostgreSQL)**: `postgresql://user:password@host:port/dbname`
- **Format (SQLite)**: `sqlite:///./corporate_intel.db`
- **Example**: `postgresql://postgres:password@localhost:5432/corporate_intel`

### Optional Variables

#### `HOST`
- **Purpose**: Host address for the application
- **Default**: `0.0.0.0`
- **Development**: `127.0.0.1` or `localhost`
- **Production**: `0.0.0.0` (all interfaces)

#### `PORT`
- **Purpose**: Port number for the application
- **Default**: `8000`
- **Example**: `8000`, `8080`, `3000`

#### `ENVIRONMENT`
- **Purpose**: Application environment
- **Options**: `development`, `staging`, `production`
- **Default**: `development`
- **Impact**: Affects logging, debug mode, CORS settings

#### `LOG_LEVEL`
- **Purpose**: Logging verbosity
- **Options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **Default**: `INFO`
- **Development**: `DEBUG` for detailed logs
- **Production**: `WARNING` or `ERROR`

#### `ADMIN_EMAIL`
- **Purpose**: Default admin user email
- **Default**: `admin@corporate-intel.com`
- **Usage**: Initial login credentials

#### `ADMIN_PASSWORD`
- **Purpose**: Default admin user password
- **Default**: `changeme`
- **Security**: Change immediately after first login!

#### `REDIS_URL`
- **Purpose**: Redis connection for caching and sessions
- **Optional**: Application works without Redis
- **Format**: `redis://host:port`
- **Example**: `redis://localhost:6379`

#### `CORS_ORIGINS`
- **Purpose**: Allowed origins for CORS
- **Format**: Comma-separated list
- **Example**: `http://localhost:3000,https://app.example.com`
- **Development**: `*` (all origins)
- **Production**: Specific domains only

#### `JWT_ALGORITHM`
- **Purpose**: Algorithm for JWT token signing
- **Default**: `HS256`
- **Options**: `HS256`, `RS256`, `ES256`

#### `ACCESS_TOKEN_EXPIRE_MINUTES`
- **Purpose**: JWT access token lifetime
- **Default**: `30` minutes
- **Security**: Shorter for higher security

#### `RATE_LIMIT_PER_MINUTE`
- **Purpose**: API rate limiting
- **Default**: `60` requests/minute
- **Usage**: Prevent abuse and DoS

---

## Troubleshooting Common Startup Errors

### Error: "Python is not installed"

**Problem**: Python is not in your system PATH

**Solution**:
```bash
# Check Python installation
python --version

# If not found, install Python 3.10+
# Windows: Download from python.org
# Mac: brew install python@3.10
# Linux: sudo apt install python3.10
```

### Error: "Python 3.10 or higher is required"

**Problem**: Your Python version is too old

**Solution**:
```bash
# Check your version
python --version

# Install newer Python version
# Windows: Download from python.org
# Mac: brew install python@3.10
# Linux: sudo apt install python3.10

# Create venv with specific version
python3.10 -m venv venv
```

### Error: "Missing required environment variables"

**Problem**: `.env` file is incomplete or missing

**Solution**:
```bash
# Run quick-start to regenerate .env
./scripts/quick-start.sh

# Or manually check .env file
cat .env

# Ensure these are set:
# - SECRET_KEY
# - DATABASE_URL
```

### Error: "Database connection failed"

**Problem**: Cannot connect to database

**Solutions**:

#### For PostgreSQL:
```bash
# Check if PostgreSQL is running
# Windows: Check Services
# Mac: brew services list
# Linux: sudo systemctl status postgresql

# Start PostgreSQL
docker-compose up -d postgres

# Or manually
# Mac: brew services start postgresql
# Linux: sudo systemctl start postgresql

# Verify connection
psql -U postgres -h localhost -p 5432
```

#### For SQLite:
```bash
# Ensure database URL is correct in .env
DATABASE_URL=sqlite:///./corporate_intel.db

# Check file permissions
ls -la corporate_intel.db
```

### Error: "Port 8000 is already in use"

**Problem**: Another application is using port 8000

**Solutions**:
```bash
# Option 1: Stop existing process
./scripts/stop-app.sh

# Option 2: Use different port
export PORT=8001
./scripts/launch-app.sh

# Option 3: Kill process on port 8000
# Windows: netstat -ano | findstr :8000
# Mac/Linux: lsof -ti:8000 | xargs kill -9
```

### Error: "ModuleNotFoundError"

**Problem**: Python dependencies not installed

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# If still failing, recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Error: "Migration failed"

**Problem**: Database schema migration issues

**Solutions**:
```bash
# Check Alembic status
alembic current

# Recreate database (CAUTION: Destroys data!)
# For SQLite:
rm corporate_intel.db
alembic upgrade head

# For PostgreSQL:
psql -U postgres -c "DROP DATABASE corporate_intel;"
psql -U postgres -c "CREATE DATABASE corporate_intel;"
alembic upgrade head

# Or reset migrations
rm -rf alembic/versions/*.py
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### Error: "Permission denied"

**Problem**: Script is not executable

**Solution**:
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run again
./scripts/launch-app.sh
```

### Error: "Docker services failed to start"

**Problem**: Docker is not running or docker-compose issues

**Solutions**:
```bash
# Check Docker status
docker --version
docker-compose --version

# Start Docker
# Windows: Start Docker Desktop
# Mac: Open Docker Desktop
# Linux: sudo systemctl start docker

# Check docker-compose file
docker-compose config

# Rebuild containers
docker-compose down -v
docker-compose up -d --build
```

---

## Next Steps After Successful Start

### 1. Access the Application

- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health

### 2. Test API Endpoints

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "version": "1.0.0"
# }
```

### 3. Login as Admin

Navigate to http://localhost:8000/docs and use the "Authorize" button:

- **Email**: Your configured `ADMIN_EMAIL` (default: admin@corporate-intel.com)
- **Password**: Your configured `ADMIN_PASSWORD` (default: changeme)

**IMPORTANT**: Change the admin password immediately!

### 4. Explore API Documentation

The interactive API documentation at `/docs` allows you to:
- View all available endpoints
- Test API calls directly in the browser
- See request/response schemas
- Generate code snippets

### 5. Create Your First Resources

#### Create a Company
```bash
curl -X POST "http://localhost:8000/api/v1/companies/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corporation",
    "industry": "Technology",
    "description": "Leading tech innovator"
  }'
```

#### Create a Contact
```bash
curl -X POST "http://localhost:8000/api/v1/contacts/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@acme.com",
    "company_id": 1
  }'
```

### 6. Configure Production Settings

Before deploying to production:

1. **Change Admin Password**
   ```bash
   # Use API to update password
   curl -X PUT "http://localhost:8000/api/v1/users/me/password" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -d '{"new_password": "strong_password_here"}'
   ```

2. **Generate New SECRET_KEY**
   ```bash
   python -c 'import secrets; print(secrets.token_urlsafe(32))'
   ```

3. **Configure CORS**
   ```bash
   # In .env
   CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

4. **Set Production Environment**
   ```bash
   # In .env
   ENVIRONMENT=production
   LOG_LEVEL=WARNING
   ```

5. **Enable HTTPS**
   - Use reverse proxy (Nginx, Traefik)
   - Configure SSL certificates
   - Update CORS settings

6. **Setup Database Backups**
   ```bash
   # PostgreSQL backup script
   pg_dump -U postgres corporate_intel > backup.sql

   # Automated backups with cron
   0 2 * * * /path/to/backup-script.sh
   ```

### 7. Monitor Application

```bash
# View logs
tail -f logs/app.log

# Check system resources
# Docker stats
docker stats

# Application metrics
curl http://localhost:8000/api/v1/metrics
```

### 8. Development Workflow

```bash
# Make code changes
# App auto-reloads with --reload flag

# Run tests
pytest

# Check code quality
flake8 app/
black app/ --check
mypy app/

# Update dependencies
pip freeze > requirements.txt
```

---

## Performance Optimization Tips

### 1. Enable Redis Caching
```bash
# In .env
REDIS_URL=redis://localhost:6379

# Start Redis
docker-compose up -d redis
```

### 2. Database Connection Pooling
```bash
# In .env
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### 3. Use Production ASGI Server
```bash
# Install gunicorn
pip install gunicorn

# Run with workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### 4. Enable Compression
```bash
# Already configured in FastAPI middleware
# Compresses responses > 500 bytes
```

---

## Security Best Practices

1. **Never commit `.env` to version control**
   ```bash
   # Ensure .env is in .gitignore
   echo ".env" >> .gitignore
   ```

2. **Use strong passwords**
   - Minimum 12 characters
   - Mix of uppercase, lowercase, numbers, symbols

3. **Keep dependencies updated**
   ```bash
   pip list --outdated
   pip install --upgrade package_name
   ```

4. **Enable rate limiting**
   ```bash
   # In .env
   RATE_LIMIT_PER_MINUTE=60
   ```

5. **Use HTTPS in production**
   - Never use HTTP for sensitive data
   - Configure SSL/TLS certificates

6. **Regular backups**
   - Automated database backups
   - Offsite backup storage
   - Test restore procedures

---

## Getting Help

### Resources
- **Documentation**: `/docs` directory
- **API Docs**: http://localhost:8000/docs
- **Project README**: `README.md`
- **Architecture Guide**: `docs/ARCHITECTURE.md`

### Common Commands Reference

```bash
# Start application
./scripts/launch-app.sh

# Stop application
./scripts/stop-app.sh

# First-time setup
./scripts/quick-start.sh

# Run tests
pytest

# Database migrations
alembic upgrade head
alembic downgrade -1

# Create migration
alembic revision --autogenerate -m "description"

# Check logs
tail -f logs/app.log

# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
```

---

## Quick Troubleshooting Checklist

- [ ] Python 3.10+ installed
- [ ] Virtual environment activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file exists and configured
- [ ] `SECRET_KEY` is set
- [ ] `DATABASE_URL` is set correctly
- [ ] Database is running (PostgreSQL/SQLite accessible)
- [ ] Port 8000 is available
- [ ] Migrations are up to date (`alembic upgrade head`)
- [ ] Admin user created
- [ ] No firewall blocking connections

---

**Ready to build amazing corporate intelligence applications!**
