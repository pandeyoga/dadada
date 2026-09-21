#!/usr/bin/env bash
# edge.sh — sambungkan Kain Nusantara ke port 80/443 TANPA bentrok dengan proyek lain di VPS.
# Dipanggil install_vps.sh dan update.sh; aman dijalankan ulang (idempoten).
#
# Deteksi otomatis siapa yang memegang port 80/443:
#   kosong                → jalankan Caddy milik KN (profil `edge`, HTTPS otomatis)     [EDGE_MODE=caddy]
#   container Caddy lain  → tambahkan blok situs KN ke Caddyfile-nya + sambung jaringan [EDGE_MODE=attach]
#   nginx di host         → vhost nginx + certbot (auto-renew via certbot.timer)        [EDGE_MODE=nginx]
#   lainnya               → berhenti dengan pesan jelas (tidak mengubah apa pun)
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$APP_DIR/deploy/.env"
[ -f "$ENV_FILE" ] || { echo "deploy/.env belum ada — jalankan install_vps.sh" >&2; exit 1; }
# shellcheck disable=SC1090
set -a; . "$ENV_FILE"; set +a
KN_WEB_PORT="${KN_WEB_PORT:-18080}"
HOSTS="$DOMAIN${EXTRA_HOSTS:+ $EXTRA_HOSTS}"
MARK_BEGIN="# >>> kainnusantara (KN) — dikelola deploy/edge.sh, jangan ubah manual >>>"
MARK_END="# <<< kainnusantara (KN) <<<"

log() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!!  %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mXX  %s\033[0m\n' "$*" >&2; exit 1; }
save_mode() { grep -q '^EDGE_MODE=' "$ENV_FILE" && sed -i "s|^EDGE_MODE=.*|EDGE_MODE=$1|" "$ENV_FILE" || echo "EDGE_MODE=$1" >> "$ENV_FILE"; }
compose() { docker compose --env-file "$ENV_FILE" -f "$APP_DIR/deploy/docker-compose.yml" "$@"; }

# ── siapa yang memegang :80 / :443 ────────────────────────────────────────────
port_owner() { ss -Hltnp "sport = :$1" 2>/dev/null | grep -oE 'users:\(\("[^"]+"' | head -n1 | sed -E 's/users:\(\("//'; }
OWNER80="$(port_owner 80 || true)"; OWNER443="$(port_owner 443 || true)"
KN_CADDY_ID="$(docker ps -q --filter name='^kn-caddy$' || true)"
OTHER_DOCKER="$(docker ps --filter publish=80 --filter publish=443 --format '{{.Names}}|{{.Image}}' | grep -v '^kn-caddy|' | head -n1 || true)"

if [ -n "$KN_CADDY_ID" ] || { [ -z "$OWNER80" ] && [ -z "$OWNER443" ]; }; then
  MODE=caddy
elif [ -n "$OTHER_DOCKER" ]; then
  case "$OTHER_DOCKER" in
    *caddy*) MODE=attach ;;
    *) die "Port 80/443 dipegang container '$OTHER_DOCKER' (bukan Caddy). Tambahkan reverse proxy ke http://127.0.0.1:$KN_WEB_PORT untuk host $HOSTS secara manual." ;;
  esac
elif [ "$OWNER80" = nginx ] || [ "$OWNER443" = nginx ]; then
  MODE=nginx
else
  die "Port 80/443 dipegang '$OWNER80/$OWNER443'. Tambahkan reverse proxy ke http://127.0.0.1:$KN_WEB_PORT untuk host $HOSTS secara manual."
fi

case "$MODE" in
# ── A. tidak ada proxy lain → Caddy milik KN ──────────────────────────────────
caddy)
  log "Edge: Caddy milik KN (port 80/443 bebas) — HTTPS Let's Encrypt otomatis, email $ACME_EMAIL"
  compose --profile edge up -d --remove-orphans caddy
  save_mode caddy
  ;;

# ── B. Caddy proyek lain memegang 80/443 → tumpangi (tambah blok situs) ───────
attach)
  CADDY_NAME="${OTHER_DOCKER%%|*}"
  log "Edge: menumpang Caddy '$CADDY_NAME' milik proyek lain (tanpa mengganggu situsnya)"
  CADDYFILE="$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/etc/caddy/Caddyfile"}}{{.Source}}{{end}}{{end}}' "$CADDY_NAME")"
  [ -n "$CADDYFILE" ] && [ -f "$CADDYFILE" ] || die "Caddyfile '$CADDY_NAME' tidak ditemukan sebagai bind-mount host; tambahkan blok situs $HOSTS → reverse_proxy kn-web:80 secara manual."
  # sambungkan container Caddy ke jaringan `kn` supaya bisa memanggil kn-web
  docker network connect kn "$CADDY_NAME" 2>/dev/null || true
  # tulis blok di antara marker; ditulis IN-PLACE (inode tetap) agar bind-mount container ikut berubah
  BLOCK="$MARK_BEGIN
$(echo "$HOSTS" | sed 's/ /, /g') {
    encode zstd gzip
    request_body {
        max_size 50MB
    }
    reverse_proxy kn-web:80 {
        header_up X-Forwarded-Proto {scheme}
        transport http {
            read_timeout 300s
        }
    }
}
$MARK_END"
  python3 - "$CADDYFILE" "$MARK_BEGIN" "$MARK_END" "$BLOCK" <<'PY'
import re, sys
path, b, e, block = sys.argv[1:5]
src = open(path, encoding="utf-8").read()
src = re.sub(re.escape(b) + r".*?" + re.escape(e) + r"\n?", "", src, flags=re.S).rstrip("\n")
with open(path, "w", encoding="utf-8") as f:
    f.write(src + "\n\n" + block + "\n")
PY
  docker exec "$CADDY_NAME" caddy validate --config /etc/caddy/Caddyfile >/dev/null
  docker exec "$CADDY_NAME" caddy reload --config /etc/caddy/Caddyfile
  echo "Blok $HOSTS ditambahkan ke $CADDYFILE dan Caddy di-reload (sertifikat + auto-renew diurus Caddy tersebut)."
  warn "Bila proyek lain menjalankan 'git reset --hard'/update yang menimpa Caddyfile-nya, jalankan lagi: bash $APP_DIR/deploy/edge.sh"
  save_mode attach
  ;;

# ── C. nginx di host → vhost + certbot ────────────────────────────────────────
nginx)
  log "Edge: nginx host — vhost $HOSTS → 127.0.0.1:$KN_WEB_PORT + certbot (auto-renew certbot.timer)"
  export DEBIAN_FRONTEND=noninteractive
  apt-get install -y -qq certbot python3-certbot-nginx >/dev/null
  SITE=/etc/nginx/sites-available/kainnusantara
  cat > "$SITE" <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $HOSTS;
    client_max_body_size 50m;
    location / {
        proxy_pass http://127.0.0.1:$KN_WEB_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINX
  ln -sf "$SITE" /etc/nginx/sites-enabled/kainnusantara
  nginx -t && systemctl reload nginx
  # shellcheck disable=SC2086
  certbot --nginx --non-interactive --agree-tos --redirect -m "$ACME_EMAIL" $(for h in $HOSTS; do printf ' -d %s' "$h"; done) \
    || warn "certbot gagal (DNS belum mengarah?). Situs sudah aktif di HTTP; ulangi: bash $APP_DIR/deploy/edge.sh"
  systemctl enable --now certbot.timer >/dev/null 2>&1 || true
  save_mode nginx
  ;;
esac
