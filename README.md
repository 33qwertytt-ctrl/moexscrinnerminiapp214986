# BondScreener MOEX

Deploy на Hostinger VPS с Ubuntu 24.04:

- `docs/deploy-hostinger-ubuntu24.md`

Локальный запуск через `cmd`:

```cmd
cd /d E:\BondScreener MOEX
.venv\Scripts\python.exe -m pip install -r requirements.txt
cd /d E:\BondScreener MOEX\frontend
cmd /c npm install
cmd /c npm run build
cd /d E:\BondScreener MOEX
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

CLI режим:

```cmd
cd /d E:\BondScreener MOEX
.venv\Scripts\python.exe main.py --limit 20
```

Проверки:

```cmd
cd /d E:\BondScreener MOEX
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m mypy .
.venv\Scripts\python.exe -m pytest
cd /d E:\BondScreener MOEX\frontend
cmd /c npm test
```
