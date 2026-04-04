"""MOEX payload parsers."""

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from domain.entities.bond import Bond


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    if value in (None, ""):
        return Decimal(default)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def _to_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _value(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _coupons_per_year(coupon_period_days: Decimal) -> int:
    if coupon_period_days <= 0:
        return 0
    return int(
        (Decimal("365") / coupon_period_days).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def _derive_company_name(shortname: str, security_name: str | None) -> str:
    candidate = " ".join((security_name or shortname or "").split())
    if not candidate:
        return ""

    tokens = candidate.split()
    company_tokens: list[str] = []
    for token in tokens:
        if not re.search(r"\d", token):
            company_tokens.append(token)
            continue
        prefix_match = re.match(r"([A-Za-zА-Яа-яЁё-]{3,})", token)
        if prefix_match and not company_tokens:
            company_tokens.append(prefix_match.group(1).rstrip("-"))
        break

    company = " ".join(part for part in company_tokens if part)
    if company:
        return company

    fallback = re.sub(r"\s+\d.*$", "", candidate).strip(" ,.-")
    return fallback or shortname


def _normalize_currency(raw_value: Any) -> str:
    normalized = str(raw_value or "").strip().upper()
    if normalized in {"SUR", "RUR", "RUB"}:
        return "RUB"
    if normalized in {"CNY", "CNH"}:
        return "CNY"
    return normalized or "UNKNOWN"


def _to_bool(value: Any) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "yes"}


def parse_bonds(payload: dict[str, Any]) -> list[Bond]:
    """Parse securities + marketdata datasets into domain bonds."""
    securities = payload.get("securities", {})
    market_data = payload.get("marketdata", {})

    sec_columns = securities.get("columns", [])
    sec_rows = securities.get("data", [])
    md_columns = market_data.get("columns", [])
    md_rows = market_data.get("data", [])

    securities_by_id: dict[str, dict[str, Any]] = {}
    for row in sec_rows:
        mapped = dict(zip(sec_columns, row, strict=False))
        secid = str(mapped.get("SECID", "")).strip()
        if secid:
            securities_by_id[secid] = mapped

    bonds: list[Bond] = []
    for row in md_rows:
        mapped_md = dict(zip(md_columns, row, strict=False))
        secid = str(mapped_md.get("SECID", "")).strip()
        if not secid or secid not in securities_by_id:
            continue
        sec = securities_by_id[secid]

        bond = Bond(
            secid=secid,
            shortname=str(_value(sec, "SHORTNAME", default=secid)),
            company_name=_derive_company_name(
                shortname=str(_value(sec, "SHORTNAME", default=secid)),
                security_name=_value(sec, "SECNAME", default=None),
            ),
            currency=_normalize_currency(_value(sec, "FACEUNIT", "CURRENCYID", default="")),
            is_qualified_only=_to_bool(_value(sec, "ISQUALIFIEDINVESTORS", default="0")),
            rating=str(_value(sec, "RATING", "CREDITRATING", default="NR")),
            price=_to_decimal(
                _value(
                    mapped_md,
                    "LAST",
                    "WAPRICE",
                    "CLOSEPRICE",
                    "MARKETPRICE",
                    default=_value(sec, "PREVWAPRICE", "PREVPRICE", default="0"),
                )
            ),
            coupon_percent=_to_decimal(_value(sec, "COUPONPERCENT", default="0")),
            coupon_value=_to_decimal(_value(sec, "COUPONVALUE", default="0")),
            coupons_per_year=_coupons_per_year(
                _to_decimal(_value(sec, "COUPONPERIOD", default="0"))
            ),
            nominal=_to_decimal(_value(sec, "FACEVALUE", "LOTVALUE", default="1000")),
            maturity_date=_to_date(_value(sec, "MATDATE", "REDEMPTIONDATE")),
            offer_date=_to_date(_value(sec, "OFFERDATE")),
            lot_value=_to_decimal(_value(sec, "LOTVALUE", default="0")),
        )
        bonds.append(bond)
    return bonds
