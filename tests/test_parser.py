import pytest
from datetime import date, timedelta
from bot.parser import parse_item_message, ParseResult


def test_parse_simple_item_with_absolute_date():
    result = parse_item_message("Panadol expires 15 Jul 2026")
    assert result is not None
    assert result.name == "Panadol"
    assert result.expiry_date == date(2026, 7, 15)
    assert result.category is None


def test_parse_item_with_category_in_parens():
    result = parse_item_message("Panadol (medicine) expires 15 Jul 2026")
    assert result is not None
    assert result.name == "Panadol"
    assert result.category == "medicine"
    assert result.expiry_date == date(2026, 7, 15)


def test_parse_item_with_relative_date():
    result = parse_item_message("milk expires in 3 days")
    assert result is not None
    assert result.name == "milk"
    expected = date.today() + timedelta(days=3)
    assert result.expiry_date == expected


def test_parse_returns_none_when_no_date():
    result = parse_item_message("just some item name")
    assert result is None


def test_parse_item_with_expiry_date_keyword():
    result = parse_item_message("bread expiry date 2026-08-01")
    assert result is not None
    assert result.name == "bread"
    assert result.expiry_date == date(2026, 8, 1)


def test_parse_pantry_item():
    result = parse_item_message("canned beans (pantry) best before 2027-03-15")
    assert result is not None
    assert result.name == "canned beans"
    assert result.category == "pantry"
    assert result.expiry_date == date(2027, 3, 15)
