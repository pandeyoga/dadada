"""SATU master komponen biaya (W2-C, keputusan #16 / FN-01): katalog `price_components` = SUMBER, kebijakan All-in = ATURAN.

Latar belakang. Dulu ada DUA master berbeda untuk "komponen biaya":
  * katalog `price_components` (tab Komponen Biaya; kode, label, kelompok, perlakuan keuangan, satu akun GL, nilai bawaan) —
    tidak dibaca logika tagihan/jurnal mana pun (FN-01);
  * master All-in `cost_components` + `allin_schemes` (tab Biaya All-in; cara hitung, persen/nominal, ditagih/ditalangi, tiga akun GL,
    hanya-KPR) — yang BENAR-BENAR menagih dan menjurnal (`allin_engine.resolve_scheme`).

Rancangan penyatuan (bertahap, tanpa menghapus satu pun dan tanpa mengubah tagihan/jurnal yang sudah ada):
  1. Baris katalog yang berpasangan membawa blok `cost` = field otoritatif komponen biaya (cara hitung, persen, nominal,
     ditagih/ditalangi, GL beban/titipan/AP, hanya-KPR). Kolom lama katalog (`gl_account`, `value`, `applies_schemes`) menjadi
     TURUNAN blok itu (tidak lagi bisa saling bertentangan); `label` ↔ nama komponen, `active` ↔ is_active.
  2. Master All-in MEREFERENSI katalog lewat `cost_components.catalog_code` (migrasi idempoten `migrate`, tidak mengubah angka apa pun).
  3. `diff` = laporan selisih katalog↔aturan (kolom per kolom, termasuk selisih NYATA kolom lama seperti akun 2-1450 vs 2-1470).
  4. Pengaturan `cost.master_mode`: `bayangan` (bawaan; tagihan tetap dari All-in, katalog hanya dibandingkan) · `katalog_sumber`
     (definisi komponen dibaca dari katalog lewat rujukan; aturan All-in hanya menentukan komponen mana yang berlaku). Opsi kedua
     hanya sah bila selisih = 0 DAN uji ekuivalensi (hitung ulang skema aktif di kedua mode) identik — `unavailable_reason`.
  5. Pada `katalog_sumber` perubahan katalog menulis tembus (write-through) ke master All-in sehingga selisih tetap 0 dan
     kembali ke `bayangan` selalu aman; mengubah komponen di tab Biaya All-in ditolak (ubah di katalog).
"""
import logging

import cost_limits
import cost_master_rules as cmr
import policy
from core_utils import new_id, now_iso
from db import db
from idempotency import mutex

logger = logging.getLogger("sipro.costmaster")

KEY_MODE = "cost.master_mode"
BAYANGAN, KATALOG = "bayangan", "katalog_sumber"
COST_FIELDS = ("calc_method", "pct", "amount", "default_treatment", "gl_expense", "gl_liability", "gl_ap", "kpr_only")
ALIAS = {"BOOKING": "BOOKING_FEE"}   # dua kode untuk uang yang sama; dibiarkan terpisah (lihat catatan di FIELD_MAP/diff)
PROBE_PRICES = (1, 100_000_000, 850_000_000)
PROBE_KINDS = ("kpr", "cash_keras")
ALL_SCHEMES = {"cash_keras", "cash_bertahap", "kpr"}

