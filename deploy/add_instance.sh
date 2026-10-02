#!/usr/bin/env bash
# Tambah instance SIPRO baru (domain + database sendiri) ke VPS multi-instance.
#   bash deploy/add_instance.sh <nama> <domain> [--empty] [--no-demo-users] [--org-name "Nama PT"]
#   contoh: bash deploy/add_instance.sh demo demo.estora.id --empty
#     --empty          database dimulai kosong (akun + konfigurasi saja, tanpa data contoh)
#     --no-demo-users  hanya akun Super Admin (tanpa akun demo per peran)
# Aman diulang: env yang sudah ada TIDAK ditimpa, data tidak disentuh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

NAME="${1:-}"; DOMAIN="${2:-}"
[ -n "$NAME" ] && [ -n "$DOMAIN" ] || die "pakai: bash deploy/add_instance.sh <nama> <domain> [--empty] [--no-demo-users]"
[[ "$NAME" =~ ^[a-z][a-z0-9]{1,19}$ ]] || die "nama instance harus huruf kecil/angka (mis. demo, trial)"
shift 2
START_EMPTY=false; DEMO_USERS=true; ORG_NAME="SIPRO Developer"
while [ $# -gt 0 ]; do
  case "$1" in
    --empty) START_EMPTY=true ;;
    --no-demo-users) DEMO_USERS=false ;;
    --org-name) ORG_NAME="$2"; shift ;;
    *) die "opsi tidak dikenal: $1" ;;
  esac
  shift
done

[ -f "$EDGE_ENV" ] || { [ -n "${ACME_EMAIL:-}" ] || die "set ACME_EMAIL=... (belum ada $EDGE_ENV)"; mkdir -p "$EDGE_DIR"; printf 'ACME_EMAIL=%s\n' "$ACME_EMAIL" > "$EDGE_ENV"; }
mkdir -p "$INST_DIR"; chmod 700 "$INST_DIR"
ENV_FILE="$(inst_env "$NAME")"

for other in $(inst_list); do
  [ "$other" = "$NAME" ] && continue
  [ "$(envget "$(inst_env "$other")" DOMAIN)" = "$DOMAIN" ] && die "domain $DOMAIN sudah dipakai instance '$other'"
done

if [ -f "$ENV_FILE" ]; then
  say "Instance '$NAME' sudah ada — env dipakai apa adanya (tidak ditimpa)"
else
  say "Membuat $ENV_FILE"
  umask 077
  cat > "$ENV_FILE" <<EOF
INSTANCE=$NAME
COMPOSE_PROJECT_NAME=sipro_$NAME
DOMAIN=$DOMAIN
REDIRECT_FROM=
DB_NAME=sipro
DEFAULT_ORG_ID=org-sipro
DEFAULT_ORG_NAME=$ORG_NAME
JWT_SECRET=$(openssl rand -hex 48)
PORTAL_MASTER_OTP=$(shuf -i 100000-999999 -n 1)
SUPERADMIN_EMAIL=superadmin@sipro.co.id
SUPERADMIN_PASSWORD=$(openssl rand -base64 12 | tr -d '/+=' | cut -c1-16)
SEED_DEMO_USERS=$DEMO_USERS
START_EMPTY=$START_EMPTY
STORAGE_PROVIDER=mongo
EMERGENT_LLM_KEY=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
META_PIXEL_ID=
EOF
fi

dns_ok "$DOMAIN" || warn "Instance tetap dijalankan; HTTPS aktif otomatis begitu DNS $DOMAIN mengarah ke VPS."

ensure_edge_infra
if ! docker image inspect sipro-app-backend:latest >/dev/null 2>&1 || ! docker image inspect sipro-app-frontend:latest >/dev/null 2>&1; then
  say "Build image (sekali untuk semua instance)"
  dc "$NAME" build --pull
fi

say "Jalankan instance '$NAME'"
dc "$NAME" up -d --no-build --remove-orphans
wait_healthy "$NAME" 8 || die "backend '$NAME' tidak sehat"

say "Daftarkan $DOMAIN ke Caddy"
edge_up
https_ok "$DOMAIN" 20 || true

echo
echo "Instance '$NAME' → https://$DOMAIN"
echo "  Super Admin : $(envget "$ENV_FILE" SUPERADMIN_EMAIL) / $(envget "$ENV_FILE" SUPERADMIN_PASSWORD)"
[ "$(envget "$ENV_FILE" SEED_DEMO_USERS)" = "true" ] && \
  echo "  Akun demo   : owner@, manager@, marketing@, sales@, sales2@, finance@, pm@, site@sipro.co.id / Sipro#2026 (SEGERA ganti sandinya)"
