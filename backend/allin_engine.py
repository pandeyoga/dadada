"""Fase 76-77 — Master KOMPONEN BIAYA + SKEMA ALL-IN + penagihan/pembukuan biaya.

Dua makna nyata di praktik properti Indonesia:
  * `developer_borne`        → "harga all-in": biaya sudah termasuk harga, developer yang membayar
                               notaris/BPN → BEBAN penjualan (lewat AP), tidak ditagih ke pembeli.
  * `customer_pass_through`  → "harga exclude": pembeli bayar terpisah; developer hanya MENAMPUNG
                               (titipan = kewajiban, bukan pendapatan) lalu MENYALURKAN ke notaris/BPN.
Perlakuan dikunci PER KOMPONEN di master; sales hanya memilih skema. Nominal biaya TIDAK PERNAH
masuk piutang unit (piutang tetap = harga − DP/booking).
"""
import logging

import finance_engine as fe
import gl_engine as gl
import bphtb_policy   # W2-B: penanggung BPHTB (pembeli/developer/dibagi) — satu fungsi pembagi
import sequences as seq
import tax_master
from core_utils import new_id, now_iso
from db import db
from engine import add_activity
from idempotency import cas, mutex, once
from money_lock import locked

logger = logging.getLogger("sipro.allin")

CALC_METHODS = ("nominal_tetap", "persen_harga", "rumus_bphtb")
TREATMENTS = ("developer_borne", "customer_pass_through")
GL_BANK = "1-1200"
GL_TITIPAN_BIAYA = "2-1470"
GL_BEBAN_PENJUALAN = "6-1700"
GL_AP = "2-1100"
MANUAL_ROLES = ("finance_manager", "super_admin", "owner")  # = pemegang izin finance:manage
# Komponen KHUSUS: nominalnya = booking fee deal. Bila skema all-in memuatnya, booking fee yang
# dibayar pembeli melunasi komponen ini (titipan biaya) — bukan dialihkan ke termin unit.
BOOKING_CODE = "BOOKING"


async def may_manual(user: dict) -> bool:
    """Input biaya manual / koreksi & pembatalan pencairan KPR: SATU izin `finance:manage`
    (ROLE_GRANTS finance_manager; owner/super_admin implisit) dipakai backend & layar."""
    from rbac import can
    return await can(user.get("role"), "finance", "manage")

DEFAULT_COMPONENTS = [
    {"code": "BPHTB", "name": "BPHTB", "calc_method": "rumus_bphtb", "pct": 5.0, "amount": 0,
     "default_treatment": "customer_pass_through"},
    {"code": "NOTARY_FEE", "name": "Biaya notaris / akad", "calc_method": "nominal_tetap",
     "amount": 7_500_000, "default_treatment": "customer_pass_through"},
    {"code": "BANK_FEE", "name": "Biaya bank (provisi, admin, materai)", "calc_method": "persen_harga",
     "pct": 1.0, "amount": 0, "default_treatment": "customer_pass_through", "kpr_only": True},
    {"code": "INSURANCE", "name": "Asuransi jiwa & kebakaran", "calc_method": "nominal_tetap",
     "amount": 3_000_000, "default_treatment": "customer_pass_through", "kpr_only": True},
    {"code": "LEGACY", "name": "Biaya (input bebas — kontrak lama)", "calc_method": "nominal_tetap",
     "amount": 0, "default_treatment": "customer_pass_through", "is_legacy": True},
    {"code": BOOKING_CODE, "name": "Booking fee (nominal = booking fee deal)", "calc_method": "nominal_tetap",
     "amount": 0, "default_treatment": "customer_pass_through",
     "note": "Khusus: nominal mengikuti booking fee deal; booking fee yang dibayar melunasi komponen ini."},
]
DEFAULT_SCHEMES = [
    {"code": "ALLIN_STD", "name": "All-in Standar", "note": "BPHTB + notaris ditanggung developer.",
     "items": [{"component_code": "BPHTB", "treatment": "developer_borne"},
               {"component_code": "NOTARY_FEE", "treatment": "developer_borne"},
               {"component_code": "BANK_FEE", "treatment": "customer_pass_through"},
               {"component_code": "INSURANCE", "treatment": "customer_pass_through"}]},
    {"code": "EXCLUDE", "name": "Exclude (semua biaya pembeli)", "note": "Developer hanya menampung & menyalurkan.",
     "items": [{"component_code": "BPHTB", "treatment": "customer_pass_through"},
               {"component_code": "NOTARY_FEE", "treatment": "customer_pass_through"},
               {"component_code": "BANK_FEE", "treatment": "customer_pass_through"},
               {"component_code": "INSURANCE", "treatment": "customer_pass_through"}]},
]


