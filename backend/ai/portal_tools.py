"""Alat agen portal pembeli (`scope="portal"`): memanggil endpoint `/api/portal/...` in-process dengan TOKEN PORTAL
pembeli itu, sehingga data otomatis hanya miliknya. Tidak ada token staf / `ai_agent`, tidak ada `api_get`.

Lapisan kedua (pertahanan berlapis): hasil disaring lagi ke `deal_id`/unit milik pembeli (dari `/portal/overview`),
karena beberapa endpoint lama memfilter `customer_id` yang bisa kosong untuk pembeli pemegang reservasi (lead).
Usulan (`buat_komplain`, `ajukan_klaim_garansi`) hanya membuat `ai_actions` pending; pembeli sendiri yang mengirim
lewat kartu konfirmasi (`actions.confirm_by_buyer`). `serahkan_ke_cs` langsung membuat tiket (permintaan pembeli).
"""
import reference as ref
from ai import actions, portal_handoff
from ai.tools import internal_api as api
from ai.tools.read_tools import COMPLAINT_TEXT, flat, wrap_fields
from ai.tools.registry import Tool, ToolContext, ToolError, register
from db import db

S = {"type": "string"}
NOT_MINE = "Unit itu tidak terdaftar atas nama Anda. Pilih salah satu unit dari ringkasan_saya."