# Peta field kedua master (deliverable (a)): apa dibandingkan dengan apa, dan di mana pembawa otoritatifnya setelah penyatuan.
FIELD_MAP = [
    {"katalog": "code", "aturan": "code", "pembawa": "katalog", "catatan": "Kunci gabungan. BOOKING (aturan) ≈ BOOKING_FEE (katalog): "
     "uang yang sama dengan dua kode; dibiarkan terpisah karena BOOKING_FEE = baris harga (titipan 2-1450) dan BOOKING = komponen pelunas."},
    {"katalog": "label", "aturan": "name", "pembawa": "katalog", "catatan": "Nama tampil di invoice/kontrak."},
    {"katalog": "active", "aturan": "is_active", "pembawa": "katalog", "catatan": "Nonaktif = tidak ikut snapshot baru."},
    {"katalog": "cost.calc_method", "aturan": "calc_method", "pembawa": "katalog", "catatan": "Katalog lama hanya punya 'calc: manual' (tanpa rumus)."},
    {"katalog": "cost.pct", "aturan": "pct", "pembawa": "katalog", "catatan": "Katalog lama tidak punya persen."},
    {"katalog": "cost.amount  (kolom lama: value)", "aturan": "amount", "pembawa": "katalog", "catatan": "Nilai bawaan lama katalog 0 untuk semua komponen biaya."},
    {"katalog": "cost.default_treatment", "aturan": "default_treatment", "pembawa": "katalog",
     "catatan": "ditagih ke pembeli (customer_pass_through) vs ditalangi developer (developer_borne); skema All-in tetap boleh menimpa per skema."},
    {"katalog": "finance_treatment", "aturan": "(ekuivalen default_treatment)", "pembawa": "katalog",
     "catatan": "Perlakuan keuangan/pajak (pass_through, tax_out, …). Komponen ditagih ke pembeli harus pass_through."},
    {"katalog": "cost.gl_liability / cost.gl_expense  (kolom lama: gl_account)", "aturan": "gl_liability / gl_expense", "pembawa": "katalog",
     "catatan": "Katalog lama menulis 2-1450 (titipan booking); jurnal All-in sebenarnya ke 2-1470 (titipan biaya) / 6-1700 (beban)."},
    {"katalog": "cost.gl_ap", "aturan": "gl_ap", "pembawa": "katalog", "catatan": "Utang usaha beban developer (selalu 2-1100)."},
    {"katalog": "cost.kpr_only  (kolom lama: applies_schemes)", "aturan": "kpr_only", "pembawa": "katalog", "catatan": "applies_schemes=['kpr'] ≡ hanya KPR."},
    {"katalog": "group, order, note, percent_of, calc", "aturan": "—", "pembawa": "katalog", "catatan": "Hanya katalog (tampilan/kelompok)."},
    {"katalog": "—", "aturan": "allin_schemes.items[].treatment / override_amount", "pembawa": "aturan",
     "catatan": "ATURAN per skema/proyek: komponen mana yang berlaku, ditagih atau ditalangi dalam skema itu, nominal terkunci."},
]


# ============================================================ turunan & pembanding
def kpr_only_of(applies) -> bool:
    return bool(applies) and set(applies) == {"kpr"}


def derive_legacy(cost: dict) -> dict:
    """Kolom lama katalog yang DITURUNKAN dari blok biaya (satu arah — tidak bisa bertentangan)."""
    dev = cost.get("default_treatment") == "developer_borne"
    return {"gl_account": cost.get("gl_expense") if dev else cost.get("gl_liability"),
            "applies_schemes": ["kpr"] if cost.get("kpr_only") else [],
            "value": int(cost.get("amount") or 0) if cost.get("calc_method") == "nominal_tetap" else 0}


def cost_of_rule(a: dict) -> dict:
    """Blok biaya katalog dari satu dokumen master All-in."""
    return {"calc_method": a.get("calc_method"), "pct": float(a.get("pct") or 0), "amount": int(a.get("amount") or 0),
            "default_treatment": a.get("default_treatment"), "gl_expense": a.get("gl_expense"),
            "gl_liability": a.get("gl_liability"), "gl_ap": a.get("gl_ap"), "kpr_only": bool(a.get("kpr_only"))}


def _d(field, label, kat, atu, kind="biaya") -> dict:
    return {"field": field, "label": label, "katalog": kat, "aturan": atu, "kind": kind}


