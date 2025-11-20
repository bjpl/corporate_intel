"""
Data Validation Job

Validates data records against schemas and rules.
"""

from typing import Any, Dict, List, Optional
import logging

from src.jobs.base import BaseJob, JobRegistry, JobResult

logger = logging.getLogger(__name__)


@JobRegistry.register("data_validation")
class DataValidationJob(BaseJob):
    """
    Validate data records

    Parameters:
        data: List of records to validate
        schema: Validation schema
        rules: Custom validation rules
        strict: Fail on first error
    """

    max_retries = 1
    retry_delay = 1.0
    timeout = 600.0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute data validation"""
        data = kwargs.get("data", [])
        schema = kwargs.get("schema", {})
        rules = kwargs.get("rules", [])
        strict = kwargs.get("strict", False)

        if not data:
            raise ValueError("data is required")

        logger.info(f"Starting data validation on {len(data)} records")

        valid_records = []
        invalid_records = []
        errors = []

        for i, record in enumerate(data):
            record_errors = []

            # Validate against schema
            if schema:
                schema_errors = self._validate_schema(record, schema)
                record_errors.extend(schema_errors)

            # Apply custom rules
            for rule in rules:
                if callable(rule):
                    try:
                        if not rule(record):
                            record_errors.append({
                                "type": "custom_rule",
                                "message": "Custom validation rule failed"
                            })
                    except Exception as e:
                        record_errors.append({
                            "type": "rule_error",
                            "message": str(e)
                        })

            if record_errors:
                invalid_records.append(record)
                errors.append({
                    "record_index": i,
                    "record": record,
                    "errors": record_errors
                })

                if strict:
                    raise ValueError(f"Validation failed at record {i}: {record_errors}")
            else:
                valid_records.append(record)

            # Update progress
            if (i + 1) % 1000 == 0:
                self.set_metadata("records_validated", i + 1)
                logger.info(f"Validated {i + 1} records")

        validation_rate = (len(valid_records) / len(data)) * 100 if data else 0

        logger.info(
            f"Data validation completed: {len(valid_records)}/{len(data)} "
            f"valid ({validation_rate:.2f}%)"
        )

        return {
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "total_valid": len(valid_records),
            "total_invalid": len(invalid_records),
            "validation_rate": validation_rate,
            "errors": errors[:100]  # Limit errors
        }

    def _validate_schema(
        self,
        record: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Validate record against schema"""
        errors = []

        for field, field_schema in schema.items():
            # Required field check
            if field_schema.get("required", False) and field not in record:
                errors.append({
                    "type": "missing_field",
                    "field": field,
                    "message": f"Required field '{field}' is missing"
                })
                continue

            if field in record:
                value = record[field]

                # Type check
                expected_type = field_schema.get("type")
                if expected_type:
                    type_map = {
                        "string": str,
                        "int": int,
                        "float": float,
                        "bool": bool,
                        "list": list,
                        "dict": dict
                    }
                    expected_python_type = type_map.get(expected_type)
                    if expected_python_type and not isinstance(value, expected_python_type):
                        errors.append({
                            "type": "type_error",
                            "field": field,
                            "message": f"Expected {expected_type}, got {type(value).__name__}"
                        })

                # Min/max validation
                if "min" in field_schema and value < field_schema["min"]:
                    errors.append({
                        "type": "min_value",
                        "field": field,
                        "message": f"Value {value} is less than minimum {field_schema['min']}"
                    })

                if "max" in field_schema and value > field_schema["max"]:
                    errors.append({
                        "type": "max_value",
                        "field": field,
                        "message": f"Value {value} exceeds maximum {field_schema['max']}"
                    })

                # Pattern validation (for strings)
                if "pattern" in field_schema and isinstance(value, str):
                    import re
                    if not re.match(field_schema["pattern"], value):
                        errors.append({
                            "type": "pattern_mismatch",
                            "field": field,
                            "message": f"Value does not match pattern {field_schema['pattern']}"
                        })

                # Enum validation
                if "enum" in field_schema and value not in field_schema["enum"]:
                    errors.append({
                        "type": "enum_mismatch",
                        "field": field,
                        "message": f"Value must be one of {field_schema['enum']}"
                    })

        return errors

    def on_start(self) -> None:
        """Called when job starts"""
        logger.info(f"Starting data validation job {self.job_id}")

    def on_success(self, result: JobResult) -> None:
        """Called on successful completion"""
        validation_rate = result.data.get("validation_rate", 0)
        logger.info(
            f"Data validation job {self.job_id} completed: "
            f"{validation_rate:.2f}% valid"
        )
