#!/usr/bin/env bash
# Menjalankan seluruh uji peramban SIPRO (scripts/ui/*.js) terhadap UI satu-origin yang sudah berjalan.
# Prasyarat dan cara menyiapkan UI: lihat scripts/ui/README.md.
#   SIPRO_UI_BASE=http://localhost:3073 PYTHON=<python venv backend> bash scripts/ui/run_all.sh
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
export SIPRO_UI_BASE="${SIPRO_UI_BASE:-http://localhost:3073}"
export API_BASE="${API_BASE:-${SIPRO_UI_BASE}/api}"     # dibaca seed_hc.py (pembantu tes P0)
export SIPRO_API_BASE="${SIPRO_API_BASE:-$API_BASE}"
export NODE_PATH="${NODE_PATH:-/opt/node-tools/node_modules}"   # tempat paket `playwright`
PY="${PYTHON:-python3}"

echo "== menyemai data uji =="
"$PY" "$HERE/seed_hc.py" > /dev/null || { echo "GAGAL menyemai data"; exit 2; }

fail=0
for t in webhook_security ronde_a_pembatalan ronde_bc_banner ronde_d_void ronde_e_aksi_409 ronde_f_batal_reservasi w0_kebijakan; do
  echo; echo "================ $t ================"
  node "$HERE/$t.js" || fail=1
done
echo; [ "$fail" = 0 ] && echo "SEMUA LULUS" || echo "ADA YANG GAGAL"
exit "$fail"