def compare(a: dict, k: dict) -> list:
    """Selisih satu pasangan (dokumen aturan `a`, baris katalog `k`) — daftar dict; kosong = sama."""
    out = []
    cost = k.get("cost")
    if cost:
        mine = cost_of_rule(a)
        if (a.get("name") or "") != (k.get("label") or ""):
            out.append(_d("name", "Nama komponen", k.get("label"), a.get("name")))
        if bool(a.get("is_active", True)) != bool(k.get("active", True)):
            out.append(_d("is_active", "Aktif", bool(k.get("active", True)), bool(a.get("is_active", True))))
        for f in COST_FIELDS:
            kv, av = cost.get(f), mine.get(f)
            if f == "pct":
                kv, av = float(kv or 0), float(av or 0)
            if f in ("amount",):
                kv, av = int(kv or 0), int(av or 0)
            if f == "kpr_only":
                kv, av = bool(kv), bool(av)
            if kv != av:
                out.append(_d(f, f, kv, av))
        der = derive_legacy(cost)   # konsistensi internal katalog: kolom lama harus sama dengan turunan blok biaya
        if k.get("gl_account") != der["gl_account"]:
            out.append(_d("gl_account", "Akun GL (kolom lama katalog)", k.get("gl_account"), der["gl_account"], "kolom_lama"))
        if int(k.get("value") or 0) != der["value"]:
            out.append(_d("value", "Nilai bawaan (kolom lama katalog)", int(k.get("value") or 0), der["value"], "kolom_lama"))
        if kpr_only_of(k.get("applies_schemes")) != bool(cost.get("kpr_only")):
            out.append(_d("applies_schemes", "Berlaku pada skema (kolom lama katalog)", k.get("applies_schemes"),
                          der["applies_schemes"], "kolom_lama"))
        if cost.get("default_treatment") == "customer_pass_through" and k.get("finance_treatment") != "pass_through":
            out.append(_d("finance_treatment", "Perlakuan keuangan (kolom lama katalog)", k.get("finance_treatment"),
                          "pass_through", "kolom_lama"))
        return out
    # belum bermigrasi: tunjukkan selisih NYATA kolom lama katalog terhadap aturan berjalan
    liab = a.get("gl_expense") if a.get("default_treatment") == "developer_borne" else a.get("gl_liability")
    if (k.get("gl_account") or None) != liab:
        out.append(_d("gl_account", "Akun GL", k.get("gl_account"), liab, "kolom_lama"))
    if (k.get("calc") or "manual") != "manual" or a.get("calc_method") != "nominal_tetap" or int(k.get("value") or 0) != int(a.get("amount") or 0):
        out.append(_d("calc", "Cara hitung / nilai bawaan",
                      f"{k.get('calc') or 'manual'} · Rp {int(k.get('value') or 0):,}".replace(",", "."),
                      (f"{a.get('calc_method')} · Rp {int(a.get('amount') or 0):,}" if a.get("calc_method") == "nominal_tetap"
                       else f"{a.get('calc_method')} · {float(a.get('pct') or 0):g}%").replace(",", "."), "kolom_lama"))
    if a.get("default_treatment") == "customer_pass_through" and k.get("finance_treatment") != "pass_through":
        out.append(_d("finance_treatment", "Perlakuan keuangan", k.get("finance_treatment"), "pass_through", "kolom_lama"))
    if kpr_only_of(k.get("applies_schemes")) != bool(a.get("kpr_only")):
        out.append(_d("applies_schemes", "Berlaku pada skema", k.get("applies_schemes"),
                      ["kpr"] if a.get("kpr_only") else "semua skema", "kolom_lama"))
    if bool(a.get("is_active", True)) != bool(k.get("active", True)):
        out.append(_d("is_active", "Aktif", bool(k.get("active", True)), bool(a.get("is_active", True)), "kolom_lama"))
    if (a.get("name") or "") != (k.get("label") or ""):
        out.append(_d("name", "Nama komponen", k.get("label"), a.get("name"), "kolom_lama"))
    return out


# ============================================================ laporan selisih
async def _load(org: str):
    rules = await db.cost_components.find({"org_id": org}, {"_id": 0}).sort("code", 1).to_list(None)
    cat = await db.price_components.find({"org_id": org}, {"_id": 0}).sort("order", 1).to_list(None)
    schemes = await db.allin_schemes.find({"org_id": org}, {"_id": 0}).to_list(None)
    return rules, cat, schemes


def _rows(rules, cat, schemes) -> list:
    by_cat = {k["code"]: k for k in cat}
    rows, used = [], set()
    for a in rules:
        code = a.get("catalog_code") or a["code"]
        k = by_cat.get(code)
        if not k:
            rows.append({"code": a["code"], "name": a.get("name"), "status": "hanya_aturan", "blocking": True, "diffs": [],
                         "catatan": "Belum ada di katalog — jalankan migrasi."})
            continue
        used.add(code)
        diffs = compare(a, k)
        if not k.get("cost"):
            st, blk = "belum_dimigrasi", True
        else:
            st, blk = ("beda" if diffs else "sama"), bool(diffs)
        rows.append({"code": a["code"], "name": a.get("name"), "status": st, "blocking": blk, "diffs": diffs,
                     "linked": bool(a.get("catalog_code")), "catatan": ""})
    for k in cat:
        if k["code"] in used:
            continue
        if k.get("cost"):
            rows.append({"code": k["code"], "name": k.get("label"), "status": "hanya_katalog_biaya", "blocking": False, "diffs": [],
                         "catatan": "Komponen biaya di katalog yang belum didaftarkan ke master All-in (migrasi mendaftarkannya)."})
        else:
            rows.append({"code": k["code"], "name": k.get("label"), "status": "hanya_katalog", "blocking": False, "diffs": [],
                         "catatan": ("Baris harga/pajak/potongan — bukan komponen biaya All-in." if k["code"] != "BOOKING_FEE" else
                                     "Baris harga booking fee; padanan komponen pelunas All-in adalah BOOKING.")})
    known = {a["code"] for a in rules}
    for s in schemes:
        for it in s.get("items") or []:
            if it.get("component_code") not in known:
                rows.append({"code": it.get("component_code"), "name": f"skema {s.get('code')}", "status": "rujukan_putus", "blocking": True,
                             "diffs": [], "catatan": f"Skema {s.get('code')} merujuk komponen yang tidak ada di master All-in."})
    return rows


