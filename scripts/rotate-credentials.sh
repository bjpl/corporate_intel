#!/bin/bash

# Corporate Intelligence Platform - Credential Rotation Script
# ============================================================
# This script guides you through rotating all system credentials safely.
#
# WARNING: This is a semi-automated process requiring manual intervention
# at key steps to ensure data integrity and security.
#
# Usage: bash scripts/rotate-credentials.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================"
echo "Credential Rotation Script"
echo "Corporate Intelligence Platform"
echo -e "================================${NC}\n"

# Function to generate strong passwords
generate_password() {
    local length=${1:-32}
    openssl rand -base64 48 | tr -d "=+/" | cut -c1-${length}
}

# Function to backup .env file
backup_env() {
    local backup_file=".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}Creating backup: ${backup_file}${NC}"
    cp .env "$backup_file"
    chmod 600 "$backup_file"
    echo -e "${GREEN}Backup created successfully${NC}\n"
}

# Function to update .env file
update_env_var() {
    local key=$1
    local value=$2
    local env_file=".env"

    if grep -q "^${key}=" "$env_file"; then
        # Use different sed syntax for different platforms
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$env_file"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$env_file"
        fi
        echo -e "${GREEN}Updated ${key}${NC}"
    else
        echo "${key}=${value}" >> "$env_file"
        echo -e "${GREEN}Added ${key}${NC}"
    fi
}

# Main rotation process
main() {
    echo -e "${RED}WARNING: This will rotate ALL credentials!${NC}"
    echo "This process requires:"
    echo "  1. Access to all services (PostgreSQL, Redis, MinIO)"
    echo "  2. Ability to restart all containers"
    echo "  3. Approximately 10-15 minutes of downtime"
    echo ""
    read -p "Continue? (yes/no): " confirm

    if [[ "$confirm" != "yes" ]]; then
        echo "Rotation cancelled."
        exit 0
    fi

    # Step 1: Backup current .env
    echo -e "\n${YELLOW}Step 1: Backing up current configuration${NC}"
    backup_env

    # Step 2: Generate new credentials
    echo -e "${YELLOW}Step 2: Generating new credentials${NC}"
    NEW_POSTGRES_PASSWORD=$(generate_password 32)
    NEW_REDIS_PASSWORD=$(generate_password 32)
    NEW_MINIO_ROOT_PASSWORD=$(generate_password 32)
    NEW_JWT_SECRET=$(generate_password 64)
    NEW_SUPERSET_SECRET=$(generate_password 64)
    NEW_GRAFANA_PASSWORD=$(generate_password 24)

    echo -e "${GREEN}New credentials generated${NC}\n"

    # Step 3: Update PostgreSQL
    echo -e "${YELLOW}Step 3: Rotating PostgreSQL password${NC}"
    echo "Run this command in PostgreSQL:"
    echo -e "${GREEN}ALTER USER intel_user WITH PASSWORD '${NEW_POSTGRES_PASSWORD}';${NC}"
    echo ""
    read -p "Press Enter after updating PostgreSQL..."

    update_env_var "POSTGRES_PASSWORD" "$NEW_POSTGRES_PASSWORD"

    # Update DATABASE_URL with new password
    local escaped_password=$(echo "$NEW_POSTGRES_PASSWORD" | sed 's/[&/\]/\\&/g')
    update_env_var "DATABASE_URL" "postgresql://intel_user:${escaped_password}@localhost:5432/corporate_intel"

    # Step 4: Update Redis
    echo -e "\n${YELLOW}Step 4: Rotating Redis password${NC}"
    echo "Run this command in Redis CLI:"
    echo -e "${GREEN}CONFIG SET requirepass '${NEW_REDIS_PASSWORD}'${NC}"
    echo -e "${GREEN}CONFIG REWRITE${NC}"
    echo ""
    read -p "Press Enter after updating Redis..."

    update_env_var "REDIS_PASSWORD" "$NEW_REDIS_PASSWORD"
    update_env_var "REDIS_URL" "redis://:${NEW_REDIS_PASSWORD}@localhost:6379/0"

    # Step 5: Update MinIO
    echo -e "\n${YELLOW}Step 5: Rotating MinIO credentials${NC}"
    echo "MinIO credentials must be updated through environment variables and container restart."
    echo "Current root user: corporate_intel_admin"
    echo -e "New password: ${GREEN}${NEW_MINIO_ROOT_PASSWORD}${NC}"
    echo ""
    read -p "Press Enter to continue..."

    update_env_var "MINIO_ROOT_PASSWORD" "$NEW_MINIO_ROOT_PASSWORD"

    # Step 6: Update application secrets
    echo -e "\n${YELLOW}Step 6: Rotating application secrets${NC}"
    update_env_var "JWT_SECRET_KEY" "$NEW_JWT_SECRET"
    update_env_var "SUPERSET_SECRET_KEY" "$NEW_SUPERSET_SECRET"
    update_env_var "GRAFANA_PASSWORD" "$NEW_GRAFANA_PASSWORD"
    echo -e "${GREEN}Application secrets updated${NC}\n"

    # Step 7: Restart services
    echo -e "${YELLOW}Step 7: Restarting services${NC}"
    echo "Run the following commands to restart services:"
    echo -e "${GREEN}docker-compose down${NC}"
    echo -e "${GREEN}docker-compose up -d${NC}"
    echo ""
    read -p "Press Enter after restarting services..."

    # Step 8: Verification
    echo -e "\n${YELLOW}Step 8: Verification${NC}"
    echo "Test the following endpoints to verify rotation:"
    echo "  - Database: curl http://localhost:8000/health/database"
    echo "  - Cache:    curl http://localhost:8000/health/cache"
    echo "  - API:      curl http://localhost:8000/health"
    echo ""

    # Step 9: Security checklist
    echo -e "${YELLOW}Step 9: Post-Rotation Security Checklist${NC}"
    echo "  [ ] All health checks passing"
    echo "  [ ] Application can authenticate to all services"
    echo "  [ ] Old credentials invalidated"
    echo "  [ ] Backup .env file secured (chmod 600)"
    echo "  [ ] Rotation logged in security audit trail"
    echo "  [ ] Team members notified if shared credentials"
    echo ""

    # Summary
    echo -e "${GREEN}================================"
    echo "Credential Rotation Complete!"
    echo -e "================================${NC}"
    echo ""
    echo "Summary:"
    echo "  - PostgreSQL password: ROTATED"
    echo "  - Redis password: ROTATED"
    echo "  - MinIO password: ROTATED"
    echo "  - JWT secret: ROTATED"
    echo "  - Superset secret: ROTATED"
    echo "  - Grafana password: ROTATED"
    echo ""
    echo "Next steps:"
    echo "  1. Verify all services are functioning"
    echo "  2. Update any external systems using these credentials"
    echo "  3. Securely delete old backup files after verification"
    echo "  4. Document rotation in security log"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Keep the backup file for 7 days in case of issues${NC}"
    echo "Backup location: $(ls -t .env.backup.* | head -1)"
    echo ""
}

# Check if .env exists
if [[ ! -f ".env" ]]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file first (use .env.example as template)"
    exit 1
fi

# Check if required tools are installed
for tool in openssl sed; do
    if ! command -v $tool &> /dev/null; then
        echo -e "${RED}Error: $tool is not installed${NC}"
        exit 1
    fi
done

# Run main function
main
