#!/usr/bin/env python3
"""INV-DOC-01 — CODEBASE_MAP.md tidak boleh menyimpang >10% dari kenyataan kode.

Kelas cacat yang ditutup (T-07 audit 2026-09): peta tulisan tangan v1.0 (28 Mei 2026)
tetap terdaftar TIER 0 "wajib dibaca tiap sesi" sementara isinya 25 router / 106
endpoint — kenyataan 123 router / 1.100+ endpoint, dan `hash_password` masih disebut
SHA256 padahal sudah bcrypt. Agen yang mempercayai peta menulis kode yang salah.

Penjaga ini membaca tabel "Ringkasan angka" di CODEBASE_MAP.md dan membandingkan
dengan hitung ulang `scripts/gen_codebase_map.py --json`. Selisih relatif >10% pada
salah satu angka → MERAH. Peta tanpa penanda generator → MERAH (berarti disunting tangan).

Pakai:  python3 scripts/guardrails/verify_codebase_map.py
        python3 scripts/guardrails/verify_codebase_map.py --self-test
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import Guard, ROOT, G, R, X  # noqa: E402

MAP = ROOT / "CODEBASE_MAP.md"
GEN = ROOT / "scripts" / "gen_codebase_map.py"
TOL = 0.10
KEYS = {
    "routers": r"\| Router \(`backend/routers/\*\.py`\) \| (\d+) \|",
    "endpoints": r"\| Endpoint \(`@router\.<method>`\) \| (\d+) \|",
    "services": r"\| Service \(`backend/services/\*\.py`\) \| (\d+) \|",
    "collections": r"\| Koleksi MongoDB disentuh kode produksi \| (\d+) \|",
}
MARKER = "DIHASILKAN OTOMATIS oleh scripts/gen_codebase_map.py"


def actual() -> dict:
    out = subprocess.run([sys.executable, str(GEN), "--json"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def check(map_text: str, real: dict) -> Guard:
    g = Guard("INV-DOC-01", "CODEBASE_MAP.md selaras kode (selisih ≤10%)")
    g.bump()
    if MARKER not in map_text:
        g.add("CODEBASE_MAP.md tanpa penanda generator — peta disunting tangan / versi lama. "
              "Jalankan: python3 scripts/gen_codebase_map.py")
        return g
    for key, rx in KEYS.items():
        g.bump()
        m = re.search(rx, map_text)
        if not m:
            g.add(f"angka '{key}' tidak ditemukan di peta (format tabel berubah?)")
            continue
        peta, nyata = int(m.group(1)), int(real[key])
        if nyata == 0:
            continue
        dev = abs(peta - nyata) / nyata
        if dev > TOL:
            g.add(f"{key}: peta {peta} vs nyata {nyata} (selisih {dev:.0%} > {TOL:.0%}) — "
                  "jalankan ulang scripts/gen_codebase_map.py")
    return g


def self_test() -> int:
    real = actual()
    fails = 0

    def case(name: str, text: str, expect_red: bool):
        nonlocal fails
        g = check(text, real)
        red = bool(g.violations)
        ok = red == expect_red
        fails += 0 if ok else 1
        print(f"  [{G if ok else R}{'PASS' if ok else 'FAIL'}{X}] {name} → {'MERAH' if red else 'hijau'}")

    good = subprocess.run([sys.executable, str(GEN), "--stdout"], capture_output=True, text=True, check=True).stdout
    case("peta hasil generator → hijau", good, False)
    case("peta tanpa penanda generator (tulisan tangan) → MERAH", good.replace(MARKER, "x"), True)
    bad = re.sub(KEYS["routers"].replace("(\\d+)", r"\d+").replace("\\", "\\"),
                 f"| Router (`backend/routers/*.py`) | {real['routers'] * 2} |", good)
    case("jumlah router digandakan (menyimpang 100%) → MERAH", bad, True)
    bad2 = re.sub(r"\| Endpoint \(`@router\.<method>`\) \| \d+ \|",
                  f"| Endpoint (`@router.<method>`) | {int(real['endpoints'] * 1.05)} |", good)
    case("endpoint menyimpang 5% (≤ toleransi) → hijau", bad2, False)
    bad3 = re.sub(r"\| Endpoint \(`@router\.<method>`\) \| \d+ \|",
                  f"| Endpoint (`@router.<method>`) | {int(real['endpoints'] * 0.8)} |", good)
    case("endpoint menyimpang 20% → MERAH", bad3, True)
    case("peta lama v1.0 (tabel Ringkasan angka tidak ada) → MERAH",
         "# CODEBASE MAP — Quick Reference\n" + MARKER + "\n", True)
    print(f"{G if not fails else R}  SELF-TEST {'HIJAU' if not fails else 'MERAH'} ({fails} gagal).{X}")
    return 1 if fails else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    if not MAP.exists():
        print(f"{R}[FAIL]{X} CODEBASE_MAP.md tidak ada.")
        return 1
    return check(MAP.read_text(errors="ignore"), actual()).finish()


if __name__ == "__main__":
    sys.exit(main())
