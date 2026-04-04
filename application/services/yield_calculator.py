"""Yield calculations with Decimal precision."""

from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal, getcontext

from domain.entities.bond import Bond, YieldMetrics

getcontext().prec = 28


class YieldCalculator:
    """Calculator for annualized and horizon yields."""

    @staticmethod
    def _days_to_redemption(today: date, target_date: date | None) -> int:
        if target_date is None:
            return 365
        return max((target_date - today).days, 1)

    @staticmethod
    def _months_between(today: date, target_date: date | None) -> Decimal:
        days = YieldCalculator._days_to_redemption(today, target_date)
        return (Decimal(days) / Decimal("30")).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def _market_price_amount(bond: Bond) -> Decimal:
        # MOEX often returns bond price in % of nominal (e.g. 96.42).
        if bond.price <= Decimal("200") and bond.nominal > 0:
            return (bond.nominal * bond.price / Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        return bond.price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def calculate(
        self, bond: Bond, horizon_days: int | None, today: date | None = None
    ) -> YieldMetrics:
        """Calculate horizon and annual yield by capital gain plus coupon cashflow."""
        effective_today = today or date.today()
        redemption_date = bond.offer_date or bond.maturity_date
        days_to_redemption = self._days_to_redemption(effective_today, redemption_date)
        months_to_redemption = self._months_between(effective_today, redemption_date)
        effective_period_days = (
            days_to_redemption
            if horizon_days is None or horizon_days <= 0
            else max(min(horizon_days, days_to_redemption), 1)
        )
        market_price_amount = self._market_price_amount(bond)

        if market_price_amount <= 0:
            return YieldMetrics(
                annual_yield_percent=Decimal("0"),
                horizon_yield_percent=Decimal("0"),
                months_to_redemption=months_to_redemption,
            )

        coupons_in_period = int(
            (
                Decimal(effective_period_days)
                * Decimal(bond.coupons_per_year)
                / Decimal("365")
            ).to_integral_value(rounding=ROUND_DOWN)
        )
        coupon_income = bond.coupon_value * Decimal(coupons_in_period)
        capital_gain = (
            bond.nominal - market_price_amount
            if effective_period_days >= days_to_redemption
            else Decimal("0")
        )
        horizon_yield = ((capital_gain + coupon_income) / market_price_amount) * Decimal(
            "100"
        )

        annualization_factor = Decimal("365") / Decimal(effective_period_days)
        annual_yield = horizon_yield * annualization_factor

        return YieldMetrics(
            annual_yield_percent=annual_yield.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            horizon_yield_percent=horizon_yield.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            months_to_redemption=months_to_redemption,
        )
