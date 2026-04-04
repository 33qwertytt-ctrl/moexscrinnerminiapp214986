# Проверка Этапов

## Этап 1: Базовая Инфраструктура ✅
- ✅ config/settings.py.
- ✅ utils/logging.py.
- ✅ utils/calendar.py.
- Проверка: mypy/ruff pass.

## Этап 2: Данные ✅
- ✅ moex/client.py.
- ✅ Parsers.
- Проверка: Async fetch работает.

## Этап 3: Расчёты ✅
- ✅ Entities.
- ✅ YieldCalculator.
- Проверка: Формула верна (тест Decimal).

## Этап 4: CLI ✅
- ✅ typer + rich.
- Проверка: python main.py --horizon 30.

## Этап 5: Mini App ✅
- ✅ React app.
- Проверка: Таблица в Telegram.