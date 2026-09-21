#!/usr/bin/env python3
"""Triase kandidat N+1 (T-04 Langkah 1, audit 2026-09) — TABEL, bukan perbaikan.

Mendeteksi query BACA (find_one/find/count_documents/aggregate) di dalam `for` atas data,
mencatat SUMBER iterabel loop (teks apa adanya), dan memberi vonis awal yang JUJUR:
  BIARKAN (sengaja)     : find_one_and_update di loop (atomisitas per dokumen, INV-CONC-01)
  BIARKAN (loop kecil)  : iterabel `range(n)` kecil / enumerate(range)
  PERBAIKI              : hanya untuk lokasi yang sudah DIPERIKSA MANUSIA (daftar VONIS_MANUAL)
  TIDAK TAHU            : sisanya — ukuran loop tidak bisa disimpulkan statik
Pakai: python3 scripts/triase_nplus1.py [--md memory/TRIASE_NPLUS1_2026-09.md]
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BE = ROOT / "backend"
READ_OPS = {"find_one", "find", "count_documents", "aggregate", "distinct"}
ATOMIC = {"find_one_and_update"}

# (berkas, baris-query) → (vonis, alasan). Hanya lokasi yang benar-benar dibaca 2026-09-05.
VONIS_MANUAL = {
    ("routers/reporting.py", 44): ("PERBAIKI", "atas `balances` (seluruh inventory_balances ter-scope, ratusan–ribuan baris); find_one mutasi terakhir per baris → satu aggregate $group product+warehouse $max timestamp"),
    ("routers/admin.py", 160): ("PERBAIKI", "atas `rows` CSV impor produk (bisa ribuan baris); find_one by sku per baris → satu find {sku: {$in: [...]}} lalu peta"),
    ("routers/categories.py", 50): ("BIARKAN (loop kecil)", "atas `rows` kategori master (puluhan baris); count per kategori — bisa jadi satu aggregate, tapi bukan jalur panas"),
    ("routers/entities.py", 70): ("BIARKAN (loop kecil)", "atas `rows` badan usaha (≤ puluhan, berhalaman `limit`); count user per entitas"),
}


def iter_src(node: ast.For, lines: list[str]) -> str:
    seg = ast.get_source_segment("\n".join(lines), node.iter) or "?"
    return " ".join(seg.split())[:70]


def scan() -> list[dict]:
    out = []
    for f in sorted(BE.rglob("*.py")):
        rel = str(f.relative_to(BE))
        if any(p in f"/{rel}" for p in ("/tests/", "/scripts/", "/_legacy/")) or f.name.startswith(("test_", "backend_test", "seed_", "_", "poc_")) or "_poc" in f.name:
            continue
        src = f.read_text(errors="ignore")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        lines = src.splitlines()
        for loop in ast.walk(tree):
            if not isinstance(loop, (ast.For, ast.AsyncFor)):
                continue
            for n in ast.walk(loop):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in READ_OPS | ATOMIC:
                    v = n.func.value
                    if not (isinstance(v, ast.Attribute) and isinstance(v.value, ast.Name) and v.value.id in ("db", "database")):
                        continue
                    it = iter_src(loop, lines) if isinstance(loop, ast.For) else "async for"
                    key = (rel, n.lineno)
                    if n.func.attr in ATOMIC:
                        vonis, alasan = "BIARKAN (sengaja)", "find_one_and_update per dokumen = pengaman balapan (INV-CONC-01); JANGAN jadi bulk"
                    elif key in VONIS_MANUAL:
                        vonis, alasan = VONIS_MANUAL[key]
                    elif it.startswith(("range(", "enumerate(range(")):
                        vonis, alasan = "BIARKAN (loop kecil)", "loop terbatas `range`"
                    else:
                        vonis, alasan = "TIDAK TAHU", "ukuran iterabel tidak bisa disimpulkan statik — belum dibaca manusia"
                    out.append({"file": rel, "line": n.lineno, "loop_line": loop.lineno, "query": f"db.{v.attr}.{n.func.attr}",
                                "iter": it, "vonis": vonis, "alasan": alasan})
    # unik per (file, line)
    seen, uniq = set(), []
    for r in out:
        k = (r["file"], r["line"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq


def main() -> int:
    rows = scan()
    from collections import Counter
    c = Counter(r["vonis"] for r in rows)
    L = ["# Triase kandidat N+1 (T-04 Langkah 1) — dihasilkan `scripts/triase_nplus1.py`", "",
         f"Total kandidat: **{len(rows)}** · " + " · ".join(f"{k}: **{v}**" for k, v in sorted(c.items())), "",
         "Vonis `PERBAIKI` hanya diberikan untuk lokasi yang sudah dibaca manusia (`VONIS_MANUAL`). "
         "`TIDAK TAHU` adalah vonis yang SAH — bukan tebakan. Tidak ada satu pun yang diperbaiki di langkah ini.", "",
         "| # | Berkas:baris | Query | Loop (baris) atas | Vonis | Alasan |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        it = r["iter"].replace("|", "¦")
        L.append(f"| {i} | `backend/{r['file']}:{r['line']}` | `{r['query']}` | `{it}` ({r['loop_line']}) | {r['vonis']} | {r['alasan']} |")
    text = "\n".join(L) + "\n"
    if "--md" in sys.argv:
        out = ROOT / sys.argv[sys.argv.index("--md") + 1]
        out.write_text(text)
        print(f"ditulis: {out} · {dict(c)}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
