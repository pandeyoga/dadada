/** T-03 Lapis 4 — pager kecil bersama untuk tabel SDM (absensi & kunjungan). */
export default function KNPager({ page, pageSize, total, onChange, testId = "pager" }) {
  const pages = Math.max(1, Math.ceil((total || 0) / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-2 text-[12px] text-[#6E6E73]" data-testid={testId}>
      <span className="tabular-nums">Halaman {page} / {pages} · {total} baris</span>
      <div className="flex gap-1">
        <button type="button" className="secondary-button btn-xs" disabled={page <= 1} onClick={() => onChange(page - 1)} data-testid={`${testId}-prev`}>Sebelumnya</button>
        <button type="button" className="secondary-button btn-xs" disabled={page >= pages} onClick={() => onChange(page + 1)} data-testid={`${testId}-next`}>Berikutnya</button>
      </div>
    </div>
  );
}
