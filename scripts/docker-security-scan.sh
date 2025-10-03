#!/bin/bash
# =============================================================================
# Docker Security Scanning Script for Corporate Intelligence Platform
# Performs comprehensive security analysis using multiple tools
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="${IMAGE_NAME:-corporate-intel:latest}"
REPORT_DIR="${REPORT_DIR:-./security-reports}"
TRIVY_VERSION="${TRIVY_VERSION:-latest}"
HADOLINT_VERSION="${HADOLINT_VERSION:-latest}"

# Create reports directory
mkdir -p "$REPORT_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    log_info "Checking Docker daemon..."
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    log_success "Docker is running"
}

# Dockerfile linting with Hadolint
lint_dockerfile() {
    log_info "Running Hadolint for Dockerfile linting..."

    if ! command -v hadolint &> /dev/null; then
        log_warning "Hadolint not found. Installing via Docker..."
        docker run --rm -i hadolint/hadolint:${HADOLINT_VERSION} < Dockerfile | tee "$REPORT_DIR/hadolint-report.txt"
    else
        hadolint Dockerfile --format json | tee "$REPORT_DIR/hadolint-report.json"
    fi

    if [ $? -eq 0 ]; then
        log_success "Hadolint scan completed - No critical issues found"
    else
        log_warning "Hadolint found some issues - Check $REPORT_DIR/hadolint-report.txt"
    fi
}

# Vulnerability scanning with Trivy
scan_with_trivy() {
    log_info "Running Trivy vulnerability scanner..."

    # Check if Trivy is installed
    if ! command -v trivy &> /dev/null; then
        log_warning "Trivy not found. Installing via Docker..."

        # Scan using Docker
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PWD/$REPORT_DIR:/reports" \
            aquasec/trivy:${TRIVY_VERSION} image \
            --severity CRITICAL,HIGH,MEDIUM \
            --format json \
            --output /reports/trivy-report.json \
            "$IMAGE_NAME"

        # Generate human-readable report
        docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
            -v "$PWD/$REPORT_DIR:/reports" \
            aquasec/trivy:${TRIVY_VERSION} image \
            --severity CRITICAL,HIGH,MEDIUM \
            --format table \
            "$IMAGE_NAME" | tee "$REPORT_DIR/trivy-report.txt"
    else
        # Scan with local Trivy
        trivy image \
            --severity CRITICAL,HIGH,MEDIUM \
            --format json \
            --output "$REPORT_DIR/trivy-report.json" \
            "$IMAGE_NAME"

        trivy image \
            --severity CRITICAL,HIGH,MEDIUM \
            --format table \
            "$IMAGE_NAME" | tee "$REPORT_DIR/trivy-report.txt"
    fi

    log_success "Trivy scan completed - Report saved to $REPORT_DIR/trivy-report.json"
}

# Docker Bench Security (if available)
run_docker_bench() {
    log_info "Running Docker Bench Security (optional)..."

    if command -v docker-bench-security &> /dev/null; then
        docker-bench-security | tee "$REPORT_DIR/docker-bench-report.txt"
        log_success "Docker Bench Security scan completed"
    else
        log_warning "Docker Bench Security not found - Skipping this check"
        log_info "Install from: https://github.com/docker/docker-bench-security"
    fi
}

# Check image size
check_image_size() {
    log_info "Checking image size..."

    IMAGE_SIZE=$(docker images "$IMAGE_NAME" --format "{{.Size}}")
    log_info "Image size: $IMAGE_SIZE"

    # Convert size to MB for comparison
    SIZE_MB=$(docker images "$IMAGE_NAME" --format "{{.Size}}" | sed 's/MB//' | sed 's/GB/*1024/' | bc 2>/dev/null || echo "0")

    if (( $(echo "$SIZE_MB > 500" | bc -l) )); then
        log_warning "Image size exceeds 500MB target - Consider optimization"
    else
        log_success "Image size is within 500MB target"
    fi
}

