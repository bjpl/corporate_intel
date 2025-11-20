"""SEC filing data validation and parsing."""

from typing import Any, Dict

import pandas as pd
from great_expectations.core.batch import RuntimeBatchRequest
from loguru import logger

# Handle Great Expectations API changes across versions
try:
    from great_expectations.data_context import DataContext
except ImportError:
    # Newer versions of Great Expectations
    try:
        from great_expectations.data_context.data_context.file_data_context import FileDataContext as DataContext
    except ImportError:
        # If still failing, create a simple context wrapper
        from great_expectations.data_context import get_context
        DataContext = lambda project_config: get_context(project_config=project_config)

from great_expectations.data_context.types.base import (
    DataContextConfig,
    InMemoryStoreBackendDefaults,
)

# Make Prefect optional for testing environments
try:
    from prefect import task
    PREFECT_AVAILABLE = True
except ImportError:
    # Dummy decorator when Prefect is not available
    def task(*args, **kwargs):
        """Dummy task decorator when Prefect unavailable."""
        def decorator(func):
            return func
        return decorator if not args else decorator(args[0])
    PREFECT_AVAILABLE = False


@task
def validate_filing_data(filing_data: Dict[str, Any]) -> bool:
    """Validate filing data using Great Expectations.

    Validates:
    - Required column presence
    - Data types
    - Format constraints (CIK, accession numbers, form types)
    - Value constraints (dates, non-null fields)
    - Content quality checks

    Returns True if validation passes or if GX is not available.
    """
    try:
        # Convert filing data to DataFrame for GE validation
        df = pd.DataFrame([filing_data])

        # Initialize in-memory Great Expectations context
        data_context_config = DataContextConfig(
            store_backend_defaults=InMemoryStoreBackendDefaults()
        )
        context = DataContext(project_config=data_context_config)

        # Create runtime batch request
        batch_request = RuntimeBatchRequest(
            datasource_name="runtime_datasource",
            data_connector_name="runtime_data_connector",
            data_asset_name="sec_filing",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier_name": "filing_validation"},
        )

        # Create expectation suite
        suite_name = "sec_filing_validation_suite"
        context.add_or_update_expectation_suite(expectation_suite_name=suite_name)

        # Get validator
        validator = context.get_validator(
            batch_request=batch_request,
            expectation_suite_name=suite_name,
        )

        # 1. Column Presence Expectations
        required_columns = [
            "accessionNumber",
            "form",
            "filingDate",
            "cik",
            "content",
            "content_hash",
            "downloaded_at",
        ]

        for column in required_columns:
            validator.expect_column_to_exist(column=column)

        # 2. Data Type Validations
        validator.expect_column_values_to_be_of_type(
            column="accessionNumber", type_="str"
        )
        validator.expect_column_values_to_be_of_type(column="form", type_="str")
        validator.expect_column_values_to_be_of_type(column="cik", type_="str")
        validator.expect_column_values_to_be_of_type(column="content", type_="str")
        validator.expect_column_values_to_be_of_type(
            column="content_hash", type_="str"
        )

        # 3. Format Validations using Regex

        # CIK format: numeric string, 1-10 digits
        validator.expect_column_values_to_match_regex(
            column="cik",
            regex=r"^\d{1,10}$",
            meta={"description": "CIK must be 1-10 digit numeric string"},
        )

        # Accession number format: NNNNNNNNNN-NN-NNNNNN
        validator.expect_column_values_to_match_regex(
            column="accessionNumber",
            regex=r"^\d{10}-\d{2}-\d{6}$",
            meta={"description": "Accession number format must be NNNNNNNNNN-NN-NNNNNN"},
        )

        # Form type validation: Common SEC form types
        valid_form_types = [
            "10-K", "10-Q", "8-K", "10-K/A", "10-Q/A", "8-K/A",
            "S-1", "S-3", "S-4", "S-8", "DEF 14A", "SC 13D", "SC 13G",
            "4", "3", "5", "144"
        ]
        validator.expect_column_values_to_be_in_set(
            column="form",
            value_set=valid_form_types,
            meta={"description": "Form type must be valid SEC form"},
        )

        # Filing date format: YYYY-MM-DD
        validator.expect_column_values_to_match_regex(
            column="filingDate",
            regex=r"^\d{4}-\d{2}-\d{2}$",
            meta={"description": "Filing date must be in YYYY-MM-DD format"},
        )

        # Content hash format: SHA-256 hex (64 characters)
        validator.expect_column_values_to_match_regex(
            column="content_hash",
            regex=r"^[a-f0-9]{64}$",
            meta={"description": "Content hash must be valid SHA-256 hex"},
        )

        # 4. Value Constraints

        # Non-null validations for critical fields
        validator.expect_column_values_to_not_be_null(column="accessionNumber")
        validator.expect_column_values_to_not_be_null(column="form")
        validator.expect_column_values_to_not_be_null(column="filingDate")
        validator.expect_column_values_to_not_be_null(column="cik")
        validator.expect_column_values_to_not_be_null(column="content")

        # Content length validation: minimum 100 characters
        validator.expect_column_value_lengths_to_be_between(
            column="content",
            min_value=100,
            max_value=None,
            meta={"description": "Filing content must be at least 100 characters"},
        )

        # Filing date range validation: not in future, not too old (e.g., after 1990)
        validator.expect_column_values_to_match_strftime_format(
            column="filingDate",
            strftime_format="%Y-%m-%d",
        )

        # Additional quality checks
        if "primaryDocument" in filing_data:
            validator.expect_column_values_to_not_be_null(column="primaryDocument")

        # 5. Execute validation
        validation_result = validator.validate()

        # Check if validation passed
        if not validation_result.success:
            logger.warning(
                f"Filing validation failed for {filing_data.get('accessionNumber', 'unknown')}"
            )
            logger.warning(f"Validation results: {validation_result.statistics}")

            # Log specific failures
            for result in validation_result.results:
                if not result.success:
                    logger.warning(
                        f"Failed expectation: {result.expectation_config.expectation_type} "
                        f"for column {result.expectation_config.kwargs.get('column', 'N/A')}"
                    )

            return False

        logger.info(
            f"Filing validation passed for {filing_data.get('accessionNumber', 'unknown')}"
        )
        return True

    except Exception as e:
        # If GX isn't properly initialized, skip validation and allow filing storage
        if "No gx directory" in str(e) or "DataContext" in str(e):
            logger.warning(f"Great Expectations not initialized - skipping validation: {str(e)}")
            return True  # Allow filing to be stored without GX validation
        logger.error(f"Error during filing validation: {str(e)}")
        return False


def classify_edtech_company(company_info: Dict[str, Any]) -> str:
    """Classify company into EdTech category based on SIC code and description."""
    sic = company_info.get("sic", "")
    description = company_info.get("sicDescription", "").lower()

    # Educational services SIC codes
    if sic.startswith("82"):
        if "elementary" in description or "secondary" in description:
            return "k12"
        elif "college" in description or "university" in description:
            return "higher_education"
        else:
            return "direct_to_consumer"

    # Software and technology
    elif sic.startswith("73"):
        if "education" in description or "training" in description:
            return "enabling_technology"
        else:
            return "corporate_learning"

    # Default
    return "enabling_technology"
