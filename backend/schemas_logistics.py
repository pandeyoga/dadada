"""FB-02 schemas — Modul Logistik: pengiriman (ekspedisi / armada sendiri / diambil pelanggan)
dengan validasi foto MUAT & POD, riwayat posisi, tahapan status, kode pickup, dan armada."""
from typing import List, Optional
from pydantic import BaseModel, Field


class DeliveryCreateIn(BaseModel):
    shipment_ids: List[str] = Field(min_length=1)   # Surat Jalan (SJ-) yang diangkut
    mode: str = "expedition"                        # expedition | own_fleet | self_pickup
    courier_name: str = ""
    service_level: str = ""
    tracking_no: str = ""
    shipping_cost: float = Field(default=0, ge=0)   # biaya kirim ekspedisi (Rp)
    vehicle_id: str = ""                            # armada sendiri: kendaraan dari master
    vehicle_plate: str = ""
    driver_name: str = ""
    driver_user_id: str = ""
    eta: str = ""                                   # YYYY-MM-DD
    destination: str = ""
    receiver_phone: str = ""                        # kosong → otomatis dari alamat kirim SO / kontak pelanggan
    notes: str = ""


class DeliveryUpdateIn(BaseModel):
    mode: Optional[str] = None
    courier_name: Optional[str] = None
    service_level: Optional[str] = None
    tracking_no: Optional[str] = None
    shipping_cost: Optional[float] = Field(default=None, ge=0)
    vehicle_id: Optional[str] = None
    vehicle_plate: Optional[str] = None
    driver_name: Optional[str] = None
    driver_user_id: Optional[str] = None
    eta: Optional[str] = None
    destination: Optional[str] = None
    receiver_phone: Optional[str] = None
    notes: Optional[str] = None


class PositionIn(BaseModel):
    location: str = Field(min_length=2, max_length=200)
    note: str = ""
    lat: Optional[float] = Field(default=None, ge=-90, le=90)      # L-2
    lng: Optional[float] = Field(default=None, ge=-180, le=180)


class TransitionIn(BaseModel):
    to: str                                         # loaded | in_transit | delivered | completed | failed | prepared
    reason: str = ""
    receiver_name: str = ""
    received_at: str = ""
    note: str = ""


class MyRouteIn(BaseModel):
    """Urutan tujuan sopir hari ini (id pengiriman berurutan)."""
    ids: List[str] = Field(min_length=1)


class PickupHandoverIn(BaseModel):
    """Serah terima barang ke pelanggan yang mengambil sendiri (validasi kode + identitas)."""
    pickup_code: str = Field(min_length=4, max_length=12)
    picker_name: str = Field(min_length=2, max_length=120)
    picker_id_no: str = Field(default="", max_length=40)    # No. KTP/SIM/identitas pengambil
    note: str = ""


class VehicleIn(BaseModel):
    plate: str = Field(min_length=3, max_length=20)
    type: str = "other"
    name: str = ""
    capacity_note: str = ""
    default_driver_user_id: str = ""
    notes: str = ""


class VehicleUpdateIn(BaseModel):
    plate: Optional[str] = None
    type: Optional[str] = None
    name: Optional[str] = None
    capacity_note: Optional[str] = None
    default_driver_user_id: Optional[str] = None
    notes: Optional[str] = None


class VehicleStatusIn(BaseModel):
    status: str                                     # available | maintenance
    note: str = ""
