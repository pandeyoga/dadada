async def test_app_boots_and_superadmin_logs_in(client, login):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert await login("superadmin@estora.id")
