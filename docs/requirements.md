# Requirements for BondScreener MOEX

## Общая Информация
- Цель: Парсер/скринер облигаций MOEX за 3-5 сек.
- Фильтр: Мин.рейтинг (default ruA).
- Расчёт: Точная формула (Decimal).
- Вывод: Rich table, топ-10+.

## Формат
- Таблица: 9 колонок, цвета.
- Дисклеймер: Не рекомендация.

## Дополнительно
- Основной веб-канал: Telegram Mini App (`frontend/`), URL в BotFather — HTTPS того же хоста, что и API.

## Фидбек (Mini App + Telegram)
- Отправка из Mini App: `POST /api/feedback/submit` (form: `init_data`, `message`, опционально `file`); подпись `initData` проверяется токеном **бота Mini App**.
- Привязка пользователя к оператору: оператор в боте фидбека `/pair` → одноразовый код; пользователь передаёт код в `POST /api/feedback/pair` (`init_data`, `pairing_code`).
- Операторский бот: webhook `POST /api/telegram/webhook/feedback`, уведомления в чаты из `BONDS_FEEDBACK_NOTIFY_CHAT_IDS`; inline «В архив» / «Удалить» с двойным подтверждением; reply-кнопка «Архив».
- Лимит размера файла задаётся `BONDS_FEEDBACK_MAX_ATTACHMENT_BYTES` (дефолт 25 MiB для Mini App).
- Публичный домен и IP: `BONDS_PUBLIC_DOMAIN`, `BONDS_PUBLIC_IPV4`, `BONDS_PUBLIC_IPV6`; клиент может запросить `GET /api/public-config`.
- Длина и алфавит кода `/pair`: `BONDS_FEEDBACK_PAIRING_CODE_LENGTH`, `BONDS_FEEDBACK_PAIRING_CODE_ALPHABET` (пусто = встроенный набор символов).
