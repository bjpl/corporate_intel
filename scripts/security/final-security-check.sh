#!/bin/bash
# Final comprehensive security check before public release
# Usage: ./scripts/security/final-security-check.sh

set -euo pipefail

echo "🔒 FINAL SECURITY CHECK - Corporate Intel Platform"
echo "===================================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

# Helper functions
check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

check_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# 1. SECRET SCAN
echo -e "\n${BLUE}[1/10] Scanning for exposed secrets...${NC}"
if git ls-files | grep -qE "^\.env$"; then
    check_fail ".env file is tracked in git!"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
else
    check_pass "No .env files tracked"
fi

if git log --all --full-history --pretty=format:"%H" -- .env 2>/dev/null | head -1 | grep -q .; then
    check_fail ".env files found in git history!"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    echo "   Run: ./scripts/security/remove-secrets-from-history.sh"
else
    check_pass "No .env files in git history"
fi

# Check for hardcoded credentials
if git grep -iE "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}" -- '*.py' 2>/dev/null | grep -v ".md" | grep -v "example" | grep -v "REPLACE_WITH" | grep -q .; then
    check_fail "Hardcoded credentials found!"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    git grep -iE "(password|secret|api_key|token)\s*=\s*['\"][^'\"]{8,}" -- '*.py' | grep -v ".md" | grep -v "example" | grep -v "REPLACE_WITH" | head -3
else
    check_pass "No hardcoded credentials"
fi

# 2. GITIGNORE CHECK
echo -e "\n${BLUE}[2/10] Verifying .gitignore protection...${NC}"
REQUIRED_IGNORES=(".env" ".env.local" ".env.production" "*.pem" "*.key")
for item in "${REQUIRED_IGNORES[@]}"; do
    if git check-ignore "$item" &>/dev/null || grep -q "^$item$" .gitignore 2>/dev/null; then
        check_pass "$item is gitignored"
    else
        check_fail "$item is NOT gitignored!"
        HIGH_ISSUES=$((HIGH_ISSUES + 1))
    fi
done

# 3. ENVIRONMENT FILES CHECK
echo -e "\n${BLUE}[3/10] Checking environment file security...${NC}"
if [ -f .env.example ]; then
    # Check .env.example doesn't have real secrets
    if grep -qE "[a-f0-9]{32,64}" .env.example | grep -v "REPLACE_WITH" | grep -v "your-"; then
        check_warn ".env.example may contain real secrets"
        MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
    else
        check_pass ".env.example is sanitized"
    fi
else
    check_warn ".env.example not found"
    MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
fi

# Check current .env has required vars
if [ -f .env ]; then
    REQUIRED_VARS=("SECRET_KEY" "POSTGRES_PASSWORD" "REDIS_PASSWORD")
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            # Check it's not a placeholder
            value=$(grep "^${var}=" .env | cut -d= -f2-)
            if echo "$value" | grep -qE "REPLACE|your-|changeme|example"; then
                check_fail "$var uses placeholder value!"
                HIGH_ISSUES=$((HIGH_ISSUES + 1))
            else
                check_pass "$var is set"
            fi
        else
            check_fail "$var not found in .env"
            HIGH_ISSUES=$((HIGH_ISSUES + 1))
        fi
    done
else
    check_warn ".env file not found (expected in development)"
    check_info "Copy .env.example to .env and set real values"
fi

