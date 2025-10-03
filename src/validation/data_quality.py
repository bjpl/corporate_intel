"""Data quality validation using Great Expectations and Pandera."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import great_expectations as gx
import pandas as pd
import pandera as pa
from great_expectations.checkpoint import Checkpoint
from great_expectations.core.batch import RuntimeBatchRequest
from great_expectations.core.yaml_handler import YAMLHandler
from loguru import logger
from pandera.typing import DataFrame, Series

from src.core.config import get_settings


# Pandera schemas for dataframe validation
class FinancialMetricsSchema(pa.SchemaModel):
    """Schema for financial metrics dataframe."""
    
    company_id: Series[str] = pa.Field(nullable=False)
    ticker: Series[str] = pa.Field(nullable=False, regex="^[A-Z]{1,5}$")
    metric_date: Series[pd.Timestamp] = pa.Field(nullable=False)
    metric_type: Series[str] = pa.Field(
        nullable=False,
        isin=[
            "revenue", "monthly_active_users", "average_revenue_per_user",
            "customer_acquisition_cost", "net_revenue_retention",
            "course_completion_rate", "gross_margin", "churn_rate"
        ]
    )
    value: Series[float] = pa.Field(nullable=False, ge=0)
    unit: Series[str] = pa.Field(nullable=False, isin=["USD", "percent", "count"])
    confidence_score: Series[float] = pa.Field(nullable=True, ge=0, le=1)
    
    class Config:
        coerce = True
        strict = True
        
    @pa.check("value")
    def check_reasonable_values(cls, values: Series[float], metric_type: Series[str]) -> Series[bool]:
        """Check that values are within reasonable ranges for each metric type."""
        checks = []
        
        for val, m_type in zip(values, metric_type):
            if m_type == "net_revenue_retention" and not (50 <= val <= 200):
                checks.append(False)  # NRR typically between 50-200%
            elif m_type == "churn_rate" and not (0 <= val <= 50):
                checks.append(False)  # Churn rarely exceeds 50%
            elif m_type == "gross_margin" and not (0 <= val <= 100):
                checks.append(False)  # Margin is a percentage
            else:
                checks.append(True)
        
        return Series(checks)


class SECFilingSchema(pa.SchemaModel):
    """Schema for SEC filing data."""
    
    company_id: Series[str] = pa.Field(nullable=False)
    filing_type: Series[str] = pa.Field(
        nullable=False,
        isin=["10-K", "10-Q", "8-K", "DEF 14A", "20-F", "S-1", "S-4"]
    )
    filing_date: Series[pd.Timestamp] = pa.Field(nullable=False)
    accession_number: Series[str] = pa.Field(
        nullable=False,
        regex="^[0-9]{10}-[0-9]{2}-[0-9]{6}$"
    )
    content_length: Series[int] = pa.Field(nullable=False, gt=100)  # Minimum content
    
    @pa.check("filing_date")
    def check_filing_date_reasonable(cls, dates: Series[pd.Timestamp]) -> Series[bool]:
        """Ensure filing dates are not in the future and not too old."""
        today = pd.Timestamp.now()
        min_date = pd.Timestamp("1994-01-01")  # EDGAR started in 1994
        
        return (dates <= today) & (dates >= min_date)


class DataQualityValidator:
    """Main data quality validation orchestrator."""
    
    def __init__(self):
        self.settings = get_settings()
        self.context = self._initialize_context()
        self.expectations = self._load_expectations()
    
    def _initialize_context(self) -> gx.DataContext:
        """Initialize Great Expectations context."""
        config = {
            "datasources": {
                "pandas_datasource": {
                    "class_name": "Datasource",
                    "module_name": "great_expectations.datasource",
                    "execution_engine": {
                        "class_name": "PandasExecutionEngine",
                        "module_name": "great_expectations.execution_engine",
                    },
                    "data_connectors": {
                        "runtime_data_connector": {
                            "class_name": "RuntimeDataConnector",
                            "module_name": "great_expectations.datasource.data_connector",
                            "batch_identifiers": ["default_identifier_name"],
                        },
                    },
                },
            },
            "stores": {
                "expectations_store": {
                    "class_name": "ExpectationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "expectations/",
                    },
                },
                "validations_store": {
                    "class_name": "ValidationsStore",
                    "store_backend": {
                        "class_name": "TupleFilesystemStoreBackend",
                        "base_directory": "validations/",
                    },
                },
            },
            "expectations_store_name": "expectations_store",
            "validations_store_name": "validations_store",
            "evaluation_parameter_store_name": "evaluation_parameter_store",
        }
        
        context = gx.get_context(mode="ephemeral", project_config=config)
        return context
    
    def _load_expectations(self) -> Dict[str, Any]:
        """Load or create expectation suites."""
        expectations = {}
        
        # Financial metrics expectations
        expectations["financial_metrics"] = self._create_financial_metrics_expectations()
        
        # SEC filing expectations
        expectations["sec_filings"] = self._create_sec_filing_expectations()
        
        # Document quality expectations
        expectations["documents"] = self._create_document_expectations()
        
        return expectations
    
    def _create_financial_metrics_expectations(self) -> Dict[str, Any]:
        """Create expectations for financial metrics."""
        return {
            "columns": {
                "company_id": {"not_null": True},
                "ticker": {"not_null": True, "regex": "^[A-Z]{1,5}$"},
                "metric_date": {"not_null": True},
                "metric_type": {"not_null": True, "in_set": [
                    "revenue", "mau", "arpu", "cac", "nrr", "completion_rate"
                ]},
                "value": {"not_null": True, "min": 0},
            },
            "row_conditions": [
                {
                    "name": "reasonable_revenue",
                    "condition": "metric_type == 'revenue' implies value < 1e12"  # < $1 trillion
                },
                {
                    "name": "percentage_bounds",
                    "condition": "unit == 'percent' implies 0 <= value <= 100"
                },
            ],
            "aggregate_expectations": [
                {
                    "name": "unique_company_metric_date",
                    "columns": ["company_id", "metric_type", "metric_date"],
                    "unique": True
                },
            ]
        }
    
    def _create_sec_filing_expectations(self) -> Dict[str, Any]:
        """Create expectations for SEC filings."""
        return {
            "columns": {
                "accession_number": {
                    "not_null": True,
                    "regex": "^[0-9]{10}-[0-9]{2}-[0-9]{6}$",
                    "unique": True
                },
                "filing_type": {
                    "not_null": True,
                    "in_set": ["10-K", "10-Q", "8-K", "DEF 14A", "20-F"]
                },
                "content": {
                    "not_null": True,
                    "min_length": 1000  # Minimum content length
                },
            },
            "content_quality": [
                {
                    "name": "has_financial_tables",
                    "check": "contains_financial_data"
                },
                {
                    "name": "valid_html_or_text",
                    "check": "valid_format"
                },
            ]
        }
    
    def _create_document_expectations(self) -> Dict[str, Any]:
        """Create expectations for processed documents."""
        return {
            "embedding_quality": {
                "dimension": 384,  # Using sentence-transformers
                "not_null": True,
                "normalized": True,  # Should be unit vectors
            },
            "chunk_quality": {
                "min_length": 100,
                "max_length": 2000,
                "overlap_present": True,
            },
            "metadata_completeness": {
                "required_fields": ["source", "date", "company_id", "document_type"],
            }
        }
    
    def validate_dataframe(
        self,
        df: pd.DataFrame,
        schema: pa.SchemaModel
    ) -> tuple[bool, List[str]]:
        """Validate dataframe using Pandera schema."""
        try:
            schema.validate(df)
            return True, []
        except pa.errors.SchemaErrors as e:
            errors = []
            for error in e.failure_cases.to_dict(orient="records"):
                errors.append(f"{error['column']}: {error['check']} failed for {error['failure_case']}")
            return False, errors
    
    def validate_financial_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate financial metrics data."""
        logger.info(f"Validating {len(df)} financial metrics")
        
        # Pandera validation
        is_valid, errors = self.validate_dataframe(df, FinancialMetricsSchema)
        
        # Great Expectations validation
        batch_request = RuntimeBatchRequest(
            datasource_name="pandas_datasource",
            data_connector_name="runtime_data_connector",
            data_asset_name="financial_metrics",
            runtime_parameters={"batch_data": df},
            batch_identifiers={"default_identifier_name": "default_identifier"},
        )
        
        # Run expectations
        expectation_suite_name = "financial_metrics_suite"
        
        results = {
            "pandera_valid": is_valid,
            "pandera_errors": errors,
            "row_count": len(df),
            "unique_companies": df["company_id"].nunique() if "company_id" in df else 0,
            "date_range": {
                "min": df["metric_date"].min() if "metric_date" in df else None,
                "max": df["metric_date"].max() if "metric_date" in df else None,
            },
        }
        
        # Check for anomalies
        anomalies = self._detect_metric_anomalies(df)
        if anomalies:
            results["anomalies"] = anomalies
        
        return results
    
    def _detect_metric_anomalies(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in financial metrics."""
        anomalies = []
        
        if "value" not in df.columns or "metric_type" not in df.columns:
            return anomalies
        
        # Check for sudden changes (>50% change)
        for company_id in df["company_id"].unique():
            company_df = df[df["company_id"] == company_id].sort_values("metric_date")
            
            for metric_type in company_df["metric_type"].unique():
                metric_df = company_df[company_df["metric_type"] == metric_type]
                
                if len(metric_df) > 1:
                    values = metric_df["value"].values
                    pct_changes = (values[1:] - values[:-1]) / values[:-1] * 100
                    
                    for i, pct_change in enumerate(pct_changes):
                        if abs(pct_change) > 50:
                            anomalies.append({
                                "company_id": company_id,
                                "metric_type": metric_type,
                                "date": metric_df.iloc[i + 1]["metric_date"],
                                "change_pct": pct_change,
                                "severity": "high" if abs(pct_change) > 100 else "medium"
                            })
        
        return anomalies
    
    def validate_sec_filing(self, filing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual SEC filing."""
        results = {
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        
        # Check required fields
        required_fields = ["accession_number", "filing_type", "content", "filing_date"]
        for field in required_fields:
            if field not in filing_data or not filing_data[field]:
                results["valid"] = False
                results["errors"].append(f"Missing required field: {field}")
        
        # Validate accession number format
        if "accession_number" in filing_data:
            import re
            if not re.match(r"^[0-9]{10}-[0-9]{2}-[0-9]{6}$", filing_data["accession_number"]):
                results["valid"] = False
                results["errors"].append("Invalid accession number format")
        
        # Check content quality
        if "content" in filing_data:
            content = filing_data["content"]
            
            # Minimum length check
            if len(content) < 1000:
                results["warnings"].append("Content suspiciously short")
            
            # Check for financial data presence
            financial_keywords = ["revenue", "income", "assets", "liabilities", "cash flow"]
            if not any(keyword in content.lower() for keyword in financial_keywords):
                results["warnings"].append("No financial keywords found")
            
            # Check for tables (simple heuristic)
            if "<table" in content.lower() or "|-" in content:
                results["has_tables"] = True
            else:
                results["has_tables"] = False
                results["warnings"].append("No tables detected")
        
        # Validate filing date
        if "filing_date" in filing_data:
            try:
                filing_date = pd.Timestamp(filing_data["filing_date"])
                if filing_date > pd.Timestamp.now():
                    results["valid"] = False
                    results["errors"].append("Filing date in the future")
                elif filing_date < pd.Timestamp("1994-01-01"):
                    results["warnings"].append("Filing date before EDGAR system (1994)")
            except:
                results["valid"] = False
                results["errors"].append("Invalid filing date format")
        
        return results
    
    def validate_embeddings(self, embeddings: np.ndarray, expected_dim: int = 384) -> Dict[str, Any]:
        """Validate embedding quality."""
        import numpy as np
        
        results = {
            "valid": True,
            "shape": embeddings.shape,
            "issues": [],
        }
        
        # Check dimension
        if embeddings.shape[1] != expected_dim:
            results["valid"] = False
            results["issues"].append(f"Wrong dimension: {embeddings.shape[1]} vs {expected_dim}")
        
        # Check for NaN or Inf
        if np.any(np.isnan(embeddings)):
            results["valid"] = False
            results["issues"].append("Contains NaN values")
        
        if np.any(np.isinf(embeddings)):
            results["valid"] = False
            results["issues"].append("Contains infinite values")
        
        # Check normalization (should be unit vectors for cosine similarity)
        norms = np.linalg.norm(embeddings, axis=1)
        if not np.allclose(norms, 1.0, atol=0.01):
            results["issues"].append("Embeddings not normalized")
            results["mean_norm"] = np.mean(norms)
            results["std_norm"] = np.std(norms)
        
        # Check diversity (embeddings shouldn't be too similar)
        if len(embeddings) > 1:
            similarities = np.dot(embeddings, embeddings.T)
            np.fill_diagonal(similarities, 0)  # Ignore self-similarity
            
            mean_similarity = np.mean(np.abs(similarities))
            if mean_similarity > 0.9:
                results["issues"].append(f"Embeddings too similar (mean similarity: {mean_similarity:.2f})")
            
            results["embedding_diversity"] = {
                "mean_similarity": mean_similarity,
                "max_similarity": np.max(similarities),
                "min_similarity": np.min(similarities),
            }
        
        return results
    
    def create_validation_report(
        self,
        validation_results: Dict[str, Any]
    ) -> str:
        """Create a formatted validation report."""
        report = []
        report.append("=" * 60)
        report.append("DATA QUALITY VALIDATION REPORT")
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("=" * 60)
        
        # Summary
        total_issues = sum(
            len(v.get("errors", [])) + len(v.get("warnings", []))
            for v in validation_results.values()
        )
        
        report.append(f"\nTotal Issues Found: {total_issues}")
        
        # Detailed results
        for category, results in validation_results.items():
            report.append(f"\n{category.upper()}")
            report.append("-" * 40)
            
            if "valid" in results:
                status = "✅ VALID" if results["valid"] else "❌ INVALID"
                report.append(f"Status: {status}")
            
            if "errors" in results and results["errors"]:
                report.append("\nErrors:")
                for error in results["errors"]:
                    report.append(f"  • {error}")
            
            if "warnings" in results and results["warnings"]:
                report.append("\nWarnings:")
                for warning in results["warnings"]:
                    report.append(f"  ⚠ {warning}")
            
            if "anomalies" in results and results["anomalies"]:
                report.append(f"\nAnomalies Detected: {len(results['anomalies'])}")
                for anomaly in results["anomalies"][:5]:  # Show first 5
                    report.append(f"  • {anomaly['metric_type']} changed {anomaly['change_pct']:.1f}% "
                                f"for {anomaly['company_id']}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)