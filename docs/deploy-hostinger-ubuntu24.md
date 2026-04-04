# Deploy: Hostinger VPS + Ubuntu 24.04

Это инструкция для деплоя текущего проекта на VPS в Hostinger с Ubuntu 24.04, `systemd`, `nginx` и HTTPS через Certbot.

Проект уже содержит готовые файлы деплоя:

- `scripts/deploy/vps-setup.sh`
- `scripts/deploy/bondscreener.service`
- `scripts/deploy/nginx-bondscreener.conf`

## 1. Подготовить репозиторий и выгрузить его на GitHub из Cursor

### Вариант A. Через терминал внутри Cursor

Открой терминал в Cursor и выполни:

```powershell
cd "E:\BondScreener MOEX"
git init
git add .
git commit -m "Initial commit"
```

Проверь, что `.env` не попал в индекс:

```powershell
git status --short
```

Если на GitHub еще нет репозитория:

1. Открой GitHub.
2. Нажми `New repository`.
3. Укажи имя, например `bondscreener-moex`.
4. Не добавляй `README`, `.gitignore` и license, потому что они уже есть локально.
5. Создай репозиторий.

После этого GitHub покажет команды. Для нового пустого репозитория обычно подходят такие:

```powershell
git branch -M main
git remote add origin https://github.com/USERNAME/bondscreener-moex.git
git push -u origin main
```

Если репозиторий приватный и GitHub попросит авторизацию, удобнее всего войти через встроенный браузер Cursor или использовать Personal Access Token вместо пароля.

### Вариант B. Через Source Control в Cursor

1. Открой вкладку `Source Control`.
2. Нажми `Initialize Repository`, если Git еще не инициализирован.
3. Нажми `+` рядом с изменениями или `Stage All`.
4. Введи сообщение коммита, например `Initial commit`.
5. Нажми `Commit`.
6. Нажми `Publish Branch` или добавь remote вручную и сделай `Push`.

Если удобнее, remote все равно можно добавить через терминал:

```powershell
git remote add origin https://github.com/USERNAME/bondscreener-moex.git
git push -u origin main
```

## 2. Подготовить VPS в Hostinger

В hPanel тебе понадобятся:

- публичный IP сервера
- SSH port
- root password или заранее добавленный SSH key

Рекомендую сразу:

1. Выдать серверу статический домен или поддомен.
2. Добавить SSH key в Hostinger, а не работать только по паролю.
3. Убедиться, что ОС именно Ubuntu 24.04.

## 3. Подключиться к VPS с Windows

Из обычного `cmd` или PowerShell:

```powershell
ssh root@YOUR_SERVER_IP
```

Если порт нестандартный:

```powershell
ssh -p YOUR_SSH_PORT root@YOUR_SERVER_IP
```

При первом подключении подтверди fingerprint и введи пароль.

## 4. Подготовить домен

Если домен находится в Hostinger:

1. Открой `Domains`.
2. Выбери нужный домен.
3. Перейди в `DNS / Nameservers`.
4. Удали старые записи `A`, `AAAA`, `CNAME` для `@` и `www`, если они конфликтуют.
5. Добавь:
   - `A` для `@` -> IP твоего VPS
   - `A` для `www` -> IP твоего VPS

Если используешь схему `A + CNAME`, тогда:

- `A` для `@` -> IP VPS
- `CNAME` для `www` -> твой домен

Проверка с сервера:

```bash
dig A +short your-domain.com
```

DNS может обновляться до 24 часов, но часто начинает работать быстрее.

## 5. Клонировать проект на сервер

На сервере выполни:

```bash
mkdir -p /opt
cd /opt
git clone https://github.com/USERNAME/bondscreener-moex.git bondscreener
cd /opt/bondscreener
```

Если репозиторий приватный, используй один из вариантов:

- `git clone` по SSH через deploy key
- временно HTTPS + Personal Access Token

## 6. Создать `.env` на сервере

Если нужно, сначала скопируй шаблон:

```bash
cd /opt/bondscreener
cp .env.example .env
nano .env
```

Минимально проверь и заполни:

- `BONDS_PUBLIC_DOMAIN=your-domain.com`
- `ALLOWED_HOSTS=your-domain.com,www.your-domain.com,127.0.0.1,localhost`
- `TELEGRAM_BOT_TOKEN=...`
- `TELEGRAM_BOT_USERNAME=...`
- `TELEGRAM_CHAT_ID=...`
- другие обязательные переменные проекта, если они есть в `.env.example`