# ============================================================ master
async def ensure_defaults(org: str):
    """Seed komponen & skema bawaan (idempoten per kode) + akun GL titipan/beban."""
    ts = now_iso()
    for c in DEFAULT_COMPONENTS:
        await db.cost_components.update_one(
            {"org_id": org, "code": c["code"]},
            {"$setOnInsert": {"id": new_id(), "org_id": org, "is_active": True, "pct": 0.0,
                              "gl_expense": GL_BEBAN_PENJUALAN, "gl_liability": GL_TITIPAN_BIAYA,
                              "gl_ap": GL_AP, "created_at": ts, "updated_at": ts, **c}},
            upsert=True)
    for s in DEFAULT_SCHEMES:
        await db.allin_schemes.update_one(
            {"org_id": org, "code": s["code"]},
            {"$setOnInsert": {"id": new_id(), "org_id": org, "is_active": True,
                              "project_ids": [], "unit_types": [],
                              "created_at": ts, "updated_at": ts, **s}},
            upsert=True)
    await gl.ensure_coa(org)


async def list_components(org: str, include_inactive=False) -> list:
    q = {"org_id": org}
    if not include_inactive:
        q["is_active"] = True
    return await db.cost_components.find(q, {"_id": 0}).sort("code", 1).to_list(200)


async def list_schemes(org: str, project_id: str = None, unit_type: str = None,
                       include_inactive=False) -> list:
    q = {"org_id": org}
    if not include_inactive:
        q["is_active"] = True
    rows = await db.allin_schemes.find(q, {"_id": 0}).sort("name", 1).to_list(200)
    if project_id:
        rows = [r for r in rows if not r.get("project_ids") or project_id in r["project_ids"]]
    if unit_type:
        rows = [r for r in rows if not r.get("unit_types") or unit_type in r["unit_types"]]
    return rows


# ============================================================ perhitungan
async def npoptkp_for(org: str, project_id: str) -> int:
    """NPOPTKP efektif dari MASTER PAJAK (org + penimpaan proyek). Kolom `npoptkp` proyek yang dulu dijanjikan layar tak pernah
    tersimpan (FN-12a) — tidak dibaca lagi supaya master tetap SATU sumber."""
    return int((await tax_master.resolve(project_id, org_id=org))["npoptkp"])


def compute_amount(comp: dict, price: int, npoptkp: int, override: int = None,
                   booking_fee: int = None, bphtb_rate: float = None, njop_total: int = 0,
                   bank_fee_pct: float = 0, plafon: int = None) -> tuple:
    """(nominal, rumus-teks). Override nominal terkunci dari skema menang atas rumus.
    W2-A: tarif BPHTB/NJOP dan % plafon BANK_FEE datang dari master pajak (None/0 = rumus lama persis)."""
    if comp.get("code") == BOOKING_CODE:
        return int(booking_fee or 0), "= booking fee deal"
    if override is not None:
        return int(override), "nominal terkunci skema"
    m = comp.get("calc_method")
    if comp.get("code") == "BANK_FEE" and m == "persen_harga" and bank_fee_pct and plafon:
        return int(round(int(plafon) * float(bank_fee_pct) / 100)), f"{float(bank_fee_pct):g}% × plafon KPR Rp {int(plafon):,}".replace(",", ".")
    if m == "persen_harga":
        pct = float(comp.get("pct") or 0)
        return int(round(price * pct / 100)), f"{pct:g}% × harga"
    if m == "rumus_bphtb":
        pct = float(bphtb_rate if bphtb_rate is not None else (comp.get("pct") or 5))   # tarif = master pajak, bukan persen komponen
        npop = max(int(price), int(njop_total or 0))
        base = max(0, npop - int(npoptkp))
        dasar = "harga" if npop == int(price) else f"NJOP Rp {npop:,}".replace(",", ".")
        return int(round(base * pct / 100)), f"{pct:g}% × ({dasar} − NPOPTKP Rp {npoptkp:,})".replace(",", ".")
    return int(comp.get("amount") or 0), "nominal tetap"


