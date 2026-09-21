"""HRD H5 schemas — Design Gallery (motif kain) + AI auto-tag.

Di-re-export via `schemas.py`. Koleksi `design_gallery` (entity-scoped). Upload
gambar via storage lokal (services.storage_service). Lihat memory/PLAN_HRD.md §H5
(keputusan 3a) + §10b HR-Q5 (AI Anthropic Claude langsung, graceful).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GalleryInput(BaseModel):
    """Buat entri motif: judul + cerita/deskripsi + tags + (opsional) link produk.

    FASE F (PS-14) — diperluas menjadi MASTER DESAIN: kode unik, jenis desain, dan
    atribut printing (repeat, jumlah warna, jumlah screen). Semua opsional supaya
    entri galeri HRD yang lama tetap sah dibuat tanpa perubahan.
    """
    title: str = ""
    story: str = ""
    tags: List[str] = []
    product_id: str = ""             # opsional: tautan ke produk (SKU/varian)
    code: str = ""                   # kode desain (unik per entitas)
    design_type: str = ""            # LEGACY (dihapus dari UI 2026-09-17) — dibiarkan opsional
    repeat_cm: Optional[float] = None
    color_count: Optional[int] = None
    screen_count: Optional[int] = None
    line_code: str = ""              # FASE L — lini kerja MD (kosong = semua lini)
    # Design Studio — Kategori Pattern (category_code) + Kategori Design (design_category_code).
    category_code: str = ""
    design_category_code: str = ""
    recommended_product_ids: List[str] = []   # ditetapkan penilai saat ACC (UI desainer tidak mengirim)
    colors: List[Dict[str, Any]] = []      # LEGACY palet — tidak lagi dipakai form


class GalleryUpdate(BaseModel):
    """Update parsial entri motif / master desain."""
    title: Optional[str] = None
    story: Optional[str] = None
    tags: Optional[List[str]] = None
    product_id: Optional[str] = None
    code: Optional[str] = None
    design_type: Optional[str] = None
    repeat_cm: Optional[float] = None
    color_count: Optional[int] = None
    screen_count: Optional[int] = None
    line_code: Optional[str] = None   # FASE L
    status: Optional[str] = None      # draft | approved | retired
    category_code: Optional[str] = None
    design_category_code: Optional[str] = None
    final_color_count: Optional[int] = None
    recommended_product_ids: Optional[List[str]] = None
    colors: Optional[List[Dict[str, Any]]] = None


class DesignVersionIn(BaseModel):
    """Naikkan versi desain (artwork direvisi) — versi lama tetap terarsip."""
    note: str = ""
    repeat_cm: Optional[float] = None
    color_count: Optional[int] = None
    screen_count: Optional[int] = None


class DesignTransitionIn(BaseModel):
    """Aksi siklus hidup: catatan (wajib untuk revisi/arsip) + nilai opsional saat ACC.
    Saat ACC penilai juga menetapkan peruntukan produk & jumlah varian warna final."""
    note: str = ""
    score: Optional[float] = None
    recommended_product_ids: Optional[List[str]] = None
    final_color_count: Optional[int] = None


class DesignScoreIn(BaseModel):
    """Nilai versi 0–2 kelipatan 0,25 (divalidasi di service)."""
    score: float
    note: str = ""


class DesignFeedbackIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    version: Optional[int] = None


class ColorwayIn(BaseModel):
    name: Optional[str] = None
    note: Optional[str] = None
    colors: Optional[List[Dict[str, Any]]] = None
    is_default: Optional[bool] = None


class CategoryIn(BaseModel):
    design_type: str
    code: str
    name: str


class CategoryPatch(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


class DesignApproveIn(BaseModel):
    note: str = ""


class DesignRatingIn(BaseModel):
    """Set/ubah rating bintang 1–5 untuk sebuah desain (1 nilai per penilai)."""
    stars: int
    note: str = ""


class DesignRejectIn(BaseModel):
    """Alasan pengembalian desain ke draf — WAJIB."""
    reason: str = Field(min_length=3, max_length=500)


class DesignAiIllustrateIn(BaseModel):
    """FB-01 — minta ilustrasi AI (arahan atasan): mockup produk atau modifikasi artwork."""
    mode: str = "mockup"                      # mockup | modify
    prompt: str = Field(min_length=3, max_length=1500)
    source_file_id: Optional[str] = None      # artwork acuan; default = artwork pertama


class IllustrationCommentIn(BaseModel):
    """Komentar/balasan pada ilustrasi AI — diskusi arahan atasan ↔ desainer."""
    text: str = Field(min_length=1, max_length=1000)
