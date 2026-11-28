import React, { useState } from "react";
import { KeyRound } from "lucide-react";
import { saveApiKey, testConnection, saveSettings, friendlyError } from "../aiApi";

const MODE_LABEL = { live: "Live (Claude sungguhan)", simulation: "Simulasi (data contoh)", off: "Mati" };

/** Kunci API TIDAK PERNAH ditampilkan utuh: hanya `has_key` + 4 karakter terakhir dari server. */
export default function ApiKeyCard({ settings, onChanged }) {
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState(null); // {ok, text}
  const last4 = String(settings?.key_last4 || settings?.api_key_last4 || "").slice(-4);

  const run = async (name, fn, okText) => {
    setBusy(name); setMsg(null);
    try { const r = await fn(); setMsg({ ok: r?.ok !== false, text: r?.message || okText }); onChanged?.(); return true; }
    catch (e) { setMsg({ ok: false, text: friendlyError(e, "Gagal diproses.") }); return false; }
    finally { setBusy(""); }
  };

  const save = async () => {
    const k = key.trim();
    if (!k) return;
    const ok = await run("save", () => saveApiKey(k), "Kunci API tersimpan.");
    if (ok) setKey("");
  };

  return (
    <section id="kunci" aria-labelledby="h-kunci" className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <h2 id="h-kunci" className="m-0 flex items-center gap-2 font-['Space_Grotesk',Inter,sans-serif] text-xl">
        <KeyRound className="h-5 w-5 text-[#006284]" aria-hidden="true" /> Kunci API Claude
      </h2>
      <p className="mt-2 text-sm text-[#2B4744]" data-testid="key-status">
        {settings?.has_key ? <>Kunci tersimpan: <code className="rounded bg-[#EEF3F1] px-1.5 py-0.5">{"••••••••" + last4}</code></> : "Belum ada kunci API."}
      </p>
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <label className="flex min-w-[240px] flex-1 flex-col gap-1 text-[13px] text-[#2B4744]">
          {settings?.has_key ? "Ganti kunci API" : "Tempel kunci API"}
          <input type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)}
            placeholder="sk-ant-…" className="min-h-[44px] rounded-[10px] border border-[#C9D8D3] px-3 text-sm text-[#12312F]" />
        </label>
        <button type="button" onClick={save} disabled={!key.trim() || !!busy}
          className="min-h-[44px] rounded-[10px] bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Simpan kunci</button>
        <button type="button" onClick={() => run("test", testConnection, "Koneksi berhasil.")} disabled={!!busy}
          className="min-h-[44px] rounded-[10px] border border-[#B9CFC8] bg-white px-4 text-sm font-semibold text-[#12312F] disabled:opacity-60">Tes koneksi</button>
      </div>
      <label className="mt-4 flex flex-wrap items-center gap-2 text-sm text-[#2B4744]">
        Mode
        <select value={settings?.mode || "simulation"} disabled={!!busy}
          onChange={(e) => run("mode", () => saveSettings({ mode: e.target.value }), "Mode disimpan.")}
          className="min-h-[40px] rounded-lg border border-[#C9D8D3] bg-white px-2 text-sm font-semibold text-[#12312F]">
          {Object.entries(MODE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <span className="text-xs text-[#3E5653]">Mode efektif saat ini: {MODE_LABEL[settings?.effective_mode] || settings?.effective_mode || "—"}</span>
      </label>
      {settings?.effective_mode && settings.effective_mode !== "live" ? (
        <p className="mt-2 text-[13px] text-[#7A3E00]">Mode simulasi: AI belum memanggil Claude sungguhan, jawabannya data contoh.</p>
      ) : null}
      {msg ? <p role={msg.ok ? "status" : "alert"} className={`mt-2 text-[13px] ${msg.ok ? "text-[#14532D]" : "text-[#9B1C1C]"}`}>{msg.text}</p> : null}
    </section>
  );
}
