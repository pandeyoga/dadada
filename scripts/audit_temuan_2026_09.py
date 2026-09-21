#!/usr/bin/env python3
"""
audit_temuan_2026_09.py — VERIFIKATOR TEMUAN AUDIT (statik, read-only).

TUJUAN
------
Menghapus ruang bagi agen untuk MENGARANG. Setiap temuan di
`INSTRUKSI_PERBAIKAN_2026-09.md` punya satu pemeriksa mekanis di sini yang
membaca KODE SUMBER dan menjawab satu dari tiga:

    TERBUKTI   — pola cacat masih ada (temuan NYATA, belum diperbaiki)
    GUGUR      — pola cacat TIDAK ada (temuan salah / sudah diperbaiki)
    RALAT      — file/simbol acuan tidak ditemukan → temuan tak bisa diuji
                 (agen WAJIB lapor, DILARANG menebak)

ATURAN PEMAKAIAN (untuk agen)
-----------------------------
1. Jalankan dari akar repo:  python3 scripts/audit_temuan_2026_09.py
2. SALIN-TEMPEL keluaran mentahnya ke laporan. Jangan diringkas, jangan diketik ulang.
3. DILARANG mengubah berkas ini untuk membuat temuan lewat. Berkas ini dijaga
   checksum (lihat blok SEGEL di bawah, dicetak tiap kali dijalankan).
4. Sesudah perbaikan, jalankan lagi. Temuan yang diperbaiki HARUS berubah
   TERBUKTI → GUGUR. Kalau tetap TERBUKTI, perbaikan itu BELUM selesai.
5. Kode keluar: 0 = tidak ada temuan TERBUKTI. 1 = masih ada. 2 = ada RALAT.

Read-only: skrip ini TIDAK menyentuh database, TIDAK menjalankan server,
TIDAK mengubah satu berkas pun.
"""
from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ─── Segel: checksum berkas ini sendiri ──────────────────────────────────────
SELF = pathlib.Path(__file__).resolve()

C_OK = "\033[32m"; C_BAD = "\033[31m"; C_WARN = "\033[33m"; C_DIM = "\033[2m"; C_END = "\033[0m"
if not sys.stdout.isatty():
    C_OK = C_BAD = C_WARN = C_DIM = C_END = ""

hasil: list[tuple[str, str, str, str]] = []   # (id, status, judul, bukti)


def baca(rel: str) -> str | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    return p.read_text(errors="ignore")


def lapor(tid: str, judul: str, status: str, bukti: str) -> None:
    hasil.append((tid, status, judul, bukti))


def baris_dari(teks: str, pola: str, flags=0) -> list[tuple[int, str]]:
    """Kembalikan [(nomor_baris, isi_baris)] yang cocok pola."""
    out = []
    for i, l in enumerate(teks.split("\n"), 1):
        if re.search(pola, l, flags):
            out.append((i, l.rstrip()))
    return out


# ════════════════════════════════════════════════════════════════════════════
# T-01 — Tidak ada transaksi MongoDB di kode produksi
# ════════════════════════════════════════════════════════════════════════════
def t01() -> None:
    tid, judul = "T-01", "Tidak ada transaksi MongoDB (atomisitas lintas dokumen)"
    hits = []
    for p in (ROOT / "backend").rglob("*.py"):
        rel = str(p.relative_to(ROOT))
        if "/tests/" in rel or re.search(r"(^|/)(test_|_test)", rel.split("/")[-1]):
            continue
        s = p.read_text(errors="ignore")
        for n, l in baris_dari(s, r"start_session|with_transaction|start_transaction"):
            hits.append(f"{rel}:{n}: {l.strip()[:90]}")

    # Bukti pendamping: alur resolve_escalation menulis 3 koleksi tanpa penjaga ulang-jalan.
    src = baca("backend/routers/outbound_picking.py")
    if src is None:
        lapor(tid, judul, "RALAT", "backend/routers/outbound_picking.py TIDAK DITEMUKAN")
        return
    guard = baris_dari(src, r'if not task\.get\("escalation"\)')
    rolls = baris_dari(src, r"release_order_rolls_partial")
    so_upd = baris_dari(src, r"db\.sales_orders\.update_one")
    task_upd = baris_dari(src, r"db\.wms_tasks\.find_one_and_update")

    bukti = [
        f"transaksi di kode produksi: {len(hits)} (harapan temuan: 0)",
        f"penjaga resolve_escalation  : {guard[0][0] if guard else '?'}  -> "
        f"{guard[0][1].strip() if guard else 'TIDAK ADA'}",
        f"tulis inventory_rolls       : baris {[n for n, _ in rolls]}",
        f"tulis sales_orders          : baris {[n for n, _ in so_upd]}",
        f"tulis wms_tasks             : baris {[n for n, _ in task_upd]}",
    ]
    # TERBUKTI bila: nol transaksi DAN penjaga hanya memeriksa keberadaan escalation
    # (bukan escalation['status'] != 'resolved') DAN ada >=3 koleksi ditulis.
    penjaga_lemah = bool(guard) and not baris_dari(src, r'escalation.*status.*!=.*resolved')
    if len(hits) == 0 and penjaga_lemah and rolls and so_upd and task_upd:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    elif len(hits) > 0:
        lapor(tid, judul, "GUGUR", "Transaksi DITEMUKAN:\n  " + "\n  ".join(hits[:10]))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti) + "\n  -> penjaga ulang-jalan sudah ada")


