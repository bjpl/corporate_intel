#!/bin/bash
# Production Load Testing Execution Script
# This script runs various load test scenarios and generates reports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PRODUCTION_HOST="${PRODUCTION_API_URL:-https://api.example.com}"
REPORT_DIR="./load_test_reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create report directory
mkdir -p "$REPORT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Production Load Testing Suite${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Target: $PRODUCTION_HOST"
echo "Report Directory: $REPORT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to run a load test scenario
run_scenario() {
    local scenario_name=$1
    local users=$2
    local spawn_rate=$3
    local run_time=$4
    local description=$5

    echo -e "${YELLOW}========================================${NC}"
    echo -e "${YELLOW}Running: $scenario_name${NC}"
    echo -e "${YELLOW}Description: $description${NC}"
    echo -e "${YELLOW}========================================${NC}"
    echo "Users: $users"
    echo "Spawn Rate: $spawn_rate"
    echo "Duration: $run_time"
    echo ""

    local report_file="${REPORT_DIR}/${scenario_name}_${TIMESTAMP}"

    # Run locust in headless mode
    locust -f locustfile_production.py \
        --host="$PRODUCTION_HOST" \
        --users="$users" \
        --spawn-rate="$spawn_rate" \
        --run-time="$run_time" \
        --headless \
        --html="${report_file}.html" \
        --csv="${report_file}" \
        --loglevel=INFO

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ $scenario_name completed successfully${NC}"
        echo "Report: ${report_file}.html"
    else
        echo -e "${RED}❌ $scenario_name failed${NC}"
        return 1
    fi
    echo ""
}

# Scenario 1: Baseline Load Test
echo -e "${GREEN}Scenario 1: Baseline Load${NC}"
run_scenario \
    "baseline" \
    10 \
    1 \
    "5m" \
    "Normal load - establishes baseline performance metrics"

# Wait between scenarios
sleep 30

# Scenario 2: Peak Load Test (2x normal)
echo -e "${GREEN}Scenario 2: Peak Load (2x Normal)${NC}"
run_scenario \
    "peak_load" \
    100 \
    10 \
    "10m" \
    "Peak load - 2x expected traffic during busy periods"

# Wait between scenarios
sleep 30

# Scenario 3: Stress Test (find breaking point)
echo -e "${GREEN}Scenario 3: Stress Test${NC}"
run_scenario \
    "stress_test" \
    200 \
    20 \
    "15m" \
    "Stress test - push system to find breaking point"

# Wait for recovery
sleep 60

# Scenario 4: Endurance Test (sustained load)
echo -e "${GREEN}Scenario 4: Endurance Test${NC}"
run_scenario \
    "endurance" \
    50 \
    5 \
    "60m" \
    "Endurance test - sustained load to detect memory leaks"

# Generate summary report
echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Generating Summary Report${NC}"
echo -e "${YELLOW}========================================${NC}"

SUMMARY_FILE="${REPORT_DIR}/summary_${TIMESTAMP}.txt"

cat > "$SUMMARY_FILE" << EOF
Load Test Summary Report
Generated: $(date)
Target: $PRODUCTION_HOST

Scenarios Executed:
1. Baseline Load (10 users, 5 min)
2. Peak Load (100 users, 10 min)
3. Stress Test (200 users, 15 min)
4. Endurance Test (50 users, 60 min)

Reports Generated:
- baseline_${TIMESTAMP}.html
- peak_load_${TIMESTAMP}.html
- stress_test_${TIMESTAMP}.html
- endurance_${TIMESTAMP}.html

Review the HTML reports for detailed performance metrics.

Key Metrics to Review:
- P95 response time should be < 500ms
- P99 response time should be < 1000ms
- Failure rate should be < 1%
- No memory leaks during endurance test
- System should recover quickly after stress test

Next Steps:
1. Review all HTML reports
2. Compare against baseline metrics
3. Identify performance bottlenecks
4. Plan optimizations if thresholds not met
5. Re-run tests after optimizations
EOF

echo -e "${GREEN}Summary report saved to: $SUMMARY_FILE${NC}"
cat "$SUMMARY_FILE"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All Load Tests Completed${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Reports available in: $REPORT_DIR"
echo ""
echo "To view HTML reports:"
echo "  Open $REPORT_DIR/*.html in your browser"
echo ""
