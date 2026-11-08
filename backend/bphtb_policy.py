"""BPHTB PER KONTRAK — siapa menanggung BPHTB (docs/audit/12 keputusan #3, W2-B).

Dua kunci pengaturan (`settings_policy.py`, tingkat organisasi · proyek · KONTRAK, sensitif):
  * `bphtb.borne_by`            pembeli (BAWAAN) · developer · dibagi
  * `bphtb.developer_share_pct` porsi developer untuk `dibagi` (usulan sistem 50%)

SATU fungsi pembagi — `split_amount` — dibaca semua titik hitung (jangan menyebar):
  * `allin_engine.resolve_scheme`  membentuk komponen biaya saat penawaran/reservasi/amandemen (`apply_policy`);
  * perubahan per kontrak          (`routers/contract_policy_router` → `contract_policy` → `contract_plan` di sini);
  * `allin_engine.ledger`, `tax_engine.enrich_records` dan layar kontrak membaca hasilnya lewat `bphtb_split` / `derive`.

Bagaimana keputusan menjadi angka (komponen biaya adalah SNAPSHOT dokumen — pola yang sudah ada, tidak diubah):
  * pembeli    satu baris `BPHTB`, `customer_pass_through` → invoice biaya → titipan 2-1470 → disalurkan (perilaku lama persis);
  * developer  satu baris `BPHTB`, `developer_borne`      → tidak ditagih; beban dicatat lewat jalur "Catat beban" yang sudah ada
               (Dr akun beban komponen [bawaan 6-1700] / Cr Utang Usaha 2-1100) — tidak ada akun baru;
  * dibagi     dua baris: `BPHTB` (pembeli, `customer_pass_through`, bagian pembeli) + `BPHTB_DEV` (developer, `developer_borne`).
Semua pembaca lama (tagihan, ledger, dokumen, penawaran) sudah membaca `treatment` per baris, jadi tidak ada yang perlu tahu soal pembagian.

NILAI BAWAAN = PERILAKU SEBELUM PENGATURAN INI ADA. Selama tidak ada pilihan eksplisit (asal nilai `default`), perlakuan BPHTB
mengikuti skema all-in yang dipilih sales (Exclude → pembeli, All-in Standar → developer). Begitu dipilih eksplisit di organisasi/proyek/
kontrak, pilihan itu menang atas skema dan dicatat di baris komponen (`bphtb_policy`: borne_by, share_pct, origin, scheme_treatment).
"""
import policy
import settings_store as cfg
from db import ORG_ID

KEY_BY, KEY_PCT = "bphtb.borne_by", "bphtb.developer_share_pct"
CODE, CODE_DEV = "BPHTB", "BPHTB_DEV"
PEMBELI, DEVELOPER, DIBAGI = "pembeli", "developer", "dibagi"
T_BUYER, T_DEV = "customer_pass_through", "developer_borne"
EXPLICIT = ("contract", "project", "org", "cluster")   # asal nilai yang berarti "sudah dipilih" (bukan bawaan kode)
MARK = "bphtb_policy"
_CUT = " − potongan"


# ----------------------------------------------------------------------------- aritmetika (satu-satunya tempat)
def split_amount(total, borne_by: str, share_pct=0) -> dict:
    """{total, buyer, developer}. dibagi: developer = round(total × porsi/100), sisanya pembeli (sisa pembulatan ke pembeli)."""
    total = max(0, int(total or 0))
    if borne_by == PEMBELI:
        dev = 0
    elif borne_by == DEVELOPER:
        dev = total
    elif borne_by == DIBAGI:
        pct = float(share_pct)
        if not 0 <= pct <= 100:
            raise ValueError("Porsi developer BPHTB harus antara 0 dan 100 persen.")
        dev = int(round(total * pct / 100))
    else:
        raise ValueError(f"Penanggung BPHTB '{borne_by}' tidak dikenal ({', '.join((PEMBELI, DEVELOPER, DIBAGI))}).")
    return {"total": total, "buyer": total - dev, "developer": dev}


def _is_bphtb(c: dict) -> bool:
    return (c or {}).get("code") in (CODE, CODE_DEV)


def _rows(components) -> list:
    return [c for c in components or [] if _is_bphtb(c)]


def _mark_of(rows: list):
    return next((c[MARK] for c in rows if isinstance(c.get(MARK), dict)), None)


