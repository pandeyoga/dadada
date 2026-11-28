"""Kerangka uji AI: aplikasi dijalankan in-process (tanpa server HTTP) ke MongoDB lokal."""
import os
import sys
from pathlib import Path

# Env harus diset SEBELUM `server`/`db` diimpor.
DB_NAME = os.environ.get("AI_TEST_DB", "estora_ai_test")
if not os.environ.get("MONGO_URL"):
    raise SystemExit("Set MONGO_URL ke MongoDB lokal uji (lihat tests_ai/README.md) sebelum menjalankan tests_ai.")
os.environ["DB_NAME"] = DB_NAME
os.environ.setdefault("JWT_SECRET", "test-secret-estora-ai-0123456789abcdef")
os.environ["SEED_DEMO_USERS"] = "true"
os.environ.setdefault("STORAGE_PROVIDER", "mongo")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402


@pytest_asyncio.fixture(scope="session")
async def app():
    import server
    from db import client as mongo
    await mongo.drop_database(DB_NAME)  # run bisa diulang
    async with server.app.router.lifespan_context(server.app):
        yield server.app
    try:
        import engine
        if engine._scheduler:
            engine._scheduler.shutdown(wait=False)
    except Exception:
        pass


@pytest_asyncio.fixture(scope="session")
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture(scope="session")
async def login(client):
    import seed

    async def _login(email: str) -> str:
        pw = seed.SUPERADMIN_PASSWORD if email.lower() == seed.SUPERADMIN_EMAIL else seed.TEST_PASSWORD
        r = await client.post("/api/auth/login", json={"email": email, "password": pw})
        assert r.status_code == 200, r.text
        return r.json()["access_token"]
    return _login


@pytest_asyncio.fixture(scope="session")
def auth():
    return lambda token: {"Authorization": f"Bearer {token}"}