# ════════════════════════════════════════════════════════════════════════════
# T-02 — CORS default "*" + allow_credentials, cookie secure=False hardcoded
# ════════════════════════════════════════════════════════════════════════════
def t02() -> None:
    tid, judul = "T-02", "CORS default '*' + cookie sesi non-Secure (hardcoded)"
    srv = baca("backend/server.py")
    auth = baca("backend/routers/auth.py")
    if srv is None or auth is None:
        lapor(tid, judul, "RALAT", "server.py atau routers/auth.py TIDAK DITEMUKAN")
        return
    cors = baris_dari(srv, r'CORS_ORIGINS["\']\s*,\s*["\']\*["\']')
    cred = baris_dari(srv, r"allow_credentials\s*=\s*True")
    ck = baris_dari(auth, r"set_cookie\(.*secure\s*=\s*False")
    if not ck:
        ck = baris_dari(auth, r"secure\s*=\s*False")
    bukti = [
        f"server.py CORS default '*'   : {'baris ' + str(cors[0][0]) if cors else 'TIDAK ADA'}"
        + (f"  -> {cors[0][1].strip()}" if cors else ""),
        f"server.py allow_credentials  : {'baris ' + str(cred[0][0]) if cred else 'TIDAK ADA'}",
        f"auth.py  cookie secure=False : {'baris ' + str(ck[0][0]) if ck else 'TIDAK ADA'}"
        + (f"  -> {ck[0][1].strip()}" if ck else ""),
    ]
    if cors and cred and ck:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-03 — Paginasi belum merata; to_list() besar tanpa batas nyata
# ════════════════════════════════════════════════════════════════════════════
AMBANG_TO_LIST = 20000


def t03() -> None:
    tid, judul = "T-03", f"to_list(>={AMBANG_TO_LIST}) & paginasi belum merata"
    besar: list[str] = []
    total_1000 = 0
    for d in ("backend/routers", "backend/services"):
        base = ROOT / d
        if not base.is_dir():
            lapor(tid, judul, "RALAT", f"{d} TIDAK DITEMUKAN")
            return
        for p in sorted(base.glob("*.py")):
            rel = str(p.relative_to(ROOT))
            for i, l in enumerate(p.read_text(errors="ignore").split("\n"), 1):
                for m in re.finditer(r"to_list\((\d+)\)", l):
                    n = int(m.group(1))
                    if n >= 1000:
                        total_1000 += 1
                    if n >= AMBANG_TO_LIST:
                        besar.append(f"{rel}:{i}  to_list({n})")
    routers = sorted((ROOT / "backend/routers").glob("*.py"))
    paged = [p.name for p in routers if "from pagination import" in p.read_text(errors="ignore")]
    bukti = [
        f"to_list(>=1000)          : {total_1000}",
        f"to_list(>={AMBANG_TO_LIST})         : {len(besar)}",
        f"router pakai pagination  : {len(paged)} / {len(routers)}",
        "10 lokasi terbesar:",
        *[f"    {b}" for b in besar[:10]],
    ]
    if besar:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-04 — Query BACA di dalam loop atas data (kandidat N+1)
