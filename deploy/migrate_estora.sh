#!/usr/bin/env bash
# Migrasi SATU KALI: stack lama satu-domain (hl5.portalsipro.com) → multi-instance estora.id
#   - hl5.portalsipro.com  → hl5.estora.id  (database, file, akun & sesi JWT TETAP sama)
#   - hl5.portalsipro.com tetap hidup: dialihkan 308 ke hl5.estora.id (webhook /api/webhooks/* dilayani langsung)
#   - demo.estora.id & trial.estora.id: instance baru, database kosong + akun demo per peran
#
#   bash deploy/migrate_estora.sh             → jalankan migrasi (aman diulang)
#   bash deploy/migrate_estora.sh rollback    → kembali ke stack lama / domain lama (DATA TIDAK DIHAPUS)
#
# Variabel opsional: NEW_DOMAIN, MAIN_INST, EXTRA_INSTANCES="demo:demo.estora.id trial:trial.estora.id",
#                    ASSUME_YES=1 (tanpa konfirmasi), FORCE_DNS=1 (lanjut walau DNS hl5 belum benar)
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

NEW_DOMAIN="${NEW_DOMAIN:-hl5.estora.id}"
MAIN_INST="${MAIN_INST:-hl5}"
EXTRA_INSTANCES="${EXTRA_INSTANCES:-demo:demo.estora.id trial:trial.estora.id}"
LEGACY_ENV="$DEPLOY_DIR/.env"
LEGACY_BAK="$DEPLOY_DIR/.env.legacy"
LEGACY_COMPOSE="$DEPLOY_DIR/docker-compose.yml"
STAMP="$(date +%Y-%m-%d_%H%M%S)"
MIG_DIR="$DEPLOY_DIR/backups/migrasi-estora-$STAMP"

[ "$(id -u)" = "0" ] || die "jalankan sebagai root"
command -v docker >/dev/null 2>&1 || die "docker tidak terpasang"
command -v dig >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq dnsutils >/dev/null; }

legacy_dc() { local proj="$1" envf="$2"; shift 2; docker compose -p "$proj" --env-file "$envf" -f "$LEGACY_COMPOSE" "$@"; }

confirm() {
  [ "${ASSUME_YES:-0}" = "1" ] && return 0
  local ans; read -r -p "$1 Ketik YA untuk lanjut: " ans
  [ "$ans" = "YA" ] || die "dibatalkan oleh pengguna"
}

# ------------------------------------------------------------------ rollback
rollback() {
  local envf="$LEGACY_BAK"; [ -f "$envf" ] || envf="$LEGACY_ENV"
  [ -f "$envf" ] || die "env lama tidak ditemukan ($LEGACY_BAK / $LEGACY_ENV)"
  local proj; proj="$(envget "$envf" COMPOSE_PROJECT_NAME)"; proj="${proj:-sipro}"
  say "ROLLBACK ke stack lama ($(envget "$envf" DOMAIN)) — volume data TIDAK dihapus"
  dc_edge down 2>/dev/null || true
  local inst
  for inst in $(inst_list); do
    if [ "$(inst_project "$inst")" = "$proj" ]; then dc "$inst" down 2>/dev/null || true
    else dc "$inst" stop 2>/dev/null || true; fi
  done
  [ -f "$LEGACY_ENV" ] || cp -p "$LEGACY_BAK" "$LEGACY_ENV"
  legacy_dc "$proj" "$LEGACY_ENV" up -d --remove-orphans
  [ -d "$INST_DIR" ] && mv "$INST_DIR" "$INST_DIR.rollback-$STAMP"
  ok "Stack lama berjalan lagi di https://$(envget "$LEGACY_ENV" DOMAIN)"
  echo "Konfigurasi multi-instance disimpan di $INST_DIR.rollback-$STAMP (demo/trial dihentikan, datanya tetap ada)."
}

if [ "${1:-}" = "rollback" ]; then rollback; exit 0; fi

