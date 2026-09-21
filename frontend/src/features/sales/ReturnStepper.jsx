/**
 * ReturnStepper — peta alur retur jual dalam satu baris (2026-06).
 *
 * Aturan alurnya (dari `services/return_service.py` + `return_state.py`):
 *   draft → pending_approval → approved → inspecting → inspected
 *         → settle (refund / store credit / nego)  |  rejected / cancelled.
 * Layar detail dulu hanya menaruh pill status kecil; orang yang jarang memegang
 * retur tidak tahu SEDANG DI MANA dokumennya dan APA langkah berikutnya.
 */
import { Check, X } from "lucide-react";

const STEPS = [
  { key: "draft", label: "Draf", hint: "Lengkapi item & bukti, lalu kirim untuk persetujuan." },
  { key: "approval", label: "Persetujuan", hint: "Menunggu keputusan manajer (Setujui / Tolak)." },
  { key: "inspection", label: "Inspeksi 4-Titik", hint: "Barang diperiksa: kondisi, grade, kelayakan restock." },
  { key: "settlement", label: "Penyelesaian", hint: "Pilih outcome: refund, store credit, atau nego." },
];

const STAGE_OF = {
  draft: 0, pending_approval: 1, approved: 2, inspecting: 2, inspected: 3,
  refund_settled: 4, credit_settled: 4, nego_settled: 4,
};

const NEXT_HINT = {
  draft: "Langkah berikutnya: kirim untuk persetujuan.",
  pending_approval: "Langkah berikutnya: keputusan manajer (Setujui / Tolak).",
  approved: "Langkah berikutnya: mulai inspeksi 4-titik di panel bawah.",
  inspecting: "Langkah berikutnya: selesaikan inspeksi & catat kondisi tiap item.",
  inspected: "Langkah berikutnya: pilih outcome (refund / store credit / nego) — tombol \"Selesaikan\".",
};

export default function ReturnStepper({ status }) {
  const dead = status === "rejected" || status === "cancelled";
  const stage = STAGE_OF[status] ?? 0;

  return (
    <div className="section-card mb-3 !p-3" data-testid="return-stepper">
      <div className="flex flex-wrap items-center gap-1.5">
        {STEPS.map((s, i) => {
          const done = stage > i;
          const now = !dead && stage === i;
          return (
            <div key={s.key} className="flex items-center gap-1.5" title={s.hint}>
              <span data-testid={`return-step-${s.key}`}
                className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold transition-colors ${
                  done ? "border-[#BFE3CC] bg-[#EAF7EF] text-[#1B7F4B]"
                    : now ? "border-[#0058CC] bg-[#0058CC] text-white"
                      : "border-[#E5E5EA] bg-white text-[#8E8E93]"}`}>
                {done ? <Check size={11} /> : <span className="tabular-nums">{i + 1}</span>}
                {s.label}
              </span>
              {i < STEPS.length - 1 && <span className="text-[#C7C7CC]">→</span>}
            </div>
          );
        })}
        {dead && (
          <span data-testid="return-step-dead"
            className="flex items-center gap-1.5 rounded-full border border-[#F3C1C1] bg-[#FDF0F0] px-2.5 py-1 text-[11px] font-bold text-[#C62828]">
            <X size={11} /> {status === "rejected" ? "Ditolak" : "Dibatalkan (reversal)"}
          </span>
        )}
      </div>
      {!dead && NEXT_HINT[status] && (
        <p className="mt-1.5 text-[11px] text-[#6B6B73]" data-testid="return-stepper-hint">
          {NEXT_HINT[status]}
        </p>
      )}
    </div>
  );
}
