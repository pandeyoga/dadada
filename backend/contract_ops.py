"""Aksi kontrak yang mengubah SKEMA / JADWAL TAGIHAN — dipisah dari `contracts_engine.py`.

## KT-05 — ganti jenis skema kontrak

`set_scheme` dulu hanya menulis `contract.scheme`. Deal (`scheme_id`), AR (item termin) dan
pengajuan KPR tetap milik jenis LAMA, sehingga kontrak "KPR" bertagihan cash keras: tidak ada SPR
yang bisa terbit (blok `skema_deal_beda`), gerbang akad kredit tanpa pengajuan KPR. Sekarang jenis
baru diselaraskan ke deal, AR, dan pengajuan KPR sekaligus — atau DITOLAK dengan alasan jelas bila
perubahan itu tidak aman (sudah ada uang nyata / SPR bertanda tangan / KPR berjalan / tahap legal).

## KT-06 / KT-11 — aktivasi

`activate` idempoten: kontrak yang sudah aktif TIDAK menyusun ulang jadwal tagihan (dulu setiap
klik membangun ulang AR, mengacak alokasi pembayaran, dan menerbitkan ulang event+notifikasi).
Dasar tanggal jatuh tempo = saat aktivasi ("N hari setelah kontrak diaktifkan").
"""
import finance_engine as fin
import kpr_engine as kprmod
import payment_scheme_engine as psx
import reference as ref
from builtin_schemes import ensure_payment_scheme
from core_utils import now_iso
from db import db
from engine import add_activity
from idempotency import mutex, reserved


def _ce():
    """Impor malas `contracts_engine` — memutus siklus impor."""
    import contracts_engine as ce
    return ce


def _rp(v) -> str:
    return f"Rp {int(v or 0):,}".replace(",", ".")


async def _real_money(org: str, deal_id: str) -> int:
    """Uang NYATA (kuitansi kas/KPR, bukan pemakaian titipan/booking fee) yang sudah diterima."""
    n = 0
    async for r in db.receipts.find(
            {"org_id": org, "deal_id": deal_id, "funding": {"$ne": "deposit"},
             "status": {"$ne": "void"}, "applied": {"$gt": 0}}, {"_id": 0, "applied": 1}):
        n += int(r.get("applied") or 0)
    return n


async def _guard_kind_change(org: str, c: dict, scheme: str) -> None:
    """Tolak ganti jenis skema bila perubahannya tidak aman — pesan menyebut jalan keluarnya."""
    ce = _ce()
    if c.get("state") in ("cancelled", "completed"):
        raise ValueError(f"Kontrak berstatus {c.get('state')} — jenis skema tidak bisa diubah.")
    if any((c.get("legal") or {}).get(s) for s in ce.LEGAL_ORDER):
        raise ValueError("Skema tidak bisa diubah setelah ada tahap legal — terbitkan "
                         "adendum/kontrak baru.")
    money = await _real_money(org, c["deal_id"])
    if money > 0:
        raise ValueError(
            f"Sudah ada penerimaan {_rp(money)} pada kontrak ini. Mengganti jenis skema akan "
            "menyusun ulang jadwal yang sebagian sudah dibayar — terbitkan adendum, jangan "
            "menimpa jadwal berjalan.")
    signed = await db.documents.find_one(
        {"org_id": org, "deal_id": c["deal_id"], "status": "signed",
         "template_code": {"$in": list(ce.SCHEME_DOC.values())}},
        {"_id": 0, "doc_number": 1})
    if signed:
        raise ValueError(
            f"SPR {signed.get('doc_number')} sudah ditandatangani pembeli dengan jenis skema "
            f"{ref.label_of('payment_scheme', c.get('scheme'))}. Ganti jenis lewat adendum, "
            "bukan mengubah kontrak diam-diam.")
    if c.get("scheme") == "kpr" and scheme != "kpr":
        app = await db.financing_apps.find_one({"org_id": org, "deal_id": c["deal_id"]},
                                               {"_id": 0}, sort=[("created_at", -1)]) or {}
        if app and (app.get("kpr_stage") not in (None, "", "berkas_lengkap")
                    or int(app.get("approved_plafon") or 0) > 0
                    or int(app.get("disbursed_total") or 0) > 0):
            raise ValueError("Pengajuan KPR sudah berjalan (sudah melewati tahap berkas). Batalkan/"
                             "selesaikan pengajuan KPR itu dulu sebelum mengganti ke skema tunai.")