# ------------------------------------------------------------------ migrasi instance utama
migrate_main() {
  [ -f "$LEGACY_ENV" ] || die "$LEGACY_ENV tidak ada — stack lama tidak ditemukan"
  local old_domain db_name proj mongo_cid vol
  old_domain="$(envget "$LEGACY_ENV" DOMAIN)"
  db_name="$(envget "$LEGACY_ENV" DB_NAME)"; db_name="${db_name:-sipro}"

  say "Deteksi stack lama"
  mongo_cid="$(docker ps -q --filter label=com.docker.compose.service=mongo \
               --filter "label=com.docker.compose.project.working_dir=$DEPLOY_DIR" | head -1)"
  [ -n "$mongo_cid" ] || die "container mongo stack lama tidak berjalan (cd deploy && docker compose ps)"
  proj="$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$mongo_cid")"
  vol="$(docker inspect -f '{{ range .Mounts }}{{ if eq .Destination "/data/db" }}{{ .Name }}{{ end }}{{ end }}' "$mongo_cid")"
  [ "$vol" = "${proj}_mongo_data" ] || die "volume data '$vol' tidak sesuai pola '${proj}_mongo_data' — hentikan, hubungi developer"
  ok "project=$proj  volume data=$vol  database=$db_name  domain lama=$old_domain"

  say "Cek DNS domain baru"
  if ! dns_ok "$NEW_DOMAIN"; then
    [ "${FORCE_DNS:-0}" = "1" ] || die "Arahkan A record $NEW_DOMAIN ke IP VPS dulu (lihat docs/DOMAIN_ESTORA.md), tunggu 5–30 menit, lalu ulangi."
    warn "FORCE_DNS=1 → lanjut walau DNS belum benar"
  fi
  local spec
  for spec in $EXTRA_INSTANCES; do dns_ok "${spec#*:}" || true; done

  echo
  echo "Rencana:"
  echo "  1. Backup penuh database '$db_name' + salinan .env ke $MIG_DIR"
  echo "  2. Build image baru (situs lama tetap jalan selama build)"
  echo "  3. Pindah ke Caddy bersama (jeda ±1–2 menit), data volume '$vol' dipakai ulang apa adanya"
  echo "  4. Verifikasi jumlah dokumen tiap koleksi sama/lebih banyak dari sebelum (gagal → rollback otomatis)"
  echo "  5. $old_domain → dialihkan ke https://$NEW_DOMAIN"
  echo "  6. Buat instance kosong: $EXTRA_INSTANCES"
  confirm "Lanjutkan migrasi?"

  say "1/6 Backup sebelum migrasi"
  mkdir -p "$MIG_DIR"; chmod 700 "$MIG_DIR"
  docker exec "$mongo_cid" mongodump --db "$db_name" --archive --gzip > "$MIG_DIR/$MAIN_INST-sebelum.archive.gz"
  gzip -t "$MIG_DIR/$MAIN_INST-sebelum.archive.gz" || die "arsip backup rusak — migrasi dihentikan, tidak ada yang diubah"
  [ "$(stat -c %s "$MIG_DIR/$MAIN_INST-sebelum.archive.gz")" -gt 1000 ] || die "arsip backup terlalu kecil — migrasi dihentikan"
  cp -p "$LEGACY_ENV" "$MIG_DIR/env.legacy"
  mongo_counts "$mongo_cid" "$db_name" > "$MIG_DIR/jumlah-sebelum.txt"
  grep -q '^users ' "$MIG_DIR/jumlah-sebelum.txt" || die "koleksi users tidak ditemukan di '$db_name' — salah database?"
  ok "Backup: $MIG_DIR/$MAIN_INST-sebelum.archive.gz ($(du -h "$MIG_DIR/$MAIN_INST-sebelum.archive.gz" | cut -f1)), $(wc -l < "$MIG_DIR/jumlah-sebelum.txt") koleksi"

  say "2/6 Konfigurasi instance '$MAIN_INST' (salinan .env lama, hanya domain yang berubah)"
  mkdir -p "$INST_DIR"; chmod 700 "$INST_DIR"
  local envf; envf="$(inst_env "$MAIN_INST")"
  ( umask 077; grep -vE '^(DOMAIN|COMPOSE_PROJECT_NAME|INSTANCE|REDIRECT_FROM|START_EMPTY|ACME_EMAIL)=' "$LEGACY_ENV" > "$envf" )
  envset "$envf" INSTANCE "$MAIN_INST"
  envset "$envf" COMPOSE_PROJECT_NAME "$proj"
  envset "$envf" DOMAIN "$NEW_DOMAIN"
  envset "$envf" REDIRECT_FROM "$([ "$old_domain" != "$NEW_DOMAIN" ] && echo "$old_domain")"
  envset "$envf" START_EMPTY false
  envset "$envf" DB_NAME "$db_name"
  mkdir -p "$EDGE_DIR"; printf 'ACME_EMAIL=%s\n' "$(envget "$LEGACY_ENV" ACME_EMAIL)" > "$EDGE_ENV"

  say "3/6 Build image baru (situs lama masih melayani)"
  dc "$MAIN_INST" build --pull
  ensure_edge_infra
  gen_caddyfile

  say "4/6 Pindah ke Caddy bersama"
  legacy_dc "$proj" "$LEGACY_ENV" stop caddy || true
  legacy_dc "$proj" "$LEGACY_ENV" rm -f caddy || true
  dc "$MAIN_INST" up -d --no-build --remove-orphans
  edge_up
  if ! wait_healthy "$MAIN_INST" 8; then
    warn "backend baru tidak sehat → rollback otomatis"; rollback; die "migrasi dibatalkan, situs lama dipulihkan"
  fi

  say "5/6 Verifikasi data"
  local new_cid; new_cid="$(dc "$MAIN_INST" ps -q mongo)"
  [ "$(docker inspect -f '{{ range .Mounts }}{{ if eq .Destination "/data/db" }}{{ .Name }}{{ end }}{{ end }}' "$new_cid")" = "$vol" ] \
    || { rollback; die "mongo baru tidak memakai volume $vol — rollback dilakukan"; }
  mongo_counts "$new_cid" "$db_name" > "$MIG_DIR/jumlah-sesudah.txt"
  # Koleksi sementara (TTL / dibangun ulang saat start) hanya dilaporkan, tidak memicu rollback.
  local volatile=" wa_webhook_events build_submit_claims automation_rules portal_otps "
  local missing
  missing="$(awk -v vol="$volatile" 'NR==FNR{after[$1]=$2; next}
            {a=(($1 in after)?after[$1]:"HILANG"); if (!($1 in after) || after[$1]+0 < $2+0) {
               if (index(vol, " "$1" ")) print "  (info) "$1" sebelum="$2" sesudah="a > "/dev/stderr";
               else print $1" sebelum="$2" sesudah="a }}' \
            "$MIG_DIR/jumlah-sesudah.txt" "$MIG_DIR/jumlah-sebelum.txt")"
  if [ -n "$missing" ]; then
    echo "$missing"; warn "jumlah data berkurang → rollback otomatis"; rollback
    die "migrasi dibatalkan. Backup aman di $MIG_DIR"
  fi
  ok "Semua $(wc -l < "$MIG_DIR/jumlah-sebelum.txt") koleksi utuh (jumlah dokumen sama/lebih banyak)"

  https_ok "$NEW_DOMAIN" 40 || warn "Bila https://$NEW_DOMAIN tetap tidak bisa dibuka: bash deploy/migrate_estora.sh rollback"
  if [ -n "$(envget "$envf" REDIRECT_FROM)" ]; then
    local loc; loc="$(curl -sS -o /dev/null -w '%{redirect_url}' --max-time 10 "https://$old_domain/" 2>/dev/null || true)"
    case "$loc" in https://"$NEW_DOMAIN"*) ok "https://$old_domain → $loc" ;; *) warn "pengalihan $old_domain belum terverifikasi (dapat: '${loc:-tidak ada}')" ;; esac
  fi
  mv "$LEGACY_ENV" "$LEGACY_BAK"
  ok "deploy/.env lama disimpan sebagai deploy/.env.legacy (untuk rollback)"
}

