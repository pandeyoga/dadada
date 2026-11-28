"""SimulatedClaude — demo UI tanpa kunci API: deterministik berbasis kata kunci pesan terakhir."""
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


def _tool(name: str, inp: dict) -> dict:
    return {"type": "tool_use", "id": "toolu_sim_" + new_id()[:12], "name": name, "input": inp}


class SimulatedClaude:
    def __init__(self, org_id: str = None):
        self.org_id = org_id

    def _resp(self, content, stop):
        return {"content": content, "stop_reason": stop, "stop_details": None, "model": "simulated",
                "usage": {"input_tokens": 0, "output_tokens": 0}}

    async def turn(self, *, model, system, messages, tools, effort, max_tokens, on_text, context,
                   output_format=None) -> dict:
        text, results = _last(messages)
        names = {t.get("name") for t in tools or []}
        prior = [b.get("name") for m in messages if isinstance(m.get("content"), list)
                 for b in m["content"] if b.get("type") == "tool_use"]
        if results:
            if "funnel_penjualan" in prior and "buat_laporan" not in prior and "buat_laporan" in names:
                return self._resp([_tool("buat_laporan", SAMPLE_REPORT)], "tool_use")
            out = [{"type": "text", "text": NOTICE + " Laporan simulasi sudah dibuat."}]
        elif ("laporan" in text or "funnel" in text) and "funnel_penjualan" in names:
            return self._resp([_tool("funnel_penjualan", {})], "tool_use")
        elif "jadwalkan" in text and "jadwalkan_survei" in names:
            return self._resp([_tool("jadwalkan_survei", {"catatan": text[:200]})], "tool_use")
        else:
            out = [{"type": "text", "text": NOTICE}]
        if on_text:
            await on_text(out[0]["text"])
        return self._resp(out, "end_turn")