async def resolve_scheme(org: str, scheme_id: str, price: int, project_id: str = None,
                         scheme: str = None, booking_fee: int = None, land_area=None, plafon: int = None,
                         contract: dict = None) -> dict:
    """Snapshot komponen dari skema all-in untuk harga ini → disimpan di `deal.costs`.

    FN-02: komponen NONAKTIF tidak ikut ditagihkan pada snapshot baru (dulu `include_inactive=True`
    membuatnya tetap masuk reservasi baru). Kontrak/deal yang snapshot-nya sudah terbit tidak berubah."""
    if int(price) < 0:
        raise ValueError("Harga tidak boleh negatif.")
    sch = await db.allin_schemes.find_one({"org_id": org, "id": scheme_id}, {"_id": 0})
    if not sch:
        raise ValueError("Skema all-in tidak ditemukan.")
    if not sch.get("is_active", True):
        raise ValueError("Skema all-in ini sudah nonaktif — pilih skema lain.")
    comps = {c["code"]: c for c in await list_components(org, include_inactive=False)}
    tm = await tax_master.resolve(project_id, org_id=org)   # W2-A: NPOPTKP, tarif BPHTB, NJOP, % plafon BANK_FEE — satu master
    npoptkp = int(tm["npoptkp"])
    njop_total = tax_master.bphtb_npop(0, tm["njop_per_m2"], land_area)
    components = []
    for it in sch.get("items") or []:
        comp = comps.get(it.get("component_code"))
        if not comp:
            continue
        if comp.get("kpr_only") and scheme and scheme != "kpr":
            continue
        amount, formula = compute_amount(comp, int(price), npoptkp, it.get("override_amount"),
                                         booking_fee=booking_fee, bphtb_rate=tm["bphtb_rate"], njop_total=njop_total,
                                         bank_fee_pct=tm["bank_fee_pct_of_plafon"], plafon=plafon)
        if amount < 0:   # master lama yang rusak (sebelum validasi API) tidak boleh melahirkan tagihan negatif
            raise ValueError(f"Komponen {comp['code']} bernilai negatif (Rp {amount:,}) — perbaiki master "
                             "komponen/skema di Pusat Konfigurasi dulu.".replace(",", "."))
        components.append({
            "code": comp["code"], "name": comp["name"], "amount": amount,
            "treatment": it.get("treatment") or comp.get("default_treatment"),
            "calc_method": comp.get("calc_method"), "formula": formula,
            "kpr_only": bool(comp.get("kpr_only")),
            "gl_expense": comp.get("gl_expense") or GL_BEBAN_PENJUALAN,
            "gl_liability": comp.get("gl_liability") or GL_TITIPAN_BIAYA,
            "gl_ap": comp.get("gl_ap") or GL_AP, "source": "scheme"})
    # W2-B: penanggung BPHTB (pembeli/developer/dibagi) — pilihan eksplisit organisasi/proyek/kontrak menang atas perlakuan skema;
    # tanpa pilihan eksplisit komponen TIDAK berubah (perilaku lama: perlakuan mengikuti skema).
    components = await bphtb_policy.apply_policy(org, components, project_id, contract)
    return {"scheme_id": sch["id"], "scheme_code": sch.get("code"), "scheme_name": sch["name"],
            "npoptkp": npoptkp, "components": components}


def manual_components(items: list, reason: str, actor: str) -> dict:
    """Input manual (hanya finance_manager/superadmin) — wajib alasan, setiap baris ter-audit."""
    if len((reason or "").strip()) < 10:
        raise ValueError("Input biaya manual wajib alasan (minimal 10 huruf).")
    out = []
    for it in items or []:
        code = (it.get("code") or "").strip().upper()
        if not code or it.get("amount") is None:
            raise ValueError("Komponen manual wajib kode & nominal.")
        if int(it["amount"]) < 0:
            raise ValueError(f"Nominal komponen manual {code} tidak boleh negatif.")
        tr = it.get("treatment") or "customer_pass_through"
        if tr not in TREATMENTS:
            raise ValueError(f"Perlakuan '{tr}' tidak dikenal.")
        out.append({"code": code, "name": it.get("name") or code, "amount": int(it["amount"]),
                    "treatment": tr, "calc_method": "nominal_tetap", "formula": "manual",
                    "gl_expense": GL_BEBAN_PENJUALAN, "gl_liability": GL_TITIPAN_BIAYA,
                    "gl_ap": GL_AP, "source": "manual"})
    return {"scheme_id": None, "scheme_code": "MANUAL", "scheme_name": "Manual (finance)",
            "manual_reason": reason.strip(), "manual_by": actor, "components": out}


def legacy_components(costs: dict, scheme: str = None) -> list:
    """Pemetaan `costs` bebas (kontrak lama) → komponen LEGACY agar breakdown tidak berubah."""
    labels = {"bphtb": "BPHTB", "notary_fee": "Biaya notaris / akad",
              "bank_fee": "Biaya bank (provisi, admin, blokir, materai)",
              "insurance": "Asuransi jiwa & kebakaran"}
    dev = bool(costs.get("all_in_by_developer"))
    out = []
    for k, label in labels.items():
        if costs.get(k) is None:
            continue
        out.append({"code": k.upper(), "name": label, "amount": int(costs[k]),
                    "treatment": "developer_borne" if dev else "customer_pass_through",
                    "calc_method": "nominal_tetap", "formula": "legacy", "component_code": "LEGACY",
                    "kpr_only": k in ("bank_fee", "insurance"),
                    "gl_expense": GL_BEBAN_PENJUALAN, "gl_liability": GL_TITIPAN_BIAYA,
                    "gl_ap": GL_AP, "source": "legacy"})
    return out


