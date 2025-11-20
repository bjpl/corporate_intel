"""Validation utilities and mixins for DTOs.

This module provides reusable validation logic, custom validators,
and validation mixins for common field types and business rules.
"""

import re
from datetime import date, datetime, timedelta
from typing import Any, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, field_validator, Field


class ValidationMixin(BaseModel):
    """Mixin providing common validation methods.

    Can be inherited by DTOs to add standard validation utilities.
    """

    @classmethod
    def validate_non_empty_string(cls, value: str, field_name: str) -> str:
        """Validate string is not empty or whitespace only.

        Args:
            value: String value to validate
            field_name: Field name for error messages

        Returns:
            Validated string

        Raises:
            ValueError: If string is empty or whitespace
        """
        if not value or not value.strip():
            raise ValueError(f"{field_name} cannot be empty or whitespace")
        return value.strip()

    @classmethod
    def validate_positive_number(
        cls,
        value: Union[int, float],
        field_name: str,
        allow_zero: bool = False,
    ) -> Union[int, float]:
        """Validate number is positive.

        Args:
            value: Numeric value to validate
            field_name: Field name for error messages
            allow_zero: Whether zero is allowed

        Returns:
            Validated number

        Raises:
            ValueError: If number is not positive
        """
        if allow_zero:
            if value < 0:
                raise ValueError(f"{field_name} must be non-negative")
        else:
            if value <= 0:
                raise ValueError(f"{field_name} must be positive")
        return value

    @classmethod
    def validate_range(
        cls,
        value: Union[int, float],
        field_name: str,
        min_value: Optional[Union[int, float]] = None,
        max_value: Optional[Union[int, float]] = None,
    ) -> Union[int, float]:
        """Validate number is within range.

        Args:
            value: Numeric value to validate
            field_name: Field name for error messages
            min_value: Minimum allowed value (inclusive)
            max_value: Maximum allowed value (inclusive)

        Returns:
            Validated number

        Raises:
            ValueError: If value is out of range
        """
        if min_value is not None and value < min_value:
            raise ValueError(f"{field_name} must be >= {min_value}")
        if max_value is not None and value > max_value:
            raise ValueError(f"{field_name} must be <= {max_value}")
        return value


# Stock ticker validation

TICKER_PATTERN = re.compile(r"^[A-Z]{1,5}$")

def validate_ticker(ticker: str) -> str:
    """Validate stock ticker symbol.

    Args:
        ticker: Ticker symbol to validate

    Returns:
        Uppercase ticker symbol

    Raises:
        ValueError: If ticker format is invalid

    Example:
        validate_ticker("aapl")  # Returns "AAPL"
        validate_ticker("123")   # Raises ValueError
    """
    if not ticker:
        raise ValueError("Ticker symbol cannot be empty")

    ticker = ticker.upper().strip()

    if not TICKER_PATTERN.match(ticker):
        raise ValueError(
            f"Invalid ticker symbol '{ticker}'. "
            "Must be 1-5 uppercase letters (A-Z)"
        )

    return ticker


# CIK validation

def validate_cik(cik: str) -> str:
    """Validate SEC CIK number.

    Args:
        cik: CIK number to validate

    Returns:
        Padded 10-digit CIK

    Raises:
        ValueError: If CIK format is invalid

    Example:
        validate_cik("789019")    # Returns "0000789019"
        validate_cik("invalid")   # Raises ValueError
    """
    if not cik:
        raise ValueError("CIK cannot be empty")

    # Remove any whitespace
    cik = cik.strip()

    # Must be numeric
    if not cik.isdigit():
        raise ValueError(f"Invalid CIK '{cik}'. Must contain only digits")

    # Must be 1-10 digits
    if len(cik) > 10:
        raise ValueError(f"Invalid CIK '{cik}'. Maximum 10 digits")

    # Pad to 10 digits
    return cik.zfill(10)


# UUID validation

def validate_uuid(value: Union[str, UUID], field_name: str = "UUID") -> UUID:
    """Validate and convert to UUID.

    Args:
        value: String or UUID value
        field_name: Field name for error messages

    Returns:
        UUID instance

    Raises:
        ValueError: If value is not a valid UUID
    """
    if isinstance(value, UUID):
        return value

    try:
        return UUID(str(value))
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid {field_name}: {value}") from e


# Date/time validation

def validate_date_range(
    start_date: Union[date, datetime],
    end_date: Union[date, datetime],
    max_days: Optional[int] = None,
) -> tuple[Union[date, datetime], Union[date, datetime]]:
    """Validate date range.

    Args:
        start_date: Start date/datetime
        end_date: End date/datetime
        max_days: Maximum allowed days in range

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If date range is invalid
    """
    if start_date > end_date:
        raise ValueError("start_date must be before or equal to end_date")

    if max_days is not None:
        delta = end_date - start_date
        days = delta.days if isinstance(delta, timedelta) else (end_date - start_date).days

        if days > max_days:
            raise ValueError(
                f"Date range exceeds maximum of {max_days} days. "
                f"Provided range is {days} days"
            )

    return start_date, end_date


