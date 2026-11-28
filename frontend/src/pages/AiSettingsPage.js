import React, { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import AutonomyTable, { normalizeCategories } from "@/components/ai/settings/AutonomyTable";
import ChannelCards from "@/components/ai/settings/ChannelCards";
import BudgetCard from "@/components/ai/settings/BudgetCard";
import ApiKeyCard from "@/components/ai/settings/ApiKeyCard";
import PrivacyCard from "@/components/ai/settings/PrivacyCard";
import { getSettings, getAccuracy, getChannels, getUsage, saveSettings, friendlyError } from "@/components/ai/aiApi";

const NAV = [["otonomi", "Kemandirian agen"], ["kanal", "Kanal WhatsApp"], ["biaya", "Batas biaya"],
  ["kunci", "Kunci API"], ["privasi", "Privasi & data"]];

export default function AiSettingsPage() {
  const [settings, setSettings] = useState(null);
  const [cats, setCats] = useState([]);
  const [channels, setChannels] = useState(null);
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState([]);

  const load = useCallback(async () => {
    const [s, a, c, u] = await Promise.allSettled([getSettings(), getAccuracy(), getChannels(), getUsage()]);
    const n = [];
    if (s.status === "fulfilled") { setSettings(s.value); setError(""); } else setError(friendlyError(s.reason, "Gagal memuat pengaturan."));
    if (a.status === "fulfilled") setCats(normalizeCategories(a.value)); else n.push("Data akurasi belum tersedia.");
    if (c.status === "fulfilled") setChannels(c.value); else n.push("Pengaturan kanal belum tersedia.");
    if (u.status === "fulfilled") setUsage(u.value);
    setNotes(n);
  }, []);
  useEffect(() => { load(); }, [load]);

  const setThreshold = async (v) => {
    setSettings((s) => ({ ...s, accuracy_threshold: v }));
    try { await saveSettings({ accuracy_threshold: v }); load(); } catch (e) { setError(friendlyError(e)); }
  };

  return (
    <div className="-m-4 flex min-h-[calc(100vh-4rem)] flex-wrap bg-[#F4F7F6] font-[Inter,system-ui,sans-serif] text-[#12312F] md:-m-6" data-testid="ai-settings-page">
      <nav aria-label="Menu pengaturan" className="box-border flex flex-[0_1_240px] flex-col gap-1 border-r border-[#D5E0DC] bg-[#EAF1EF] px-3 py-4">
        <Link to="/ai" className="mb-2 inline-flex min-h-[40px] items-center gap-2 px-2 text-[13px] font-semibold text-[#006284] hover:text-[#00454D]">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Kembali ke Copilot
        </Link>
        <span className="px-2 pb-1 font-['Space_Grotesk',Inter,sans-serif] text-base font-bold">Pengaturan AI</span>
        {NAV.map(([id, l]) => (
          <a key={id} href={`#${id}`} className="min-h-[40px] rounded-lg px-2.5 py-2 text-sm text-[#12312F] hover:bg-[#DFE9E6]">{l}</a>
        ))}
      </nav>
      <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-5 p-6">
        {error ? <p role="alert" className="rounded-lg border border-[#E8C4C0] bg-[#FDF2F1] px-3 py-2 text-sm text-[#9B1C1C]">{error}</p> : null}
        {notes.map((n) => <p key={n} role="status" className="rounded-lg bg-[#FFF4E5] px-3 py-2 text-[13px] text-[#7A3E00]">{n}</p>)}
        {settings && settings.effective_mode !== "live" ? (
          <p role="status" className="rounded-lg border border-[#F2D7A6] bg-[#FFF4E5] px-3 py-2 text-[13px] text-[#7A3E00]"><b>Mode simulasi.</b> AI belum memakai Claude sungguhan.</p>
        ) : null}
        <AutonomyTable categories={cats} threshold={settings?.accuracy_threshold ?? 0.95}
          onThreshold={setThreshold} onChanged={load} />
        {channels ? <ChannelCards channels={channels} onChanged={load} /> : null}
        <BudgetCard settings={settings} usage={usage} onChanged={load} />
        <ApiKeyCard settings={settings} onChanged={load} />
        <PrivacyCard settings={settings} onChanged={load} />
      </main>
    </div>
  );
}
