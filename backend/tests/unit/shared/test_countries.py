import pytest

from app.shared.countries import (
    SUPPORTED_COUNTRIES,
    UnsupportedCountryError,
    currency_for,
    get_country,
    to_usd,
)


def test_known_country_exposes_its_local_currency():
    assert get_country("India").currency == "INR"
    assert currency_for("Germany") == "EUR"


def test_usd_country_converts_one_to_one():
    assert to_usd(120_000, "United States") == 120_000


def test_local_salary_is_converted_to_usd_using_static_rate():
    india = get_country("India")
    assert to_usd(1_000_000, "India") == round(1_000_000 * india.usd_rate)


def test_unknown_country_is_rejected_with_a_clear_error():
    with pytest.raises(UnsupportedCountryError, match="Atlantis"):
        get_country("Atlantis")


def test_supported_countries_are_sorted_and_unique():
    names = [c.name for c in SUPPORTED_COUNTRIES]
    assert names == sorted(names)
    assert len(names) == len(set(names))
