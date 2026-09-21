#!/usr/bin/env python3
"""INV-PERF-01 — `to_list(n)` dengan n > 20000 DILARANG di kode produksi backend,
kecuali terdaftar di ALLOWLIST ber-alasan tertulis (≥20 karakter) — pola INV-UI-07/08.

Kelas cacat yang ditutup (T-03 audit 2026-09): 63 pemanggilan `to_list(≥20000)`;
beberapa memuat SELURUH koleksi lalu menyaring di Python (mis. `product_sales_velocity`
memuat semua `inventory_movements` untuk memilih 2 jenis mutasi). Angka ini hanya bisa
TURUN: entri ALLOWLIST yang sudah tidak ada di kode → MERAH juga (ratchet), supaya
daftar-kecuali tidak menjadi kuburan alasan basi.

Cakupan: backend/**/*.py KECUALI berkas uji/POC/seed/skrip migrasi (`backend/scripts/`,
`backend/tests/`, `*test*`, `*_poc*`, `seed_*`, `_smoke*`, `poc_*`).

Pakai:  python3 scripts/guardrails/verify_to_list_bound.py
        python3 scripts/guardrails/verify_to_list_bound.py --self-test
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from _common import Guard, BACKEND, G, R, X  # noqa: E402

LIMIT = 20000
RE_TOLIST = re.compile(r"\.to_list\(\s*([0-9_]+)\s*\)")
EXCLUDE_PARTS = ("/tests/", "/scripts/", "/_legacy/")
EXCLUDE_NAME = re.compile(r"(test|_poc|^poc_|^seed_|^_smoke|^_)", re.I)

# Kunci: (path relatif ke backend, n). Nilai: (jumlah kejadian yang DIIZINKAN, alasan ≥20 huruf).
# Menambah kejadian baru di berkas yang sama dengan n sama → jumlah naik → MERAH.
ALLOWLIST: dict[tuple[str, int], tuple[int, str]] = {
    ("services/lot_migration.py", 100000): (3, "migrasi lot satu-kali (dipicu admin), bukan jalur request harian — hutang T-03 Lapis 4"),
    ("services/roll_service.py", 100000): (2, "rebuild inventory_balances dari rolls (seed/migrasi), proyeksi 3 field — hutang T-03"),
    ("services/so_status.py", 100000): (1, "migrasi status SO massal (proyeksi sempit), bukan endpoint daftar — hutang T-03"),
    ("services/stock_analytics_service.py", 100000): (1, "roll fisik ber-sisa (length_remaining>0) per scope untuk aging — hutang T-03 agregasi"),
    ("services/profitability_service.py", 50000): (1, "laporan profitabilitas: SO dalam rentang tanggal (filter created_at) — hutang T-03 paginasi"),
    ("services/cashflow_forecast_service.py", 50000): (1, "proyeksi arus kas: proyeksi 12 field SO terbuka — hutang T-03"),
    ("services/financial_statement_service.py", 100000): (1, "laporan keuangan: journal_entries tersaring tanggal/entitas, proyeksi lines — hutang T-03 agregasi"),
    ("services/gl_service.py", 50000): (2, "trial balance / buku besar per akun: journal_entries tersaring status+tanggal — hutang T-03 agregasi"),
    ("services/gl_service.py", 100000): (2, "valuasi persediaan per entitas: rolls fisik per owner, proyeksi sempit — hutang T-03"),
}


def scan(root: Path = BACKEND) -> dict[tuple[str, int], list[int]]:
    """{(rel_path, n): [nomor baris, ...]} untuk semua to_list(n > LIMIT) di kode produksi."""
    found: dict[tuple[str, int], list[int]] = {}
    for f in sorted(root.rglob("*.py")):
        rel = str(f.relative_to(root))
        if any(p in f"/{rel}" for p in EXCLUDE_PARTS) or EXCLUDE_NAME.search(f.name):
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            for m in RE_TOLIST.finditer(line):
                n = int(m.group(1).replace("_", ""))
                if n > LIMIT:
                    found.setdefault((rel, n), []).append(i)
    return found


def check(found: dict[tuple[str, int], list[int]], allow=ALLOWLIST) -> Guard:
    g = Guard("INV-PERF-01", f"to_list(n) dengan n > {LIMIT} dilarang di kode produksi (kecuali allowlist ber-alasan)")
    for key, lines in sorted(found.items()):
        g.bump()
        rel, n = key
        if key not in allow:
            g.add(f"backend/{rel}:{','.join(map(str, lines))} — to_list({n}) > {LIMIT}. Pindahkan penyaring ke query / "
                  "pakai agregasi / paginasi (backend/pagination.py), atau daftarkan di ALLOWLIST dengan alasan ≥20 huruf.")
            continue
        cap, reason = allow[key]
        if len(reason.strip()) < 20:
            g.add(f"backend/{rel} to_list({n}): alasan allowlist terlalu pendek (<20 huruf): {reason!r}")
        if len(lines) > cap:
            g.add(f"backend/{rel}:{','.join(map(str, lines))} — to_list({n}) muncul {len(lines)}× > {cap}× yang diizinkan. "
                  "Kejadian BARU tidak boleh ditambah; angka ini hanya boleh turun.")
    for key, (cap, _) in allow.items():
        g.bump()
        if key not in found:
            g.add(f"backend/{key[0]} to_list({key[1]}) ada di ALLOWLIST tetapi tidak lagi di kode — hapus entrinya (ratchet).")
    return g


def self_test() -> int:
    fails = 0

    def case(name, found, allow, expect_red):
        nonlocal fails
        g = check(found, allow)
        red = bool(g.violations)
        ok = red == expect_red
        fails += 0 if ok else 1
        print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] {name} → {'MERAH' if red else 'hijau'}")

    case("kode bersih, allowlist kosong → hijau", {}, {}, False)
    case("to_list(50000) baru tanpa allowlist → MERAH", {("services/x.py", 50000): [10]}, {}, True)
    case("to_list(20000) tepat batas → tidak dipindai (hijau)", scan_fake("x = await db.a.find().to_list(20000)\n"), {}, False)
    case("to_list(20001) → MERAH", scan_fake("x = await db.a.find().to_list(20001)\n"), {}, True)
    case("to_list(100_000) dengan underscore → MERAH", scan_fake("x = await db.a.find().to_list(100_000)\n"), {}, True)
    case("terdaftar dengan alasan panjang → hijau", {("services/x.py", 50000): [10]},
         {("services/x.py", 50000): (1, "alasan yang cukup panjang untuk lolos")}, False)
    case("terdaftar tapi alasan pendek → MERAH", {("services/x.py", 50000): [10]},
         {("services/x.py", 50000): (1, "pendek")}, True)
    case("kejadian bertambah melebihi kuota allowlist → MERAH", {("services/x.py", 50000): [10, 20]},
         {("services/x.py", 50000): (1, "alasan yang cukup panjang untuk lolos")}, True)
    case("entri allowlist basi (kode sudah bersih) → MERAH (ratchet)", {},
         {("services/x.py", 50000): (1, "alasan yang cukup panjang untuk lolos")}, True)
    case("berkas uji/POC/seed dikecualikan → hijau",
         scan_fake("x = await db.a.find().to_list(999999)\n", name="test_core_x_poc.py"), {}, False)
    real = check(scan())
    ok = not real.violations
    fails += 0 if ok else 1
    print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] kode nyata saat ini HIJAU ({len(real.violations)} pelanggaran)")
    for v in real.violations:
        print(f"    ✗ {v[:160]}")
    print(f"{G if not fails else R}  SELF-TEST {'HIJAU' if not fails else 'MERAH'} ({fails} gagal).{X}")
    return 1 if fails else 0


def scan_fake(src: str, name: str = "services/fake_service.py") -> dict:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(src)
        return scan(Path(d))


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    return check(scan()).finish()


if __name__ == "__main__":
    sys.exit(main())