async def migrate_legacy_contracts(org: str) -> int:
    """Kontrak dengan `costs` bebas tanpa `components` → snapshot LEGACY (sekali, idempoten)."""
    n = 0
    cur = db.contracts.find({"org_id": org, "costs": {"$exists": True},
                             "costs.components": {"$exists": False}}, {"_id": 0, "id": 1, "costs": 1, "scheme": 1})
    async for c in cur:
        costs = c.get("costs") or {}
        comps = legacy_components(costs, c.get("scheme"))
        if not comps:
            continue
        await db.contracts.update_one({"id": c["id"]}, {"$set": {
            "costs.components": comps, "costs.scheme_code": "LEGACY",
            "costs.scheme_name": "Legacy (input bebas)", "costs.migrated_at": now_iso()}})
        n += 1
    return n


# ============================================================ penagihan & pembukuan biaya
def _applicable(contract: dict) -> list:
    return [c for c in (contract.get("costs") or {}).get("components") or []
            if not (c.get("kpr_only") and contract.get("scheme") != "kpr")]


def _pass_through(contract: dict) -> list:
    return [c for c in _applicable(contract)
            if c.get("treatment") == "customer_pass_through" and int(c.get("amount") or 0) > 0]


def booking_component(contract: dict) -> dict:
    """Komponen BOOKING (pass-through, nominal > 0) pada snapshot all-in — None bila tidak ada."""
    return next((c for c in _pass_through(contract) if c.get("code") == BOOKING_CODE), None)


async def apply_booking_deposit(org: str, deal: dict, actor: str) -> dict:
    """Booking fee yang sudah masuk titipan (2-1450) dialihkan ke komponen BOOKING pada invoice
    biaya (titipan biaya 2-1470) — dipanggil saat jadwal tagihan lahir. Tanpa komponen BOOKING
    → tidak melakukan apa-apa (booking fee tetap dialihkan ke termin unit seperti biasa)."""
    contract = await deal_as_contract(org, deal)
    comp = booking_component(contract)
    if not comp:
        return None
    dep = await db.customer_deposits.find_one({"org_id": org, "deal_id": deal["id"]},
                                              {"_id": 0, "balance": 1})
    balance = int((dep or {}).get("balance") or 0)
    if balance <= 0:
        return None
    q = {"org_id": org, **_scope(contract)}
    inv = await db.cost_invoices.find_one({**q, "status": {"$ne": "void"}}, {"_id": 0})
    if not inv:
        inv = await issue_cost_invoice(org, contract, actor or "system")
    already = 0
    async for r in db.cost_receipts.find({**q, "funding": "booking_deposit", "status": {"$ne": "void"}},
                                         {"_id": 0, "amount": 1}):
        already += int(r["amount"])
    amount = min(balance, int(comp["amount"]) - already, int(inv["outstanding"]))
    if amount <= 0:
        return None
    ts = now_iso()
    rc_id, entry_id = new_id(), new_id()
    ctx = {"unit_id": deal.get("unit_id"), "unit_code": deal.get("unit_code"),
           "customer_name": deal.get("lead_name")}
    note = "Booking fee dialihkan ke komponen BOOKING (skema all-in)"
    # Audit IN-01/IN-02: titipan dicadangkan LEBIH DULU (saldo dicek atomik — tidak bisa negatif),
    # lalu invoice biaya diklaim dengan CAS; bila langkah berikutnya gagal, cadangan dikembalikan.
    await fe._deposit_move(org, deal["id"], ctx, "apply_cost", amount, note, actor,
                           receipt_id=rc_id, entry_id=entry_id)
    try:
        paid = int(inv["paid"]) + amount
        await cas("cost_invoices", {"id": inv["id"]}, {"paid": inv.get("paid"), "status": inv.get("status")},
                  {"$set": {"paid": paid, "outstanding": int(inv["total"]) - paid,
                            "status": "paid" if paid >= int(inv["total"]) else "partial", "updated_at": ts}},
                  what="Invoice biaya ini")
        rc = {"id": rc_id, "org_id": org, "contract_id": inv.get("contract_id"), "deal_id": inv.get("deal_id"),
              "invoice_id": inv["id"], "invoice_no": inv["number"], "unit_code": inv.get("unit_code"),
              "customer_name": inv.get("customer_name"), "kind": "cost", "component_code": BOOKING_CODE,
              "receipt_no": await seq.next_number("cost_receipt", org, prefix="KWB",
                                                  context={"unit_id": inv.get("unit_id"),
                                                           "customer_id": inv.get("customer_id")}),
              "amount": amount, "method": "deposit", "funding": "booking_deposit",
              "note": note, "status": "posted",
              "proof_file_ids": [], "actor": actor, "created_at": ts}
        await db.cost_receipts.insert_one(dict(rc))
        rc.pop("_id", None)
        await gl.post_journal(org, f"Booking fee dialihkan ke titipan biaya BOOKING — {rc['receipt_no']}", [
            {"account_code": "2-1450", "debit": amount, "credit": 0},
            {"account_code": comp.get("gl_liability") or GL_TITIPAN_BIAYA, "debit": 0, "credit": amount}],
            source_type="cost_receipt", source_id=rc["id"], source_event=f"cost_receipt:{rc['id']}",
            posted_by=actor, source_deal_id=inv.get("deal_id"))
    except BaseException:
        await db.cost_receipts.delete_one({"id": rc_id})
        await db.cost_invoices.update_one({"id": inv["id"], "paid": paid}, {"$set": {
            "paid": int(inv["paid"]), "outstanding": int(inv["outstanding"]),
            "status": inv.get("status"), "updated_at": ts}})
        await fe._deposit_undo(org, deal["id"], "apply_cost", amount, entry_id)
        raise
    await add_activity(entity_type="lead", entity_id=deal.get("lead_id"), type="finance", actor=actor,
                       org_id=org,
                       body=(f"Booking fee Rp {amount:,} dialihkan ke komponen BOOKING skema all-in "
                             f"(kuitansi biaya {rc['receipt_no']}) — tidak mengurangi termin unit.")
                       .replace(",", "."))
    return rc


