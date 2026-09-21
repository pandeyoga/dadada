"""FASE SL — Decoder LABEL SUPPLIER (GS1-128 · QR JSON · teks berpemisah · regex).

Label fisik dari pabrik supplier dibaca satu kali oleh scanner, lalu decoder ini
menerjemahkannya ke bentuk baku:
  {supplier_sku, gtin, lot, roll_no, length, length_unit, weight_kg, color_code, count, format}

Pola per supplier tersimpan di `suppliers.label_pattern`. `format="auto"` (default)
mencoba JSON → GS1 → teks berpemisah. Modul ini MURNI (tanpa DB) agar bisa diuji
lewat "scan contoh" di master supplier.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

FORMATS = ("auto", "gs1", "qr_json", "delimited", "regex")
FIELDS = ("supplier_sku", "gtin", "lot", "roll_no", "length", "weight_kg", "color_code", "count")
GS = "\x1d"

# AI GS1 → (panjang tetap | None=variabel), field baku, pengali desimal untuk 31xx/32xx
_FIXED_LEN = {"00": 18, "01": 14, "02": 14, "11": 6, "13": 6, "15": 6, "17": 6, "20": 2,
              "410": 13, "411": 13, "412": 13, "413": 13, "414": 13}
_VAR_AIS = ("10", "21", "22", "30", "37", "240", "241", "242", "250", "251", "400", "401",
            "90", "91", "92", "93", "94", "95", "96", "97", "98", "99")
DEFAULT_GS1_MAP = {"01": "gtin", "240": "supplier_sku", "241": "supplier_sku", "10": "lot",
                   "21": "roll_no", "30": "count", "310": "weight_kg", "311": "length_m",
                   "323": "length_yd", "91": "color_code"}
DEFAULT_JSON_KEYS = {
    "supplier_sku": ["sku", "item", "code", "kode", "article", "art"],
    "lot": ["lot", "dye_lot", "dyelot", "batch"],
    "roll_no": ["roll", "roll_no", "rollno", "serial", "sn", "no"],
    "length": ["len", "length", "yd", "yard", "m", "meter", "qty"],
    "weight_kg": ["wt", "weight", "kg", "berat"],
    "color_code": ["color", "colour", "col", "warna", "shade"],
    "gtin": ["gtin", "ean", "barcode"],
}
DEFAULT_DELIMITED_FIELDS = ["supplier_sku", "lot", "roll_no", "length", "weight_kg", "color_code"]

DEFAULT_PATTERN: Dict[str, Any] = {
    "format": "auto", "length_unit": "yard", "delimiter": "|",
    "fields": list(DEFAULT_DELIMITED_FIELDS), "regex": "",
    "json_keys": {}, "gs1_ai_map": {},
}


class LabelDecodeError(Exception):
    """Label tidak bisa dibaca dengan pola ini (→ HTTP 400 di router)."""


def normalize_pattern(raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    p = {**DEFAULT_PATTERN, **{k: v for k, v in (raw or {}).items() if v is not None}}
    if p["format"] not in FORMATS:
        p["format"] = "auto"
    p["length_unit"] = "meter" if str(p.get("length_unit", "")).lower().startswith("m") else "yard"
    if not isinstance(p.get("fields"), list) or not p["fields"]:
        p["fields"] = list(DEFAULT_DELIMITED_FIELDS)
    p["delimiter"] = (p.get("delimiter") or "|")[:3]
    p["json_keys"] = p.get("json_keys") if isinstance(p.get("json_keys"), dict) else {}
    p["gs1_ai_map"] = p.get("gs1_ai_map") if isinstance(p.get("gs1_ai_map"), dict) else {}
    return p


def _num(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


def _empty(fmt: str, unit: str) -> Dict[str, Any]:
    return {"supplier_sku": "", "gtin": "", "lot": "", "roll_no": "", "length": None,
            "length_unit": unit, "weight_kg": None, "color_code": "", "count": None, "format": fmt}


# ── GS1-128 ──────────────────────────────────────────────────────────────────
def _split_gs1(raw: str) -> List[tuple]:
    s = raw.strip()
    for prefix in ("]C1", "]Q3", "]d2", "]e0"):
        if s.startswith(prefix):
            s = s[len(prefix):]
    if "(" in s:  # bentuk human-readable "(01)0123(10)LOT"
        pairs = re.findall(r"\((\d{2,4})\)([^(]*)", s)
        if not pairs:
            raise LabelDecodeError("Format GS1 dengan kurung tidak dikenali.")
        return [(ai, val.strip()) for ai, val in pairs]
    out: List[tuple] = []
    i = 0
    while i < len(s):
        if s[i] == GS:
            i += 1
            continue
        ai = None
        for n in (4, 3, 2):
            cand = s[i:i + n]
            if len(cand) < n or not cand.isdigit():
                continue
            if n == 4 and cand[:3] in ("310", "311", "320", "323", "337") or \
               n == 3 and (cand in _VAR_AIS or cand in _FIXED_LEN) or \
               n == 2 and (cand in _VAR_AIS or cand in _FIXED_LEN):
                ai = cand
                break
        if ai is None:
            raise LabelDecodeError(f"AI GS1 tidak dikenal pada posisi {i} ('{s[i:i+4]}').")
        i += len(ai)
        if len(ai) == 4:
            val, i = s[i:i + 6], i + 6
        elif ai in _FIXED_LEN:
            val, i = s[i:i + _FIXED_LEN[ai]], i + _FIXED_LEN[ai]
        else:
            end = s.find(GS, i)
            end = len(s) if end < 0 else end
            val, i = s[i:end], end
        out.append((ai, val))
    return out


def decode_gs1(raw: str, pattern: Dict[str, Any]) -> Dict[str, Any]:
    ai_map = {**DEFAULT_GS1_MAP, **pattern.get("gs1_ai_map", {})}
    out = _empty("gs1", pattern["length_unit"])
    for ai, val in _split_gs1(raw):
        field = ai_map.get(ai) or ai_map.get(ai[:3]) or ai_map.get(ai[:2])
        if not field:
            continue
        if len(ai) == 4 and field in ("weight_kg", "length_m", "length_yd", "length"):
            num = _num(val)
            if num is None:
                continue
            num = num / (10 ** int(ai[3]))
            if field == "weight_kg":
                out["weight_kg"] = round(num, 3)
            else:
                out["length"] = round(num, 2)
                out["length_unit"] = "meter" if field == "length_m" else (
                    "yard" if field == "length_yd" else pattern["length_unit"])
        elif field == "count":
            out["count"] = _num(val)
        elif field in ("length", "weight_kg"):
            out[field] = _num(val)
        elif field in out:
            out[field] = val.strip()
    return out


# ── QR JSON ──────────────────────────────────────────────────────────────────
def decode_json(raw: str, pattern: Dict[str, Any]) -> Dict[str, Any]:
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise LabelDecodeError("Isi QR bukan JSON yang sah.") from exc
    if not isinstance(data, dict):
        raise LabelDecodeError("Isi QR harus objek JSON {…}.")
    lower = {str(k).lower(): v for k, v in data.items()}
    keys = {f: [*(pattern.get("json_keys", {}).get(f) or []), *DEFAULT_JSON_KEYS.get(f, [])]
            for f in DEFAULT_JSON_KEYS}
    out = _empty("qr_json", pattern["length_unit"])
    for field, aliases in keys.items():
        for a in aliases:
            if str(a).lower() in lower:
                v = lower[str(a).lower()]
                if field in ("length", "weight_kg"):
                    out[field] = _num(v)
                    if field == "length" and str(a).lower() in ("m", "meter"):
                        out["length_unit"] = "meter"
                    elif field == "length" and str(a).lower() in ("yd", "yard"):
                        out["length_unit"] = "yard"
                else:
                    out[field] = str(v).strip()
                break
    for uk in ("unit", "uom", "satuan"):
        if uk in lower and str(lower[uk]).lower().startswith("m"):
            out["length_unit"] = "meter"
        elif uk in lower and str(lower[uk]).lower().startswith("y"):
            out["length_unit"] = "yard"
    return out


# ── Teks berpemisah / regex ──────────────────────────────────────────────────
def decode_delimited(raw: str, pattern: Dict[str, Any]) -> Dict[str, Any]:
    parts = [p.strip() for p in raw.strip().split(pattern["delimiter"])]
    if len(parts) < 2:
        raise LabelDecodeError(f"Teks label tidak memuat pemisah '{pattern['delimiter']}'.")
    out = _empty("delimited", pattern["length_unit"])
    for field, val in zip(pattern["fields"], parts):
        if field in ("length", "weight_kg", "count"):
            out[field] = _num(val)
        elif field in out:
            out[field] = val
    return out


def decode_regex(raw: str, pattern: Dict[str, Any]) -> Dict[str, Any]:
    rx = pattern.get("regex") or ""
    if not rx:
        raise LabelDecodeError("Pola regex supplier belum diisi.")
    try:
        m = re.search(rx, raw.strip())
    except re.error as exc:
        raise LabelDecodeError(f"Regex pola tidak sah: {exc}") from exc
    if not m:
        raise LabelDecodeError("Teks label tidak cocok dengan regex pola supplier.")
    out = _empty("regex", pattern["length_unit"])
    for field, val in m.groupdict().items():
        if val is None:
            continue
        if field in ("length", "weight_kg", "count"):
            out[field] = _num(val)
        elif field in out:
            out[field] = val.strip()
    return out


def _looks_gs1(s: str) -> bool:
    s = s.strip()
    return s.startswith("]") or GS in s or bool(re.match(r"^\(\d{2,4}\)", s)) or \
        bool(re.match(r"^(01\d{14}|240|10|21)", s))


def decode(raw: str, pattern: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Terjemahkan string hasil scan sesuai pola supplier (atau deteksi otomatis)."""
    p = normalize_pattern(pattern)
    raw = (raw or "").strip()
    if not raw:
        raise LabelDecodeError("Hasil scan kosong.")
    fmt = p["format"]
    if fmt == "gs1":
        out = decode_gs1(raw, p)
    elif fmt == "qr_json":
        out = decode_json(raw, p)
    elif fmt == "delimited":
        out = decode_delimited(raw, p)
    elif fmt == "regex":
        out = decode_regex(raw, p)
    else:
        if raw.startswith("{"):
            out = decode_json(raw, p)
        elif _looks_gs1(raw):
            out = decode_gs1(raw, p)
        elif p["delimiter"] in raw:
            out = decode_delimited(raw, p)
        elif p.get("regex"):
            out = decode_regex(raw, p)
        else:
            raise LabelDecodeError(
                "Format label tidak dikenali (bukan GS1, QR JSON, maupun teks berpemisah). "
                "Atur pola label di master supplier, atau pakai 'Label tidak terbaca'.")
    out["raw"] = raw
    return out


def decode_first(raw: str, candidates: List[tuple]) -> Dict[str, Any]:
    """Coba pola berurutan [(source, pattern), …] — pola per Barang Supplier lebih dulu, lalu pola supplier.

    Hasil membawa `pattern_source` (mis. "item:CBN-MEGA-PREM" atau "supplier"). Bila semua gagal,
    pesan error pola pertama (paling spesifik) dipakai.
    """
    errors: List[str] = []
    for source, pattern in candidates or [("supplier", None)]:
        try:
            out = decode(raw, pattern)
        except LabelDecodeError as exc:
            errors.append(str(exc))
            continue
        out["pattern_source"] = source
        return out
    raise LabelDecodeError(errors[0] if errors else "Hasil scan kosong.")
