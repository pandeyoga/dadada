/** FinalPanel — tahap sesudah ACC: mockup (WAJIB ≥1) + file desain asli (WAJIB ≥1, bisa diunduh kembali). Tidak ada varian warna. */
import { CheckCircle2, Circle } from "lucide-react";
import FilesPanel from "./FilesPanel";

function Row({ ok, text, testId }) {
  return (
    <li className={`flex items-center gap-1.5 text-[11.5px] ${ok ? "text-[#1A7A3A]" : "text-[#6B6B73]"}`} data-testid={testId}>
      {ok ? <CheckCircle2 size={13} /> : <Circle size={13} />} {text}
    </li>
  );
}

export default function FinalPanel({ design, canEdit, onDone, onError }) {
  const fin = design.final || {};
  const locked = !["approved", "final_submitted", "active"].includes(design.status);
  const editable = canEdit && !locked && design.status !== "active";
  return (
    <div className="space-y-4" data-testid="design-final-panel">
      <div className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-3">
        <p className="text-[10.5px] font-bold uppercase text-[#8E8E93]">Syarat berkas final (sesudah ACC)</p>
        <ul className="mt-1.5 space-y-1">
          <Row ok={(fin.mockup_files ?? 0) >= 1} testId="design-final-check-mockup"
            text={`Mockup hasil desain yang di-ACC: ${fin.mockup_files ?? 0} / 1 file (wajib)`} />
          <Row ok={(fin.source_files ?? 0) >= 1} testId="design-final-check-source"
            text={`File desain asli (AI / PSD / EPS / PDF / ZIP): ${fin.source_files ?? 0} / 1 file (wajib, bisa diunduh kembali)`} />
        </ul>
        {locked && <p className="mt-2 text-[10.5px] text-[#A05000]" data-testid="design-final-locked">Tahap ini terbuka setelah desain di-ACC penilai.</p>}
      </div>
      <FilesPanel design={design} kind="mockup" canEdit={editable} onDone={onDone} onError={onError} />
      <FilesPanel design={design} kind="source" canEdit={editable} onDone={onDone} onError={onError} />
    </div>
  );
}
