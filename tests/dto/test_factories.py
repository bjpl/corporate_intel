"""Tests for DTO factories."""

from datetime import datetime
from uuid import uuid4

import pytest

from src.dto.api.companies import CompanyDTO, CompanyListDTO
from src.dto.api.filings import FilingDTO, FilingListDTO
from src.dto.api.metrics import MetricDTO, MetricsListDTO
from src.dto.factories import (
    companies_to_list_dto,
    company_to_dto,
    dict_to_dto,
    filing_to_dto,
    filings_to_list_dto,
    metric_to_dto,
    metrics_to_list_dto,
    model_to_dto,
    models_to_dtos,
    paginated_response,
)


class MockCompany:
    """Mock Company model for testing."""

    def __init__(self):
        self.id = uuid4()
        self.ticker = "CHGG"
        self.name = "Chegg, Inc."
        self.cik = "0001364954"
        self.sector = "Technology"
        self.subsector = "EdTech"
        self.category = "higher_education"
        self.subcategory = ["homework_help"]
        self.delivery_model = "b2c"
        self.monetization_strategy = ["subscription"]
        self.founded_year = 2005
        self.headquarters = "Santa Clara, CA"
        self.website = "https://www.chegg.com"
        self.employee_count = 3200
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockFiling:
    """Mock SECFiling model for testing."""

    def __init__(self):
        self.id = uuid4()
        self.company_id = uuid4()
        self.filing_type = "10-K"
        self.filing_date = datetime.utcnow()
        self.accession_number = "0001193125-25-123456"
        self.filing_url = "https://sec.gov/filing"
        self.processing_status = "completed"
        self.processed_at = datetime.utcnow()
        self.error_message = None
        self.raw_text = "Filing content..."
        self.parsed_sections = {"item_1": "Business"}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class MockMetric:
    """Mock FinancialMetric model for testing."""

    def __init__(self):
        self.id = 12345
        self.company_id = uuid4()
        self.metric_date = datetime.utcnow()
        self.period_type = "quarterly"
        self.metric_type = "revenue"
        self.metric_category = "financial"
        self.value = 194500000
        self.unit = "USD"
        self.source = "sec_filing"
        self.source_document_id = uuid4()
        self.confidence_score = 1.0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()


class TestCompanyFactories:
    """Test company DTO factories."""

    def test_company_to_dto(self):
        """Test converting Company model to DTO."""
        company = MockCompany()
        dto = company_to_dto(company)

        assert isinstance(dto, CompanyDTO)
        assert dto.id == company.id
        assert dto.ticker == company.ticker
        assert dto.name == company.name
        assert dto.category == company.category

    def test_companies_to_list_dto(self):
        """Test converting list of companies to list DTO."""
        companies = [MockCompany(), MockCompany()]
        list_dto = companies_to_list_dto(
            companies=companies,
            total=27,
            limit=100,
            offset=0
        )

        assert isinstance(list_dto, CompanyListDTO)
        assert len(list_dto.companies) == 2
        assert list_dto.total == 27
        assert list_dto.limit == 100
        assert list_dto.offset == 0

    def test_empty_company_list(self):
        """Test converting empty company list."""
        list_dto = companies_to_list_dto(
            companies=[],
            total=0,
            limit=100,
            offset=0
        )

        assert len(list_dto.companies) == 0
        assert list_dto.total == 0


class TestFilingFactories:
    """Test filing DTO factories."""

    def test_filing_to_dto(self):
        """Test converting Filing model to DTO."""
        filing = MockFiling()
        dto = filing_to_dto(filing)

        assert isinstance(dto, FilingDTO)
        assert dto.id == filing.id
        assert dto.filing_type == filing.filing_type
        assert dto.processing_status == filing.processing_status

    def test_filings_to_list_dto(self):
        """Test converting list of filings to list DTO."""
        filings = [MockFiling(), MockFiling()]
        list_dto = filings_to_list_dto(
            filings=filings,
            total=156,
            limit=100,
            offset=0
        )

        assert isinstance(list_dto, FilingListDTO)
        assert len(list_dto.filings) == 2
        assert list_dto.total == 156


class TestMetricFactories:
    """Test metric DTO factories."""

    def test_metric_to_dto(self):
        """Test converting Metric model to DTO."""
        metric = MockMetric()
        dto = metric_to_dto(metric)

        assert isinstance(dto, MetricDTO)
        assert dto.id == metric.id
        assert dto.metric_type == metric.metric_type
        assert dto.value == metric.value

    def test_metrics_to_list_dto(self):
        """Test converting list of metrics to list DTO."""
        metrics = [MockMetric(), MockMetric(), MockMetric()]
        list_dto = metrics_to_list_dto(
            metrics=metrics,
            total=1500,
            limit=100,
            offset=0
        )

        assert isinstance(list_dto, MetricsListDTO)
        assert len(list_dto.metrics) == 3
        assert list_dto.total == 1500


class TestGenericFactories:
    """Test generic factory functions."""

    def test_model_to_dto(self):
        """Test generic model to DTO conversion."""
        company = MockCompany()
        dto = model_to_dto(company, CompanyDTO)

        assert isinstance(dto, CompanyDTO)
        assert dto.ticker == company.ticker

    def test_models_to_dtos(self):
        """Test converting list of models to DTOs."""
        companies = [MockCompany(), MockCompany()]
        dtos = models_to_dtos(companies, CompanyDTO)

        assert len(dtos) == 2
        assert all(isinstance(dto, CompanyDTO) for dto in dtos)

    def test_dict_to_dto(self):
        """Test converting dictionary to DTO."""
        data = {
            "ticker": "DUOL",
            "company_name": "Duolingo, Inc.",
            "edtech_category": "direct_to_consumer",
            "revenue_yoy_growth": 45.3,
            "latest_revenue": 531000000,
            "overall_score": 92.5,
            "growth_rank": 1,
            "company_health_status": "healthy"
        }

        from src.dto.api.companies import TrendingCompanyDTO
        dto = dict_to_dto(data, TrendingCompanyDTO)

        assert isinstance(dto, TrendingCompanyDTO)
        assert dto.ticker == "DUOL"
        assert dto.revenue_yoy_growth == 45.3

    def test_paginated_response(self):
        """Test generic paginated response factory."""
        companies = [MockCompany(), MockCompany()]
        company_dtos = models_to_dtos(companies, CompanyDTO)

        list_dto = paginated_response(
            items=company_dtos,
            total=27,
            limit=20,
            offset=0,
            list_dto_class=CompanyListDTO
        )

        assert isinstance(list_dto, CompanyListDTO)
        assert len(list_dto.companies) == 2
        assert list_dto.total == 27


class TestFactoryErrorHandling:
    """Test factory error handling."""

    def test_invalid_model_data(self):
        """Test factory with invalid model data."""
        class InvalidModel:
            ticker = "INVALID@"  # Invalid ticker format

        with pytest.raises(Exception):  # Will raise validation error
            model_to_dto(InvalidModel(), CompanyDTO)

    def test_missing_required_fields(self):
        """Test factory with missing required fields."""
        data = {
            "ticker": "TEST"
            # Missing required 'company_name' field
        }

        from src.dto.api.companies import TrendingCompanyDTO
        with pytest.raises(Exception):
            dict_to_dto(data, TrendingCompanyDTO)
