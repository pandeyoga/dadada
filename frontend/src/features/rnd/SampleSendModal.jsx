/**
 * SampleSendModal — mode "send": kirim permintaan ke beberapa supplier × beberapa JENIS (round 1 per kombinasi);
 * mode "round": buka round berikutnya untuk satu supplier pada SATU jenis setelah hasil `revisi`
 * (melewati `rnd.max_rounds` wajib alasan — server yang menegakkan; kuota per supplier × jenis).
 */
import KNDatePicker from "@/components/KNDatePicker";
import { useEffect, useMemo, useState } from "react";
import { Plus, Search, Send } from "lucide-react";
import FormModal from "../../components/FormModal";
import axios, { API } from "@/services/apiClient";
import { errMsg } from "./rndMeta";
import { Field, Footer, Hint } from "./RndField";
import { roundTypeOf, sampleTypesOf, typeLabel } from "./sampleTypeMeta";

// Daftar supplier hidup DI SINI (bukan rndApi.js) — modul bersama itu dipakai layar desainer tanpa izin supplier.view.
const listSuppliers = (params) => axios.get(`${API}/suppliers`, { params }).then((r) => r.data);

export default function SampleSendModal({ mode = "send", sample, participant, typeCode, types, policy, onClose, onConfirm, busy }) {
  const [suppliers, setSuppliers] = useState([]);
  const [picked, setPicked] = useState([]);
  const [q, setQ] = useState("");
  const [due, setDue] = useState("");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState("");
  const [err, setErr] = useState("");
  const isSend = mode === "send";
  const kinds = useMemo(() => sampleTypesOf(sample), [sample]);
  const [pickedTypes, setPickedTypes] = useState(kinds);
  useEffect(() => { setPickedTypes(kinds); }, [kinds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!isSend) return;
    listSuppliers({ limit: 500 }).then((r) => setSuppliers(Array.isArray(r) ? r : r?.items || []))
      .catch((e) => setErr(errMsg(e, "Gagal memuat daftar supplier.")));
  }, [isSend]);

  const covered = useMemo(() => {
    const set = new Set();
    (sample?.rounds || []).forEach((r) => set.add(`${r.supplier_id}|${roundTypeOf(r, sample)}`));
    return set;
  }, [sample]);
  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    return suppliers.filter((s) => !term || `${s.name || ""}${s.code || ""}${s.city || ""}`.toLowerCase().includes(term));
  }, [suppliers, q]);
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const toggleType = (c) => setPickedTypes((p) => (p.includes(c) ? p.filter((x) => x !== c) : [...p, c]));

  const roundsOfPartner = (sample?.rounds || []).filter((r) => r.supplier_id === participant?.supplier_id && roundTypeOf(r, sample) === typeCode);
  const nextNo = roundsOfPartner.length + 1;
  const maxRounds = Number(policy?.max_rounds || 3);
  const overLimit = nextNo > maxRounds;
  const newRounds = picked.reduce((acc, sid) => acc + pickedTypes.filter((t) => !covered.has(`${sid}|${t}`)).length, 0);

  const disabled = isSend ? (picked.length === 0 || pickedTypes.length === 0) : (overLimit && !reason.trim());
  const confirm = () => (isSend
    ? onConfirm({ supplier_ids: picked, type_codes: pickedTypes, due_date: due, note })
    : onConfirm({ supplier_id: participant?.supplier_id, type_code: typeCode, due_date: due, note, reason }));

  return (
    <FormModal open onClose={onClose} size="md" testId="sample-send-modal" icon={isSend ? Send : Plus} error={err}
      title={isSend ? "Kirim Permintaan ke Supplier" : `Buka round ${nextNo} · ${typeLabel(typeCode, types)}`}
      subtitle={isSend ? `${sample?.number} · round 1 dibuka untuk tiap supplier × jenis` : `${participant?.supplier_name || ""} · ${sample?.number}`}
      footer={<Footer onClose={onClose} onConfirm={confirm} busy={busy} disabled={disabled} icon={isSend ? Send : Plus} testId="sample-send-confirm"
        confirmLabel={isSend ? `Kirim · ${newRounds} round` : `Buka round ${nextNo}`} />}>
      <div className="grid gap-3">
        {isSend ? (
          <>
            <Hint>Pilih <b>lebih dari satu supplier</b> bila ingin membandingkan hasil, dan <b>jenis mana saja</b> yang dikirim sekarang. Setiap kombinasi supplier × jenis mendapat round 1 sendiri dengan tenggat yang sama.</Hint>
            <div>
              <p className="mb-1 text-[10.5px] font-semibold text-[#6B6B73]">Jenis yang dikirim sekarang</p>
              <div className="flex flex-wrap gap-1.5" data-testid="sample-send-types">
                {kinds.map((c) => {
                  const on = pickedTypes.includes(c);
                  return (
                    <button key={c} type="button" onClick={() => toggleType(c)} data-testid={`sample-send-type-${c}`}
                      className={`rounded-full border px-3 py-1 text-[11px] font-medium transition-colors ${on ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#0058CC]"}`}>
                      {typeLabel(c, types)}
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <p className="mb-1 text-[10.5px] font-semibold text-[#6B6B73]">Supplier tujuan *</p>
              <div className="relative">
                <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
                <input className="field !pl-8" data-testid="sample-send-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Cari supplier…" />
              </div>
              <div className="mt-1.5 max-h-[240px] divide-y divide-[#F4F5F7] overflow-y-auto rounded-lg border border-[#EFF0F2]" data-testid="sample-send-supplier-list">
                {filtered.length === 0 && <p className="px-3 py-6 text-center text-[11.5px] text-[#6B6B73]">Tidak ada supplier yang cocok.</p>}
                {filtered.map((s) => {
                  const done = pickedTypes.length > 0 && pickedTypes.every((t) => covered.has(`${s.id}|${t}`));
                  const on = picked.includes(s.id);
                  const partial = pickedTypes.filter((t) => covered.has(`${s.id}|${t}`)).length;
                  return (
                    <button key={s.id} type="button" disabled={done} data-testid={`sample-send-supplier-${s.id}`} onClick={() => toggle(s.id)}
                      className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left ${done ? "cursor-not-allowed bg-[#FAFBFC] opacity-60" : on ? "bg-[#EFF4FF]" : "hover:bg-[#FAFBFC]"}`}>
                      <span className="min-w-0">
                        <span className="block truncate text-[12px] font-semibold">{s.name}</span>
                        <span className="block truncate text-[10.5px] text-[#6B6B73]">{s.code || "—"}{s.city ? ` · ${s.city}` : ""}{!done && partial > 0 ? ` · ${partial} jenis sudah berjalan` : ""}</span>
                      </span>
                      <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-bold ${done ? "border-[#E5E5EA] text-[#8E8E93]" : on ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#E5E5EA] text-[#6B6B73]"}`}>
                        {done ? "sudah semua jenis" : on ? "dipilih" : "pilih"}
                      </span>
                    </button>
                  );
                })}
              </div>
              <p className="mt-1.5 text-[11px] text-[#6B6B73]" data-testid="sample-send-count">
                {picked.length} supplier × {pickedTypes.length} jenis → <b>{newRounds} round baru</b> akan dibuka.
              </p>
            </div>
          </>
        ) : (
          <Hint tone={overLimit ? "warn" : "info"} testId="sample-round-limit-note">
            {overLimit
              ? <>Round {nextNo} jenis <b>{typeLabel(typeCode, types)}</b> MELEWATI batas {maxRounds} iterasi. Hanya manager/admin yang boleh membukanya dan alasan tertulis WAJIB (batas diubah di Pusat Pengaturan → R&amp;D &amp; Desain).</>
              : <>Round {nextNo} dari batas {maxRounds} iterasi untuk jenis <b>{typeLabel(typeCode, types)}</b>. Kuota dihitung per jenis — perbaikan warna tidak menghabiskan kuota perbaikan handfeel.</>}
          </Hint>
        )}
        <div className="grid gap-2.5 sm:grid-cols-2">
          <Field label={`Tenggat round (kosong = SLA ${policy?.round_sla_days || 7} hari)`}>
            <KNDatePicker data-testid="sample-send-due" value={due} onChange={setDue} />
          </Field>
          <Field label="Catatan untuk supplier">
            <input className="field" data-testid="sample-send-note" value={note} onChange={(e) => setNote(e.target.value)} placeholder="mis. kirim swatch 3 meter" />
          </Field>
        </div>
        {!isSend && (
          <Field label={`Alasan round tambahan${overLimit ? " *" : " (opsional)"}`}>
            <input className="field" data-testid="sample-round-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="mis. pelanggan minta warna sedikit lebih muda" />
          </Field>
        )}
      </div>
    </FormModal>
  );
}