# 4. PRIVATE KEYS CHECK
echo -e "\n${BLUE}[4/10] Scanning for private keys...${NC}"
if find . -type f \( -name "*.pem" -o -name "*.key" -o -name "*_rsa" \) -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./venv/*" 2>/dev/null | head -1 | grep -q .; then
    check_fail "Private key files found!"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    find . -type f \( -name "*.pem" -o -name "*.key" -o -name "*_rsa" \) -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./venv/*" 2>/dev/null
else
    check_pass "No private key files found"
fi

# 5. DATABASE CONNECTION STRINGS
echo -e "\n${BLUE}[5/10] Checking for exposed database URLs...${NC}"
if git grep -E "postgresql://[^:]+:[^@]+@" -- '*.py' '*.sh' 2>/dev/null | grep -v "example" | grep -v "your-" | grep -v ".md" | grep -q .; then
    check_fail "Database URLs with credentials found!"
    HIGH_ISSUES=$((HIGH_ISSUES + 1))
else
    check_pass "No exposed database URLs"
fi

# 6. PRE-COMMIT HOOKS
echo -e "\n${BLUE}[6/10] Checking pre-commit hook setup...${NC}"
if [ -f .pre-commit-config.yaml ]; then
    check_pass ".pre-commit-config.yaml exists"

    # Check if hooks are installed
    if [ -d .git/hooks ] && [ -f .git/hooks/pre-commit ]; then
        check_pass "Pre-commit hooks installed"
    else
        check_warn "Pre-commit hooks not installed"
        check_info "Run: pre-commit install"
        MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
    fi

    # Check for secret detection
    if grep -q "detect-secrets" .pre-commit-config.yaml; then
        check_pass "Secret detection configured"
    else
        check_fail "Secret detection not configured!"
        HIGH_ISSUES=$((HIGH_ISSUES + 1))
    fi
else
    check_fail ".pre-commit-config.yaml not found!"
    HIGH_ISSUES=$((HIGH_ISSUES + 1))
fi

# 7. SECURITY DOCUMENTATION
echo -e "\n${BLUE}[7/10] Checking security documentation...${NC}"
REQUIRED_DOCS=(
    "SECURITY.md"
    "docs/security/SECURITY_GUIDELINES.md"
    "docs/security/CREDENTIAL_ROTATION_GUIDE.md"
)

for doc in "${REQUIRED_DOCS[@]}"; do
    if [ -f "$doc" ]; then
        check_pass "$doc exists"
    else
        check_warn "$doc not found"
        MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
    fi
done

# 8. API SECURITY CHECKS
echo -e "\n${BLUE}[8/10] Verifying API security implementation...${NC}"

# Check for security middleware
if grep -q "SecurityHeadersMiddleware" src/api/main.py 2>/dev/null; then
    check_pass "Security headers middleware configured"
else
    check_fail "Security headers middleware not found!"
    HIGH_ISSUES=$((HIGH_ISSUES + 1))
fi

# Check for rate limiting
if grep -q "RateLimitMiddleware" src/api/main.py 2>/dev/null; then
    check_pass "Rate limiting middleware configured"
else
    check_warn "Rate limiting middleware not found"
    MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
fi

# Check for SQL injection prevention
if grep -q "ALLOWED_ORDER_COLUMNS\|whitelist" src/api/v1/*.py 2>/dev/null; then
    check_pass "SQL injection prevention implemented"
else
    check_warn "SQL injection prevention may not be comprehensive"
    MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
fi

# 9. DEPENDENCY SECURITY
echo -e "\n${BLUE}[9/10] Checking dependency security...${NC}"

# Check if safety or pip-audit is available
if command -v safety &> /dev/null; then
    check_info "Running safety check..."
    if safety check --json 2>/dev/null | grep -q "\"vulnerabilities_found\": 0"; then
        check_pass "No known vulnerabilities in dependencies"
    else
        check_warn "Vulnerabilities found in dependencies"
        MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
        check_info "Run: safety check --full-report"
    fi
elif command -v pip-audit &> /dev/null; then
    check_info "Running pip-audit..."
    if pip-audit --format json 2>/dev/null | grep -q "\"vulnerabilities\": \[\]"; then
        check_pass "No known vulnerabilities in dependencies"
    else
        check_warn "Vulnerabilities found in dependencies"
        MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
        check_info "Run: pip-audit"
    fi
else
    check_warn "Neither safety nor pip-audit installed"
    check_info "Install with: pip install safety pip-audit"
    LOW_ISSUES=$((LOW_ISSUES + 1))
fi

# 10. PRODUCTION READINESS
echo -e "\n${BLUE}[10/10] Production readiness check...${NC}"

# Check for DEBUG mode
if grep -q "DEBUG=false" .env.example 2>/dev/null; then
    check_pass "DEBUG mode disabled by default"
else
    check_warn "DEBUG mode configuration unclear"
    LOW_ISSUES=$((LOW_ISSUES + 1))
fi

# Check for HTTPS enforcement
if grep -q "SECURE=true\|SSL=true" config/production/*.yml 2>/dev/null; then
    check_pass "HTTPS/SSL configuration found"
else
    check_warn "HTTPS/SSL configuration not found"
    check_info "Ensure TLS/SSL is configured for production"
    MEDIUM_ISSUES=$((MEDIUM_ISSUES + 1))
fi

# Check for secrets manager integration
if [ -f "config/vault_integration.py" ] || [ -f "config/aws_secrets_integration.py" ]; then
    check_pass "Secrets manager integration available"
else
    check_info "No secrets manager integration found"
    check_info "Consider using Vault, AWS Secrets Manager, or similar"
    LOW_ISSUES=$((LOW_ISSUES + 1))
fi

# SUMMARY
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}SECURITY CHECK SUMMARY${NC}"
echo -e "${BLUE}========================================${NC}"

TOTAL_ISSUES=$((CRITICAL_ISSUES + HIGH_ISSUES + MEDIUM_ISSUES + LOW_ISSUES))

echo -e "\n${RED}Critical Issues: $CRITICAL_ISSUES${NC}"
echo -e "${YELLOW}High Issues: $HIGH_ISSUES${NC}"
echo -e "${YELLOW}Medium Issues: $MEDIUM_ISSUES${NC}"
echo -e "${GREEN}Low Issues: $LOW_ISSUES${NC}"
echo -e "\nTotal Issues: $TOTAL_ISSUES"

echo -e "\n${BLUE}========================================${NC}"

# Recommendations
if [ $CRITICAL_ISSUES -gt 0 ]; then
    echo -e "\n${RED}⛔ CRITICAL ISSUES FOUND!${NC}"
    echo "DO NOT deploy to production or share publicly until these are fixed!"
    echo ""
    echo "Required actions:"
    echo "1. Remove secrets from git history: ./scripts/security/remove-secrets-from-history.sh"
    echo "2. Rotate ALL exposed credentials: docs/security/CREDENTIAL_ROTATION_GUIDE.md"
    echo "3. Update .gitignore to prevent future commits"
    echo "4. Install pre-commit hooks: pre-commit install"
    exit 1
elif [ $HIGH_ISSUES -gt 0 ]; then
    echo -e "\n${YELLOW}⚠  HIGH PRIORITY ISSUES FOUND${NC}"
    echo "Address these before public release."
    exit 1
elif [ $MEDIUM_ISSUES -gt 0 ]; then
    echo -e "\n${YELLOW}⚠  MEDIUM PRIORITY ISSUES FOUND${NC}"
    echo "Recommended to fix before public release."
    echo "Review the warnings above."
    exit 0
else
    echo -e "\n${GREEN}✅ Security check PASSED!${NC}"
    echo "Repository appears safe for public sharing."
    echo ""
    echo "📋 Final checklist:"
    echo "  [ ] All credentials have been rotated"
    echo "  [ ] .env file is in .gitignore"
    echo "  [ ] Pre-commit hooks are installed"
    echo "  [ ] README includes security instructions"
    echo "  [ ] SECURITY.md is present and complete"
    echo "  [ ] Production secrets use secrets manager"
    exit 0
fi