async def set_scheme(org: str, contract_id: str, scheme: str, actor: str,
                     reason: str = None) -> dict:
    """Ganti JENIS skema kontrak dan selaraskan deal + AR + pengajuan KPR (KT-05)."""
    ce = _ce()
    if scheme not in ce.SCHEMES:
        raise ValueError(f"Skema '{scheme}' tidak dikenal.")
    async with mutex(f"contract:{contract_id}", wait=15, ttl=60, what="Kontrak ini"):
        c = await ce.get_raw(org, contract_id)
        if c.get("scheme") == scheme:
            return c
        await _guard_kind_change(org, c, scheme)
        deal = await db.deals.find_one({"id": c["deal_id"]}, {"_id": 0}) or {}
        hasil = await psx.resolve_for_contract(
            org, {"scheme": scheme, "project_id": c.get("project_id")})
        sch = hasil.get("scheme") or await ensure_payment_scheme(org, scheme)
        ts = now_iso()
        histori = {"from": c.get("scheme"), "to": scheme, "at": ts, "by": actor, "reason": reason}
        baru = {"scheme": scheme, "scheme_label": ref.label_of("payment_scheme", scheme),
                "payment_scheme_id": sch["id"], "payment_scheme_name": sch.get("name"),
                "updated_at": ts}
        lama = {k: c.get(k) for k in baru}
        async with reserved("contracts", {"id": contract_id},
                            {"scheme": c.get("scheme"), "state": c.get("state")},
                            {"$set": baru, "$push": {"scheme_history": histori}},
                            undo={"$set": lama, "$pop": {"scheme_history": 1}},
                            what="Kontrak ini"):
            # Jadwal tagihan lahir bila deal sudah booking; jenis baru memakai skema jenis itu.
            if deal and await db.ar_invoices.find_one({"org_id": org, "deal_id": deal["id"]},
                                                      {"_id": 0, "id": 1}):
                await fin.create_ar_for_deal({**deal, "scheme_id": sch["id"]}, scheme_id=sch["id"],
                                             org_id=org, replace=True, actor=actor)
            if deal:
                await db.deals.update_one({"id": deal["id"]}, {
                    "$set": {"scheme_id": sch["id"], "scheme_explicit": True, "updated_at": ts},
                    "$push": {"scheme_history": {
                        "from": deal.get("scheme_id"), "to": sch["id"], "at": ts, "by": actor,
                        "reason": "jenis skema kontrak diubah: "
                                  + (reason or ref.label_of("payment_scheme", scheme))}}})
        c = await ce.get_raw(org, contract_id)
        if scheme == "kpr":
            await fin.tag_bank_items_for_deal(org, c["deal_id"])
            await kprmod.ensure_kpr_app(org, c, actor)
    await add_activity(entity_type="customer", entity_id=c.get("customer_id"),
                       type="system", actor=actor, org_id=org,
                       body=(f"Skema kontrak {c.get('number')} diubah menjadi "
                             f"{ref.label_of('payment_scheme', scheme)}"
                             + (f" — {reason}" if reason else ".")))
    return c


async def activate(org: str, contract_id: str, actor: str) -> dict:
    """Aktifkan kontrak: termin AR dibuat/disegarkan dari skema `[DOC]` kontrak ini. IDEMPOTEN.

    Kenapa AR dibuat ulang: saat deal di-booking, AR lahir dari skema BAWAAN keuangan
    ("Standar KPR (DP 20%)") — bukan skema kontrak. Sesudah kontrak punya skema resmi,
    tagihan harus mengikuti dokumen yang ditandatangani pembeli, bukan bawaan sistem.
    Hanya SEKALI: kontrak yang sudah aktif dikembalikan apa adanya (KT-06).
    """
    ce = _ce()
    async with mutex(f"contract:{contract_id}", wait=15, ttl=60, what="Kontrak ini"):
        c = await ce.get_raw(org, contract_id)
        if c.get("state") == "active":
            return c
        if c.get("state") in ("completed", "cancelled"):
            raise ValueError(f"Kontrak berstatus {c.get('state')} — tidak bisa diaktifkan.")
        deal = await db.deals.find_one({"id": c["deal_id"]}, {"_id": 0})
        if not deal:
            raise ValueError("Deal kontrak ini tidak ditemukan.")
        if deal.get("status") not in ("booked", "completed"):
            raise ValueError("Kontrak hanya bisa diaktifkan setelah reservasi dikonfirmasi "
                             "(booking).")
        scheme_doc = (await psx.resolve_for_contract(org, c)).get("scheme") \
            or await ensure_payment_scheme(org, c.get("scheme"))
        ts = now_iso()
        inv = await fin.create_ar_for_deal(deal, scheme_id=scheme_doc["id"], org_id=org,
                                           replace=True, actor=actor, base_date=ts)
        await db.contracts.update_one({"id": contract_id}, {"$set": {
            "state": "active", "activated_at": ts, "activated_by": actor,
            "ar_invoice_id": inv.get("id"), "payment_scheme_id": scheme_doc["id"],
            "payment_scheme_name": scheme_doc.get("name"), "updated_at": ts}})
    await add_activity(entity_type="customer", entity_id=c.get("customer_id"),
                       type="system", actor=actor, org_id=org,
                       body=(f"Kontrak {c.get('number')} diaktifkan — termin mengikuti "
                             f"skema {scheme_doc.get('name')} (total "
                             f"{_rp(inv.get('total'))})."))
    return await ce.get_raw(org, contract_id)
