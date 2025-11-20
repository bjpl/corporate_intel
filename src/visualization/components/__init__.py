"""
Visualization Components Package
=================================

This package provides backward-compatible re-exports of all visualization
component functions. Imports are organized by module for better maintainability.

Usage:
    from src.visualization.components import create_revenue_comparison_bar
    # OR
    from src.visualization.components.tables import create_revenue_comparison_bar
"""

# Re-export layout constants and base classes
from .layouts import VisualizationComponents

# Re-export complex chart functions
from .charts import (
    create_cohort_heatmap,
    create_competitive_landscape_scatter,
    create_market_share_sunburst,
    create_metrics_waterfall,
    create_retention_curves,
    create_segment_comparison_radar,
)

# Re-export tabular visualization functions
from .tables import (
    create_earnings_growth_distribution,
    create_margin_comparison_chart,
    create_revenue_by_category_treemap,
    create_revenue_comparison_bar,
)

# Filter components (placeholder for future use)
from . import filters

__all__ = [
    # Base classes and constants
    'VisualizationComponents',

    # Complex charts
    'create_cohort_heatmap',
    'create_competitive_landscape_scatter',
    'create_market_share_sunburst',
    'create_metrics_waterfall',
    'create_retention_curves',
    'create_segment_comparison_radar',

    # Tabular visualizations
    'create_earnings_growth_distribution',
    'create_margin_comparison_chart',
    'create_revenue_by_category_treemap',
    'create_revenue_comparison_bar',

    # Submodules
    'filters',
]
