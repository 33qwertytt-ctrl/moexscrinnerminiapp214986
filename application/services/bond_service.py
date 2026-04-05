"""Bond screening service."""

import asyncio
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from application.services.yield_calculator import YieldCalculator
from domain.entities.bond import Bond, YieldMetrics
from infrastructure.moex.client import MoexClient

RATING_ORDER = [
    "NR",
    "ruBBB-",
    "ruBBB",
    "ruBBB+",
    "ruA-",
    "ruA",
    "ruA+",
    "ruAA-",
    "ruAA",
    "ruAA+",
    "ruAAA",
]


@dataclass(slots=True)
class RankedBond:
    """Bond paired with computed yields."""

    bond: Bond
    metrics: YieldMetrics


def _rating_rank(rating: str) -> int:
    return RATING_ORDER.index(rating) if rating in RATING_ORDER else 0


def _normalize_rating_value(raw_rating: str) -> str | None:
    lowered = raw_rating.lower()
    if lowered.strip() in {"nr", "н/д", "n/a", "not rated"}:
        return "NR"
    # CCI often returns values like `AA+(RU)`; normalize them to `ruAA+`.
    ru_match = re.search(r"\b([ab]{1,3}[+-]?)\s*\(ru\)\b", lowered)
    if ru_match:
        return f"ru{ru_match.group(1).upper()}"
    pipe_ru_match = re.search(r"\b([ab]{1,3}[+-]?)\|ru\|", lowered)
    if pipe_ru_match:
        return f"ru{pipe_ru_match.group(1).upper()}"
    for rating in sorted(RATING_ORDER[1:], key=len, reverse=True):
        if rating.lower() in lowered:
            return rating
    return None


class BondService:
    """Orchestrates filtering and ranking of bonds."""

    def __init__(self, client: MoexClient, calculator: YieldCalculator) -> None:
        self.client = client
        self.calculator = calculator

    @staticmethod
    def _passes_min_rating(bond: Bond, min_rating: str) -> bool:
        normalized_min_rating = _normalize_rating_value(min_rating) or "NR"
        parts = [part.strip() for part in bond.rating.split("/")]
        source_rating = next((part for part in parts if part and part != "NR"), "NR")
        normalized_rating = _normalize_rating_value(source_rating)
        if normalized_rating is None:
            return normalized_min_rating == "NR"
        return _rating_rank(normalized_rating) >= _rating_rank(normalized_min_rating)

    @staticmethod
    def _merge_ratings(existing_rating: str, combined_rating: str) -> str:
        if combined_rating != "NR/NR":
            return combined_rating
        existing_normalized = _normalize_rating_value(existing_rating)
        if existing_normalized is None or existing_normalized == "NR":
            return "NR/NR"
        return f"{existing_normalized}/NR"

    async def _enrich_ratings(self, ranked_bonds: list[RankedBond]) -> None:
        if self.client.cci_denied_threshold <= 1:
            for item in ranked_bonds:
                if self.client.cci_access_denied:
                    break
                combined_rating = await self.client.get_combined_rating(item.bond.secid)
                item.bond.rating = self._merge_ratings(item.bond.rating, combined_rating)
            return

        semaphore = asyncio.Semaphore(8)

        async def enrich_one(item: RankedBond) -> None:
            async with semaphore:
                combined_rating = await self.client.get_combined_rating(item.bond.secid)
                item.bond.rating = self._merge_ratings(item.bond.rating, combined_rating)

        await asyncio.gather(*(enrich_one(item) for item in ranked_bonds))

    def _rank(
        self,
        bonds: Iterable[Bond],
        horizon_days: int | None,
        min_rating: str,
        limit: int,
        min_annual_yield: Decimal | None,
    ) -> list[RankedBond]:
        ranked: list[RankedBond] = []
        for bond in bonds:
            if bond.nominal != Decimal("1000"):
                continue
            if bond.coupons_per_year <= 0:
                continue
            if bond.coupon_percent <= Decimal("0.01"):
                continue
            if bond.coupon_value <= Decimal("0"):
                continue
            if not self._passes_min_rating(bond, min_rating):
                continue
            metrics = self.calculator.calculate(bond, horizon_days)
            if metrics.annual_yield_percent <= Decimal("0"):
                continue
            if (
                min_annual_yield is not None
                and metrics.annual_yield_percent < min_annual_yield
            ):
                continue
            ranked.append(RankedBond(bond=bond, metrics=metrics))

        ranked.sort(key=lambda item: item.metrics.annual_yield_percent, reverse=True)
        return ranked[:limit]

    async def screen_bonds(
        self,
        bonds: Iterable[Bond],
        horizon_days: int | None,
        min_rating: str,
        limit: int,
        min_annual_yield: Decimal | None = None,
        *,
        enrich_ratings: bool,
    ) -> list[RankedBond]:
        """Filter and rank already-loaded bonds, optionally enriching ratings."""
        candidate_limit = max(limit * 4, 40)
        ranked = self._rank(bonds, horizon_days, "NR", candidate_limit, min_annual_yield)
        filtered: list[RankedBond] = []
        batch_size = 10
        for batch_start in range(0, len(ranked), batch_size):
            batch = ranked[batch_start : batch_start + batch_size]
            if enrich_ratings:
                await self._enrich_ratings(batch)
            filtered.extend(
                item for item in batch if self._passes_min_rating(item.bond, min_rating)
            )
            if enrich_ratings and self.client.cci_access_denied:
                for item in batch:
                    item.bond.rating = self._merge_ratings(item.bond.rating, "NR/NR")
                tail = ranked[batch_start + batch_size :]
                for item in tail:
                    item.bond.rating = self._merge_ratings(item.bond.rating, "NR/NR")
                filtered = [
                    item for item in filtered if self._passes_min_rating(item.bond, min_rating)
                ]
                filtered.extend(
                    item for item in tail if self._passes_min_rating(item.bond, min_rating)
                )
                break
            if len(filtered) >= limit:
                break
        if len(filtered) >= limit:
            filtered.sort(key=lambda item: item.metrics.annual_yield_percent, reverse=True)
            return filtered[:limit]

        seen_secids = {item.bond.secid for item in filtered}
        fallback = [item for item in ranked if item.bond.secid not in seen_secids]
        filtered.extend(fallback[: max(0, limit - len(filtered))])
        filtered.sort(key=lambda item: item.metrics.annual_yield_percent, reverse=True)
        return filtered[:limit]

    async def screen(
        self,
        horizon_days: int | None,
        min_rating: str,
        limit: int,
        min_annual_yield: Decimal | None = None,
    ) -> list[RankedBond]:
        """Fetch bonds and return filtered top list."""
        bonds = await self.client.get_bonds()
        return await self.screen_bonds(
            bonds,
            horizon_days=horizon_days,
            min_rating=min_rating,
            limit=limit,
            min_annual_yield=min_annual_yield,
            enrich_ratings=True,
        )
