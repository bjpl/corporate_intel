#!/bin/bash
set -euo pipefail

# Production Deployment Script with Safety Checks
# Deploys Corporate Intel API to production with comprehensive validation

ENVIRONMENT="production"
NAMESPACE="production"
VERSION="${1:-}"
KUBECONFIG="${KUBECONFIG:-~/.kube/config}"
HELM_RELEASE="corporate-intel"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

send_slack_notification() {
    local message="$1"
    local color="${2:-good}"

    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST "$SLACK_WEBHOOK" \
            -H 'Content-Type: application/json' \
            -d "{
                \"attachments\": [{
                    \"color\": \"$color\",
                    \"title\": \"Production Deployment\",
                    \"text\": \"$message\",
                    \"footer\": \"Corporate Intel CI/CD\",
                    \"ts\": $(date +%s)
                }]
            }" || true
    fi
}

# Validate version
if [ -z "$VERSION" ]; then
    log_error "Usage: $0 <version>"
    log_info "Example: $0 v1.0.0"
    exit 1
fi

log_info "🚀 Starting production deployment for version: $VERSION"
send_slack_notification "🚀 Starting production deployment for version: $VERSION" "warning"

# Pre-deployment checks
log_info "🔍 Running pre-deployment checks..."

# Check kubectl connectivity
if ! kubectl cluster-info &> /dev/null; then
    log_error "Cannot connect to Kubernetes cluster"
    exit 1
fi

# Check if namespace exists
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    log_error "Namespace $NAMESPACE does not exist"
    exit 1
fi

# Verify Docker image exists
log_info "🐳 Verifying Docker image..."
if ! docker manifest inspect "corporate-intel:${VERSION}" &> /dev/null; then
    log_error "Docker image corporate-intel:${VERSION} not found"
    exit 1
fi

# Run security scan
log_info "🔒 Running security scan..."
trivy image --severity HIGH,CRITICAL "corporate-intel:${VERSION}" || {
    log_error "Security vulnerabilities found in image"
    send_slack_notification "❌ Security vulnerabilities found in version ${VERSION}" "danger"
    exit 1
}

# Check database connectivity
log_info "🗄️  Checking database connectivity..."
kubectl run -it --rm db-check \
    --image=postgres:15 \
    --namespace="$NAMESPACE" \
    --restart=Never \
    --command -- psql "$DATABASE_URL" -c "SELECT 1" || {
    log_error "Database connectivity check failed"
    exit 1
}

# Create database backup before deployment
log_info "💾 Creating pre-deployment database backup..."
./scripts/backup/backup-database.sh || {
    log_error "Database backup failed"
    exit 1
}

# Run database migrations in dry-run mode
log_info "🔧 Validating database migrations..."
kubectl run -it --rm migration-check \
    --image="corporate-intel:${VERSION}" \
    --namespace="$NAMESPACE" \
    --restart=Never \
    --command -- alembic upgrade head --sql > /tmp/migration-preview.sql

log_warn "Migration preview saved to /tmp/migration-preview.sql"
log_warn "Review migrations before proceeding"
read -p "Continue with deployment? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    log_info "Deployment cancelled by user"
    exit 0
fi

# Deployment
log_info "📦 Deploying to production..."

# Update Helm release with new version
helm upgrade "$HELM_RELEASE" ./helm/corporate-intel \
    --namespace="$NAMESPACE" \
    --values=./helm/corporate-intel/values-production.yaml \
    --set image.tag="$VERSION" \
    --set deployment.timestamp="$(date +%s)" \
    --wait \
    --timeout=10m \
    --atomic \
    --cleanup-on-fail || {
    log_error "Helm deployment failed"
    send_slack_notification "❌ Production deployment failed for version ${VERSION}" "danger"
    exit 1
}

# Run database migrations
log_info "🔄 Running database migrations..."
kubectl run -it --rm migration-apply \
    --image="corporate-intel:${VERSION}" \
    --namespace="$NAMESPACE" \
    --restart=Never \
    --command -- alembic upgrade head || {
    log_error "Migration failed"
    log_info "🔙 Rolling back deployment..."
    helm rollback "$HELM_RELEASE" --namespace="$NAMESPACE"
    send_slack_notification "❌ Migration failed, deployment rolled back" "danger"
    exit 1
}