def derive(components, costs: dict = None):
    """Keadaan BPHTB yang SEDANG berlaku pada snapshot komponen: {total, buyer, developer, discount, borne_by, share_pct, origin, source}
    atau None bila tidak ada komponen BPHTB (`costs` dipakai hanya untuk kontrak lama: input biaya bebas `costs.bphtb`)."""
    rows = _rows(components)
    if not rows:
        v = (costs or {}).get("bphtb") if components is None else None
        if v is None:
            return None
        dev = bool((costs or {}).get("all_in_by_developer"))
        v = int(v)
        return {"total": v, "buyer": 0 if dev else v, "developer": v if dev else 0, "discount": 0,
                "borne_by": DEVELOPER if dev else PEMBELI, "share_pct": None, "origin": "legacy", "source": "legacy"}
    buyer = sum(int(c.get("amount") or 0) for c in rows if c.get("treatment") != T_DEV)
    dev = sum(int(c.get("amount") or 0) for c in rows if c.get("treatment") == T_DEV)
    disc = sum(int(c.get("discount") or 0) for c in rows)
    mark = _mark_of(rows)
    if mark:
        by, share, origin = mark.get("borne_by"), mark.get("share_pct"), mark.get("origin") or "skema"
    else:
        by = DIBAGI if (buyer and dev) else (DEVELOPER if dev else PEMBELI)
        if not buyer and not dev:   # nilai 0: baca perlakuan baris
            by = DEVELOPER if rows[0].get("treatment") == T_DEV else PEMBELI
        share, origin = None, "skema"
    return {"total": buyer + dev + disc, "buyer": buyer, "developer": dev, "discount": disc, "borne_by": by,
            "share_pct": share, "origin": origin, "source": (rows[0].get("source") or "scheme")}


# ----------------------------------------------------------------------------- keputusan (kontrak → proyek/organisasi → bawaan)
def _valid(key: str, value):
    try:
        return cfg.coerce(cfg.DEFAULTS[key], value)
    except (ValueError, KeyError):
        return None


async def _layer(key: str, org: str, project_id: str, contract: dict, *, skip_contract: bool = False):
    """(nilai, asal): penimpaan kontrak → nilai BEKU kontrak yang asalnya eksplisit → proyek/organisasi/bawaan (hidup).
    Nilai beku yang asalnya bukan pilihan eksplisit (bawaan/skema) TIDAK mengikat — kontrak bernilai-bawaan mengikuti skema."""
    if contract and not skip_contract:
        ov = (contract.get("policy_overrides") or {}).get(key)
        if isinstance(ov, dict) and _valid(key, ov.get("value")) is not None:
            return _valid(key, ov["value"]), "contract"
        sn = (contract.get("policy_snapshot") or {}).get(key)
        if isinstance(sn, dict) and sn.get("origin") in EXPLICIT and _valid(key, sn.get("value")) is not None:
            return _valid(key, sn["value"]), sn["origin"]
    return await policy.resolve_with_origin(key, org_id=org, project_id=project_id)


async def decide(org: str, project_id: str = None, contract: dict = None, *, skip_contract: bool = False) -> dict:
    """Keputusan BPHTB yang berlaku: {borne_by, borne_by_origin, share_pct, share_origin, explicit}. `explicit` = ada pilihan
    (asal ≠ bawaan kode); bila False, perlakuan BPHTB mengikuti skema all-in. `skip_contract` = abaikan lapisan kontrak (untuk
    "kembali mengikuti proyek/organisasi")."""
    by, by_o = await _layer(KEY_BY, org, project_id, contract, skip_contract=skip_contract)
    pct, pct_o = await _layer(KEY_PCT, org, project_id, contract, skip_contract=skip_contract)
    return {"borne_by": by, "borne_by_origin": by_o, "share_pct": float(pct), "share_origin": pct_o, "explicit": by_o in EXPLICIT}


# ----------------------------------------------------------------------------- menerapkan keputusan ke komponen biaya
def _base_formula(row: dict) -> str:
    return str(row.get("formula") or "").split(_CUT)[0]


