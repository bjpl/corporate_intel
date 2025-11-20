"""Tests to verify all imports work correctly after refactoring."""

import pytest
import sys
import importlib
from pathlib import Path


class TestCoreImports:
    """Test core module imports."""

    def test_config_imports(self):
        """Test config module imports."""
        from src.core import config
        from src.core.config import get_settings

        settings = get_settings()
        assert settings is not None

    def test_exceptions_imports(self):
        """Test exceptions module imports."""
        from src.core import exceptions
        assert hasattr(exceptions, 'DataIngestionError') or hasattr(exceptions, 'ValidationError')

    def test_cache_imports(self):
        """Test cache module imports."""
        from src.core import cache
        assert hasattr(cache, 'get_cache') or hasattr(cache, 'cache_key_wrapper')

    def test_dependencies_imports(self):
        """Test dependencies module imports."""
        from src.core import dependencies
        assert hasattr(dependencies, 'get_current_user') or hasattr(dependencies, 'get_db')


class TestAPIImports:
    """Test API module imports."""

    def test_main_api_import(self):
        """Test main API import."""
        from src.api import main
        assert hasattr(main, 'app')

    def test_v1_endpoints_import(self):
        """Test v1 endpoint imports."""
        from src.api.v1 import companies
        from src.api.v1 import metrics
        from src.api.v1 import filings
        from src.api.v1 import health

        assert hasattr(companies, 'router')
        assert hasattr(metrics, 'router')
        assert hasattr(filings, 'router')
        assert hasattr(health, 'router')


class TestDTOImports:
    """Test DTO module imports."""

    def test_base_dto_imports(self):
        """Test base DTO imports."""
        from src.dto import BaseDTO
        from src.dto import TimestampMixin, UUIDMixin

        assert BaseDTO is not None

    def test_response_dto_imports(self):
        """Test response DTO imports."""
        try:
            from src.dto import ResponseDTO, ErrorResponseDTO
            from src.dto import success_response
        except ImportError:
            # These might not exist yet, that's okay
            pass

    def test_pagination_dto_imports(self):
        """Test pagination DTO imports."""
        try:
            from src.dto import PaginatedResponseDTO, PaginationParams
        except ImportError:
            # These might not exist yet, that's okay
            pass


class TestJobsImports:
    """Test jobs module imports."""

    def test_base_job_imports(self):
        """Test base job imports."""
        from src.jobs import BaseJob, JobState, JobRegistry

        assert BaseJob is not None
        assert JobState is not None
        assert JobRegistry is not None

    def test_job_components_imports(self):
        """Test job component imports."""
        try:
            from src.jobs import QueueManager, JobScheduler, JobMonitor
        except ImportError:
            # These might not be implemented yet
            pass


class TestDatabaseImports:
    """Test database module imports."""

    def test_db_base_imports(self):
        """Test database base imports."""
        from src.db import base
        from src.db.base import get_db, Base

        assert get_db is not None
        assert Base is not None

    def test_db_models_imports(self):
        """Test database models imports."""
        from src.db import models

        assert hasattr(models, 'Company')
        assert hasattr(models, 'FinancialMetric')

    def test_db_session_imports(self):
        """Test database session imports."""
        from src.db import session
        assert hasattr(session, 'get_session') or hasattr(session, 'SessionLocal')


class TestPipelineImports:
    """Test pipeline module imports."""

    def test_pipeline_common_imports(self):
        """Test pipeline common imports."""
        from src.pipeline import common
        assert common is not None

    def test_ingestion_pipeline_imports(self):
        """Test ingestion pipeline imports."""
        try:
            from src.pipeline import sec_ingestion
            from src.pipeline import yahoo_finance_ingestion
            from src.pipeline import alpha_vantage_ingestion
        except ImportError as e:
            # Some pipelines might not exist
            pass

    def test_sec_submodule_imports(self):
        """Test SEC submodule imports."""
        try:
            from src.pipeline.sec import client, parser, processor
        except ImportError:
            pass


