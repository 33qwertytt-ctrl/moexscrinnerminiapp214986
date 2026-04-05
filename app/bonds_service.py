"""Application-level bond service for CLI and Web API reuse."""

import asyncio
import re
from decimal import Decimal

from pydantic import BaseModel

from application.services.bond_service import BondService
from application.services.yield_calculator import YieldCalculator
from config.settings import settings
from domain.entities.bond import Bond as DomainBond
from infrastructure.moex.client import MoexClient

RATING_ORDER = [
    "NR",
    "BBB-",
    "BBB",
    "BBB+",
    "A-",
    "A",
    "A+",
    "AA-",
    "AA",
    "AA+",
    "AAA",
]


class Bond(BaseModel):
    """Serialized bond model used by CLI and API."""

    ticker: str
    name: str
    company: str
    currency: str
    is_qualified_only: bool
    rating: str
    price: float
    bond_annual_yield: float
    coupon_percent: float
    coupons_per_year: int
    annual_yield: float
    yield_to_horizon: float
    months_to_maturity: float


def _rating_rank(rating: str) -> int:
    return RATING_ORDER.index(rating) if rating in RATING_ORDER else 0


def _normalize_rating(raw_rating: str) -> str | None:
    lowered = raw_rating.lower().strip()
    if lowered in {"", "nr", "н/д", "n/a", "not rated"}:
        return "NR"

    # Normalize values like ruAA+ and AA+(RU) to AA+.
    ru_suffix_match = re.search(r"([ab]{1,3}[+-]?)\s*\(ru\)", lowered)
    if ru_suffix_match:
        return ru_suffix_match.group(1).upper()

    ru_pipe_match = re.search(r"([ab]{1,3}[+-]?)\|ru\|", lowered)
    if ru_pipe_match:
        return ru_pipe_match.group(1).upper()

    ru_prefix_match = re.search(r"ru([ab]{1,3}[+-]?)", lowered)
    if ru_prefix_match:
        return ru_prefix_match.group(1).upper()

    for rating in sorted(RATING_ORDER[1:], key=len, reverse=True):
        if rating.lower() in lowered:
            return rating
    return None


def _passes_min_rating(raw_rating: str, min_rating: str | None) -> bool:
    if not min_rating:
        return True
    normalized_min = _normalize_rating(min_rating)
    normalized_current = _normalize_rating(raw_rating)
    if normalized_min is None:
        return True
    if normalized_current is None:
        return normalized_min == "NR"
    return _rating_rank(normalized_current) >= _rating_rank(normalized_min)


def _split_issue_issuer(raw_rating: str) -> tuple[str, str]:
    parts = [part.strip() for part in raw_rating.split("/")]
    if len(parts) >= 2:
        return parts[0] or "NR", parts[1] or "NR"
    single = parts[0] if parts and parts[0] else "NR"
    return single, "NR"


def _format_rating_display(raw_rating: str) -> str:
    normalized = raw_rating.strip()
    if not normalized:
        return "NR"
    parts = [part.strip() for part in normalized.split("/")]
    if len(parts) == 2 and parts[0] and parts[1]:
        if parts[0].upper() == parts[1].upper() and parts[0].upper() != "NR":
            return parts[0]
    return normalized


async def get_top_bonds_async(
    horizon_days: int | None = None,
    limit: int | None = None,
    min_annual_yield: Decimal | None = None,
    min_bond_rating: str | None = None,
    min_emitter_rating: str | None = None,
    currency: str | None = None,
    investor_profile: str | None = None,
    source_bonds: list[DomainBond] | None = None,
) -> list[Bond]:
    """Fetch top bonds while preserving existing calculation logic."""
    requested_limit = limit or settings.limit
    prefilter_limit = max(requested_limit * 8, 200)
    client = MoexClient()
    service = BondService(client=client, calculator=YieldCalculator())
    try:
        if source_bonds is None:
            ranked = await service.screen(
                horizon_days=horizon_days,
                min_rating="NR",
                limit=prefilter_limit,
                min_annual_yield=min_annual_yield,
            )
        else:
            ranked = await service.screen_bonds(
                source_bonds,
                horizon_days=horizon_days,
                min_rating="NR",
                limit=min(prefilter_limit, len(source_bonds)),
                min_annual_yield=min_annual_yield,
                enrich_ratings=False,
            )
    finally:
        await client.aclose()

    result: list[Bond] = []
    for item in ranked:
        if currency and item.bond.currency != currency:
            continue
        if investor_profile == "NONQUAL" and item.bond.is_qualified_only:
            continue
        issue_rating, issuer_rating = _split_issue_issuer(item.bond.rating)
        if not _passes_min_rating(issue_rating, min_bond_rating):
            continue
        if not _passes_min_rating(issuer_rating, min_emitter_rating):
            continue

        result.append(
            Bond(
                ticker=item.bond.secid,
                name=item.bond.shortname,
                company=item.bond.company_name,
                currency=item.bond.currency,
                is_qualified_only=item.bond.is_qualified_only,
                rating=_format_rating_display(item.bond.rating),
                price=float(YieldCalculator._market_price_amount(item.bond)),
                bond_annual_yield=float(item.bond.bond_annual_yield),
                coupon_percent=float(item.bond.coupon_percent),
                coupons_per_year=item.bond.coupons_per_year,
                annual_yield=float(item.metrics.annual_yield_percent),
                yield_to_horizon=float(item.metrics.horizon_yield_percent),
                months_to_maturity=float(item.metrics.months_to_redemption),
            )
        )
        if limit is not None and len(result) >= limit:
            break

    return result


def get_top_bonds(
    horizon_days: int | None = None,
    limit: int | None = None,
    min_annual_yield: Decimal | None = None,
    min_bond_rating: str | None = None,
    min_emitter_rating: str | None = None,
    currency: str | None = None,
    investor_profile: str | None = None,
) -> list[Bond]:
    """Sync wrapper for CLI usage."""
    return asyncio.run(
        get_top_bonds_async(
            horizon_days=horizon_days,
            limit=limit,
            min_annual_yield=min_annual_yield,
            min_bond_rating=min_bond_rating,
            min_emitter_rating=min_emitter_rating,
            currency=currency,
            investor_profile=investor_profile,
        )
    )
