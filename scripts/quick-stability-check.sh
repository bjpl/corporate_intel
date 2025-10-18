#!/bin/bash
# Quick Stability Check - Short 5-minute validation
# For rapid testing and validation before full 1-hour monitoring

set -euo pipefail

# Configuration for quick check (5 minutes)
export MONITORING_DURATION=300  # 5 minutes
export SAMPLE_INTERVAL=15       # Sample every 15 seconds (20 samples)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running Quick Stability Check (5 minutes, 20 samples)"
echo "This validates the monitoring system before the full 1-hour observation"
echo ""

# Run the main stability monitor with short duration
bash "${SCRIPT_DIR}/stability-monitor.sh"
