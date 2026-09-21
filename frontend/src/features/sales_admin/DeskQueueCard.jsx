/**
 * DeskQueueCard — satu ANTREAN meja kerja (dipakai Meja Admin Sales & Meja Finance).
 *
 * Aturan desain yang dijaga komponen ini (US15):
 *  1. Setiap antrean membawa **JUMLAH · NILAI · UMUR TERTUA** di kepalanya.
 *  2. **Satu tindakan jelas per baris.** Bukan menu tiga titik.
 *  3. Satuannya ikut jenis nilainya (yard vs rupiah) — `value_kind`.
 *
 * UI/UX 2026-06 (keluhan pemilik):
 *  4. Kartu hanya menampilkan CUPLIKAN 5 baris teratas (urutan server = paling
 *     mendesak dulu). Server bisa mengirim hingga 60 baris (`ROW_LIMIT`); merender
 *     semuanya membuat satu kartu setinggi tiga layar. Selebihnya dibuka lewat
 *     "Lihat semua" → pop-up dengan pencarian + paginasi (`SeeAllModal`), dan
 *     tindakan per baris tetap bisa dikerjakan DI DALAM pop-up.
 *  5. Buka/tutup kartu beranimasi (`Collapse`) + panah yang berputar — sebelumnya
 *     isinya hilang mendadak dan kartu di grid 2 kolom ikut setinggi tetangganya
 *     (kesan "statis"); `self-start` membuat tiap kartu memakai tingginya sendiri.
 */
import { useState } from "react";
import { ChevronDown, Inbox } from "lucide-react";
import { formatCurrency, formatQty } from "../../utils/formatters";
import { RevisionBadge } from "../../components/RevisionProgress";
import { ageTone, badgeClass, badgeLabel, queueMeta } from "./workDeskApi";
import Collapse from "../../components/Collapse";
import SeeAllModal, { SeeAllFooter } from "../../components/SeeAllModal";

const PREVIEW_ROWS = 5;

