"""FASE E-8 (E8.7/E8.15/E8.20) — **MEJA KERJA BERBASIS ANTREAN** (Admin Sales & Finance).

KENAPA BERKAS INI ADA
=====================
Temuan A9 (`ANALISIS_DOMAIN_SALES.md`): keputusan yang harus diambil Admin Sales
tersebar di **lima layar milik domain lain** (Pembelian, Gudang, Keuangan, CRM,
Antar Entitas). Orang yang seharusnya menjaga alur pesanan justru harus berkeliling
menu untuk tahu "apa yang menunggu saya hari ini" — dan karena tidak ada satu tempat
yang menghitungnya, pekerjaan basi tanpa ada yang sadar.

Yang dibangun di sini **bukan mesin baru**: seluruh angka diambil dari mesin yang
sudah terbukti (papan pending SO, backorder, retur, permintaan internal, pengingat
penagihan, selisih bayar, denda). Modul ini hanya **menyusunnya jadi antrean kerja**
dengan satu tindakan jelas per baris.

DUA MEJA, SESUAI KEPUTUSAN PEMILIK (E8.10b#2)
---------------------------------------------
* **Meja Admin Sales** (8 antrean) — alur pesanan: verifikasi → konfirmasi → dokumen
  → pemenuhan → retur → permintaan internal. **Faktur pajak & uang masuk TIDAK di
  sini** (itu Finance) supaya pemisahan tugas terlihat di layar, bukan cuma di izin.
* **Meja Finance** (5 antrean) — uang masuk & pajak keluaran: faktur pajak siap
  terbit, uang masuk perlu dicatat, selisih bayar, denda perlu diterbitkan, jatuh tempo.

Tiap baris membawa: konteks pelanggan · nilai · **umur (hari)** · tindakan tunggal.
Umur dipakai sebagai isyarat SLA: makin tua, makin merah di layar.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from db import db
from core_utils import now_iso, safe_doc

ROW_LIMIT = 60

# ── Status pesanan per tahap alur ────────────────────────────────────────────
STATUS_BARU = ("reserved", "waiting_stock")
STATUS_SIAP_KONFIRMASI = ("approved",)
STATUS_MENUNGGU_MANAJER = ("waiting_approval",)
STATUS_DOKUMEN = ("confirmed", "partially_picked", "picked", "partially_shipped", "shipped")
STATUS_PAJAK_LAYAK = ("confirmed", "partially_picked", "picked", "partially_shipped",
                      "shipped", "done")
RETUR_ANTREAN = ("pending_approval", "approved", "pending_process", "quarantine")
PIN_ANTREAN = ("draft", "submitted", "open", "pending")


def _age_days(iso: Optional[str]) -> int:
    if not iso:
        return 0
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if not t.tzinfo:
            t = t.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - t).days)
    except Exception:  # noqa: BLE001
        return 0


def _q(scope: Dict[str, Any], extra: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(scope or {})
    out.update(extra)
    return out


def _row(*, ref_type: str, ref_id: str, number: str, title: str, subtitle: str = "",
         value: float = 0.0, age_days: int = 0, badge: str = "",
         action: str = "", action_kind: str = "open", extra: Optional[Dict[str, Any]] = None
         ) -> Dict[str, Any]:
    return {"ref_type": ref_type, "ref_id": ref_id, "number": number, "title": title,
            "subtitle": subtitle, "value": round(float(value or 0), 2),
            "age_days": int(age_days), "badge": badge,
            "action": action, "action_kind": action_kind, **(extra or {})}


def _queue(qid: str, label: str, hint: str, rows: List[Dict[str, Any]], *,
           action_label: str = "", owner: str = "sales_admin",
           value_kind: str = "money", value_label: str = "Nilai") -> Dict[str, Any]:
    """Bungkus satu antrean + ringkasannya.

    `value_kind` ada karena tidak semua antrean menghitung RUPIAH: antrean
    "Perlu dipenuhi" menghitung **jumlah barang yang kurang** (yard/meter). Tanpa
    penanda ini layar akan menuliskan `Rp 200` untuk 200 yard — angka yang salah
    arti, dan jenis kekeliruan yang membuat pengguna berhenti percaya pada ringkasan.
    """
    rows = rows[:ROW_LIMIT]
    return {
        "id": qid, "label": label, "hint": hint, "owner": owner,
        "count": len(rows),
        "total_value": round(sum(r["value"] for r in rows), 2),
        "value_kind": value_kind, "value_label": value_label,
        "oldest_age_days": max([r["age_days"] for r in rows], default=0),
        "action_label": action_label,
        "rows": rows,
    }


async def _orders(scope: Dict[str, Any], statuses, *, verified: Optional[bool] = None
                  ) -> List[Dict[str, Any]]:
    flt = _q(scope, {"status": {"$in": list(statuses)}, "order_type": {"$ne": "sample"}})
    rows = await db.sales_orders.find(flt, {
        "_id": 0, "id": 1, "number": 1, "customer_name": 1, "customer_city": 1,
        "grand_total": 1, "total_amount": 1, "created_at": 1, "status": 1, "stage": 1,
        "sales_name": 1, "verification": 1, "entity_id": 1, "is_pkp": 1, "ppn_amount": 1,
        "payment_status": 1, "pending_approvals": 1, "required_approval_role": 1,
    }).sort("created_at", 1).to_list(500)
    out = []
    for o in rows:
        ver = ((o.get("verification") or {}).get("status") == "verified")
        if verified is True and not ver:
            continue
        if verified is False and ver:
            continue
        out.append(safe_doc(o))
    return out


# ═══════════════════════════════════════════════════════════════════════════
# MEJA ADMIN SALES
# ═══════════════════════════════════════════════════════════════════════════
async def sales_admin_desk(actor: Dict[str, Any], scope: Dict[str, Any],
                           entity_ids: List[str]) -> Dict[str, Any]:
    queues: List[Dict[str, Any]] = []

    # 1 — perlu diverifikasi (E8.13): pesanan baru dari sales, belum diperiksa
    belum = await _orders(scope, STATUS_BARU, verified=False)
    queues.append(_queue(
        "perlu_verifikasi", "Perlu diverifikasi",
        "Periksa kelengkapan: alamat & penerima · syarat bayar · PPN · NPWP bila minta faktur.",
        [_row(ref_type="sales_order", ref_id=o["id"], number=o["number"],
              title=o.get("customer_name", "—"),
              subtitle=f"{o.get('customer_city') or '—'} · dibuat {o.get('sales_name') or '—'}",
              value=o.get("grand_total") or o.get("total_amount") or 0,
              age_days=_age_days(o.get("created_at")), badge=o.get("stage") or o.get("status"),
              action="Verifikasi", action_kind="verify") for o in belum],
        action_label="Verifikasi"))

    # 2 — siap dikonfirmasi: sudah disetujui → tekan konfirmasi, tugas gudang lahir
    approved = await _orders(scope, STATUS_SIAP_KONFIRMASI)
    queues.append(_queue(
        "siap_dikonfirmasi", "Siap dikonfirmasi",
        "Konfirmasi memicu tugas gudang. Wewenang Anda — tidak perlu menunggu manajer.",
        [_row(ref_type="sales_order", ref_id=o["id"], number=o["number"],
              title=o.get("customer_name", "—"),
              subtitle=("Terverifikasi" if (o.get("verification") or {}).get("status") == "verified"
                        else "Belum diverifikasi"),
              value=o.get("grand_total") or o.get("total_amount") or 0,
              age_days=_age_days(o.get("created_at")), badge=o.get("stage") or o.get("status"),
              action="Konfirmasi", action_kind="confirm") for o in approved],
        action_label="Konfirmasi"))

    # 3 — menunggu keputusan manajer (harga khusus/kredit/nilai) → hanya memantau
    tunggu = await _orders(scope, STATUS_MENUNGGU_MANAJER)
    queues.append(_queue(
        "menunggu_manajer", "Menunggu keputusan manajer",
        "Nilai · kredit · harga khusus adalah keputusan manajer. Anda memantau, bukan menyetujui.",
        [_row(ref_type="sales_order", ref_id=o["id"], number=o["number"],
              title=o.get("customer_name", "—"),
              subtitle="Butuh peran " + str(o.get("required_approval_role") or "manager"),
              value=o.get("grand_total") or o.get("total_amount") or 0,
              age_days=_age_days(o.get("created_at")), badge="menunggu",
              action="Lihat", action_kind="open") for o in tunggu],
        action_label="Lihat"))

    # 4 — siap cetak Surat Jalan / Invoice
    dok = await _orders(scope, STATUS_DOKUMEN)
    queues.append(_queue(
        "siap_cetak_dokumen", "Siap cetak Surat Jalan / Invoice",
        "Dokumen pengiriman & tagihan untuk pesanan yang sudah dikonfirmasi.",
        [_row(ref_type="sales_order", ref_id=o["id"], number=o["number"],
              title=o.get("customer_name", "—"), subtitle=o.get("stage") or o.get("status"),
              value=o.get("grand_total") or o.get("total_amount") or 0,
              age_days=_age_days(o.get("created_at")), badge=o.get("status"),
              action="Cetak", action_kind="open") for o in dok],
        action_label="Cetak"))

    # 5 — perlu dipenuhi (kurang stok) → TIGA tombol keputusan pemenuhan (US16)
    from services import stock_bucket_service as sbs
    pend = await sbs.pending_so_board(dict(scope or {}))
    per_order: Dict[str, Dict[str, Any]] = {}
    for b in pend:
        cur = per_order.setdefault(b["order_id"], {
            "order_number": b["order_number"], "customer_name": b.get("customer_name", "—"),
            "lines": [], "created_at": b.get("created_at"), "coverage": "covered"})
        cur["lines"].append(b)
        if b.get("coverage") != "covered":
            cur["coverage"] = b.get("coverage") or "partial"
    queues.append(_queue(
        "perlu_dipenuhi", "Perlu dipenuhi (kurang stok)",
        "Pilih SATU: ambil dari PT lain · reorder ke supplier · tahan untuk barang masuk.",
        [_row(ref_type="sales_order", ref_id=oid, number=v["order_number"],
              title=v["customer_name"],
              subtitle=" · ".join(f"{ln['product_name']} kurang "
                                  f"{ln['backorder_qty']:g} {ln['unit']}"
                                  for ln in v["lines"][:2]),
              value=sum(float(ln.get("backorder_qty") or 0) for ln in v["lines"]),
              age_days=_age_days(v.get("created_at")),
              badge=v["coverage"], action="Putuskan pemenuhan", action_kind="fulfill",
              extra={"lines": v["lines"],
                     "unit": (v["lines"][0].get("unit") if v["lines"] else "")})
         for oid, v in per_order.items()],
        action_label="Putuskan pemenuhan",
        # Yang dijumlahkan di sini JUMLAH BARANG yang kurang, bukan rupiah.
        value_kind="qty", value_label="Kurang"))

    # 6 — jatuh tempo & pengingat (Admin Sales memantau SELURUH pelanggan)
    from services.customer_service import collection_reminders
    tagih = await collection_reminders(actor, days_ahead=30,
                                       entity_id=entity_ids[0] if len(entity_ids) == 1 else None)
    queues.append(_queue(
        "jatuh_tempo", "Jatuh tempo & pengingat",
        "Tagihan lewat/nyaris jatuh tempo. Pencatatan uangnya di Meja Finance.",
        [_row(ref_type="sales_order", ref_id=r["order_id"], number=r["order_number"],
              title=r.get("customer_name", "—"),
              subtitle=(f"lewat {r['days_late']} hari" if r.get("overdue")
                        else f"jatuh tempo {abs(r['days_late'])} hari lagi"),
              value=r.get("outstanding") or 0,
              age_days=max(0, int(r.get("days_late") or 0)),
              badge="lewat" if r.get("overdue") else "segera",
              action="Follow-up", action_kind="open") for r in tagih],
        action_label="Follow-up"))

    # 7 — retur menunggu proses dokumen (diajukan sales, diproses Admin Sales)
    ret = await db.sales_returns.find(
        _q(scope, {"status": {"$in": list(RETUR_ANTREAN)}}),
        {"_id": 0, "id": 1, "number": 1, "customer_name": 1, "order_number": 1,
         "status": 1, "created_at": 1, "total_refund": 1, "items": 1, "return_type": 1}
    ).sort("created_at", 1).to_list(200)
    queues.append(_queue(
        "retur", "Retur menunggu proses dokumen",
        "Sales mengajukan, Anda memproses dokumennya. Persetujuan akhir tetap manajer.",
        [_row(ref_type="sales_return", ref_id=r["id"], number=r.get("number", "—"),
              title=r.get("customer_name", "—"),
              subtitle=f"atas {r.get('order_number') or '—'} · {len(r.get('items') or [])} baris",
              value=r.get("total_refund") or 0, age_days=_age_days(r.get("created_at")),
              badge=r.get("status", ""), action="Proses", action_kind="open")
         for r in map(safe_doc, ret)],
        action_label="Proses"))

    # 8 — permintaan internal dari sales (E8.8) → jadikan transaksi antar-PT
    pin = await db.internal_requests.find(
        _q(scope, {"status": {"$in": list(PIN_ANTREAN)}}),
        {"_id": 0, "id": 1, "number": 1, "reason": 1, "status": 1, "created_at": 1,
         "est_value": 1, "items": 1, "requested_by_name": 1, "source_order_number": 1}
    ).sort("created_at", 1).to_list(200)
    queues.append(_queue(
        "permintaan_internal", "Permintaan internal dari sales",
        "Sales meminta barang dari PT lain — Anda yang memilih sumbernya & mengesahkan.",
        [_row(ref_type="internal_request", ref_id=r["id"], number=r.get("number", "—"),
              title=r.get("reason", "—")[:70] or "—",
              subtitle=(f"untuk {r.get('source_order_number')}" if r.get("source_order_number")
                        else f"{len(r.get('items') or [])} barang"),
              value=r.get("est_value") or 0, age_days=_age_days(r.get("created_at")),
              badge=r.get("status", ""), action="Tindak", action_kind="open")
         for r in map(safe_doc, pin)],
        action_label="Tindak"))

    # Fase 4 OD — pesanan khusus yang butuh tindakan Admin Sales (ACC pelanggan · kunci harga · siap kirim).
    try:
        from services import special_order_phase2 as _p2
        od_rows = await _p2.desk_rows(scope)
    except Exception:  # noqa: BLE001
        od_rows = {"acc_pelanggan": [], "kunci_harga": [], "siap_kirim": []}
    queues.append(_queue(
        "od_acc_pelanggan", "Pesanan khusus — menunggu ACC pelanggan",
        "Sample sudah diputus pemenang. Hubungi pelanggan, catat ACC / revisi / tolak + bukti di rincian OD.",
        [_row(ref_type="special_order", ref_id=o["id"], number=o.get("number", "—"), title=o.get("customer_name", "—"),
              subtitle=f"{', '.join(o.get('request_types') or [])} · sample {((o.get('basis') or {}).get('sample') or {}).get('number') or ((o.get('basis') or {}).get('design') or {}).get('code') or '—'}",
              value=o.get("total_amount") or 0, age_days=_age_days(o.get("updated_at")), badge="ACC pelanggan",
              action="Catat ACC", action_kind="open") for o in od_rows["acc_pelanggan"]],
        action_label="Catat ACC"))
    queues.append(_queue(
        "od_kunci_harga", "Pesanan khusus — perlu kunci harga",
        "Pelanggan sudah ACC. Tetapkan margin & kunci harga final → PR/PO ke supplier pemenang lahir otomatis.",
        [_row(ref_type="special_order", ref_id=o["id"], number=o.get("number", "—"), title=o.get("customer_name", "—"),
              subtitle=f"kontrak Rp {float((o.get('pricing_preview') or {}).get('cost_price') or 0):,.0f} → final Rp {float((o.get('pricing_preview') or {}).get('final_unit_price') or 0):,.0f}/{(o.get('pricing_preview') or {}).get('unit', 'meter')}",
              value=(o.get("pricing_preview") or {}).get("total") or 0, age_days=_age_days(o.get("customer_decision_at") or o.get("updated_at")),
              badge="Kunci harga", action="Kunci harga", action_kind="open") for o in od_rows["kunci_harga"]],
        action_label="Kunci harga"))
    if od_rows["siap_kirim"]:
        queues.append(_queue(
            "od_siap_kirim", "Pesanan khusus — barang siap, pengiriman belum disiapkan",
            "PO sudah diterima gudang tetapi Surat Jalan belum lahir. Buka OD → 'Siapkan pengiriman'.",
            [_row(ref_type="special_order", ref_id=o["id"], number=o.get("number", "—"), title=o.get("customer_name", "—"),
                  subtitle=o.get("shipping_error") or "SO belum dikonversi", value=o.get("total_amount") or 0,
                  age_days=_age_days(o.get("updated_at")), badge="Siap kirim", action="Siapkan", action_kind="open") for o in od_rows["siap_kirim"]],
            action_label="Siapkan"))

    return {"desk": "sales_admin", "desk_label": "Meja Admin Sales",
            "generated_at": now_iso(), "entity_ids": entity_ids,
            "queues": queues,
            "totals": {"open_items": sum(q["count"] for q in queues)},
            "not_my_desk": ["Faktur Pajak keluaran", "Pencatatan uang masuk (kwitansi AR)",
                            "Keputusan selisih bayar"]}


# ═══════════════════════════════════════════════════════════════════════════
# MEJA FINANCE
# ═══════════════════════════════════════════════════════════════════════════
async def finance_desk(actor: Dict[str, Any], scope: Dict[str, Any],
                       entity_ids: List[str]) -> Dict[str, Any]:
    queues: List[Dict[str, Any]] = []

    # 1 — siap terbitkan Faktur Pajak: pesanan layak pajak yang belum ber-faktur aktif
    layak = await _orders(scope, STATUS_PAJAK_LAYAK)
    ids = [o["id"] for o in layak]
    ber_faktur = set()
    if ids:
        async for f in db.tax_invoices.find(
                {"order_id": {"$in": ids}, "status": {"$ne": "batal"}},
                {"_id": 0, "order_id": 1}):
            ber_faktur.add(f["order_id"])
    kandidat = [o for o in layak
                if o.get("is_pkp") is not False and float(o.get("ppn_amount") or 0) > 0
                and o["id"] not in ber_faktur]
    queues.append(_queue(
        "siap_faktur_pajak", "Siap terbitkan Faktur Pajak",
        "Pesanan ber-PPN yang belum punya faktur pajak keluaran aktif.",
        [_row(ref_type="sales_order", ref_id=o["id"], number=o["number"],
              title=o.get("customer_name", "—"),
              subtitle=f"PPN {float(o.get('ppn_amount') or 0):,.0f}".replace(",", "."),
              value=o.get("grand_total") or o.get("total_amount") or 0,
              age_days=_age_days(o.get("created_at")), badge=o.get("status", ""),
              action="Terbitkan", action_kind="issue_tax") for o in kandidat],
        action_label="Terbitkan", owner="finance"))

    # 2 & 5 — uang masuk perlu dicatat + jatuh tempo (dari pengingat penagihan)
    from services.customer_service import collection_reminders
    tagih = await collection_reminders(actor, days_ahead=30,
                                       entity_id=entity_ids[0] if len(entity_ids) == 1 else None)
    queues.append(_queue(
        "uang_masuk", "Uang masuk perlu dicatat & dialokasikan",
        "Catat kwitansi AR lalu alokasikan ke invoice — inilah wewenang inti Anda.",
        [_row(ref_type="customer", ref_id=r["customer_id"], number=r["order_number"],
              title=r.get("customer_name", "—"),
              subtitle=("lewat " + str(r["days_late"]) + " hari" if r.get("overdue")
                        else "belum jatuh tempo"),
              value=r.get("outstanding") or 0,
              age_days=max(0, int(r.get("days_late") or 0)),
              badge="lewat" if r.get("overdue") else "segera",
              action="Catat kwitansi", action_kind="receipt",
              extra={"order_id": r["order_id"], "row_key": r["order_id"]}) for r in tagih],
        action_label="Catat kwitansi", owner="finance"))

    # 3 — selisih bayar (lebih/kurang bayar) dalam batas kewenangan Finance
    from services import payment_variance_service as pvs
    ent_scope: Any = scope.get("entity_id") if isinstance(scope, dict) else ""
    selisih = await pvs.pending(ent_scope or "")
    queues.append(_queue(
        "selisih_bayar", "Selisih bayar perlu diputuskan",
        "Lebih/kurang bayar yang belum diputus. Di luar batas kewenangan → manajer.",
        [_row(ref_type="ar_receipt", ref_id=r.get("id", ""), number=r.get("number", "—"),
              title=r.get("customer_name", "—"),
              subtitle=str((r.get("variance") or {}).get("kind_label")
                           or (r.get("variance") or {}).get("kind") or "selisih"),
              value=abs(float((r.get("variance") or {}).get("amount") or 0)),
              age_days=_age_days(r.get("created_at")), badge="perlu keputusan",
              action="Putuskan", action_kind="decide_variance")
         for r in map(safe_doc, selisih)],
        action_label="Putuskan", owner="finance"))

    # 4 — denda perlu diterbitkan (draf hasil hitungan sistem)
    denda = await db.penalties.find(
        _q(scope, {"status": "draft"}),
        {"_id": 0, "id": 1, "number": 1, "customer_name": 1, "amount": 1, "created_at": 1,
         "doc_number": 1, "days_late": 1}
    ).sort("created_at", 1).to_list(200)
    queues.append(_queue(
        "denda_draft", "Denda perlu diterbitkan",
        "Nota denda hasil hitungan sistem — Anda yang menerbitkan; pembebasan → manajer.",
        [_row(ref_type="penalty", ref_id=d["id"], number=d.get("number", "—"),
              title=d.get("customer_name", "—"),
              subtitle=f"atas {d.get('doc_number') or '—'}",
              value=d.get("amount") or 0, age_days=_age_days(d.get("created_at")),
              badge="draf", action="Terbitkan", action_kind="issue_penalty")
         for d in map(safe_doc, denda)],
        action_label="Terbitkan", owner="finance"))

    lewat = [r for r in tagih if r.get("overdue")]
    queues.append(_queue(
        "jatuh_tempo", "Jatuh tempo (sudah lewat)",
        "Tagihan yang sudah melewati tanggal jatuh tempo.",
        [_row(ref_type="sales_order", ref_id=r["order_id"], number=r["order_number"],
              title=r.get("customer_name", "—"),
              subtitle=f"lewat {r['days_late']} hari · sales {r.get('sales_name') or '—'}",
              value=r.get("outstanding") or 0, age_days=int(r.get("days_late") or 0),
              badge="lewat", action="Tagih", action_kind="open",
              extra={"customer_id": r.get("customer_id", ""), "order_id": r.get("order_id")}) for r in lewat],
        action_label="Tagih", owner="finance"))

    # 6 — HUTANG jatuh tempo (PB-01 lanjutan): PO ber-`payment_due_date` (turun dari termin
    # kontrak/supplier) yang belum lunas, lewat atau ≤7 hari lagi — lencana merah bila lewat.
    today = datetime.now(timezone.utc).date()
    horizon = (today + timedelta(days=7)).isoformat()
    pos = await db.purchase_orders.find(
        _q(scope, {"payment_due_date": {"$gt": "", "$lte": horizon},
                   "status": {"$nin": ["cancelled", "closed", "draft", "rejected"]},
                   "po_type": {"$ne": "blanket"},
                   "payment_status": {"$ne": "paid"}}),
        {"_id": 0, "id": 1, "po_number": 1, "supplier_name": 1, "payment_due_date": 1,
         "grand_total": 1, "total_amount": 1, "amount_paid": 1, "outstanding": 1,
         "payment_term_code": 1, "parent_po_number": 1, "status": 1}
    ).sort("payment_due_date", 1).to_list(200)
    hutang_rows = []
    for p in pos:
        base = float(p.get("grand_total") or p.get("total_amount") or 0)
        sisa = float(p.get("outstanding") if p.get("outstanding") is not None
                     else base - float(p.get("amount_paid") or 0))
        if sisa <= 0.01:
            continue
        due = datetime.fromisoformat(p["payment_due_date"]).date()
        late = (today - due).days
        hutang_rows.append(_row(
            ref_type="purchase_order", ref_id=p["id"], number=p.get("po_number", "—"),
            title=p.get("supplier_name", "—"),
            subtitle=(f"lewat {late} hari" if late > 0 else ("jatuh tempo hari ini" if late == 0
                      else f"{-late} hari lagi")) + f" · {p.get('payment_term_code') or 'tanpa termin'}"
                     + (f" · kontrak {p['parent_po_number']}" if p.get("parent_po_number") else ""),
            value=sisa, age_days=max(0, late),
            badge="lewat" if late > 0 else "segera",
            action="Bayar", action_kind="open",
            extra={"payment_due_date": p["payment_due_date"], "overdue": late > 0}))
    queues.append(_queue(
        "hutang_jatuh_tempo", "Hutang supplier jatuh tempo",
        "PO belum lunas yang sudah lewat / ≤7 hari menuju jatuh tempo bayar (termin kontrak/supplier).",
        hutang_rows, action_label="Bayar", owner="finance"))

    # 7 — KEB-PDPT: uang muka pesanan yang BELUM dikirim. Kebijakan: kas ini kewajiban
    # (2-1400) sampai barang keluar. Pesanan historis yang pendapatannya sudah diakui
    # sebelum kebijakan berlaku ditandai "diakui (historis)" — putuskan per kasus.
    from services import gl_service as _gl
    belum_kirim = await db.sales_orders.find(
        _q(scope, {"status": {"$nin": list(_gl.FULLY_SHIPPED_STATUSES | set(_gl.DEAD_STATUSES))},
                   "paid_total": {"$gt": 0}}),
        {"_id": 0, "id": 1, "number": 1, "customer_name": 1, "paid_total": 1, "payments": 1,
         "grand_total": 1, "total_amount": 1, "status": 1, "created_at": 1}
    ).sort("created_at", 1).to_list(300)
    diakui_ids = {j["source_id"] async for j in db.journal_entries.find(
        {"source_type": "sales_order", "status": {"$ne": "void"},
         "source_id": {"$in": [o["id"] for o in belum_kirim]}}, {"_id": 0, "source_id": 1})}
    um_rows = []
    for o in belum_kirim:
        diakui = o["id"] in diakui_ids   # legacy: jurnal per pesanan lahir sebelum kirim
        tertahan = await _gl.order_advance_unrecognized(o)
        if not diakui and tertahan <= 0.01:
            continue   # uang muka sudah seluruhnya direklas (pro-rata) → bukan kewajiban lagi
        um_rows.append(_row(
            ref_type="sales_order", ref_id=o["id"], number=o.get("number", "—"),
            title=o.get("customer_name", "—"),
            subtitle=(("PENDAPATAN SUDAH DIAKUI sebelum kirim (historis) · "
                       if diakui else "tertahan di 2-1400 Uang Muka Pelanggan · ")
                      + f"status {o.get('status', '')}"),
            value=(o.get("paid_total") or 0) if diakui else tertahan,
            age_days=_age_days(o.get("created_at")),
            badge="diakui (historis)" if diakui else "kewajiban",
            action="Buka", action_kind="open",
            extra={"revenue_recognized": diakui,
                   "advance_total": _gl.order_advance_total(o), "advance_unrecognized": tertahan}))
    queues.append(_queue(
        "uang_muka_belum_kirim", "Uang muka pesanan belum dikirim",
        "Kas sudah masuk, barang belum keluar: kewajiban sampai dikirim. Lencana merah = "
        "pendapatan historis yang diakui sebelum kebijakan baru.",
        um_rows, action_label="Buka", owner="finance"))

    return {"desk": "finance", "desk_label": "Meja Finance",
            "generated_at": now_iso(), "entity_ids": entity_ids,
            "queues": queues,
            "totals": {"open_items": sum(q["count"] for q in queues),
                       "ap_overdue": sum(1 for r in hutang_rows if r.get("overdue")),
                       "advance_liability": round(sum(r["value"] for r in um_rows
                                                      if not r.get("revenue_recognized")), 2),
                       "advance_recognized_legacy": sum(1 for r in um_rows
                                                        if r.get("revenue_recognized"))},
            "not_my_desk": ["Membuat / mengonfirmasi pesanan",
                            "Keputusan pemenuhan (ambil dari PT lain · reorder)",
                            "Sisi hutang lainnya: tagihan supplier · kontrabon · landed cost"]}


# ═══════════════════════════════════════════════════════════════════════════
# MEJA MD (Merchandiser) — Sesi #087
# ═══════════════════════════════════════════════════════════════════════════
def _ent_q(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Filter entitas dari scope pesanan (kunci `entity_id` sama di semua koleksi)."""
    return {"entity_id": scope["entity_id"]} if scope.get("entity_id") is not None else {}


