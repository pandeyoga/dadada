/**
 * SeeAllModal + SeeAllFooter — standar "kartu = cuplikan, pop-up = semuanya".
 *
 * MASALAH YANG DISELESAIKAN (keluhan pemilik, 2026-06): kartu antrean di beranda,
 * Pusat Persetujuan, Meja Admin Sales & Meja Finance merender SEMUA barisnya ke
 * bawah. Dengan 60 baris satu kartu bisa setinggi tiga layar dan kartu di bawahnya
 * tak pernah terlihat. Pola di sini: kartu menampilkan 5-6 baris teratas (urutan
 * server = paling mendesak dulu), lalu `SeeAllFooter` menyebut jujur "Menampilkan X
 * dari Y" dan membuka pop-up berisi SELURUH baris + pencarian + paginasi.
 *
 * Perilaku pop-up mengikuti standar FormModal/DetailModal: Esc menutup lewat
 * `useEscapeClose`, backdrop lewat `overlayDismiss()` (INV-UI-01), scroll halaman
 * di belakang dikunci, kepala & paginasi menempel (sticky).
 */
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Inbox, Search, X } from "lucide-react";
import { overlayDismiss } from "@/utils/overlayDismiss";
import { useEscapeClose } from "@/utils/escapeLayers";

export function SeeAllFooter({
  shown, total, onClick, testId, label = "baris", accent = "#0058CC",
  className, style,
}) {
  if ((total || 0) <= (shown || 0)) return null;
  return (
    <button
      type="button"
      data-testid={testId}
      onClick={onClick}
      className={className
        || "flex w-full items-center justify-center gap-1.5 border-t border-dashed border-[#E0E4EA] bg-[#FAFBFC] px-3 py-2 text-[11.5px] font-semibold transition-colors hover:bg-[#F2F6FC]"}
      style={style || { color: accent }}
    >
      Menampilkan {shown} dari {total} {label} · Lihat semua →
    </button>
  );
}

export default function SeeAllModal({
  open, onClose, title, subtitle = "", icon: Icon = null, accent = "#0058CC",
  rows = [], renderRow, rowText, pageSize = 10, testId = "see-all",
  emptyText = "Tidak ada baris yang cocok dengan pencarian.",
  searchPlaceholder = "Cari nomor, nama, atau keterangan…",
  listClassName = "divide-y divide-[#F4F5F7]",
  footerNote = null,
}) {
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);

  useEscapeClose(open, onClose);
  useEffect(() => { if (open) { setQ(""); setPage(1); } }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    const sebelumnya = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = sebelumnya; };
  }, [open]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return rows;
    return rows.filter((r) =>
      String(rowText ? rowText(r) : JSON.stringify(r)).toLowerCase().includes(s));
  }, [rows, q, rowText]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const cur = Math.min(page, totalPages);
  const slice = filtered.slice((cur - 1) * pageSize, cur * pageSize);
  const from = filtered.length === 0 ? 0 : (cur - 1) * pageSize + 1;
  const to = Math.min(cur * pageSize, filtered.length);

  if (!open) return null;

  return (
    <div
      className="modal-overlay fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-black/40 p-4 sm:items-center"
      data-testid={`${testId}-overlay`}
      {...overlayDismiss(onClose)}
    >
      <div
        role="dialog" aria-modal="true" aria-label={title} data-testid={testId}
        className="my-auto w-full max-w-2xl rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* KEPALA — judul + jumlah + pencarian, menempel saat isi di-scroll */}
        <div className="sticky top-0 z-10 rounded-t-xl border-b border-[#EFF0F2] bg-white px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2">
              {Icon && (
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full"
                  style={{ background: `${accent}18`, color: accent }}>
                  <Icon size={15} />
                </span>
              )}
              <div className="min-w-0">
                <h3 data-testid={`${testId}-title`}
                  className="flex items-center gap-2 text-[13.5px] font-bold leading-tight text-[#1C1C1E]">
                  <span className="truncate">{title}</span>
                  <span data-testid={`${testId}-count`}
                    className="shrink-0 rounded-full px-2 py-0.5 text-[10.5px] font-bold tabular-nums"
                    style={{ background: `${accent}14`, color: accent }}>
                    {rows.length}
                  </span>
                </h3>
                {subtitle && <p className="mt-0.5 truncate text-[11px] text-[#6B6B73]">{subtitle}</p>}
              </div>
            </div>
            <button type="button" className="icon-button shrink-0" aria-label="Tutup"
              data-testid={`${testId}-close`} onClick={onClose}>
              <X size={14} />
            </button>
          </div>
          <div className="relative mt-2">
            <Search size={13}
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
            <input
              value={q}
              onChange={(e) => { setQ(e.target.value); setPage(1); }}
              data-testid={`${testId}-search`}
              placeholder={searchPlaceholder}
              className="w-full rounded-lg border border-[#E5E5EA] bg-[#FAFBFC] py-1.5 pl-8 pr-3 text-[12px] outline-none transition-colors focus:border-[#0058CC] focus:bg-white"
            />
          </div>
        </div>

        {/* BADAN — daftar berhalaman */}
        <div className="max-h-[55vh] overflow-y-auto" data-testid={`${testId}-body`}>
          {slice.length === 0 ? (
            <div className="px-4 py-10 text-center text-[11.5px] text-[#6B6B73]"
              data-testid={`${testId}-empty`}>
              <Inbox size={22} className="mx-auto mb-1.5 text-[#D6D6DB]" />
              {emptyText}
            </div>
          ) : (
            <div className={listClassName}>{slice.map((r, i) => renderRow(r, i))}</div>
          )}
        </div>

        {/* KAKI — info rentang + paginasi, menempel di bawah */}
        <div className="sticky bottom-0 rounded-b-xl border-t border-[#EFF0F2] bg-[#FAFBFC] px-4 py-2.5">
          {footerNote}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] tabular-nums text-[#6B6B73]" data-testid={`${testId}-info`}>
              {filtered.length === 0 ? "0 baris" : (
                <>Menampilkan <b className="text-[#1C1C1E]">{from}–{to}</b> dari{" "}
                  <b className="text-[#1C1C1E]">{filtered.length}</b>
                  {q ? ` hasil (${rows.length} total)` : ""}</>
              )}
            </span>
            {totalPages > 1 && (
              <div className="flex items-center gap-1">
                <button type="button" data-testid={`${testId}-prev`}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={cur <= 1}
                  className="inline-flex items-center gap-1 rounded-md border border-[#E5E5EA] bg-white px-2 py-1 text-[11px] font-semibold text-[#3C3C43] hover:bg-[#F2F2F7] disabled:cursor-not-allowed disabled:opacity-40">
                  <ChevronLeft size={12} /> Sebelumnya
                </button>
                <span data-testid={`${testId}-page`}
                  className="whitespace-nowrap px-1.5 text-[11px] font-semibold tabular-nums text-[#6B6B73]">
                  Hal {cur} / {totalPages}
                </span>
                <button type="button" data-testid={`${testId}-next`}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={cur >= totalPages}
                  className="inline-flex items-center gap-1 rounded-md border border-[#E5E5EA] bg-white px-2 py-1 text-[11px] font-semibold text-[#3C3C43] hover:bg-[#F2F2F7] disabled:cursor-not-allowed disabled:opacity-40">
                  Berikutnya <ChevronRight size={12} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