async def _usage(org: str) -> list:
    """Kode komponen pada SNAPSHOT deal/kontrak yang sudah terbit (beku; tidak terpengaruh mode) dan keterkenalannya."""
    pipe = [{"$match": {"org_id": org, "costs.components": {"$exists": True}}}, {"$unwind": "$costs.components"},
            {"$group": {"_id": "$costs.components.code", "n": {"$sum": 1}, "sumber": {"$addToSet": "$costs.components.source"}}}]
    cnt = {}
    for coll in ("contracts", "deals"):
        async for r in db[coll].aggregate(pipe):
            c = cnt.setdefault(r["_id"], {"code": r["_id"], "n": 0, "sumber": set()})
            c["n"] += r["n"]
            c["sumber"] |= set(x for x in r["sumber"] if x)
    known = {k["code"] for k in await db.price_components.find({"org_id": org}, {"_id": 0, "code": 1}).to_list(None)}
    rules = {a["code"] for a in await db.cost_components.find({"org_id": org}, {"_id": 0, "code": 1}).to_list(None)}
    return [{"code": c["code"], "n": c["n"], "sumber": sorted(c["sumber"]), "di_katalog": c["code"] in known, "di_aturan": c["code"] in rules}
            for c in sorted(cnt.values(), key=lambda x: x["code"])]


async def diff(org: str, *, usage: bool = False, probe: bool = False) -> dict:
    rules, cat, schemes = await _load(org)
    rows = _rows(rules, cat, schemes)
    blocking = [r for r in rows if r["blocking"]]
    n_diff = sum(max(1, len(r["diffs"])) for r in blocking)
    out = {"field_map": FIELD_MAP, "rows": rows,
           "summary": {"komponen_aturan": len(rules), "baris_katalog": len(cat), "skema": len(schemes),
                       "baris_selisih": len(blocking), "selisih": n_diff, "nol": not blocking,
                       "informasi": sum(1 for r in rows if not r["blocking"] and r["status"] not in ("sama",))}}
    if usage:
        out["snapshot_kode"] = await _usage(org)
    if probe:
        out["probe"] = await probe_equivalence(org)
    return out


async def probe_equivalence(org: str, limit: int = 150) -> dict:
    """Bukti ekuivalensi pada DATA: hitung ulang tiap skema AKTIF di kedua mode untuk beberapa harga/jenis skema; semua harus identik.
    Bila skema aktif lebih dari `limit`, bukti TIDAK dianggap penuh (`lengkap` false) — tidak ada klaim "terbukti" yang separuh."""
    import allin_engine as ae
    mism, n = [], 0
    total = await db.allin_schemes.count_documents({"org_id": org, "is_active": True})
    async for s in db.allin_schemes.find({"org_id": org, "is_active": True}, {"_id": 0, "id": 1, "code": 1}).limit(limit):
        for price in PROBE_PRICES:
            for kind in PROBE_KINDS:
                n += 1
                try:
                    a = await ae.resolve_scheme(org, s["id"], price, None, kind, booking_fee=5_000_000, mode=BAYANGAN)
                    b = await ae.resolve_scheme(org, s["id"], price, None, kind, booking_fee=5_000_000, mode=KATALOG)
                except ValueError as e:
                    mism.append({"skema": s.get("code"), "harga": price, "jenis": kind, "sebab": str(e)[:160]})
                    continue
                b = {k: v for k, v in b.items() if k not in ("master_mode",)}
                b["components"] = [{k: v for k, v in c.items() if k != "catalog_code"} for c in b["components"]]
                if a != b:
                    mism.append({"skema": s.get("code"), "harga": price, "jenis": kind, "sebab": "hasil hitung berbeda"})
    return {"diperiksa": n, "skema_aktif": total, "beda": len(mism), "contoh": mism[:5], "identik": not mism, "lengkap": total <= limit}


async def unavailable_reason(org: str, probe: bool = False):
    """None bila `katalog_sumber` sah dipilih (selisih = 0 [+ ekuivalensi identik]); selain itu alasan jujur."""
    return reason_of(await diff(org, probe=probe), probe)


