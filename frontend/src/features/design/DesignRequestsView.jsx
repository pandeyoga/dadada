/**
 * DesignRequestsView — FASE D · **PERMINTAAN DESAIN** (`<ENT>/DSR-#####`).
 *
 * Satu layar untuk tiga peran yang membicarakan dokumen yang sama:
 *  - **MD / Admin Sales**: membuat permintaan dari pesanan pelanggan, menugaskan,
 *    dan memantau tenggat.
 *  - **Desainer**: melihat TUGASNYA (pagar kepemilikan ditegakkan server), menandai
 *    mulai mengerjakan, lalu menyerahkan artwork dari Galeri Desain.
 *  - **Manajer**: memutuskan ACC / minta revisi **ber-alasan**.
 *
 * Dua tampilan yang sengaja dipisah:
 *  · **Papan** — kolom per status (kanban), untuk melihat "macet di mana".
 *  · **Daftar** — tabel berhalaman + **Unduh CSV** (INV-UI-07), untuk rekap.
 * Kartu ringkasan SELALU dari agregat server (`summary`) — pelajaran FASE P5:
 * lencana yang dihitung dari halaman aktif diam-diam menyusut.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { CalendarClock, Palette, Plus, RefreshCw } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import DetailModal from "../../components/DetailModal";
import ErrorNotice from "../../components/ErrorNotice";
import { RevisionBadge, RevisionFilter } from "../../components/RevisionProgress";
import LineFilter from "../../components/LineFilter";
import PaginationBar from "../../components/PaginationBar";
import { usePagedList } from "../../hooks/usePagedList";
import { EmptyState } from "../finance/financeShared";
import DesignRequestCreateModal from "./DesignRequestCreateModal";
import DesignRequestDetailPanel from "./DesignRequestDetailPanel";
import { formatDateId } from "../../components/KNDatePicker";
import DesignerReportPanel from "./DesignerReportPanel";
import MyDesignerReportPanel from "./MyDesignerReportPanel";
import {
  apiText, DSR_BOARD_ORDER, DSR_STATUS_CLASS, DSR_STATUS_LABEL, dsrMeta,
  getDesignRequest, referenceUrl,
} from "./designRequestsApi";
import { DESIGN_STATUS_META } from "../rnd/rndMeta";
import { roleIs } from "../../config/roles";

/** Kartu papan: nomor · kategori · brief · desain Studio tertaut · desainer · tenggat. */
function BoardCard({ r, onOpen }) {
  const d = (r.designs || [])[r.designs?.length - 1];
  const dm = d ? (DESIGN_STATUS_META[d.status] || DESIGN_STATUS_META.draft) : null;
  return (
    <button type="button" data-testid={`dsr-card-${r.id}`} onClick={onOpen}
      className="w-full rounded-lg border border-[#EFF0F2] bg-white p-2 text-left shadow-sm transition-[border-color,box-shadow] hover:border-[#C9B3DB] hover:shadow-md">
      <p className="flex flex-wrap items-center gap-1.5 text-[11.5px] font-bold text-[#1C1C1E]">
        {r.number}
        <RevisionBadge count={r.revision_count} size="xs" testId={`dsr-card-revision-${r.id}`} />
        {r.is_overdue && <span className="status-pill pill-danger !text-[9px]">lewat tenggat</span>}
      </p>
      {(r.category_code || r.design_category_code) && (
        <p className="mt-1 flex flex-wrap gap-1" data-testid={`dsr-card-cats-${r.id}`}>
          {r.category_code && <span className="rounded bg-[#F1E9F7] px-1.5 py-0.5 text-[9.5px] font-semibold text-[#6B219A]">{r.category_name || r.category_code}</span>}
          {r.design_category_code && <span className="rounded bg-[#EEF4FF] px-1.5 py-0.5 text-[9.5px] font-semibold text-[#0058CC]">{r.design_category_name || r.design_category_code}</span>}
        </p>
      )}
      <p className="mt-1 line-clamp-2 text-[10.5px] leading-snug text-[#3C3C43]">{r.brief}</p>
      {r.customer_name && <p className="mt-0.5 truncate text-[10px] text-[#8E8E93]">{r.so_number ? `${r.so_number} · ` : ""}{r.customer_name}</p>}
      {(r.references || []).length > 0 && (
        <p className="mt-1 flex gap-1" data-testid={`dsr-card-refs-${r.id}`}>
          {r.references.slice(0, 4).map((f) => (
            <img key={f.id} src={referenceUrl(r.id, f.id)} alt="" className="h-7 w-7 rounded border border-[#EFF0F2] object-cover" loading="lazy" />
          ))}
          {r.references.length > 4 && <span className="flex h-7 w-7 items-center justify-center rounded bg-[#F2F2F5] text-[9px] font-bold text-[#6B6B73]">+{r.references.length - 4}</span>}
        </p>
      )}
      {d && (
        <p className="mt-1.5 flex items-center gap-1.5 rounded-md bg-[#FAFBFC] px-1.5 py-1 text-[10px]" data-testid={`dsr-card-design-${r.id}`}>
          <span className="font-mono font-bold text-[#1C1C1E]">{d.code || "tanpa kode"}</span>
          <span className={`status-pill ${dm.cls} !text-[9px]`}>{dm.label}</span>
        </p>
      )}
      <p className="mt-1.5 flex items-center justify-between gap-1 text-[10px] text-[#8E8E93]">
        <span className="flex items-center gap-1 truncate">
          <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#E5E5EA] text-[8.5px] font-bold text-[#3C3C43]">
            {(r.assigned_name || "?").slice(0, 1).toUpperCase()}
          </span>
          <span className="truncate">{r.assigned_name || "Belum ditugaskan"}</span>
        </span>
        {r.due_date && (
          <span className={`shrink-0 ${r.is_overdue ? "font-semibold text-[#A8221A]" : ""}`}>
            <CalendarClock size={9} className="inline" /> {formatDateId(r.due_date, "dd MMM")}
          </span>
        )}
      </p>
    </button>
  );
}

