"""Tests for company DTOs."""

from datetime import datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.dto.api.companies import (
    CompanyCreateDTO,
    CompanyDTO,
    CompanyListDTO,
    CompanyMetricsDTO,
    TrendingCompanyDTO,
)


class TestCompanyCreateDTO:
    """Test CompanyCreateDTO validation and creation."""

    def test_valid_company_create(self):
        """Test creating valid company DTO."""
        dto = CompanyCreateDTO(
            ticker="CHGG",
            name="Chegg, Inc.",
            cik="0001364954",
            sector="Technology",
            subsector="EdTech",
            category="higher_education",
            subcategory=["homework_help", "study_resources"],
            delivery_model="b2c",
            monetization_strategy=["subscription"],
            founded_year=2005,
            headquarters="Santa Clara, CA",
            website="https://www.chegg.com",
            employee_count=3200
        )

        assert dto.ticker == "CHGG"
        assert dto.name == "Chegg, Inc."
        assert dto.category == "higher_education"
        assert "homework_help" in dto.subcategory

    def test_ticker_uppercase_validation(self):
        """Test ticker is converted to uppercase."""
        dto = CompanyCreateDTO(
            ticker="chgg",
            name="Chegg, Inc."
        )

        assert dto.ticker == "CHGG"

    def test_invalid_ticker_format(self):
        """Test ticker validation with invalid format."""
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="invalid@ticker",
                name="Test Company"
            )

    def test_invalid_cik_format(self):
        """Test CIK validation."""
        # Too short
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                cik="123"
            )

        # Non-numeric
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                cik="abcd123456"
            )

    def test_invalid_category(self):
        """Test category validation."""
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                category="invalid_category"
            )

    def test_invalid_delivery_model(self):
        """Test delivery model validation."""
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                delivery_model="invalid_model"
            )

    def test_founded_year_validation(self):
        """Test founded year bounds."""
        # Too early
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                founded_year=1700
            )

        # Future year
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                founded_year=2200
            )

    def test_employee_count_validation(self):
        """Test employee count must be non-negative."""
        with pytest.raises(ValidationError):
            CompanyCreateDTO(
                ticker="TEST",
                name="Test",
                employee_count=-100
            )


class TestCompanyDTO:
    """Test CompanyDTO."""

    def test_company_dto_creation(self):
        """Test creating company response DTO."""
        company_id = uuid4()
        now = datetime.utcnow()

        dto = CompanyDTO(
            id=company_id,
            ticker="DUOL",
            name="Duolingo, Inc.",
            cik="0001788577",
            sector="Technology",
            subsector="EdTech",
            category="direct_to_consumer",
            created_at=now,
            updated_at=now
        )

        assert dto.id == company_id
        assert dto.ticker == "DUOL"
        assert dto.category == "direct_to_consumer"
        assert dto.created_at == now


class TestCompanyListDTO:
    """Test CompanyListDTO."""

    def test_company_list_dto(self):
        """Test company list response."""
        companies = [
            CompanyDTO(
                id=uuid4(),
                ticker="CHGG",
                name="Chegg, Inc.",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            CompanyDTO(
                id=uuid4(),
                ticker="DUOL",
                name="Duolingo, Inc.",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]

        dto = CompanyListDTO(
            companies=companies,
            total=27,
            limit=100,
            offset=0
        )

        assert len(dto.companies) == 2
        assert dto.total == 27
        assert dto.limit == 100
        assert dto.offset == 0

    def test_empty_company_list(self):
        """Test empty company list."""
        dto = CompanyListDTO(
            companies=[],
            total=0,
            limit=100,
            offset=0
        )

        assert len(dto.companies) == 0
        assert dto.total == 0


class TestCompanyMetricsDTO:
    """Test CompanyMetricsDTO."""

    def test_company_metrics_dto(self):
        """Test company metrics DTO."""
        company_id = uuid4()

        dto = CompanyMetricsDTO(
            company_id=company_id,
            ticker="CHGG",
            latest_revenue=776500000,
            revenue_growth_yoy=-4.2,
            monthly_active_users=7800000,
            arpu=8.32,
            cac=45.50,
            nrr=95.3,
            last_updated=datetime.utcnow()
        )

        assert dto.company_id == company_id
        assert dto.ticker == "CHGG"
        assert dto.latest_revenue == 776500000
        assert dto.revenue_growth_yoy == -4.2
        assert dto.nrr == 95.3

    def test_negative_revenue_validation(self):
        """Test revenue cannot be negative."""
        with pytest.raises(ValidationError):
            CompanyMetricsDTO(
                company_id=uuid4(),
                ticker="TEST",
                latest_revenue=-1000,
                last_updated=datetime.utcnow()
            )

    def test_nrr_bounds(self):
        """Test NRR percentage bounds."""
        # Valid
        dto = CompanyMetricsDTO(
            company_id=uuid4(),
            ticker="TEST",
            nrr=120.5,
            last_updated=datetime.utcnow()
        )
        assert dto.nrr == 120.5

        # Too high
        with pytest.raises(ValidationError):
            CompanyMetricsDTO(
                company_id=uuid4(),
                ticker="TEST",
                nrr=250.0,
                last_updated=datetime.utcnow()
            )


class TestTrendingCompanyDTO:
    """Test TrendingCompanyDTO."""

    def test_trending_company_dto(self):
        """Test trending company DTO."""
        dto = TrendingCompanyDTO(
            ticker="DUOL",
            company_name="Duolingo, Inc.",
            edtech_category="direct_to_consumer",
            revenue_yoy_growth=45.3,
            latest_revenue=531000000,
            overall_score=92.5,
            growth_rank=1,
            company_health_status="healthy"
        )

        assert dto.ticker == "DUOL"
        assert dto.revenue_yoy_growth == 45.3
        assert dto.overall_score == 92.5
        assert dto.growth_rank == 1

    def test_score_bounds(self):
        """Test overall score bounds."""
        # Too high
        with pytest.raises(ValidationError):
            TrendingCompanyDTO(
                ticker="TEST",
                company_name="Test",
                edtech_category="k12",
                overall_score=150.0
            )

        # Negative
        with pytest.raises(ValidationError):
            TrendingCompanyDTO(
                ticker="TEST",
                company_name="Test",
                edtech_category="k12",
                overall_score=-10.0
            )

    def test_growth_rank_validation(self):
        """Test growth rank must be positive."""
        with pytest.raises(ValidationError):
            TrendingCompanyDTO(
                ticker="TEST",
                company_name="Test",
                edtech_category="k12",
                growth_rank=0
            )
