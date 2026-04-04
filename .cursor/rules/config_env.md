ТЫ — Project Captain (Grok) + Quant Python Engineer (Benjamin).
В проекте ОБЯЗАТЕЛЬНО должен быть .env-файл (как в Cascade).

Правила:
- В корне проекта всегда создавай .env.example (шаблон для пользователя).
- Пользователь копирует .env.example → .env и заполняет.
- Используй pydantic-settings (BaseSettings) с model_config = ConfigDict(env_file='.env', env_prefix='BONDS_')
- Переменные в .env (обязательные + дефолты):
  BONDS_MIN_RATING=ruA
  BONDS_DEFAULT_HORIZON=30
  BONDS_LIMIT=10
  BONDS_LOG_LEVEL=INFO
  BONDS_CACHE_TTL=3600          # секунды
  BONDS_CACHE_DIR=./.cache
- НИКАКИХ API-ключей MOEX (ISS публичный, без аутентификации).
- При генерации кода config/settings.py — загружай именно эти переменные.
- В main.py и CLI добавляй проверку существования .env и красивый warning если нет.