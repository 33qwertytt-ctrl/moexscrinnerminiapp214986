#!/usr/bin/env bash
# BondScreener MOEX — первичная настройка Ubuntu 24.04 (Hostinger VPS)
# Запуск на сервере от пользователя с sudo:
#   chmod +x vps-setup.sh && ./vps-setup.sh
#
# Перед запуском задайте переменные ниже (или экспортируйте их в shell).

set -euo pipefail

# --- Обязательно отредактируйте ---
# Пользователь Linux, от имени которого будет работать приложение (создастся, если нет)
DEPLOY_USER="${DEPLOY_USER:-bondscreener}"
# Каталог с кодом на VPS (репозиторий должен быть уже склонирован сюда)
APP_DIR="${APP_DIR:-/opt/bondscreener}"
# Домен (DuckDNS → статический IP VPS); в BotFather укажите HTTPS URL этого домена как Mini App
DOMAIN="${DOMAIN:-moextab.duckdns.org}"
# Если в репозитории уже есть .env с BONDS_PUBLIC_DOMAIN — подставить в DOMAIN
if [[ -f "${APP_DIR}/.env" ]]; then
  _dom_line="$(grep -E '^BONDS_PUBLIC_DOMAIN=' "${APP_DIR}/.env" 2>/dev/null | tail -n1 || true)"
  if [[ -n "${_dom_line}" ]]; then
    DOMAIN="${_dom_line#BONDS_PUBLIC_DOMAIN=}"
    DOMAIN="${DOMAIN//$'\r'/}"
    DOMAIN="${DOMAIN//\"/}"
  fi
fi
# Пример репозитория (может быть приватным — используйте SSH или deploy key)
GIT_REPO_EXAMPLE="${GIT_REPO_EXAMPLE:-https://github.com/33qwertytt-ctrl/moexscrinnerminiapp214987.git}"

# --- Опционально ---
# Email для Let's Encrypt (certbot)
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-33qwertytt@gmail.com}"
# Токен DuckDNS (нужен только если на VPS ставите ddclient/cron для обновления IP)
DUCKDNS_TOKEN="${DUCKDNS_TOKEN:-}"
DUCKDNS_SUBDOMAIN="${DUCKDNS_SUBDOMAIN:-moextab}"

log() { echo "[$(date -Iseconds)] $*"; }

if [[ "$(id -u)" -ne 0 ]]; then
  log "Запустите скрипт с sudo."
  exit 1
fi

log "Обновление пакетов..."
apt-get update -y
apt-get install -y python3.12 python3.12-venv python3-pip nginx git ufw curl nodejs npm

log "Пользователь ${DEPLOY_USER}..."
if ! id -u "${DEPLOY_USER}" &>/dev/null; then
  useradd --system --create-home --shell /bin/bash "${DEPLOY_USER}"
fi

if [[ ! -d "${APP_DIR}" ]]; then
  log "Каталог ${APP_DIR} не найден."
  log "Склонируйте репозиторий вручную, например:"
  log "  sudo mkdir -p $(dirname "${APP_DIR}") && sudo git clone ${GIT_REPO_EXAMPLE} ${APP_DIR}"
  log "  sudo chown -R ${DEPLOY_USER}:${DEPLOY_USER} ${APP_DIR}"
  exit 1
fi

chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${APP_DIR}"

log "Python venv и зависимости..."
sudo -u "${DEPLOY_USER}" bash <<EOF
set -euo pipefail
cd "${APP_DIR}"
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
cd "${APP_DIR}/frontend"
if [[ -f package-lock.json ]]; then
  npm ci
else
  npm install
fi
npm run build
EOF

if [[ ! -f "${APP_DIR}/.env" ]]; then
  log "Нет .env: копирую из .env.example (в репозитории обычно уже есть .env из git — тогда этот шаг пропускается)."
  sudo -u "${DEPLOY_USER}" cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
fi

SERVICE_SRC="${APP_DIR}/scripts/deploy/bondscreener.service"
if [[ ! -f "${SERVICE_SRC}" ]]; then
  log "Не найден ${SERVICE_SRC}. Убедитесь, что в ${APP_DIR} полная копия репозитория."
  exit 1
fi

log "Установка systemd unit..."
TMP_UNIT="$(mktemp)"
sed -e "s|DEPLOY_USER|${DEPLOY_USER}|g" \
    -e "s|DEPLOY_APP_DIR|${APP_DIR}|g" \
    "${SERVICE_SRC}" > "${TMP_UNIT}"
install -m 0644 "${TMP_UNIT}" /etc/systemd/system/bondscreener.service
rm -f "${TMP_UNIT}"

systemctl daemon-reload
systemctl enable bondscreener
systemctl restart bondscreener

log "Nginx..."
NGX_SRC="${APP_DIR}/scripts/deploy/nginx-bondscreener.conf"
if [[ -f "${NGX_SRC}" ]]; then
  TMP_NGX="$(mktemp)"
  sed -e "s|__DOMAIN__|${DOMAIN}|g" "${NGX_SRC}" > "${TMP_NGX}"
  install -m 0644 "${TMP_NGX}" /etc/nginx/sites-available/bondscreener
  rm -f "${TMP_NGX}"
  ln -sf /etc/nginx/sites-available/bondscreener /etc/nginx/sites-enabled/bondscreener
  if [[ -L /etc/nginx/sites-enabled/default ]]; then
    rm -f /etc/nginx/sites-enabled/default
  fi
  nginx -t
  systemctl reload nginx
else
  log "Пропуск nginx: нет ${NGX_SRC}"
fi

log "UFW: открываю 22, 80, 443..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable || true

log "Готово. Проверка: curl -sS http://127.0.0.1:8000/api/bonds?limit=1 | head"
sudo -u "${DEPLOY_USER}" curl -sS "http://127.0.0.1:8000/api/bonds?limit=1" | head -c 200 || true
echo

log "Сайт по домену: http://${DOMAIN}/"
log "HTTPS: sudo apt install -y certbot python3-certbot-nginx"
if [[ -n "${LETSENCRYPT_EMAIL}" ]]; then
  log "      sudo certbot --nginx -d ${DOMAIN} --email ${LETSENCRYPT_EMAIL} --agree-tos -n"
else
  log "      sudo certbot --nginx -d ${DOMAIN}"
fi
log "В @BotFather → Bot → Menu Button / Mini App укажите: https://${DOMAIN}/"

if [[ -n "${DUCKDNS_TOKEN}" ]]; then
  log "DUCKDNS_TOKEN задан: настройте обновление IP на https://www.duckdns.org/ (install, cron или ddclient), subdomain=${DUCKDNS_SUBDOMAIN}"
fi

log "Статус сервиса: systemctl status bondscreener --no-pager"