#        CATATAN: find_one_and_update dalam loop SENGAJA (atomisitas) → dikecualikan.
# ════════════════════════════════════════════════════════════════════════════
def t04() -> None:
    tid, judul = "T-04", "Kandidat N+1: query BACA di dalam loop atas data"
    baca_ops = ("find_one", "find", "count_documents", "aggregate")
    kandidat: list[str] = []
    dikecualikan = 0
    for d in ("backend/routers", "backend/services"):
        base = ROOT / d
        if not base.is_dir():
            lapor(tid, judul, "RALAT", f"{d} TIDAK DITEMUKAN")
            return
        for p in sorted(base.glob("*.py")):
            rel = str(p.relative_to(ROOT))
            lines = p.read_text(errors="ignore").split("\n")
            stack: list[tuple[int, int, str]] = []
            for i, l in enumerate(lines):
                if not l.strip():
                    continue
                ind = len(l) - len(l.lstrip())
                while stack and ind <= stack[-1][0]:
                    stack.pop()
                if re.match(r"\s*(for|while)\s", l):
                    stack.append((ind, i + 1, l.strip()))
                    continue
                if not stack:
                    continue
                m = re.search(r"await db\.(\w+)\.(\w+)", l)
                if not m:
                    continue
                op = m.group(2)
                # loop `range(...)` = terbatas, bukan N+1
                if re.match(r"\s*for\s+\w+\s+in\s+range\(", stack[0][2]):
                    continue
                if op == "find_one_and_update":
                    dikecualikan += 1
                    continue
                if op in baca_ops:
                    kandidat.append(f"{rel}:{i+1}  (loop baris {stack[0][1]})  db.{m.group(1)}.{op}")
    bukti = [
        f"kandidat N+1 (baca)      : {len(kandidat)}",
        f"find_one_and_update loop : {dikecualikan}  <- SENGAJA, JANGAN diubah jadi bulk",
        "10 kandidat pertama:",
        *[f"    {k}" for k in kandidat[:10]],
    ]
    if kandidat:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-06 — Tidak ada CI otomatis; riwayat git tergencet
