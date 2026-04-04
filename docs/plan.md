# Implementation Plan for BondScreener MOEX

## Основные Принципы
- Этапы по возрастанию: База, Данные, Расчёты, CLI, Mini App (опционально).
- После этапа обновлять `docs/architecture.md`.
- North Star: 3-5 сек, >0% доходность, мин.рейтинг.

## Этапы Реализации

### Этап 1: Базовая Инфраструктура ✅
- ✅ `.env` в репозитории (публичные ключи; секреты — пустые) + `.env.example` как дубль структуры.
- ✅ `config/settings.py` (pydantic-settings).
- ✅ `utils/logging.py`.
- ✅ `utils/calendar.py`.
- ✅ `requirements.txt`.

### Этап 2: Данные и Infrastructure ✅
- ✅ `infrastructure/moex/client.py` (async httpx к ISS).
- ✅ `infrastructure/moex/parsers.py`.
- ✅ Кэш через `aiocache`.
- ✅ Жёсткий фильтр по `min_rating` в сервисе.
- ✅ Обновление 2026-02-28:
  - добавлено получение рейтинга выпуска и эмитента из MOEX CCI;
  - добавлено получение `EMITTER_ID` через `securities/{SECID}` (`description`);
  - формат рейтинга в модели/выводе: `issue/issuer`;
  - добавлены `User-Agent`/`Accept` и более мягкий retry-backoff для снижения `denied`;
  - добавлена авто-остановка CCI после 3 последовательных `denied` в рамках одного запуска.
- ✅ Обновление 2026-03-05:
  - исправлена интерпретация CCI-ответов: `X-MicexPassport-Marker=denied` больше не считается фатальным, если тело содержит валидный JSON;
  - переход на CCI endpoint'ы формата `ecbd_{EMITTER_ID}` / `isin_{SECID}` (`iss.json=extended`) для рейтингов эмитента и выпуска;
  - расширен парсер CCI под `extended` payload (list datasets + `RATING_LEVEL_NAME_SHORT_*`).

### Этап 3: Domain и Application ✅
- ✅ `domain/entities/bond.py`.
- ✅ `application/services/yield_calculator.py` (`Decimal`).
- ✅ `application/services/bond_service.py` (фильтр, сортировка, >0%).
- ✅ Обновление 2026-02-28:
  - фильтр только по облигациям с номиналом `1000`;
  - новая формула доходности до горизонта и годовой доходности;
  - фильтрация и сортировка по годовой доходности;
  - опциональный порог `min_annual_yield`;
  - переход с лет до погашения на месяцы;
  - исключение облигаций с `0` купонов в год;
  - исключение облигаций с `coupon_value = 0`;
  - корректировка формулы: прирост к номиналу учитывается только если горизонт достигает оферты/погашения;
  - батчевое обогащение рейтингов до заполнения `limit` (вместо обогащения всего пула кандидатов).
- ✅ Обновление 2026-03-05:
  - расширена нормализация рейтингов: формат CCI `AA+(RU)` приводится к шкале `ruAA+` для корректной работы `--min-rating`.
  - добавлен фильтр "технического нуля" для купона: бумаги с `coupon_percent <= 0.01` исключаются из ранжирования.
  - перед финальным возвратом после fallback добавлена обязательная пересортировка по годовой доходности по убыванию.

### Этап 4: Presentation и CLI ✅
- ✅ `presentation/cli/main.py` (`typer` + `rich`).
- ✅ Флаги `--horizon`, `--min-rating`, `--limit`.
- ✅ Таблица на 9 колонок + цвета.
- ✅ `main.py` entrypoint и warning для отсутствующего `.env`.
- ✅ Обновление 2026-02-28:
  - удалена колонка дюрации;
  - добавлена колонка "Купонов в год" (после "Купон, %");
  - "Лет до погашения" заменено на "Месяцев до погашения";
  - добавлен CLI-флаг `--min-annual-yield`;
  - дефолтный лимит строк увеличен до `20`;
  - добавлен CLI-флаг `--debug-rating` для диагностики CCI-ответов (причины `NR/NR`).
- ✅ Обновление 2026-03-01:
  - в таблице оставлен исходный формат `NR/NR`; схлопываются только дубли вида `X/X` (кроме `NR/NR`);
  - исправлена фильтрация `min_rating`: `NR` и нераспознанные значения больше не проходят порог `ruA`/`ruAA` по умолчанию;
  - добавлен fallback при `CCI -> NR/NR`: если в `securities` уже есть рейтинг выпуска, выводится `issue/NR` вместо полной потери рейтинга.
  - добавлен fallback заполнения выдачи: если после фильтра `min_rating` не хватает строк из-за недоступных рейтингов, таблица дополняется лучшими по доходности бумагами, чтобы не возвращать пустой результат.
  - для CCI-denied сценария включена немедленная авто-остановка после первого `denied` (вместо серии повторов), чтобы сократить время запуска при недоступном источнике рейтингов.
  - при `cci_denied_threshold=1` обогащение рейтингов переведено в последовательный режим с ранним завершением, чтобы не создавать лишний burst запросов.
  - исправлен denied-edge-case: при раннем останове CCI незавершённые бумаги текущего батча теперь тоже нормализуются через fallback `NR/NR`/`issue/NR`.