async def md_desk(actor: Dict[str, Any], scope: Dict[str, Any],
                  entity_ids: List[str]) -> Dict[str, Any]:
    eq = _ent_q(scope)
    queues: List[Dict[str, Any]] = []

    # 1 — permintaan desain menunggu keputusan / penugasan MD
    reqs = await db.design_requests.find(
        {**eq, "status": {"$in": ["submitted", "approved", "in_progress", "delivered"]}},
        {"_id": 0}).sort("requested_at", 1).to_list(200)
    label_st = {"submitted": "perlu disetujui", "approved": "belum ditugaskan",
                "in_progress": "dikerjakan desainer", "delivered": "perlu diputuskan"}
    queues.append(_queue(
        "desain", "Permintaan desain",
        "Setujui, tugaskan ke desainer, lalu putuskan karya yang diserahkan.",
        [_row(ref_type="design_request", ref_id=r["id"], number=r.get("number", ""),
              title=r.get("customer_name") or r.get("so_number")
                    or f"Internal · {r.get('target_type') or r.get('design_type') or 'desain'}",
              subtitle=(r.get("brief") or "")[:80], value=0,
              age_days=_age_days(r.get("requested_at") or r.get("created_at")),
              badge=label_st.get(r.get("status"), r.get("status", "")),
              action="Buka", action_kind="open",
              extra={"revision_count": int(r.get("revision_count") or 0)}) for r in reqs],
        action_label="Buka", owner="md", value_kind="count", value_label="Permintaan"))

    # 2 — sample / labdip menunggu penilaian atau keputusan
    samples = await db.md_samples.find(
        {**eq, "status": {"$in": ["in_progress", "sent", "assessed"]}}, {"_id": 0}).to_list(200)
    lbl = {"in_progress": "putaran berjalan", "sent": "dikirim ke pelanggan", "assessed": "perlu diputuskan"}
    queues.append(_queue(
        "sample", "Sample & labdip",
        "Putaran sample yang menunggu penilaian pelanggan atau keputusan ACC/tolak.",
        [_row(ref_type="md_sample", ref_id=s["id"], number=s.get("number", ""),
              title=s.get("title") or s.get("design_title") or s.get("spec_number") or "—",
              subtitle=f"{len(s.get('rounds') or [])} putaran · target {s.get('target_date') or '-'}",
              value=float(s.get("cost_total") or 0),
              age_days=_age_days(s.get("created_at")), badge=lbl.get(s.get("status"), s.get("status", "")),
              action="Buka", action_kind="open",
              extra={"revision_count": _sample_revision_count(s)}) for s in samples],
        action_label="Buka", owner="md"))

    # 3 — pengajuan pembelian bahan (PR) yang belum diajukan / masih menunggu
    prs = await db.purchase_requisitions.find(
        {**eq, "status": {"$in": ["draft", "pending_approval"]}}, {"_id": 0}).to_list(200)
    queues.append(_queue(
        "pr", "Permintaan pembelian bahan",
        "PR draf perlu diajukan; PR menunggu persetujuan perlu dikejar.",
        [_row(ref_type="purchase_requisition", ref_id=p["id"], number=p.get("number") or p.get("pr_number", ""),
              title=p.get("purpose") or p.get("notes") or _pr_items_title(p),
              subtitle=_pr_subtitle(p), value=float(p.get("total") or p.get("estimated_total") or _pr_total(p)),
              age_days=_age_days(p.get("created_at")),
              badge="draf" if p.get("status") == "draft" else "menunggu persetujuan",
              action="Buka", action_kind="open") for p in prs],
        action_label="Buka", owner="md"))

    # 4 — SPK inspeksi dengan tahanan warna/handfeel (butuh acuan MD)
    ins = await db.inspections.find(
        {**eq, "status": {"$in": ["draft", "in_progress"]}, "baseline_sample_id": {"$in": [None, ""]}},
        {"_id": 0}).to_list(100)
    queues.append(_queue(
        "acuan", "SPK inspeksi tanpa acuan sample",
        "Inspeksi berjalan tanpa sample ACC — warna & handfeel hanya jadi pengamatan. Tetapkan acuannya.",
        [_row(ref_type="inspection", ref_id=i["id"], number=i.get("number", ""),
              title=i.get("supplier_name") or i.get("customer_name") or i.get("ref_doc_number") or "—",
              subtitle=_ins_kind_label(i), value=0, age_days=_age_days(i.get("spk_date") or i.get("created_at")),
              badge=i.get("status", ""), action="Buka", action_kind="open") for i in ins],
        action_label="Buka", owner="md", value_kind="count", value_label="SPK"))

    return {"desk": "md", "queues": queues,
            "not_my_desk": ["Konfirmasi pesanan & keputusan pemenuhan (Admin Sales)",
                            "Uang masuk, faktur pajak & pembayaran supplier (Finance)",
                            "Operasi gudang & pengiriman (Admin Gudang)"]}


