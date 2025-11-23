"""Common utilities for data ingestion pipelines.

DEPRECATED: This module is being consolidated into common/utilities.py
All new code should import from src.pipeline.common.utilities instead.

This file is kept temporarily for backwards compatibility but will be removed
in a future release. See src/pipeline/common/utilities.py for the canonical
implementation of all shared pipeline functions.
"""

import warnings
from src.pipeline.common.utilities import (
    get_or_create_company,
    upsert_financial_metric,
    retry_with_backoff,
    run_coordination_hook,
    notify_progress
)

# Emit deprecation warning
warnings.warn(
    "src.pipeline.common is deprecated. Use src.pipeline.common.utilities instead.",
    DeprecationWarning,
    stacklevel=2
)

__all__ = [
    'get_or_create_company',
    'upsert_financial_metric',
    'retry_with_backoff',
    'run_coordination_hook',
    'notify_progress'
]
