"""Daily bond snapshot storage and refresh orchestration."""

from __future__ import annotations

import asyncio
import copy
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog

from application.services.bond_service import BondService
from application.services.yield_calculator import YieldCalculator
from config.settings import Settings
from domain.entities.bond import Bond
from infrastructure.moex.client import MoexClient

logger = structlog.get_logger(__name__)

SNAPSHOT_HORIZONS = (7, 14, 30, 90)
SNAPSHOT_CANDIDATE_LIMIT = 400
SNAPSHOT_ENRICH_CONCURRENCY = 24


def _load_timezone(name: str):
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        logger.warning("bond_snapshot_timezone_fallback", requested=name)
        return datetime.now().astimezone().tzinfo or UTC


def _serialize_bond(bond: Bond) -> dict[str, Any]:
    return {
        "secid": bond.secid,
        "shortname": bond.shortname,
        "company_name": bond.company_name,
        "currency": bond.currency,
        "is_qualified_only": bond.is_qualified_only,
        "rating": bond.rating,
        "price": str(bond.price),
        "bond_annual_yield": str(bond.bond_annual_yield),
        "coupon_percent": str(bond.coupon_percent),
        "coupon_value": str(bond.coupon_value),
        "coupons_per_year": bond.coupons_per_year,
        "nominal": str(bond.nominal),
        "maturity_date": bond.maturity_date.isoformat() if bond.maturity_date else None,
        "offer_date": bond.offer_date.isoformat() if bond.offer_date else None,
        "lot_value": str(bond.lot_value),
    }


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _deserialize_bond(payload: dict[str, Any]) -> Bond:
    return Bond(
        secid=str(payload["secid"]),
        shortname=str(payload["shortname"]),
        company_name=str(payload["company_name"]),
        currency=str(payload["currency"]),
        is_qualified_only=bool(payload["is_qualified_only"]),
        rating=str(payload["rating"]),
        price=Decimal(str(payload["price"])),
        bond_annual_yield=Decimal(str(payload.get("bond_annual_yield", "0"))),
        coupon_percent=Decimal(str(payload["coupon_percent"])),
        coupon_value=Decimal(str(payload["coupon_value"])),
        coupons_per_year=int(payload["coupons_per_year"]),
        nominal=Decimal(str(payload["nominal"])),
        maturity_date=_parse_date(payload.get("maturity_date")),
        offer_date=_parse_date(payload.get("offer_date")),
        lot_value=Decimal(str(payload["lot_value"])),
    )


