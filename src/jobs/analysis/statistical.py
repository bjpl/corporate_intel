"""
Statistical Analysis Job

Performs statistical analysis on datasets.
"""

from typing import Any, Dict, List, Optional
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("statistical_analysis")
class StatisticalAnalysisJob(BaseJob):
    """
    Perform statistical analysis on data

    Parameters:
        data: List of records to analyze
        metrics: List of metrics to calculate
        groupby: Optional grouping field
    """

    max_retries = 2
    retry_delay = 1.0
    timeout = 600.0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute statistical analysis"""
        data = kwargs.get("data", [])
        metrics = kwargs.get("metrics", ["mean", "median", "std", "min", "max"])
        groupby = kwargs.get("groupby")

        if not data:
            raise ValueError("data is required")

        logger.info(f"Starting statistical analysis on {len(data)} records")

        # Import numpy for calculations
        try:
            import numpy as np
        except ImportError:
            logger.warning("numpy not available, using basic statistics")
            np = None

        # Extract numeric fields
        numeric_fields = self._get_numeric_fields(data)

        if not numeric_fields:
            raise ValueError("No numeric fields found in data")

        # Calculate statistics
        statistics = {}

        for field in numeric_fields:
            values = [r[field] for r in data if field in r and r[field] is not None]

            if not values:
                continue

            field_stats = {}

            if "count" in metrics:
                field_stats["count"] = len(values)

            if "mean" in metrics:
                field_stats["mean"] = sum(values) / len(values) if values else 0

            if "median" in metrics:
                sorted_values = sorted(values)
                mid = len(sorted_values) // 2
                if len(sorted_values) % 2 == 0:
                    field_stats["median"] = (sorted_values[mid - 1] + sorted_values[mid]) / 2
                else:
                    field_stats["median"] = sorted_values[mid]

            if "min" in metrics:
                field_stats["min"] = min(values)

            if "max" in metrics:
                field_stats["max"] = max(values)

            if "sum" in metrics:
                field_stats["sum"] = sum(values)

            if "std" in metrics and np:
                field_stats["std"] = float(np.std(values))

            if "var" in metrics and np:
                field_stats["var"] = float(np.var(values))

            statistics[field] = field_stats

        logger.info(f"Statistical analysis completed for {len(numeric_fields)} fields")

        return {
            "statistics": statistics,
            "fields_analyzed": numeric_fields,
            "total_records": len(data),
            "metrics": metrics
        }

    def _get_numeric_fields(self, data: List[Dict[str, Any]]) -> List[str]:
        """Identify numeric fields in data"""
        if not data:
            return []

        numeric_fields = []
        sample = data[0]

        for field, value in sample.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                numeric_fields.append(field)

        return numeric_fields

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting statistical analysis job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        fields_analyzed = len(result.data.get("fields_analyzed", []))
        logger.info(
            f"Statistical analysis job {self.job_id} completed: "
            f"{fields_analyzed} fields analyzed"
        )
