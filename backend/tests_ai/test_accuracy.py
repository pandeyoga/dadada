"""Gerbang akurasi, sampel audit, dan penurunan otomatis (Estora AI tahap 1, Task 10)."""
import pytest

import settings_store as ss
from ai import accuracy, config
from core_utils import new_id, now_iso
from db import db, ORG_ID

ORG = ORG_ID
CAT = "stok_harga"


@pytest.fixture(autouse=True)
async def _clean():
    await ss.set_value("ai.category_modes", {CAT: "draft"}, actor="test", reason="reset", org_id=ORG)
    await db.ai_drafts.delete_many({"org_id": ORG})
    yield
    await ss.set_value("ai.category_modes", {CAT: "draft"}, actor="test", reason="reset", org_id=ORG)


async def _seed(correct, wrong=0, status="sent", **extra):
    ids = []
    for ok in [True] * correct + [False] * wrong:
        d = {"id": new_id(), "org_id": ORG, "category": CAT, "status": status, "text": "x", "correct": ok,
             "outcome_at": now_iso(), "at": now_iso(), **extra}
        await db.ai_drafts.insert_one(dict(d))
        ids.append(d["id"])
    return ids


async def test_accuracy_threshold_blocks_auto_enable():
    await _seed(49)
    ok, why = await accuracy.can_enable_auto(ORG, CAT)
    assert not ok and "Sampel kurang" in why
    with pytest.raises(ValueError):
        await config.set_category_mode(ORG, CAT, "auto", "tester")  # gerbang terpasang di config
    await db.ai_drafts.delete_many({"org_id": ORG})
    await _seed(48, 2)  # 50 sampel, 96%
    ok, _ = await accuracy.can_enable_auto(ORG, CAT)
    assert ok
    assert (await config.set_category_mode(ORG, CAT, "auto", "tester"))[CAT] == "auto"
    await db.ai_drafts.delete_many({"org_id": ORG})
    await _seed(45, 5)  # 90% < ambang 95%
    ok, why = await accuracy.can_enable_auto(ORG, CAT)
    assert not ok and "ambang" in why
    ok, why = await accuracy.can_enable_auto(ORG, "diskon_nego")
    assert not ok and "sales" in why


async def test_auto_sampling_and_demote(client):  # client = aplikasi hidup, pengguna admin ter-seed
    probe = {"id": "abc"}
    assert await accuracy.maybe_sample(probe, 1.0) and not await accuracy.maybe_sample(probe, 0.0)
    assert await accuracy.maybe_sample(probe, 0.5) == await accuracy.maybe_sample(probe, 0.5)  # deterministik
    hits = sum([await accuracy.maybe_sample({"id": f"d{i}"}, 0.10) for i in range(600)])
    assert 30 <= hits <= 100
    await _seed(48, 2)
    await config.set_category_mode(ORG, CAT, "auto", "tester")
    d = {"id": new_id(), "org_id": ORG, "category": CAT, "status": "auto_sent", "text": "x", "sampled": True,
         "sample_review": None, "correct": None, "at": now_iso()}
    await db.ai_drafts.insert_one(dict(d))
    before = await db.notifications.count_documents({"title": {"$regex": "diturunkan ke Draf"}})
    await accuracy.review_sample(d["id"], "wrong", {"org_id": ORG, "email": "owner@estora.id"})
    st = await accuracy.stats(ORG, CAT)
    assert st["samples"] == 51 and st["accuracy"] < 0.95
    assert (await ss.get("ai.category_modes", org_id=ORG))[CAT] == "draft"
    assert await db.notifications.count_documents({"title": {"$regex": "diturunkan ke Draf"}}) > before