class BondSnapshotService:
    """Keeps a local on-disk and in-memory snapshot of MOEX bonds."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._snapshot_path = Path(settings.bonds_snapshot_path)
        self._timezone = _load_timezone(settings.bonds_snapshot_timezone)
        self._lock = asyncio.Lock()
        self._bonds: list[Bond] = []
        self._meta: dict[str, Any] = {}
        self._scheduler_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        loaded = await self._load_from_disk()
        if not loaded:
            await self.refresh(reason="startup_empty")
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._scheduler_task is None:
            return
        self._scheduler_task.cancel()
        try:
            await self._scheduler_task
        except asyncio.CancelledError:
            pass

    async def get_bonds(self) -> list[Bond]:
        async with self._lock:
            if self._bonds:
                return copy.deepcopy(self._bonds)
        await self.refresh(reason="request_miss")
        async with self._lock:
            return copy.deepcopy(self._bonds)

    async def get_meta(self) -> dict[str, Any]:
        async with self._lock:
            return dict(self._meta)

    async def refresh(self, *, reason: str) -> dict[str, Any]:
        async with self._lock:
            started_at = datetime.now(tz=UTC)
            logger.info("bond_snapshot_refresh_started", reason=reason)

            client = MoexClient(timeout_seconds=2.0, max_attempts=1)
            client.cci_denied_threshold = 3
            screener = BondService(client=client, calculator=YieldCalculator())
            try:
                all_bonds = await client.get_bonds()
                bonds = self._select_candidates(all_bonds, screener)
                await self._enrich_all_ratings(bonds, client, screener)
            finally:
                await client.aclose()

            completed_at = datetime.now(tz=UTC)
            meta = {
                "refreshed_at": completed_at.isoformat(),
                "started_at": started_at.isoformat(),
                "reason": reason,
                "bond_count": len(bonds),
                "source_bond_count": len(all_bonds),
                "cci_status": client.get_rating_runtime_status(),
            }
            payload = {"meta": meta, "bonds": [_serialize_bond(bond) for bond in bonds]}
            await asyncio.to_thread(self._write_snapshot, payload)

            self._bonds = bonds
            self._meta = meta
            logger.info("bond_snapshot_refresh_finished", **meta)
            return dict(meta)

    def _select_candidates(self, all_bonds: list[Bond], screener: BondService) -> list[Bond]:
        selected: dict[str, Bond] = {}
        for horizon in SNAPSHOT_HORIZONS:
            ranked = screener._rank(
                all_bonds,
                horizon_days=horizon,
                min_rating="NR",
                limit=SNAPSHOT_CANDIDATE_LIMIT,
                min_annual_yield=None,
            )
            for item in ranked:
                selected.setdefault(item.bond.secid, copy.deepcopy(item.bond))
        return list(selected.values())

    async def _enrich_all_ratings(
        self,
        bonds: list[Bond],
        client: MoexClient,
        screener: BondService,
    ) -> None:
        if client.cci_denied_threshold <= 1:
            for bond in bonds:
                if client.cci_access_denied:
                    break
                combined_rating = await client.get_combined_rating(bond.secid)
                bond.rating = screener._merge_ratings(bond.rating, combined_rating)
            if client.cci_access_denied:
                for bond in bonds:
                    bond.rating = screener._merge_ratings(bond.rating, "NR/NR")
            return

        semaphore = asyncio.Semaphore(SNAPSHOT_ENRICH_CONCURRENCY)

        async def enrich_one(bond: Bond) -> None:
            async with semaphore:
                combined_rating = await client.get_combined_rating(bond.secid)
                bond.rating = screener._merge_ratings(bond.rating, combined_rating)

        await asyncio.gather(*(enrich_one(bond) for bond in bonds))

    async def _load_from_disk(self) -> bool:
        if not self._snapshot_path.is_file():
            return False
        try:
            payload = await asyncio.to_thread(self._read_snapshot)
        except (OSError, json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.warning("bond_snapshot_load_failed", path=str(self._snapshot_path))
            return False

        bonds = [_deserialize_bond(item) for item in payload.get("bonds", [])]
        meta = payload.get("meta", {})
        async with self._lock:
            self._bonds = bonds
            self._meta = dict(meta) if isinstance(meta, dict) else {}
        logger.info(
            "bond_snapshot_loaded",
            path=str(self._snapshot_path),
            bond_count=len(bonds),
            refreshed_at=self._meta.get("refreshed_at"),
        )
        return True

    async def _scheduler_loop(self) -> None:
        while not self._stop_event.is_set():
            delay = self._seconds_until_next_refresh()
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            except asyncio.TimeoutError:
                try:
                    await self.refresh(reason="scheduled")
                except Exception:
                    logger.exception("bond_snapshot_refresh_failed")

    def _seconds_until_next_refresh(self) -> float:
        now = datetime.now(self._timezone)
        next_run = now.replace(
            hour=self._settings.bonds_snapshot_refresh_hour,
            minute=self._settings.bonds_snapshot_refresh_minute,
            second=0,
            microsecond=0,
        )
        if next_run <= now:
            next_run += timedelta(days=1)
        return max((next_run - now).total_seconds(), 1.0)

    def _read_snapshot(self) -> dict[str, Any]:
        return json.loads(self._snapshot_path.read_text(encoding="utf-8"))

    def _write_snapshot(self, payload: dict[str, Any]) -> None:
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshot_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
