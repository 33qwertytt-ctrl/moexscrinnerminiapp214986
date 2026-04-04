"""Domain entities used by services and presentation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(slots=True)
class Bond:
    """Bond entity with fields needed for screening and output."""

    secid: str
    shortname: str
    company_name: str
    currency: str
    is_qualified_only: bool
    rating: str
    price: Decimal
    coupon_percent: Decimal
    coupon_value: Decimal
    coupons_per_year: int
    nominal: Decimal
    maturity_date: date | None
    offer_date: date | None
    lot_value: Decimal


@dataclass(slots=True)
class YieldMetrics:
    """Calculated yield metrics for ranking."""

    annual_yield_percent: Decimal
    horizon_yield_percent: Decimal
    months_to_redemption: Decimal
