"""Model request Fase 26 — titipan pelanggan (kelebihan bayar).

Dipisah dari `models.py` agar file itu tetap di bawah batas compliance (800 baris).
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class DepositReceive(BaseModel):
    """Terima titipan di muka (belum dialokasikan ke termin)."""
    amount: int
    note: Optional[str] = None
    proof_file_ids: List[str] = Field(min_length=1)


class DepositApply(BaseModel):
    """Pakai titipan untuk termin. amount None = sebanyak mungkin (min saldo, sisa tagihan)."""
    amount: Optional[int] = None
    note: Optional[str] = None


class DepositRefund(BaseModel):
    """Kembalikan titipan ke pelanggan. amount None = seluruh saldo."""
    amount: Optional[int] = None
    note: Optional[str] = None
