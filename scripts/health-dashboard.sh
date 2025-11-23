#!/bin/bash
# Corporate Intelligence Platform - Real-Time Health Dashboard
# =============================================================
# Displays real-time health status with automatic refresh
# Usage: ./scripts/health-dashboard.sh [environment] [interval]
#   environment: staging (default) | production
#   interval: refresh interval in seconds (default: 5)

# Environment and refresh interval
ENVIRONMENT="${1:-staging}"
REFRESH_INTERVAL="${2:-5}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration based on environment
if [ "$ENVIRONMENT" = "staging" ]; then
    API_URL="http://localhost:8004"
    POSTGRES_CONTAINER="corporate-intel-staging-postgres"
    POSTGRES_USER="intel_staging_user"
    POSTGRES_DB="corporate_intel_staging"
    REDIS_CONTAINER="corporate-intel-staging-redis"
    REDIS_PASSWORD="dev-redis-password"
    PROMETHEUS_URL="http://localhost:9091"
    GRAFANA_URL="http://localhost:3001"
else
    echo -e "${RED}Production environment not configured yet${NC}"
    exit 1
fi

# Function to get HTTP status with timing
get_http_status() {
    local url=$1
    result=$(curl -s -o /dev/null -w "%{http_code}|%{time_total}" "$url" 2>/dev/null || echo "000|0.000")
    echo "$result"
}

# Function to format status
format_status() {
    local code=$1
    local time=$2

    if [ "$code" = "200" ]; then
        echo -e "${GREEN}✓ UP${NC} (${time}s)"
    elif [ "$code" = "000" ]; then
        echo -e "${RED}✗ DOWN${NC}"
    else
        echo -e "${YELLOW}⚠ HTTP $code${NC} (${time}s)"
    fi
}

# Function to get container health
get_container_health() {
    local container=$1
    status=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "unknown")

    case "$status" in
        "healthy")
            echo -e "${GREEN}✓ HEALTHY${NC}"
            ;;
        "unhealthy")
            echo -e "${RED}✗ UNHEALTHY${NC}"
            ;;
        "starting")
            echo -e "${YELLOW}⟳ STARTING${NC}"
            ;;
        *)
            # If no health check, check if running
            running=$(docker inspect --format='{{.State.Running}}' "$container" 2>/dev/null || echo "false")
            if [ "$running" = "true" ]; then
                echo -e "${CYAN}● RUNNING${NC}"
            else
                echo -e "${RED}✗ STOPPED${NC}"
            fi
            ;;
    esac
}

