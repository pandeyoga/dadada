import React, { useEffect, useState } from "react";
import { saveSettings, friendlyError } from "../aiApi";

const rp = (n) => `Rp${Math.round(Number(n) || 0).toLocaleString("id-ID")}`;

export default function BudgetCard({ settings, usage, onChanged }) {
  const [limit, setLimit] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  useEffect(() => { setLimit(String(settings?.budget_idr_month ?? "")); }, [settings?.budget_idr_month]);

  const spent = usage?.spent_idr ?? 0;
  const lim = usage?.limit_idr ?? settings?.budget_idr_month ?? 0;
  const ratio = lim ? spent / lim : 0;
  const state = usage?.state || (ratio >= 1 ? "stop" : ratio >= 0.8 ? "warn" : "ok");
  const color = state === "stop" ? "#9B1C1C" : state === "warn" ? "#B45309" : "#209F59";

  const save = async () => {
    const n = Number(String(limit).replace(/\D/g, ""));
    if (!n) { setMsg({ ok: false, text: "Isi batas dengan angka rupiah." }); return; }
    setBusy(true); setMsg(null);
    try { await saveSettings({ budget_idr_month: n }); setMsg({ ok: true, text: "Batas disimpan." }); onChanged?.(); }
    catch (e) { setMsg({ ok: false, text: friendlyError(e, "Batas gagal disimpan.") }); }
    finally { setBusy(false); }
  };

  return (
    <section id="biaya" aria-labelledby="h-biaya" className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <h2 id="h-biaya" className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">Batas biaya bulanan</h2>
      <div className="mt-3 flex flex-wrap items-end gap-2">
        <label className="flex flex-col gap-1 text-[13px] text-[#2B4744]">
          Batas (Rp)
          <input inputMode="numeric" value={limit} onChange={(e) => setLimit(e.target.value)} aria-label="Batas biaya bulanan"
            className="min-h-[44px] w-56 rounded-[10px] border border-[#C9D8D3] px-3 text-sm text-[#12312F]" />
        </label>
        <button type="button" onClick={save} disabled={busy}
          className="min-h-[44px] rounded-[10px] bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Simpan batas</button>
      </div>
      <div className="mt-4" role="progressbar" aria-label="Pemakaian anggaran" aria-valuemin={0} aria-valuemax={100}
        aria-valuenow={Math.min(100, Math.round(ratio * 100))}>
        <div className="h-3 overflow-hidden rounded-full bg-[#EEF3F1]">
          <div className="h-full rounded-full" style={{ width: `${Math.min(100, ratio * 100)}%`, background: color }} />
        </div>
      </div>
      <p className="mt-2 text-[13px] text-[#3E5653]">
        Terpakai bulan ini: <b>{rp(spent)}</b> dari {rp(lim)} ({Math.round(ratio * 100)}%) · Peringatan di 80%, agen otomatis berhenti di 100% (Copilot tetap jalan untuk admin).
      </p>
      {msg ? <p role={msg.ok ? "status" : "alert"} className={`text-[13px] ${msg.ok ? "text-[#14532D]" : "text-[#9B1C1C]"}`}>{msg.text}</p> : null}
    </section>
  );
}
