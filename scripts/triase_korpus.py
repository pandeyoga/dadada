#!/usr/bin/env python3
"""Triase korpus uji (T-05, audit 2026-09) dari keluaran `scripts/run_corpus.py`.

Vonis per skrip berdasarkan ATURAN yang bisa dibaca di bawah (bukan tebakan bebas):
  LULUS            rc=0
  LINGKUNGAN       URL preview basi hardcoded · prasyarat seed tambahan (blueprint gudang,
                   akun bootstrap) · stok/urutan residu skrip sebelumnya
  UJI BASI         perilaku sengaja berubah (mis. pemisahan tugas approval harga)
  TIDAK TAHU       belum bisa disimpulkan — vonis SAH, bukan kegagalan
Pakai: python3 scripts/triase_korpus.py coverage_data/corpus_run_2026-09-05.json --md memory/TRIASE_KORPUS_2026-09.md
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CUR_URL = ""
for line in (ROOT / "frontend/.env").read_text().splitlines():
    if line.startswith("REACT_APP_BACKEND_URL="):
        CUR_URL = line.split("=", 1)[1].strip()

RULES = [
    (r"Pemisahan tugas: pengaju harga tidak boleh menyetujui", "UJI BASI",
     "aturan pemisahan tugas approval harga (sakelar Pusat Pengaturan → Persetujuan & Ambang, FASE PS-20/approval matrix) — uji masih memakai admin sebagai pengaju+penyetuju"),
    (r"SRG-01|RCM-RETUR|Gedung Retur", "LINGKUNGAN",
     "prasyarat: blueprint gudang (`POST /warehouse-sites/seed-blueprint`) belum dijalankan di DB uji"),
    (r"login (wh\.admin|md)@kainnusantara\.id -> 401", "LINGKUNGAN",
     "akun md@/wh.admin@ hanya dibuat `bootstrap.run_bootstrap()` saat backend START; `seed_realistic.py` menghapus `users` → wajib restart backend SESUDAH seed"),
    (r"Stok milik entitas tidak mencukupi", "LINGKUNGAN",
     "stok demo sudah dipotong skrip sebelumnya (residu urutan) — POC ini HIJAU saat dijalankan sendiri di seed bersih (lihat gate --full)"),
    (r"REACT_APP_BACKEND_URL must be set|'NoneType' object has no attribute 'rstrip'", "LINGKUNGAN",
     "env REACT_APP_BACKEND_URL tidak di-set di shell (runner kini mengisinya dari frontend/.env)"),
    (r"Login failed.*404|Login .*404|Expected 200, got 404|got 404|status=404|Status 404|404 page not found|API Health Check|Auth - Login|Failed to login|Login\s*$", "LINGKUNGAN",
     "URL backend preview LAMA di-hardcode di skrip (bukan env) → 404 dari ingress, bukan dari aplikasi"),
]


def hardcoded_url(path: str) -> str | None:
    src = (ROOT / path).read_text(errors="ignore")
    if "REACT_APP_BACKEND_URL" in src:
        return None
    urls = set(re.findall(r"https://[a-z0-9\-]+\.preview\.emergentagent\.com", src))
    urls.discard(CUR_URL)
    return sorted(urls)[0] if urls else None


def vonis(r: dict) -> tuple[str, str]:
    if r["rc"] == 0:
        return "LULUS", "rc=0"
    text = "\n".join(r.get("errors") or []) + "\n" + (r.get("tail") or "")
    hu = hardcoded_url(r["file"]) if r["mode"] == "direct" else None
    if hu:
        return "LINGKUNGAN", f"URL preview basi hardcoded: {hu}"
    for rx, v, why in RULES:
        if re.search(rx, text):
            return v, why
    return "TIDAK TAHU", "galat belum diklasifikasi — perlu dibaca satu per satu"


def main() -> int:
    src = pathlib.Path(sys.argv[1])
    d = json.loads(src.read_text())
    rows = []
    for r in d["results"]:
        v, why = vonis(r)
        rows.append((r, v, why))
    from collections import Counter
    c = Counter(v for _, v, _ in rows)
    L = [f"# TRIASE KORPUS UJI — 2026-09 (T-05)", "",
         f"- Sumber: `{src}` (dihasilkan `scripts/run_corpus.py`, berurutan, commit `{d.get('commit')}`, {d.get('when')})",
         f"- Skrip: **{len(rows)}** · " + " · ".join(f"{k}: **{n}**" for k, n in sorted(c.items())),
         "- Catatan: korpus lama `coverage_data/corpus_summary.json` (122 skrip) TIDAK bisa direproduksi — 58 dari 122 berkasnya sudah tidak ada di repo. Korpus di bawah = semua skrip uji/POC yang ADA hari ini (220).",
         "- Vonis mengikuti aturan tertulis di `scripts/triase_korpus.py` (`RULES`). `TIDAK TAHU` = belum disimpulkan, bukan lulus.",
         "", "| # | Skrip | Mode | RC | Lulus/Total | Vonis | Bukti (galat pertama / aturan) |", "|---|---|---|---|---|---|---|"]
    for i, (r, v, why) in enumerate(rows, 1):
        lt = f"{r['passed']}/{r['total']}" if r.get("total") is not None else "?"
        err = (r["errors"][0] if r.get("errors") else "").replace("|", "¦")[:140]
        bukti = f"`{err}` — {why}" if err and v != "LULUS" else why
        L.append(f"| {i} | `{r['file']}` | {r['mode']} | {r['rc']} | {lt} | **{v}** | {bukti} |")
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
