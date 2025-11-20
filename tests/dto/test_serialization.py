"""Tests for DTO serialization and deserialization."""

import pytest
import json
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID, uuid4
from enum import Enum
from typing import Optional, List, Dict

from src.dto.base import BaseDTO, TimestampedDTO, IDMixin


class TestBasicSerialization:
    """Test basic DTO serialization."""

    def test_simple_dto_to_dict(self):
        """Test simple DTO serialization to dict."""

        class SimpleDTO(BaseDTO):
            name: str
            count: int

        dto = SimpleDTO(name="test", count=42)
        data = dto.model_dump()

        assert data == {"name": "test", "count": 42}
        assert isinstance(data, dict)

    def test_simple_dto_to_json(self):
        """Test simple DTO serialization to JSON."""

        class SimpleDTO(BaseDTO):
            name: str
            count: int

        dto = SimpleDTO(name="test", count=42)
        json_str = dto.model_dump_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed == {"name": "test", "count": 42}

    def test_dto_from_dict(self):
        """Test DTO deserialization from dict."""

        class SimpleDTO(BaseDTO):
            name: str
            count: int

        data = {"name": "test", "count": 42}
        dto = SimpleDTO(**data)

        assert dto.name == "test"
        assert dto.count == 42

    def test_dto_from_json(self):
        """Test DTO deserialization from JSON."""

        class SimpleDTO(BaseDTO):
            name: str
            count: int

        json_str = '{"name": "test", "count": 42}'
        dto = SimpleDTO.model_validate_json(json_str)

        assert dto.name == "test"
        assert dto.count == 42


class TestComplexTypeSerialization:
    """Test serialization of complex types."""

    def test_datetime_serialization(self):
        """Test datetime field serialization."""

        class DateTimeDTO(BaseDTO):
            timestamp: datetime
            date: date
            time: time

        now = datetime(2025, 11, 20, 12, 30, 45)
        dto = DateTimeDTO(
            timestamp=now,
            date=now.date(),
            time=now.time()
        )

        json_str = dto.model_dump_json()
        parsed = json.loads(json_str)

        assert "2025-11-20" in parsed["timestamp"]
        assert parsed["date"] == "2025-11-20"
        assert "12:30:45" in parsed["time"]

    def test_datetime_deserialization(self):
        """Test datetime field deserialization."""

        class DateTimeDTO(BaseDTO):
            timestamp: datetime

        json_str = '{"timestamp": "2025-11-20T12:30:45"}'
        dto = DateTimeDTO.model_validate_json(json_str)

        assert isinstance(dto.timestamp, datetime)
        assert dto.timestamp.year == 2025
        assert dto.timestamp.month == 11
        assert dto.timestamp.day == 20

    def test_uuid_serialization(self):
        """Test UUID field serialization."""

        class UUIDDTO(IDMixin):
            name: str

        test_id = uuid4()
        dto = UUIDDTO(id=test_id, name="test")

        json_str = dto.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["id"] == str(test_id)

    def test_uuid_deserialization(self):
        """Test UUID field deserialization."""

        class UUIDDTO(IDMixin):
            name: str

        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        json_str = f'{{"id": "{uuid_str}", "name": "test"}}'
        dto = UUIDDTO.model_validate_json(json_str)

        assert isinstance(dto.id, UUID)
        assert str(dto.id) == uuid_str

    def test_decimal_serialization(self):
        """Test Decimal field serialization."""

        class DecimalDTO(BaseDTO):
            price: Decimal

        dto = DecimalDTO(price=Decimal("99.99"))
        json_str = dto.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["price"] == "99.99"

    def test_enum_serialization(self):
        """Test Enum field serialization."""

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class EnumDTO(BaseDTO):
            status: Status

        dto = EnumDTO(status=Status.ACTIVE)
        data = dto.model_dump()

        assert data["status"] == "active"

    def test_enum_deserialization(self):
        """Test Enum field deserialization."""

        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        class EnumDTO(BaseDTO):
            status: Status

        json_str = '{"status": "active"}'
        dto = EnumDTO.model_validate_json(json_str)

        assert dto.status == Status.ACTIVE


