"""FASE SL — skema penerimaan berbasis SCAN LABEL SUPPLIER."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ManualLabelIn(BaseModel):
    """Fallback 'label tidak terbaca' — barang DIPILIH dari item PO, bukan diketik."""
    supplier_item_id: str = ""
    supplier_roll_no: str
    declared_length: float = Field(0, ge=0)
    length_unit: str = "yard"
    declared_weight_kg: float = Field(0, ge=0)
    lot: str = ""
    color_code: str = ""
    reason: str = "label_unreadable"      # label_unreadable | label_damaged | no_barcode | other
    reason_note: str = ""


class ScanLabelIn(BaseModel):
    raw: str = ""
    manual: Optional[ManualLabelIn] = None


class ConfirmMeasureIn(BaseModel):
    """Hanya PENGUKURAN FISIK yang boleh disentuh manusia."""
    actual_length: Optional[float] = Field(None, ge=0)
    actual_weight_kg: Optional[float] = Field(None, ge=0)
    grade: str = ""
    defects: List[str] = []


class PutawayIn(BaseModel):
    bin_code: str = ""
    bin_id: str = ""


class TagRfidIn(BaseModel):
    epc: str = ""          # kosong = EPC dibuat sistem; isi bila dibaca dari handheld/printer


class LabelPatternIn(BaseModel):
    format: str = "auto"
    length_unit: str = "yard"
    delimiter: str = "|"
    fields: List[str] = []
    regex: str = ""
    json_keys: Dict[str, List[str]] = {}
    gs1_ai_map: Dict[str, str] = {}


class LabelPatternTestIn(BaseModel):
    raw: str
    pattern: Optional[LabelPatternIn] = None
