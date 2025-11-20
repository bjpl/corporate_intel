"""
Data Transform Job

Applies transformations to data records.
"""

from typing import Any, Callable, Dict, List, Optional
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("data_transform")
class DataTransformJob(BaseJob):
    """
    Transform data records

    Parameters:
        data: List of records to transform
        transformations: List of transformation functions
        batch_size: Process records in batches
        parallel: Use parallel processing
    """

    max_retries = 2
    retry_delay = 1.0
    timeout = 600.0  # 10 minutes

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute data transformation"""
        data = kwargs.get("data", [])
        transformations = kwargs.get("transformations", [])
        batch_size = kwargs.get("batch_size", 1000)
        parallel = kwargs.get("parallel", False)

        if not data:
            raise ValueError("data is required")

        logger.info(f"Starting data transformation on {len(data)} records")

        transformed_data = []
        errors = []
        batch_count = 0

        # Process in batches
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            batch_count += 1

            # Apply transformations to batch
            for record in batch:
                try:
                    transformed_record = record.copy()

                    # Apply each transformation
                    for transform_func in transformations:
                        if callable(transform_func):
                            transformed_record = transform_func(transformed_record)
                        elif isinstance(transform_func, dict):
                            # Named transformation
                            transformed_record = self._apply_named_transform(
                                transformed_record,
                                transform_func
                            )

                    transformed_data.append(transformed_record)

                except Exception as e:
                    errors.append({
                        "record": record,
                        "error": str(e)
                    })
                    logger.warning(f"Error transforming record: {e}")

            # Update progress
            self.set_metadata("records_processed", len(transformed_data))
            self.set_metadata("batches_processed", batch_count)
            self.set_metadata("errors", len(errors))

            logger.info(
                f"Processed batch {batch_count}, "
                f"total records: {len(transformed_data)}"
            )

        success_rate = (len(transformed_data) / len(data)) * 100 if data else 0

        logger.info(
            f"Data transformation completed: {len(transformed_data)}/{len(data)} "
            f"records ({success_rate:.2f}% success rate)"
        )

        return {
            "records": transformed_data,
            "total_records": len(transformed_data),
            "original_count": len(data),
            "error_count": len(errors),
            "success_rate": success_rate,
            "errors": errors[:100]  # Limit error list
        }

    def _apply_named_transform(
        self,
        record: Dict[str, Any],
        transform: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply a named transformation"""
        transform_type = transform.get("type")

        if transform_type == "rename":
            # Rename fields
            mapping = transform.get("mapping", {})
            return {mapping.get(k, k): v for k, v in record.items()}

        elif transform_type == "filter":
            # Filter fields
            fields = transform.get("fields", [])
            return {k: v for k, v in record.items() if k in fields}

        elif transform_type == "convert":
            # Convert field types
            conversions = transform.get("conversions", {})
            result = record.copy()
            for field, target_type in conversions.items():
                if field in result:
                    if target_type == "int":
                        result[field] = int(result[field])
                    elif target_type == "float":
                        result[field] = float(result[field])
                    elif target_type == "str":
                        result[field] = str(result[field])
            return result

        elif transform_type == "default":
            # Set default values
            defaults = transform.get("defaults", {})
            result = record.copy()
            for field, default_value in defaults.items():
                if field not in result or result[field] is None:
                    result[field] = default_value
            return result

        return record

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting data transform job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        total_records = result.data.get("total_records", 0)
        success_rate = result.data.get("success_rate", 0)
        logger.info(
            f"Data transform job {self.job_id} completed: "
            f"{total_records} records ({success_rate:.2f}% success)"
        )
