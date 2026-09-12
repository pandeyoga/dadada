#!/usr/bin/env bash
# Backup / restore MongoDB SIPRO.
#   bash deploy/backup.sh                                  -> buat arsip baru (simpan 14 hari)
#   bash deploy/backup.sh restore deploy/backups/xxx.gz    -> pulihkan arsip
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_DIR="$REPO_DIR/deploy"
ENV_FILE="$DEPLOY_DIR/.env"
BACKUP_DIR="$DEPLOY_DIR/backups"
KEEP_DAYS=14

[ -f "$ENV_FILE" ] || { echo "GAGAL: $ENV_FILE tidak ada"; exit 1; }
DB_NAME="$(grep '^DB_NAME=' "$ENV_FILE" | cut -d= -f2-)"
DB_NAME="${DB_NAME:-sipro}"
mkdir -p "$BACKUP_DIR"
cd "$DEPLOY_DIR"

MONGO_CID="$(docker compose ps -q mongo)"
[ -n "$MONGO_CID" ] || { echo "GAGAL: container mongo tidak jalan"; exit 1; }

if [ "${1:-}" = "restore" ]; then
  ARCHIVE="${2:-}"
  [ -f "$REPO_DIR/$ARCHIVE" ] && ARCHIVE="$REPO_DIR/$ARCHIVE"
  [ -f "$ARCHIVE" ] || { echo "GAGAL: arsip '$2' tidak ditemukan"; exit 1; }
  echo "Memulihkan $ARCHIVE ke DB '$DB_NAME' (data saat ini akan ditimpa)..."
  docker exec -i "$MONGO_CID" mongorestore --archive --gzip --drop \
    --nsInclude="${DB_NAME}.*" < "$ARCHIVE"
  echo "Selesai. Restart backend: cd $DEPLOY_DIR && docker compose restart backend"
  exit 0
fi

STAMP="$(date +%Y-%m-%d_%H%M)"
OUT="$BACKUP_DIR/sipro-${STAMP}.archive.gz"
docker exec "$MONGO_CID" mongodump --db "$DB_NAME" --archive --gzip > "$OUT"
find "$BACKUP_DIR" -name 'sipro-*.archive.gz' -mtime "+$KEEP_DAYS" -delete
echo "Backup: $OUT ($(du -h "$OUT" | cut -f1))"
