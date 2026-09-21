"""
pdf_service.py — Orkestrasi render dokumen: template config + branding entitas +
resolver context + (opsional) blok e-sign → HTML → PDF.
"""
from __future__ import annotations
import base64
import io
from db import db
from services.pdf_engine import render_html, render_pdf
from services.pdf_resolvers import DOC_REGISTRY

# ─── Default template config per dokumen ─────────────────────────────────────
# Sesi #086 — konfigurasi BERLAPIS (pola sipro `doc_layout`): bawaan kode → `__default__`
# (gaya seluruh dokumen) → override per jenis dokumen yang hanya menyimpan PERBEDAAN.
DEFAULT_CODE = "__default__"
DEFAULT_TEMPLATE_CFG = {
    "paper_size": "A4", "orientation": "portrait",
    "margin_top": 16, "margin_right": 14, "margin_bottom": 16, "margin_left": 14,
    "font_family": "'DejaVu Sans'", "font_size": 10,
    "color_primary": "#0058CC", "color_accent": "#1a1a1a",
    "show_logo": True, "show_terbilang": True,
    "watermark_text": "", "watermark_opacity": 6,          # 1..40 (%)
    "footer_text": "", "show_page_numbers": True,
    "title_override": "",
    "custom_fields": [],       # [{label, value}]
    "signature_slots": [],     # override doc.signatures bila diisi [{label, role, name, show_stamp}]
    "hidden_fields": [],       # label meta yang disembunyikan
    # Kop: dirakit sistem | gambar kop desainer | kosong (kertas berkop cetakan)
    "header_mode": "system",   # system | image | none
    "footer_mode": "text",     # text | image | none
    # Naskah pembuka/penutup dengan placeholder {{token}} (divalidasi saat simpan)
    "intro_text": "", "closing_note": "",
    "show_place_date": False, "place": "",
    "show_materai": False, "materai_note": "Bermeterai cukup",
    "show_generated_note": False,
    # Bagian dokumen yang boleh dimatikan (angka tetap milik mesin — hanya tampil/sembunyi)
    "sections": {"parties": True, "meta": True, "items": True, "totals": True,
                 "notes": True, "signatures": True, "refs": True},
    # Gaya tabel rincian
    "table": {"grid": "full", "show_header": True, "header_fill": True, "zebra": False,
              "total_highlight": True, "font_size": 9, "grid_color": "#bbbbbb"},
}
NESTED_KEYS = ("sections", "table")

# Placeholder yang SAH di naskah — diturunkan dari konteks dokumen yang benar-benar terisi.
PLACEHOLDERS = {
    "nomor": "Nomor dokumen", "tanggal": "Tanggal dokumen", "judul": "Judul dokumen",
    "status": "Status dokumen", "perusahaan": "Nama perusahaan penerbit",
    "alamat_perusahaan": "Alamat perusahaan", "npwp_perusahaan": "NPWP perusahaan",
    "pihak": "Nama pihak tujuan (pelanggan/supplier)", "alamat_pihak": "Alamat pihak tujuan",
    "grand_total": "Nilai total dokumen", "terbilang": "Total dalam huruf",
    "jumlah_baris": "Jumlah baris rincian", "hari_ini": "Tanggal cetak (WIB)",
}
_TOKEN_RE = None


def _token_re():
    global _TOKEN_RE
    if _TOKEN_RE is None:
        import re
        _TOKEN_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")
    return _TOKEN_RE


def unknown_tokens(text: str) -> list:
    return sorted({t for t in _token_re().findall(text or "") if t not in PLACEHOLDERS})


def render_text(text: str, doc: dict, branding: dict) -> str:
    """Isi {{token}} dari konteks dokumen. Token tak dikenal dibiarkan apa adanya."""
    if not text:
        return ""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    party = doc.get("party_to") or {}
    total = ""
    for t in doc.get("totals") or []:
        if t.get("strong"):
            total = t.get("value") or ""
    vals = {
        "nomor": doc.get("number") or "", "tanggal": doc.get("date") or "",
        "judul": doc.get("title") or "", "status": doc.get("status") or "",
        "perusahaan": branding.get("company_name") or "",
        "alamat_perusahaan": branding.get("address") or "",
        "npwp_perusahaan": branding.get("npwp") or "",
        "pihak": party.get("name") or "", "alamat_pihak": party.get("address") or "",
        "grand_total": total, "terbilang": doc.get("terbilang") or "",
        "jumlah_baris": str(len(doc.get("items") or [])),
        "hari_ini": datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y"),
    }
    return _token_re().sub(lambda m: str(vals.get(m.group(1), m.group(0))), text)


