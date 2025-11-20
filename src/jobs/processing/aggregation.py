"""
Data Aggregation Job

Aggregates and summarizes data.
"""

from typing import Any, Dict, List, Optional
from collections import defaultdict
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("data_aggregation")
class DataAggregationJob(BaseJob):
    """
    Aggregate data records

    Parameters:
        data: List of records to aggregate
        group_by: Fields to group by
        aggregations: Aggregation operations
    """

    max_retries = 2
    retry_delay = 1.0
    timeout = 600.0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute data aggregation"""
        data = kwargs.get("data", [])
        group_by = kwargs.get("group_by", [])
        aggregations = kwargs.get("aggregations", {})

        if not data:
            raise ValueError("data is required")

        logger.info(f"Starting data aggregation on {len(data)} records")

        # Group data
        groups = defaultdict(list)

        for record in data:
            # Create group key
            if group_by:
                key = tuple(record.get(field) for field in group_by)
            else:
                key = "all"

            groups[key].append(record)

        # Aggregate each group
        aggregated = []

        for key, group_records in groups.items():
            agg_record = {}

            # Add group by fields
            if group_by and key != "all":
                for i, field in enumerate(group_by):
                    agg_record[field] = key[i]

            # Apply aggregations
            for field, agg_func in aggregations.items():
                values = [r.get(field) for r in group_records if field in r]

                if agg_func == "count":
                    agg_record[f"{field}_count"] = len(values)
                elif agg_func == "sum":
                    agg_record[f"{field}_sum"] = sum(values) if values else 0
                elif agg_func == "avg":
                    agg_record[f"{field}_avg"] = sum(values) / len(values) if values else 0
                elif agg_func == "min":
                    agg_record[f"{field}_min"] = min(values) if values else None
                elif agg_func == "max":
                    agg_record[f"{field}_max"] = max(values) if values else None
                elif agg_func == "distinct":
                    agg_record[f"{field}_distinct"] = len(set(values))

            # Add record count
            agg_record["_count"] = len(group_records)

            aggregated.append(agg_record)

        logger.info(
            f"Data aggregation completed: {len(data)} records -> "
            f"{len(aggregated)} groups"
        )

        return {
            "records": aggregated,
            "total_groups": len(aggregated),
            "original_count": len(data),
            "group_by": group_by,
            "aggregations": aggregations
        }

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting data aggregation job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        total_groups = result.data.get("total_groups", 0)
        logger.info(
            f"Data aggregation job {self.job_id} completed: {total_groups} groups"
        )
