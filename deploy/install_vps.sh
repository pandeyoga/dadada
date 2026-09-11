#!/usr/bin/env bash
# Pasang SIPRO di VPS Ubuntu bersih (Docker + Caddy HTTPS otomatis + MongoDB 7).
# Pakai:
#   DOMAIN=app.domain.com ACME_EMAIL=email@anda.com bash deploy/install_vps.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_DIR/deploy"
ENV_FILE="$DEPLOY_DIR/.env"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mGAGAL: %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || die "jalankan sebagai root"

if [ ! -f "$ENV_FILE" ]; then
  : "${DOMAIN:?set DOMAIN=...}" ; : "${ACME_EMAIL:?set ACME_EMAIL=...}"
fi

say "Paket dasar & Docker"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git ufw dnsutils
if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi
docker compose version >/dev/null 2>&1 || die "docker compose plugin tidak tersedia"

say "Firewall (22/80/443)"
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

if [ ! -f "$ENV_FILE" ]; then
  say "Cek DNS $DOMAIN"
  ip_vps="$(curl -fsS https://api.ipify.org || true)"
  ip_dns="$(dig +short "$DOMAIN" | tail -1 || true)"
  [ -n "$ip_dns" ] || die "A record $DOMAIN belum ada"
  [ "$ip_dns" = "$ip_vps" ] || echo "PERINGATAN: DNS $ip_dns != IP VPS $ip_vps (matikan proxy Cloudflare)"

  say "Membuat deploy/.env"
  umask 077
  cat > "$ENV_FILE" <<EOF
COMPOSE_PROJECT_NAME=sipro
DOMAIN=$DOMAIN
ACME_EMAIL=$ACME_EMAIL
DB_NAME=${DB_NAME:-sipro}
DEFAULT_ORG_ID=${DEFAULT_ORG_ID:-org-sipro}
DEFAULT_ORG_NAME=${DEFAULT_ORG_NAME:-SIPRO Developer}
JWT_SECRET=$(openssl rand -hex 48)
PORTAL_MASTER_OTP=$(shuf -i 100000-999999 -n 1)
SUPERADMIN_EMAIL=${SUPERADMIN_EMAIL:-superadmin@sipro.co.id}
SUPERADMIN_PASSWORD=${SUPERADMIN_PASSWORD:-$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-16)}
SEED_DEMO_USERS=true
STORAGE_PROVIDER=mongo
EMERGENT_LLM_KEY=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
META_PIXEL_ID=
EOF
else
  say "deploy/.env sudah ada — dipakai apa adanya"
fi

say "Build & jalankan"
mkdir -p "$DEPLOY_DIR/backups"
cd "$DEPLOY_DIR"
docker compose build --pull
docker compose up -d --remove-orphans

say "Tunggu backend sehat"
for i in $(seq 1 72); do
  status="$(docker compose ps --format '{{.Service}} {{.Health}}' 2>/dev/null | awk '$1=="backend"{print $2}')"
  [ "$status" = "healthy" ] && break
  sleep 5
  [ "$i" = "72" ] && { docker compose logs --tail=80 backend; die "backend tidak sehat"; }
done

DOMAIN_VAL="$(grep '^DOMAIN=' "$ENV_FILE" | cut -d= -f2-)"
say "Tunggu HTTPS $DOMAIN_VAL (Let's Encrypt)"
for i in $(seq 1 40); do
  code="$(curl -fsS -o /dev/null -w '%{http_code}' "https://$DOMAIN_VAL/api/health" || true)"
  [ "$code" = "200" ] && break
  sleep 6
done

say "Cron backup harian 02:00"
CRON_LINE="0 2 * * * bash $DEPLOY_DIR/backup.sh >> /var/log/sipro-backup.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'sipro/deploy/backup.sh' ; echo "$CRON_LINE" ) | crontab -

docker compose ps
echo
echo "SELESAI  ->  https://$DOMAIN_VAL"
echo "Login    ->  $(grep '^SUPERADMIN_EMAIL=' "$ENV_FILE" | cut -d= -f2-) / $(grep '^SUPERADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
echo "Update   ->  cd $REPO_DIR && bash deploy/update.sh"