# ═══════════════════════════════════════════════════════════════════════════
# MEJA ADMIN GUDANG — Sesi #087 (termasuk jembatan Gudang → Logistik)
# ═══════════════════════════════════════════════════════════════════════════
def _sample_revision_count(s: Dict[str, Any]) -> int:
    """Revisi ke-N sample R&D = round tertinggi (per supplier×jenis) dikurangi 1."""
    top = max((int(r.get("round_no") or 1) for r in s.get("rounds") or []), default=0)
    return max(0, top - 1)


def _ins_kind_label(i: Dict[str, Any]) -> str:
    from services.inspection_service import KIND_LABEL
    kind = i.get("kind", "")
    ref = i.get("ref_doc_number") or i.get("po_number") or i.get("so_number") or ""
    return " · ".join(x for x in [KIND_LABEL.get(kind, kind), ref, i.get("product_name") or ""] if x)


def _pr_items_title(p: Dict[str, Any]) -> str:
    items = p.get("items") or []
    if not items:
        return "PR tanpa baris"
    head = items[0]
    lead = f"{head.get('product_name') or head.get('description') or head.get('sku') or 'bahan'}"
    return lead if len(items) == 1 else f"{lead} +{len(items) - 1} lainnya"


def _pr_total(p: Dict[str, Any]) -> float:
    return round(sum(float(i.get("subtotal") or (float(i.get("quantity") or 0) * float(i.get("est_price") or 0)))
                     for i in p.get("items") or []), 2)


