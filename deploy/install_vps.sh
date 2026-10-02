#!/usr/bin/env bash
# Pasang SIPRO di VPS Ubuntu BERSIH (Docker + Caddy HTTPS otomatis + MongoDB 7), mode multi-instance.
#   DOMAIN=hl5.estora.id ACME_EMAIL=email@anda.com INSTANCE=hl5 bash deploy/install_vps.sh
# Instance berikutnya: bash deploy/add_instance.sh <nama> <domain> [--empty]
# VPS yang masih memakai stack lama (deploy/.env) → pakai deploy/migrate_estora.sh, bukan skrip ini.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

[ "$(id -u)" = "0" ] || die "jalankan sebagai root"
[ -f "$DEPLOY_DIR/.env" ] && [ -z "$(inst_list)" ] && die "Stack lama terdeteksi (deploy/.env). Jalankan: bash deploy/migrate_estora.sh"

say "Paket dasar & Docker"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq ca-certificates curl git ufw dnsutils openssl
command -v docker >/dev/null 2>&1 || curl -fsSL https://get.docker.com | sh
docker compose version >/dev/null 2>&1 || die "docker compose plugin tidak tersedia"

say "Firewall (22/80/443)"
ufw allow 22/tcp >/dev/null; ufw allow 80/tcp >/dev/null; ufw allow 443/tcp >/dev/null
ufw --force enable >/dev/null

if [ -z "$(inst_list)" ]; then
  : "${DOMAIN:?set DOMAIN=...}" ; : "${ACME_EMAIL:?set ACME_EMAIL=...}"
  ACME_EMAIL="$ACME_EMAIL" bash "$DEPLOY_DIR/add_instance.sh" "${INSTANCE:-main}" "$DOMAIN"
else
  say "Instance sudah ada — jalankan update"
  bash "$DEPLOY_DIR/update.sh" --no-pull
fi

install_backup_cron
say "SELESAI. Update: cd $REPO_DIR && bash deploy/update.sh"
