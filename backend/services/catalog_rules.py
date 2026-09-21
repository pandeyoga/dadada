"""Kontrak murni induk/axis/SKU; digunakan R&D, generator, editor dan impor.

Label kompatibel tetap di variant_attrs. variant_options menyimpan kode stabil;
variant_key adalah identitas kombinasi, bukan pengganti product_id transaksi.
"""
import hashlib
import itertools
import json
import math
import re

MAX_AXES = 6
MAX_OPTIONS = 50
MAX_COMBINATIONS = 200


def normalize_axes(axes):
    if not isinstance(axes, list) or len(axes) > MAX_AXES:
        raise ValueError(f"Maksimal {MAX_AXES} jenis atribut per induk.")
    result, keys = [], set()
    for axis in axes:
        key = str(axis.get("key") or "").strip().lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", key) or key in keys:
            raise ValueError("Kode atribut wajib unik: huruf kecil, angka atau garis bawah.")
        keys.add(key)
        raw = axis.get("options", [])
        # Kompatibilitas eksplisit untuk helper lama, bukan membuang nilai senyap.
        if not raw and axis.get("values"):
            raw = [{"label": str(v)} for v in axis["values"]]
        if not raw or len(raw) > MAX_OPTIONS:
            raise ValueError(f"Atribut {key} memerlukan 1–{MAX_OPTIONS} pilihan.")
        opts, codes, labels = [], set(), set()
        for opt in raw:
            label = str(opt.get("label") or opt.get("code") or "").strip()
            code = str(opt.get("code") or re.sub(r"[^A-Za-z0-9]", "", label)[:16]).strip().upper()
            if not label or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{0,39}", code):
                raise ValueError(f"Pilihan {key} memerlukan nama dan kode SKU yang sah.")
            if code in codes or label.casefold() in labels:
                raise ValueError(f"Pilihan {key} memiliki kode atau nama ganda.")
            codes.add(code); labels.add(label.casefold())
            hx = str(opt.get("hex") or "").strip()
            if hx and not re.fullmatch(r"#[0-9A-Fa-f]{6}", hx):
                raise ValueError("Kode hex warna harus #RRGGBB.")
            opts.append({"code": code, "label": label, "value": opt.get("value", ""), "hex": hx})
        result.append({"key": key, "label": str(axis.get("label") or key).strip(), "options": opts})
    return result


def combination(template, product):
    """Resolve seluruh axis secara tepat. Jangan jatuh ke SKU/opsi terdekat."""
    attrs = dict(product.get("variant_attrs") or {})
    raw_codes = dict(product.get("variant_options") or {})
    axes = template.get("axes") or []
    codes, labels = {}, {}
    for axis in axes:
        key = axis["key"]
        raw = attrs.get(key, product.get(key))
        code = raw_codes.get(key)
        options = axis.get("options") or []
        matches = [o for o in options if (o["code"] == code if code else (
            str(raw).strip().casefold() in {str(o.get("label")).casefold(), str(o.get("code")).casefold(), str(o.get("value")).casefold()} if raw not in (None, "") else False))]
        if len(matches) != 1:
            raise ValueError(f"Pilih {axis['label']} yang sah untuk induk {template.get('name', '')}.")
        o = matches[0]
        codes[key], labels[key] = o["code"], o["label"]
        if key == "color":
            product.update(color=o["label"], color_name=o["label"], color_code=str(o.get("value") or o["code"]), color_hex=o.get("hex", ""))
        elif key == "grade":
            product["grade"] = o["label"]
        elif key == "lebar":
            product["lebar"] = finite_number(o.get("value") or str(o["label"]).replace("cm", ""), "Lebar")
        elif key == "origin":
            product["origin"] = str(o.get("value") or o["label"]).strip().lower()
    unknown = (set(attrs) | set(raw_codes)) - {a['key'] for a in axes}
    if axes and unknown:
        raise ValueError("Atribut di luar definisi induk: " + ", ".join(sorted(unknown)))
    if not axes:
        # Induk satu-varian; data lama yang belum didefinisikan tidak ditebak.
        labels = attrs
        codes = {k: str(v).strip().casefold() for k, v in attrs.items()}
    product["variant_attrs"], product["variant_options"] = labels, codes
    product["variant_label"] = " · ".join(str(v) for v in labels.values()) or "Standar"
    canonical = json.dumps(codes, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    product["variant_key"] = hashlib.sha256(canonical.encode()).hexdigest()
    return product


def finite_number(value, label):
    try:
        num = float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{label} harus berupa angka.")
    if not math.isfinite(num) or num < 0:
        raise ValueError(f"{label} harus angka tidak negatif dan berhingga.")
    return num


def combinations(axes):
    count = math.prod(len(a["options"]) for a in axes) if axes else 0
    if count < 1 or count > MAX_COMBINATIONS:
        raise ValueError(f"Pilih 1–{MAX_COMBINATIONS} kombinasi per proses.")
    return list(itertools.product(*(a["options"] for a in axes)))