def _clean_cfg(config: dict) -> dict:
    """Ambil hanya kunci yang dikenal; kelompok bersarang digabung per kunci."""
    out = {}
    for k, v in (config or {}).items():
        if k not in DEFAULT_TEMPLATE_CFG:
            continue
        if k in NESTED_KEYS and isinstance(v, dict):
            out[k] = {kk: vv for kk, vv in v.items() if kk in DEFAULT_TEMPLATE_CFG[k]}
        else:
            out[k] = v
    return out


def merge_cfg(base: dict, over: dict) -> dict:
    out = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v)
           for k, v in base.items()}
    for k, v in (over or {}).items():
        if k in NESTED_KEYS and isinstance(v, dict):
            out[k] = {**out.get(k, {}), **v}
        else:
            out[k] = v
    return out


def diff_cfg(effective_default: dict, full: dict) -> dict:
    """Simpan hanya yang BERBEDA dari bawaan efektif (pola override sipro)."""
    out = {}
    for k, v in full.items():
        base = effective_default.get(k)
        if k in NESTED_KEYS and isinstance(v, dict):
            d = {kk: vv for kk, vv in v.items() if (base or {}).get(kk) != vv}
            if d:
                out[k] = d
        elif v != base:
            out[k] = v
    return out


def qr_data_url(payload: str) -> str:
    import qrcode
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


async def _default_effective() -> dict:
    row = await db.pdf_templates.find_one({"doc_type": DEFAULT_CODE}, {"_id": 0})
    cfg = merge_cfg(DEFAULT_TEMPLATE_CFG, {})
    if row and isinstance(row.get("config"), dict):
        cfg = merge_cfg(cfg, _clean_cfg(row["config"]))
    return cfg


async def get_template_cfg(doc_type: str) -> dict:
    """Konfigurasi EFEKTIF: bawaan kode → `__default__` → override jenis dokumen."""
    cfg = await _default_effective()
    if doc_type != DEFAULT_CODE:
        row = await db.pdf_templates.find_one({"doc_type": doc_type}, {"_id": 0})
        if row and isinstance(row.get("config"), dict):
            cfg = merge_cfg(cfg, _clean_cfg(row["config"]))
    return cfg


async def template_meta(doc_type: str) -> dict:
    row = await db.pdf_templates.find_one({"doc_type": doc_type}, {"_id": 0, "config": 0}) or {}
    override = await db.pdf_templates.find_one({"doc_type": doc_type}, {"_id": 0, "config": 1}) or {}
    return {"customized": bool(row), "version": row.get("version") or 0,
            "updated_at": row.get("updated_at") or "", "updated_by": row.get("updated_by") or "",
            "override_keys": sorted((override.get("config") or {}).keys())}


async def save_template_cfg(doc_type: str, config: dict, actor: str = "") -> dict:
    """`__default__` menyimpan konfigurasi penuh; jenis dokumen hanya menyimpan PERBEDAAN
    terhadap bawaan efektif, sehingga mengganti warna di `__default__` ikut mengubah semua
    dokumen yang tidak menimpanya (pola sipro)."""
    from core_utils import now_iso
    clean = _clean_cfg(config)
    for t in ("intro_text", "closing_note"):
        bad = unknown_tokens(clean.get(t, ""))
        if bad:
            raise ValueError(f"Placeholder tidak dikenal di naskah: {', '.join('{{' + b + '}}' for b in bad)}. "
                             f"Yang sah: {', '.join('{{' + k + '}}' for k in PLACEHOLDERS)}")
    if doc_type == DEFAULT_CODE:
        stored = merge_cfg(DEFAULT_TEMPLATE_CFG, clean)
    else:
        full = merge_cfg(await _default_effective(), clean)
        stored = diff_cfg(await _default_effective(), full)
    cur = await db.pdf_templates.find_one({"doc_type": doc_type}, {"_id": 0, "version": 1}) or {}
    await db.pdf_templates.update_one(
        {"doc_type": doc_type},
        {"$set": {"doc_type": doc_type, "config": stored, "updated_by": actor,
                  "updated_at": now_iso(), "version": int(cur.get("version") or 0) + 1}},
        upsert=True,
    )
    return await get_template_cfg(doc_type)