const CSV_COLUMNS = [
  { key: "number", header: "Nomor" },
  { key: "status_label", header: "Status" },
  { key: "target_label", header: "Jenis" },
  { key: "assigned_name", header: "Desainer" },
  { key: "requested_by", header: "Diminta oleh" },
  { key: "so_number", header: "No. Pesanan" },
  { key: "customer_name", header: "Pelanggan" },
  { key: "due_date", header: "Tenggat" },
  { key: "versions", header: "Versi diserahkan", type: "number" },
  { key: "revision_count", header: "Putaran revisi", type: "number" },
  { key: "brief", header: "Brief" },
];

export default function DesignRequestsView({ currentUser, selectedEntity = "all", focusDoc, onClearFocus }) {
  const [meta, setMeta] = useState({ designers: [], target_types: [], sources: [], role: "" });
  const [tab, setTab] = useState("board");
  const [statusFilter, setStatusFilter] = useState("");
  const [minRevision, setMinRevision] = useState("");
  const [line, setLine] = useState("");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState("");

  const role = meta.role || currentUser?.role || "";
  const canCreate = roleIs(role, ["admin", "manager", "sales_admin", "md"]);
  const canReport = roleIs(role, ["admin", "manager"]);
  // FASE D — desainer TIDAK melihat rapor rekan (itu wewenang atasan), tetapi ia
  // berhak melihat angkanya SENDIRI. Tanpa cabang ini tab rapor hanya bisa 403 untuk
  // desainer dan `audit_sales_roles_ux` melaporkannya sebagai **panel mati** — benar,
  // karena layar menawarkan pintu yang selalu menolak.
  const canReportMine = !canReport && !!meta.own_only;

  const params = useMemo(() => {
    const p = {};
    if (statusFilter) p.status = statusFilter;
    if (line) p.line = line;
    if (minRevision) p.min_revision = Number(minRevision);
    if (selectedEntity && selectedEntity !== "all") p.entity_id = selectedEntity;
    return p;
  }, [statusFilter, line, minRevision, selectedEntity]);

  const paged = usePagedList("/design-requests", { pageSize: 50, params, search });
  // Kartu ringkasan diambil TERPISAH dari agregat server (`summary`) dengan filter yang
  // sama: `usePagedList` hanya membawa `items`. Menghitungnya dari isi halaman akan
  // membuat angkanya diam-diam menyusut begitu daftarnya berhalaman (pelajaran FASE P5).
  const [summary, setSummary] = useState({});

  useEffect(() => {
    dsrMeta().then(setMeta).catch((e) => setError(apiText(e, "Gagal memuat pilihan layar.")));
  }, []);

  const loadSummary = useCallback(async () => {
    try {
      const r = await axios.get(`${API}/design-requests`, {
        params: { ...params, ...(search ? { q: search } : {}), page: 1, page_size: 1 } });
      setSummary(r.data?.summary || {});
    } catch (e) { /* bilah galat daftar sudah bicara — jangan dobel */ }
  }, [params, search]);

  useEffect(() => { loadSummary(); }, [loadSummary]);

  useEffect(() => {
    if (!canCreate) return;
    axios.get(`${API}/sales-orders`, { params: { page: 1, page_size: 50 } })
      .then((r) => setOrders(Array.isArray(r.data) ? r.data : (r.data?.items || [])))
      .catch(() => setOrders([]));
  }, [canCreate]);

  const openDetail = useCallback(async (id) => {
    try { setDetail(await getDesignRequest(id)); }
    catch (e) { setError(apiText(e, "Gagal memuat rincian permintaan.")); }
  }, []);

  // Deep-link (Meja MD / dokumen terkait) → langsung buka rinciannya.
  useEffect(() => {
    if (focusDoc?.focus_type === "design_request" && focusDoc.focus_id) {
      openDetail(focusDoc.focus_id);
      onClearFocus?.();
    }
  }, [focusDoc?.focus_id]); // eslint-disable-line

  const grouped = useMemo(() => {
    const out = {};
    DSR_BOARD_ORDER.forEach((s) => { out[s] = []; });
    (paged.items || []).forEach((r) => {
      if (!out[r.status]) out[r.status] = [];
      out[r.status].push(r);
    });
    return out;
  }, [paged.items]);

  const chips = [{ key: "", label: "Semua" }].concat(
    DSR_BOARD_ORDER.map((s) => ({ key: s, label: DSR_STATUS_LABEL[s] })));

  return (
    <div data-testid="design-requests-view" className="grid gap-3">
      {error && <ErrorNotice message={error} onRetry={paged.refresh} onDismiss={() => setError("")} testId="dsr-error" />}
      {paged.error && !error && (
        <ErrorNotice message={paged.error} onRetry={paged.refresh} testId="dsr-list-error" />
      )}

      {/* Kepala + aksi */}
      <div className="section-card">
        <div className="section-head">
          <div className="flex items-center gap-2 min-w-0">
            <Palette size={15} className="text-[#6B219A]" />
            <div className="min-w-0">
              <span className="kicker">Desain</span>
              <h2 data-testid="panel-title" className="text-[13px] font-bold">Permintaan Desain</h2>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LineFilter value={line} onChange={setLine} storageKey="design-requests"
              allowed={currentUser?.allowed_line_codes} className="!py-1.5" testId="dsr-line-filter" />
            <input data-testid="dsr-search" className="field !py-1.5 !text-[11.5px] w-52"
              placeholder="Cari nomor / brief / pelanggan…"
              value={search} onChange={(e) => setSearch(e.target.value)} />
            <button data-testid="dsr-refresh" className="secondary-button !py-1.5" onClick={() => { paged.refresh(); loadSummary(); }}>
              <RefreshCw size={12} /> Muat ulang
            </button>
            {canCreate && (
              <button data-testid="dsr-create-button" className="primary-button" onClick={() => setShowCreate(true)}>
                <Plus size={13} /> Buat Permintaan
              </button>
            )}
          </div>
        </div>

        {/* Kartu ringkasan — dari agregat SERVER (bukan dari isi halaman) */}
        <div className="grid gap-2 sm:grid-cols-5">
          {[
            ["Total", summary.total ?? 0, "dsr-kpi-total"],
            ["Berjalan", summary.open ?? 0, "dsr-kpi-open"],
            ["Menunggu keputusan", summary.delivered ?? 0, "dsr-kpi-delivered"],
            ["Minta revisi", summary.revision ?? 0, "dsr-kpi-revision"],
            ["Lewat tenggat", summary.overdue ?? 0, "dsr-kpi-overdue"],
          ].map(([label, value, tid]) => (
            <div key={tid} className="rounded-lg border border-[#EFF0F2] bg-white px-3 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#9A9BA3]">{label}</p>
              <p data-testid={tid} className="text-[15px] font-bold tabular-nums text-[#1C1C1E]">{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Tab tampilan */}
      <div className="flex flex-wrap items-center gap-2">
        {[["board", "Papan"], ["list", "Daftar"]]
          .concat(canReport ? [["report", "Rapor Desainer"]] : [])
          .concat(canReportMine ? [["myreport", "Rapor Saya"]] : [])
          .map(([key, label]) => (
            <button key={key} data-testid={`dsr-tab-${key}`}
              className={tab === key ? "primary-button !py-1.5" : "secondary-button !py-1.5"}
              onClick={() => setTab(key)}>{label}</button>
          ))}
        {tab !== "report" && tab !== "myreport" && (
          <div className="ml-auto flex flex-wrap items-center gap-1.5">
            <RevisionFilter value={minRevision} onChange={setMinRevision} testId="dsr-revision-filter" />
            <span className="mx-1 h-4 w-px bg-[#E5E5EA]" />
            {chips.map((c) => (
              <button key={c.key || "all"} data-testid={`dsr-chip-${c.key || "all"}`}
                className={`status-pill ${statusFilter === c.key ? "pill-info" : "pill-muted"}`}
                onClick={() => setStatusFilter(c.key)}>{c.label}</button>
            ))}
          </div>
        )}
      </div>

      {tab === "report" ? (
        <DesignerReportPanel selectedEntity={selectedEntity} line={line} />
      ) : tab === "myreport" ? (
        <MyDesignerReportPanel selectedEntity={selectedEntity} line={line} />
      ) : paged.loading ? (
        <div data-testid="dsr-loading" className="section-card grid gap-2">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-9 animate-pulse rounded-md bg-[#F2F2F5]" />)}
        </div>
      ) : (paged.items || []).length === 0 ? (
        <div className="section-card">
          <EmptyState icon={Palette} title={minRevision ? `Tidak ada permintaan dengan revisi ≥ ${minRevision}` : "Belum ada permintaan desain"}
            hint={minRevision ? "Kabar baik — tidak ada desain yang tersendat di revisi berulang. Pilih \"Semua ronde\" untuk melihat seluruhnya."
              : canCreate
              ? "Buat permintaan dari pesanan pelanggan atau inisiatif internal, lalu tugaskan ke desainer."
              : "Permintaan yang ditugaskan kepada Anda akan muncul di sini."}
            testId="dsr-empty" />
        </div>
      ) : tab === "board" ? (
        <>
          <div data-testid="dsr-board" className="grid grid-flow-col auto-cols-[minmax(215px,1fr)] gap-2 overflow-x-auto pb-1">
            {DSR_BOARD_ORDER.map((s) => (
              <div key={s} data-testid={`dsr-col-${s}`} className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-2">
                <p className="mb-1.5 flex items-center justify-between text-[10.5px] font-bold uppercase tracking-wide text-[#6B6B73]">
                  <span className="flex items-center gap-1.5">
                    <span className={`inline-block h-2 w-2 rounded-full ${DSR_STATUS_CLASS[s] === "pill-success" ? "bg-[#1A7A3A]" : DSR_STATUS_CLASS[s] === "pill-danger" ? "bg-[#C62828]" : DSR_STATUS_CLASS[s] === "pill-warning" ? "bg-[#E08A00]" : DSR_STATUS_CLASS[s] === "pill-info" ? "bg-[#0058CC]" : "bg-[#B4B4BB]"}`} />
                    {DSR_STATUS_LABEL[s]}
                  </span>
                  <span data-testid={`dsr-col-count-${s}`} className="rounded-full bg-white px-1.5 tabular-nums">{(grouped[s] || []).length}</span>
                </p>
                <div className="grid gap-1.5">
                  {(grouped[s] || []).map((r) => <BoardCard key={r.id} r={r} onOpen={() => openDetail(r.id)} />)}
                  {(grouped[s] || []).length === 0 && (
                    <p className="px-1 py-1.5 text-[10.5px] text-[#B4B4BB]">— kosong —</p>
                  )}
                </div>
              </div>
            ))}
          </div>
          {paged.total > (paged.items || []).length && (
            <p data-testid="dsr-board-note" className="text-[11px] text-[#8E8E93]">
              Papan menampilkan {(paged.items || []).length} permintaan terbaru dari {paged.total}.
              Pakai penyaring status/lini atau buka tab <strong>Daftar</strong> untuk melihat semuanya.
            </p>
          )}
        </>
      ) : (
        <div className="section-card">
          <div className="overflow-x-auto">
            <table className="w-full text-[11.5px]">
              <thead>
                <tr className="bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73]">
                  <th className="px-2 py-1.5 text-left">Nomor</th>
                  <th className="px-2 py-1.5 text-left">Brief</th>
                  <th className="px-2 py-1.5 text-left">Desainer</th>
                  <th className="px-2 py-1.5 text-left">Tenggat</th>
                  <th className="px-2 py-1.5 text-left">Status</th>
                  <th className="px-2 py-1.5 text-left">Ronde</th>
                  <th className="px-2 py-1.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {(paged.items || []).map((r) => (
                  <tr key={r.id} data-testid={`dsr-row-${r.id}`} className="border-b border-[#F2F2F5] last:border-0">
                    <td className="px-2 py-1.5 font-semibold text-[#1C1C1E]">{r.number}</td>
                    <td className="px-2 py-1.5 text-[#3C3C43]"><span className="line-clamp-1">{r.brief}</span></td>
                    <td className="px-2 py-1.5">{r.assigned_name || "—"}</td>
                    <td className={`px-2 py-1.5 ${r.is_overdue ? "font-semibold text-[#A8221A]" : ""}`}>
                      {r.due_date ? formatDateId(r.due_date, "dd MMM yyyy") : "—"}
                    </td>
                    <td className="px-2 py-1.5">
                      <span className={`status-pill ${DSR_STATUS_CLASS[r.status] || "pill-muted"}`}>
                        {r.status_label}
                      </span>
                    </td>
                    <td className="px-2 py-1.5">
                      <RevisionBadge count={r.revision_count} testId={`dsr-row-revision-${r.id}`} />
                    </td>
                    <td className="px-2 py-1.5 text-right">
                      <button data-testid={`dsr-detail-${r.id}`} className="link-button"
                        onClick={() => openDetail(r.id)}>Detail</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-2">
            <PaginationBar
              page={paged.page} pageSize={paged.pageSize} total={paged.total}
              hasMore={paged.hasMore} loading={paged.loading}
              onPrev={paged.prev} onNext={paged.next} onPageSize={paged.setPageSize}
              testId="dsr-pager" label="permintaan"
              exportConfig={{ columns: CSV_COLUMNS, rows: paged.items,
                fetchAll: paged.fetchAll, filename: "permintaan-desain" }}
            />
          </div>
        </div>
      )}

      <DesignRequestCreateModal
        open={showCreate} onClose={() => setShowCreate(false)} meta={meta} orders={orders}
        onCreated={() => { setShowCreate(false); paged.refresh(); loadSummary(); }}
      />

      {detail && (
        <DetailModal framed onClose={() => setDetail(null)} label="Rincian permintaan desain"
          testId="dsr-detail-modal">
          <DesignRequestDetailPanel
            doc={detail} meta={meta}
            onChanged={(fresh) => { if (fresh) setDetail(fresh); paged.refresh(); loadSummary(); }}
            onClose={() => { setDetail(null); paged.refresh(); loadSummary(); }}
          />
        </DetailModal>
      )}
    </div>
  );
}
