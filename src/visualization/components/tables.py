"""
Tabular Visualization Components
================================

This module contains tabular and comparison chart components including
bar charts, margin comparisons, and distribution visualizations.

SPARC Design:
- Specification: Create comparison and distribution visualizations
- Architecture: Bar charts, box plots, and treemaps for data comparison
- Refinement: Interactive tooltips and responsive layouts
"""

from typing import Dict, List

import pandas as pd
import plotly.graph_objects as go

from .layouts import VisualizationComponents


def create_revenue_comparison_bar(companies_df: pd.DataFrame) -> go.Figure:
    """
    Create revenue comparison bar chart for all companies.

    SPARC Design:
    - Specification: Show actual revenue data across all companies
    - Pseudocode: Sort by revenue DESC, create bar chart by category
    - Architecture: Horizontal bar chart with category colors
    - Refinement: Interactive tooltips with company details
    """

    # Sort by revenue descending
    df = companies_df.sort_values('revenue', ascending=True, na_position='first')

    # Map category to colors
    df['color'] = df['category'].map(VisualizationComponents.CATEGORY_COLORS)

    fig = go.Figure()

    # Create bar chart
    fig.add_trace(go.Bar(
        y=df['ticker'],
        x=df['revenue'] / 1e6,  # Convert to millions
        orientation='h',
        marker=dict(
            color=df['color'],
            line=dict(color='white', width=1),
        ),
        text=[f"${r/1e6:.1f}M" for r in df['revenue']],
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Revenue: $%{x:.1f}M<br>" +
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="Revenue Comparison - All Companies",
        xaxis_title="Revenue ($M)",
        yaxis_title="",
        template="plotly_white",
        height=max(400, len(df) * 20),  # Dynamic height based on company count
        showlegend=False,
        margin=dict(l=80, r=120, t=60, b=40),
        xaxis=dict(
            tickformat="$,.0f",
            ticksuffix="M",
        ),
    )

    return fig


def create_margin_comparison_chart(companies_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """
    Create grouped bar chart comparing gross and operating margins.

    SPARC Design:
    - Specification: Compare margins for top companies
    - Pseudocode: Group bars showing GM and OM side by side
    - Architecture: Grouped bar chart with dual metrics
    - Refinement: Show only top N companies by revenue
    """

    # Filter to top N companies by revenue
    df = companies_df.nlargest(top_n, 'revenue')
    df = df.sort_values('revenue', ascending=True)

    fig = go.Figure()

    # Add gross margin bars
    fig.add_trace(go.Bar(
        name='Gross Margin',
        y=df['ticker'],
        x=df['gross_margin'],
        orientation='h',
        marker=dict(color=VisualizationComponents.COLORS['primary']),
        text=[f"{v:.1f}%" if pd.notna(v) else "N/A" for v in df['gross_margin']],
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Gross Margin: %{x:.1f}%<extra></extra>",
    ))

    # Add operating margin bars
    fig.add_trace(go.Bar(
        name='Operating Margin',
        y=df['ticker'],
        x=df['operating_margin'],
        orientation='h',
        marker=dict(color=VisualizationComponents.COLORS['success']),
        text=[f"{v:.1f}%" if pd.notna(v) else "N/A" for v in df['operating_margin']],
        textposition='outside',
        hovertemplate="<b>%{y}</b><br>Operating Margin: %{x:.1f}%<extra></extra>",
    ))

    fig.update_layout(
        title=f"Margin Comparison - Top {top_n} Companies by Revenue",
        xaxis_title="Margin (%)",
        yaxis_title="",
        template="plotly_white",
        height=max(400, top_n * 25),
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=80, r=120, t=60, b=40),
        xaxis=dict(
            tickformat=".0f",
            ticksuffix="%",
        ),
    )

    return fig


def create_earnings_growth_distribution(companies_df: pd.DataFrame) -> go.Figure:
    """
    Create box plot showing earnings growth distribution by category.

    SPARC Design:
    - Specification: Show distribution of earnings growth
    - Pseudocode: Filter companies with earnings_growth, create box plot by category
    - Architecture: Box plot with category grouping
    - Refinement: Show individual points for transparency
    """

    # Filter to companies with earnings growth data
    df = companies_df[companies_df['earnings_growth'].notna()].copy()

    if df.empty:
        # Return empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No earnings growth data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    fig = go.Figure()

    # Create box plot for each category
    for category in df['category'].unique():
        df_category = df[df['category'] == category]

        fig.add_trace(go.Box(
            y=df_category['earnings_growth'],
            name=category.replace('_', ' ').title(),
            marker=dict(
                color=VisualizationComponents.CATEGORY_COLORS.get(
                    category,
                    VisualizationComponents.COLORS['info']
                )
            ),
            boxpoints='all',  # Show all points
            jitter=0.3,
            pointpos=-1.8,
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Earnings Growth: %{y:.1f}%<br>" +
                "<extra></extra>"
            ),
            text=df_category['ticker'],
        ))

    fig.update_layout(
        title=f"Earnings Growth Distribution by Category ({len(df)} companies)",
        yaxis_title="Earnings Growth (%)",
        xaxis_title="Category",
        template="plotly_white",
        height=500,
        showlegend=False,
        yaxis=dict(
            tickformat=".0f",
            ticksuffix="%",
            zeroline=True,
            zerolinecolor='gray',
            zerolinewidth=1,
        ),
    )

    return fig


def create_revenue_by_category_treemap(companies_df: pd.DataFrame) -> go.Figure:
    """
    Create treemap showing revenue distribution by category and company.

    SPARC Design:
    - Specification: Hierarchical view of revenue by category
    - Pseudocode: Build tree structure (root -> category -> companies)
    - Architecture: Treemap with 2-level hierarchy
    - Refinement: Size by revenue, color by category
    """

    # Prepare hierarchical data
    labels = []
    parents = []
    values = []
    colors = []

    # Add root
    labels.append("EdTech Market")
    parents.append("")
    values.append(0)  # Will be calculated from children
    colors.append(VisualizationComponents.COLORS['primary'])

    # Add categories
    for category in companies_df['category'].unique():
        df_cat = companies_df[companies_df['category'] == category]
        cat_revenue = df_cat['revenue'].sum()

        labels.append(category.replace('_', ' ').title())
        parents.append("EdTech Market")
        values.append(cat_revenue)
        colors.append(VisualizationComponents.CATEGORY_COLORS.get(
            category,
            VisualizationComponents.COLORS['info']
        ))

        # Add companies in this category
        for _, row in df_cat.iterrows():
            if pd.notna(row['revenue']) and row['revenue'] > 0:
                labels.append(f"{row['ticker']}")
                parents.append(category.replace('_', ' ').title())
                values.append(row['revenue'])
                colors.append(VisualizationComponents.CATEGORY_COLORS.get(
                    category,
                    VisualizationComponents.COLORS['info']
                ))

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(
            colors=colors,
            line=dict(color="white", width=2),
        ),
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
        hovertemplate=(
            "<b>%{label}</b><br>" +
            "Revenue: $%{value:,.0f}<br>" +
            "<extra></extra>"
        ),
    ))

    fig.update_layout(
        title="Revenue Distribution - Market Treemap",
        template="plotly_white",
        height=500,
        margin=dict(t=60, b=0, l=0, r=0),
    )

    return fig
