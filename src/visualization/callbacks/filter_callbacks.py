"""
Filter Callback Functions
=========================

This module contains callbacks for filter controls and user interactions.

SPARC Design:
- Specification: Handle filter state and user controls
- Architecture: Simple state toggles and filter updates
- Refinement: Real-time responsiveness
"""

import logging
from typing import Optional

from dash import Input, Output
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def register_filter_callbacks(app, engine: Optional[Engine]):
    """Register filter and control callbacks.

    Args:
        app: Dash application instance
        engine: SQLAlchemy database engine (can be None if DB unavailable)
    """

    @app.callback(
        Output("interval-component", "disabled"),
        Input("auto-refresh-toggle", "value")
    )
    def toggle_auto_refresh(auto_refresh: bool) -> bool:
        """Enable/disable auto-refresh based on toggle state.

        Args:
            auto_refresh: Boolean state of auto-refresh toggle

        Returns:
            bool: Inverted state (disabled = not auto_refresh)
        """
        return not auto_refresh
