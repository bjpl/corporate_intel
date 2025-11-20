"""
Visualization Callbacks Package
================================

This package provides backward-compatible re-exports of callback registration
functions. The main register_callbacks function coordinates all callback types.

Usage:
    from src.visualization.callbacks import register_callbacks
    register_callbacks(app, engine)
"""

from typing import Optional
from sqlalchemy.engine import Engine

from .data_callbacks import register_data_callbacks
from .filter_callbacks import register_filter_callbacks
from .navigation_callbacks import register_navigation_callbacks


def register_callbacks(app, engine: Optional[Engine]):
    """
    Register all dashboard callbacks.

    This is the main entry point for callback registration, maintaining
    backward compatibility with the original callbacks.py interface.

    Args:
        app: Dash application instance
        engine: SQLAlchemy database engine (can be None if DB unavailable)
    """
    # Register all callback categories
    register_data_callbacks(app, engine)
    register_filter_callbacks(app, engine)
    register_navigation_callbacks(app, engine)


__all__ = [
    'register_callbacks',
    'register_data_callbacks',
    'register_filter_callbacks',
    'register_navigation_callbacks',
]
