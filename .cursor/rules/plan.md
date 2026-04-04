# Implementation Plan for BondScreener MOEX

## Основные Принципы
- Этапы по возрастанию: База, Данные, Расчёты, CLI, Mini App (опционально).
- Личный проект: Нет монетизации.
- После этапа: Обновить docs/architecture.md.
- North Star: 3–5 сек, >0% доходность, мин.рейтинг.

## Этапы Реализации

### Этап 1: Базовая Инфраструктура ✅
- ✅ .env.example + .env (с BONDS_ переменными)
- ✅ config/settings.py (pydantic-settings)
- ✅ utils/logging.py
- ✅ utils/calendar.py
- ✅ requirements.txt.
- Чек-лист:
  - [x] Pydantic-settings.
  - [x] Structlog setup.
- Промпт для Cursor: "Implement Stage 1 following .cursor/rules/02_architecture.md and 07_clean_code.md"

### Этап 2: Данные и Infrastructure (moex client, parsers, cache) ✅
- ✅ infrastructure/moex/client.py (async httpx to ISS).
- ✅ Parsers for securities.json, bondization.json, etc.
- ✅ Кэш: aiocache.
- Чек-лист:
  - [x] Async requests.
  - [x] Жёсткий фильтр min_rating.
- Промпт: "Implement Stage 2 following .cursor/rules/04_data_sources.md"

### Этап 3: Domain и Application (entities, YieldCalculator) ✅
- ✅ domain/entities/Bond.py etc.
- ✅ application/services/YieldCalculator.py (ТОЧНАЯ формула!).
- ✅ BondService (фильтр, сортировка).
- Чек-лист:
  - [x] Decimal everywhere.
  - [x] Формула locked.
- Промпт: "Implement Stage 3 following .cursor/rules/03_yield_formula.md"

### Этап 4: Presentation и CLI (typer + rich table) ✅
- ✅ presentation/cli/main.py (флаги --horizon, --min-rating, --limit).
- ✅ Rich table с цветами.
- ✅ main.py entry.
- Чек-лист:
  - [x] 9 колонок.
  - [x] Цвета hex.
- Промпт: "Implement Stage 4 following .cursor/rules/05_rich_table.md and 06_cli_typer.md"

### Этап 5: Telegram Mini App (опционально) ✅
- ✅ React + Telegram WebApp SDK.
- ✅ Чипсы для горизонта/рейтинга/лимита.
- ✅ Таблица + карточка.
- Чек-лист:
  - [x] После CLI.
- Промпт: "Implement Stage 5 as optional"

## Финальный Этап: Тест и Интеграция
- ✅ Полный run: python main.py.
- ✅ Дисклеймер в выводе.
- Чек-лист:
  - [ ] <5 сек.
  - [ ] Только >0%.