def apply_to_components(components: list, borne_by: str, share_pct=0, origin: str = "org", *, mark: bool = True,
                        scheme_treatment: str = None) -> list:
    """Daftar komponen BARU dengan baris BPHTB dibentuk menurut keputusan (tanpa mengubah masukan). Bila tidak ada baris BPHTB →
    masukan dikembalikan apa adanya (skema tanpa BPHTB: tak ada yang diatur). Potongan promo yang menempel pada BPHTB diputar ulang
    ke bagian PEMBELI (dibatasi nilainya) — promo mengurangi tagihan pembeli, bukan beban developer. `mark=False` = kembali ke perlakuan
    skema (tanpa penanda)."""
    rows = _rows(components)
    if not rows:
        return components
    first = next((c for c in rows if c.get("code") == CODE), rows[0])
    old = _mark_of(rows)
    # perlakuan MENURUT SKEMA sebelum keputusan pertama dipasang — disimpan di penanda supaya "ikuti skema" bisa dipulihkan
    base_treatment = scheme_treatment or (old or {}).get("scheme_treatment") or (T_DEV if first.get("treatment") == T_DEV else T_BUYER)
    total = sum(int(c.get("amount") or 0) + int(c.get("discount") or 0) for c in rows)
    cuts = [dict(x) for c in rows for x in (c.get("discount_lines") or [])]
    sp = split_amount(total, borne_by, share_pct)
    pct = float(share_pct)
    seed = {k: v for k, v in first.items() if k not in ("amount", "discount", "discount_lines", MARK, "treatment")}
    two = sp["buyer"] > 0 and sp["developer"] > 0
    dev_only = (not two) and (sp["developer"] > 0 or (total == 0 and borne_by == DEVELOPER))
    base_f = _base_formula(first)
    main = {**seed, "code": CODE, "treatment": T_DEV if dev_only else T_BUYER, "amount": sp["buyer"] if two else total,
            "discount": 0, "discount_lines": [], "formula": base_f + (f" · bagian pembeli {100 - pct:g}%" if two else "")}
    out_rows = [main]
    if two:
        out_rows.append({**seed, "code": CODE_DEV, "name": f"{seed.get('name') or CODE} (porsi developer)", "treatment": T_DEV,
                         "amount": sp["developer"], "discount": 0, "discount_lines": [],
                         "formula": base_f + f" · bagian developer {pct:g}%"})
    left = int(main["amount"])
    for x in cuts:   # putar ulang potongan promo pada baris utama
        c = min(int(x.get("amount") or 0), left)
        if c <= 0:
            continue
        left -= c
        main["discount"] += c
        main["discount_lines"].append({**x, "amount": c})
    if main["discount"]:
        main["amount"] = int(main["amount"]) - main["discount"]
        main["formula"] = f"{main['formula']}{_CUT} Rp {main['discount']:,}".replace(",", ".")
    if mark:
        info = {"borne_by": borne_by, "share_pct": pct, "origin": origin, "scheme_treatment": base_treatment}
        for r in out_rows:
            r[MARK] = dict(info)
    out, placed = [], False
    for c in components:
        if _is_bphtb(c):
            if not placed:
                out.extend(out_rows)
                placed = True
            continue
        out.append(c)
    return out


async def apply_policy(org: str, components: list, project_id: str = None, contract: dict = None) -> list:
    """Dipanggil `allin_engine.resolve_scheme` setelah komponen skema dihitung. Tanpa pilihan eksplisit → komponen TIDAK berubah
    (perilaku lama: perlakuan mengikuti skema). Dengan pilihan eksplisit → baris BPHTB dibentuk menurut keputusan."""
    if not _rows(components):
        return components
    dec = await decide(org, project_id, contract)
    if not dec["explicit"]:
        return components
    return apply_to_components(components, dec["borne_by"], dec["share_pct"], dec["borne_by_origin"])


async def bphtb_split(doc: dict, project_id: str = None, *, org_id: str = ORG_ID, total: int = None) -> dict:
    """{total, buyer, developer, discount, borne_by, share_pct, origin} untuk kontrak/deal. Tanpa `total`: angka dibaca dari snapshot
    komponen BPHTB dokumen (yang berlaku; None bila tak ada). Dengan `total` (mis. nominal catatan pajak): `total` DIBAGI menurut
    penanggung yang berlaku pada dokumen (dari snapshot komponennya; bila tak ada, dari keputusan efektif `decide`) lewat `split_amount`."""
    d = derive((doc.get("costs") or {}).get("components"), doc.get("costs"))
    if total is None:
        return d
    if d:
        by, share, origin = d["borne_by"], d["share_pct"], d["origin"]
    else:
        dec = await decide(org_id, project_id or doc.get("project_id"), doc)
        by, share, origin = ((dec["borne_by"], dec["share_pct"], dec["borne_by_origin"]) if dec["explicit"]
                             else (PEMBELI, None, "skema"))
    if share is None:
        share = float((await decide(org_id, project_id or doc.get("project_id"), doc))["share_pct"])
    sp = split_amount(total, by, share)
    return {**sp, "discount": 0, "borne_by": by, "share_pct": float(share) if by == DIBAGI else None, "origin": origin,
            "source": "kebijakan"}


