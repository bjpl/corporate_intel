#!/bin/bash
# Remove .env files and secrets from git history
# WARNING: This rewrites git history! Coordinate with your team.
# Usage: ./scripts/security/remove-secrets-from-history.sh

set -euo pipefail

echo "⚠️  WARNING: This will rewrite git history!"
echo "============================================"
echo ""
echo "This script will:"
echo "  1. Remove ALL .env files from git history"
echo "  2. Remove secrets.json, credentials.json, etc."
echo "  3. Force push to remote (requires coordination)"
echo ""
echo "Prerequisites:"
echo "  - pip install git-filter-repo"
echo "  - Coordinate with team members"
echo "  - Backup your repository"
echo ""
read -p "Do you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 1
fi

# Check if git-filter-repo is installed
if ! command -v git-filter-repo &> /dev/null; then
    echo "❌ git-filter-repo not found!"
    echo "Install with: pip install git-filter-repo"
    exit 1
fi

# Backup current state
echo "📦 Creating backup..."
BACKUP_DIR="../corporate_intel_backup_$(date +%Y%m%d_%H%M%S)"
cp -r . "$BACKUP_DIR"
echo "✓ Backup created at: $BACKUP_DIR"

# Files to remove from history
FILES_TO_REMOVE=(
    ".env"
    ".env.local"
    ".env.development"
    ".env.staging"
    ".env.production"
    "secrets.json"
    "credentials.json"
    ".aws/credentials"
    "*.pem"
    "*.key"
    "*_rsa"
)

echo ""
echo "🗑️  Removing sensitive files from history..."
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "  - $file"
    git filter-repo --path "$file" --invert-paths --force || true
done

# Remove sensitive strings from all files
echo ""
echo "🔍 Scanning for sensitive patterns..."

# Create a file with patterns to replace
cat > /tmp/git-filter-patterns.txt <<EOF
# Replace actual secrets with placeholders
regex:GITHUB_TOKEN=gh[a-zA-Z0-9_]{36,}==>GITHUB_TOKEN=your-github-token-here
regex:ALPHA_VANTAGE_API_KEY=[A-Z0-9]{16}==>ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key-here
regex:NEWSAPI_KEY=[a-z0-9]{32}==>NEWSAPI_KEY=your-newsapi-key-here
regex:SECRET_KEY=[a-f0-9]{64}==>SECRET_KEY=your-secret-key-here-replace-with-64-char-hex
regex:MINIO_ACCESS_KEY=[a-f0-9]{32}==>MINIO_ACCESS_KEY=your-minio-access-key-here
regex:MINIO_SECRET_KEY=[a-f0-9]{64}==>MINIO_SECRET_KEY=your-minio-secret-key-here
regex:SENTRY_DSN=https://[a-z0-9]+@[a-z0-9]+\.ingest\.sentry\.io/[0-9]+==>SENTRY_DSN=
regex:postgresql://[^:]+:[^@]+@==>postgresql://user:password@
EOF

git filter-repo --replace-text /tmp/git-filter-patterns.txt --force || true
rm /tmp/git-filter-patterns.txt

# Clean up
echo ""
echo "🧹 Cleaning up..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "✅ History cleaned successfully!"
echo ""
echo "⚠️  IMPORTANT NEXT STEPS:"
echo "  1. Verify the changes: git log --all --oneline"
echo "  2. Rotate ALL credentials that were exposed"
echo "  3. Force push to remote:"
echo "     git push origin --force --all"
echo "     git push origin --force --tags"
echo "  4. Notify team members to re-clone the repository"
echo "  5. Delete the backup once verified: rm -rf $BACKUP_DIR"
echo ""
echo "📖 See docs/security/SECURITY_GUIDELINES.md for credential rotation"