if [ -f "$(inst_env "$MAIN_INST")" ]; then
  say "Instance '$MAIN_INST' sudah dimigrasikan sebelumnya — lanjut ke instance tambahan"
else
  migrate_main
fi

say "6/6 Instance tambahan"
for spec in $EXTRA_INSTANCES; do
  name="${spec%%:*}"; dom="${spec#*:}"
  bash "$DEPLOY_DIR/add_instance.sh" "$name" "$dom" --empty
done

install_backup_cron
ok "Cron backup harian 02:00 untuk semua instance"

say "SELESAI"
for inst in $(inst_list); do
  f="$(inst_env "$inst")"
  printf '  %-6s https://%-22s superadmin: %s / %s\n' "$inst" "$(envget "$f" DOMAIN)" \
    "$(envget "$f" SUPERADMIN_EMAIL)" "$(envget "$f" SUPERADMIN_PASSWORD)"
done
cat <<EOF

Langkah manual sesudah migrasi:
  1. Meta (WhatsApp) → Configuration → Webhook → ganti Callback URL ke https://$NEW_DOMAIN/api/webhooks/wa
     (domain lama tetap meneruskan webhook, tapi sebaiknya diganti).
  2. Pengguna perlu login ulang sekali di https://$NEW_DOMAIN (cookie terikat domain).
  3. Ganti sandi akun demo (Sipro#2026) di demo & trial bila diakses publik.
Rollback kapan saja: bash deploy/migrate_estora.sh rollback
EOF
