#!/usr/bin/env bash
# update.sh — tarik kode terbaru dari GitHub, rebuild image, restart tanpa menghapus data.
#   cd /opt/kainnusantara && bash deploy/update.sh
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$APP_DIR/deploy/.env"
compose() { docker compose --env-file "$ENV_FILE" -f "$APP_DIR/deploy/docker-compose.yml" "$@"; }
cd "$APP_DIR"

echo "==> git sync ke origin"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
git fetch origin "$BRANCH"
# reset --hard, bukan pull --ff-only: riwayat di GitHub bisa ditulis ulang (force push).
# Berkas yang tidak ter-track (deploy/.env, deploy/backups) tidak tersentuh.
git reset --hard "origin/$BRANCH"

echo "==> build & restart"
compose build --pull
compose up -d --remove-orphans mongo backend web
docker image prune -f >/dev/null

echo -n "==> menunggu backend "
OK=0
for _ in $(seq 1 60); do
  if compose exec -T backend curl -fsS http://127.0.0.1:8001/api/ >/dev/null 2>&1; then OK=1; echo "OK"; break; fi
  echo -n "."; sleep 4
done
[ "$OK" = 1 ] || { compose logs --tail=60 backend; echo "Backend belum sehat — periksa log di atas." >&2; exit 1; }

echo "==> pastikan edge HTTPS masih tersambung"
bash "$APP_DIR/deploy/edge.sh"
