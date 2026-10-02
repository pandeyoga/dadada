#!/usr/bin/env bash
# Backup / restore MongoDB SIPRO.
#   bash deploy/backup.sh                              -> backup SEMUA instance (simpan 14 hari)
#   bash deploy/backup.sh hl5                          -> backup satu instance
#   bash deploy/backup.sh restore hl5 <arsip.gz>       -> pulihkan arsip ke instance (data saat ini ditimpa)
# Stack lama (sebelum migrasi): bash deploy/backup.sh [restore <arsip.gz>]
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
KEEP_DAYS=14
STAMP="$(date +%Y-%m-%d_%H%M)"

backup_cid() {  # backup_cid <container> <db> <folder> <prefix>
  mkdir -p "$3"
  local out="$3/$4-${STAMP}.archive.gz"
  docker exec "$1" mongodump --db "$2" --archive --gzip > "$out"
  gzip -t "$out" || die "arsip $out rusak"
  find "$3" -maxdepth 1 -name "$4-*.archive.gz" -mtime "+$KEEP_DAYS" -delete
  echo "Backup: $out ($(du -h "$out" | cut -f1))"
}

restore_cid() {  # restore_cid <container> <db> <arsip>
  local archive="$3"
  [ -f "$REPO_DIR/$archive" ] && archive="$REPO_DIR/$archive"
  [ -f "$archive" ] || die "arsip '$3' tidak ditemukan"
  echo "Memulihkan $archive ke DB '$2' (data saat ini akan ditimpa)..."
  docker exec -i "$1" mongorestore --archive --gzip --drop --nsInclude="${2}.*" < "$archive"
}

# ---- Stack lama
if [ -z "$(inst_list)" ]; then
  ENV_FILE="$DEPLOY_DIR/.env"
  [ -f "$ENV_FILE" ] || die "$ENV_FILE tidak ada"
  DB_NAME="$(envget "$ENV_FILE" DB_NAME)"; DB_NAME="${DB_NAME:-sipro}"
  cd "$DEPLOY_DIR"
  CID="$(docker compose ps -q mongo)"; [ -n "$CID" ] || die "container mongo tidak jalan"
  if [ "${1:-}" = "restore" ]; then
    restore_cid "$CID" "$DB_NAME" "${2:-}"; echo "Restart backend: cd $DEPLOY_DIR && docker compose restart backend"
  else
    backup_cid "$CID" "$DB_NAME" "$DEPLOY_DIR/backups" sipro
  fi
  exit 0
fi

# ---- Multi-instance
if [ "${1:-}" = "restore" ]; then
  INST="${2:-}"; [ -f "$(inst_env "$INST")" ] || die "pakai: backup.sh restore <instance> <arsip.gz>"
  CID="$(dc "$INST" ps -q mongo)"; [ -n "$CID" ] || die "mongo '$INST' tidak jalan"
  restore_cid "$CID" "$(envget "$(inst_env "$INST")" DB_NAME)" "${3:-}"
  dc "$INST" restart backend
  exit 0
fi

TARGETS="${1:-$(inst_list)}"
for inst in $TARGETS; do
  [ -f "$(inst_env "$inst")" ] || die "instance '$inst' tidak ada"
  CID="$(dc "$inst" ps -q mongo)"
  [ -n "$CID" ] || { warn "mongo '$inst' tidak jalan — dilewati"; continue; }
  backup_cid "$CID" "$(envget "$(inst_env "$inst")" DB_NAME)" "$DEPLOY_DIR/backups/$inst" "sipro-$inst"
done
