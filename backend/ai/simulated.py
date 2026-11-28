"""SimulatedClaude — demo UI tanpa kunci API: deterministik berbasis kata kunci pesan terakhir."""
import json
import re
from datetime import datetime, timedelta, timezone

from core_utils import new_id

NOTICE = ("Mode simulasi: kunci API Anthropic belum dipasang, jadi ini jawaban contoh otomatis, "
          "bukan hasil analisis AI sungguhan.")


def _last(messages: list):
    m = messages[-1] if messages else {"content": ""}
    c = m.get("content")
    if isinstance(c, str):
        return c.lower(), []
    text = " ".join(b.get("text", "") for b in c if b.get("type") == "text").lower()
    return text, [b for b in c if b.get("type") == "tool_result"]


SAMPLE_REPORT = {
    "judul": "Laporan funnel penjualan (contoh simulasi)",
    "ringkasan": "Data contoh untuk demo tampilan; bukan data sebenarnya.",
    "bagian": [{"judul": "Funnel", "teks": "Contoh jumlah prospek per tahap.",
                "tabel": {"kolom": ["Tahap", "Jumlah"], "baris": [["Baru", 40], ["Survei", 18], ["Booking", 6]]},
                "grafik": {"jenis": "funnel", "label": ["Baru", "Survei", "Booking"],
                           "seri": [{"nama": "Jumlah", "nilai": [40, 18, 6]}]}}],
}


# Pemilah simulasi: kata kunci -> kategori (urutan = prioritas). Kepercayaan tetap 0.8.
TRIAGE_KEYWORDS = (
    ("komplain", ("komplain", "rusak", "bocor")),
    ("diskon_nego", ("nego", "diskon")),
    ("tagihan_pembayaran", ("tagihan", "va ", "bayar")),
    ("simulasi_kpr", ("cicil", "kpr", "gaji")),
    ("jadwal_survei", ("survei", "survey", "jadwal")),
    ("stok_harga", ("harga", "unit", "tipe")),
    ("lokasi_fasilitas", ("lokasi", "alamat")),
    ("sapaan_umum", ("halo", "pagi", "siang")),
)
PORTAL_KEYWORDS = (("tagihan", "tagihan_saya"), ("progres", "progres_rumah_saya"))
SIM_DRAFT = "[Draf simulasi, bukan AI sungguhan] Terima kasih sudah menghubungi kami. Tim kami akan membantu Anda segera."


def _triage_json(text: str) -> str:
    t = (text.split("pesan terakhir pelanggan:")[-1] + " ")
    cat = next((c for c, kws in TRIAGE_KEYWORDS if any(k in t for k in kws)), "lainnya_tidak_yakin")
    return json.dumps({"category": cat, "intent": "Pelanggan bertanya (simulasi)", "objections": [],
                       "sentiment": "netral", "confidence": 0.8})


def _tool(name: str, inp: dict) -> dict:
    return {"type": "tool_use", "id": "toolu_sim_" + new_id()[:12], "name": name, "input": inp}


class SimulatedClaude:
    def __init__(self, org_id: str = None):
        self.org_id = org_id

    async def _portal(self, text, results, names, on_text):
        """Agen portal tanpa kunci: 'tagihan' -> tagihan_saya, 'progres' -> progres_rumah_saya, selain itu teks jujur."""
        if not results:
            for kw, tool in PORTAL_KEYWORDS:
                if kw in text and tool in names:
                    return self._resp([_tool(tool, {})], "tool_use")
            msg = f"{NOTICE} Coba tanyakan tagihan atau progres rumah Anda untuk melihat contoh alurnya."
        else:
            msg = f"{NOTICE} Data akun Anda sudah dibaca; ringkasan sebenarnya akan ditulis AI setelah kunci API dipasang."
        if on_text:
            await on_text(msg)
        return self._resp([{"type": "text", "text": msg}], "end_turn")

    def _resp(self, content, stop):
        return {"content": content, "stop_reason": stop, "stop_details": None, "model": "simulated",
                "usage": {"input_tokens": 0, "output_tokens": 0}}

    async def turn(self, *, model, system, messages, tools, effort, max_tokens, on_text, context,
                   output_format=None) -> dict:
        text, results = _last(messages)
        if output_format:  # pemilah WA: JSON deterministik sesuai skema
            return self._resp([{"type": "text", "text": _triage_json(text)}], "end_turn")
        names = {t.get("name") for t in tools or []}
        prior = [b.get("name") for m in messages if isinstance(m.get("content"), list)
                 for b in m["content"] if b.get("type") == "tool_use"]
        if (context or {}).get("channel") == "portal":
            return await self._portal(text, results, names, on_text)
        if results:
            if "funnel_penjualan" in prior and "buat_laporan" not in prior and "buat_laporan" in names:
                return self._resp([_tool("buat_laporan", SAMPLE_REPORT)], "tool_use")
            if "cari_lead" in prior and "jadwalkan_survei" not in prior and "jadwalkan_survei" in names:
                m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", json.dumps([r.get("content") for r in results]))
                if m:
                    waktu = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT10:00:00")
                    return self._resp([_tool("jadwalkan_survei", {"lead_id": m.group(0), "waktu": waktu,
                                                                  "catatan": "Usulan simulasi"})], "tool_use")
            done = "Laporan simulasi sudah dibuat." if "buat_laporan" in prior else "Usulan simulasi sudah disiapkan; periksa kartu persetujuan."
            out = [{"type": "text", "text": f"{NOTICE} {done}"}]
        elif ("laporan" in text or "funnel" in text) and "funnel_penjualan" in names:
            return self._resp([_tool("funnel_penjualan", {})], "tool_use")
        elif "jadwalkan" in text and "cari_lead" in names and "jadwalkan_survei" in names:
            return self._resp([_tool("cari_lead", {"batas": 1})], "tool_use")
        elif (context or {}).get("channel") in ("wa", "whatsapp") or (context or {}).get("purpose") == "rewrite":
            out = [{"type": "text", "text": SIM_DRAFT}]
        else:
            out = [{"type": "text", "text": NOTICE}]
        if on_text:
            await on_text(out[0]["text"])
        return self._resp(out, "end_turn")