# Function to display dashboard
display_dashboard() {
    # Clear screen
    clear

    # Header
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Corporate Intelligence Platform - Health Dashboard           ║${NC}"
    echo -e "${BLUE}║  Environment: ${ENVIRONMENT^^}                                            ║${NC}"
    echo -e "${BLUE}║  Auto-refresh: ${REFRESH_INTERVAL}s                                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Timestamp
    echo -e "${CYAN}Last Updated: $(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo ""

    # API Service
    echo -e "${MAGENTA}━━━ API SERVICE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # API Health
    result=$(get_http_status "$API_URL/health")
    code=$(echo "$result" | cut -d'|' -f1)
    time=$(echo "$result" | cut -d'|' -f2)
    echo -ne "  Health Endpoint:  "
    format_status "$code" "$time"

    # API Metrics
    result=$(get_http_status "$API_URL/metrics/")
    code=$(echo "$result" | cut -d'|' -f1)
    time=$(echo "$result" | cut -d'|' -f2)
    echo -ne "  Metrics Endpoint: "
    format_status "$code" "$time"

    # API Version
    if [ "$code" = "200" ]; then
        version=$(curl -s "$API_URL/health" 2>/dev/null | python -c "import sys, json; print(json.load(sys.stdin).get('version', 'N/A'))" 2>/dev/null || echo "N/A")
        echo -e "  Version:          ${GREEN}$version${NC}"
    fi

    echo ""

    # Database
    echo -e "${MAGENTA}━━━ DATABASE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # PostgreSQL Status
    echo -ne "  PostgreSQL:       "
    get_container_health "$POSTGRES_CONTAINER"

    # Database size
    db_size=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" 2>/dev/null | xargs || echo "N/A")
    echo -e "  Database Size:    ${CYAN}$db_size${NC}"

    # Active connections
    conn_count=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT COUNT(*) FROM pg_stat_activity WHERE datname='$POSTGRES_DB';" 2>/dev/null | xargs || echo "N/A")
    echo -e "  Connections:      ${CYAN}$conn_count${NC}"

    # TimescaleDB
    timescale=$(docker exec $POSTGRES_CONTAINER psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "SELECT extversion FROM pg_extension WHERE extname='timescaledb';" 2>/dev/null | xargs || echo "N/A")
    if [ "$timescale" != "N/A" ]; then
        echo -e "  TimescaleDB:      ${GREEN}v$timescale${NC}"
    else
        echo -e "  TimescaleDB:      ${RED}Not installed${NC}"
    fi

    echo ""

    # Redis Cache
    echo -e "${MAGENTA}━━━ REDIS CACHE ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Redis Status
    echo -ne "  Redis:            "
    get_container_health "$REDIS_CONTAINER"

    # Memory usage
    redis_memory=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r' || echo "N/A")
    echo -e "  Memory Usage:     ${CYAN}$redis_memory${NC}"

    # Connected clients
    redis_clients=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO clients 2>/dev/null | grep "connected_clients:" | cut -d: -f2 | tr -d '\r' || echo "N/A")
    echo -e "  Connected Clients:${CYAN}$redis_clients${NC}"

    # Cache hit ratio
    hits=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO stats 2>/dev/null | grep "keyspace_hits:" | cut -d: -f2 | tr -d '\r' || echo "0")
    misses=$(docker exec $REDIS_CONTAINER redis-cli -a $REDIS_PASSWORD INFO stats 2>/dev/null | grep "keyspace_misses:" | cut -d: -f2 | tr -d '\r' || echo "0")
    total=$((hits + misses))
    if [ $total -gt 0 ]; then
        hit_ratio=$((hits * 100 / total))
        echo -e "  Cache Hit Ratio:  ${CYAN}${hit_ratio}%${NC}"
    else
        echo -e "  Cache Hit Ratio:  ${CYAN}N/A (no requests)${NC}"
    fi

    echo ""

    # Monitoring
    echo -e "${MAGENTA}━━━ MONITORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Prometheus
    result=$(get_http_status "$PROMETHEUS_URL/-/healthy")
    code=$(echo "$result" | cut -d'|' -f1)
    time=$(echo "$result" | cut -d'|' -f2)
    echo -ne "  Prometheus:       "
    format_status "$code" "$time"

    # Prometheus targets
    if [ "$code" = "200" ]; then
        targets_up=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(sum(1 for t in data['data']['activeTargets'] if t['health']=='up'))" 2>/dev/null || echo "0")
        targets_total=$(curl -s "$PROMETHEUS_URL/api/v1/targets" 2>/dev/null | python -c "import sys, json; data=json.load(sys.stdin); print(len(data['data']['activeTargets']))" 2>/dev/null || echo "0")
        if [ $targets_total -gt 0 ]; then
            echo -e "  Active Targets:   ${CYAN}$targets_up/$targets_total UP${NC}"
        fi
    fi

    # Grafana
    result=$(get_http_status "$GRAFANA_URL/api/health")
    code=$(echo "$result" | cut -d'|' -f1)
    time=$(echo "$result" | cut -d'|' -f2)
    echo -ne "  Grafana:          "
    format_status "$code" "$time"

    echo ""

    # Docker Containers
    echo -e "${MAGENTA}━━━ CONTAINERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    docker ps --filter "name=corporate-intel-$ENVIRONMENT" --format "{{.Names}}:{{.Status}}" | while IFS=: read -r name status; do
        short_name=$(echo "$name" | sed "s/corporate-intel-$ENVIRONMENT-//")
        printf "  %-18s" "$short_name:"

        if echo "$status" | grep -q "(healthy)"; then
            echo -e "${GREEN}✓ HEALTHY${NC}"
        elif echo "$status" | grep -q "(unhealthy)"; then
            echo -e "${RED}✗ UNHEALTHY${NC}"
        elif echo "$status" | grep -q "Up"; then
            uptime=$(echo "$status" | sed 's/Up //')
            echo -e "${CYAN}● RUNNING${NC} ($uptime)"
        else
            echo -e "${YELLOW}⚠ $status${NC}"
        fi
    done

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}Press Ctrl+C to exit${NC}"
}

# Trap Ctrl+C
trap 'echo -e "\n${YELLOW}Dashboard stopped${NC}"; exit 0' INT

# Main loop
while true; do
    display_dashboard
    sleep $REFRESH_INTERVAL
done