class TestNestedSerialization:
    """Test serialization of nested DTOs."""

    def test_nested_dto_serialization(self):
        """Test nested DTO serialization."""

        class InnerDTO(BaseDTO):
            value: int

        class OuterDTO(BaseDTO):
            name: str
            inner: InnerDTO

        dto = OuterDTO(
            name="test",
            inner=InnerDTO(value=42)
        )

        data = dto.model_dump()
        assert data == {
            "name": "test",
            "inner": {"value": 42}
        }

    def test_nested_dto_deserialization(self):
        """Test nested DTO deserialization."""

        class InnerDTO(BaseDTO):
            value: int

        class OuterDTO(BaseDTO):
            name: str
            inner: InnerDTO

        data = {
            "name": "test",
            "inner": {"value": 42}
        }

        dto = OuterDTO(**data)
        assert dto.name == "test"
        assert isinstance(dto.inner, InnerDTO)
        assert dto.inner.value == 42

    def test_list_of_dtos_serialization(self):
        """Test list of DTOs serialization."""

        class ItemDTO(BaseDTO):
            id: int
            name: str

        class ListDTO(BaseDTO):
            items: List[ItemDTO]

        dto = ListDTO(items=[
            ItemDTO(id=1, name="first"),
            ItemDTO(id=2, name="second")
        ])

        data = dto.model_dump()
        assert len(data["items"]) == 2
        assert data["items"][0] == {"id": 1, "name": "first"}

    def test_dict_of_dtos_serialization(self):
        """Test dict of DTOs serialization."""

        class ValueDTO(BaseDTO):
            amount: int

        class DictDTO(BaseDTO):
            values: Dict[str, ValueDTO]

        dto = DictDTO(values={
            "key1": ValueDTO(amount=10),
            "key2": ValueDTO(amount=20)
        })

        data = dto.model_dump()
        assert data["values"]["key1"] == {"amount": 10}
        assert data["values"]["key2"] == {"amount": 20}


class TestOptionalFieldSerialization:
    """Test serialization of optional fields."""

    def test_optional_field_with_value(self):
        """Test optional field with value."""

        class OptionalDTO(BaseDTO):
            required: str
            optional: Optional[str] = None

        dto = OptionalDTO(required="test", optional="value")
        data = dto.model_dump()

        assert data == {"required": "test", "optional": "value"}

    def test_optional_field_without_value(self):
        """Test optional field without value."""

        class OptionalDTO(BaseDTO):
            required: str
            optional: Optional[str] = None

        dto = OptionalDTO(required="test")
        data = dto.model_dump()

        assert data == {"required": "test", "optional": None}

    def test_exclude_none_serialization(self):
        """Test excluding None values from serialization."""

        class OptionalDTO(BaseDTO):
            required: str
            optional: Optional[str] = None

        dto = OptionalDTO(required="test")
        data = dto.model_dump(exclude_none=True)

        assert data == {"required": "test"}
        assert "optional" not in data


class TestSerializationModes:
    """Test different serialization modes."""

    def test_exclude_fields(self):
        """Test excluding specific fields."""

        class FullDTO(BaseDTO):
            public: str
            private: str
            internal: str

        dto = FullDTO(public="pub", private="priv", internal="int")
        data = dto.model_dump(exclude={"private", "internal"})

        assert data == {"public": "pub"}

    def test_include_fields(self):
        """Test including only specific fields."""

        class FullDTO(BaseDTO):
            field1: str
            field2: str
            field3: str

        dto = FullDTO(field1="v1", field2="v2", field3="v3")
        data = dto.model_dump(include={"field1", "field3"})

        assert data == {"field1": "v1", "field3": "v3"}

    def test_by_alias_serialization(self):
        """Test serialization using field aliases."""

        from pydantic import Field

        class AliasDTO(BaseDTO):
            internal_name: str = Field(alias="externalName")

        dto = AliasDTO(externalName="test")

        # Default: uses field name
        data = dto.model_dump()
        assert "internal_name" in data

        # By alias: uses alias
        data = dto.model_dump(by_alias=True)
        assert "externalName" in data