def _pr_subtitle(p: Dict[str, Any]) -> str:
    items = p.get("items") or []
    qty = sum(float(i.get("quantity") or 0) for i in items)
    unit = (items[0].get("unit") if items else "") or ""
    parts = [f"{qty:g} {unit}".strip(), p.get("warehouse_name") or "", p.get("supplier_name") or "",
             f"butuh {str(p.get('needed_by'))[:10]}" if p.get("needed_by") else "",
             p.get("requested_by") or ""]
    return " · ".join(x for x in parts if x)


def _delivery_subtitle(d: Dict[str, Any]) -> str:
    mode = {"own_fleet": "armada sendiri", "courier": "ekspedisi", "expedition": "ekspedisi",
            "pickup": "diambil", "self_pickup": "diambil pelanggan"}.get(d.get("mode"), d.get("mode") or "")
    who = d.get("driver_name") or d.get("courier_name") or ""
    parts = [", ".join(d.get("shipment_nos") or []), mode, who, d.get("vehicle_plate") or "",
             f"ETA {str(d.get('eta'))[:10]}" if d.get("eta") else "",
             f"gagal: {d.get('fail_reason')}" if d.get("fail_reason") else ""]
    return " · ".join(x for x in parts if x)[:110]


def _po_receive_subtitle(p: Dict[str, Any]) -> str:
    """'diterima 200/400 yard · 2 baris · ETA 03 Sep' — cukup untuk memutuskan tanpa membuka PO."""
    items = p.get("items") or []
    ordered = sum(float(i.get("quantity") or 0) for i in items)
    received = sum(float(i.get("received_qty") or 0) for i in items)
    unit = (items[0].get("unit") if items else "") or ""
    eta = (p.get("expected_delivery_date") or "")[:10]
    parts = [f"diterima {received:g}/{ordered:g} {unit}".strip(), f"{len(items)} baris"]
    if eta:
        parts.append(f"ETA {eta}")
    return " · ".join(parts)