def reason_of(d: dict, probe: bool = False):
    s = d["summary"]
    if not s["nol"]:
        contoh = ", ".join(r["code"] for r in d["rows"] if r["blocking"])[:120]
        return (f"masih ada {s['baris_selisih']} komponen yang berselisih antara katalog dan aturan All-in ({contoh}). "
                "Buka Pusat Konfigurasi › Komponen Biaya › Selisih, jalankan 'Migrasi ke katalog' lalu 'Selaraskan katalog' "
                "(atau perbaiki selisihnya), kemudian pilih ulang.")
    if probe and not d["probe"]["lengkap"]:
        return (f"ekuivalensi tidak bisa dibuktikan penuh: ada {d['probe']['skema_aktif']} skema aktif (batas uji 150). Nonaktifkan "
                "skema yang tidak dipakai lalu coba lagi.")
    if probe and not d["probe"]["identik"]:
        return (f"uji ekuivalensi gagal: {d['probe']['beda']} dari {d['probe']['diperiksa']} perhitungan skema berbeda hasilnya "
                f"antara kedua sumber (mis. {d['probe']['contoh'][0]}).")
    return None


# ============================================================ mode
async def mode_for(org: str, project_id: str = None) -> str:
    return await policy.resolve(KEY_MODE, org_id=org, project_id=project_id)


async def source_components(org: str, codes) -> dict:
    """Definisi komponen untuk mode `katalog_sumber`: dari baris katalog lewat RUJUKAN (`cost_components.catalog_code`, bila kosong
    kode yang sama). Komponen yang rujukannya tak punya blok biaya → galat jelas (jangan diam-diam menghilangkan biaya dari tagihan)."""
    codes = list(codes)
    refs = {a["code"]: a.get("catalog_code") or a["code"]
            for a in await db.cost_components.find({"org_id": org, "code": {"$in": codes}}, {"_id": 0, "code": 1, "catalog_code": 1}).to_list(None)}
    cat = {k["code"]: k for k in await db.price_components.find(
        {"org_id": org, "code": {"$in": list(set(refs.values()) | set(codes))}}, {"_id": 0}).to_list(None)}
    out = {}
    for code in codes:
        k = cat.get(refs.get(code, code))
        if not k or not k.get("cost"):
            raise ValueError(f"Komponen {code} belum ada di katalog dengan blok biaya (mode 'katalog sebagai sumber') — jalankan "
                             "'Migrasi ke katalog' di Pusat Konfigurasi › Komponen Biaya.")
        if k.get("active") is False:
            continue
        c = k["cost"]
        out[code] = {"code": code, "catalog_code": k["code"], "name": k.get("label") or code, "is_active": True,
                     **{f: c.get(f) for f in COST_FIELDS}, "kpr_only": bool(c.get("kpr_only"))}
    return out


# ============================================================ migrasi & selaras
def _catalog_row_from_rule(a: dict, order: int, ts: str) -> dict:
    cost = cost_of_rule(a)
    note = a.get("note") or ("Nominal = booking fee deal; booking fee yang dibayar melunasi komponen ini." if a["code"] == "BOOKING" else None)
    return {"id": new_id(), "org_id": a["org_id"], "code": a["code"], "label": a.get("name") or a["code"], "group": "biaya",
            "calc": "manual", "percent_of": None, "finance_treatment": "pass_through", "order": order, "note": note,
            "active": bool(a.get("is_active", True)), "created_by": "w2c-migrasi", "created_at": ts, "updated_at": ts,
            "cost": cost, **derive_legacy(cost)}