class TestORMSerialization:
    """Test ORM object serialization."""

    def test_from_orm_object(self):
        """Test creating DTO from ORM object."""

        class MockORM:
            def __init__(self):
                self.id = 1
                self.name = "test"
                self.created_at = datetime(2025, 1, 1)

        class ORMDTO(BaseDTO):
            id: int
            name: str
            created_at: datetime

        orm_obj = MockORM()
        dto = ORMDTO.model_validate(orm_obj)

        assert dto.id == 1
        assert dto.name == "test"
        assert dto.created_at == datetime(2025, 1, 1)

    def test_from_orm_with_relationships(self):
        """Test creating DTO from ORM with relationships."""

        class MockRelated:
            def __init__(self):
                self.value = 42

        class MockORM:
            def __init__(self):
                self.id = 1
                self.related = MockRelated()

        class RelatedDTO(BaseDTO):
            value: int

        class ORMDTO(BaseDTO):
            id: int
            related: RelatedDTO

        orm_obj = MockORM()
        dto = ORMDTO.model_validate(orm_obj)

        assert dto.id == 1
        assert dto.related.value == 42


class TestSerializationEdgeCases:
    """Test edge cases in serialization."""

    def test_empty_list_serialization(self):
        """Test empty list serialization."""

        class ListDTO(BaseDTO):
            items: List[str]

        dto = ListDTO(items=[])
        data = dto.model_dump()

        assert data == {"items": []}

    def test_empty_dict_serialization(self):
        """Test empty dict serialization."""

        class DictDTO(BaseDTO):
            data: Dict[str, int]

        dto = DictDTO(data={})
        data_dict = dto.model_dump()

        assert data_dict == {"data": {}}

    def test_deeply_nested_serialization(self):
        """Test deeply nested structure serialization."""

        class Level3(BaseDTO):
            value: int

        class Level2(BaseDTO):
            level3: Level3

        class Level1(BaseDTO):
            level2: Level2

        dto = Level1(
            level2=Level2(
                level3=Level3(value=42)
            )
        )

        data = dto.model_dump()
        assert data["level2"]["level3"]["value"] == 42

    def test_circular_reference_prevention(self):
        """Test that circular references are handled."""
        # Pydantic prevents circular references at definition time
        # This test validates the error handling

        with pytest.raises((ValueError, RecursionError)):
            class SelfRef(BaseDTO):
                name: str
                children: Optional[List['SelfRef']] = None


class TestSerializationPerformance:
    """Test serialization performance."""

    def test_large_list_serialization(self):
        """Test serialization of large lists."""

        class ItemDTO(BaseDTO):
            id: int
            value: str

        items = [ItemDTO(id=i, value=f"item_{i}") for i in range(1000)]

        class LargeListDTO(BaseDTO):
            items: List[ItemDTO]

        dto = LargeListDTO(items=items)
        data = dto.model_dump()

        assert len(data["items"]) == 1000
        assert data["items"][0]["id"] == 0

    def test_large_dict_serialization(self):
        """Test serialization of large dicts."""

        class ValueDTO(BaseDTO):
            amount: int

        values = {f"key_{i}": ValueDTO(amount=i) for i in range(1000)}

        class LargeDictDTO(BaseDTO):
            values: Dict[str, ValueDTO]

        dto = LargeDictDTO(values=values)
        data = dto.model_dump()

        assert len(data["values"]) == 1000
        assert data["values"]["key_0"]["amount"] == 0
