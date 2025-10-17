"""Plotly Dash application for corporate intelligence visualization.

Clean, refactored implementation focused on REAL data visualization.
This module handles initialization and configuration only.
Layout and callbacks are separated for maintainability.

Architecture:
- dash_app.py: Application initialization and configuration
- layouts.py: UI components and layout structure
- callbacks.py: Data fetching and interactive behavior
"""

import logging
from typing import Optional

from dash import Dash
import dash_bootstrap_components as dbc
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.core.config import get_settings
from src.visualization.layouts import create_dashboard_layout
from src.visualization.callbacks import register_callbacks


class CorporateIntelDashboard:
    """Main dashboard application for EdTech intelligence - Real data only.

    This class orchestrates the dashboard by:
    1. Initializing the database connection
    2. Creating the Dash application
    3. Setting up the layout (from layouts.py)
    4. Registering callbacks (from callbacks.py)

    Attributes:
        settings: Application settings from environment
        logger: Logger instance for this module
        engine: SQLAlchemy database engine (synchronous)
        app: Dash application instance
    """

    def __init__(self):
        """Initialize the dashboard with database connection and Dash app."""
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)

        # Create synchronous database engine for Dash callbacks
        self.engine: Optional[Engine] = None
        try:
            sync_url = self.settings.sync_database_url
            self.engine = create_engine(sync_url, pool_pre_ping=True)
            self.logger.info("Database engine initialized successfully")
        except Exception as e:
            self.logger.warning(
                f"Failed to initialize database engine: {e}. "
                "Dashboard will show 'No data' messages."
            )

        # Initialize Dash application
        self.app = Dash(
            __name__,
            title="Corporate Intelligence Platform",
            update_title="Loading...",
            suppress_callback_exceptions=True,
            external_stylesheets=[dbc.themes.COSMO, dbc.icons.FONT_AWESOME],
        )

        # Set up layout from layouts module
        self.app.layout = create_dashboard_layout()

        # Register callbacks from callbacks module
        register_callbacks(self.app, self.engine)

    def run(self, debug: bool = False, port: int = 8050, host: str = "0.0.0.0"):
        """Run the dashboard application.

        Args:
            debug: Enable debug mode with hot reloading
            port: Port number to run the server on
            host: Host address to bind to (default: all interfaces)
        """
        self.logger.info(f"Starting dashboard on {host}:{port} (debug={debug})")
        self.app.run(debug=debug, port=port, host=host)


def create_app() -> Dash:
    """Factory function to create and return the Dash application.

    This is useful for testing and production deployments where you
    need access to the app object without running the server.

    Returns:
        Dash: Configured Dash application instance
    """
    dashboard = CorporateIntelDashboard()
    return dashboard.app


if __name__ == "__main__":
    """Run the dashboard application directly."""
    dashboard = CorporateIntelDashboard()
    print("=" * 60)
    print("🚀 Starting Corporate Intelligence Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8050")
    print("=" * 60)
    dashboard.run(debug=True, port=8050)
