"""
Visualization Layout Constants and Base Classes
===============================================

This module contains color palettes, layout constants, and base
visualization component classes used throughout the dashboard.

SPARC Design:
- Specification: Centralized design system and color palette
- Architecture: Reusable constants and base classes
- Refinement: WCAG AA compliant colors for accessibility
"""


class VisualizationComponents:
    """
    SPARC-designed visualization component factory.

    Architecture Decision: Class-based to enable state management
    and component lifecycle hooks for future enhancements.
    """

    # Professional color palette with WCAG AA compliant contrast ratios
    COLORS = {
        'primary': '#2C5282',        # Professional blue (4.5:1 contrast on white)
        'secondary': '#4A7BA7',      # Muted medium blue
        'success': '#2F855A',        # Forest green
        'warning': '#D97706',        # Amber
        'danger': '#C53030',         # Deep red
        'info': '#2C5282',           # Same as primary for consistency
        'gradient_start': '#4A7BA7', # Removed - using solid colors
        'gradient_end': '#2C5282',   # Removed - using solid colors
    }

    # Category colors - muted, professional tones with good contrast
    CATEGORY_COLORS = {
        'k12': '#6B8E9F',                    # Slate blue
        'higher_education': '#5A8F7B',       # Sage green
        'corporate_learning': '#7C8FA6',     # Blue-gray
        'direct_to_consumer': '#8B9D83',     # Olive gray
        'enabling_technology': '#9D8E7C',    # Warm gray
    }