# ════════════════════════════════════════════════════════════════════════════
def t06() -> None:
    tid, judul = "T-06", "Tidak ada CI otomatis + riwayat git tergencet"
    gh = (ROOT / ".github").is_dir()
    hook = (ROOT / ".git/hooks/pre-commit").is_file()
    try:
        n = subprocess.run(["git", "rev-list", "--count", "HEAD"], cwd=ROOT,
                           capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception as exc:                      # noqa: BLE001
        n = f"(gagal: {exc})"
    gate = (ROOT / "scripts/gate.sh").is_file()
    bukti = [
        f".github/                 : {'ADA' if gh else 'TIDAK ADA'}",
        f".git/hooks/pre-commit    : {'terpasang' if hook else 'TIDAK terpasang'}",
        f"jumlah commit            : {n}",
        f"scripts/gate.sh          : {'ADA (tapi manual)' if gate else 'TIDAK ADA'}",
    ]
    if not gh and not hook:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-07 — CODEBASE_MAP.md melenceng dari kenyataan
# ════════════════════════════════════════════════════════════════════════════
def t07() -> None:
    tid, judul = "T-07", "CODEBASE_MAP.md melenceng dari kenyataan"
    cm = baca("CODEBASE_MAP.md")
    if cm is None:
        lapor(tid, judul, "RALAT", "CODEBASE_MAP.md TIDAK DITEMUKAN")
        return
    rd = ROOT / "backend/routers"
    aktual_router = len(list(rd.glob("*.py"))) if rd.is_dir() else -1
    pasangan = []
    for berkas, pola in (
        ("backend/dependencies.py", r"`dependencies\.py`[^|]*\|[^|]*\|\s*(\d+)\s*\|"),
        ("backend/schemas.py", r"`schemas\.py`[^|]*\|[^|]*\|\s*(\d+)\s*\|"),
        ("backend/server.py", r"`server\.py`[^|]*\|[^|]*\|\s*(\d+)\s*\|"),
    ):
        m = re.search(pola, cm)
        src = baca(berkas)
        if m and src is not None:
            klaim, nyata = int(m.group(1)), len(src.split("\n"))
            pasangan.append((berkas, klaim, nyata))
    bukti = [f"router terdaftar di peta : (peta v1.0, 28 Mei 2026) vs aktual {aktual_router} berkas"]
    melenceng = 0
    for berkas, klaim, nyata in pasangan:
        selisih = abs(nyata - klaim)
        if selisih > max(20, klaim * 0.2):
            melenceng += 1
        bukti.append(f"{berkas:28s}: peta {klaim:5d} baris  vs  aktual {nyata:5d} baris"
                     f"  (selisih {selisih})")
    if melenceng >= 2 or aktual_router > 60:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-08 — SEED_DEMO_ENABLED bawaan "true" (endpoint destruktif hidup by default)
# ════════════════════════════════════════════════════════════════════════════
def t08() -> None:
    tid, judul = "T-08", "SEED_DEMO_ENABLED bawaan 'true' (reset DB hidup by default)"
    s = baca("backend/routers/admin.py")
    if s is None:
        lapor(tid, judul, "RALAT", "backend/routers/admin.py TIDAK DITEMUKAN")
        return
    hit = baris_dari(s, r'SEED_DEMO_ENABLED"\s*,\s*"true"')
    if hit:
        lapor(tid, judul, "TERBUKTI",
              f"backend/routers/admin.py:{hit[0][0]}: {hit[0][1].strip()}")
    else:
        alt = baris_dari(s, r"SEED_DEMO_ENABLED")
        lapor(tid, judul, "GUGUR",
              "bawaan bukan 'true'. Baris terkait:\n  "
              + ("\n  ".join(f"{n}: {l.strip()}" for n, l in alt) or "(tidak ada)"))


# ════════════════════════════════════════════════════════════════════════════
# T-09 — Saran reorder tidak menyaring lifecycle & tak membawa warehouse_id
# ════════════════════════════════════════════════════════════════════════════
def t09() -> None:
    tid, judul = "T-09", "Saran reorder: tanpa filter lifecycle + tanpa warehouse_id"
    s = baca("backend/services/purchase_requisition_service.py")
    if s is None:
        lapor(tid, judul, "RALAT",
              "backend/services/purchase_requisition_service.py TIDAK DITEMUKAN")
        return
    m = re.search(r"async def reorder_suggestions\(.*?\n(.*?)(?=\nasync def |\Z)", s, re.S)
    if not m:
        lapor(tid, judul, "RALAT", "fungsi reorder_suggestions() TIDAK DITEMUKAN")
        return
    badan = m.group(1)
    mulai = s[:m.start()].count("\n") + 1
    q = baris_dari(badan, r"db\.products\.find\(")
    ada_gate = bool(re.search(r"rnd_gate|is_orderable|lifecycle", badan))
    ada_wh = bool(re.search(r'"warehouse_id"', badan))
    # pembanding: create PR memang punya gerbangnya
    gate_di_create = baris_dari(s, r"rnd_gate\.assert_orderable")
    bukti = [
        f"reorder_suggestions() mulai baris ~{mulai}",
        f"query produk            : baris ~{mulai + q[0][0] - 1 if q else '?'}"
        + (f"  -> {q[0][1].strip()}" if q else "  -> TIDAK DITEMUKAN"),
        f"filter lifecycle/rnd_gate di saran : {'ADA' if ada_gate else 'TIDAK ADA'}",
        f"field warehouse_id di baris saran  : {'ADA' if ada_wh else 'TIDAK ADA'}",
        f"pembanding rnd_gate.assert_orderable dipakai saat BUAT PR : "
        f"baris {[n for n, _ in gate_di_create] or 'TIDAK ADA'}",
    ]
    if (not ada_gate or not ada_wh) and gate_di_create:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-10 — POST /ar-receipts: validasi skema jalan sebelum cek izin
# ════════════════════════════════════════════════════════════════════════════
def t10() -> None:
    tid, judul = "T-10", "POST /ar-receipts: 422 mendahului 403 (bentuk skema bocor)"
    s = baca("backend/routers/ar_receipts.py")
    if s is None:
        lapor(tid, judul, "RALAT", "backend/routers/ar_receipts.py TIDAK DITEMUKAN")
        return
    m = re.search(r'@router\.post\("/ar-receipts"\)\s*\n'
                  r'async def (\w+)\(([^)]*)\)[^:]*:\s*\n(.*?)(?=\n@router\.|\Z)', s, re.S)
    if not m:
        lapor(tid, judul, "RALAT", 'endpoint POST "/ar-receipts" TIDAK DITEMUKAN')
        return
    fn, sig, badan = m.group(1), m.group(2), m.group(3)
    n = s[:m.start()].count("\n") + 1
    body_model = re.search(r"(\w+)\s*:\s*(\w*(?:Payload|Input|In|Request|Model)\w*)", sig)
    perm = re.search(r"require_permission|require_role", badan)
    bukti = [
        f"endpoint di baris ~{n}, fungsi {fn}()",
        f"tanda tangan: {sig.strip()[:100]}",
        f"model body sebagai PARAMETER : {'YA -> ' + body_model.group(0) if body_model else 'TIDAK'}",
        f"cek izin di dalam badan      : {'YA' if perm else 'TIDAK'}",
        "arti: FastAPI memvalidasi body SEBELUM badan fungsi jalan, jadi payload"
        " salah -> 422 walau pemanggil tak berwenang.",
    ]
    if body_model and perm:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
# T-11 — approve_order 409 INVALID_TRANSITION setelah SO auto-approved
# ════════════════════════════════════════════════════════════════════════════
def t11() -> None:
    tid, judul = "T-11", "approve_order -> 409 INVALID_TRANSITION setelah SO auto-approved"
    ex = baca("backend/routers/sales_orders_extra.py")
    ap = baca("backend/routers/so_approvals.py")
    if ex is None or ap is None:
        lapor(tid, judul, "RALAT",
              "sales_orders_extra.py atau so_approvals.py TIDAK DITEMUKAN")
        return
    auto = baris_dari(ap, r'"approved",\s*actor\["name"\],\s*"order_approved"')
    m = re.search(r'@router\.post\("/sales-orders/\{order_id\}/approve"\)(.*?)'
                  r'(?=\n@router\.|\Z)', ex, re.S)
    if not m:
        lapor(tid, judul, "RALAT", "endpoint approve SO TIDAK DITEMUKAN")
        return
    badan = m.group(1)
    n = ex[:m.start()].count("\n") + 1
    trans = re.search(r'_transition\(\s*order_id,\s*(\[[^\]]*\])', badan)
    daftar = trans.group(1) if trans else "?"
    sudah_approved_ditangani = ('"approved"' in daftar) or bool(
        re.search(r'status.*==.*"approved".*return|already_approved|sudah disetujui', badan))
    bukti = [
        f"so_approvals.py auto-transisi ke 'approved' : baris {[x for x, _ in auto] or 'TIDAK ADA'}",
        f"approve_order() di sales_orders_extra.py    : baris ~{n}",
        f"expected_from pada _transition              : {daftar}",
        f"status 'approved' ditangani idempoten       : {'YA' if sudah_approved_ditangani else 'TIDAK'}",
    ]
    if auto and trans and not sudah_approved_ditangani:
        lapor(tid, judul, "TERBUKTI", "\n".join(bukti))
    else:
        lapor(tid, judul, "GUGUR", "\n".join(bukti))


# ════════════════════════════════════════════════════════════════════════════
PEMERIKSA = [t01, t02, t03, t04, t06, t07, t08, t09, t10, t11]
# CATATAN: T-05 (korpus uji 55 gagal) TIDAK bisa diperiksa statik — ia menuntut
# server + Mongo hidup. Lihat §T-05 di INSTRUKSI_PERBAIKAN_2026-09.md: agen WAJIB
# menjalankan ulang korpusnya sendiri, DILARANG mengutip coverage_data/*.json lama.


def main() -> int:
    segel = hashlib.sha256(SELF.read_bytes()).hexdigest()[:16]
    print("=" * 78)
    print("  VERIFIKATOR TEMUAN AUDIT — Kain Nusantara")
    print(f"  akar repo : {ROOT}")
    print(f"  segel     : sha256:{segel}  (berkas ini)")
    print("=" * 78)

    for fn in PEMERIKSA:
        try:
            fn()
        except Exception as exc:                  # noqa: BLE001
            lapor(fn.__name__.upper().replace("T", "T-"), fn.__doc__ or fn.__name__,
                  "RALAT", f"pemeriksa melempar {type(exc).__name__}: {exc}")

    n_terbukti = n_gugur = n_ralat = 0
    for tid, status, judul, bukti in hasil:
        warna = {"TERBUKTI": C_BAD, "GUGUR": C_OK, "RALAT": C_WARN}[status]
        print(f"\n{warna}[{status:8s}]{C_END} {tid} — {judul}")
        for l in bukti.split("\n"):
            print(f"    {C_DIM}{l}{C_END}")
        n_terbukti += status == "TERBUKTI"
        n_gugur += status == "GUGUR"
        n_ralat += status == "RALAT"

    print("\n" + "=" * 78)
    print(f"  TERBUKTI (masih cacat) : {n_terbukti}")
    print(f"  GUGUR (bersih/sudah)   : {n_gugur}")
    print(f"  RALAT (tak bisa diuji) : {n_ralat}")
    print(f"  segel: sha256:{segel}")
    print("=" * 78)
    if n_ralat:
        return 2
    return 1 if n_terbukti else 0


if __name__ == "__main__":
    sys.exit(main())
