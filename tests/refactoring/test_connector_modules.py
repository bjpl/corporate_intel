"""Tests for connector module refactoring."""

import pytest
from pathlib import Path


class TestConnectorStructure:
    """Test connector module structure."""

    def test_connectors_module_exists(self):
        """Test connectors module exists."""
        import src.connectors
        assert src.connectors is not None

    def test_connectors_has_init(self):
        """Test connectors has __init__.py."""
        connectors_path = Path(__file__).parent.parent.parent / "src" / "connectors"
        init_file = connectors_path / "__init__.py"
        assert init_file.exists()


class TestConnectorSubmodules:
    """Test connector submodules."""

    def test_connector_imports_work(self):
        """Test connector imports work."""
        try:
            import src.connectors
        except ImportError as e:
            pytest.fail(f"Connector import failed: {e}")


class TestConnectorIntegration:
    """Test connector integration."""

    def test_connectors_dont_cause_import_errors(self):
        """Test connectors don't cause import errors."""
        try:
            from src import connectors
            assert connectors is not None
        except ImportError as e:
            pytest.fail(f"Connector caused import error: {e}")
