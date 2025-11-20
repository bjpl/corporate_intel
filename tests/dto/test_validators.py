"""Tests for DTO validation logic."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from pydantic import ValidationError, BaseModel, field_validator

from src.dto.base import BaseDTO


class TestTickerValidation:
    """Test ticker symbol validation."""

    def test_valid_ticker_formats(self):
        """Test valid ticker formats."""

        class TickerDTO(BaseDTO):
            ticker: str

            @field_validator('ticker')
            @classmethod
            def validate_ticker(cls, v):
                """Validate ticker format."""
                if not v or not isinstance(v, str):
                    raise ValueError("Ticker must be a non-empty string")
                v = v.upper().strip()
                if not v.isalpha():
                    raise ValueError("Ticker must contain only letters")
                if len(v) < 1 or len(v) > 5:
                    raise ValueError("Ticker must be 1-5 characters")
                return v

        # Valid tickers
        valid_tickers = ["AAPL", "MSFT", "GOOGL", "A", "DUOL"]
        for ticker in valid_tickers:
            dto = TickerDTO(ticker=ticker)
            assert dto.ticker == ticker.upper()

    def test_invalid_ticker_formats(self):
        """Test invalid ticker formats."""

        class TickerDTO(BaseDTO):
            ticker: str

            @field_validator('ticker')
            @classmethod
            def validate_ticker(cls, v):
                if not v or not isinstance(v, str):
                    raise ValueError("Ticker must be a non-empty string")
                v = v.upper().strip()
                if not v.isalpha():
                    raise ValueError("Ticker must contain only letters")
                if len(v) < 1 or len(v) > 5:
                    raise ValueError("Ticker must be 1-5 characters")
                return v

        # Invalid tickers
        invalid_tickers = [
            "",           # Empty
            "TOOLONG",    # Too long
            "123",        # Numbers
            "AA-PL",      # Hyphen
            "AA.PL",      # Dot
            "  ",         # Whitespace
        ]

        for ticker in invalid_tickers:
            with pytest.raises(ValidationError):
                TickerDTO(ticker=ticker)

    def test_ticker_case_normalization(self):
        """Test ticker uppercase normalization."""

        class TickerDTO(BaseDTO):
            ticker: str

            @field_validator('ticker')
            @classmethod
            def validate_ticker(cls, v):
                return v.upper().strip()

        # Lowercase should be converted to uppercase
        dto = TickerDTO(ticker="aapl")
        assert dto.ticker == "AAPL"

        # Mixed case
        dto = TickerDTO(ticker="MsFt")
        assert dto.ticker == "MSFT"


class TestUUIDValidation:
    """Test UUID validation."""

    def test_valid_uuid_formats(self):
        """Test valid UUID formats."""

        class UUIDTestDTO(BaseDTO):
            id: UUID

        # UUID object
        test_id = uuid4()
        dto = UUIDTestDTO(id=test_id)
        assert dto.id == test_id

        # UUID string
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        dto = UUIDTestDTO(id=uuid_str)
        assert str(dto.id) == uuid_str

    def test_invalid_uuid_formats(self):
        """Test invalid UUID formats."""

        class UUIDTestDTO(BaseDTO):
            id: UUID

        invalid_uuids = [
            "not-a-uuid",
            "123",
            "",
            "550e8400-e29b-41d4-a716",  # Incomplete
        ]

        for invalid in invalid_uuids:
            with pytest.raises(ValidationError):
                UUIDTestDTO(id=invalid)


class TestDateRangeValidation:
    """Test date range validation."""

    def test_valid_date_range(self):
        """Test valid date ranges."""

        class DateRangeDTO(BaseDTO):
            start_date: datetime
            end_date: datetime

            @field_validator('end_date')
            @classmethod
            def validate_date_range(cls, v, info):
                if 'start_date' in info.data and v < info.data['start_date']:
                    raise ValueError("end_date must be after start_date")
                return v

        start = datetime(2025, 1, 1)
        end = datetime(2025, 12, 31)

        dto = DateRangeDTO(start_date=start, end_date=end)
        assert dto.start_date == start
        assert dto.end_date == end

    def test_invalid_date_range(self):
        """Test invalid date ranges (end before start)."""

        class DateRangeDTO(BaseDTO):
            start_date: datetime
            end_date: datetime

            @field_validator('end_date')
            @classmethod
            def validate_date_range(cls, v, info):
                if 'start_date' in info.data and v < info.data['start_date']:
                    raise ValueError("end_date must be after start_date")
                return v

        start = datetime(2025, 12, 31)
        end = datetime(2025, 1, 1)

        with pytest.raises(ValidationError) as exc_info:
            DateRangeDTO(start_date=start, end_date=end)

        assert "end_date must be after start_date" in str(exc_info.value)

    def test_same_date_range(self):
        """Test date range with same start and end."""

        class DateRangeDTO(BaseDTO):
            start_date: datetime
            end_date: datetime

            @field_validator('end_date')
            @classmethod
            def validate_date_range(cls, v, info):
                if 'start_date' in info.data and v < info.data['start_date']:
                    raise ValueError("end_date must be after start_date")
                return v

        same_date = datetime(2025, 6, 15)

        # Same date should be valid (start <= end)
        dto = DateRangeDTO(start_date=same_date, end_date=same_date)
        assert dto.start_date == dto.end_date


class TestNumericValidation:
    """Test numeric field validation."""

    def test_positive_number_validation(self):
        """Test positive number validation."""

        class PositiveDTO(BaseDTO):
            count: int
            price: float

            @field_validator('count', 'price')
            @classmethod
            def validate_positive(cls, v):
                if v <= 0:
                    raise ValueError("Value must be positive")
                return v

        # Valid positive numbers
        dto = PositiveDTO(count=10, price=99.99)
        assert dto.count == 10
        assert dto.price == 99.99

        # Invalid: zero
        with pytest.raises(ValidationError):
            PositiveDTO(count=0, price=99.99)

        # Invalid: negative
        with pytest.raises(ValidationError):
            PositiveDTO(count=10, price=-1.0)

    def test_range_validation(self):
        """Test numeric range validation."""

        from pydantic import Field

        class RangeDTO(BaseDTO):
            percentage: float = Field(ge=0.0, le=100.0)
            priority: int = Field(ge=1, le=10)

        # Valid ranges
        dto = RangeDTO(percentage=50.0, priority=5)
        assert dto.percentage == 50.0
        assert dto.priority == 5

        # Boundary values
        dto = RangeDTO(percentage=0.0, priority=1)
        assert dto.percentage == 0.0

        dto = RangeDTO(percentage=100.0, priority=10)
        assert dto.percentage == 100.0

        # Out of range
        with pytest.raises(ValidationError):
            RangeDTO(percentage=101.0, priority=5)

        with pytest.raises(ValidationError):
            RangeDTO(percentage=50.0, priority=11)


class TestStringValidation:
    """Test string field validation."""

    def test_string_length_validation(self):
        """Test string length constraints."""

        from pydantic import Field

        class StringLengthDTO(BaseDTO):
            short: str = Field(min_length=1, max_length=10)
            medium: str = Field(min_length=5, max_length=50)

        # Valid lengths
        dto = StringLengthDTO(short="test", medium="medium text")
        assert dto.short == "test"

        # Too short
        with pytest.raises(ValidationError):
            StringLengthDTO(short="", medium="valid text")

        # Too long
        with pytest.raises(ValidationError):
            StringLengthDTO(short="way too long", medium="valid")

    def test_string_pattern_validation(self):
        """Test string pattern validation."""

        from pydantic import Field

        class PatternDTO(BaseDTO):
            email: str = Field(pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
            phone: str = Field(pattern=r"^\d{3}-\d{3}-\d{4}$")

        # Valid patterns
        dto = PatternDTO(
            email="test@example.com",
            phone="555-123-4567"
        )
        assert dto.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            PatternDTO(email="invalid-email", phone="555-123-4567")

        # Invalid phone
        with pytest.raises(ValidationError):
            PatternDTO(email="test@example.com", phone="1234567890")


class TestListValidation:
    """Test list field validation."""

    def test_list_length_validation(self):
        """Test list length constraints."""

        from pydantic import Field

        class ListDTO(BaseDTO):
            tags: list[str] = Field(min_length=1, max_length=5)

        # Valid list
        dto = ListDTO(tags=["tag1", "tag2"])
        assert len(dto.tags) == 2

        # Empty list (invalid)
        with pytest.raises(ValidationError):
            ListDTO(tags=[])

        # Too many items
        with pytest.raises(ValidationError):
            ListDTO(tags=["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"])

    def test_list_item_validation(self):
        """Test validation of list items."""

        class ItemDTO(BaseDTO):
            value: int

            @field_validator('value')
            @classmethod
            def validate_value(cls, v):
                if v < 0:
                    raise ValueError("Value must be non-negative")
                return v

        class ListDTO(BaseDTO):
            items: list[ItemDTO]

        # Valid items
        dto = ListDTO(items=[
            {"value": 1},
            {"value": 2},
            {"value": 3}
        ])
        assert len(dto.items) == 3

        # Invalid item in list
        with pytest.raises(ValidationError):
            ListDTO(items=[
                {"value": 1},
                {"value": -1},  # Invalid
                {"value": 3}
            ])


class TestConditionalValidation:
    """Test conditional validation logic."""

    def test_dependent_field_validation(self):
        """Test validation that depends on other fields."""

        class ConditionalDTO(BaseDTO):
            has_discount: bool
            discount_percentage: float = 0.0

            @field_validator('discount_percentage')
            @classmethod
            def validate_discount(cls, v, info):
                if info.data.get('has_discount') and v <= 0:
                    raise ValueError("Discount percentage must be positive when has_discount is True")
                if not info.data.get('has_discount') and v != 0:
                    raise ValueError("Discount percentage must be 0 when has_discount is False")
                return v

        # Valid: discount enabled with percentage
        dto = ConditionalDTO(has_discount=True, discount_percentage=10.0)
        assert dto.discount_percentage == 10.0

        # Valid: discount disabled with zero
        dto = ConditionalDTO(has_discount=False, discount_percentage=0.0)
        assert dto.discount_percentage == 0.0

        # Invalid: discount enabled but zero percentage
        with pytest.raises(ValidationError):
            ConditionalDTO(has_discount=True, discount_percentage=0.0)

    def test_mutually_exclusive_fields(self):
        """Test mutually exclusive field validation."""

        class ExclusiveDTO(BaseDTO):
            option_a: str = None
            option_b: str = None

            @field_validator('option_b')
            @classmethod
            def validate_exclusive(cls, v, info):
                if v and info.data.get('option_a'):
                    raise ValueError("option_a and option_b are mutually exclusive")
                if not v and not info.data.get('option_a'):
                    raise ValueError("Either option_a or option_b must be provided")
                return v

        # Valid: only option_a
        dto = ExclusiveDTO(option_a="value_a")
        assert dto.option_a == "value_a"
        assert dto.option_b is None

        # Valid: only option_b
        dto = ExclusiveDTO(option_b="value_b")
        assert dto.option_b == "value_b"


class TestCustomValidators:
    """Test custom validation functions."""

    def test_custom_email_validator(self):
        """Test custom email validation."""

        def validate_email(email: str) -> str:
            """Custom email validator."""
            email = email.lower().strip()
            if '@' not in email:
                raise ValueError("Invalid email format")
            local, domain = email.split('@', 1)
            if not local or not domain:
                raise ValueError("Invalid email format")
            return email

        class EmailDTO(BaseDTO):
            email: str

            @field_validator('email')
            @classmethod
            def check_email(cls, v):
                return validate_email(v)

        # Valid email
        dto = EmailDTO(email="Test@Example.com")
        assert dto.email == "test@example.com"

        # Invalid email
        with pytest.raises(ValidationError):
            EmailDTO(email="invalid")

    def test_custom_phone_validator(self):
        """Test custom phone number validation."""

        def validate_phone(phone: str) -> str:
            """Custom phone validator."""
            # Remove common separators
            cleaned = phone.replace('-', '').replace(' ', '').replace('(', '').replace(')', '')
            if not cleaned.isdigit():
                raise ValueError("Phone must contain only digits and separators")
            if len(cleaned) != 10:
                raise ValueError("Phone must be 10 digits")
            # Format as XXX-XXX-XXXX
            return f"{cleaned[:3]}-{cleaned[3:6]}-{cleaned[6:]}"

        class PhoneDTO(BaseDTO):
            phone: str

            @field_validator('phone')
            @classmethod
            def check_phone(cls, v):
                return validate_phone(v)

        # Various valid formats
        formats = [
            "5551234567",
            "555-123-4567",
            "(555) 123-4567",
            "555 123 4567"
        ]

        for fmt in formats:
            dto = PhoneDTO(phone=fmt)
            assert dto.phone == "555-123-4567"

        # Invalid phone
        with pytest.raises(ValidationError):
            PhoneDTO(phone="123")  # Too short


class TestValidationPerformance:
    """Test validation performance with large datasets."""

    def test_bulk_validation(self):
        """Test validation of many items."""

        class ItemDTO(BaseDTO):
            id: int
            value: str

            @field_validator('value')
            @classmethod
            def validate_value(cls, v):
                if len(v) < 1:
                    raise ValueError("Value must not be empty")
                return v

        # Validate 1000 items
        items = [
            ItemDTO(id=i, value=f"value_{i}")
            for i in range(1000)
        ]

        assert len(items) == 1000
        assert items[0].id == 0
        assert items[999].value == "value_999"

    def test_nested_validation_performance(self):
        """Test nested validation performance."""

        class InnerDTO(BaseDTO):
            value: int

        class MiddleDTO(BaseDTO):
            inners: list[InnerDTO]

        class OuterDTO(BaseDTO):
            middles: list[MiddleDTO]

        # Create deeply nested structure
        data = {
            "middles": [
                {
                    "inners": [
                        {"value": j}
                        for j in range(10)
                    ]
                }
                for i in range(10)
            ]
        }

        dto = OuterDTO(**data)
        assert len(dto.middles) == 10
        assert len(dto.middles[0].inners) == 10