def _obj(props: dict, required: list = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


def _complaint_categories() -> list:
    return [v for v in ref.values("complaint_category") if v != "internal"]


async def _pget(ctx: ToolContext, path: str):
    st, data = await api.call(ctx.token, "GET", path)
    if st >= 400:
        raise ToolError(f"Gagal membaca data ({st}): {api.error_detail(data)}")
    return data


def _rows(d) -> list:
    rows = d.get("data") if isinstance(d, dict) else d
    return rows if isinstance(rows, list) else []


async def _own(ctx: ToolContext) -> list:
    """Unit/transaksi milik pembeli ini menurut `/portal/overview` (dibatasi token pembeli)."""
    return _rows(await _pget(ctx, "/portal/overview"))


async def _scope(ctx: ToolContext, inp: dict):
    """-> (daftar milik pembeli, set deal_id milik pembeli, deal_id yang diminta atau None)."""
    own = await _own(ctx)
    ids = {r.get("deal_id") for r in own if r.get("deal_id")}
    want = inp.get("deal_id") or None
    if want and want not in ids:
        raise ToolError(NOT_MINE)
    return own, ids, want


def _by_deal(rows: list, want) -> list:
    return [r for r in rows if not want or r.get("deal_id") == want]


# ------------------------------------------------------------------ alat baca
async def ringkasan_saya(ctx, inp):
    own, _ids, want = await _scope(ctx, inp)
    keep = ("deal_id", "status", "price", "unit_code", "unit_type", "project_name", "construction_progress",
            "construction_status_label", "payment", "financing", "documents_count", "open_complaints")
    rows = [{k: r.get(k) for k in keep} for r in _by_deal(own, want)]
    return {"unit": rows, "jumlah_unit": len(rows),
            "catatan": "Bila pembeli punya lebih dari satu unit, tanyakan unit yang dimaksud.",
            "summary": f"Ringkasan {len(rows)} unit"}


async def kpr_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    rows = [r for r in _by_deal(_rows(await _pget(ctx, "/portal/kpr")), want) if r.get("deal_id") in ids]
    return {"kpr": rows, "catatan": "Jadwal angsuran adalah perkiraan, bukan tagihan bank.",
            "summary": f"Data KPR {len(rows)} unit" if rows else "Belum ada data KPR"}


async def tagihan_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    out = []
    for r in _by_deal(_rows(await _pget(ctx, "/portal/payments")), want):
        if r.get("deal_id") not in ids:
            continue
        out.append({"deal_id": r.get("deal_id"), "unit_code": r.get("unit_code"), "status_transaksi": r.get("deal_status"),
                    "ringkasan": r.get("summary"), "jadwal": [flat(i) for i in (r.get("schedule") or [])][:36],
                    "kuitansi_terakhir": [flat(x) for x in (r.get("receipts") or [])][:5],
                    "booking_fee": r.get("booking_fee"), "keterlambatan": r.get("late")})
    subs = [flat(s) for s in _rows(await _pget(ctx, "/portal/payments/submissions"))
            if s.get("deal_id") in ids and (not want or s.get("deal_id") == want)]
    return {"tagihan": out, "bukti_transfer": subs[:20],
            "catatan": "Bukti transfer berstatus menunggu belum mengurangi tagihan sampai diverifikasi finance.",
            "summary": f"Tagihan {len(out)} unit"}


async def kuitansi_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    rows = [flat(r) for r in _by_deal(_rows(await _pget(ctx, "/portal/receipts")), want) if r.get("deal_id") in ids]
    return {"kuitansi": rows[:30], "jumlah": len(rows), "total_rp": sum(int(r.get("amount") or 0) for r in rows),
            "summary": f"{len(rows)} kuitansi"}


async def progres_rumah_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    out = []
    for r in _by_deal(_rows(await _pget(ctx, "/portal/progress")), want):
        if r.get("deal_id") not in ids:
            continue
        out.append({"deal_id": r.get("deal_id"), "unit_code": r.get("unit_code"),
                    "progres_persen": r.get("construction_progress"), "status": r.get("construction_status_label"),
                    "jadwal_rumah": r.get("build"),
                    "pekerjaan_kawasan": [{k: p.get(k) for k in ("name", "progress", "status")} for p in (r.get("phases") or [])][:20],
                    "jumlah_foto": len(r.get("photos") or []), "jumlah_perbaikan": len(r.get("repairs") or [])})
    return {"progres": out, "catatan": "pekerjaan_kawasan = jalan/drainase proyek, bukan rumah pembeli.",
            "summary": f"Progres {len(out)} rumah"}


async def dokumen_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    rows = [flat(r) for r in _by_deal(_rows(await _pget(ctx, "/portal/documents")), want) if r.get("deal_id") in ids]
    return {"dokumen": rows[:30], "jumlah": len(rows), "catatan": "Dokumen bisa diunduh dari menu Dokumen di portal.",
            "summary": f"{len(rows)} dokumen"}


def _complaint_row(r: dict) -> dict:
    row = wrap_fields(flat(r), COMPLAINT_TEXT)
    row["kategori"] = ref.label_of("complaint_category", r.get("category"))
    row["status_label"] = ref.label_of("complaint_status", r.get("status"))
    if r.get("kind") == "pertanyaan_chat":
        row["jenis"] = "Pertanyaan ke CS (dari chat)"
    row["balasan_terakhir"] = [{"pesan": x.get("message"), "waktu": x.get("at")} for x in (r.get("responses") or [])][-3:]
    return row


async def komplain_saya(ctx, inp):
    _own_, ids, want = await _scope(ctx, inp)
    cid = (ctx.user or {}).get("customer_id")
    rows = [r for r in _rows(await _pget(ctx, "/portal/complaints"))
            if r.get("deal_id") in ids or (cid and r.get("customer_id") == cid)]
    rows = [r for r in rows if (not want or r.get("deal_id") == want) and (not inp.get("status") or r.get("status") == inp["status"])]
    return {"komplain": [_complaint_row(r) for r in rows][:20], "jumlah": len(rows), "summary": f"{len(rows)} komplain"}


async def garansi_saya(ctx, inp):
    own, _ids, want = await _scope(ctx, inp)
    code = next((r.get("unit_code") for r in own if r.get("deal_id") == want), None) if want else None
    rows = [r for r in _rows(await _pget(ctx, "/portal/warranty")) if not want or (r.get("unit") or {}).get("code") == code]
    unit_ids = {(r.get("unit") or {}).get("id") for r in rows}
    cid = (ctx.user or {}).get("customer_id")
    claims = [flat(c) for c in _rows(await _pget(ctx, "/portal/warranty/claims"))
              if c.get("unit_id") in unit_ids or (not want and cid and c.get("customer_id") == cid)]
    out = [{"unit": r.get("unit"), "masa_garansi": [{k: w.get(k) for k in ("category", "expires_at", "days_left", "state_label")}
                                                     for w in (r.get("warranty") or [])],
            "belum_serah_terima": r.get("missing"), "keterangan": r.get("detail")} for r in rows]
    return {"garansi": out, "klaim": claims[:20], "summary": f"Garansi {len(out)} rumah, {len(claims)} klaim"}


async def serah_terima_saya(ctx, inp):
    own, _ids, want = await _scope(ctx, inp)
    code = next((r.get("unit_code") for r in own if r.get("deal_id") == want), None) if want else None
    rows = [flat(r) for r in _rows(await _pget(ctx, "/portal/handovers"))
            if not want or r.get("deal_id") == want or (code and r.get("unit_code") == code)]
    return {"serah_terima": rows[:10], "jumlah": len(rows),
            "catatan": "Tanggal serah terima yang belum tercatat tidak boleh diperkirakan atau dijanjikan.",
            "summary": f"{len(rows)} berita acara serah terima"}


async def site_plan(ctx, inp):
    d = await _pget(ctx, "/portal/site-plan")
    out = []
    for p in ((d.get("data") or {}).get("projects") or []):
        units = p.get("units") or []
        status = {}
        for u in units:
            if not u.get("mine"):
                status[u.get("status") or "-"] = status.get(u.get("status") or "-", 0) + 1
        out.append({"proyek": p.get("project_name"), "lokasi": p.get("location"), "unit_saya": [u for u in units if u.get("mine")],
                    "kavling_lain_per_status": status})
    return {"site_plan": out, "summary": f"Site plan {len(out)} proyek"}


async def info_umum(ctx, inp):
    d = await _pget(ctx, "/portal/reference")
    groups = d.get("data") if isinstance(d, dict) else {}
    return {"kamus": groups, "summary": "Info umum portal"}


# ------------------------------------------------------------------ usulan & serah ke CS
def _pending(a: dict, summary: str) -> dict:
    return {"action_id": a["id"], "status": "pending",
            "pesan": "Kartu konfirmasi ditampilkan; isian BELUM terkirim sampai pembeli menekan Kirim.", "summary": summary}


def _text(inp: dict, key: str, label: str, mx: int, mn: int = 1) -> str:
    v = " ".join(str(inp.get(key) or "").split()) if key != "pesan" else str(inp.get(key) or "").strip()
    if len(v) < mn or len(v) > mx:
        raise ToolError(f"{label} harus {mn}-{mx} karakter.")
    return v


async def buat_komplain(ctx, inp):
    own, _ids, deal_id = await _scope(ctx, inp)
    if not deal_id:
        raise ToolError("deal_id wajib diisi (unit yang dikomplain).")
    if inp["kategori"] not in _complaint_categories():
        raise ToolError("Kategori komplain tidak dikenal.")
    subjek, pesan = _text(inp, "subjek", "Subjek", 140, 3), _text(inp, "pesan", "Isi komplain", 2000, 5)
    unit = next((r for r in own if r.get("deal_id") == deal_id), {})
    prev = {"title": "Kirim komplain ini?", "subject": subjek,
            "changes": [f"Unit: {unit.get('unit_code') or '-'} ({unit.get('project_name') or '-'})",
                        f"Kategori: {ref.label_of('complaint_category', inp['kategori'])}", f"Subjek: {subjek}", f"Isi: {pesan}"],
            "checks": []}
    a = await actions.create_pending(ctx, tool="buat_komplain", resource="portal_complaints", permission="create",
                                     method="POST", path="/portal/complaints", preview=prev, entity_id=deal_id,
                                     json={"deal_id": deal_id, "category": inp["kategori"], "subject": subjek,
                                           "message": pesan, "priority": "medium"})
    return _pending(a, "Menyiapkan komplain untuk dikonfirmasi")


async def ajukan_klaim_garansi(ctx, inp):
    rows = _rows(await _pget(ctx, "/portal/warranty"))
    row = next((r for r in rows if (r.get("unit") or {}).get("id") == inp["unit_id"]), None)
    if not row:
        raise ToolError("Rumah ini tidak terdaftar atas nama Anda. Lihat garansi_saya untuk unit_id yang benar.")
    if inp["category"] not in ref.values("warranty_category"):
        raise ToolError("Bagian garansi tidak dikenal.")
    title = _text(inp, "title", "Judul klaim", 140, 4)
    desc = str(inp.get("description") or "").strip()[:2000] or None
    w = next((x for x in (row.get("warranty") or []) if x.get("category") == inp["category"]), None)
    checks = [{"ok": bool(w and w.get("state") != "habis"),
               "label": (f"Masih bergaransi sampai {w.get('expires_at')}" if w and w.get("state") != "habis" else
                         "Masa garansi bagian ini sudah habis atau belum tercatat; klaim tetap dicatat dan bisa ditolak")}]
    prev = {"title": "Ajukan klaim garansi ini?", "subject": title,
            "changes": [f"Unit: {(row.get('unit') or {}).get('code') or '-'}",
                        f"Bagian: {ref.label_of('warranty_category', inp['category'])}", f"Judul: {title}"]
            + ([f"Keterangan: {desc}"] if desc else []), "checks": checks}
    a = await actions.create_pending(ctx, tool="ajukan_klaim_garansi", resource="portal_warranty_claims", permission="create",
                                     method="POST", path="/portal/warranty/claims", preview=prev, entity_id=inp["unit_id"],
                                     json={"unit_id": inp["unit_id"], "category": inp["category"], "title": title,
                                           "description": desc})
    return _pending(a, "Menyiapkan klaim garansi untuk dikonfirmasi")


async def _last_question(conv_id: str) -> str:
    async for m in db.ai_messages.find({"conversation_id": conv_id, "role": "user"}, {"_id": 0, "content": 1}).sort("seq", -1):
        c = m.get("content")
        blocks = c if isinstance(c, list) else [{"type": "text", "text": c or ""}]
        text = " ".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        if text:
            return text
    return ""


async def serahkan_ke_cs(ctx, inp):
    alasan = _text(inp, "alasan", "Alasan", 200, 3)
    deal_id = inp.get("deal_id") or None
    if deal_id:
        await _scope(ctx, {"deal_id": deal_id})
    q = await _last_question(ctx.conversation_id) if ctx.conversation_id else ""
    t = await portal_handoff.create_ticket(ctx, reason=alasan, question=q or alasan, summary=inp["ringkasan"],
                                           sensitive=False, deal_id=deal_id)
    return {"tiket": t, "pesan": f"Tiket {t['number']} dibuat; CS menghubungi paling lambat {portal_handoff.due_text(t['due_at'])}.",
            "summary": f"Diteruskan ke CS (tiket {t['number']})"}


# ------------------------------------------------------------------ registrasi
def register_all():
    R = register
    d = {"deal_id": S}
    P = "portal"
    R(Tool("ringkasan_saya", "Ringkasan semua unit milik pembeli: unit, proyek, status, harga, tagihan, KPR, progres, jumlah "
           "dokumen & komplain terbuka. Pakai dulu untuk mengetahui deal_id tiap unit.", _obj(d), "read", P, ringkasan_saya,
           "Membaca ringkasan unit"))
    R(Tool("kpr_saya", "KPR pembeli: bank, produk, plafon, tenor, bunga, perkiraan jadwal angsuran.", _obj(d), "read", P,
           kpr_saya, "Membaca data KPR"))
    R(Tool("tagihan_saya", "Tagihan pembeli: ringkasan, jadwal pembayaran, keterlambatan, dan status bukti transfer.",
           _obj(d), "read", P, tagihan_saya, "Membaca tagihan"))
    R(Tool("kuitansi_saya", "Kuitansi pembayaran yang sudah diterima.", _obj(d), "read", P, kuitansi_saya, "Membaca kuitansi"))
    R(Tool("progres_rumah_saya", "Progres pembangunan rumah pembeli dan pekerjaan kawasan.", _obj(d), "read", P,
           progres_rumah_saya, "Membaca progres rumah"))
    R(Tool("dokumen_saya", "Daftar dokumen transaksi pembeli (SPR, PPJB, dsb.).", _obj(d), "read", P, dokumen_saya,
           "Membaca dokumen"))
    R(Tool("komplain_saya", "Komplain dan pertanyaan ke CS milik pembeli beserta statusnya.",
           _obj({**d, "status": {"type": "string", "enum": list(ref.values("complaint_status"))}}), "read", P,
           komplain_saya, "Membaca komplain"))
    R(Tool("garansi_saya", "Masa garansi per bagian rumah dan klaim garansi pembeli (berisi unit_id untuk klaim).",
           _obj(d), "read", P, garansi_saya, "Membaca garansi"))
    R(Tool("serah_terima_saya", "Berita acara serah terima rumah pembeli.", _obj(d), "read", P, serah_terima_saya,
           "Membaca serah terima"))
    R(Tool("site_plan", "Site plan proyek: kavling milik pembeli dan status kavling lain (tanpa data pembeli lain).",
           _obj({}), "read", P, site_plan, "Membaca site plan"))
    R(Tool("info_umum", "Info umum portal: daftar kategori komplain, status, bagian garansi, dan labelnya.",
           _obj({}), "read", P, info_umum, "Membaca info umum"))
    R(Tool("buat_komplain", "Siapkan komplain baru untuk satu unit pembeli. TIDAK langsung terkirim: pembeli menekan Kirim "
           "pada kartu konfirmasi. deal_id wajib (dari ringkasan_saya).",
           _obj({"deal_id": S, "kategori": {"type": "string", "enum": _complaint_categories()}, "subjek": S, "pesan": S},
                ["deal_id", "kategori", "subjek", "pesan"]), "propose", P, buat_komplain, "Menyiapkan komplain"))
    R(Tool("ajukan_klaim_garansi", "Siapkan klaim garansi untuk satu rumah pembeli (unit_id dari garansi_saya). TIDAK langsung "
           "terkirim: pembeli menekan Kirim pada kartu konfirmasi.",
           _obj({"unit_id": S, "category": {"type": "string", "enum": list(ref.values("warranty_category"))}, "title": S,
                 "description": S}, ["unit_id", "category", "title"]), "propose", P, ajukan_klaim_garansi,
           "Menyiapkan klaim garansi"))
    R(Tool("serahkan_ke_cs", "Teruskan ke CS manusia sebagai tiket (tenggat 1x24 jam): bila pembeli minta staf, bila data tidak "
           "tersedia dari alat, atau pertanyaan di luar kewenangan AI. ringkasan = ringkasan percakapan untuk CS.",
           _obj({"alasan": S, "ringkasan": S, "deal_id": S}, ["alasan", "ringkasan"]), "handoff", P, serahkan_ke_cs,
           "Meneruskan ke CS"))
