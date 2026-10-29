"""Supported countries, their currencies and the static FX table used for reporting.

Salaries are stored in the employee's local currency. Any cross-country comparison
converts to USD through this single table so that numbers are never silently mixed.
Rates are deliberately static (see docs/REQUIREMENTS.md) to keep reports reproducible.
"""

from dataclasses import dataclass

FX_RATES_AS_OF = "2026-10-01"


class UnsupportedCountryError(ValueError):
    def __init__(self, country: str) -> None:
        super().__init__(f"Unsupported country: {country!r}")
        self.country = country


@dataclass(frozen=True, slots=True)
class Country:
    name: str
    currency: str
    usd_rate: float  # 1 unit of local currency in USD


SUPPORTED_COUNTRIES: tuple[Country, ...] = (
    Country("Australia", "AUD", 0.66),
    Country("Brazil", "BRL", 0.18),
    Country("Canada", "CAD", 0.73),
    Country("France", "EUR", 1.08),
    Country("Germany", "EUR", 1.08),
    Country("India", "INR", 0.012),
    Country("Japan", "JPY", 0.0067),
    Country("Singapore", "SGD", 0.74),
    Country("United Kingdom", "GBP", 1.27),
    Country("United States", "USD", 1.0),
)

_BY_NAME = {c.name: c for c in SUPPORTED_COUNTRIES}


def get_country(name: str) -> Country:
    try:
        return _BY_NAME[name]
    except KeyError:
        raise UnsupportedCountryError(name) from None


def currency_for(country: str) -> str:
    return get_country(country).currency


def to_usd(amount: float, country: str) -> int:
    return round(amount * get_country(country).usd_rate)