# ----------------------------------------------------------------------------- penangan tingkat KONTRAK (dipakai `contract_policy`)
# Antarmuka penangan: contract_applied (nilai yang SEDANG berlaku, dibaca dari snapshot komponen), contract_lock_reason (kenapa
# sekarang tidak boleh diubah), contract_plan (field kontrak yang harus berubah), contract_after (efek lanjutan setelah ditulis).
KEYS = (KEY_BY, KEY_PCT)


def contract_applied(contract: dict) -> dict:
    """{kunci: (nilai, asal)} yang SEDANG berlaku pada kontrak (dari snapshot komponen biaya). Kosong bila tak ada komponen BPHTB."""
    d = derive((contract.get("costs") or {}).get("components"), contract.get("costs"))
    if not d:
        return {}
    out = {KEY_BY: (d["borne_by"], d["origin"])}
    if d["borne_by"] == DIBAGI and d["share_pct"] is not None:
        out[KEY_PCT] = (d["share_pct"], d["origin"])
    return out


def _scope(contract: dict) -> dict:
    """Dokumen biaya lahir saat BOOKING (sebelum kontrak ada) → dicari lewat deal_id juga (sama dengan `allin_engine._scope`)."""
    ors = [{"deal_id": contract["deal_id"]}] if contract.get("deal_id") else []
    ors.append({"contract_id": contract["id"]})
    return {"$or": ors}


async def contract_lock_reason(org: str, contract: dict):
    """Alasan tanggungan BPHTB kontrak ini TIDAK boleh diubah sekarang (atau None). Aturan: boleh selama uang BPHTB belum bergerak —
    sama ketatnya dengan amandemen skema biaya. Invoice biaya yang belum dibayar akan dibatalkan & diterbitkan ulang; setelah ada
    kuitansi biaya (titipan masuk), penyaluran, beban developer, atau catatan pajak BPHTB dilaporkan/disetor, perubahan ditolak
    (tidak ada fitur void kuitansi biaya — koreksi dilakukan Keuangan secara manual)."""
    from db import db
    if not _rows((contract.get("costs") or {}).get("components")):
        return ("Kontrak ini tidak memuat komponen BPHTB pada skema biayanya (input biaya bebas lama atau skema tanpa BPHTB) — "
                "pilih skema all-in yang memuat BPHTB lewat amandemen skema biaya dulu.")
    if await db.allin_amendments.find_one({"org_id": org, "contract_id": contract["id"], "status": "pending"}, {"_id": 0, "id": 1}):
        return "Masih ada amandemen skema biaya yang menunggu keputusan — selesaikan dulu."
    q = {"org_id": org, **_scope(contract)}
    if await db.cost_receipts.find_one({**q, "status": {"$ne": "void"}}, {"_id": 0, "id": 1}):
        return ("Sudah ada kuitansi biaya (titipan biaya pembeli) yang diterima — tanggungan BPHTB tidak bisa diubah lagi. "
                "Koreksi dilakukan Keuangan secara manual.")
    both = {"$in": [CODE, CODE_DEV]}
    if await db.cost_disbursements.find_one({**q, "component_code": both}, {"_id": 0, "id": 1}):
        return "BPHTB sudah disalurkan ke pihak ketiga — tanggungan tidak bisa diubah lagi."
    if await db.cost_expenses.find_one({**q, "component_code": both}, {"_id": 0, "id": 1}):
        return "Beban BPHTB developer sudah dicatat — tanggungan tidak bisa diubah lagi."
    if await db.tax_records.find_one({"org_id": org, "deal_id": contract.get("deal_id"), "type": "bphtb",
                                      "status": {"$in": ["reported", "paid"]}}, {"_id": 0, "id": 1}):
        return "Catatan pajak BPHTB deal ini sudah dilaporkan/disetor — tanggungan tidak bisa diubah lagi."
    return None


