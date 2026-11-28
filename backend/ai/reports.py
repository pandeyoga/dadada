"""Laporan Estora AI: grafik PNG, PDF, dan XLSX sebagai artefak (`ai_artifacts`)."""
import asyncio
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Font  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # noqa: E402

import storage  # noqa: E402
from core_utils import new_id, now_iso  # noqa: E402
from db import db  # noqa: E402

PALETTE = ["#006284", "#007F83", "#01916F", "#209F59", "#49AE42"]
CT = {"pdf": "application/pdf", "png": "image/png",
      "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

_GRAFIK = {
    "type": "object", "additionalProperties": False,
    "required": ["jenis", "label", "seri"],
    "properties": {
        "jenis": {"type": "string", "enum": ["batang", "garis", "funnel", "pie"]},
        "label": {"type": "array", "items": {"type": "string"}},
        "seri": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["nama", "nilai"],
            "properties": {"nama": {"type": "string"},
                           "nilai": {"type": "array", "items": {"type": "number"}}}}},
    },
}
_TABEL = {
    "type": "object", "additionalProperties": False, "required": ["kolom", "baris"],
    "properties": {
        "kolom": {"type": "array", "items": {"type": "string"}},
        "baris": {"type": "array", "items": {"type": "array",
                  "items": {"type": ["string", "number", "boolean", "null"]}}},
    },
}
REPORT_TOOL_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["judul", "ringkasan", "bagian"],
    "properties": {
        "judul": {"type": "string"},
        "ringkasan": {"type": "string"},
        "bagian": {"type": "array", "items": {
            "type": "object", "additionalProperties": False, "required": ["judul"],
            "properties": {"judul": {"type": "string"}, "teks": {"type": "string"},
                           "tabel": _TABEL, "grafik": _GRAFIK}}},
    },
}


def _validate(spec: dict) -> None:
    for b in spec.get("bagian") or []:
        t = b.get("tabel")
        if t:
            n = len(t["kolom"])
            for r in t["baris"]:
                if len(r) != n:
                    raise ValueError(f"Jumlah kolom pada baris tabel '{b['judul']}' tidak sama dengan jumlah judul kolom.")
        g = b.get("grafik")
        if g:
            for s in g["seri"]:
                if len(s["nilai"]) != len(g["label"]):
                    raise ValueError(f"Panjang seri '{s['nama']}' pada grafik '{b['judul']}' tidak sama dengan jumlah label.")


