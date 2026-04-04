# Architecture Rules

## Структура
- Корень: main.py, requirements.txt.
- domain/: entities/.
- infrastructure/: moex/.
- application/: services/.
- presentation/: cli/.
- utils/.
- docs/.
- logs/.

## Библиотеки
- Python 3.12, pydantic v2, httpx, aiocache, typer, rich, structlog, decimal, ruff, mypy.

## Правила Кода
- Clean Architecture.
- Decimal для цен/доходности.
- Async + retry.
- Google docstrings.
- Ruff + mypy strict.
- Нет print(), только rich/logger.
- Избегать: Hardcode, globals.