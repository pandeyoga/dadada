import { useEffect, useState } from "react";
import axios, { API } from "../../services/apiClient";
import { Wand2, KeyRound, CheckCircle2, FlaskConical, PlugZap, AlertTriangle } from "lucide-react";
import KNSelect from "../../components/KNSelect";

// FB-01 — Panel Integrasi Gemini "Nano Banana Pro" (ilustrasi AI galeri desain). Admin only.
export default function GeminiIntegrationPanel() {
  const [cfg, setCfg] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("gemini-3-pro-image-preview");
  const [enabled, setEnabled] = useState(true);
  const [dailyLimit, setDailyLimit] = useState(10);
  const [testing, setTesting] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => { load(); }, []); // eslint-disable-line
  async function load() {
    try {
      const r = await axios.get(`${API}/admin/integrations`);
      const gm = r.data?.gemini || {};
      setCfg(gm); setModel(gm.model || "gemini-3-pro-image-preview"); setEnabled(gm.enabled !== false); setDailyLimit(gm.daily_limit || 10); setApiKey("");
    } catch (e) { setErr(e.response?.data?.detail || "Gagal memuat konfigurasi."); }
  }
  async function testConnection() {   // G-3
    setTesting(true); setErr(""); setMsg("");
    try {
      const r = await axios.post(`${API}/admin/integrations/gemini/test`);
      setMsg(`Uji koneksi LULUS — key valid (${r.data?.models_seen ?? 0} model terlihat). Status kini LIVE.`);
      await load();
    } catch (e) { setErr(e.response?.data?.detail || "Uji koneksi gagal."); await load(); }
    finally { setTesting(false); }
  }
  async function save({ clear = false } = {}) {
    setBusy(true); setErr(""); setMsg("");
    const payload = { gemini_model: model, gemini_enabled: enabled, gemini_daily_limit: Number(dailyLimit) || 10 };
    if (clear) payload.gemini_clear_key = true;
    else if (apiKey.trim()) payload.gemini_api_key = apiKey.trim();
    try {
      const r = await axios.put(`${API}/admin/integrations`, payload);
      const gm = r.data?.gemini || {};
      setCfg(gm); setModel(gm.model); setEnabled(gm.enabled !== false); setDailyLimit(gm.daily_limit || 10); setApiKey("");
      setMsg(clear ? "API key Gemini dihapus — kembali ke MODE DEMO." : (payload.gemini_api_key ? "Key tersimpan — jalankan \"Uji koneksi\" agar status menjadi LIVE." : "Konfigurasi Gemini tersimpan."));
    } catch (e) { setErr(e.response?.data?.detail || "Gagal menyimpan."); }
    finally { setBusy(false); }
  }

  const demo = !cfg?.has_key;
  const verified = !!cfg?.verified_at;
  const cost = Number(cfg?.cost_per_image_usd || 0.134);
  const modelOpts = (cfg?.models_available || ["gemini-3-pro-image-preview", "gemini-3.1-flash-image-preview"]).map((m) => ({ value: m, label: m }));

  return (
    <section className="section-card" data-testid="gemini-integration-panel">
      <div className="section-head flex items-center gap-2"><Wand2 size={15} className="text-[#5B2EA6]" /><h2 className="text-[13px] font-bold">Integrasi AI — Gemini Nano Banana Pro (Ilustrasi Galeri Desain)</h2></div>
      <div className="section-body">
        {!cfg && !err ? <p className="text-[12px] text-[#6B6B73] py-4">Memuat…</p> : (
          <div className="grid gap-3 max-w-[560px]">
            <div className={`flex items-center gap-2 rounded-lg px-3 py-2 text-[12px] font-semibold ${!enabled ? "bg-[#EDEEF1] text-[#6B6B73]" : !demo && verified ? "bg-[#E7F5EC] text-[#1F7A45]" : "bg-[#FBF3E2] text-[#B7791F]"}`} data-testid="gemini-status">
              {!enabled ? <FlaskConical size={15} /> : !demo && verified ? <CheckCircle2 size={15} /> : !demo ? <AlertTriangle size={15} /> : <FlaskConical size={15} />}
              {!enabled ? "NONAKTIF — ilustrasi AI dimatikan admin." : demo ? "BELUM DIKONFIGURASI — pembuatan gambar dinonaktifkan sampai key Gemini tersedia." : verified ? `KEY TERUJI — ${String(cfg.verified_at).slice(0, 16).replace("T", " ")}; hasil gambar tetap bergantung respons Gemini.` : "KEY TERSIMPAN, BELUM DIUJI — klik \"Uji koneksi\" untuk memastikan key valid sebelum dipakai."}
            </div>
            {err && <div className="notice-bar danger !py-1.5" data-testid="gemini-error"><span className="text-[11.5px]">{err}</span></div>}
            {msg && <div className="notice-bar success !py-1.5" data-testid="gemini-msg"><span className="text-[11.5px]">{msg}</span></div>}
            <div className="grid gap-1">
              <label className="text-[11px] font-bold uppercase text-[#6B6B73] flex items-center gap-1"><KeyRound size={12} /> Gemini API Key</label>
              <input data-testid="gemini-apikey" type="password" className="form-input" value={apiKey} onChange={(e) => setApiKey(e.target.value)}
                placeholder={!demo ? "•••• tersimpan — isi untuk mengganti" : "Masukkan Gemini API key (AIza…) dari aistudio.google.com"} />
              <p className="text-[10.5px] text-[#9A9BA3]">Key disimpan aman di server (atau lewat env <code>GEMINI_API_KEY</code>) & tidak pernah ditampilkan kembali.</p>
            </div>
            <div className="grid gap-1">
              <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Model</label>
              <KNSelect data-testid="gemini-model" value={model} onValueChange={setModel} options={modelOpts} className="field !w-[300px]" />
            </div>
            <div className="grid gap-1">
              <label className="text-[11px] font-bold uppercase text-[#6B6B73]">Batas ilustrasi per desain / SKU per hari</label>
              <div className="flex items-center gap-2">
                <input data-testid="gemini-daily-limit" type="number" min="1" max="200" className="form-input !w-[110px]" value={dailyLimit} onChange={(e) => setDailyLimit(e.target.value)} />
                <span className="text-[10.5px] text-[#9A9BA3]" data-testid="gemini-cost-estimate">Estimasi biaya saat LIVE ≈ US${cost.toFixed(3)}/gambar → maks ≈ US${(cost * (Number(dailyLimit) || 0)).toFixed(2)}/desain/hari (tarif Google, dapat berubah).</span>
              </div>
            </div>
            <label className="flex items-center gap-2 text-[12.5px] cursor-pointer">
              <input data-testid="gemini-enabled" type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} className="h-4 w-4 accent-[#5B2EA6]" />
              Aktifkan ilustrasi AI pada Galeri Desain & Varian Produk
            </label>
            <div className="flex items-center gap-2 pt-1">
              <button data-testid="gemini-save" className="btn-primary" onClick={() => save()} disabled={busy}>{busy ? "Menyimpan…" : "Simpan Konfigurasi"}</button>
              {!demo && <button data-testid="gemini-test" className="btn-secondary" onClick={testConnection} disabled={busy || testing}><PlugZap size={13} /> {testing ? "Menguji…" : "Uji koneksi"}</button>}
              {!demo && <button data-testid="gemini-clear" className="btn-secondary" onClick={() => save({ clear: true })} disabled={busy}>Hapus Key</button>}
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
