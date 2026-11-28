import React, { useEffect, useState } from "react";
import { saveSettings, friendlyError } from "../aiApi";

/** Kartu "Asisten portal pembeli": saklar, batas pesan harian, teks pemberitahuan, pemakaian. */
export default function PortalAgentCard({ settings, usage, onChanged }) {
  const [enabled, setEnabled] = useState(false);
  const [limit, setLimit] = useState("30");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    setEnabled(!!settings?.portal_enabled);
    setLimit(String(settings?.portal_daily_limit ?? 30));
    setNotice(settings?.portal_notice ?? "");
  }, [settings?.portal_enabled, settings?.portal_daily_limit, settings?.portal_notice]);

  const save = async (patch, okText) => {
    setBusy(true); setMsg(null);
    try { await saveSettings(patch); setMsg({ ok: true, text: okText }); onChanged?.(); }
    catch (e) { setMsg({ ok: false, text: friendlyError(e, "Pengaturan gagal disimpan.") }); }
    finally { setBusy(false); }
  };

  const toggle = (v) => { setEnabled(v); save({ portal_enabled: v }, v ? "Asisten portal diaktifkan." : "Asisten portal dimatikan."); };
  const saveDetails = () => {
    const n = Number(String(limit).replace(/\D/g, ""));
    if (!n) { setMsg({ ok: false, text: "Isi batas pesan dengan angka." }); return; }
    save({ portal_daily_limit: n, portal_notice: notice }, "Pengaturan disimpan.");
  };

  const ch = usage?.by_channel?.portal;
  // Backend: by_channel = {web, wa, portal} dalam rupiah (angka). Bentuk objek tetap dibaca bila ada.
  const spent = ch == null ? null : (typeof ch === "object" ? ch.spent_idr ?? ch.cost_idr : ch);
  const used = ch && typeof ch === "object" ? ch.messages ?? ch.count ?? ch.calls : null;

  return (
    <section id="portal" aria-labelledby="h-portal" data-testid="portal-agent-card"
      className="rounded-2xl border border-[#D5E0DC] bg-white p-5">
      <h2 id="h-portal" className="m-0 font-['Space_Grotesk',Inter,sans-serif] text-xl">Asisten portal pembeli</h2>
      <p className="mt-1 text-[13px] text-[#3E5653]">
        &ldquo;Tanya Estora&rdquo; menjawab pertanyaan pembeli di Portal Pembeli dan hanya membaca data pembeli itu sendiri.
        Komplain baru selalu menunggu konfirmasi pembeli; topik harga, diskon, dan sengketa diserahkan ke CS.
      </p>
      <label className="mt-3 flex min-h-[44px] items-center gap-2 text-sm">
        <input type="checkbox" role="switch" checked={enabled} disabled={busy}
          onChange={(e) => toggle(e.target.checked)} aria-label="Aktifkan asisten portal" className="h-5 w-5" />
        Aktifkan asisten di Portal Pembeli
      </label>
      <div className="mt-2 flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[13px] text-[#2B4744]">
          Batas pesan per pembeli per hari
          <input inputMode="numeric" value={limit} onChange={(e) => setLimit(e.target.value)} aria-label="Batas pesan harian"
            className="min-h-[44px] w-40 rounded-[10px] border border-[#C9D8D3] px-3 text-sm text-[#12312F]" />
        </label>
      </div>
      <label className="mt-3 flex flex-col gap-1 text-[13px] text-[#2B4744]">
        Teks pemberitahuan pertama (ditampilkan sekali kepada pembeli)
        <textarea value={notice} onChange={(e) => setNotice(e.target.value)} rows={3} aria-label="Teks pemberitahuan portal"
          className="rounded-[10px] border border-[#C9D8D3] px-3 py-2 text-sm text-[#12312F]" />
      </label>
      <button type="button" onClick={saveDetails} disabled={busy}
        className="mt-3 min-h-[44px] rounded-[10px] bg-[#006284] px-4 text-sm font-semibold text-white hover:bg-[#00454D] disabled:opacity-60">Simpan</button>
      <p className="mt-3 text-[13px] text-[#3E5653]" data-testid="portal-agent-usage">
        Biaya AI bulan ini lewat portal: {spent != null ? <b>Rp{Math.round(Number(spent) || 0).toLocaleString("id-ID")}</b> : "belum ada data"}
        {used != null ? ` · ${Number(used).toLocaleString("id-ID")} pesan` : ""}
      </p>
      {msg ? <p role={msg.ok ? "status" : "alert"} className={`text-[13px] ${msg.ok ? "text-[#14532D]" : "text-[#9B1C1C]"}`}>{msg.text}</p> : null}
    </section>
  );
}
