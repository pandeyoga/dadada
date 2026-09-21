"""Wilayah & kode pos — pencarian bertingkat untuk form alamat (negara → provinsi → kota → kecamatan → kode pos)."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from dependencies import current_user
from services import wilayah_service as w

router = APIRouter(prefix="/api")


@router.get("/wilayah/countries")
async def countries(request: Request) -> List[Dict[str, str]]:
    await current_user(request)
    return w.COUNTRIES


@router.get("/wilayah/provinces")
async def provinces(request: Request) -> List[Dict[str, str]]:
    await current_user(request)
    return w.provinces()


@router.get("/wilayah/regencies")
async def regencies(request: Request, province_code: str) -> List[Dict[str, str]]:
    await current_user(request)
    return w.regencies(province_code)


@router.get("/wilayah/districts")
async def districts(request: Request, regency_code: str) -> List[Dict[str, Any]]:
    await current_user(request)
    return w.districts(regency_code)


@router.get("/wilayah/villages")
async def villages(request: Request, district_code: str) -> List[Dict[str, Any]]:
    await current_user(request)
    return w.villages(district_code)


@router.get("/wilayah/postal-code/{code}")
async def postal_code(code: str, request: Request) -> List[Dict[str, Any]]:
    await current_user(request)
    return w.by_postal_code(code)


@router.get("/wilayah/search")
async def search(request: Request, q: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    await current_user(request)
    return w.search(q, limit=max(1, min(limit, 50)))


@router.post("/wilayah/validate")
async def validate(request: Request, body: Dict[str, Any], require: Optional[bool] = True) -> Dict[str, Any]:
    await current_user(request)
    return {"valid": True, **w.normalize_location(body or {}, require=bool(require))}
