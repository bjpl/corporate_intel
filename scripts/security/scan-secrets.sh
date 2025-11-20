#!/bin/bash
# Security scanner for detecting exposed secrets
# Usage: ./scripts/security/scan-secrets.sh

set -euo pipefail

echo "🔍 Security Scan: Detecting exposed secrets..."
echo "================================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ISSUES_FOUND=0

# 1. Check if .env files are tracked
echo -e "\n${YELLOW}[1/7]${NC} Checking for tracked .env files..."
if git ls-files | grep -E "^\.env"; then
    echo -e "${RED}❌ CRITICAL: .env files are tracked in git!${NC}"
    git ls-files | grep -E "^\.env"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} No .env files tracked"
fi

# 2. Check git history for .env files
echo -e "\n${YELLOW}[2/7]${NC} Checking git history for .env files..."
if git log --all --full-history --pretty=format:"%H" -- .env .env.* 2>/dev/null | head -1; then
    echo -e "${RED}❌ CRITICAL: .env files found in git history!${NC}"
    echo "Commits containing .env files:"
    git log --all --full-history --oneline -- .env .env.* | head -5
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} No .env files in git history"
fi

# 3. Search for hardcoded credentials
echo -e "\n${YELLOW}[3/7]${NC} Scanning for hardcoded credentials..."
CRED_PATTERNS=(
    "password\s*=\s*['\"][^'\"]{8,}"
    "api[_-]?key\s*=\s*['\"][^'\"]{10,}"
    "secret\s*=\s*['\"][^'\"]{10,}"
    "token\s*=\s*['\"][^'\"]{10,}"
    "postgres://[^:]+:[^@]+@"
)

for pattern in "${CRED_PATTERNS[@]}"; do
    if git grep -iE "$pattern" -- '*.py' '*.js' '*.ts' '*.sh' 2>/dev/null | grep -v ".md" | grep -v "example" | head -1; then
        echo -e "${RED}❌ Found potential credentials matching: $pattern${NC}"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓${NC} No hardcoded credentials found"
fi

# 4. Check for private keys
echo -e "\n${YELLOW}[4/7]${NC} Checking for private keys..."
if find . -type f \( -name "*.pem" -o -name "*.key" -o -name "*_rsa" \) -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./venv/*" | head -1; then
    echo -e "${RED}❌ Private key files found!${NC}"
    find . -type f \( -name "*.pem" -o -name "*.key" -o -name "*_rsa" \) -not -path "./.git/*" -not -path "./node_modules/*" -not -path "./venv/*"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} No private key files found"
fi

# 5. Check .gitignore coverage
echo -e "\n${YELLOW}[5/7]${NC} Verifying .gitignore coverage..."
REQUIRED_IGNORES=(
    ".env"
    ".env.local"
    ".env.*.local"
    ".env.staging"
    ".env.production"
    "*.pem"
    "*.key"
)

MISSING_IGNORES=0
for item in "${REQUIRED_IGNORES[@]}"; do
    if ! git check-ignore "$item" &>/dev/null; then
        echo -e "${RED}❌ Missing in .gitignore: $item${NC}"
        MISSING_IGNORES=$((MISSING_IGNORES + 1))
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    fi
done

if [ $MISSING_IGNORES -eq 0 ]; then
    echo -e "${GREEN}✓${NC} All required patterns in .gitignore"
fi

# 6. Check for AWS credentials
echo -e "\n${YELLOW}[6/7]${NC} Checking for AWS credentials..."
if [ -f ~/.aws/credentials ]; then
    echo -e "${YELLOW}⚠${NC}  AWS credentials file exists at ~/.aws/credentials"
    echo "   Make sure these are not committed to the repository"
fi

if git grep -iE "AKIA[0-9A-Z]{16}" -- '*.py' '*.js' '*.sh' 2>/dev/null | head -1; then
    echo -e "${RED}❌ AWS access key found in code!${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} No AWS access keys in code"
fi

# 7. Check for exposed database URLs
echo -e "\n${YELLOW}[7/7]${NC} Checking for exposed database URLs..."
if git grep -E "postgresql://[^:]+:[^@]+@" -- '*.py' '*.md' 2>/dev/null | grep -v "example" | grep -v "your-" | head -1; then
    echo -e "${RED}❌ Database URL with credentials found!${NC}"
    ISSUES_FOUND=$((ISSUES_FOUND + 1))
else
    echo -e "${GREEN}✓${NC} No exposed database URLs"
fi

# Summary
echo -e "\n================================================"
if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✅ Security scan passed! No issues found.${NC}"
    exit 0
else
    echo -e "${RED}❌ Security scan failed! Found $ISSUES_FOUND issue(s).${NC}"
    echo ""
    echo "🔧 Remediation steps:"
    echo "  1. Remove secrets from tracked files"
    echo "  2. Update .gitignore to prevent future commits"
    echo "  3. Remove secrets from git history:"
    echo "     git filter-repo --path .env --invert-paths"
    echo "  4. Rotate ALL exposed credentials"
    echo "  5. Run this scan again to verify"
    echo ""
    echo "📖 See docs/security/SECURITY_GUIDELINES.md for details"
    exit 1
fi