Если домен будет без `www`, можешь оставить только основной домен и локальные хосты.

## 7. Запустить встроенный deploy-скрипт

В проекте уже есть bootstrap-скрипт под Ubuntu 24.04. На сервере:

```bash
cd /opt/bondscreener
chmod +x scripts/deploy/vps-setup.sh
sudo APP_DIR=/opt/bondscreener DOMAIN=your-domain.com DEPLOY_USER=bondscreener ./scripts/deploy/vps-setup.sh
```

Что он делает:

- ставит Python, `venv`, `pip`, `nginx`, `git`, `ufw`, `nodejs`, `npm`
- создает Linux-пользователя для приложения
- создает `.venv`
- ставит Python-зависимости
- собирает фронтенд
- устанавливает `systemd` unit
- ставит конфиг `nginx`
- включает firewall

## 8. Проверить, что приложение запустилось

Проверки на сервере:

```bash
systemctl status bondscreener --no-pager
journalctl -u bondscreener -n 100 --no-pager
curl -I http://127.0.0.1:8000/
curl -s http://127.0.0.1:8000/api/bonds?limit=1 | head
```

Проверки nginx:

```bash
nginx -t
systemctl status nginx --no-pager
curl -I http://your-domain.com/
```

Если по IP или домену приходит HTML/200, значит backend и proxy уже живы.

## 9. Включить HTTPS

После того как домен уже смотрит на VPS и HTTP открывается, ставим Certbot:

```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d www.your-domain.com --email you@example.com --agree-tos -n
```

Если `www` не используешь:

```bash
sudo certbot --nginx -d your-domain.com --email you@example.com --agree-tos -n
```

Проверка автопродления:

```bash
systemctl status certbot.timer --no-pager
sudo certbot renew --dry-run
```

## 10. Настроить Telegram Mini App

После выпуска HTTPS:

1. Открой `@BotFather`.
2. Выбери своего бота.
3. Открой настройки Mini App или Menu Button.
4. Укажи URL:

```text
https://your-domain.com/
```

Если в проекте используются webhook или публичные callback URL, проверь, что в `.env` указан именно прод-домен.

## 11. Базовые команды сопровождения

### Обновление после новых коммитов

```bash
cd /opt/bondscreener
git pull
.venv/bin/pip install -r requirements.txt
cd frontend
npm ci
npm run build
cd ..
sudo systemctl restart bondscreener
sudo systemctl reload nginx
```

### Смотреть логи

```bash
journalctl -u bondscreener -f
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Перезапуск

```bash
sudo systemctl restart bondscreener
sudo systemctl restart nginx
```

## 12. Что проверить после деплоя

Открой и проверь:

1. `https://your-domain.com/`
2. `https://your-domain.com/api/public-config`
3. `https://your-domain.com/api/bonds?limit=3`
4. открытие фильтров, поиск, индикатор
5. отправку feedback из интерфейса
6. работу Mini App внутри Telegram

## 13. Типичные проблемы

### `502 Bad Gateway`

Обычно значит, что `uvicorn` не поднялся:

```bash
systemctl status bondscreener --no-pager
journalctl -u bondscreener -n 100 --no-pager
```

### Домен не открывается

Проверь:

- правильно ли смотрит `A` запись
- завершилась ли DNS propagation
- открыт ли порт `80/443`
- есть ли корректный `server_name` в nginx

### Не выпускается сертификат

Проверь:

- домен уже должен резолвиться в IP VPS
- `http://your-domain.com/` должен открываться извне
- порты `80` и `443` должны быть открыты

## 14. Рекомендованный порядок действий

Если делать без лишней суеты, то путь такой:

1. Локально сделать первый commit и push на GitHub.
2. На VPS подключиться по SSH.
3. Привязать домен к IP VPS.
4. Склонировать репозиторий в `/opt/bondscreener`.
5. Создать `.env`.
6. Запустить `scripts/deploy/vps-setup.sh`.
7. Проверить HTTP.
8. Выпустить HTTPS через Certbot.
9. Указать HTTPS-домен в BotFather.
10. Проверить приложение в браузере и внутри Telegram.
