"""Cakupan data portal pembeli: akun pemegang reservasi (lead, `customer_id` kosong) hanya melihat
barisnya SENDIRI — bukan seluruh organisasi, dan bukan setiap baris yang `customer_id`-nya null.

Dulu `GET /portal/payments/submissions` & `/portal/warranty/claims` melewatkan saringan pemilik bila
`customer_id` kosong (= semua baris org), sedangkan `/portal/complaints`, `/portal/handovers` dan
detail klaim mencocokkan `customer_id: None` (= setiap baris tanpa pelanggan milik orang lain).
"""
import uuid

import pytest

from core_utils import new_id, now_iso
from db import db, ORG_ID
from portal_security import create_portal_token

TS = "2026-11-01T00:00:00+00:00"


def _phone() -> str:
    return f"+62815{uuid.uuid4().int % 10**8:08d}"


async def _deal(tag: str, lead_id: str, customer_id=None, status="booked") -> dict:
    unit_id, deal_id = new_id(), new_id()
    await db.units.insert_one({"id": unit_id, "org_id": ORG_ID, "code": f"SC-{tag}", "type": "36",
                               "project_id": "proj-scope-uji", "status": "sold"})
    await db.deals.insert_one({"id": deal_id, "org_id": ORG_ID, "lead_id": lead_id,
                               "customer_id": customer_id, "unit_id": unit_id,
                               "project_id": "proj-scope-uji", "status": status, "created_at": TS})
    return {"deal_id": deal_id, "unit_id": unit_id}


async def _rows(tag: str, d: dict, customer_id=None) -> dict:
    """Satu komplain, satu bukti transfer, satu klaim garansi, satu BAST untuk deal `d`."""
    ids = {k: new_id() for k in ("complaint", "intake", "claim", "handover")}
    await db.complaints.insert_one({"id": ids["complaint"], "org_id": ORG_ID, "customer_id": customer_id,
                                    "deal_id": d["deal_id"], "unit_id": d["unit_id"],
                                    "subject": f"Rahasia {tag}", "message": "isi", "category": "lainnya",
                                    "status": "open", "created_at": TS})
    await db.payment_intakes.insert_one({"id": ids["intake"], "org_id": ORG_ID, "customer_id": customer_id,
                                         "deal_id": d["deal_id"], "unit_id": d["unit_id"],
                                         "amount": 1_000_000, "state": "pending", "source": "portal",
                                         "customer_name": f"Pembeli {tag}", "created_at": TS})
    await db.warranty_claims.insert_one({"id": ids["claim"], "org_id": ORG_ID, "customer_id": customer_id,
                                         "deal_id": d["deal_id"], "unit_id": d["unit_id"],
                                         "number": f"KG-{tag}", "title": f"Bocor {tag}", "state": "diajukan",
                                         "created_at": TS})
    await db.unit_handovers.insert_one({"id": ids["handover"], "org_id": ORG_ID, "customer_id": customer_id,
                                        "deal_id": d["deal_id"], "unit_id": d["unit_id"],
                                        "number": f"BAST-{tag}", "state": "issued", "handed_over_at": TS})
    return ids


async def _portal_user(*, customer_id=None, lead_id=None, tag: str) -> str:
    pu = {"id": new_id(), "org_id": ORG_ID, "is_active": True, "customer_id": customer_id,
          "lead_id": lead_id, "name": f"Pembeli {tag}", "phone": _phone(), "email": None,
          "created_at": now_iso()}
    await db.portal_users.insert_one(dict(pu))
    return create_portal_token(pu)


@pytest.fixture(scope="module")
async def world(app):
    tag = uuid.uuid4().hex[:6]
    # B — pembeli penuh (customer + lead).
    b_lead, b_cust = new_id(), new_id()
    await db.leads.insert_one({"id": b_lead, "org_id": ORG_ID, "name": "B", "phone": _phone()})
    await db.customers.insert_one({"id": b_cust, "org_id": ORG_ID, "name": "B", "lead_id": b_lead})
    b_deal = await _deal(f"B{tag}", b_lead, b_cust)
    b_rows = await _rows(f"B{tag}", b_deal, customer_id=b_cust)
    # R — pemegang reservasi saja (lead, tanpa customer).
    r_lead = new_id()
    await db.leads.insert_one({"id": r_lead, "org_id": ORG_ID, "name": "R", "phone": _phone()})
    r_deal = await _deal(f"R{tag}", r_lead, None, status="reserved")
    r_rows = await _rows(f"R{tag}", r_deal, customer_id=None)
    # X — lead lain: baris ber-`customer_id` null yang BUKAN milik R.
    x_lead = new_id()
    await db.leads.insert_one({"id": x_lead, "org_id": ORG_ID, "name": "X", "phone": _phone()})
    x_deal = await _deal(f"X{tag}", x_lead, None, status="reserved")
    x_rows = await _rows(f"X{tag}", x_deal, customer_id=None)
    # Y — pembeli penuh lain (customer_id terisi), juga bukan milik R maupun B.
    y_cust, y_lead = new_id(), new_id()
    y_deal = await _deal(f"Y{tag}", y_lead, y_cust)
    y_rows = await _rows(f"Y{tag}", y_deal, customer_id=y_cust)
    return {"B": (await _portal_user(customer_id=b_cust, tag="B"), b_rows),
            "R": (await _portal_user(lead_id=r_lead, tag="R"), r_rows),
            "Z": (await _portal_user(tag="Z"), {}),  # akun yatim: tanpa customer & tanpa lead
            "others": [x_rows, y_rows]}


