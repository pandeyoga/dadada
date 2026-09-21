/**
 * RevisionProgress — komponen BERSAMA untuk menandai "hasil revisi ke berapa" di semua divisi
 * (Design Studio, sample R&D per supplier×jenis, permintaan desain MD, baris Meja MD).
 * Satu bahasa visual: badge ronde + kotak progres per ronde.
 */
import { Ban, CheckCircle2, Clock, FileImage, RotateCcw } from "lucide-react";

export const ROUND_RESULT_STYLE = {
  acc: { label: "ACC", cls: "border-[#1A7A3A] bg-[#EAF7EF] text-[#1A7A3A]", Icon: CheckCircle2 },
  revision: { label: "Direvisi", cls: "border-[#E8B4B0] bg-[#FDF3F2] text-[#C62828]", Icon: RotateCcw },
  rejected: { label: "Ditolak", cls: "border-[#C62828] bg-[#FDECEC] text-[#8E1B1B]", Icon: Ban },
  review: { label: "Menunggu penilaian", cls: "border-[#0058CC] bg-[#F2F7FF] text-[#0058CC]", Icon: Clock },
  draft: { label: "Sedang dikerjakan", cls: "border-[#D9D9DE] bg-[#FAFBFC] text-[#6B6B73]", Icon: FileImage },
};

/** Label ronde seragam: ronde 1 = "Pengajuan awal", ronde N = "Revisi N-1". */
export const revisionLabel = (roundNo) => (Number(roundNo || 1) <= 1 ? "Pengajuan awal" : `Revisi ${Number(roundNo) - 1}`);

/** Badge kecil "Pengajuan awal" / "Revisi ke-N" — dipakai di kartu, baris tabel, header detail. */
export function RevisionBadge({ count = 0, testId, title, size = "sm" }) {
  const n = Math.max(0, Number(count) || 0);
  const pad = size === "xs" ? "px-1 py-px text-[9px]" : "px-1.5 py-0.5 text-[9.5px]";
  return (
    <span data-testid={testId} title={title || (n ? `Hasil revisi ke-${n}` : "Belum pernah direvisi")}
      className={`inline-flex shrink-0 items-center gap-0.5 rounded font-bold ${pad} ${n ? "bg-[#FDF3F2] text-[#C62828]" : "bg-[#F5F5F7] text-[#6B6B73]"}`}>
      {n ? <><RotateCcw size={9} /> Revisi ke-{n}</> : "Pengajuan awal"}
    </span>
  );
}

/**
 * Kotak progres per ronde. items: [{ key, title, sub, result: acc|revision|rejected|review|draft }].
 * `trailing` = kotak tambahan opsional (mis. tahap Final di Design Studio).
 */
export function RoundBoxes({ items = [], testPrefix = "round", trailing = null, testId }) {
  return (
    <div className="flex flex-wrap items-stretch gap-1.5" data-testid={testId}>
      {items.map((r, i) => {
        const m = ROUND_RESULT_STYLE[r.result] || ROUND_RESULT_STYLE.draft;
        return (
          <div key={r.key ?? i} className="flex items-center gap-1.5">
            <div className={`min-w-[132px] rounded-lg border px-2.5 py-1.5 ${m.cls}`} data-testid={`${testPrefix}-${r.key ?? i + 1}`}>
              <p className="flex items-center gap-1 text-[10.5px] font-bold"><m.Icon size={11} /> {r.title}</p>
              <p className="text-[9.5px] opacity-90">{r.sub ? `${r.sub} · ` : ""}{m.label}</p>
            </div>
            {(i < items.length - 1 || trailing) && <span className="h-px w-3 bg-[#D9D9DE]" />}
          </div>
        );
      })}
      {trailing}
    </div>
  );
}

/** Penyaring seragam "Revisi ≥ N" — value "" = semua, "1".."3" = minimal N kali revisi. */
export const REVISION_FILTER_OPTIONS = [
  { value: "", label: "Semua ronde" }, { value: "1", label: "Revisi ≥ 1" },
  { value: "2", label: "Revisi ≥ 2" }, { value: "3", label: "Revisi ≥ 3" },
];

export function RevisionFilter({ value = "", onChange, testId = "revision-filter" }) {
  return (
    <div className="flex flex-wrap gap-1" data-testid={testId} title="Saring dokumen yang berulang kali direvisi">
      {REVISION_FILTER_OPTIONS.map((o) => (
        <button key={o.value || "all"} type="button" data-testid={`${testId}-${o.value || "all"}`}
          onClick={() => onChange(o.value)}
          className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10.5px] font-semibold ${value === o.value
            ? "border-[#C62828] bg-[#FDF3F2] text-[#C62828]"
            : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#C62828]"}`}>
          {o.value && <RotateCcw size={9} />}{o.label}
        </button>
      ))}
    </div>
  );
}

/** Hitung revisi sample R&D: ronde tertinggi per supplier×jenis, dikurangi 1. */
export function sampleRevisionCount(sample) {
  const max = (sample?.rounds || []).reduce((a, r) => Math.max(a, Number(r.round_no) || 1), 0);
  return Math.max(0, max - 1);
}

/** Petakan hasil round sample R&D (acc/revisi/tolak/kosong) ke gaya kotak bersama. */
export function sampleRoundResult(r) {
  if (r.result === "acc") return "acc";
  if (r.result === "revisi") return "revision";
  if (r.result === "tolak") return "rejected";
  return r.status === "submitted" ? "review" : "draft";
}

/**
 * Susun ronde Permintaan Desain (MD) dari `history`: tiap "delivered" membuka ronde,
 * "revision"/"approved" berikutnya menutupnya. Ronde terakhir mengikuti status dokumen.
 */
export function designRequestRounds(doc) {
  const items = [];
  const openRound = (at) => items.push({
    key: items.length + 1, title: revisionLabel(items.length + 1),
    sub: String(at || "").slice(0, 10), result: "review",
  });
  for (const h of doc?.history || []) {
    const last = items[items.length - 1];
    if (h.event === "delivered") { if (!last || last.result !== "review") openRound(h.at); }
    else if (h.event === "revision" && last) last.result = "revision";
    else if (h.event === "approved" && last) last.result = "acc";
    else if (h.event === "cancelled" && last && last.result === "review") last.result = "rejected";
  }
  const st = doc?.status;
  const last = items[items.length - 1];
  if (last && last.result === "revision" && ["revision", "in_progress"].includes(st)) {
    items.push({ key: items.length + 1, title: revisionLabel(items.length + 1), sub: "", result: "draft" });
  } else if (!last && ["assigned", "in_progress"].includes(st)) {
    items.push({ key: 1, title: revisionLabel(1), sub: "", result: "draft" });
  }
  return items;
}
