import pytest

from db import db, ORG_ID

pytestmark = pytest.mark.asyncio


async def test_api_key_roundtrip_is_encrypted(app):
    from ai import config
    await config.save_api_key(ORG_ID, "sk-ant-test-1234567890", "tester")
    assert await config.get_api_key(ORG_ID) == "sk-ant-test-1234567890"
    raw = await db.channel_accounts.find_one({"org_id": ORG_ID, "code": "anthropic"})
    assert "sk-ant-test-1234567890" not in str(raw)
    await db.channel_accounts.delete_one({"org_id": ORG_ID, "code": "anthropic"})


async def test_cost_math(app):
    from ai import budget
    usd = budget.cost_usd("claude-opus-5-5", {"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    assert usd == 24.0
    doc = await budget.record_usage(ORG_ID, model="claude-opus-5-5", context={"t": 1},
                                    usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000})
    assert doc["cost_idr"] == 384000
    await db.ai_usage.delete_many({"org_id": ORG_ID})
    await db.ai_budget_alerts.delete_many({"org_id": ORG_ID})


async def test_budget_states(app):
    import settings_store as ss
    from ai import budget
    await db.ai_usage.delete_many({"org_id": ORG_ID})
    await db.ai_budget_alerts.delete_many({"org_id": ORG_ID})
    await db.notifications.delete_many({"related_entity_type": "ai_budget"})
    await ss.set_value("ai.budget_idr_month", 1000000, actor="t", reason="uji", org_id=ORG_ID)

    async def add(idr):
        await db.ai_usage.insert_one({"org_id": ORG_ID, "month": budget._month(), "cost_idr": idr})
        await budget._maybe_warn(ORG_ID)
        return await budget.budget_state(ORG_ID)

    assert (await add(790000))["state"] == "ok"
    assert (await db.notifications.count_documents({"related_entity_type": "ai_budget"})) == 0
    assert (await add(10000))["state"] == "warn"
    n1 = await db.notifications.count_documents({"related_entity_type": "ai_budget"})
    assert n1 >= 1
    assert (await add(10000))["state"] == "warn"
    assert await db.notifications.count_documents({"related_entity_type": "ai_budget"}) == n1
    assert (await add(190000))["state"] == "stop"
    assert await db.notifications.count_documents({"related_entity_type": "ai_budget"}) == n1
    await ss.reset("ai.budget_idr_month", actor="t", org_id=ORG_ID)
    await db.ai_usage.delete_many({"org_id": ORG_ID})


async def test_rbac_defaults(app):
    import rbac
    assert await rbac.can("sales", "ai_inbox", "use")
    assert not await rbac.can("finance", "ai_inbox", "use")
    assert await rbac.can("finance", "ai_copilot", "use")
    assert await rbac.can("owner", "ai_settings", "manage")
    assert not await rbac.can("sales", "ai_settings", "manage")
    assert await rbac.can("ai_agent", "leads", "view_all")
    assert await rbac.can("ai_agent", "appointments", "create")
    matrix = await rbac.get_matrix()
    for res in matrix:
        assert not await rbac.can("ai_agent", res, "delete"), res