async def _ids(client, token: str, path: str) -> set:
    r = await client.get(f"/api/portal{path}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, (path, r.text)
    return {row["id"] for row in r.json()["data"]}


LISTS = (("/payments/submissions", "intake"), ("/warranty/claims", "claim"),
         ("/complaints", "complaint"), ("/handovers", "handover"))


@pytest.mark.parametrize("who", ["B", "R"])
@pytest.mark.parametrize("path,key", LISTS)
async def test_lists_show_exactly_own_rows(client, world, who, path, key):
    token, own = world[who]
    assert await _ids(client, token, path) == {own[key]}


@pytest.mark.parametrize("path,key", LISTS)
async def test_orphan_account_sees_nothing(client, world, path, key):
    token, _ = world["Z"]
    assert await _ids(client, token, path) == set()


async def test_submission_summary_counts_only_own(client, world):
    for who in ("B", "R", "Z"):
        token, own = world[who]
        r = await client.get("/api/portal/payments/submissions", headers={"Authorization": f"Bearer {token}"})
        body = r.json()
        assert body["total"] == (1 if own else 0), who
        assert body["summary"]["pending"] == body["total"], who
        assert body["summary"]["pending_amount"] == 1_000_000 * body["total"], who


@pytest.mark.parametrize("who", ["B", "R", "Z"])
async def test_detail_of_someone_elses_row_is_404(client, world, who):
    token, _ = world[who]
    h = {"Authorization": f"Bearer {token}"}
    for other in world["others"]:
        r = await client.get(f"/api/portal/warranty/claims/{other['claim']}", headers=h)
        assert r.status_code == 404, (who, r.text)
        r = await client.get(f"/api/portal/handovers/{other['handover']}/pdf", headers=h)
        assert r.status_code == 404, (who, r.text)


@pytest.mark.parametrize("who", ["B", "R"])
async def test_detail_of_own_claim_still_works(client, world, who):
    token, own = world[who]
    r = await client.get(f"/api/portal/warranty/claims/{own['claim']}",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] == own["claim"]


async def test_rows_written_by_reservation_portal_are_visible_only_to_it(client, world):
    """Lewat jalur tulis yang SEBENARNYA (bukan sisipan langsung): komplain & bukti transfer yang dikirim
    akun reservasi tersimpan dengan `customer_id` kosong/lead — tetap terlihat olehnya, tidak oleh B/Z."""
    tok_r, own_r = world["R"]
    h = {"Authorization": f"Bearer {tok_r}"}
    deal_id = (await db.complaints.find_one({"id": own_r["complaint"]}, {"_id": 0}))["deal_id"]
    r = await client.post("/api/portal/complaints", headers=h, json={
        "deal_id": deal_id, "category": "lainnya", "subject": "Lewat portal", "message": "isi"})
    assert r.status_code == 200, r.text
    complaint_id = r.json()["data"]["id"]
    pdf = b"%PDF-1.4\n% bukti " + uuid.uuid4().hex.encode() + b"\n%%EOF\n"
    r = await client.post("/api/portal/payments/proof/upload", headers=h, data={"deal_id": deal_id},
                          files={"file": ("bukti.pdf", pdf, "application/pdf")})
    assert r.status_code == 200, r.text
    r = await client.post("/api/portal/payments/proof", headers=h, json={
        "deal_id": deal_id, "amount": 2_500_000, "transfer_date": "2026-11-20",
        "file_ids": [r.json()["data"]["id"]]})
    assert r.status_code == 200, r.text
    intake_id = r.json()["data"]["id"]
    assert complaint_id in await _ids(client, tok_r, "/complaints")
    assert intake_id in await _ids(client, tok_r, "/payments/submissions")
    for who in ("B", "Z"):
        tok = world[who][0]
        assert complaint_id not in await _ids(client, tok, "/complaints"), who
        assert intake_id not in await _ids(client, tok, "/payments/submissions"), who


async def test_resold_unit_is_not_the_old_buyers_house(client):
    """Deal batal bukan "rumah saya": A membatalkan unit U, U dijual ulang ke B dan diserahterimakan. A tetap punya akses
    portal (refund), tetapi tidak melihat BAST (nama & nomor B) / klaim B dan tidak bisa mengajukan atau mengakui klaim
    di rumah B — lewat endpoint maupun alat Tanya Estora."""
    import reference as ref
    from ai import conversations
    from ai.tools import catalog, registry  # noqa: F401
    from ai.tools.registry import ToolContext
    tag = uuid.uuid4().hex[:6]
    a_lead, a_cust, b_lead, b_cust, b_deal = new_id(), new_id(), new_id(), new_id(), new_id()
    for lead, cust, name in ((a_lead, a_cust, "A"), (b_lead, b_cust, "B")):
        await db.leads.insert_one({"id": lead, "org_id": ORG_ID, "name": name, "phone": _phone()})
        await db.customers.insert_one({"id": cust, "org_id": ORG_ID, "name": name, "lead_id": lead})
    a = await _deal(f"A{tag}", a_lead, a_cust, status="cancelled")
    await db.deals.insert_one({"id": b_deal, "org_id": ORG_ID, "lead_id": b_lead, "customer_id": b_cust,
                               "unit_id": a["unit_id"], "project_id": "proj-scope-uji", "status": "booked", "created_at": TS})
    b_rows = await _rows(f"B{tag}", {"deal_id": b_deal, "unit_id": a["unit_id"]}, customer_id=b_cust)
    pa = {"id": new_id(), "org_id": ORG_ID, "is_active": True, "customer_id": a_cust, "lead_id": None, "name": "Pembeli A",
          "phone": _phone(), "email": None, "created_at": now_iso()}
    await db.portal_users.insert_one(dict(pa))
    ta, tb = create_portal_token(pa), await _portal_user(customer_id=b_cust, tag="B")
    ha = {"Authorization": f"Bearer {ta}"}
    assert await _ids(client, tb, "/handovers") == {b_rows["handover"]}  # kontrol: B (pemilik baru) melihatnya
    assert b_rows["claim"] in await _ids(client, tb, "/warranty/claims")
    assert await _ids(client, ta, "/handovers") == set()
    assert b_rows["claim"] not in await _ids(client, ta, "/warranty/claims")
    w = (await client.get("/api/portal/warranty", headers=ha)).json()
    assert w["data"] == [] and f"B{tag}" not in str(w)
    assert (await client.get(f"/api/portal/warranty/claims/{b_rows['claim']}", headers=ha)).status_code == 404
    r = await client.post(f"/api/portal/warranty/claims/{b_rows['claim']}/ack", headers=ha, json={"satisfied": True})
    assert r.status_code == 404
    assert (await client.get(f"/api/portal/handovers/{b_rows['handover']}/pdf", headers=ha)).status_code == 404
    cat = next(iter(ref.values("warranty_category")))
    r = await client.post("/api/portal/warranty/claims", headers=ha,
                          json={"unit_id": a["unit_id"], "category": cat, "title": "Atap bocor"})
    assert r.status_code == 403 and await db.warranty_claims.count_documents({"unit_id": a["unit_id"]}) == 1
    conv = await conversations.create(ORG_ID, pa["id"], role="buyer_cs", channel="portal")
    ctx = ToolContext(org_id=ORG_ID, user=pa, token=ta, channel="portal", conversation_id=conv["id"], verified=True,
                      role="buyer_cs")
    for inp in ({}, {"deal_id": a["deal_id"]}):  # termasuk menanyakan deal batalnya sendiri (dulu dicocokkan lewat kode unit)
        st = await registry.run(ctx, "serah_terima_saya", inp)
        assert st["ok"] and st["data"]["jumlah"] == 0 and f"B{tag}" not in str(st), st
        gr = await registry.run(ctx, "garansi_saya", inp)
        assert gr["ok"] and gr["data"]["garansi"] == [] and gr["data"]["klaim"] == [], gr
    bad = await registry.run(ctx, "ajukan_klaim_garansi", {"unit_id": a["unit_id"], "category": cat, "title": "Atap bocor"})
    assert bad["ok"] is False and await db.ai_actions.count_documents({"entity_id": a["unit_id"]}) == 0