def _scope(contract: dict) -> dict:
    """Invoice/kuitansi biaya lahir saat BOOKING (sebelum kontrak ada) → dicari lewat deal_id juga."""
    ors = [{"deal_id": contract.get("deal_id")}] if contract.get("deal_id") else []
    if contract.get("id"):
        ors.append({"contract_id": contract["id"]})
    return {"$or": ors} if ors else {"contract_id": None, "deal_id": None}


async def deal_as_contract(org: str, deal: dict) -> dict:
    """Bentuk 'kontrak semu' dari deal untuk menerbitkan invoice biaya SAAT BOOKING —
    piutang biaya per komponen tercatat di Finance bersamaan dengan piutang unit."""
    sch = await db.payment_schemes.find_one({"id": deal.get("scheme_id")}, {"_id": 0, "kind": 1, "type": 1}) \
        if deal.get("scheme_id") else None
    return {"id": deal.get("contract_id"), "deal_id": deal["id"], "costs": deal.get("costs") or {},
            "scheme": ((sch or {}).get("kind") or (sch or {}).get("type") or (deal.get("pricing") or {}).get("scheme", {}).get("type")),
            "customer_id": deal.get("customer_id"), "unit_id": deal.get("unit_id"),
            "unit_code": deal.get("unit_code"), "customer_name": deal.get("lead_name"),
            "number": deal.get("contract_id") or f"deal {deal.get('unit_code')}"}


async def link_cost_docs_to_contract(org: str, contract: dict) -> int:
    """Kontrak lahir → invoice/kuitansi biaya yang terbit saat booking diikat ke kontraknya."""
    n = 0
    for coll in ("cost_invoices", "cost_receipts", "cost_disbursements", "cost_expenses"):
        res = await db[coll].update_many(
            {"org_id": org, "deal_id": contract["deal_id"], "contract_id": None},
            {"$set": {"contract_id": contract["id"], "customer_id": contract.get("customer_id"),
                      "customer_name": contract.get("customer_name")}})
        n += res.modified_count
    return n


async def ledger(org: str, contract: dict) -> dict:
    """Invoice biaya, kuitansi biaya, penyaluran, sisa titipan, beban developer — per kontrak."""
    q = _scope(contract)
    invoices = await db.cost_invoices.find({"org_id": org, **q}, {"_id": 0}).to_list(50)
    receipts = await db.cost_receipts.find({"org_id": org, **q, "status": {"$ne": "void"}},
                                           {"_id": 0}).sort("created_at", 1).to_list(200)
    disb = await db.cost_disbursements.find({"org_id": org, **q}, {"_id": 0}).sort("created_at", 1).to_list(200)
    exp = await db.cost_expenses.find({"org_id": org, **q}, {"_id": 0}).sort("created_at", 1).to_list(200)
    received = sum(int(r["amount"]) for r in receipts)
    paid_out = sum(int(d["amount"]) for d in disb)
    invoiced = sum(int(i["total"]) for i in invoices if i.get("status") != "void")
    comps = _applicable(contract)
    dev_total = sum(int(c["amount"] or 0) for c in comps if c.get("treatment") == "developer_borne")
    return {"components": comps, "pass_through_total": sum(int(c["amount"]) for c in _pass_through(contract)),
            "developer_borne_total": dev_total,
            "bphtb": bphtb_policy.derive((contract.get("costs") or {}).get("components"), contract.get("costs")),   # W2-B: total/pembeli/developer
            "developer_expensed": sum(int(e["amount"]) for e in exp),
            "invoices": invoices, "receipts": receipts, "disbursements": disb, "expenses": exp,
            "invoiced": invoiced, "received": received, "paid_out": paid_out,
            "titipan_balance": received - paid_out,
            "uninvoiced": max(0, sum(int(c["amount"]) for c in _pass_through(contract)) - invoiced)}


async def issue_cost_invoice(org: str, contract: dict, actor: str) -> dict:
    """Terbitkan INVOICE BIAYA (seri sendiri, bukan AR unit) untuk komponen pass-through.

    Dikunci per kontrak: dua penerbitan bersamaan dulu sama-sama lolos cek "sudah terbit" dan
    melahirkan dua invoice biaya untuk komponen yang sama (piutang biaya berlipat)."""
    async with locked("allin.issue", contract.get("id") or contract.get("deal_id"),
                      what="Penerbitan invoice biaya kontrak ini"):
        return await _issue_cost_invoice_locked(org, contract, actor)


