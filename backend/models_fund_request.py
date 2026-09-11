"""Model payload modul Pengajuan keuangan."""
from typing import List, Optional

from pydantic import BaseModel, Field

from models_p27 import CashbonExpenseItem
from reference import _opt

FundRequestType = _opt("fund_request_type")
FundRequestUrgency = _opt("fund_request_urgency")


class FundRequestItem(BaseModel):
    description: str = Field(min_length=2, max_length=200)
    qty: int = Field(default=1, ge=1)
    unit_price: int = Field(ge=0)


class FundRequestCreate(BaseModel):
    type: FundRequestType
    title: str = Field(min_length=3, max_length=200)
    amount: int = Field(gt=0)
    category: str = "lainnya"
    urgency: FundRequestUrgency = "normal"
    needed_date: Optional[str] = None
    project_id: Optional[str] = None
    payee_name: Optional[str] = None
    payee_bank: Optional[str] = None
    payee_account: Optional[str] = None
    # vendor_payment: tagihan AP yang dibayar lewat pengajuan ini — pencairan melunasi
    # 2-1100 (bukan membebankan ulang), jadi biaya tidak tercatat dua kali.
    ap_bill_id: Optional[str] = None
    items: List[FundRequestItem] = []
    attachment_ids: List[str] = []
    note: Optional[str] = None


class FundRequestDecision(BaseModel):
    note: Optional[str] = None
    approved_amount: Optional[int] = None


class FundRequestDisburse(BaseModel):
    amount: Optional[int] = None
    source: str = "bank"
    cash_account_id: Optional[str] = None
    reference_no: Optional[str] = None
    note: Optional[str] = None


class FundRequestSettle(BaseModel):
    items: List[CashbonExpenseItem] = Field(min_length=1)
    attachment_ids: List[str] = []
    note: Optional[str] = None
