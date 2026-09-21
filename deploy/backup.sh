#!/usr/bin/env bash
# backup.sh — mongodump database KN + arsip uploads ke deploy/backups/, simpan 14 hari (cron harian).
#   bash deploy/backup.sh            → backup sekarang
#   bash deploy/backup.sh restore deploy/backups/kainnusantara-2026-09-07_0230.archive.gz
set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$APP_DIR/deploy/.env"
DEST="$APP_DIR/deploy/backups"
KEEP_DAYS=14
compose() { docker compose --env-file "$ENV_FILE" -f "$APP_DIR/deploy/docker-compose.yml" "$@"; }
DB_NAME="$(grep '^DB_NAME=' "$ENV_FILE" | cut -d= -f2)"

if [ "${1:-}" = "restore" ]; then
  FILE="${2:?berkas arsip wajib}"
  echo "==> restore $FILE → db $DB_NAME (data lama DITIMPA)"
  compose exec -T mongo mongorestore --archive --gzip --drop --nsInclude="$DB_NAME.*" < "$FILE"
  echo "selesai"; exit 0
fi

mkdir -p "$DEST"
STAMP="$(date +%F_%H%M)"
OUT="$DEST/${DB_NAME}-$STAMP.archive.gz"
compose exec -T mongo mongodump --db "$DB_NAME" --archive --gzip > "$OUT"
docker run --rm --volumes-from kn-backend -v "$DEST":/backup alpine \
  tar -czf "/backup/uploads-$STAMP.tar.gz" -C /data uploads 2>/dev/null || true
cp -f "$ENV_FILE" "$DEST/.env.last" && chmod 600 "$DEST/.env.last"
find "$DEST" \( -name "*.archive.gz" -o -name "uploads-*.tar.gz" \) -mtime +$KEEP_DAYS -delete
echo "$(date '+%F %T') backup OK → $OUT ($(du -h "$OUT" | cut -f1))"