async def _issue_cost_invoice_locked(org: str, contract: dict, actor: str) -> dict:
    import cancellation_costs as cc
    closed = await cc.closed_reason(org, contract.get("deal_id"), contract.get("id"))
    if closed:   # W1-C #12: deal batal/kedaluwarsa tidak menagih biaya baru (invoice lama sudah ditangani kebijakan pembatalan)
        raise ValueError(f"Deal ini sudah {closed} — invoice biaya baru tidak bisa diterbitkan untuk penjualan yang batal.")
    comps = _pass_through(contract)
    if not comps:
        raise ValueError("Tidak ada komponen biaya yang ditagih ke pembeli (semua ditanggung developer "
                         "atau skema all-in belum dipilih).")
    exist = await db.cost_invoices.find_one({"org_id": org, **_scope(contract),
                                             "status": {"$ne": "void"}}, {"_id": 0})
    if exist:
        raise ValueError(f"Invoice biaya {exist['number']} sudah terbit untuk kontrak ini.")
    ts = now_iso()
    total = sum(int(c["amount"]) for c in comps)
    doc = {"id": new_id(), "org_id": org, "contract_id": contract.get("id"), "deal_id": contract.get("deal_id"),
           "customer_id": contract.get("customer_id"), "unit_id": contract.get("unit_id"),
           "unit_code": contract.get("unit_code"), "customer_name": contract.get("customer_name"),
           "number": await seq.next_number("cost_invoice", org, prefix="INB",
                                           context={"unit_id": contract.get("unit_id"),
                                                    "customer_id": contract.get("customer_id")}),
           "items": [{"code": c["code"], "name": c["name"], "amount": int(c["amount"]),
                      "discount": int(c.get("discount") or 0),
                      "gross": int(c["amount"]) + int(c.get("discount") or 0),
                      "discount_lines": c.get("discount_lines") or []} for c in comps],
           "total": total, "paid": 0, "outstanding": total, "status": "unpaid",
           "created_by": actor, "created_at": ts, "updated_at": ts}
    await db.cost_invoices.insert_one(dict(doc))
    doc.pop("_id", None)
    deal = await db.deals.find_one({"id": contract.get("deal_id")}, {"_id": 0, "lead_id": 1}) or {}
    await add_activity(entity_type="customer" if contract.get("customer_id") else "lead",
                       entity_id=contract.get("customer_id") or deal.get("lead_id"), type="finance",
                       actor=actor, org_id=org,
                       body=(f"Invoice biaya {doc['number']} terbit (Rp {total:,}) — piutang biaya per komponen, "
                             "terpisah dari piutang unit.").replace(",", "."))
    return doc


async def pay_cost_invoice(org: str, invoice_id: str, amount: int, method: str, note: str, actor: str,
                           proof_file_ids: list = None, cash_account_id: str = None,
                           cancelled_override: dict = None) -> dict:
    """Kuitansi biaya → jurnal Kas / Titipan biaya customer (kewajiban, BUKAN pendapatan).

    FN-03 (sisa): pada deal yang sudah BATAL/kedaluwarsa pembayaran ditolak (`cancellation_costs.assert_movable`) kecuali
    `cancelled_override` (terobosan berizin `finance:approve` + alasan, disahkan router). Dicek di bawah mutex deal yang
    sama dengan pembatalan, jadi tak ada celah antara cek dan jurnal. Tidak ada jurnal tambahan akibat gerbang ini."""
    import cancellation_costs as cc
    from deal_money import deal_money
    inv0 = await db.cost_invoices.find_one({"org_id": org, "id": invoice_id}, {"_id": 0, "deal_id": 1, "contract_id": 1})
    async with deal_money(org, (inv0 or {}).get("deal_id")):
        ov = (await cc.assert_movable(org, deal_id=inv0.get("deal_id"), contract_id=inv0.get("contract_id"),
                                      what="Pembayaran invoice biaya", override=cancelled_override)) if inv0 else None
        return await _pay_cost_invoice(org, invoice_id, amount, method, note, actor, proof_file_ids,
                                       cash_account_id, ov)


