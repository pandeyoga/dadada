import React, { useEffect, useState } from "react";
import { saveSettings, friendlyError } from "../aiApi";

export default function PrivacyCard({ settings, onChanged }) {
  const [notice, setNotice] = useState("");
  const [ratio, setRatio] = useState("35");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  useEffect(() => {
    setNotice(settings?.privacy_notice || "");
    if (settings?.kpr_max_installment_ratio != null) setRatio(String(Math.round(settings.kpr_max_installment_ratio * 100)));
  }, [settings?.privacy_notice, settings?.kpr_max_installment_ratio]);

  const save = async () => {
    const r = Number(ratio);
    if (!(r > 0 && r <= 100)) { setMsg({ ok: false, text: "Rasio cicilan harus antara 1 dan 100%." }); return; }
    setBusy(true); setMsg(null);
    try {
      await saveSettings({ privacy_notice: notice, kpr_max_installment_ratio: r / 100 });
      setMsg({ ok: true, text: "Tersimpan." }); onChanged?.();
    } catch (e) { setMsg({ ok: false, text: friendlyError(e, "Gagal menyimpan.") }); }
    finally { setBusy(false); }
  };

  return (
    <section id="privasi" aria-labelledby="h-privasi" className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <h2 id="h-privasi" className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">Privasi &amp; simulasi KPR</h2>
      <label className="mt-3 flex flex-col gap-1 text-[13px] text-[#2B4744]">
        Teks pemberitahuan untuk kontak (disertakan pada balasan AI pertama)
        <textarea rows={3} value={notice} onChange={(e) => setNotice(e.target.value)}
          className="rounded-[10px] border border-[#C9D8D3] p-3 text-sm text-[#12312F]" />
      </label>
      <label className="mt-3 flex flex-wrap items-center gap-2 text-sm text-[#2B4744]">
        Rasio maksimum cicilan KPR terhadap gaji
        <input inputMode="numeric" value={ratio} onChange={(e) => setRatio(e.target.value)} aria-label="Rasio cicilan KPR (persen)"
          className="min-h-[40px] w-20 rounded-lg border border-[#C9D8D3] px-2 text-sm" /> %
      </label>
      <div className="mt-3">
        <button type="button" onClick={save} disabled={busy}
          className="min-h-[44px] rounded-[10px] bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Simpan</button>
      </div>
      {msg ? <p role={msg.ok ? "status" : "alert"} className={`mt-2 text-[13px] ${msg.ok ? "text-[#14532D]" : "text-[#9B1C1C]"}`}>{msg.text}</p> : null}
    </section>
  );
}
