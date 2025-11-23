#!/bin/bash
# Deploy New Dashboard with Real Data Visualizations

echo "🚀 Deploying Updated Dashboard with Real Data Visualizations"
echo "=============================================================="
echo ""

# Backup old dashboard
echo "📦 Backing up old dashboard..."
if [ -f "src/visualization/dash_app.py" ]; then
    cp src/visualization/dash_app.py src/visualization/dash_app_backup_$(date +%Y%m%d_%H%M%S).py
    echo "✅ Backup created"
else
    echo "⚠️  No existing dashboard found"
fi

# Deploy new dashboard
echo ""
echo "🔄 Deploying new dashboard..."
if [ -f "src/visualization/dash_app_updated.py" ]; then
    cp src/visualization/dash_app_updated.py src/visualization/dash_app.py
    echo "✅ New dashboard deployed"
else
    echo "❌ Updated dashboard file not found!"
    exit 1
fi

# Show what changed
echo ""
echo "📊 New Visualizations Added:"
echo "  1. ✅ Revenue Comparison Bar Chart (23 companies)"
echo "  2. ✅ Margin Comparison Chart (Gross vs Operating)"
echo "  3. ✅ Earnings Growth Distribution (12 companies with data)"
echo "  4. ✅ Revenue by Category Treemap"
echo ""
echo "🗑️  Removed Visualizations (No Data):"
echo "  - ❌ Retention Curves (no cohort data)"
echo "  - ❌ Cohort Heatmap (no cohort data)"
echo "  - ❌ Competitive Landscape Scatter (insufficient YoY growth data)"
echo ""
echo "✨ Dashboard deployment complete!"
echo ""
echo "To start the dashboard:"
echo "  python src/visualization/dash_app.py"
echo ""
echo "Access at: http://localhost:8050"
