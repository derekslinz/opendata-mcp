"""Tests for shared Pydantic parameter type aliases in meta_data_mcp.fields."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, Field, ValidationError

from meta_data_mcp.fields import NonEmptyStr, PageInt, PageSize, Slug


class _NonEmptyStrModel(BaseModel):
    value: NonEmptyStr


class _SlugModel(BaseModel):
    value: Slug


class _PageIntModel(BaseModel):
    value: PageInt


class _PageIntModelWithFieldMetadata(BaseModel):
    value: PageInt = Field(description="Results page.")


class _PageSizeModel(BaseModel):
    value: PageSize


class _PageSizeModelWithFieldMetadata(BaseModel):
    value: PageSize = Field(description="Results page size.")


# ---------------------------------------------------------------------------
# NonEmptyStr
# ---------------------------------------------------------------------------


def test_non_empty_str_accepts_single_char() -> None:
    assert _NonEmptyStrModel(value="x").value == "x"


def test_non_empty_str_rejects_empty() -> None:
    with pytest.raises(ValidationError):
        _NonEmptyStrModel(value="")


# ---------------------------------------------------------------------------
# Slug
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", ["us-gov", "abc123", "a", "us-gov-2"])
def test_slug_accepts_valid(value: str) -> None:
    assert _SlugModel(value=value).value == value


@pytest.mark.parametrize("value", ["US_Gov", "us gov", "", "US-Gov", "us.gov"])
def test_slug_rejects_invalid(value: str) -> None:
    with pytest.raises(ValidationError):
        _SlugModel(value=value)


# ---------------------------------------------------------------------------
# PageInt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [1, 5, 100])
def test_page_int_accepts_positive(value: int) -> None:
    assert _PageIntModel(value=value).value == value


@pytest.mark.parametrize("value", [0, -1, -100])
def test_page_int_rejects_non_positive(value: int) -> None:
    with pytest.raises(ValidationError):
        _PageIntModel(value=value)


def test_page_int_default_is_one() -> None:
    assert _PageIntModel().value == 1


def test_page_int_default_survives_field_merge() -> None:
    assert _PageIntModelWithFieldMetadata().value == 1


# ---------------------------------------------------------------------------
# PageSize
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [1, 100, 1000])
def test_page_size_accepts_in_range(value: int) -> None:
    assert _PageSizeModel(value=value).value == value


@pytest.mark.parametrize("value", [0, 1001, -1, 5000])
def test_page_size_rejects_out_of_range(value: int) -> None:
    with pytest.raises(ValidationError):
        _PageSizeModel(value=value)


def test_page_size_default_is_twenty() -> None:
    assert _PageSizeModel().value == 20


def test_page_size_default_survives_field_merge() -> None:
    assert _PageSizeModelWithFieldMetadata().value == 20