- ✅ Обновление 2026-03-05:
  - заголовок колонки рейтинга уточнен до `Рейтинги, выпуск, эмитент`;
  - проверена консистентность величин в выдаче: отображаемая цена берется из `_market_price_amount`, доходности совпадают с повторным расчетом `YieldCalculator` для тех же входных данных.

### Этап 5: Telegram Mini App ✅
- ✅ `frontend/` (Vite + React + `@telegram-apps/sdk` + `telegram-web-app.js`).
- ✅ Живые данные с `GET /api/bonds` (чипсы горизонт/рейтинг/лимит, обновление, обработка ошибок).
- ✅ Таблица (9 колонок) + карточка по клику + дисклеймер + подсветка годовой доходности.
- ✅ `vite` dev-proxy `/api` → `http://127.0.0.1:8000`.

### Этап 6: Web API + Shared Service ✅
- ✅ Добавлен `app/bonds_service.py` с переиспользованием существующей бизнес-логики `BondService`/`YieldCalculator`.
- ✅ Вынесен единый контракт `get_top_bonds()` / `get_top_bonds_async()` для CLI и Web API.
- ✅ Добавлена фильтрация по минимальным рейтингам:
  - `min_bond_rating` (рейтинг выпуска);
  - `min_emitter_rating` (рейтинг эмитента);
  - шкала: `AAA > AA+ > AA > AA- > A+ > A > A- > BBB+ > BBB > BBB- > NR`.
- ✅ Добавлен FastAPI сервер `app/main.py`:
  - `GET /api/bonds`;
  - раздача собранного Mini App из `frontend/dist` (`/`, `/assets/*`).
- ✅ Устаревший vanilla UI в `web/` не подключён к `app/main.py` (по желанию можно удалить позже).
- ✅ Добавлен новый CLI-слой `cli/print_table.py` с `rich.Table`, использующий `get_top_bonds()`.
- ✅ Обновлен entrypoint `main.py`: запуск CLI через `cli/print_table.py`.
- ✅ Команда запуска сервера: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

### Развёртывание VPS (Ubuntu / Hostinger) ✅
- ✅ `scripts/deploy/vps-setup.sh` — Python venv, **Node.js + сборка `frontend/`**, `systemd`, nginx, UFW; `GIT_REPO_EXAMPLE`, `LETSENCRYPT_EMAIL` (дефолт под проект), подсказка URL для BotFather.
- ✅ Переменные `DEPLOY_USER`, `APP_DIR`, `DOMAIN` (дефолт `moextab.duckdns.org`).
- ✅ `scripts/deploy/bondscreener.service` — uvicorn на `127.0.0.1:8000`, `WorkingDirectory` = корень репозитория, `EnvironmentFile` = `.env`.
- ✅ `scripts/deploy/nginx-bondscreener.conf` — reverse proxy на backend; HTTPS через certbot вручную после проверки HTTP.

### Этап 7: Фидбек + Telegram (операторский бот) ✅
- ✅ SQLite (`BONDS_FEEDBACK_DB_PATH`) и каталог вложений; лимит размера файла `BONDS_FEEDBACK_MAX_ATTACHMENT_BYTES` (дефолт ~5 MiB ≈ средний скриншот × 10).
- ✅ `POST /api/feedback/submit` (multipart: `init_data`, `message`, опционально `file`), `POST /api/feedback/pair` — проверка подписи initData токеном Mini App-бота.
- ✅ `POST /api/telegram/webhook/feedback` — бот фидбека: уведомления в `BONDS_FEEDBACK_NOTIFY_CHAT_IDS`, inline «В архив»/«Удалить» с подтверждением, reply «Архив», команды `/start`, `/pair` для операторов из `BONDS_FEEDBACK_ADMIN_TELEGRAM_IDS`.
- ✅ Зависимость `python-multipart` для загрузки файлов; переменные окружения описаны в `.env.example`.
- ✅ `BONDS_PUBLIC_DOMAIN` / `BONDS_PUBLIC_IPV4` / `BONDS_PUBLIC_IPV6`, `GET /api/public-config`; параметры pairing: `BONDS_FEEDBACK_PAIRING_CODE_LENGTH`, `BONDS_FEEDBACK_PAIRING_CODE_ALPHABET`; nginx `__DOMAIN__` + `client_max_body_size 32m` через `vps-setup.sh`.