def validate_future_date(
    value: Union[date, datetime],
    field_name: str = "Date",
    allow_today: bool = True,
) -> Union[date, datetime]:
    """Validate date is not in the past.

    Args:
        value: Date/datetime to validate
        field_name: Field name for error messages
        allow_today: Whether today's date is allowed

    Returns:
        Validated date/datetime

    Raises:
        ValueError: If date is in the past
    """
    today = datetime.now().date() if isinstance(value, date) else datetime.now()

    if allow_today:
        if value < today:
            raise ValueError(f"{field_name} cannot be in the past")
    else:
        if value <= today:
            raise ValueError(f"{field_name} must be in the future")

    return value


# Email validation

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)

def validate_email(email: str) -> str:
    """Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        Lowercase email address

    Raises:
        ValueError: If email format is invalid
    """
    if not email:
        raise ValueError("Email cannot be empty")

    email = email.lower().strip()

    if not EMAIL_PATTERN.match(email):
        raise ValueError(f"Invalid email format: {email}")

    return email


# URL validation

URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE
)

def validate_url(url: str, require_https: bool = False) -> str:
    """Validate URL format.

    Args:
        url: URL to validate
        require_https: Whether HTTPS is required

    Returns:
        Validated URL

    Raises:
        ValueError: If URL format is invalid
    """
    if not url:
        raise ValueError("URL cannot be empty")

    url = url.strip()

    if not URL_PATTERN.match(url):
        raise ValueError(f"Invalid URL format: {url}")

    if require_https and not url.startswith("https://"):
        raise ValueError(f"URL must use HTTPS: {url}")

    return url


# List validation

def validate_unique_list(
    values: List[Any],
    field_name: str = "List",
) -> List[Any]:
    """Validate list contains unique values.

    Args:
        values: List to validate
        field_name: Field name for error messages

    Returns:
        Validated list

    Raises:
        ValueError: If list contains duplicates
    """
    if not values:
        return values

    seen = set()
    duplicates = set()

    for value in values:
        # Convert unhashable types to strings
        hashable_value = value if isinstance(value, (str, int, float, bool, tuple)) else str(value)

        if hashable_value in seen:
            duplicates.add(hashable_value)
        seen.add(hashable_value)

    if duplicates:
        raise ValueError(f"{field_name} contains duplicate values: {duplicates}")

    return values


def validate_list_length(
    values: List[Any],
    field_name: str = "List",
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
) -> List[Any]:
    """Validate list length.

    Args:
        values: List to validate
        field_name: Field name for error messages
        min_length: Minimum list length
        max_length: Maximum list length

    Returns:
        Validated list

    Raises:
        ValueError: If list length is invalid
    """
    if values is None:
        values = []

    length = len(values)

    if min_length is not None and length < min_length:
        raise ValueError(f"{field_name} must have at least {min_length} items")

    if max_length is not None and length > max_length:
        raise ValueError(f"{field_name} cannot have more than {max_length} items")

    return values


# EdTech-specific validators

EDTECH_CATEGORIES = {
    "k12",
    "higher_education",
    "corporate_learning",
    "direct_to_consumer",
    "enabling_technology",
}

DELIVERY_MODELS = {
    "b2b",
    "b2c",
    "b2b2c",
    "marketplace",
    "hybrid",
}

def validate_edtech_category(category: str) -> str:
    """Validate EdTech category.

    Args:
        category: Category to validate

    Returns:
        Validated category

    Raises:
        ValueError: If category is invalid
    """
    if not category:
        raise ValueError("EdTech category cannot be empty")

    category = category.lower().strip()

    if category not in EDTECH_CATEGORIES:
        raise ValueError(
            f"Invalid EdTech category '{category}'. "
            f"Must be one of: {', '.join(sorted(EDTECH_CATEGORIES))}"
        )

    return category


def validate_delivery_model(model: str) -> str:
    """Validate delivery model.

    Args:
        model: Delivery model to validate

    Returns:
        Validated model

    Raises:
        ValueError: If model is invalid
    """
    if not model:
        raise ValueError("Delivery model cannot be empty")

    model = model.lower().strip()

    if model not in DELIVERY_MODELS:
        raise ValueError(
            f"Invalid delivery model '{model}'. "
            f"Must be one of: {', '.join(sorted(DELIVERY_MODELS))}"
        )

    return model
