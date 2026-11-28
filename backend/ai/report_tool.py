"""Alat `buat_laporan` + bentuk artefak untuk UI (blok bars/table/markdown, jenis unduhan)."""
from ai import config, reports
from ai.tools import registry
from ai.tools.registry import Tool, ToolError


def artifact_view(doc: dict, *, is_sample: bool = False) -> dict:
    spec = doc.get("spec") or {}
    blocks = []
    if spec.get("ringkasan"):
        blocks.append({"type": "markdown", "text": spec["ringkasan"]})
    for b in spec.get("bagian") or []:
        if b.get("teks"):
            blocks.append({"type": "markdown", "text": f"**{b['judul']}**\n\n{b['teks']}"})
        g = b.get("grafik")
        if g and g.get("seri"):
            vals = g["seri"][0]["nilai"]
            blocks.append({"type": "bars", "title": b["judul"],
                           "items": [{"label": l, "value": v} for l, v in zip(g["label"], vals)]})
        t = b.get("tabel")
        if t:
            blocks.append({"type": "table", "title": b["judul"], "columns": t["kolom"], "rows": t["baris"]})
    f = doc.get("files") or {}
    kinds = [k for k in ("pdf", "xlsx") if f.get(k)] + (["png"] if f.get("png") else [])
    return {"id": doc["id"], "title": doc.get("title") or spec.get("judul"), "is_sample": is_sample,
            "updated_at": doc.get("at"), "sources": [], "kinds": kinds, "blocks": blocks}


async def _handler(ctx, inp: dict) -> dict:
    try:
        doc = await reports.build_report(org_id=ctx.org_id, conversation_id=ctx.conversation_id,
                                         created_by=(ctx.user or {}).get("id", "na"), spec=inp)
    except ValueError as e:
        raise ToolError(str(e))
    sample = (await config.get_ai_settings(ctx.org_id)).get("effective_mode") != "live"
    return {"artifact": artifact_view(doc, is_sample=sample), "summary": f"Laporan '{doc['title']}' dibuat"}


def register_all() -> None:
    registry.register(Tool(
        "buat_laporan",
        "Membuat laporan (PDF, Excel, grafik PNG) dari data yang sudah Anda kumpulkan. Isi hanya dengan angka "
        "dari hasil alat lain; jangan mengarang data.",
        reports.REPORT_TOOL_SCHEMA, "report", "staff", _handler, "Membuat laporan"))