def _signature(components) -> list:
    """Isi EKONOMIS baris BPHTB (kode, perlakuan, nilai, potongan) — tanpa penanda/teks rumus."""
    return sorted((c.get("code"), c.get("treatment"), int(c.get("amount") or 0), int(c.get("discount") or 0)) for c in _rows(components))


def contract_summary(contract: dict):
    """Ringkasan BPHTB kontrak untuk layar: {total, buyer, developer, discount, borne_by, share_pct, origin} atau None."""
    return derive((contract.get("costs") or {}).get("components"), contract.get("costs"))


async def contract_plan(org: str, contract: dict, eff: dict):
    """{"fields": {path: nilai}, "material": bool} bila snapshot komponen harus berubah agar mengikuti keputusan `eff` = {kunci: (nilai, asal)};
    None bila tidak ada yang perlu ditulis. `material` = nilai/perlakuan baris BPHTB benar-benar berubah (hanya penanda yang berganti →
    tidak ada invoice yang dibatalkan/diterbitkan ulang). Asal ∉ EXPLICIT (bawaan) = kembali ke perlakuan skema."""
    costs = contract.get("costs") or {}
    comps = costs.get("components") or []
    rows = _rows(comps)
    by, by_o = eff[KEY_BY]
    pct = float(eff[KEY_PCT][0])
    mark = _mark_of(rows)
    if by_o in EXPLICIT:
        if mark and mark.get("borne_by") == by and mark.get("origin") == by_o and (by != DIBAGI or float(mark.get("share_pct")) == pct):
            return None   # sudah persis begitu
        new = apply_to_components(comps, by, pct, by_o)
    else:
        if not mark:
            return None   # belum pernah dipasang keputusan eksplisit → sudah mengikuti skema
        st = mark.get("scheme_treatment") or T_BUYER
        new = apply_to_components(comps, DEVELOPER if st == T_DEV else PEMBELI, pct, "skema", mark=False)
    fields = {"costs.components": new}
    if "buyer_total" in costs or "developer_total" in costs or "discount_total" in costs:   # agregat yang dihitung `attach_costs`
        fields["costs.buyer_total"] = sum(int(c.get("amount") or 0) for c in new if c.get("treatment") != T_DEV)
        fields["costs.developer_total"] = sum(int(c.get("amount") or 0) for c in new if c.get("treatment") == T_DEV)
        fields["costs.discount_total"] = sum(int(c.get("discount") or 0) for c in new)
    return {"fields": fields, "material": _signature(new) != _signature(comps)}


async def contract_after(org: str, contract_id: str, actor: str, why: str) -> dict:
    """Setelah komponen berubah: invoice biaya yang BELUM dibayar dibatalkan (nominalnya sudah tak berlaku) dan diterbitkan ulang
    dari komponen baru; bila tak ada lagi yang ditagih ke pembeli (developer) tidak ada invoice baru. Deal ikut disinkronkan
    (`deals.costs`) supaya `deal.costs` tidak menjadi sumber kedua yang basi."""
    import allin_engine as ae
    from core_utils import now_iso
    from db import db
    c = await db.contracts.find_one({"id": contract_id, "org_id": org}, {"_id": 0})
    ts = now_iso()
    res = await db.cost_invoices.update_many(
        {"org_id": org, **_scope(c), "status": "unpaid", "paid": {"$in": [0, None]}},
        {"$set": {"status": "void", "void_reason": why, "updated_at": ts}})
    out = {"voided": res.modified_count, "reissued": None, "reissue_note": None}
    sync = {k: v for k, v in (c.get("costs") or {}).items() if k in ("components", "buyer_total", "developer_total", "discount_total")}
    if c.get("deal_id") and sync:
        await db.deals.update_one({"id": c["deal_id"], "org_id": org}, {"$set": {f"costs.{k}": v for k, v in sync.items()}})
    try:
        out["reissued"] = (await ae.issue_cost_invoice(org, c, actor))["number"]
    except ValueError as e:   # tidak ada komponen yang ditagih ke pembeli, atau deal sudah tutup — dicatat, bukan galat
        out["reissue_note"] = str(e)
    return out