async def _pay_cost_invoice(org: str, invoice_id: str, amount: int, method: str, note: str, actor: str,
                            proof_file_ids: list, cash_account_id: str, cancel_ov: dict) -> dict:
    inv = await db.cost_invoices.find_one({"org_id": org, "id": invoice_id}, {"_id": 0})
    if not inv or inv.get("status") == "void":
        raise ValueError("Invoice biaya tidak ditemukan.")
    amount = int(amount or 0)
    if amount <= 0:
        raise ValueError("Nominal pembayaran biaya wajib > 0.")
    if amount > int(inv["outstanding"]):
        raise ValueError(f"Nominal Rp {amount:,} melebihi sisa invoice biaya Rp {inv['outstanding']:,}.".replace(",", "."))
    # GL-17: rekening/kas pilihan kasir; tanpa pilihan, tunai -> Kas (dulu `GL_BANK` tetap walau metode tunai).
    import cash_bank as _cb
    cash_code = await _cb.resolve_code(org, cash_account_id, "1-1100" if str(method).lower() in ("cash", "tunai") else GL_BANK)
    cash_acc = await _cb.account_by_code(org, cash_code) or {}
    ts = now_iso()
    paid = int(inv["paid"]) + amount
    rid = new_id()
    # Audit IN-01: KLAIM invoice dengan CAS terhadap `paid` yang tadi dibaca SEBELUM kuitansi &
    # jurnal lahir. Dua pembayaran bersamaan dulu sama-sama menulis `paid = 0 + amount`: kuitansi
    # 2× (lebih dari tagihan), invoice hanya mencatat 1×.
    await cas("cost_invoices", {"id": inv["id"]}, {"paid": inv.get("paid"), "status": inv.get("status")},
              {"$set": {"paid": paid, "outstanding": int(inv["total"]) - paid,
                        "status": "paid" if paid >= int(inv["total"]) else "partial", "updated_at": ts}},
              what="Invoice biaya ini")
    try:
        rc = {"id": rid, "org_id": org, "contract_id": inv["contract_id"], "deal_id": inv.get("deal_id"),
              "invoice_id": inv["id"], "invoice_no": inv["number"], "unit_code": inv.get("unit_code"),
              "customer_name": inv.get("customer_name"), "kind": "cost",
              "receipt_no": await seq.next_number("cost_receipt", org, prefix="KWB",
                                                  context={"unit_id": inv.get("unit_id"),
                                                           "customer_id": inv.get("customer_id")}),
              "amount": amount, "method": method or "transfer", "note": note, "status": "posted",
              "proof_file_ids": [str(f) for f in (proof_file_ids or []) if f],
              "cash_account_id": cash_acc.get("id"), "cash_account_name": cash_acc.get("name"),
              "cash_account_code": cash_code, "actor": actor, "created_at": ts,
              **({"cancel_override": cancel_ov} if cancel_ov else {})}
        await db.cost_receipts.insert_one(dict(rc))
        rc.pop("_id", None)
        je = await gl.post_journal(org, f"Titipan biaya pembeli diterima — {rc['receipt_no']}", [
            {"account_code": cash_code, "debit": amount, "credit": 0},
            {"account_code": GL_TITIPAN_BIAYA, "debit": 0, "credit": amount}],
            source_type="cost_receipt", source_id=rc["id"], source_event=f"cost_receipt:{rc['id']}",
            posted_by=actor, source_deal_id=inv.get("deal_id"))
    except BaseException:
        await db.cost_receipts.delete_one({"id": rid})
        await db.cost_invoices.update_one({"id": inv["id"], "paid": paid}, {"$set": {
            "paid": int(inv["paid"]), "outstanding": int(inv["outstanding"]),
            "status": inv.get("status"), "updated_at": ts}})
        raise
    return {"receipt": rc, "journal_id": je.get("id")}


async def disburse_titipan(org: str, contract: dict, component_code: str, amount: int,
                           payee: str, note: str, actor: str, cash_account_id: str = None,
                           cancelled_override: dict = None) -> dict:
    """Salurkan titipan ke notaris/BPN → Titipan / Kas. Tidak boleh melebihi sisa titipan.

    FN-03 (sisa): pada deal/kontrak yang sudah BATAL penyaluran ditolak kecuali `cancelled_override` (lihat
    `pay_cost_invoice`); dicek di bawah mutex deal yang sama dengan pembatalan.

    PK-02: dua penyaluran bersamaan dulu sama-sama membaca sisa titipan yang sama lalu keduanya
    mengeluarkan kas. Sekarang diserialkan per kontrak (mutex) dengan kunci klik ganda; sisa titipan
    dibaca ULANG di dalam kunci, lalu dana kas diperiksa (PK-06).
    """
    import cancellation_costs as cc
    from deal_money import deal_money
    async with deal_money(org, contract.get("deal_id")):
        ov = await cc.assert_movable(org, deal_id=contract.get("deal_id"), contract_id=contract.get("id"),
                                     what="Penyaluran titipan biaya", override=cancelled_override)
        return await _disburse_titipan(org, contract, component_code, amount, payee, note, actor, cash_account_id, ov)