async def migrate(org: str, actor: str) -> dict:
    """Migrasi IDEMPOTEN, tidak merusak: (1) baris katalog untuk komponen All-in yang belum ada, (2) blok biaya untuk baris katalog yang
    berpasangan tetapi belum membawanya (kolom lama/label/aktif TIDAK ditimpa — selisihnya dilaporkan), (3) rujukan `catalog_code` pada
    master All-in, (4) pendaftaran baris katalog bermuatan biaya ke master All-in. TIDAK menyentuh skema, snapshot, tagihan, jurnal."""
    async with mutex(f"costmaster.migrate:{org}", what="Migrasi master komponen biaya"):
        ts = now_iso()
        rules, cat, _ = await _load(org)
        by_cat = {k["code"]: k for k in cat}
        res = {"katalog_dibuat": 0, "blok_biaya_diisi": 0, "rujukan_dipasang": 0, "aturan_didaftarkan": 0}
        nxt = max([int(k.get("order") or 0) for k in cat] + [0])
        for a in rules:
            code = a.get("catalog_code") or a["code"]
            k = by_cat.get(code)
            if not k:
                nxt += 10
                row = _catalog_row_from_rule(a, nxt, ts)
                await db.price_components.insert_one(dict(row))
                by_cat[code] = row
                res["katalog_dibuat"] += 1
            elif not k.get("cost"):
                await db.price_components.update_one({"id": k["id"], "cost": {"$exists": False}},
                                                     {"$set": {"cost": cost_of_rule(a), "updated_at": ts, "updated_by": actor}})
                res["blok_biaya_diisi"] += 1
            if a.get("catalog_code") != code:
                await db.cost_components.update_one({"id": a["id"], "org_id": org}, {"$set": {"catalog_code": code, "updated_at": ts}})
                res["rujukan_dipasang"] += 1
        known = {a["code"] for a in rules}
        for k in (await db.price_components.find({"org_id": org, "cost": {"$exists": True}}, {"_id": 0}).to_list(None)):
            if k["code"] in known:
                continue
            c = k["cost"]
            await db.cost_components.insert_one({
                "id": new_id(), "org_id": org, "code": k["code"], "name": k.get("label") or k["code"], "is_active": bool(k.get("active", True)),
                "catalog_code": k["code"], "created_at": ts, "updated_at": ts, **{f: c.get(f) for f in COST_FIELDS}})
            res["aturan_didaftarkan"] += 1
        res["sudah_selaras"] = not any(res[x] for x in ("katalog_dibuat", "blok_biaya_diisi", "rujukan_dipasang", "aturan_didaftarkan"))
        if not res["sudah_selaras"]:
            await db.cost_master_log.insert_one({"id": new_id(), "org_id": org, "at": ts, "by": actor, "action": "migrate", "result": res})
        return res


async def sync_to_catalog(org: str, actor: str, reason: str) -> dict:
    """'Selaraskan katalog': samakan baris katalog (blok biaya, label, aktif, kolom turunan) dengan aturan All-in yang BERJALAN. Tagihan
    tidak berubah (All-in tetap sumber pada bayangan). Nilai katalog lama dicatat di `cost_master_log` (dapat ditinjau)."""
    if len((reason or "").strip()) < 10:
        raise ValueError("Alasan menyelaraskan katalog wajib (minimal 10 huruf).")
    if await db.settings.find_one({"org_id": org, "key": KEY_MODE, "value": KATALOG}, {"_id": 1}):
        # katalog = SUMBER di org/proyek ini: menimpa katalog dengan aturan All-in (yang bukan sumber) akan membatalkan perubahan katalog
        raise ValueError("Katalog sedang menjadi sumber (cost.master_mode = katalog_sumber di organisasi/proyek) — menimpa katalog dengan "
                         "aturan All-in ditolak. Gunakan 'aturan_ikut_katalog' atau kembalikan mode ke bayangan dulu.")
    mig = await migrate(org, actor)
    async with mutex(f"costmaster.sync:{org}", what="Penyelarasan katalog komponen biaya"):
        ts = now_iso()
        rules, cat, _ = await _load(org)
        by_cat = {k["code"]: k for k in cat}
        changes = []
        for a in rules:
            k = by_cat.get(a.get("catalog_code") or a["code"])
            if not k:
                continue
            ds = compare(a, k)
            if not ds:
                continue
            cost = cost_of_rule(a)
            new = {"cost": cost, "label": a.get("name") or a["code"], "active": bool(a.get("is_active", True)), **derive_legacy(cost)}
            if cost["default_treatment"] == "customer_pass_through":
                new["finance_treatment"] = "pass_through"
            await db.price_components.update_one({"id": k["id"]}, {"$set": {**new, "updated_at": ts, "updated_by": actor}})
            changes.append({"code": a["code"], "diffs": [{"field": d["field"], "dari": d["katalog"], "ke": d["aturan"]} for d in ds]})
        await db.cost_master_log.insert_one({"id": new_id(), "org_id": org, "at": ts, "by": actor, "action": "sync_to_catalog",
                                             "reason": reason.strip(), "changes": changes})
        return {"migrasi": mig, "diselaraskan": len(changes), "perubahan": changes}


async def sync_to_rules(org: str, actor: str, reason: str) -> dict:
    """Perbaikan arah sebaliknya — HANYA pada mode katalog_sumber (katalog = sumber): salin definisi katalog ke master All-in."""
    if (await mode_for(org)) != KATALOG:
        raise ValueError("Menyalin katalog ke master All-in hanya untuk mode 'katalog sebagai sumber'. Pada mode bayangan All-in adalah "
                         "sumber tagihan — ubah komponen di tab Biaya All-in lalu 'Selaraskan katalog'.")
    if len((reason or "").strip()) < 10:
        raise ValueError("Alasan wajib (minimal 10 huruf).")
    n = 0
    for k in await db.price_components.find({"org_id": org, "cost": {"$exists": True}}, {"_id": 0}).to_list(None):
        n += await _write_through(org, k)
    await db.cost_master_log.insert_one({"id": new_id(), "org_id": org, "at": now_iso(), "by": actor, "action": "sync_to_rules",
                                         "reason": reason.strip(), "changed": n})
    return {"diselaraskan": n}


