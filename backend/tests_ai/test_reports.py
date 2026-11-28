import asyncio
import io
import os
import sys

assert os.environ.get("MONGO_URL"), "set MONGO_URL"
os.environ["DB_NAME"] = "estora_ai_reports"
os.environ["STORAGE_PROVIDER"] = "mongo"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openpyxl import load_workbook  # noqa: E402
from ai import reports  # noqa: E402

ROWS = [["Januari", 10], ["Februari", 25]]
SPEC = {"judul": "Penjualan", "ringkasan": "Ringkas", "bagian": [{
    "judul": "Bulanan", "teks": "x",
    "tabel": {"kolom": ["Bulan", "Unit"], "baris": ROWS},
    "grafik": {"jenis": "batang", "label": ["Januari", "Februari"],
               "seri": [{"nama": "Unit", "nilai": [10, 25]}]}}]}


def test_report_files_created():
    async def run():
        art = await reports.build_report(org_id="org1", conversation_id="c1", created_by="u1", spec=SPEC)
        assert "_id" not in art
        pdf, ct, _ = await reports.artifact_file(art["id"], "pdf")
        assert pdf.startswith(b"%PDF") and ct == "application/pdf"
        x, _, _ = await reports.artifact_file(art["id"], "xlsx")
        ws = load_workbook(io.BytesIO(x)).worksheets[0]
        assert [list(r) for r in ws.iter_rows(min_row=2, values_only=True)] == ROWS
        assert ws["A1"].font.bold
        png, _, _ = await reports.artifact_file(art["id"], "png")
        assert png.startswith(b"\x89PNG\r\n\x1a\n")
        bad = {**SPEC, "bagian": [{"judul": "B", "grafik": {"jenis": "garis", "label": ["a"],
               "seri": [{"nama": "s", "nilai": [1, 2]}]}}]}
        try:
            await reports.build_report(org_id="org1", conversation_id=None, created_by="u1", spec=bad)
            raise AssertionError("harus ValueError")
        except ValueError:
            pass
    asyncio.run(run())
