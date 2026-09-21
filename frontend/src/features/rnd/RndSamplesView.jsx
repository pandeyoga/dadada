/**
 * RndSamplesView — **Permintaan Sample** (labdip · handfeel · proofing), dibuat SEMIRIP
 * mungkin dengan papan Permintaan Desain: kartu ringkasan dari agregat SERVER, tab
 * **Papan** (kolom per status) dan **Daftar** (tabel), penyaring jenis dari MASTER
 * `/api/rnd/sample-types`, lalu pop-up rincian bergaya studio dengan tab per jenis.
 *
 * Mekanisme di server TIDAK berubah (kirim ke supplier → round → nilai → pemenang);
 * yang diperbarui hanya wajah & alur klik-nya.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { Beaker, Plus, RefreshCw } from "lucide-react";
import ErrorNotice from "../../components/ErrorNotice";
import LineFilter from "../../components/LineFilter";
import DetailModal from "../../components/DetailModal";
import EntityBadge from "../../components/EntityBadge";
import { formatDateId } from "../../components/KNDatePicker";
import { RevisionBadge, RevisionFilter, sampleRevisionCount } from "../../components/RevisionProgress";
import { EmptyState } from "../finance/financeShared";
import SampleFormModal from "./SampleFormModal";
import SampleDetailPanel from "./SampleDetailPanel";
import SampleBoardCard, { TypeBadge } from "./SampleBoardCard";
import { listSamples, sampleTypes } from "./rndApi";
import { errMsg, SAMPLE_BOARD_ORDER, SAMPLE_STATUS_META } from "./rndMeta";
import { sampleTypesOf } from "./sampleTypeMeta";
import { roleIs } from "../../config/roles";

const DOT = { "pill-muted": "bg-[#B4B4BB]", "pill-info": "bg-[#0058CC]", "pill-warning": "bg-[#E08A00]", "pill-success": "bg-[#1A7A3A]", "pill-danger": "bg-[#C62828]" };

export default function RndSamplesView({ currentUser, selectedEntity, focus, onFocusConsumed }) {
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState({});
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("board");
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [minRevision, setMinRevision] = useState("");
  const [lineFilter, setLineFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [openId, setOpenId] = useState("");
  const [focusRoundId, setFocusRoundId] = useState("");
  const [prefill, setPrefill] = useState(null);
  const [pendingNumber, setPendingNumber] = useState("");

  const role = currentUser?.role;
  const canCreate = roleIs(role, ["admin", "manager", "sales", "md"]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const params = { limit: 300 };
      if (selectedEntity && selectedEntity !== "all") params.entity_id = selectedEntity;
      if (type) params.sample_type = type;
      if (lineFilter) params.line = lineFilter;
      const res = await listSamples(params);
      setRows(res?.items || []);
      setStats(res?.stats || {});
      setError("");
    } catch (e) {
      setError(errMsg(e, "Gagal memuat permintaan sample."));
    } finally { setLoading(false); }
  }, [selectedEntity, type, lineFilter]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const p = {};
    if (selectedEntity && selectedEntity !== "all") p.entity_id = selectedEntity;
    if (lineFilter) p.line = lineFilter;
    sampleTypes(p).then((r) => setTypes(Array.isArray(r) ? r : [])).catch(() => {});
  }, [selectedEntity, lineFilter]);

  // Deep-link masuk (Pustaka Warna / kartu desain / tautan "asal harga").
  useEffect(() => {
    if (!focus?.nonce) return;
    if (focus.sampleId) { setOpenId(focus.sampleId); setFocusRoundId(focus.roundId || ""); }
    else if (focus.sampleNumber) setPendingNumber(focus.sampleNumber);
    if (focus.colorId || focus.designId) {
      setPrefill({
        color_id: focus.colorId || "", design_id: focus.designId || "",
        need_design: Boolean(focus.designId),
        source_label: focus.colorLabel || focus.designLabel || "",
      });
      setShowForm(true);
    }
    onFocusConsumed?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus?.nonce]);

  useEffect(() => {
    if (!pendingNumber || rows.length === 0) return;
    const hit = rows.find((r) => r.number === pendingNumber);
    if (hit) { setOpenId(hit.id); setPendingNumber(""); }
  }, [pendingNumber, rows]);

  const filtered = useMemo(() => {
    const term = q.trim().toLowerCase();
    const minRev = Number(minRevision) || 0;
    return rows.filter((r) => {
      if (statusFilter && r.status !== statusFilter) return false;
      if (minRev && sampleRevisionCount(r) < minRev) return false;
      if (!term) return true;
      return [r.number, r.title, r.spec_number, r.color_target?.name, r.design_code, r.so_number,
        ...(r.participants || []).map((p) => p.supplier_name)]
        .some((v) => (v || "").toLowerCase().includes(term));
    });
  }, [rows, q, minRevision, statusFilter]);

  const grouped = useMemo(() => {
    const out = {};
    SAMPLE_BOARD_ORDER.forEach((s) => { out[s] = []; });
    filtered.forEach((r) => { (out[r.status] = out[r.status] || []).push(r); });
    return out;
  }, [filtered]);

  const typeChips = [{ value: "", label: "Semua jenis" }, ...types.map((t) => ({ value: t.value, label: t.label.split(" (")[0] }))];
  const statusChips = [{ key: "", label: "Semua" }, ...SAMPLE_BOARD_ORDER.map((s) => ({ key: s, label: SAMPLE_STATUS_META[s].label }))];
  const closeDetail = () => { setOpenId(""); setFocusRoundId(""); };

  return (
    <div data-testid="rnd-samples-view" className="grid gap-3">
      <ErrorNotice message={error} onRetry={load} onDismiss={() => setError("")} testId="rnd-samples-error" />

      <div className="section-card">
        <div className="section-head">
          <div className="flex min-w-0 items-center gap-2">
            <Beaker size={15} className="text-[#0058CC]" />
            <div className="min-w-0">
              <span className="kicker">R&amp;D</span>
              <h2 data-testid="rnd-samples-title" className="text-[13px] font-bold">Permintaan Sample</h2>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <LineFilter value={lineFilter} onChange={setLineFilter} storageKey="rnd-samples"
              allowed={currentUser?.allowed_line_codes} className="!py-1.5" testId="rnd-samples-line-filter" />
            <input data-testid="rnd-samples-search" className="field w-56 !py-1.5 !text-[11.5px]" value={q}
              onChange={(e) => setQ(e.target.value)} placeholder="Cari nomor / judul / supplier / warna…" />
            <button className="secondary-button !py-1.5" onClick={load} data-testid="rnd-samples-refresh">
              <RefreshCw size={12} /> Muat ulang
            </button>
            {canCreate && (
              <button className="primary-button" data-testid="rnd-sample-create-button" onClick={() => setShowForm(true)}>
                <Plus size={13} /> Buat Permintaan
              </button>
            )}
          </div>
        </div>
        {pendingNumber && (
          <div className="mb-2 rounded-lg bg-[#FFF6E5] px-3 py-2 text-[11.5px] text-[#8C4A00]" data-testid="rnd-samples-pending-number">
            Mencari permintaan <b>{pendingNumber}</b>… Bila tidak ditemukan, permintaan itu mungkin milik entitas (PT) lain.
          </div>
        )}
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6" data-testid="rnd-samples-stats">
          {[
            ["Total", stats.total ?? 0, "rnd-samples-kpi-total"],
            ["Terkirim", stats.sent ?? 0, "rnd-samples-kpi-sent"],
            ["Dikerjakan", stats.in_progress ?? 0, "rnd-samples-kpi-in-progress"],
            ["Ada ACC", stats.assessed ?? 0, "rnd-samples-kpi-assessed"],
            ["Pemenang dipilih", stats.decided ?? 0, "rnd-samples-kpi-decided"],
            ["Round terlambat", stats.overdue_rounds ?? 0, "rnd-samples-kpi-overdue"],
          ].map(([label, value, tid]) => (
            <div key={tid} className="rounded-lg border border-[#EFF0F2] bg-white px-3 py-2">
              <p className="text-[10px] font-bold uppercase tracking-wide text-[#9A9BA3]">{label}</p>
              <p data-testid={tid} className={`text-[15px] font-bold tabular-nums ${tid.endsWith("overdue") && value ? "text-[#C62828]" : "text-[#1C1C1E]"}`}>{value}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {[["board", "Papan"], ["list", "Daftar"]].map(([key, label]) => (
          <button key={key} data-testid={`rnd-samples-tab-${key}`}
            className={tab === key ? "primary-button !py-1.5" : "secondary-button !py-1.5"}
            onClick={() => setTab(key)}>{label}</button>
        ))}
        <span className="mx-1 h-4 w-px bg-[#E5E5EA]" />
        <div className="flex flex-wrap gap-1.5" data-testid="rnd-samples-filters">
          {typeChips.map((f) => (
            <button key={f.value || "all"} data-testid={`rnd-samples-filter-${f.value || "all"}`}
              onClick={() => setType(f.value)}
              className={`rounded-full border px-3 py-1 text-[11px] font-medium ${type === f.value
                ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#E5E5EA] bg-white text-[#3C3C43] hover:border-[#0058CC]"}`}>
              {f.label}
            </button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-1.5">
          <RevisionFilter value={minRevision} onChange={setMinRevision} testId="rnd-samples-revision-filter" />
          <span className="mx-1 h-4 w-px bg-[#E5E5EA]" />
          {statusChips.map((c) => (
            <button key={c.key || "all"} data-testid={`rnd-samples-chip-${c.key || "all"}`}
              className={`status-pill ${statusFilter === c.key ? "pill-info" : "pill-muted"}`}
              onClick={() => setStatusFilter(c.key)}>{c.label}</button>
          ))}
        </div>
      </div>

      {loading ? (
        <div data-testid="rnd-samples-loading" className="section-card grid gap-2">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-9 animate-pulse rounded-md bg-[#F2F2F5]" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="section-card">
          <EmptyState icon={Beaker} testId="rnd-samples-empty"
            title={minRevision ? `Tidak ada sample dengan revisi ≥ ${minRevision}` : "Belum ada permintaan sample"}
            hint={minRevision ? "Tidak ada yang tersendat di revisi berulang. Pilih \"Semua ronde\" untuk melihat seluruhnya."
              : canCreate ? "Buat permintaan labdip / handfeel / proofing, lalu kirim ke satu atau beberapa supplier untuk dibandingkan."
                : "Permintaan sample badan usaha ini akan muncul di sini."} />
        </div>
      ) : tab === "board" ? (
        <div data-testid="rnd-samples-board" className="grid grid-flow-col auto-cols-[minmax(215px,1fr)] gap-2 overflow-x-auto pb-1">
          {SAMPLE_BOARD_ORDER.map((s) => {
            const meta = SAMPLE_STATUS_META[s];
            return (
              <div key={s} data-testid={`rnd-samples-col-${s}`} className="rounded-xl border border-[#EFF0F2] bg-[#FAFBFC] p-2">
                <p className="mb-1.5 flex items-center justify-between text-[10.5px] font-bold uppercase tracking-wide text-[#6B6B73]">
                  <span className="flex items-center gap-1.5">
                    <span className={`inline-block h-2 w-2 rounded-full ${DOT[meta.cls] || DOT["pill-muted"]}`} />
                    {meta.label}
                  </span>
                  <span data-testid={`rnd-samples-col-count-${s}`} className="rounded-full bg-white px-1.5 tabular-nums">{grouped[s].length}</span>
                </p>
                <div className="grid gap-1.5">
                  {grouped[s].map((r) => <SampleBoardCard key={r.id} s={r} types={types} onOpen={() => setOpenId(r.id)} />)}
                  {grouped[s].length === 0 && <p className="px-1 py-1.5 text-[10.5px] text-[#B4B4BB]">— kosong —</p>}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="section-card">
          <div className="overflow-x-auto">
            <table className="w-full text-[11.5px]">
              <thead>
                <tr className="bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73]">
                  <th className="px-2 py-1.5 text-left">Nomor</th>
                  <th className="px-2 py-1.5 text-left">Judul</th>
                  <th className="px-2 py-1.5 text-left">Jenis</th>
                  <th className="px-2 py-1.5 text-left">Supplier</th>
                  <th className="px-2 py-1.5 text-left">Target</th>
                  <th className="px-2 py-1.5 text-left">Status</th>
                  <th className="px-2 py-1.5 text-left">Ronde</th>
                  <th className="px-2 py-1.5 text-right">Aksi</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((s) => {
                  const meta = SAMPLE_STATUS_META[s.status] || SAMPLE_STATUS_META.draft;
                  const overdue = (s.rounds || []).some((r) => r.overdue);
                  return (
                    <tr key={s.id} data-testid={`rnd-sample-row-${s.id}`} className="border-b border-[#F2F2F5] last:border-0">
                      <td className="px-2 py-1.5 font-semibold text-[#1C1C1E]">
                        <button className="link-button" data-testid={`rnd-sample-open-${s.id}`} onClick={() => setOpenId(s.id)}>{s.number}</button>
                      </td>
                      <td className="px-2 py-1.5 text-[#3C3C43]">
                        <span className="line-clamp-1">{s.title}</span>
                        <span className="flex items-center gap-1 text-[10px] text-[#8E8E93]"><EntityBadge entityId={s.entity_id} />{s.spec_number || ""}{s.so_number ? ` · ${s.so_number}` : ""}</span>
                      </td>
                      <td className="px-2 py-1.5"><span className="flex flex-wrap gap-1" data-testid={`rnd-sample-types-${s.id}`}>{sampleTypesOf(s).map((c) => <TypeBadge key={c} code={c} types={types} />)}</span></td>
                      <td className="px-2 py-1.5">{(s.participants || []).map((p) => p.supplier_name).join(", ") || "—"}</td>
                      <td className={`px-2 py-1.5 ${overdue ? "font-semibold text-[#A8221A]" : ""}`}>{s.target_date ? formatDateId(s.target_date, "dd MMM yyyy") : "—"}</td>
                      <td className="px-2 py-1.5"><span className={`status-pill ${meta.cls}`} data-testid={`rnd-sample-status-${s.id}`}>{meta.label}</span></td>
                      <td className="px-2 py-1.5"><RevisionBadge count={sampleRevisionCount(s)} testId={`rnd-sample-revision-${s.id}`} /></td>
                      <td className="px-2 py-1.5 text-right"><button className="link-button" data-testid={`rnd-sample-detail-${s.id}`} onClick={() => setOpenId(s.id)}>Detail</button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showForm && (
        <SampleFormModal selectedEntity={selectedEntity} prefill={prefill}
          onClose={() => { setShowForm(false); setPrefill(null); }}
          onSaved={(created) => { setShowForm(false); setPrefill(null); load(); setOpenId(created?.id || ""); }} />
      )}
      {openId && (
        <DetailModal framed onClose={closeDetail} label="Rincian sample" testId="sample-detail-modal">
          <SampleDetailPanel sampleId={openId} currentUser={currentUser} types={types}
            focusRoundId={focusRoundId} onClose={closeDetail} onChanged={load} />
        </DetailModal>
      )}
    </div>
  );
}