export default function DeskQueueCard({
  queue, onAction, busyRef = "", testPrefix = "desk", rowTestPrefix, defaultOpen, loading = false,
}) {
  const [open, setOpen] = useState(
    defaultOpen === undefined ? (queue?.count || 0) > 0 : defaultOpen);
  const [showAll, setShowAll] = useState(false);
  const meta = queueMeta(queue?.id);
  const Icon = meta.icon;
  const isQty = queue?.value_kind === "qty";
  const rows = Array.isArray(queue?.rows) ? queue.rows : [];
  const visible = rows.slice(0, PREVIEW_ROWS);
  const oldest = ageTone(queue?.oldest_age_days);

  // Ringkasan: qty → angka + satuan; count → jumlah dokumen; selain itu SELALU rupiah.
  const totalText = isQty
    ? `${formatQty(queue?.total_value)} ${rows[0]?.unit || ""}`.trim()
    : queue?.value_kind === "count"
      ? `${rows.length} dokumen`
      : formatCurrency(Number(queue?.total_value) || 0);

  return (
    <section className="section-card self-start" data-testid={`${testPrefix}-queue-${queue?.id}`}>
      <button
        type="button"
        data-testid={`${testPrefix}-queue-toggle-${queue?.id}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-start gap-2.5 px-3 py-2.5 text-left hover:bg-[#FAFBFC]"
      >
        <span className="mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg"
              style={{ background: meta.bg }}>
          <Icon size={16} style={{ color: meta.tone }} />
        </span>

        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center gap-2">
            <span className="text-[13px] font-bold text-[#1C1C1E]">{queue?.label}</span>
            <span data-testid={`${testPrefix}-count-${queue?.id}`}
                  className="rounded-full px-2 py-0.5 text-[10.5px] font-bold tabular-nums"
                  style={{ background: meta.bg, color: meta.tone }}>
              {queue?.count || 0}
            </span>
            {(queue?.count || 0) > 0 && (
              <span data-testid={`${testPrefix}-oldest-${queue?.id}`}
                    className={`rounded-full border px-2 py-0.5 text-[10px] font-bold ${oldest.cls}`}
                    title="Umur baris tertua di antrean ini">
                tertua {oldest.label}
              </span>
            )}
          </span>
          <span className="mt-1 block text-[10.5px] leading-relaxed text-[#6B6B73]">
            {queue?.hint}
          </span>
        </span>

        <span className="shrink-0 pl-2 text-right">
          <span className="block text-[9.5px] font-bold uppercase tracking-wide text-[#8E8E93]">
            {queue?.value_label || "Nilai"}
          </span>
          <span data-testid={`${testPrefix}-total-${queue?.id}`}
                className="block text-[12.5px] font-bold tabular-nums text-[#1C1C1E]">
            {totalText}
          </span>
        </span>
        <span className={`mt-1 shrink-0 text-[#9A9BA3] transition-transform duration-300 ${
          open ? "rotate-0" : "-rotate-90"}`}>
          <ChevronDown size={15} />
        </span>
      </button>

      <Collapse open={open}>
        <div>
          {/* Saat antrean sedang dimuat ulang, angka lama masih terpampang. Tanpa
              penanda ini pengguna menindak baris yang mungkin sudah berpindah antrean. */}
          {loading && rows.length > 0 && (
            <p data-testid={`${testPrefix}-refreshing-${queue?.id}`}
               className="border-t border-[#EFF0F2] bg-[#FAFBFC] px-3 py-1 text-[10.5px] text-[#8E8E93]">
              Memuat ulang antrean…
            </p>
          )}

          {loading && rows.length === 0 ? (
            <p data-testid={`${testPrefix}-loading-${queue?.id}`}
               className="border-t border-[#EFF0F2] px-3 py-7 text-center text-[11.5px] text-[#6B6B73]">
              Memuat antrean…
            </p>
          ) : rows.length === 0 ? (
            <div data-testid={`${testPrefix}-empty-${queue?.id}`}
                 className="border-t border-[#EFF0F2] px-3 py-7 text-center text-[11.5px] text-[#6B6B73]">
              <Inbox size={22} className="mx-auto mb-1.5 text-[#D6D6DB]" />
              Antrean ini bersih — tidak ada yang perlu ditindak.
            </div>
          ) : (
            <div className="divide-y divide-[#F4F5F7] border-t border-[#EFF0F2]">
              {visible.map((row, i) => (
                <QueueRow key={`${row.ref_type}-${row.ref_id}-${row.number || i}`}
                          row={row} queue={queue}
                          isQty={isQty} busy={busyRef === row.ref_id}
                          testPrefix={rowTestPrefix || testPrefix}
                          onAction={() => onAction?.(row, queue)} />
              ))}
            </div>
          )}

          {/* Jujur soal pemotongan: kartu = cuplikan, pop-up = semuanya. */}
          <SeeAllFooter shown={visible.length} total={rows.length} label="baris"
            accent={meta.tone} onClick={() => setShowAll(true)}
            testId={`${testPrefix}-see-all-${queue?.id}`} />
        </div>
      </Collapse>

      <SeeAllModal open={showAll} onClose={() => setShowAll(false)}
        title={queue?.label} subtitle={queue?.hint} icon={Icon} accent={meta.tone}
        rows={rows}
        rowText={(r) => `${r.number || ""} ${r.title || ""} ${r.subtitle || ""}`}
        renderRow={(row, i) => (
          <QueueRow key={`${row.ref_type}-${row.ref_id}-${row.number || i}`}
                    row={row} queue={queue}
                    isQty={isQty} busy={busyRef === row.ref_id}
                    testPrefix={`${testPrefix}-modal`}
                    onAction={() => onAction?.(row, queue)} />
        )}
        emptyText="Tidak ada baris antrean yang cocok dengan pencarian."
        testId={`${testPrefix}-see-all-modal-${queue?.id}`} />
    </section>
  );
}

function QueueRow({ row, queue, isQty, busy, onAction, testPrefix }) {
  const age = ageTone(row.age_days);
  // Kolom nilai: qty → angka + satuan; count → kosong (tidak bermakna per baris); money → rupiah.
  const value = isQty
    ? `${formatQty(row.value)} ${row.unit || ""}`.trim()
    : queue?.value_kind === "count"
      ? ""
      : formatCurrency(Number(row.value) || 0);

  return (
    <div data-testid={`${testPrefix}-row-${row.row_key || row.ref_id}`}
         className="flex flex-wrap items-center gap-x-3 gap-y-1.5 px-3 py-2.5 hover:bg-[#FAFBFC]">
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-1.5">
          <span data-testid={`${testPrefix}-number-${row.ref_id}`}
                className="text-[11.5px] font-bold text-[#0058CC]">{row.number}</span>
          {row.badge && (
            <span data-testid={`${testPrefix}-badge-${row.ref_id}`}
                  className={`rounded-full border px-1.5 py-0.5 text-[9.5px] font-bold ${badgeClass(row.badge)}`}>
              {badgeLabel(row.badge)}
            </span>
          )}
          {row.revision_count !== undefined && row.revision_count !== null && (
            <RevisionBadge count={row.revision_count} size="xs" testId={`${testPrefix}-revision-${row.ref_id}`} />
          )}
          <span className={`rounded-full border px-1.5 py-0.5 text-[9.5px] font-bold ${age.cls}`}
                title="Umur baris ini">{age.label}</span>
        </div>
        <p className="truncate text-[12px] font-semibold text-[#1C1C1E]">{row.title}</p>
        {row.subtitle && (
          <p className="truncate text-[10.5px] text-[#8E8E93]">{row.subtitle}</p>
        )}
      </div>

      <span data-testid={`${testPrefix}-value-${row.ref_id}`}
            className="w-[130px] shrink-0 text-right text-[12px] font-semibold tabular-nums">
        {value}
      </span>

      <button type="button" data-testid={`${testPrefix}-action-${row.row_key || row.ref_id}`}
              className="btn-secondary btn-xs shrink-0" disabled={busy} onClick={onAction}
              title={queue?.hint || ""}>
        {busy ? "Memproses…" : (row.action || queue?.action_label || "Buka")}
      </button>
    </div>
  );
}
