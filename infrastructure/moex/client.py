"""Async MOEX ISS client."""

import asyncio
from datetime import datetime
from typing import Any, cast

import httpx
from aiocache import cached

from config.settings import settings
from domain.entities.bond import Bond
from infrastructure.moex.parsers import parse_bonds


class MoexClient:
    """Client for MOEX ISS bond endpoints."""

    base_url = "https://iss.moex.com/iss/engines/stock/markets/bonds/securities.json"
    security_card_url = "https://iss.moex.com/iss/securities/{secid}.json"
    cci_issue_rating_url = (
        "https://iss.moex.com/iss/cci/rating/companies/ecbd_{company_id}/"
        "securities/isin_{secid}.json"
    )
    cci_company_rating_url = (
        "https://iss.moex.com/iss/cci/rating/companies/ecbd_{company_id}.json"
    )
    default_headers = {
        "User-Agent": "BondScreenerMOEX/1.0 (non-commercial)",
        "Accept": "application/json",
    }

    def __init__(self, timeout_seconds: float = 6.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.cci_access_denied = False
        self.cci_denied_streak = 0
        self.cci_denied_total = 0
        self.cci_denied_threshold = 1
        self.rating_debug: dict[str, dict[str, Any]] = {}

    def _store_rating_debug(
        self,
        secid: str,
        stage: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        if secid not in self.rating_debug:
            self.rating_debug[secid] = {}
        self.rating_debug[secid][stage] = payload or {}

    async def _fetch_json_url(
        self,
        url: str,
        params: dict[str, str] | None = None,
        debug_secid: str | None = None,
        debug_stage: str | None = None,
    ) -> Any:
        attempts = 3
        request_params = {"iss.meta": "off"}
        if params is not None:
            request_params.update(params)

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    response = await client.get(
                        url, params=request_params, headers=self.default_headers
                    )
                    response.raise_for_status()
                    is_cci_url = "/iss/cci/" in url
                    snippet = response.text[:120] if response.text else ""
                    if debug_secid is not None and debug_stage is not None:
                        self._store_rating_debug(
                            debug_secid,
                            debug_stage,
                            {
                                "url": str(response.url),
                                "status": response.status_code,
                                "marker": response.headers.get("X-MicexPassport-Marker"),
                                "content_type": response.headers.get("content-type"),
                                "content_len": len(response.text),
                                "snippet": snippet,
                                "attempt": attempt,
                            },
                        )
                    marker = response.headers.get("X-MicexPassport-Marker")
                    if not response.content:
                        if is_cci_url and marker == "denied":
                            self.cci_denied_streak += 1
                            self.cci_denied_total += 1
                            if self.cci_denied_streak >= self.cci_denied_threshold:
                                self.cci_access_denied = True
                        return {}

                    payload: Any
                    try:
                        payload = response.json()
                    except ValueError:
                        if is_cci_url and marker == "denied":
                            self.cci_denied_streak += 1
                            self.cci_denied_total += 1
                            if self.cci_denied_streak >= self.cci_denied_threshold:
                                self.cci_access_denied = True
                        return {}

                    # Some CCI endpoints may return data together with `marker=denied`.
                    # Treat this as a successful response if JSON payload is present.
                    if is_cci_url:
                        if marker == "denied" and payload in ({}, []):
                            self.cci_denied_streak += 1
                            self.cci_denied_total += 1
                            if self.cci_denied_streak >= self.cci_denied_threshold:
                                self.cci_access_denied = True
                            return {}
                        self.cci_denied_streak = 0

                    return payload
            except (httpx.HTTPError, ValueError):
                if debug_secid is not None and debug_stage is not None:
                    self._store_rating_debug(
                        debug_secid,
                        debug_stage,
                        {
                            "url": url,
                            "status": "error",
                            "marker": None,
                            "content_type": None,
                            "content_len": 0,
                            "snippet": "",
                            "attempt": attempt,
                        },
                    )
                if attempt == attempts:
                    return {}
                await asyncio.sleep(0.7 * attempt)
        return {}

    async def _fetch_json(self) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            await self._fetch_json_url(
                self.base_url,
                params={"iss.only": "securities,marketdata"},
            ),
        )

    @staticmethod
    def _extract_table_rows(payload: Any) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if isinstance(payload, list):
            for section in payload:
                if not isinstance(section, dict):
                    continue
                for value in section.values():
                    if not isinstance(value, list):
                        continue
                    for row in value:
                        if isinstance(row, dict):
                            rows.append(row)
            return rows
        for value in payload.values():
            if not isinstance(value, dict):
                continue
            columns = value.get("columns")
            data = value.get("data")
            if not isinstance(columns, list) or not isinstance(data, list):
                continue
            for row in data:
                if isinstance(row, list):
                    rows.append(dict(zip(columns, row, strict=False)))
        return rows

    @staticmethod
    def _extract_latest_rating(payload: Any) -> str | None:
        rating_keys = (
            "RATING",
            "RATING_VALUE",
            "RATINGVALUE",
            "VALUE",
            "RATING_TEXT",
            "RATINGSCALEVALUE",
            "RATING_LEVEL_NAME_SHORT_RU",
            "RATING_LEVEL_NAME_SHORT_EN",
            "RATING_LEVEL_NAME_RU",
            "RATING_LEVEL_NAME_EN",
        )
        date_keys = ("RATINGDATE", "ACTIONDATE", "DATE", "UPDATED", "MODIFIED")
        best_rating: str | None = None
        best_date = datetime.min

        for row in MoexClient._extract_table_rows(payload):
            normalized_row = {str(key).upper(): value for key, value in row.items()}
            rating_value: str | None = None
            for key in rating_keys:
                raw_value = normalized_row.get(key)
                if raw_value not in (None, ""):
                    rating_value = str(raw_value).strip()
                    break
            if not rating_value:
                continue

            parsed_date = datetime.min
            for key in date_keys:
                raw_date = normalized_row.get(key)
                if raw_date in (None, ""):
                    continue
                try:
                    normalized = str(raw_date).replace("Z", "+00:00")
                    parsed_date = datetime.fromisoformat(normalized)
                    break
                except ValueError:
                    continue

            if best_rating is None or parsed_date >= best_date:
                best_rating = rating_value
                best_date = parsed_date

        return best_rating

    @cached(ttl=settings.cache_ttl)
    async def get_emitter_id(self, secid: str) -> str | None:
        payload = await self._fetch_json_url(
            self.security_card_url.format(secid=secid),
            params={"iss.only": "description"},
            debug_secid=secid,
            debug_stage="description",
        )
        description = payload.get("description", {})
        columns = description.get("columns", [])
        rows = description.get("data", [])
        if not isinstance(columns, list) or not isinstance(rows, list):
            return None

        for row in rows:
            if not isinstance(row, list):
                continue
            mapped_row = dict(zip(columns, row, strict=False))
            key = str(mapped_row.get("name", "")).upper()
            if key in {"EMITTER_ID", "EMITENT_ID", "ISSUER_ID", "COMPANY_ID"}:
                value = mapped_row.get("value")
                if value not in (None, ""):
                    return str(value).strip()
        return None

    @cached(ttl=settings.cache_ttl)
    async def get_issue_rating(self, secid: str, company_id: str | None) -> str | None:
        if self.cci_access_denied:
            self._store_rating_debug(
                secid, "issue", {"status": "skipped", "reason": "cci_access_denied"}
            )
            return None
        payload: Any = {}
        if company_id is not None:
            payload = await self._fetch_json_url(
                self.cci_issue_rating_url.format(company_id=company_id, secid=secid),
                params={"iss.json": "extended"},
                debug_secid=secid,
                debug_stage="issue",
            )
        issue_rating = self._extract_latest_rating(payload)
        return issue_rating

    @cached(ttl=settings.cache_ttl)
    async def get_company_rating(self, company_id: str, secid: str | None = None) -> str | None:
        if self.cci_access_denied:
            if secid is not None:
                self._store_rating_debug(
                    secid, "issuer", {"status": "skipped", "reason": "cci_access_denied"}
                )
            return None
        payload = await self._fetch_json_url(
            self.cci_company_rating_url.format(company_id=company_id),
            params={"iss.json": "extended"},
            debug_secid=secid,
            debug_stage="issuer",
        )
        return self._extract_latest_rating(payload)

    @cached(ttl=settings.cache_ttl)
    async def get_combined_rating(self, secid: str) -> str:
        if self.cci_access_denied:
            return "NR/NR"
        emitter_id = await self.get_emitter_id(secid)
        self._store_rating_debug(secid, "emitter", {"emitter_id": emitter_id or ""})
        if self.cci_access_denied:
            return "NR/NR"
        issue_rating = await self.get_issue_rating(secid, emitter_id)
        if self.cci_access_denied:
            return "NR/NR"
        issuer_rating = (
            await self.get_company_rating(emitter_id, secid) if emitter_id is not None else None
        )
        return f"{issue_rating or 'NR'}/{issuer_rating or 'NR'}"

    def get_rating_debug(self, secid: str) -> dict[str, Any]:
        return self.rating_debug.get(secid, {})

    def get_rating_runtime_status(self) -> dict[str, int | bool]:
        return {
            "cci_access_denied": self.cci_access_denied,
            "cci_denied_streak": self.cci_denied_streak,
            "cci_denied_total": self.cci_denied_total,
            "cci_denied_threshold": self.cci_denied_threshold,
        }

    @cached(ttl=settings.cache_ttl)
    async def get_bonds(self) -> list[Bond]:
        """Fetch and parse bonds list."""
        payload = await self._fetch_json()
        return parse_bonds(payload)
