#!/usr/bin/env bash
# install_vps.sh — pasang Kain Nusantara ERP di VPS Ubuntu (22.04/24.04/26.04) SEKALI JALAN.
#
#   DOMAIN=kainnusantara.cloud ACME_EMAIL=pk.yogaswastika@gmail.com bash deploy/install_vps.sh
#
# Docker Compose: MongoDB 7 + FastAPI + React (nginx) + edge HTTPS otomatis (deploy/edge.sh)
# yang TIDAK bentrok dengan proyek lain di VPS (menumpang Caddy/nginx yang sudah ada bila perlu).
# Tanpa pustaka Emergent: emergentintegrations/litellm & @emergentbase/visual-edits dibuang saat build.
# Idempoten: aman dijalankan ulang (rebuild + restart; deploy/.env yang ada tidak ditimpa).
set -euo pipefail

DOMAIN="${DOMAIN:-kainnusantara.cloud}"
ACME_EMAIL="${ACME_EMAIL:-pk.yogaswastika@gmail.com}"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$APP_DIR/deploy/.env"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mXX  %s\033[0m\n' "$*" >&2; exit 1; }
compose() { docker compose --env-file "$ENV_FILE" -f "$APP_DIR/deploy/docker-compose.yml" "$@"; }

[ "$(id -u)" = 0 ] || die "Jalankan sebagai root (ssh root@IP)."
[[ "$DOMAIN" =~ ^[A-Za-z0-9.-]+$ ]] || die "DOMAIN tidak valid: $DOMAIN"

log "1/8 Paket dasar (Ubuntu $(. /etc/os-release && echo "$VERSION_ID"))"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git ufw dnsutils openssl iproute2 python3 >/dev/null
timedatectl set-timezone Asia/Jakarta 2>/dev/null || true

# build frontend (500+ berkas) butuh RAM; tambah swap bila RAM < 4 GB dan belum ada swap
MEM_MB=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
if [ "$MEM_MB" -lt 4000 ] && [ "$(swapon --show --noheadings | wc -l)" = 0 ]; then
  warn "RAM ${MEM_MB} MB < 4 GB → membuat swap 4 GB (/swapfile) agar build frontend tidak 'Killed'."
  fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile >/dev/null && swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

log "2/8 Docker + Compose"
if ! command -v docker >/dev/null 2>&1; then
  apt-get install -y -qq docker.io docker-compose-v2 >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker >/dev/null
if [ ! -f /etc/docker/daemon.json ]; then
  mkdir -p /etc/docker
  echo '{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }' > /etc/docker/daemon.json
  systemctl restart docker
fi
docker compose version >/dev/null 2>&1 || apt-get install -y -qq docker-compose-v2 >/dev/null
echo "docker $(docker --version | cut -d' ' -f3) · $(docker compose version --short)"

log "3/8 Firewall (SSH, 80, 443) — aturan yang sudah ada tidak dihapus"
ufw allow OpenSSH >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null
ufw status | sed -n 1,6p

log "4/8 Cek DNS"
SERVER_IP="$(curl -fsS4 --max-time 8 https://api.ipify.org || hostname -I | awk '{print $1}')"
DNS_IP="$(dig +short A "$DOMAIN" @1.1.1.1 | tail -n1 || true)"
if [ "$DNS_IP" = "$SERVER_IP" ]; then echo "OK: $DOMAIN → $SERVER_IP"; else
  warn "DNS $DOMAIN → '${DNS_IP:-kosong}', IP server $SERVER_IP. HTTPS gagal sampai A record benar (tanpa proxy Cloudflare). Instalasi dilanjutkan."
fi
EXTRA_HOSTS=""
WWW_IP="$(dig +short A "www.$DOMAIN" @1.1.1.1 | tail -n1 || true)"
if [ "$WWW_IP" = "$SERVER_IP" ]; then EXTRA_HOSTS="www.$DOMAIN"; echo "OK: www.$DOMAIN → $SERVER_IP (ikut dilayani)"; else
  echo "www.$DOMAIN tidak mengarah ke server ini → dilewati (tambahkan A record lalu jalankan ulang skrip bila ingin www)."
fi

log "5/8 Berkas deploy/.env (rahasia dibuat otomatis, tidak ditimpa bila sudah ada)"
if [ -f "$ENV_FILE" ]; then
  echo "Memakai $ENV_FILE yang sudah ada."
  sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|; s|^ACME_EMAIL=.*|ACME_EMAIL=$ACME_EMAIL|; s|^EXTRA_HOSTS=.*|EXTRA_HOSTS=$EXTRA_HOSTS|" "$ENV_FILE"
  grep -q '^EXTRA_HOSTS=' "$ENV_FILE" || echo "EXTRA_HOSTS=$EXTRA_HOSTS" >> "$ENV_FILE"
