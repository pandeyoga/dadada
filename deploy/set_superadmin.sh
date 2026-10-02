#!/usr/bin/env bash
# Ganti email & sandi Super Admin di SEMUA instance (atau instance tertentu).
#   bash deploy/set_superadmin.sh                                  → superadmin@estora.id / test1234 di semua instance
#   SA_EMAIL=x@estora.id SA_PASSWORD='rahasia' bash deploy/set_superadmin.sh hl5
# Akun super admin lama di-rename (id, riwayat & audit tetap), bukan dibuat akun baru. Data lain tidak disentuh.
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SA_EMAIL="$(echo "${SA_EMAIL:-superadmin@estora.id}" | tr 'A-Z' 'a-z')"
SA_PASSWORD="${SA_PASSWORD:-test1234}"
[ -n "$(inst_list)" ] || die "belum multi-instance — jalankan deploy/migrate_estora.sh dulu"
[ "${#SA_PASSWORD}" -ge 6 ] || die "sandi minimal 6 karakter"
case "$SA_PASSWORD" in *'$'*|*' '*|*'#'*) die "sandi jangan memuat \$, spasi, atau # (dibaca dari file env)";; esac

TARGETS="${1:-$(inst_list)}"
for inst in $TARGETS; do
  f="$(inst_env "$inst")"; [ -f "$f" ] || die "instance '$inst' tidak ada"
  old="$(envget "$f" SUPERADMIN_EMAIL)"; old="${old:-superadmin@sipro.co.id}"
  say "[$inst] Super Admin: $old → $SA_EMAIL"
  cp -p "$f" "$f.bak-$(date +%Y%m%d%H%M%S)"
  prev="$(envget "$f" SUPERADMIN_RENAME_FROM)"
  rename="$(printf '%s\n' superadmin@sipro.co.id $old ${prev//,/ } | tr 'A-Z' 'a-z' | { grep -vx "$SA_EMAIL" || true; } | sort -u | paste -sd, -)"
  envset "$f" SUPERADMIN_EMAIL "$SA_EMAIL"
  envset "$f" SUPERADMIN_PASSWORD "$SA_PASSWORD"
  envset "$f" SUPERADMIN_RENAME_FROM "$rename"
  dc "$inst" up -d --no-build backend
  wait_healthy "$inst" 6 || die "backend '$inst' tidak sehat — env lama ada di $f.bak-*"
  code="$(dc "$inst" exec -T backend curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1:8001/api/auth/login \
          -H 'Content-Type: application/json' -d "{\"email\":\"$SA_EMAIL\",\"password\":\"$SA_PASSWORD\"}" || true)"
  [ "$code" = "200" ] && ok "[$inst] login $SA_EMAIL berhasil" || warn "[$inst] uji login mengembalikan HTTP $code"
done

say "Selesai"
for inst in $TARGETS; do echo "  https://$(envget "$(inst_env "$inst")" DOMAIN)  →  $SA_EMAIL / $SA_PASSWORD"; done
