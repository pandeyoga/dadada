"""Definisi setting grup `ai` — dipisah dari settings_store (batas 800 baris); digabung ke DEFAULTS."""

PRIVACY_NOTICE = (
    "Anda sedang berbicara dengan asisten AI Estora. Percakapan ini diproses otomatis untuk "
    "membantu menjawab pertanyaan Anda. Balas \"STOP\" atau \"HUBUNGI STAF\" kapan saja untuk "
    "berhenti dan dilayani oleh staf kami."
)
PORTAL_NOTICE = (
    "Anda sedang berbicara dengan Tanya Estora, asisten AI. Asisten hanya membaca data milik akun Anda "
    "(unit, tagihan, KPR, progres rumah, dokumen, garansi, dan komplain) untuk menjawab pertanyaan Anda; "
    "jawabannya bisa keliru dan keputusan resmi tetap dari tim kami. Tekan \"Bicara dengan CS\" kapan saja "
    "untuk diteruskan ke staf, atau pilih \"Berhenti pakai asisten\" di menu untuk berhenti."
)
# Kategori pesan WhatsApp yang boleh diatur modenya (kategori terkunci-ke-sales ada di ai/triage.py).
CATEGORIES = ("stok_harga", "simulasi_kpr", "lokasi_fasilitas", "jadwal_survei", "berkas_kpr",
              "tagihan_pembayaran", "progres_serah_terima", "komplain", "sapaan_umum")


def _d(key, value, type_, label, help_, *, minimum=None, maximum=None, sensitive=False, options=None):
    return {"key": key, "value": value, "type": type_, "group": "ai", "label": label,
            "help": help_, "impact": "", "sensitive": sensitive, "min": minimum, "max": maximum,
            "options": options or [], "source": "SISTEM", "ref_group": None}


DEFAULTS_AI: dict = {d["key"]: d for d in [
    _d("ai.mode", "simulation", "str", "Mode Estora AI", "off | simulation | live. Live hanya aktif bila kunci API tersimpan.",
       sensitive=True, options=["off", "simulation", "live"]),
    _d("ai.model_main", "claude-opus-5-5", "str", "Model utama", "Model untuk Copilot & agen WhatsApp."),
    _d("ai.model_triage", "claude-haiku-5-5", "str", "Model pemilah", "Model murah untuk triase/klasifikasi."),
    _d("ai.effort_copilot", "high", "str", "Effort Copilot", "low|medium|high|xhigh|max",
       options=["low", "medium", "high", "xhigh", "max"]),
    _d("ai.effort_wa", "medium", "str", "Effort agen WhatsApp", "low|medium|high|xhigh|max",
       options=["low", "medium", "high", "xhigh", "max"]),
    _d("ai.effort_triage", "low", "str", "Effort pemilah", "low|medium|high|xhigh|max",
       options=["low", "medium", "high", "xhigh", "max"]),
    _d("ai.budget_idr_month", 1500000, "money", "Anggaran AI per bulan (Rp)",
       "Peringatan admin di 80%, berhenti di 100%.", minimum=0, sensitive=True),
    _d("ai.usd_idr", 16000, "int", "Kurs USD-IDR untuk biaya AI", "Dipakai menghitung biaya Rupiah.", minimum=1),
    _d("ai.accuracy_threshold", 0.95, "pct", "Ambang akurasi untuk mode auto", "0-1.", minimum=0, maximum=1),
    _d("ai.accuracy_min_samples", 50, "int", "Minimum sampel akurasi", "Sampel terverifikasi sebelum auto boleh aktif.", minimum=1),
    _d("ai.accuracy_window_days", 30, "int", "Jendela akurasi (hari)", "", minimum=1),
    _d("ai.auto_sample_rate", 0.10, "pct", "Laju sampel audit mode auto", "0-1.", minimum=0, maximum=1),
    _d("ai.kpr_max_installment_ratio", 0.35, "pct", "Rasio maks cicilan KPR", "Cicilan / penghasilan.", minimum=0, maximum=1),
    _d("ai.web_research_enabled", False, "bool", "Riset web", "Izinkan AI mencari di web."),
    _d("ai.privacy_notice", PRIVACY_NOTICE, "str", "Pemberitahuan privasi AI", "Dikirim pada pesan pertama."),
    _d("ai.verification_ttl_days", 30, "int", "Masa berlaku verifikasi (hari)", "", minimum=1),
    _d("ai.category_modes", {c: "draft" for c in CATEGORIES}, "obj", "Mode per kategori",
       "kategori -> auto|draft|off."),
    _d("ai.portal_enabled", False, "bool", "Agen portal (Tanya Estora)",
       "Asisten AI untuk pembeli di portal. Mati sampai pemilik menyalakan.", sensitive=True),
    _d("ai.portal_daily_limit", 30, "int", "Batas pesan per pembeli per hari", "Agen portal; dihitung per hari (WIB).",
       minimum=1, maximum=500),
    _d("ai.portal_notice", PORTAL_NOTICE, "str", "Pemberitahuan agen portal", "Ditampilkan saat pembeli pertama kali membuka chat."),
]}