else
  # port loopback untuk kn-web: cari yang bebas mulai 18080 supaya tidak bentrok proyek lain
  PORT=18080; while ss -Hltn "sport = :$PORT" | grep -q .; do PORT=$((PORT+1)); done
  {
    echo "DOMAIN=$DOMAIN"
    echo "EXTRA_HOSTS=$EXTRA_HOSTS"
    echo "ACME_EMAIL=$ACME_EMAIL"
    echo "DB_NAME=kainnusantara"
    echo "KN_WEB_PORT=$PORT"
    echo "ADMIN_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"
  } > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Dibuat: $ENV_FILE"
fi
# CORS mengikuti host yang dilayani (T-02: backend menolak start bila CORS_ORIGINS kosong/'*')
CORS="https://$DOMAIN${EXTRA_HOSTS:+,https://$EXTRA_HOSTS}"
grep -q '^CORS_ORIGINS=' "$ENV_FILE" && sed -i "s|^CORS_ORIGINS=.*|CORS_ORIGINS=$CORS|" "$ENV_FILE" || echo "CORS_ORIGINS=$CORS" >> "$ENV_FILE"

log "6/8 Build & jalankan (build pertama ±5–10 menit)"
compose build --pull
compose up -d --remove-orphans mongo backend web

echo -n "Menunggu backend sehat (bootstrap awal 1–3 menit) "
for _ in $(seq 1 90); do
  if compose exec -T backend curl -fsS http://127.0.0.1:8001/api/ >/dev/null 2>&1; then echo " OK"; break; fi
  echo -n "."; sleep 4
done
compose exec -T backend curl -fsS http://127.0.0.1:8001/api/ >/dev/null 2>&1 \
  || { compose logs --tail=60 backend; die "Backend belum sehat — lihat log di atas."; }

# akun demo bawaan bootstrap memakai sandi 'demo12345' → ganti sandi admin dengan yang acak (idempoten)
ADMIN_PASSWORD="$(grep '^ADMIN_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
if [ -n "$ADMIN_PASSWORD" ]; then
  compose exec -T -e ADMIN_PASSWORD="$ADMIN_PASSWORD" backend python - <<'PY' || warn "Gagal mengganti sandi admin — ganti lewat UI (Admin → Pengguna)."
import asyncio, os
from db import db
from core_utils import hash_password
async def main():
    r = await db.users.update_one({"email": "admin@kainnusantara.id"}, {"$set": {"password_hash": hash_password(os.environ["ADMIN_PASSWORD"])}})
    print("sandi admin@kainnusantara.id diperbarui" if r.matched_count else "akun admin belum ada")
asyncio.run(main())
PY
fi

log "7/8 Edge HTTPS (deteksi proyek lain di port 80/443)"
bash "$APP_DIR/deploy/edge.sh"

echo -n "Menunggu HTTPS $DOMAIN "
HTTPS_OK=0
for _ in $(seq 1 30); do
  if curl -fsS --max-time 8 "https://$DOMAIN/api/" >/dev/null 2>&1; then HTTPS_OK=1; echo " OK"; break; fi
  echo -n "."; sleep 5
done
[ "$HTTPS_OK" = 1 ] || warn "HTTPS belum aktif — biasanya DNS belum propagasi. Cek: bash $APP_DIR/deploy/edge.sh (ulang) atau log proxy."

log "8/8 Backup MongoDB harian (02:30 WIB, simpan 14 hari)"
chmod +x "$APP_DIR/deploy/"*.sh
cat > /etc/cron.d/kainnusantara-backup <<CRON
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 2 * * * root $APP_DIR/deploy/backup.sh >> /var/log/kainnusantara-backup.log 2>&1
CRON
chmod 644 /etc/cron.d/kainnusantara-backup

EDGE_MODE="$(grep '^EDGE_MODE=' "$ENV_FILE" | cut -d= -f2)"
cat <<SUMMARY

==================================================================
 Kain Nusantara ERP terpasang.
   URL            : https://$DOMAIN${EXTRA_HOSTS:+  (juga https://$EXTRA_HOSTS)}
   Login admin    : admin@kainnusantara.id / ${ADMIN_PASSWORD:-demo12345}
   Akun demo lain : md@ · manager@ · sales@ · finance@ ... @kainnusantara.id / demo12345
                    → GANTI SANDI semua akun demo lewat Admin → Pengguna sebelum dipakai.
   Edge HTTPS     : $EDGE_MODE (sertifikat Let's Encrypt diperbarui otomatis; email $ACME_EMAIL)
   Folder app     : $APP_DIR
   Rahasia        : $ENV_FILE  (backup berkas ini)

 Perintah harian:
   Update kode    : cd $APP_DIR && bash deploy/update.sh
   Log            : cd $APP_DIR/deploy && docker compose logs -f backend
   Status         : cd $APP_DIR/deploy && docker compose ps
   Backup manual  : bash $APP_DIR/deploy/backup.sh
   Sambung edge   : bash $APP_DIR/deploy/edge.sh   (ulang bila proyek lain menimpa Caddyfile-nya)
==================================================================
SUMMARY
