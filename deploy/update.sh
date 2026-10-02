#!/usr/bin/env bash
# Update SIPRO di VPS: tarik kode baru → build image SEKALI → ganti container tiap instance → reload Caddy.
# Data (volume mongo), sertifikat (caddy) dan env instance TIDAK disentuh. Backup otomatis sebelum update.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if [ "${1:-}" != "--no-pull" ]; then
  say "Tarik kode terbaru dari GitHub"
  cd "$REPO_DIR"
  git fetch --all --prune
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
  git reset --hard "origin/$BRANCH"
  git log --oneline -1
  exec bash "$DEPLOY_DIR/update.sh" --no-pull
fi

# ---- Mode lama (satu domain, deploy/.env + docker-compose.yml) — sebelum migrate_estora.sh dijalankan
if [ -z "$(inst_list)" ]; then
  ENV_FILE="$DEPLOY_DIR/.env"
  [ -f "$ENV_FILE" ] || die "Belum terpasang. Jalankan deploy/install_vps.sh"
  warn "Masih stack lama satu domain. Untuk pindah ke estora.id: bash deploy/migrate_estora.sh"
  grep -q '^COMPOSE_PROJECT_NAME=' "$ENV_FILE" || printf '\nCOMPOSE_PROJECT_NAME=sipro\n' >> "$ENV_FILE"
  cd "$DEPLOY_DIR"
  docker compose build --pull
  docker compose up -d --remove-orphans
  for i in $(seq 1 60); do
    status="$(docker compose ps --format '{{.Service}} {{.Health}}' 2>/dev/null | awk '$1=="backend"{print $2}')"
    [ "$status" = "healthy" ] && break
    sleep 5
    [ "$i" = "60" ] && { docker compose logs --tail=60 backend; die "backend tidak sehat setelah 5 menit"; }
  done
  docker compose ps
  docker image prune -f >/dev/null 2>&1 || true
  say "Selesai. Buka https://$(envget "$ENV_FILE" DOMAIN)"
  exit 0
fi

# ---- Mode multi-instance
say "Backup semua instance sebelum update"
bash "$DEPLOY_DIR/backup.sh" || warn "backup gagal — update tetap dilanjutkan"

FIRST="$(inst_list | head -1)"
say "Build image (sekali untuk semua instance)"
dc "$FIRST" build --pull

for inst in $(inst_list); do
  say "Ganti container '$inst'"
  dc "$inst" up -d --no-build --remove-orphans
  wait_healthy "$inst" 6 || die "backend '$inst' tidak sehat — instance lain belum diupdate"
done

say "Reload Caddy"
edge_up
docker image prune -f >/dev/null 2>&1 || true

say "Selesai"
for inst in $(inst_list); do echo "  $inst → https://$(envget "$(inst_env "$inst")" DOMAIN)"; done
