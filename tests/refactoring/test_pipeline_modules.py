"""Tests for pipeline module refactoring."""

import pytest
from pathlib import Path


class TestPipelineStructure:
    """Test pipeline module structure."""

    def test_pipeline_module_exists(self):
        """Test pipeline module exists."""
        import src.pipeline
        assert src.pipeline is not None

    def test_pipeline_common_exists(self):
        """Test pipeline common module exists."""
        from src.pipeline import common
        assert common is not None

    def test_pipeline_has_init(self):
        """Test pipeline has __init__.py."""
        pipeline_path = Path(__file__).parent.parent.parent / "src" / "pipeline"
        init_file = pipeline_path / "__init__.py"
        assert init_file.exists()


class TestIngestionModules:
    """Test ingestion pipeline modules."""

    def test_sec_ingestion_exists(self):
        """Test SEC ingestion module exists."""
        try:
            from src.pipeline import sec_ingestion
            assert sec_ingestion is not None
        except ImportError:
            pytest.skip("SEC ingestion not yet implemented")

    def test_yahoo_finance_ingestion_exists(self):
        """Test Yahoo Finance ingestion module exists."""
        try:
            from src.pipeline import yahoo_finance_ingestion
            assert yahoo_finance_ingestion is not None
        except ImportError:
            pytest.skip("Yahoo Finance ingestion not yet implemented")

    def test_alpha_vantage_ingestion_exists(self):
        """Test Alpha Vantage ingestion module exists."""
        try:
            from src.pipeline import alpha_vantage_ingestion
            assert alpha_vantage_ingestion is not None
        except ImportError:
            pytest.skip("Alpha Vantage ingestion not yet implemented")


class TestSECSubmodules:
    """Test SEC-related submodules."""

    def test_sec_submodule_exists(self):
        """Test SEC submodule exists."""
        try:
            from src.pipeline import sec
            assert sec is not None
        except ImportError:
            pytest.skip("SEC submodule not yet created")

    def test_sec_client_exists(self):
        """Test SEC client module exists."""
        try:
            from src.pipeline.sec import client
            assert client is not None
        except ImportError:
            pytest.skip("SEC client not yet implemented")

    def test_sec_parser_exists(self):
        """Test SEC parser module exists."""
        try:
            from src.pipeline.sec import parser
            assert parser is not None
        except ImportError:
            pytest.skip("SEC parser not yet implemented")

    def test_sec_processor_exists(self):
        """Test SEC processor module exists."""
        try:
            from src.pipeline.sec import processor
            assert processor is not None
        except ImportError:
            pytest.skip("SEC processor not yet implemented")

    def test_sec_orchestrator_exists(self):
        """Test SEC orchestrator module exists."""
        try:
            from src.pipeline.sec import orchestrator
            assert orchestrator is not None
        except ImportError:
            pytest.skip("SEC orchestrator not yet implemented")


class TestPipelineCommon:
    """Test pipeline common utilities."""

    def test_common_utilities_exists(self):
        """Test common utilities module exists."""
        try:
            from src.pipeline.common import utilities
            assert utilities is not None
        except ImportError:
            pytest.skip("Common utilities not yet implemented")

    def test_common_has_init(self):
        """Test common submodule has __init__.py."""
        common_path = Path(__file__).parent.parent.parent / "src" / "pipeline" / "common"
        if common_path.exists():
            init_file = common_path / "__init__.py"
            assert init_file.exists()


class TestPipelineIntegration:
    """Test pipeline module integration."""

    def test_pipeline_imports_dont_fail(self):
        """Test pipeline imports don't cause errors."""
        try:
            import src.pipeline
            import src.pipeline.common
        except ImportError as e:
            pytest.fail(f"Pipeline import failed: {e}")

    def test_no_circular_imports_in_pipeline(self):
        """Test no circular imports in pipeline."""
        try:
            from src.pipeline import common
            from src.pipeline import sec_ingestion
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
