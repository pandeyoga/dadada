import kpr_schedule
from ai import pii
from ai.tools import catalog, registry  # noqa: F401
from ai.tools.registry import ToolContext
from tests_ai.helpers import ctx_for, make_lead


async def test_wa_self_tool_refuses_unverified(app):
    ctx = ToolContext(org_id="o", user={}, token="x", channel="wa", verified=False,
                      contact={"phone": "0811", "lead_id": None, "buyer_customer_id": "cA"})
    r = await registry.run(ctx, "tagihan_pembeli", {})
    assert r["ok"] is False and "verifikasi" in r["error"].lower()
    assert "tagihan_pembeli" not in [t.name for t in registry.tools_for(ctx)]
    names = [t.name for t in registry.tools_for(ToolContext(org_id="o", user={}, token="x", channel="wa", verified=True,
                                                            contact={"buyer_customer_id": "cA"}))]
    assert "api_get" not in names and "cari_endpoint" not in names and "tagihan_pembeli" in names
    for s in registry.api_specs(registry.all_tools()):
        assert s["strict"] is True and s["input_schema"]["additionalProperties"] is False


async def test_wa_self_tool_scoped_to_contact(app):
    ctx = ToolContext(org_id="o", user={}, token="x", channel="wa", verified=True,
                      contact={"phone": "0811", "lead_id": None, "buyer_customer_id": "cA"})
    for tool in ("tagihan_pembeli", "status_kpr_kontrak", "progres_unit"):
        r = await registry.run(ctx, tool, {"customer_id": "cB"})
        assert r["ok"] is False and "terverifikasi" in r["error"], tool


async def test_staff_rbac_respected(client, login, auth):
    t1, t2 = await login("sales@sipro.co.id"), await login("sales2@sipro.co.id")
    mine = await make_lead(client, auth, t1, "Lead Milik Andi")
    other = await make_lead(client, auth, t2, "Lead Milik Dewi")
    ctx = await ctx_for("sales@sipro.co.id", t1)
    r = await registry.run(ctx, "cari_lead", {"batas": 25})
    ids = {x["id"] for x in r["data"]["leads"]}
    assert r["ok"] and mine["id"] in ids and other["id"] not in ids
    r2 = await registry.run(ctx, "detail_lead", {"lead_id": other["id"]})
    assert r2["ok"] is False


async def test_simulasi_kpr_ratio(app):
    ctx = ToolContext(org_id="org-sipro", user={}, token="x")
    from db import ORG_ID
    ctx.org_id = ORG_ID
    r = await registry.run(ctx, "simulasi_kpr", {"plafon": 161_000_000, "bunga_persen": 5, "tenor_bulan": 240,
                                                   "penghasilan": 6_000_000})
    d = r["data"]
    assert r["ok"] and d["batas_cicilan"] == 2_100_000
    assert d["cicilan_per_bulan"] == round(kpr_schedule.annuity(161_000_000, 5, 240))
    assert d["perkiraan_layak"] is True and "bukan keputusan bank" in d["catatan"]


def test_mask_nik_and_account():
    out = pii.mask({"nik": "3171234567890123", "catatan": "NIK 3171234567890123 rek 1234567890123 hp 081234567890 a@b.com"})
    assert out["nik"] == "************0123"
    assert "3171234567890123" not in out["catatan"] and "1234567890123" not in out["catatan"].replace("0123", "")
    assert "081234567890" in out["catatan"] and "a***@b.com" in out["catatan"]
    assert "081234567890" not in str(pii.mask(out, mask_phone=True))