# ============================================================ katalog: validasi + tulis tembus
async def prepare_catalog_patch(org: str, cur: dict, patch: dict) -> dict:
    """Validasi perubahan baris katalog (FN-02 versi katalog): blok `cost` divalidasi dengan aturan master All-in yang SAMA (rentang,
    enum, akun GL nyata & bertipe sesuai, batas nominal), kolom turunan dihitung dari blok biaya, dan batas nominal berlaku pula pada
    `value` (nilai bawaan lama)."""
    patch = dict(patch)
    limit = await cost_limits.max_amount(org)
    if "value" in patch:
        cost_limits.check(patch["value"], limit, "Nilai bawaan komponen", stored=(cur or {}).get("value"))
    new_cost = patch.pop("cost", None)
    has_cost = bool((cur or {}).get("cost")) or new_cost is not None
    if new_cost is not None:
        bad = [f for f in new_cost if f not in COST_FIELDS]
        if bad:
            raise ValueError(f"Field blok biaya tidak dikenal: {', '.join(bad)} (sah: {', '.join(COST_FIELDS)}).")
    if not has_cost:
        return patch
    merged = {**((cur or {}).get("cost") or {}), **(new_cost or {})}
    if new_cost is None:   # blok biaya tidak diubah (mis. hanya nama/aktif): tidak divalidasi ulang — akun yang kemudian dinonaktifkan tak boleh menghalangi
        cost = {f: merged.get(f) for f in COST_FIELDS}
        der = derive_legacy(cost)
        for f in ("gl_account", "value"):
            if f in patch and patch[f] != der[f]:
                raise ValueError(f"{'Akun GL' if f == 'gl_account' else 'Nilai bawaan'} komponen biaya diturunkan dari blok biaya "
                                 "(GL titipan/beban, cara hitung, nominal) — ubah lewat blok biaya, bukan langsung.")
        if "applies_schemes" in patch and kpr_only_of(patch["applies_schemes"]) != bool(cost["kpr_only"]):
            raise ValueError("'Berlaku pada skema' diturunkan dari blok biaya (hanya-KPR) — ubah lewat blok biaya, bukan langsung.")
        if cost["default_treatment"] == "customer_pass_through" and patch.get("finance_treatment", "pass_through") != "pass_through":
            raise ValueError("Komponen yang ditagih ke pembeli harus berperlakuan keuangan 'Titipan pelanggan (pass_through)'.")
        for f in ("gl_account", "value", "applies_schemes"):
            patch.pop(f, None)   # sama dengan turunan (atau setara): tidak perlu ditulis ulang
        return patch
    code = (cur or {}).get("code") or patch.get("code")
    label = patch.get("label") or (cur or {}).get("label") or code
    if code == "BOOKING" and (cur or {}).get("cost"):   # komponen khusus: cara hitung & nominal terkunci (= booking fee deal)
        for f in ("calc_method", "amount", "pct"):
            merged[f] = (cur["cost"]).get(f)
    data = {"code": code, "name": label, **{f: merged.get(f) for f in COST_FIELDS if merged.get(f) is not None}}
    data.setdefault("calc_method", merged.get("calc_method"))
    clean = await cmr.clean_component(org, data, creating=True, current=(cur or {}).get("cost"))
    clean.pop("code", None)
    clean.pop("name", None)
    cost = {f: clean.get(f, merged.get(f)) for f in COST_FIELDS}
    cost["kpr_only"] = bool(merged.get("kpr_only"))
    cost["pct"] = float(cost.get("pct") or 0)
    cost["amount"] = int(cost.get("amount") or 0)
    der = derive_legacy(cost)
    if (cur or {}).get("cost"):   # baris yang SUDAH membawa blok biaya: kolom turunan tidak boleh diubah langsung (tak ada kontradiksi)
        if "applies_schemes" in patch and kpr_only_of(patch["applies_schemes"]) != bool(cost["kpr_only"]):
            raise ValueError("'Berlaku pada skema' diturunkan dari blok biaya (hanya-KPR) — ubah lewat blok biaya, bukan langsung.")
        for f in ("gl_account", "value"):
            if f in patch and patch[f] != der[f]:
                raise ValueError(f"{'Akun GL' if f == 'gl_account' else 'Nilai bawaan'} komponen biaya diturunkan dari blok biaya "
                                 "(GL titipan/beban, cara hitung, nominal) — ubah lewat blok biaya, bukan langsung.")
    patch["cost"] = cost
    patch.update(der)
    if "applies_schemes" in patch and kpr_only_of(patch["applies_schemes"]) == bool(cost["kpr_only"]):
        patch["applies_schemes"] = der["applies_schemes"]
    if cost["default_treatment"] == "customer_pass_through":
        patch.setdefault("finance_treatment", "pass_through")
        if patch["finance_treatment"] != "pass_through":
            raise ValueError("Komponen yang ditagih ke pembeli harus berperlakuan keuangan 'Titipan pelanggan (pass_through)'.")
    return patch