# Check for non-root user
check_nonroot_user() {
    log_info "Checking if container runs as non-root user..."

    USER_CHECK=$(docker run --rm "$IMAGE_NAME" whoami 2>/dev/null || echo "root")

    if [ "$USER_CHECK" != "root" ]; then
        log_success "Container runs as non-root user: $USER_CHECK"
    else
        log_error "Container runs as root - Security risk!"
    fi
}

# Test health check
test_health_check() {
    log_info "Testing health check configuration..."

    HEALTHCHECK=$(docker inspect "$IMAGE_NAME" --format='{{.Config.Healthcheck}}')

    if [ "$HEALTHCHECK" != "<nil>" ] && [ "$HEALTHCHECK" != "" ]; then
        log_success "Health check is configured"
    else
        log_error "Health check is not configured"
    fi
}

# Generate summary report
generate_summary() {
    log_info "Generating security summary report..."

    SUMMARY_FILE="$REPORT_DIR/security-summary.txt"

    cat > "$SUMMARY_FILE" << EOF
=============================================================================
Docker Security Scan Summary Report
=============================================================================
Image: $IMAGE_NAME
Scan Date: $(date)
Report Directory: $REPORT_DIR

-----------------------------------------------------------------------------
Scan Results:
-----------------------------------------------------------------------------
1. Dockerfile Linting (Hadolint): See hadolint-report.txt
2. Vulnerability Scanning (Trivy): See trivy-report.json
3. Image Size: $(docker images "$IMAGE_NAME" --format "{{.Size}}")
4. User Check: $(docker run --rm "$IMAGE_NAME" whoami 2>/dev/null || echo "Unable to check")
5. Health Check: $(docker inspect "$IMAGE_NAME" --format='{{.Config.Healthcheck}}' | grep -q "nil" && echo "Not Configured" || echo "Configured")

-----------------------------------------------------------------------------
Critical Vulnerabilities (Trivy):
-----------------------------------------------------------------------------
$(grep -o '"Severity":"CRITICAL"' "$REPORT_DIR/trivy-report.json" 2>/dev/null | wc -l || echo "0") CRITICAL issues found

-----------------------------------------------------------------------------
High Vulnerabilities (Trivy):
-----------------------------------------------------------------------------
$(grep -o '"Severity":"HIGH"' "$REPORT_DIR/trivy-report.json" 2>/dev/null | wc -l || echo "0") HIGH issues found

-----------------------------------------------------------------------------
Recommendations:
-----------------------------------------------------------------------------
1. Review all CRITICAL and HIGH severity vulnerabilities
2. Update base image and dependencies regularly
3. Minimize attack surface by removing unnecessary packages
4. Ensure secrets are managed via environment variables
5. Run containers with least privilege (non-root user)

=============================================================================
EOF

    cat "$SUMMARY_FILE"
    log_success "Summary report saved to $SUMMARY_FILE"
}

# Main execution
main() {
    echo -e "${GREEN}"
    echo "================================================================="
    echo "  Docker Security Scanning for Corporate Intelligence Platform"
    echo "================================================================="
    echo -e "${NC}"

    check_docker

    # Check if image exists
    if ! docker images "$IMAGE_NAME" --format "{{.Repository}}:{{.Tag}}" | grep -q "$IMAGE_NAME"; then
        log_error "Image $IMAGE_NAME not found. Please build it first."
        log_info "Build with: docker build -t $IMAGE_NAME ."
        exit 1
    fi

    # Run all security checks
    lint_dockerfile
    scan_with_trivy
    check_image_size
    check_nonroot_user
    test_health_check
    run_docker_bench

    # Generate summary
    generate_summary

    echo -e "${GREEN}"
    echo "================================================================="
    echo "  Security scanning completed!"
    echo "  Reports available in: $REPORT_DIR"
    echo "================================================================="
    echo -e "${NC}"
}

# Run main function
main "$@"
