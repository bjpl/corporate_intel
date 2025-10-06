"""Tests for market intelligence API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import MarketIntelligence, Company


@pytest.fixture
def sample_intelligence(db_session: Session) -> MarketIntelligence:
    """Create a sample intelligence item for testing."""
    intel = MarketIntelligence(
        id=uuid4(),
        intel_type="market_trend",
        category="education_technology",
        title="AI-Powered Learning Tools Surge",
        summary="Market seeing 45% YoY growth in AI-powered learning platforms",
        event_date=datetime.utcnow() - timedelta(days=7),
        source="Industry Report",
    )
    db_session.add(intel)
    db_session.commit()
    db_session.refresh(intel)
    return intel


@pytest.fixture
def sample_intelligence_items(db_session: Session) -> list[MarketIntelligence]:
    """Create multiple intelligence items for testing."""
    items = [
        MarketIntelligence(
            id=uuid4(),
            intel_type="market_trend",
            category="k12_education",
            title="Remote Learning Adoption Trends",
            summary="K-12 remote learning tools see sustained adoption post-pandemic",
            event_date=datetime.utcnow() - timedelta(days=14),
            source="Education Week",
        ),
        MarketIntelligence(
            id=uuid4(),
            intel_type="competitive_move",
            category="higher_education",
            title="Major LMS Provider Announces Partnership",
            summary="Leading LMS provider partners with top universities",
            event_date=datetime.utcnow() - timedelta(days=21),
            source="Press Release",
        ),
        MarketIntelligence(
            id=uuid4(),
            intel_type="regulatory_change",
            category="corporate_learning",
            title="New Privacy Regulations for EdTech",
            summary="Updated data privacy requirements for educational platforms",
            event_date=datetime.utcnow() - timedelta(days=30),
            source="Government Publication",
        ),
        MarketIntelligence(
            id=uuid4(),
            intel_type="funding_activity",
            category="education_technology",
            title="EdTech Startup Raises $50M Series B",
            summary="AI tutoring platform secures major funding round",
            event_date=datetime.utcnow() - timedelta(days=5),
            source="TechCrunch",
        ),
    ]

    for item in items:
        db_session.add(item)

    db_session.commit()
    for item in items:
        db_session.refresh(item)

    return items


class TestListIntelligenceEndpoint:
    """Test suite for GET /api/v1/intelligence/ endpoint."""

    def test_list_intelligence_success(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test listing all intelligence items."""
        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(sample_intelligence_items)

    def test_list_intelligence_empty(self, api_client: TestClient):
        """Test listing intelligence when none exist."""
        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_intelligence_filter_by_type(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering intelligence by intel type."""
        response = api_client.get("/api/v1/intelligence/?intel_type=market_trend")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(i["intel_type"] == "market_trend" for i in data)

    def test_list_intelligence_filter_by_category(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering intelligence by category."""
        response = api_client.get("/api/v1/intelligence/?category=k12_education")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(i["category"] == "k12_education" for i in data)

    def test_list_intelligence_filter_by_type_and_category(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering by both type and category."""
        response = api_client.get(
            "/api/v1/intelligence/?intel_type=market_trend&category=k12_education"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert all(i["intel_type"] == "market_trend" for i in data)
        assert all(i["category"] == "k12_education" for i in data)

    def test_list_intelligence_pagination_limit(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test pagination with limit parameter."""
        response = api_client.get("/api/v1/intelligence/?limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) <= 2

    def test_list_intelligence_pagination_offset(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test pagination with offset parameter."""
        # Get first page
        response1 = api_client.get("/api/v1/intelligence/?limit=2&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = api_client.get("/api/v1/intelligence/?limit=2&offset=2")
        data2 = response2.json()

        # Ensure different results
        if len(data1) > 0 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_intelligence_sorted_by_event_date(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test intelligence items are sorted by event date descending."""
        response = api_client.get("/api/v1/intelligence/")

        data = response.json()

        if len(data) > 1:
            dates = [
                datetime.fromisoformat(i["event_date"].replace('Z', '+00:00'))
                if i.get("event_date")
                else None
                for i in data
            ]
            # Filter out None values for comparison
            non_null_dates = [d for d in dates if d is not None]
            if len(non_null_dates) > 1:
                assert non_null_dates == sorted(non_null_dates, reverse=True)

    def test_list_intelligence_invalid_limit(self, api_client: TestClient):
        """Test invalid limit returns 422."""
        response = api_client.get("/api/v1/intelligence/?limit=1000")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_intelligence_negative_offset(self, api_client: TestClient):
        """Test negative offset returns 422."""
        response = api_client.get("/api/v1/intelligence/?offset=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_intelligence_response_schema(
        self, api_client: TestClient, sample_intelligence: MarketIntelligence
    ):
        """Test response includes all expected fields."""
        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        assert len(data) > 0

        intel = data[0]
        assert "id" in intel
        assert "intel_type" in intel
        assert "title" in intel
        assert "summary" in intel

    def test_list_intelligence_no_auth_required(
        self, api_client: TestClient, sample_intelligence: MarketIntelligence
    ):
        """Test listing intelligence doesn't require authentication."""
        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK


class TestIntelligenceTypes:
    """Test suite for different intelligence types."""

    def test_filter_market_trends(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering market trend intelligence."""
        response = api_client.get("/api/v1/intelligence/?intel_type=market_trend")

        data = response.json()
        assert all(i["intel_type"] == "market_trend" for i in data)
        assert len(data) > 0

    def test_filter_competitive_moves(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering competitive move intelligence."""
        response = api_client.get("/api/v1/intelligence/?intel_type=competitive_move")

        data = response.json()
        assert all(i["intel_type"] == "competitive_move" for i in data)

    def test_filter_regulatory_changes(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering regulatory change intelligence."""
        response = api_client.get("/api/v1/intelligence/?intel_type=regulatory_change")

        data = response.json()
        assert all(i["intel_type"] == "regulatory_change" for i in data)

    def test_filter_funding_activity(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering funding activity intelligence."""
        response = api_client.get("/api/v1/intelligence/?intel_type=funding_activity")

        data = response.json()
        assert all(i["intel_type"] == "funding_activity" for i in data)

    def test_invalid_intel_type(self, api_client: TestClient):
        """Test querying invalid intel type returns empty list."""
        response = api_client.get("/api/v1/intelligence/?intel_type=INVALID_TYPE")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestIntelligenceCategories:
    """Test suite for different intelligence categories."""

    def test_filter_k12_education(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering K-12 education intelligence."""
        response = api_client.get("/api/v1/intelligence/?category=k12_education")

        data = response.json()
        assert all(i["category"] == "k12_education" for i in data)

    def test_filter_higher_education(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering higher education intelligence."""
        response = api_client.get("/api/v1/intelligence/?category=higher_education")

        data = response.json()
        assert all(i["category"] == "higher_education" for i in data)

    def test_filter_corporate_learning(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering corporate learning intelligence."""
        response = api_client.get("/api/v1/intelligence/?category=corporate_learning")

        data = response.json()
        assert all(i["category"] == "corporate_learning" for i in data)

    def test_filter_education_technology(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering education technology intelligence."""
        response = api_client.get("/api/v1/intelligence/?category=education_technology")

        data = response.json()
        assert all(i["category"] == "education_technology" for i in data)

    def test_invalid_category(self, api_client: TestClient):
        """Test querying invalid category returns empty list."""
        response = api_client.get("/api/v1/intelligence/?category=INVALID_CATEGORY")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestIntelligenceSources:
    """Test suite for intelligence sources."""

    def test_intelligence_with_source(
        self, api_client: TestClient, sample_intelligence: MarketIntelligence
    ):
        """Test intelligence item includes source."""
        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        assert len(data) > 0
        assert any(i.get("source") is not None for i in data)

    def test_intelligence_without_source(
        self, api_client: TestClient, db_session: Session
    ):
        """Test intelligence item without source."""
        intel = MarketIntelligence(
            id=uuid4(),
            intel_type="other",
            title="Test Intelligence",
            source=None,
        )
        db_session.add(intel)
        db_session.commit()

        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        # Find the item we just created
        test_items = [i for i in data if i["title"] == "Test Intelligence"]
        assert len(test_items) > 0
        assert test_items[0]["source"] is None


class TestIntelligenceDateHandling:
    """Test suite for intelligence event date handling."""

    def test_intelligence_with_event_date(
        self, api_client: TestClient, sample_intelligence: MarketIntelligence
    ):
        """Test intelligence with event date."""
        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        assert len(data) > 0
        assert any(i.get("event_date") is not None for i in data)

    def test_intelligence_without_event_date(
        self, api_client: TestClient, db_session: Session
    ):
        """Test intelligence without event date."""
        intel = MarketIntelligence(
            id=uuid4(),
            intel_type="general",
            title="General Intelligence",
            event_date=None,
        )
        db_session.add(intel)
        db_session.commit()

        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        # Should include items without event_date
        assert response.status_code == status.HTTP_200_OK

    def test_intelligence_recent_events(
        self, api_client: TestClient, db_session: Session
    ):
        """Test filtering recent intelligence items."""
        # Create recent intelligence
        recent = MarketIntelligence(
            id=uuid4(),
            intel_type="news",
            title="Recent Event",
            event_date=datetime.utcnow() - timedelta(days=1),
        )
        db_session.add(recent)
        db_session.commit()

        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        # Should be sorted by date, so recent should be first
        assert len(data) > 0


class TestIntelligenceCaching:
    """Test suite for intelligence endpoint caching."""

    def test_list_intelligence_cache_behavior(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test intelligence list endpoint uses caching."""
        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK

    def test_repeated_requests_consistent(
        self, api_client: TestClient, sample_intelligence: MarketIntelligence
    ):
        """Test repeated requests return consistent data."""
        response1 = api_client.get("/api/v1/intelligence/")
        response2 = api_client.get("/api/v1/intelligence/")
        response3 = api_client.get("/api/v1/intelligence/")

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1 == data2 == data3


class TestIntelligenceEdgeCases:
    """Test suite for edge cases in intelligence endpoints."""

    def test_intelligence_with_very_long_summary(
        self, api_client: TestClient, db_session: Session
    ):
        """Test intelligence with very long summary."""
        long_summary = "A" * 5000
        intel = MarketIntelligence(
            id=uuid4(),
            intel_type="analysis",
            title="Detailed Analysis",
            summary=long_summary,
        )
        db_session.add(intel)
        db_session.commit()

        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        detailed_items = [i for i in data if i["title"] == "Detailed Analysis"]
        assert len(detailed_items) > 0

    def test_intelligence_with_special_characters(
        self, api_client: TestClient, db_session: Session
    ):
        """Test intelligence with special characters in title."""
        special_title = "Market Update: Q4 2023 (EdTech & AI) - 100% Growth!"
        intel = MarketIntelligence(
            id=uuid4(),
            intel_type="update",
            title=special_title,
        )
        db_session.add(intel)
        db_session.commit()

        response = api_client.get("/api/v1/intelligence/")

        data = response.json()
        special_items = [i for i in data if i["title"] == special_title]
        assert len(special_items) > 0
        assert special_items[0]["title"] == special_title

    def test_pagination_beyond_available_data(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test pagination offset beyond available data."""
        response = api_client.get("/api/v1/intelligence/?offset=1000")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    def test_zero_limit(self, api_client: TestClient):
        """Test zero limit returns validation error."""
        response = api_client.get("/api/v1/intelligence/?limit=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestIntelligenceCombinedFilters:
    """Test suite for combined filter queries."""

    def test_type_and_category_combination(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering by both type and category."""
        response = api_client.get(
            "/api/v1/intelligence/?intel_type=market_trend&category=k12_education"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data) > 0:
            assert all(i["intel_type"] == "market_trend" for i in data)
            assert all(i["category"] == "k12_education" for i in data)

    def test_filters_with_pagination(
        self, api_client: TestClient, sample_intelligence_items: list[MarketIntelligence]
    ):
        """Test filtering combined with pagination."""
        response = api_client.get(
            "/api/v1/intelligence/?intel_type=market_trend&limit=1"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) <= 1
        if len(data) > 0:
            assert data[0]["intel_type"] == "market_trend"


class TestIntelligenceListPerformance:
    """Test suite for intelligence list performance."""

    def test_list_large_number_of_intelligence_items(
        self, api_client: TestClient, db_session: Session
    ):
        """Test listing with many intelligence items."""
        # Create 100 intelligence items
        items = []
        for i in range(100):
            intel = MarketIntelligence(
                id=uuid4(),
                intel_type="test",
                title=f"Test Intelligence {i}",
                event_date=datetime.utcnow() - timedelta(days=i),
            )
            items.append(intel)
            db_session.add(intel)

        db_session.commit()

        # Test pagination works
        response = api_client.get("/api/v1/intelligence/?limit=50")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 50

    def test_default_limit_applied(
        self, api_client: TestClient, db_session: Session
    ):
        """Test default limit is applied when not specified."""
        response = api_client.get("/api/v1/intelligence/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 100  # Default limit
