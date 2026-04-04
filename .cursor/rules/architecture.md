# Project Architecture (Current State - Updated After Each Stage)

## Общая Структура
- Корень: main.py, .env.example, requirements.txt, pyproject.toml.
- config/: settings.py (pydantic-settings + BONDS_ env prefix).
- domain/: entities/ (Bond, YieldMetrics).
- infrastructure/: moex/ (client, parsers, cache).
- application/: services/ (YieldCalculator, BondService).
- presentation/: cli/ (typer commands, rich table).
- utils/: calendar.py, logging.py.
- frontend/: React Mini App + Telegram WebApp SDK.
- docs/: architecture.md, plan.md, requirements.md, archrules.md.
- logs/: runtime directory.

## Модули и Связи
- main.py -> presentation/cli/ -> application/services/ -> infrastructure/moex/.
- YieldCalculator: Decimal-based formula.
- Кэш: aiocache.
- CLI: typer + rich (9 columns + disclaimer).

## Принципы Организации
- Clean Architecture.
- Async httpx для MOEX.
- Decimal везде.
- Логи: structlog.

## Текущий Статус
- Этап 1: Базовая Инфраструктура (выполнен).
- Этап 2: Данные и Infrastructure (выполнен).
- Этап 3: Domain и Application (выполнен).
- Этап 4: Presentation и CLI (выполнен).
- Этап 5: Telegram Mini App (optional, выполнен как frontend каркас).
- Дисклеймер: Личный инструмент, не финансовая рекомендация.