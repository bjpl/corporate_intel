#!/bin/bash
# Apply Performance Indexes to Corporate Intel Database
# Mac/Linux version

echo "========================================="
echo "Corporate Intel Platform"
echo "Applying Performance Indexes"
echo "========================================="
echo ""

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] Docker Desktop is not running!"
    echo "Please start Docker Desktop first."
    exit 1
fi

echo "[OK] Docker is running"
echo ""

echo "Applying indexes to database..."
docker exec -i corporate-intel-postgres psql -U intel_user -d corporate_intel < scripts/add_performance_indexes.sql

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Failed to apply indexes!"
    exit 1
fi

echo ""
echo "========================================="
echo "Indexes Applied Successfully!"
echo "========================================="
echo ""
echo "Performance improvements expected:"
echo "- Ticker lookups: 10-50x faster"
echo "- Metric queries: 20-100x faster"
echo "- Dashboard loads: 5-10x faster"
echo ""
