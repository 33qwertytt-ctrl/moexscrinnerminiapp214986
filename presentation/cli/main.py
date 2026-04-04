"""Typer CLI for BondScreener."""

import asyncio
from decimal import Decimal, InvalidOperation
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from application.services.bond_service import BondService, RankedBond
from application.services.yield_calculator import YieldCalculator
from config.settings import settings
from infrastructure.moex.client import MoexClient
from utils.logging import setup_logging

app = typer.Typer(help="MOEX bond screener")
console = Console()


def _horizon_to_days(raw_horizon: str | None) -> int | None:
    if raw_horizon is None or not raw_horizon.strip():
        return None
    normalized = raw_horizon.strip().lower()
    mapping = {"7": 7, "14": 14, "30": 30, "90": 90}
    return mapping.get(normalized, 30)


def _parse_min_annual_yield(raw_value: str | None) -> Decimal | None:
    if raw_value is None or not raw_value.strip():
        return None
    try:
        return Decimal(raw_value.strip())
    except InvalidOperation as exc:
        raise typer.BadParameter("Use numeric value for --min-annual-yield.") from exc


def _warn_if_env_missing() -> None:
    if not Path(".env").exists():
        console.print(
            "[bold yellow]Warning:[/] .env file is missing. "
            "Copy .env.example to .env and adjust values."
        )


def _build_table() -> Table:
    table = Table(title="Top MOEX Bonds")
    table.add_column("Тикер", style="#8ecae6")
    table.add_column("Название", style="#219ebc")
    table.add_column("Рейтинги, выпуск, эмитент", style="#90be6d")
    table.add_column("Цена", justify="right", style="#ffb703")
    table.add_column("Купон, %", justify="right", style="#fb8500")
    table.add_column("Купонов в год", justify="right", style="#f4a261")
    table.add_column("Годовая доходность, %", justify="right", style="#80ed99")
    table.add_column("Доходность до горизонта, %", justify="right", style="#57cc99")
    table.add_column("Месяцев до погашения", justify="right", style="#38a3a5")
    return table


def _format_rating_display(raw_rating: str) -> str:
    normalized = raw_rating.strip()
    if not normalized:
        return "NR"
    parts = [part.strip() for part in normalized.split("/")]
    if len(parts) == 2 and parts[0] and parts[1]:
        if parts[0].upper() == parts[1].upper() and parts[0].upper() != "NR":
            return parts[0]
    return normalized


def _print_rating_debug(client: MoexClient, ranked: list[RankedBond]) -> None:
    debug_table = Table(title="Rating Debug")
    debug_table.add_column("Тикер", style="#8ecae6")
    debug_table.add_column("Issue status", style="#90be6d")
    debug_table.add_column("Issue marker", style="#ffb703")
    debug_table.add_column("Issue len", justify="right", style="#fb8500")
    debug_table.add_column("Issuer status", style="#80ed99")
    debug_table.add_column("Issuer marker", style="#57cc99")
    debug_table.add_column("Issuer len", justify="right", style="#38a3a5")
    debug_table.add_column("Emitter", style="#4cc9f0")
    debug_table.add_column("Snippet", style="#adb5bd")

    for item in ranked:
        info = client.get_rating_debug(item.bond.secid)
        issue = info.get("issue", {})
        issuer = info.get("issuer", {})
        emitter = info.get("emitter", {})
        snippet = str(issue.get("snippet") or issuer.get("snippet") or "")
        debug_table.add_row(
            item.bond.secid,
            str(issue.get("status", "")),
            str(issue.get("marker", "")),
            str(issue.get("content_len", "")),
            str(issuer.get("status", "")),
            str(issuer.get("marker", "")),
            str(issuer.get("content_len", "")),
            str(emitter.get("emitter_id", "")),
            snippet[:60],
        )
    console.print(debug_table)


@app.command()
def run(
    horizon: str | None = typer.Option(
        settings.default_horizon,
        "--horizon",
        help="7/14/30/90 or empty value to use full period to redemption",
    ),
    min_rating: str = typer.Option(settings.min_rating, "--min-rating"),
    limit: int = typer.Option(settings.limit, "--limit"),
    min_annual_yield: str | None = typer.Option(
        None,
        "--min-annual-yield",
        help="Optional minimum annual yield in percent",
    ),
    debug_rating: bool = typer.Option(
        False,
        "--debug-rating",
        help="Show CCI rating response diagnostics for each row",
    ),
) -> None:
    """Screen bonds and render top table."""
    setup_logging(settings.log_level)
    _warn_if_env_missing()

    client = MoexClient()
    service = BondService(client=client, calculator=YieldCalculator())
    ranked = asyncio.run(
        service.screen(
            _horizon_to_days(horizon),
            min_rating,
            limit,
            _parse_min_annual_yield(min_annual_yield),
        )
    )

    table = _build_table()
    for item in ranked:
        table.add_row(
            item.bond.secid,
            item.bond.shortname,
            _format_rating_display(item.bond.rating),
            f"{YieldCalculator._market_price_amount(item.bond):.2f}",
            f"{item.bond.coupon_percent:.2f}",
            str(item.bond.coupons_per_year),
            f"{item.metrics.annual_yield_percent:.2f}",
            f"{item.metrics.horizon_yield_percent:.2f}",
            f"{item.metrics.months_to_redemption:.1f}",
        )

    console.print(table)
    runtime_status = client.get_rating_runtime_status()
    if bool(runtime_status["cci_access_denied"]):
        console.print(
            "[bold yellow]Warning:[/] CCI rating requests were auto-stopped after "
            f"threshold {runtime_status['cci_denied_threshold']} denied markers "
            f"(observed denied in run: {runtime_status['cci_denied_total']}). "
            "Current run uses NR/NR fallback for remaining rows."
        )
    if debug_rating:
        _print_rating_debug(client, ranked)