async def reset_template_cfg(doc_type: str) -> dict:
    """Buang override-nya saja; dokumen yang sudah terbit tidak berubah."""
    await db.pdf_templates.delete_one({"doc_type": doc_type})
    return await get_template_cfg(doc_type)


async def list_templates() -> list:
    rows = {r["doc_type"]: r for r in await db.pdf_templates.find(
        {}, {"_id": 0, "doc_type": 1, "version": 1, "updated_at": 1, "updated_by": 1}).to_list(500)}
    out = [{"doc_type": DEFAULT_CODE, "label": "Bawaan seluruh dokumen (gaya & kop)",
            "module": "__default__", "customized": DEFAULT_CODE in rows,
            **{k: (rows.get(DEFAULT_CODE) or {}).get(k) for k in ("version", "updated_at", "updated_by")}}]
    for k, v in DOC_REGISTRY.items():
        r = rows.get(k) or {}
        out.append({"doc_type": k, "label": v["label"], "module": v["module"],
                    "esignable": v.get("esignable", False), "customized": k in rows,
                    "version": r.get("version"), "updated_at": r.get("updated_at"),
                    "updated_by": r.get("updated_by")})
    return out


async def get_branding(entity_id: str | None) -> dict:
    ent = await db.business_entities.find_one({"id": entity_id}, {"_id": 0}) if entity_id else None
    ent = ent or {}
    row = await db.document_branding.find_one({"entity_id": entity_id}, {"_id": 0}) if entity_id else None
    row = row or {}
    logo_src = ""
    if row.get("logo_b64"):
        logo_src = f"data:image/png;base64,{row['logo_b64']}" if not str(row["logo_b64"]).startswith("data:") else row["logo_b64"]
    elif ent.get("logo_url"):
        logo_src = ent["logo_url"]
    addr = row.get("address") or ", ".join(x for x in [ent.get("address"), ent.get("city")] if x)
    def _img(key):
        v = row.get(key) or ""
        return v if (not v or str(v).startswith("data:")) else f"data:image/png;base64,{v}"
    return {
        "entity_id": entity_id,
        "company_name": row.get("company_name") or ent.get("legal_name") or ent.get("short_name") or "Perusahaan",
        "tagline": row.get("tagline") or "",
        "address": addr or "-",
        "phone": row.get("phone") or "",
        "email": row.get("email") or ent.get("email") or "",
        "website": row.get("website") or "",
        "npwp": row.get("npwp") or ent.get("npwp") or "",
        "logo_src": logo_src,
        "header_image_src": _img("header_image_b64"),   # kop gambar buatan desainer
        "footer_image_src": _img("footer_image_b64"),
        "stamp_src": _img("stamp_b64"),                 # cap perusahaan
        "signatures": row.get("signatures") or [],   # [{label, role, name, signature_b64}]
    }


async def save_branding(entity_id: str, data: dict, actor: str = "") -> dict:
    allowed = {k: data.get(k) for k in ["company_name", "tagline", "address", "phone", "email", "website",
                                        "npwp", "logo_b64", "header_image_b64", "footer_image_b64",
                                        "stamp_b64", "signatures"] if k in data}
    await db.document_branding.update_one(
        {"entity_id": entity_id},
        {"$set": {"entity_id": entity_id, **allowed, "updated_by": actor}},
        upsert=True,
    )
    return await get_branding(entity_id)