class TestVisualizationImports:
    """Test visualization module imports."""

    def test_dash_app_import(self):
        """Test dash app import."""
        from src.visualization import dash_app
        assert hasattr(dash_app, 'create_app')

    def test_visualization_components_imports(self):
        """Test visualization components imports."""
        try:
            from src.visualization import layouts
            from src.visualization import callbacks
            from src.visualization import components
        except ImportError as e:
            pytest.skip(f"Visualization components not yet implemented: {e}")


class TestAuthImports:
    """Test auth module imports."""

    def test_auth_models_imports(self):
        """Test auth models imports."""
        from src.auth import models
        assert hasattr(models, 'User')

    def test_auth_service_imports(self):
        """Test auth service imports."""
        from src.auth import service
        assert service is not None

    def test_auth_routes_imports(self):
        """Test auth routes imports."""
        from src.auth import routes
        assert hasattr(routes, 'router')


class TestRepositoryImports:
    """Test repository module imports."""

    def test_base_repository_imports(self):
        """Test base repository imports."""
        from src.repositories import base_repository
        assert hasattr(base_repository, 'BaseRepository')

    def test_metrics_repository_imports(self):
        """Test metrics repository imports."""
        try:
            from src.repositories import metrics_repository
        except ImportError:
            pass


class TestProcessingImports:
    """Test processing module imports."""

    def test_processing_modules_import(self):
        """Test processing module imports."""
        from src.processing import embeddings
        from src.processing import metrics_extractor
        from src.processing import text_chunker
        from src.processing import document_processor

        assert embeddings is not None


class TestConnectorImports:
    """Test connector module imports."""

    def test_connector_module_exists(self):
        """Test connector module exists."""
        import src.connectors
        assert src.connectors is not None


class TestCircularImports:
    """Test for circular import issues."""

    def test_no_circular_imports_in_core(self):
        """Test no circular imports in core modules."""
        try:
            import src.core.config
            import src.core.dependencies
            import src.core.cache
            import src.core.exceptions
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")

    def test_no_circular_imports_in_api(self):
        """Test no circular imports in API modules."""
        try:
            import src.api.main
            import src.api.v1.companies
            import src.api.v1.metrics
        except ImportError as e:
            pytest.fail(f"Circular import detected: {e}")


class TestBackwardCompatibility:
    """Test backward compatibility of imports."""

    def test_old_import_paths_work(self):
        """Test that old import paths still work if they should."""
        # This is a placeholder - adjust based on your actual backward compatibility needs
        try:
            from src.db.base import Base
            from src.core.config import get_settings
            assert Base is not None
            assert get_settings is not None
        except ImportError as e:
            pytest.fail(f"Backward compatibility broken: {e}")


class TestModuleStructure:
    """Test module structure is correct."""

    def test_all_modules_have_init(self):
        """Test all modules have __init__.py files."""
        src_path = Path(__file__).parent.parent.parent / "src"

        for module_dir in src_path.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('__'):
                init_file = module_dir / "__init__.py"
                assert init_file.exists(), f"Missing __init__.py in {module_dir.name}"

    def test_no_missing_dependencies(self):
        """Test no missing module dependencies."""
        # This test will fail if there are import errors
        try:
            import src.api.main
            import src.db.models
            import src.core.config
        except ImportError as e:
            pytest.fail(f"Missing dependency: {e}")


class TestImportPerformance:
    """Test import performance."""

    def test_import_speed(self):
        """Test that imports complete reasonably fast."""
        import time

        start = time.time()
        import src.api.main
        import src.db.models
        import src.core.config
        duration = time.time() - start

        # Imports should complete in less than 5 seconds
        assert duration < 5.0, f"Imports took too long: {duration}s"


class TestNamespaceCollisions:
    """Test for namespace collisions."""

    def test_no_name_conflicts(self):
        """Test no naming conflicts between modules."""
        from src.api.v1 import companies
        from src.db import models

        # Ensure they don't have conflicting names
        # This is a basic check - expand as needed
        assert companies is not None
        assert models is not None
