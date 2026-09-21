/**
 * SampleFinishModal — mode "finish": tandai Sample JADI (server menolak bila belum ada round ACC);
 * mode "deliver": catat Kirim Sample — tujuan WAJIB, tidak mungkin sebelum jadi.
 */
import KNDatePicker from "@/components/KNDatePicker";
import { useState } from "react";
import { CheckCircle2, Send } from "lucide-react";
import FormModal from "../../components/FormModal";
import KNSelect from "../../components/KNSelect";
import { Field, Footer, Hint } from "./RndField";
import { DELIVER_LABEL } from "./sampleTypeMeta";

export default function SampleFinishModal({ mode = "finish", sample, targets, busy, onClose, onConfirm }) {
  const isFinish = mode === "finish";
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [to, setTo] = useState("");
  const [toName, setToName] = useState("");
  const opts = targets && targets.length ? targets : Object.entries(DELIVER_LABEL).map(([value, label]) => ({ value, label }));
  const options = [{ value: "", label: "— pilih tujuan pengiriman —" }, ...opts];

  return (
    <FormModal open onClose={onClose} size="md" testId={isFinish ? "sample-finish-modal" : "sample-deliver-modal"} icon={isFinish ? CheckCircle2 : Send}
      title={isFinish ? "Tandai Sample Jadi" : "Catat Pengiriman Sample"} subtitle={sample?.number}
      footer={<Footer onClose={onClose} busy={busy} disabled={!isFinish && !to} icon={isFinish ? CheckCircle2 : Send}
        testId={isFinish ? "sample-finish-confirm" : "sample-deliver-confirm"} confirmLabel={isFinish ? "Tandai Jadi" : "Catat Pengiriman"}
        title={!isFinish && !to ? "Pilih tujuan pengiriman lebih dulu" : ""}
        onConfirm={() => onConfirm(isFinish ? { date, note } : { to, to_name: toName, date, note })} />}>
      <div className="grid gap-3">
        <Hint>
          {isFinish
            ? "Menandai sample JADI hanya boleh setelah ada round yang ACC — tanggal ini dipakai laporan sebagai bukti sample-nya sah."
            : "Tujuan pengiriman WAJIB dipilih supaya laporan bisa menjawab: “sample untuk siapa yang belum kembali?”"}
        </Hint>
        {!isFinish && (
          <div className="grid gap-2.5 sm:grid-cols-2">
            <Field label="Dikirim ke *">
              <KNSelect data-testid="sample-deliver-to" className="field" value={to} options={options} onValueChange={setTo} />
            </Field>
            <Field label="Nama penerima (opsional)">
              <input className="field" data-testid="sample-deliver-name" value={toName} onChange={(e) => setToName(e.target.value)} placeholder="mis. Ibu Komang — Butik Bali Indah" />
            </Field>
          </div>
        )}
        <Field label={`Tanggal ${isFinish ? "selesai" : "kirim"} (kosong = hari ini)`}>
          <KNDatePicker data-testid={isFinish ? "sample-finish-date" : "sample-deliver-date"} value={date} onChange={setDate} />
        </Field>
        <Field label="Catatan">
          <textarea className="field" rows={2} data-testid={isFinish ? "sample-finish-note" : "sample-deliver-note"} value={note} onChange={(e) => setNote(e.target.value)}
            placeholder={isFinish ? "mis. Swatch pemenang sudah dijilid & diberi label" : "mis. Dikirim bersama surat pengantar untuk persetujuan akhir"} />
        </Field>
      </div>
    </FormModal>
  );
}