async def _write_through(org: str, k: dict) -> int:
    """Salin definisi satu baris katalog ke dokumen master All-in-nya (membuat bila belum ada). 1 bila ada yang berubah.
    Tanpa baca-lalu-tulis: (1) upsert `$setOnInsert` membuat dokumen bila belum ada, (2) pembaruan bersyarat hanya mengenai dokumen
    yang nilainya BERBEDA — keduanya atomik, jadi dua penulis serentak tidak bisa menggandakan atau saling menimpa setengah-setengah."""
    c = k.get("cost") or {}
    want = {"name": k.get("label") or k["code"], "is_active": bool(k.get("active", True)), "catalog_code": k["code"],
            **{f: c.get(f) for f in COST_FIELDS}, "kpr_only": bool(c.get("kpr_only"))}
    ts = now_iso()
    flt = {"org_id": org, "code": k["code"]}
    ins = await db.cost_components.update_one(flt, {"$setOnInsert": {"id": new_id(), "created_at": ts, "updated_at": ts, **want}}, upsert=True)
    if ins.upserted_id is not None:
        return 1
    bool_default = {"kpr_only": False, "is_active": True}   # kolom boolean yang belum ada di dokumen lama = nilai bawaannya (bukan selisih)

    def differs(f, v):
        if f in bool_default:
            return {f: (not v)} if v == bool_default[f] else {f: {"$ne": v}}
        return {f: {"$ne": v}}
    upd = await db.cost_components.update_one({**flt, "$or": [differs(f, v) for f, v in want.items()]},
                                              {"$set": {**want, "updated_at": ts}})
    return int(upd.modified_count)


async def after_catalog_write(org: str, row: dict) -> bool:
    """Mode katalog_sumber: perubahan katalog ditulis tembus ke master All-in supaya selisih tetap 0 dan kembali ke bayangan aman."""
    if not row or not row.get("cost") or (await mode_for(org)) != KATALOG:
        return False
    return bool(await _write_through(org, row))


async def guard_rule_edit(org: str, upd: dict, cur: dict = None) -> None:
    """Mode katalog_sumber (tingkat organisasi): definisi komponen dimiliki katalog, jadi MENGUBAHNYA di master All-in ditolak
    (isian yang nilainya sama dengan yang tersimpan — mis. formulir yang mengirim ulang semua kolom — tidak dihitung perubahan)."""
    if upd and (await mode_for(org)) == KATALOG:
        owned = [f for f in upd if f in (*COST_FIELDS, "name", "is_active") and upd[f] != (cur or {}).get(f)]
        if owned:
            raise ValueError("Sumber master komponen biaya = KATALOG: ubah komponen ini di Pusat Konfigurasi › Komponen Biaya "
                             f"(kolom {', '.join(owned)}). Aturan All-in hanya menentukan komponen mana yang berlaku di tiap skema.")


async def mirror_new_rule(org: str, doc: dict) -> None:
    """Mode katalog_sumber: komponen All-in BARU langsung didaftarkan di katalog (tetap SATU master, selisih tetap 0).
    Upsert `$setOnInsert` (atomik; indeks unik org+kode): baris katalog yang sudah ada TIDAK ditimpa."""
    if (await mode_for(org)) != KATALOG:
        return
    cat = await db.price_components.find({"org_id": org}, {"_id": 0, "order": 1}).to_list(None)
    row = _catalog_row_from_rule({**doc, "org_id": org}, max([int(k.get("order") or 0) for k in cat] + [0]) + 10, now_iso())
    await db.price_components.update_one({"org_id": org, "code": doc["code"]},
                                         {"$setOnInsert": {k: v for k, v in row.items() if k not in ("org_id", "code")}}, upsert=True)
    await db.cost_components.update_one({"org_id": org, "code": doc["code"]}, {"$set": {"catalog_code": doc["code"]}})