def _apply_cfg_to_doc(doc: dict, cfg: dict, branding: dict) -> dict:
    if cfg.get("title_override"):
        doc["title"] = cfg["title_override"]
    # custom fields → tambah ke meta
    meta = list(doc.get("meta") or [])
    for cf in cfg.get("custom_fields") or []:
        if cf.get("label"):
            meta.append({"label": cf["label"], "value": cf.get("value", "")})
    # sembunyikan field tertentu
    hidden = set(cfg.get("hidden_fields") or [])
    doc["meta"] = [m for m in meta if m["label"] not in hidden]
    # override signature slots dari config, jika tidak ada pakai default doc + isi nama dari branding
    if cfg.get("signature_slots"):
        doc["signatures"] = cfg["signature_slots"]
    # tempel gambar TTD dari branding (match by role/label)
    brand_sig = {(s.get("role") or s.get("label") or "").lower(): s for s in (branding.get("signatures") or [])}
    for s in doc.get("signatures") or []:
        key = (s.get("role") or s.get("label") or "").lower()
        if key in brand_sig and brand_sig[key].get("signature_b64"):
            b = brand_sig[key]["signature_b64"]
            s["signature_src"] = b if str(b).startswith("data:") else f"data:image/png;base64,{b}"
            if not s.get("name") and brand_sig[key].get("name"):
                s["name"] = brand_sig[key]["name"]
        if s.get("show_stamp") and branding.get("stamp_src"):
            s["stamp_src"] = branding["stamp_src"]
    # Bagian yang dimatikan konfigurasi — nilai tidak diubah, hanya tidak dicetak.
    sec = {**DEFAULT_TEMPLATE_CFG["sections"], **(cfg.get("sections") or {})}
    if not sec.get("parties"):
        doc["party_to"] = None
    if not sec.get("meta"):
        doc["meta"] = []
    if not sec.get("items"):
        doc["items"] = []
    if not sec.get("totals"):
        doc["totals"] = []
    if not sec.get("notes"):
        doc["notes"] = ""
    if not sec.get("signatures"):
        doc["signatures"] = []
    doc["_hide_refs"] = not sec.get("refs")
    # Naskah pembuka/penutup + tempat-tanggal (placeholder diisi dari konteks nyata).
    doc["intro_text"] = render_text(cfg.get("intro_text") or "", doc, branding)
    doc["closing_note"] = render_text(cfg.get("closing_note") or "", doc, branding)
    if cfg.get("show_place_date"):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        hari = doc.get("date") or datetime.now(ZoneInfo("Asia/Jakarta")).strftime("%d %b %Y")
        doc["place_date"] = f"{cfg.get('place') or ''}, {hari}".strip(", ")
    return doc


async def _attach_esign(doc: dict, doc_type: str, source_id: str, public_base: str):
    """Bila ada tanda tangan elektronik final → tempel blok e-sign + QR ke dokumen."""
    sigs = await db.document_signatures.find(
        {"doc_type": doc_type, "source_id": source_id, "status": "signed"}, {"_id": 0}
    ).sort("signed_at", 1).to_list(20)
    if not sigs:
        return doc
    last = sigs[-1]
    code = last.get("verification_code")
    verify_url = f"{public_base}/verify-document/{code}"
    # FASE G-4 — blok tanda tangan harus BERNAMA: siapa, JABATAN apa, dan KAPAN.
    # Nama saja tidak cukup untuk dokumen kertas yang dipegang pihak luar.
    people = []
    for s in sigs:
        people.append({
            "name": s.get("signer_name") or "-",
            "role": s.get("signer_role") or "",
            "at": (s.get("signed_at") or "")[:19].replace("T", " "),
        })
    doc["esign"] = {
        "code": code,
        "signers": ", ".join(p["name"] for p in people),
        "people": people,
        "signed_at": (last.get("signed_at") or "")[:19].replace("T", " "),
        "hash_short": (last.get("doc_hash") or "")[:24] + "…",
        "verify_url": verify_url,
        "qr_src": qr_data_url(verify_url),
    }
    return doc