def _chart_png(g: dict, title: str) -> bytes:
    fig, ax = plt.subplots(figsize=(7, 3.8), dpi=110)
    lab, series, kind = g["label"], g["seri"], g["jenis"]
    if kind == "batang":
        w = 0.8 / max(len(series), 1)
        for i, s in enumerate(series):
            ax.bar([x + i * w for x in range(len(lab))], s["nilai"], w, label=s["nama"], color=PALETTE[i % 5])
        ax.set_xticks([x + w * (len(series) - 1) / 2 for x in range(len(lab))])
        ax.set_xticklabels(lab)
    elif kind == "garis":
        for i, s in enumerate(series):
            ax.plot(lab, s["nilai"], marker="o", label=s["nama"], color=PALETTE[i % 5])
    elif kind == "funnel":
        vals = series[0]["nilai"] if series else []
        mx = max(vals) if vals else 1
        for i, v in enumerate(vals):
            ax.barh(len(vals) - 1 - i, v, left=(mx - v) / 2, color=PALETTE[i % 5])
            ax.text(mx / 2, len(vals) - 1 - i, f"{lab[i]}: {v:g}", ha="center", va="center", color="white", fontsize=9)
        ax.axis("off")
    else:
        vals = series[0]["nilai"] if series else []
        ax.pie(vals, labels=lab, colors=PALETTE, autopct="%1.0f%%", startangle=90)
    ax.set_title(title)
    if kind in ("batang", "garis") and len(series) > 1:
        ax.legend()
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def _pdf(spec: dict, charts: dict) -> bytes:
    st = getSampleStyleSheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title=spec["judul"])
    el = [Paragraph('<font color="#006284"><b>Estora</b></font>', st["Title"]),
          Paragraph(datetime.now().strftime("%d-%m-%Y"), st["Normal"]), Spacer(1, 12),
          Paragraph(spec["judul"], st["Heading1"]), Paragraph(spec.get("ringkasan", ""), st["BodyText"])]
    for i, b in enumerate(spec.get("bagian") or []):
        el.append(Paragraph(b["judul"], st["Heading2"]))
        if b.get("teks"):
            el.append(Paragraph(b["teks"], st["BodyText"]))
        if i in charts:
            el.append(Image(io.BytesIO(charts[i]), width=15 * cm, height=15 * cm * 3.8 / 7))
        if b.get("tabel"):
            t = b["tabel"]
            data = [t["kolom"]] + [["" if c is None else str(c) for c in r] for r in t["baris"]]
            tb = Table(data, repeatRows=1)
            tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PALETTE[0])),
                                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                    ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                    ("FONTSIZE", (0, 0), (-1, -1), 9)]))
            el.append(tb)

    def footer(c, d):
        c.setFont("Helvetica", 8)
        c.drawString(2 * cm, 1 * cm, "Dibuat oleh Estora AI")
        c.drawRightString(A4[0] - 2 * cm, 1 * cm, f"Halaman {d.page}")
    doc.build(el, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()


def _xlsx(spec: dict) -> bytes:
    wb = Workbook()
    wb.remove(wb.active)
    used = set()
    for b in spec.get("bagian") or []:
        t = b.get("tabel")
        if not t:
            continue
        name = "".join(ch for ch in b["judul"] if ch not in '[]:*?/\\')[:28] or "Tabel"
        base, n = name, 1
        while name in used:
            n += 1
            name = f"{base[:25]}_{n}"
        used.add(name)
        ws = wb.create_sheet(name)
        ws.append(t["kolom"])
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in t["baris"]:
            ws.append(r)
    if not wb.sheetnames:
        wb.create_sheet("Laporan").append([spec["judul"]])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def build_report(*, org_id: str, conversation_id: str | None, created_by: str, spec: dict) -> dict:
    _validate(spec)
    charts = {i: _chart_png(b["grafik"], b["judul"])
              for i, b in enumerate(spec.get("bagian") or []) if b.get("grafik")}
    pdf = await asyncio.to_thread(_pdf, spec, charts)
    xlsx = await asyncio.to_thread(_xlsx, spec)

    async def put(data, name, kind):
        rec = await storage.save_file(data=data, filename=name, content_type=CT[kind], org_id=org_id,
                                      owner_type="ai_artifact", owner_id=conversation_id or "na",
                                      uploaded_by=created_by, tag="ai_report", optimize=False)
        return rec["id"]

    base = "laporan"
    files = {"pdf": await put(pdf, f"{base}.pdf", "pdf"),
             "xlsx": await put(xlsx, f"{base}.xlsx", "xlsx"),
             "png": [await put(d, f"{base}-grafik-{n + 1}.png", "png") for n, d in enumerate(charts.values())]}
    doc = {"id": new_id(), "conversation_id": conversation_id, "title": spec["judul"],
           "files": files, "spec": spec, "created_by": created_by, "at": now_iso()}
    await db.ai_artifacts.insert_one(dict(doc))
    return doc


async def artifact_file(artifact_id: str, kind: str) -> tuple[bytes, str, str]:
    if kind not in CT:
        raise ValueError("Jenis berkas tidak dikenal.")
    art = await db.ai_artifacts.find_one({"id": artifact_id}, {"_id": 0})
    if not art:
        raise FileNotFoundError(artifact_id)
    fid = art["files"][kind] if kind != "png" else (art["files"]["png"] or [None])[0]
    if not fid:
        raise FileNotFoundError(f"{artifact_id}/{kind}")
    rec = await db.files.find_one({"id": fid}, {"_id": 0})
    data, _ = await storage.get_file_bytes(rec["storage_path"], rec.get("provider"))
    return data, CT[kind], rec["original_filename"]
