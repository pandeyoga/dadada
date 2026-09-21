#!/usr/bin/env bash
# install_hooks.sh — pasang .git/hooks/pre-commit (T-06 audit 2026-09).
# Hook: gate statik (--quick) WAJIB hijau; verifikator temuan hanya MELAPOR jumlahnya
# (tidak memblokir — temuan lama bukan alasan menahan semua pekerjaan).
set -euo pipefail
cd "$(dirname "$0")/.."
HOOK=.git/hooks/pre-commit
[ -d .git ] || { echo "bukan repo git (.git tidak ada)"; exit 1; }
mkdir -p .git/hooks
cat > "$HOOK" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
echo "[pre-commit] gate --quick + verifikator temuan"
bash scripts/gate.sh --quick || { echo "GATE MERAH — commit dibatalkan"; exit 1; }
python3 scripts/audit_temuan_2026_09.py >/tmp/temuan.txt 2>&1 || true
awk '/TERBUKTI \(masih cacat\)/{print "[pre-commit] " $0}' /tmp/temuan.txt
EOF
chmod +x "$HOOK"
echo "hook terpasang: $HOOK"