# Wait for rollout to complete
log_info "⏳ Waiting for rollout to complete..."
kubectl rollout status deployment/prod-corporate-intel-api \
    --namespace="$NAMESPACE" \
    --timeout=5m || {
    log_error "Rollout failed"
    helm rollback "$HELM_RELEASE" --namespace="$NAMESPACE"
    send_slack_notification "❌ Rollout failed, deployment rolled back" "danger"
    exit 1
}

# Post-deployment validation
log_info "✅ Running post-deployment validation..."

# Health check
log_info "🏥 Checking application health..."
sleep 10  # Give app time to stabilize

HEALTH_URL="https://api.corporate-intel.com/health"
for i in {1..5}; do
    if curl -sf "$HEALTH_URL" > /dev/null; then
        log_info "Health check passed"
        break
    else
        log_warn "Health check failed (attempt $i/5)"
        sleep 5
    fi

    if [ $i -eq 5 ]; then
        log_error "Health check failed after 5 attempts"
        helm rollback "$HELM_RELEASE" --namespace="$NAMESPACE"
        send_slack_notification "❌ Health check failed, deployment rolled back" "danger"
        exit 1
    fi
done

# Smoke tests
log_info "🧪 Running smoke tests..."
kubectl run -it --rm smoke-test \
    --image=curlimages/curl:latest \
    --namespace="$NAMESPACE" \
    --restart=Never \
    --command -- sh -c "
        curl -sf https://api.corporate-intel.com/health &&
        curl -sf https://api.corporate-intel.com/api/v1/health
    " || {
    log_error "Smoke tests failed"
    helm rollback "$HELM_RELEASE" --namespace="$NAMESPACE"
    send_slack_notification "❌ Smoke tests failed, deployment rolled back" "danger"
    exit 1
}

# Performance validation
log_info "📊 Running performance validation..."
# Run a quick load test to ensure no performance regression
k6 run --vus 10 --duration 30s ./tests/performance/k6-script.js || {
    log_warn "Performance test failed - manual investigation required"
}

# Verify metrics are being collected
log_info "📈 Verifying metrics collection..."
kubectl run -it --rm metrics-check \
    --image=curlimages/curl:latest \
    --namespace="$NAMESPACE" \
    --restart=Never \
    --command -- curl -sf http://prod-corporate-intel-api:9090/metrics > /dev/null || {
    log_warn "Metrics endpoint not responding"
}

# Create deployment tag
log_info "🏷️  Creating deployment tag..."
git tag -a "deploy/production/${VERSION}" -m "Production deployment ${VERSION} at $(date)"
git push origin "deploy/production/${VERSION}"

# Update deployment record
log_info "📝 Recording deployment..."
cat <<EOF > "/tmp/deployment-${VERSION}.json"
{
  "version": "${VERSION}",
  "environment": "production",
  "timestamp": "$(date -Iseconds)",
  "deployed_by": "${USER}",
  "git_commit": "$(git rev-parse HEAD)",
  "namespace": "${NAMESPACE}",
  "helm_release": "${HELM_RELEASE}"
}
EOF

# Store deployment record in S3
aws s3 cp "/tmp/deployment-${VERSION}.json" \
    "s3://corporate-intel-deployments/production/deployment-${VERSION}.json"

# Success notification
log_info "✅ Production deployment completed successfully!"
log_info "Version: $VERSION"
log_info "Namespace: $NAMESPACE"
log_info "Time: $(date)"

send_slack_notification "✅ Production deployment successful for version ${VERSION}" "good"

# Post-deployment monitoring
log_info "📊 Monitor deployment at:"
log_info "  - Grafana: https://grafana.corporate-intel.com"
log_info "  - Prometheus: https://prometheus.corporate-intel.com"
log_info "  - Logs: kubectl logs -f -n $NAMESPACE -l app=corporate-intel"

# Create rollback script for easy recovery
cat <<EOF > "/tmp/rollback-${VERSION}.sh"
#!/bin/bash
# Rollback script for version ${VERSION}
echo "Rolling back from version ${VERSION}..."
helm rollback ${HELM_RELEASE} --namespace=${NAMESPACE}
EOF
chmod +x "/tmp/rollback-${VERSION}.sh"

log_info "💡 Rollback script created: /tmp/rollback-${VERSION}.sh"
