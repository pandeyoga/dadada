import React, { useCallback, useState } from "react";
import { UserRound, Users, Gift, FileX2, MessageCircleQuestion, Send } from "lucide-react";
import { FrostCard } from "../../components/GlassCard";
import ListRow from "../../components/ListRow";
import StatusChip from "../../components/StatusChip";
import { askQuestion, listQuestions } from "../../services/api/buyer";
import { useProto } from "../../services/useStore";
import { tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import Page from "./Page";

const FAMILY = [
  { name: "Dimas Pratama", role: "Pasangan" },
  { name: "Alya Pratama", role: "Anak" },
];
const CATEGORIES = ["Administrasi", "Pembangunan", "KPR", "Pembayaran", "Lainnya"];
const TONE = { dibuat: "warn", diverifikasi: "info", dikerjakan: "info", selesai: "ok", dikonfirmasi: "ok" };

function QuestionForm() {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({ ok: false, text: "" });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await askQuestion({ category, description: text });
      setText("");
      setMsg({ ok: true, text: "Pertanyaan terkirim. Tim Estora akan membalas lewat aplikasi." });
    } catch (err) {
      setMsg({ ok: false, text: err.message });
    } finally {
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="mt-3 space-y-3">
      <label className="block text-[13.5px] font-semibold">
        Kategori
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="mt-1 block min-h-[46px] w-full rounded-xl border border-[color:var(--rdg-line)] bg-white px-3 text-[15px]">
          {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
        </select>
      </label>
      <label className="block text-[13.5px] font-semibold">
        Pertanyaan atau keluhan
        <textarea value={text} onChange={(e) => setText(e.target.value)} rows={3} placeholder="Contoh: Kapan jadwal akad KPR?" className="mt-1 block w-full rounded-xl border border-[color:var(--rdg-line)] bg-white p-3 text-[15px]" />
      </label>
      {msg.text && <p role={msg.ok ? "status" : "alert"} className={`text-[13.5px] font-semibold ${msg.ok ? "text-rdg-forest" : "text-[color:var(--rdg-sos-ink)]"}`}>{msg.text}</p>}
      <button type="submit" className="rdg-btn-primary w-full" disabled={busy}><Send size={17} aria-hidden="true" /> Kirim</button>
    </form>
  );
}

export default function BuyerAccount() {
  const world = useProto((s) => s.world);
  const fetcher = useCallback(() => listQuestions(), []);
  const { data: questions } = useLoad(fetcher);
  return (
    <Page id="P9" title="Akun" back="/app/pembeli" right={<StatusChip tone="info" icon={null}>Data contoh</StatusChip>}>
      <FrostCard>
        <div className="flex items-center gap-3">
          <span className="grid h-14 w-14 flex-none place-items-center rounded-2xl bg-rdg-lime text-[18px] font-extrabold text-rdg-ink900" aria-hidden="true">RA</span>
          <div className="min-w-0">
            <h2 className="text-[18px] font-extrabold">{world.resident.name}</h2>
            <p className="text-[13.5px] text-[color:var(--rdg-muted)]">{world.project.name} · Blok {world.unit.block} · Tipe {world.unit.type}</p>
          </div>
        </div>
        <dl className="mt-3 divide-y divide-[color:var(--rdg-line)] text-[14px]">
          {[["WhatsApp", world.resident.phone], ["Email", world.resident.email], ["Skema", world.unit.scheme]].map(([a, b]) => (
            <div key={a} className="flex justify-between gap-3 py-2"><dt className="text-[color:var(--rdg-muted)]">{a}</dt><dd className="font-semibold [overflow-wrap:anywhere] text-right">{b}</dd></div>
          ))}
        </dl>
      </FrostCard>

      <section aria-labelledby="p9-kel">
        <h2 id="p9-kel" className="mb-2 text-[17px] font-extrabold">Anggota keluarga</h2>
        <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
          {FAMILY.map((f) => <ListRow key={f.name} icon={Users} title={f.name} subtitle={f.role} />)}
        </FrostCard>
      </section>

      <section aria-labelledby="p9-tanya">
        <h2 id="p9-tanya" className="mb-2 text-[17px] font-extrabold">Tanya / komplain pra-serah terima</h2>
        <FrostCard>
          {questions && questions.length > 0 && (
            <ul className="divide-y divide-[color:var(--rdg-line)]">
              {questions.map((q) => (
                <li key={q.id} className="flex items-start justify-between gap-3 py-2.5">
                  <div className="min-w-0">
                    <p className="text-[14.5px] font-semibold leading-snug">{q.description}</p>
                    <p className="text-[12.5px] text-[color:var(--rdg-muted)]">{q.category} · {tanggal(q.history[0].at)}</p>
                  </div>
                  <StatusChip tone={TONE[q.status] || "neutral"}>{q.status.charAt(0).toUpperCase() + q.status.slice(1)}</StatusChip>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 flex items-center gap-2 text-[14px] font-bold"><MessageCircleQuestion size={18} aria-hidden="true" /> Kirim pertanyaan baru</p>
          <QuestionForm />
        </FrostCard>
      </section>

      <FrostCard className="divide-y divide-[color:var(--rdg-line)] !p-1">
        <ListRow icon={Gift} title="Ajak teman" subtitle="Kode dan hadiah rujukan" to="/app/ajak-teman" />
        <ListRow icon={FileX2} title="Pembatalan & refund" subtitle="Aturan dan status" to="/app/pembeli/pembatalan" />
        <ListRow icon={UserRound} title="Peta kavling" subtitle="Lokasi rumah Anda" to="/app/pembeli/kavling" />
      </FrostCard>
    </Page>
  );
}
