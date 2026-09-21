"""Idempotency-Key — aksi gudang dari HP (juga saat sinkron ulang dari antrean offline).

Kunci sama → balasan PERTAMA dikembalikan apa adanya (kode + body), efek samping tidak diulang.
Hanya aktif bila klien mengirim header `Idempotency-Key` pada POST. Kunci diikat ke path+user
agar kunci yang sama untuk aksi berbeda tidak saling menutupi. Rekaman kedaluwarsa 7 hari.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from db import db
from core_utils import now_iso

HEADER = "idempotency-key"
TTL_DAYS = 7
IDEMPOTENT_PREFIXES = ("/api/inbound/", "/api/outbound/", "/api/wms/tasks/",
                       "/api/rfid/lookup", "/api/rfid/roll-scans", "/api/rfid/print-jobs",
                       "/api/hr/visits", "/api/sales-orders", "/api/price-approvals",
                       "/api/ar-receipts", "/api/sales-returns", "/api/special-orders")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        key = request.headers.get(HEADER, "").strip()
        if not key or request.method not in ("POST", "PUT", "PATCH", "DELETE") \
                or not request.url.path.startswith(IDEMPOTENT_PREFIXES):
            return await call_next(request)
        who = request.headers.get("authorization", "")[-24:] or request.cookies.get("kn_session", "")[-24:]
        doc_id = f"{key}|{request.method}|{request.url.path}|{who}"
        now = datetime.now(timezone.utc)
        try:
            await db.idempotency_keys.insert_one({
                "_id": doc_id, "key": key, "path": request.url.path, "status": "in_progress",
                "created_at": now_iso(), "expires_at": now + timedelta(days=TTL_DAYS)})
        except Exception:
            existing = await db.idempotency_keys.find_one({"_id": doc_id})
            if existing and existing.get("status") == "done":
                resp = JSONResponse(status_code=existing["code"], content=existing["body"])
                resp.headers["X-Idempotent-Replay"] = "true"
                return resp
            return JSONResponse(status_code=409, content={"detail": {
                "code": "IDEMPOTENT_IN_PROGRESS",
                "message": "Permintaan dengan kunci yang sama masih diproses. Tunggu sebentar."}})
        try:
            response = await call_next(request)
        except Exception:
            await db.idempotency_keys.delete_one({"_id": doc_id})
            raise
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        parsed: Any = None
        try:
            parsed = json.loads(body.decode() or "null")
        except Exception:
            parsed = None
        if parsed is not None and response.status_code < 500:
            await db.idempotency_keys.update_one({"_id": doc_id}, {"$set": {
                "status": "done", "code": response.status_code, "body": parsed, "done_at": now_iso()}})
        else:
            await db.idempotency_keys.delete_one({"_id": doc_id})   # 5xx/non-JSON: biarkan klien coba lagi
        headers: Dict[str, str] = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        return Response(content=body, status_code=response.status_code, headers=headers,
                        media_type=response.media_type)


async def ensure_indexes() -> None:
    await db.idempotency_keys.create_index("expires_at", expireAfterSeconds=0)