async def attach_document_refs(doc: dict, doc_type: str, source_id: str,
                               source: dict, public_base: str) -> dict:
    """FASE G-4 — tempelkan blok **Referensi Dokumen** (+ QR Jejak Dokumen).

    Dipasang di SATU tempat (bukan di 21 resolver) supaya setiap dokumen cetak —
    apa pun jenisnya — otomatis menyebut surat-surat yang berkaitan. Tanpa ini,
    penerima kertas tidak bisa menghubungkan Surat Jalan dengan pesanannya.

    Aturannya configurable lewat Pusat Pengaturan (kelompok "Dokumen, Referensi &
    Tanda Tangan"): tampil/tidak, pakai QR/tidak, dan berapa nomor yang dicetak.

    Kunci yang mengatur blok ini (dibaca lewat `doc_refs_service.pdf_options`):
    `docref.show_in_pdf` · `docref.qr_in_pdf` · `docref.pdf_max_refs`.
    """
    from services import doc_refs_service as refs

    entity_id = source.get("entity_id") or ""
    try:
        opts = await refs.pdf_options(entity_id)
    except Exception:  # noqa: BLE001 — konfigurasi belum ter-seed → pakai bawaan aman
        opts = {"show": True, "qr": True, "max": 6}
    if not opts.get("show"):
        return doc

    # doc_type PDF bisa berbagi koleksi (invoice/delivery_note/picking_list → sales_orders);
    # relasi selalu dibaca dari doc_type KANONIK koleksinya.
    reg = DOC_REGISTRY.get(doc_type) or {}
    canon = (doc_type if doc_type in refs.DOC_TYPES
             else refs.type_of_collection(reg.get("collection", "")))
    if not canon:
        return doc
    line = await refs.reference_line(canon, source_id, limit=int(opts.get("max") or 6))
    if not line.get("items"):
        return doc
    trace_url = f"{public_base}/jejak-dokumen/{canon}/{source_id}" if public_base else ""
    doc["refs_block"] = {
        "text": line["text"],
        "items": line["items"],
        "hidden": line.get("hidden", 0),
        "trace_url": trace_url,
        "qr_src": qr_data_url(trace_url) if (opts.get("qr") and trace_url) else "",
    }
    return doc


async def build_document(doc_type: str, source_id: str, entity_id: str | None,
                         cfg_override: dict | None = None, public_base: str = "") -> dict:
    """Return {source, cfg, branding, doc} — dipakai render html/pdf.

    FASE G-4 — `public_base` kosong (render dari job/penjadwal/WhatsApp/skrip) TIDAK
    boleh menghasilkan QR tanpa host: kertas yang dipegang orang jadi tidak bisa
    dibuka. Karena itu di sini ada fallback ke URL aplikasi yang terkonfigurasi.
    """
    from services.app_url import configured_app_url
    public_base = (public_base or configured_app_url() or "").rstrip("/")
    reg = DOC_REGISTRY.get(doc_type)
    if not reg:
        raise ValueError(f"doc_type '{doc_type}' tidak dikenal")
    source = await db[reg["collection"]].find_one({"id": source_id}, {"_id": 0})
    if not source:
        raise LookupError(f"Dokumen sumber {doc_type}/{source_id} tidak ditemukan")
    eid = entity_id or source.get("entity_id")
    # FASE G-0 — `finance.base_currency` kini benar-benar dipakai: seluruh nominal pada
    # dokumen cetak (invoice, surat jalan, PO) mengikuti mata uang pembukuan entitas.
    from services.config_currency import base_currency
    from services.pdf_engine import set_document_currency
    set_document_currency(await base_currency(eid))
    cfg = await get_template_cfg(doc_type)
    if cfg_override:
        cfg = merge_cfg(cfg, _clean_cfg(cfg_override))
    branding = await get_branding(eid)
    doc = await reg["resolver"](source, db)
    doc = _apply_cfg_to_doc(doc, cfg, branding)
    doc = await _attach_esign(doc, doc_type, source_id, public_base)
    if not doc.get("_hide_refs"):
        doc = await attach_document_refs(doc, doc_type, source_id, source, public_base)
    return {"source": source, "cfg": cfg, "branding": branding, "doc": doc, "reg": reg}


async def render_document(doc_type: str, source_id: str, entity_id: str | None,
                          fmt: str = "pdf", cfg_override: dict | None = None, public_base: str = ""):
    built = await build_document(doc_type, source_id, entity_id, cfg_override, public_base)
    html = render_html(built["cfg"], built["branding"], built["doc"])
    if fmt == "html":
        return html, "text/html", built
    pdf, engine = render_pdf(html)
    return pdf, "application/pdf", built
