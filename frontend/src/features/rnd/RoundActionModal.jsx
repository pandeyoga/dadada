/**
 * RoundActionModal — dua peran: "submit" (setor hasil round: catatan + hasil ukur dinamis dari master
 * jenis + biaya; lampiran WAJIB sudah diunggah) dan "assess" (nilai hasil: acc | revisi | tolak + skor).
 */
import { useMemo, useState } from "react";
import MoneyInput from "@/components/MoneyInput";
import { CheckCircle2, Save } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import { Field, Footer, Hint } from "./RndField";
import { measurementFieldsOf, measurementMeta, typeLabel } from "./sampleTypeMeta";

const RESULT_OPTS = [
  { value: "acc", label: "ACC — diterima (wajib skor)" },
  { value: "revisi", label: "Revisi — minta perbaikan (round berikutnya)" },
  { value: "tolak", label: "Tolak — supplier tidak dilanjutkan" },
];

export default function RoundActionModal({ mode, round, types, measurements, onClose, onConfirm, busy }) {
  const isSubmit = mode === "submit";
  const typeCode = String(round?.type_code || "").toLowerCase();
  const fields = useMemo(() => measurementFieldsOf(typeCode, types), [typeCode, types]);
  const [note, setNote] = useState("");
  const [cost, setCost] = useState("");
  const [result, setResult] = useState("acc");
  const [score, setScore] = useState("");
  const [m, setM] = useState({});
  const setMeas = (k, v) => setM((p) => ({ ...p, [k]: v }));
  const nAttach = (round?.attachments || []).length;
  const missing = fields.filter((f) => String(m[f] ?? "").trim() === "");

  const confirm = () => {
    if (isSubmit) {
      onConfirm({ note, cost: cost || 0, measurements: Object.fromEntries(fields.map((k) => [k, String(m[k] ?? "").trim() === "" ? null : m[k]])) });
    } else {
      onConfirm({ result, score: score === "" ? null : score, note });
    }
  };

  return (
    <FormModal open onClose={onClose} size="md" testId="round-action-modal" icon={isSubmit ? Save : CheckCircle2}
      title={isSubmit ? `Setor hasil rnd ${round?.round_no}` : `Nilai hasil rnd ${round?.round_no}`}
      subtitle={`${typeLabel(typeCode, types)} · ${round?.supplier_name || ""}`}
      footer={<Footer onClose={onClose} onConfirm={confirm} busy={busy} icon={Save} testId="round-modal-confirm"
        confirmLabel={isSubmit ? "Setor hasil" : "Simpan penilaian"} disabled={isSubmit && !note.trim()} />}>
      <div className="grid gap-3">
        <span className="hidden" data-testid="round-modal-context">{typeLabel(typeCode, types)} · {round?.supplier_name}</span>
        {isSubmit ? (
          <>
            <Hint tone={nAttach ? "ok" : "warn"} testId="round-attach-hint">
              {nAttach ? `${nAttach} bukti sudah terunggah — hasil boleh disetor.`
                : "Belum ada bukti terunggah. Unggah minimal 1 berkas (foto hasil / artwork / hasil ukur) di baris round sebelum menyetor — server akan menolaknya."}
            </Hint>
            <Field label="Catatan / penjelasan hasil *">
              <textarea className="field" rows={3} data-testid="round-note-input" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="mis. Warna sedikit lebih tua dari target, handfeel bagus" />
            </Field>
            {fields.length === 0 ? (
              <p className="text-[11.5px] text-[#6B6B73]" data-testid="round-meas-none">Jenis ini tidak meminta hasil ukur — cukup catatan &amp; bukti.</p>
            ) : (
              <div className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-3">
                <p className="mb-2 text-[10.5px] font-bold uppercase tracking-wide text-[#8E8E93]">Hasil ukur · {typeLabel(typeCode, types)}</p>
                <div className="grid gap-2.5 sm:grid-cols-3" data-testid="round-meas-fields">
                  {fields.map((key) => {
                    const meta = measurementMeta(key, measurements);
                    return (
                      <Field key={key} label={`${meta.label}${meta.unit ? ` (${meta.unit})` : ""} *`}>
                        <input className="field" data-testid={`round-meas-${key}`} value={m[key] ?? ""} title={meta.hint || ""}
                          onChange={(e) => setMeas(key, e.target.value)} placeholder={meta.min != null ? `${meta.min}–${meta.max}` : ""} />
                      </Field>
                    );
                  })}
                  <Field label="Biaya sample (Rp)">
                    <MoneyInput className="field" testId="round-cost-input" value={cost} onChange={(v) => setCost(v)} placeholder="150000" />
                  </Field>
                </div>
                <p className="mt-2 text-[10px] text-[#8E8E93]" data-testid="round-meas-hint">Kolom berasal dari master Jenis Sampling (Pengaturan → Master → Jenis Sampling).</p>
                {missing.length > 0 && (
                  <p className="mt-1 text-[11px] text-[#8C4A00]" data-testid="round-meas-missing">
                    Masih kosong: <b>{missing.map((k) => measurementMeta(k, measurements).label).join(", ")}</b> — server menolak hasil yang belum lengkap.
                  </p>
                )}
              </div>
            )}
          </>
        ) : (
          <>
            <Field label="Hasil penilaian *">
              <KNSelect data-testid="round-result-select" className="field" value={result} options={RESULT_OPTS} onValueChange={setResult} />
            </Field>
            <Field label={`Skor 0–100${result === "acc" ? " (wajib saat ACC)" : ""}`}>
              <input className="field" data-testid="round-score-input" value={score} onChange={(e) => setScore(e.target.value)} placeholder="92" />
            </Field>
            <Field label="Catatan penilai">
              <textarea className="field" rows={2} data-testid="round-assess-note" value={note} onChange={(e) => setNote(e.target.value)}
                placeholder="mis. Warna presisi, siap dilanjutkan ke kontrak" />
            </Field>
            <Hint>Skor jenis <b>{typeLabel(typeCode, types)}</b> hanya dibandingkan dengan skor jenis yang sama — 90 pada labdip berarti warnanya tepat, 90 pada handfeel berarti rasanya tepat.</Hint>
          </>
        )}
      </div>
    </FormModal>
  );
}