async def _disburse_titipan(org: str, contract: dict, component_code: str, amount: int,
                            payee: str, note: str, actor: str, cash_account_id: str, cancel_ov: dict) -> dict:
    amount = int(amount or 0)
    if amount <= 0:
        raise ValueError("Nominal penyaluran wajib > 0.")
    if not (payee or "").strip():
        raise ValueError("Penerima (notaris/BPN) wajib diisi.")
    led = await ledger(org, contract)
    if amount > led["titipan_balance"]:
        raise ValueError(f"Penyaluran Rp {amount:,} melebihi sisa titipan Rp {led['titipan_balance']:,}.".replace(",", "."))
    import cash_bank as _cb
    async with once("allin.disburse", org, contract.get("id"), component_code, amount, payee.strip(), actor,
                    what="Penyaluran titipan ini"):
        async with mutex(f"allin.titipan:{org}:{contract.get('id')}", what="Titipan biaya kontrak ini"):
            led = await ledger(org, contract)
            if amount > led["titipan_balance"]:
                raise ValueError(f"Penyaluran Rp {amount:,} melebihi sisa titipan "
                                 f"Rp {led['titipan_balance']:,}.".replace(",", "."))
            bank_code = await _cb.resolve_code(org, cash_account_id, GL_BANK)
            async with _cb.cash_lock(org, bank_code):
                await _cb.assert_funds(org, amount, code=bank_code, kind="penyaluran titipan biaya")
                ts = now_iso()
                doc = {"id": new_id(), "org_id": org, "contract_id": contract.get("id"),
                       "deal_id": contract.get("deal_id"), "component_code": component_code,
                       "amount": amount, "payee": payee.strip(), "note": note,
                       "actor": actor, "created_at": ts,
                       **({"cancel_override": cancel_ov} if cancel_ov else {})}
                await db.cost_disbursements.insert_one(dict(doc))
                doc.pop("_id", None)
                je = await gl.post_journal(org, f"Penyaluran titipan biaya ({component_code}) ke {payee.strip()}", [
                    {"account_code": GL_TITIPAN_BIAYA, "debit": amount, "credit": 0},
                    {"account_code": bank_code, "debit": 0, "credit": amount}],
                    source_type="cost_disbursement", source_id=doc["id"], source_event=f"cost_disb:{doc['id']}",
                    posted_by=actor, source_deal_id=contract.get("deal_id"))
    return {"disbursement": doc, "journal_id": je.get("id"), "titipan_balance": led["titipan_balance"] - amount}


async def record_developer_expense(org: str, contract: dict, component_code: str, amount: int,
                                   vendor: str, note: str, actor: str) -> dict:
    """Komponen developer_borne: developer bayar notaris/BPN lewat AP → Beban penjualan / Utang usaha."""
    comps = {c["code"]: c for c in (contract.get("costs") or {}).get("components") or []}
    comp = comps.get(component_code)
    if not comp or comp.get("treatment") != "developer_borne":
        raise ValueError("Komponen ini bukan tanggungan developer (developer_borne).")
    amount = int(amount or comp.get("amount") or 0)
    if amount <= 0:
        raise ValueError("Nominal beban wajib > 0.")
    if await db.cost_expenses.find_one({"org_id": org, "contract_id": contract["id"], "component_code": component_code}):
        raise ValueError(f"Beban {component_code} untuk kontrak ini sudah dicatat.")
    # PK-02: dua pencatatan beban yang sama bersamaan dulu sama-sama lolos cek di atas (2 tagihan + 2 jurnal).
    async with once("allin.devexpense", org, contract["id"], component_code, what="Pencatatan beban ini"):
        deal = await db.deals.find_one({"id": contract.get("deal_id")}, {"_id": 0, "project_id": 1}) or {}
        bill = await fe.create_ap_bill(vendor or "Notaris/BPN", deal.get("project_id"), amount, 0, None,
                                       f"Biaya {comp['name']} all-in kontrak {contract.get('number')}", actor, org_id=org)
        ts = now_iso()
        await db.ap_invoices.update_one({"id": bill["id"]}, {"$set": {
            "status": "approved", "approved_by": actor, "approved_at": ts, "kind": "sales_cost",
            "contract_id": contract["id"], "component_code": component_code, "gl_expense": comp.get("gl_expense")}})
        je = await gl.post_journal(org, f"Beban penjualan {comp['name']} (all-in) — {contract.get('number')}", [
            {"account_code": comp.get("gl_expense") or GL_BEBAN_PENJUALAN, "debit": amount, "credit": 0},
            {"account_code": comp.get("gl_ap") or GL_AP, "debit": 0, "credit": amount}],
            source_type="ap_bill", source_id=bill["id"], source_event=f"ap.sales_cost:{bill['id']}",
            posted_by=actor, source_deal_id=contract.get("deal_id"))
        doc = {"id": new_id(), "org_id": org, "contract_id": contract["id"], "deal_id": contract.get("deal_id"),
               "component_code": component_code, "amount": amount, "vendor": vendor or "Notaris/BPN",
               "ap_bill_id": bill["id"], "journal_id": je.get("id"), "note": note, "actor": actor, "created_at": ts}
        await db.cost_expenses.insert_one(dict(doc))
        doc.pop("_id", None)
    return {"expense": doc, "ap_bill": bill}