async def warehouse_admin_desk(actor: Dict[str, Any], scope: Dict[str, Any],
                               entity_ids: List[str]) -> Dict[str, Any]:
    eq = _ent_q(scope)
    queues: List[Dict[str, Any]] = []

    # 1 — SJ sudah dispatch gudang tetapi BELUM diangkut logistik (jembatan WMS→Logistik)
    sj = await db.shipments.find(
        {**eq, "status": "dispatched", "$or": [{"logistics_id": {"$exists": False}}, {"logistics_id": {"$in": [None, ""]}}]},
        {"_id": 0}).sort("created_at", 1).to_list(200)
    queues.append(_queue(
        "sj_belum_diangkut", "Surat Jalan belum diangkut logistik",
        "Barang sudah keluar gudang tetapi belum ada pengiriman — buat pengiriman (armada/ekspedisi).",
        [_row(ref_type="shipment", ref_id=s["id"], number=s.get("shipment_no", ""),
              title=s.get("customer_name") or s.get("order_number") or "—",
              subtitle=f"{s.get('order_number', '')} · {s.get('product_name', '')}"[:80],
              value=float(s.get("quantity") or 0), age_days=_age_days(s.get("created_at") or s.get("dispatched_at")),
              badge="dispatched", action="Buat pengiriman", action_kind="create_delivery") for s in sj],
        action_label="Buat pengiriman", owner="warehouse_admin", value_kind="qty", value_label="Qty"))

    # 2 — tugas outbound belum tuntas
    tasks = await db.wms_tasks.find(
        {**eq, "flow_type": "outbound", "status": {"$in": ["pending", "created", "picking", "packing", "qc_pending"]}},
        {"_id": 0}).to_list(300)
    queues.append(_queue(
        "outbound", "Tugas outbound berjalan",
        "Picking/packing yang belum dispatch — pesanan pelanggan menunggu.",
        [_row(ref_type="wms_task", ref_id=t["id"], number=t.get("order_number") or t.get("id", ""),
              title=t.get("product_name") or t.get("customer_name") or "—",
              subtitle=" · ".join(x for x in [t.get("warehouse_name", ""), t.get("customer_name", ""),
                                              f"diambil {float(t.get('picked_qty') or 0):g}/{float(t.get('quantity') or 0):g} {t.get('unit') or ''}".strip()] if x),
              value=float(t.get("quantity") or 0),
              age_days=_age_days(t.get("created_at")), badge=t.get("status", ""),
              action="Buka WMS", action_kind="open",
              extra={"order_id": t.get("order_id"), "unit": t.get("unit") or "yard"}) for t in tasks],
        action_label="Buka WMS", owner="warehouse_admin", value_kind="qty", value_label="Qty"))

    # 3 — PO menunggu penerimaan barang
    pos = await db.purchase_orders.find(
        {**eq, "status": {"$in": ["pending", "receiving"]}}, {"_id": 0}).to_list(200)
    queues.append(_queue(
        "inbound", "PO menunggu penerimaan",
        "Barang supplier yang belum/baru sebagian diterima — siapkan inbound & inspeksi.",
        [_row(ref_type="purchase_order", ref_id=p["id"], number=p.get("po_number", ""),
              title=p.get("supplier_name", "—"), subtitle=_po_receive_subtitle(p),
              value=float(p.get("grand_total") or p.get("total") or 0),
              age_days=_age_days(p.get("created_at")),
              badge="Menunggu barang" if p.get("status") == "pending" else "Penerimaan sebagian",
              action="Terima barang", action_kind="open",
              extra={"expected_delivery_date": p.get("expected_delivery_date", "")}) for p in pos],
        action_label="Terima barang", owner="warehouse_admin"))

    # 4 — SPK inspeksi belum ditugaskan
    ins = await db.inspections.find(
        {**eq, "status": "draft"}, {"_id": 0}).to_list(100)
    queues.append(_queue(
        "spk", "SPK inspeksi belum ditugaskan",
        "Tugaskan petugas inspect supaya barang tidak tertahan di karantina.",
        [_row(ref_type="inspection", ref_id=i["id"], number=i.get("number", ""),
              title=i.get("supplier_name") or i.get("customer_name") or i.get("ref_doc_number") or "—",
              subtitle=_ins_kind_label(i), value=0, age_days=_age_days(i.get("spk_date") or i.get("created_at")),
              badge="draf", action="Tugaskan", action_kind="open") for i in ins],
        action_label="Tugaskan", owner="warehouse_admin", value_kind="count", value_label="SPK"))

    # 5 — opname & transfer menunggu persetujuan
    cc = await db.cycle_count_sessions.find({**eq, "status": "submitted"}, {"_id": 0}).to_list(100)
    tr = await db.warehouse_transfers.find({**eq, "status": "waiting_approval"}, {"_id": 0}).to_list(100)
    rows = [_row(ref_type="cycle_count", ref_id=c["id"], number=c.get("number", ""), title=c.get("name") or c.get("warehouse_name", "—"),
                 subtitle=f"{len(c.get('items') or [])} item dihitung · {len(c.get('discrepancies') or [])} selisih · menunggu ACC",
                 value=0, age_days=_age_days(c.get("created_at")),
                 badge="opname", action="Setujui", action_kind="open") for c in cc]
    rows += [_row(ref_type="warehouse_transfer", ref_id=t["id"], number=t.get("code", ""),
                  title=f"{t.get('source_warehouse_name', '')} → {t.get('dest_warehouse_name', '')}",
                  subtitle=f"{len(t.get('items') or [])} baris", value=0, age_days=_age_days(t.get("created_at")),
                  badge="transfer", action="Setujui", action_kind="open") for t in tr]
    queues.append(_queue(
        "persetujuan_gudang", "Opname & transfer menunggu persetujuan",
        "Selisih opname dan transfer antar gudang yang menunggu keputusan Anda.",
        rows, action_label="Setujui", owner="warehouse_admin", value_kind="count", value_label="Dokumen"))

    # 6 — pengiriman gagal / terkirim belum ditutup
    lg = await db.logistics_deliveries.find(
        {**eq, "status": {"$in": ["failed", "delivered"]}}, {"_id": 0}).to_list(200)
    queues.append(_queue(
        "logistik", "Pengiriman gagal / belum ditutup",
        "Jadwalkan ulang yang gagal; tutup (Selesaikan) yang sudah terkirim.",
        [_row(ref_type="logistics_delivery", ref_id=d["id"], number=d.get("number", ""),
              title=d.get("customer_name") or d.get("order_number") or "—",
              subtitle=_delivery_subtitle(d), value=0,
              age_days=_age_days(d.get("created_at")), badge="gagal" if d.get("status") == "failed" else "terkirim",
              action="Buka", action_kind="open") for d in lg],
        action_label="Buka", owner="warehouse_admin", value_kind="count", value_label="Pengiriman"))

    return {"desk": "warehouse_admin", "queues": queues,
            "not_my_desk": ["Konfirmasi pesanan & harga (Admin Sales)",
                            "Pembayaran supplier & uang masuk (Finance)",
                            "Keputusan desain & sample (MD)"]}
