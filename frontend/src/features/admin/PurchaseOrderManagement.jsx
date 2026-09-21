import { useEffect, useMemo, useState } from "react";
import { Plus, Package, ChevronDown, Boxes, ShoppingBag, GitBranch, Search, Clock } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { parseDecimal } from "../../utils/decimalInput";
import { formatCurrency } from "../../utils/formatters";
import { getStatusBadge, billingState, lateState } from "./po/poUtils";
import POCreateForm from "./po/POCreateForm";
import PODetailPanel from "./po/PODetailPanel";
import POCompactPanel from "./po/POCompactPanel";
import { receiptVarianceSummary } from "./po/POReceiptVariancePanel";
import DetailPopup from "../../components/DetailPopup";
import POAmendModal from "./po/POAmendModal";
import MakloonOrderCreateModal from "../purchasing/MakloonOrderCreateModal";
import ConfirmModal from "../../components/ConfirmModal";
import FormModal from "../../components/FormModal";
import ErrorNotice from "../../components/ErrorNotice";
import LineFilter from "../../components/LineFilter";   // FASE L
import PaginationBar from "../../components/PaginationBar";
import { usePagedList } from "../../hooks/usePagedList";

// FASE P6 — kolom Unduh CSV (mengikuti kolom tabel + nominal yang di layar tampil kecil
// di bawah nama supplier).
import { qtyDualCsvColumns } from "../../utils/qtyDualCsv";   // FASE U — dua satuan di CSV

const CSV_COLUMNS = [
  { key: "po_number", header: "Nomor PO" },
  { header: "Tanggal", type: "date", get: (r) => r.order_date || r.created_at },
  { key: "supplier_name", header: "Supplier" },
  { key: "warehouse_name", header: "Gudang" },
  { header: "Jumlah Item", type: "int", get: (r) => r.items?.length || 0 },
  // FASE U — dua satuan, DUA pasang: yang DIPESAN (diketik saat memesan) dan yang
  // benar-benar DITERIMA (turunan dari roll yang lahir di gudang). Dipisah supaya
  // selisihnya terlihat di lembar kerja tanpa harus membuka dokumennya satu-satu.
  ...qtyDualCsvColumns({ rollHeader: "Roll Dipesan", measureHeader: "Jumlah Dipesan" }),
  ...qtyDualCsvColumns({ rollField: "received_rolls", rollHeader: "Roll Diterima",
    measureHeader: "Jumlah Diterima", measureFields: ["received_qty"] }),
  { header: "Total", type: "num", get: (r) => Number(r.grand_total ?? r.total_amount ?? 0) },
  { key: "status", header: "Status" },
  { header: "Tgl Kirim Diharap", get: (r) => String(r.expected_delivery_date || "").slice(0, 10) },
  { header: "Telat (hari)", type: "int", get: (r) => lateState(r)?.days || "" },
];

/**
 * PurchaseOrderManagement
 *
 * Manage Purchase Orders untuk inbound receiving workflow.
 * Create PO → Auto-create inbound tasks → Staff scan & receive.
 *
 * Sub-komponen (colocated di po/):
 *   - POCreateForm    — form buat PO baru
 *   - PODetailPanel   — panel detail PO dipilih
 *   - poUtils         — getStatusBadge helper
 */
export default function PurchaseOrderManagement({ user, selectedEntity, onApprovePO, focusDoc, onClearFocus, onOpenDocument }) {
  const [products, setProducts] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [search, setSearch] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [makloonMode, setMakloonMode] = useState(null);  // null | "buy_process" | "process_only"
  const [menuOpen, setMenuOpen] = useState(false);
  const [selectedPO, setSelectedPO] = useState(null);
  const [showFullDetail, setShowFullDetail] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [confirm, setConfirm] = useState(null); // { title, message, confirmLabel, danger, withReason, onConfirm }
  const [amendPO, setAmendPO] = useState(null);  // Phase 7.2 — PO yang sedang direvisi
  const [amending, setAmending] = useState(false);

  // P2 — paginasi server-side + pencarian (po_number / supplier).
  // FASE L — chip lini disaring di SERVER (daftar berhalaman).
  const [lineFilter, setLineFilter] = useState("");
  const [lateOnly, setLateOnly] = useState(false);   // chip "Terlambat" — disaring SERVER
  const poParams = useMemo(() => ({
    ...(lineFilter ? { line: lineFilter } : {}),
    ...(lateOnly ? { late: 1 } : {}),
  }), [lineFilter, lateOnly]);
  const paged = usePagedList("/purchase-orders", { pageSize: 20, search, params: poParams });
  const pos = paged.items;
  const loading = paged.loading;
  const fetchPOs = paged.refresh;

  const emptyForm = {
    supplier_id: "", supplier_name: "", supplier_contact: "", warehouse_id: "",
    items: [], expected_delivery_date: "", notes: "",
    order_discount_percent: 0, tax_mode: "",   // P0-1 — diskon order + mode PPN Masukan
    budget_dimension: "account", budget_key: "",  // R6.3 — tag anggaran (opsional)
    created_by: user?.name || "Admin",
  };
  const [formData, setFormData] = useState(emptyForm);
  // Fase A · PS-09/D-19 — `expected_grade` WAJIB dipilih user (tidak ada default).
  // FASE U — dua satuan: `qty_rolls` (jumlah gulungan yang DIPESAN — rencana) dan
  // `unit_factor` (panjang 1 panel PADA PESANAN INI; hanya untuk satuan bertanda
  // "faktor per dokumen" di master satuan — server menolak yang lain).
  const [newItem, setNewItem] = useState({ product_id: "", quantity: 0, unit: "meter", price: 0, discount_percent: 0, expected_grade: "", qty_rolls: "", unit_factor: "" });

  useEffect(() => { fetchMasterData(); }, []); // eslint-disable-line

  const fetchMasterData = async () => {
    try {
      const [pRes, wRes, sRes] = await Promise.all([
        axios.get(`${API}/products`).catch(() => ({ data: [] })),
        axios.get(`${API}/warehouses`).catch(() => ({ data: [] })),
        axios.get(`${API}/suppliers`).catch(() => ({ data: [] })),
      ]);
      setProducts(Array.isArray(pRes.data) ? pRes.data : []);
      setWarehouses(Array.isArray(wRes.data) ? wRes.data : []);
      setSuppliers(Array.isArray(sRes.data) ? sRes.data : []);
    } catch (e) { /* non-blocking */ }
  };

  const handleAddItem = () => {
    if (!newItem.product_id || !(parseDecimal(newItem.quantity) > 0)) {
      setError("Pilih produk dan masukkan qty yang valid (> 0)."); return;
    }
    // Fase A · D-19 — grade yang diharapkan WAJIB dipilih (server juga menolak).
    if (!newItem.expected_grade) {
      setError("Pilih Grade yang diharapkan untuk item ini (tidak ada nilai default)."); return;
    }
    setError("");
    const product = products.find((p) => p.id === newItem.product_id);
    setFormData({
      ...formData,
      items: [...formData.items, {
        ...newItem,
        price: parseDecimal(newItem.price) > 0 ? newItem.price : product?.price || 0,
        discount_percent: Number(newItem.discount_percent) || 0,
        // FASE U — kosong berarti "tidak menyebut jumlah roll" (null), BUKAN 0 roll.
        qty_rolls: newItem.qty_rolls === "" || newItem.qty_rolls === null
          ? null : Math.max(0, parseInt(newItem.qty_rolls, 10) || 0),
        unit_factor: newItem.unit_factor === "" ? null : parseDecimal(newItem.unit_factor),
        unit_factor_to: newItem.unit_factor ? (product?.base_unit || "yard") : "",
      }],
    });
    setNewItem({ product_id: "", quantity: 0, unit: "meter", price: 0, discount_percent: 0, expected_grade: "" });
  };

  const handleRemoveItem = (index) => {
    setFormData({ ...formData, items: formData.items.filter((_, i) => i !== index) });
  };

  const handleCreatePO = async () => {
    if (!formData.supplier_name || !formData.warehouse_id) {
      setError("Nama supplier dan gudang wajib diisi."); return;
    }
    if (formData.items.length === 0) {
      setError("Tambahkan minimal 1 item."); return;
    }
    setError("");
    setCreating(true);
    try {
      const res = await axios.post(`${API}/purchase-orders`, formData);
      const po = res.data;
      // R6.3 — tampilkan peringatan anggaran (mode WARN) bila ada.
      const bWarn = (po.budget_check?.warnings || []).join(" · ");
      setNotice(`${po.approval_required
        ? `Purchase Order ${po.po_number} dibuat. Menunggu APPROVAL role '${po.required_approval_role}' sebelum inbound task dibuat.`
        : `Purchase Order ${po.po_number} dibuat & inbound task otomatis dibuat.`}${bWarn ? ` ⚠️ Anggaran: ${bWarn}` : ""}`);
      setShowCreateForm(false);
      setFormData(emptyForm);
      fetchPOs();
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal membuat PO.");
    } finally {
      setCreating(false);
    }
  };

  const handleViewDetail = async (poId) => {
    try {
      const res = await axios.get(`${API}/purchase-orders/${poId}`);
      setSelectedPO(res.data);
    } catch {
      setError("Gagal memuat detail PO.");
    }
  };

  // EPIC6 — deep-link: auto-buka detail PO saat dinavigasi dari Document Hub.
  useEffect(() => {
    if (focusDoc?.focus_type === "purchase_order" && focusDoc?.focus_id) {
      handleViewDetail(focusDoc.focus_id);
      onClearFocus?.();
    }
  }, [focusDoc]); // eslint-disable-line

  const handleCancelPO = (poId) => {
    const po = pos.find((p) => p.id === poId);
    setConfirm({
      title: "Batalkan Pesanan Pembelian",
      message: `Yakin membatalkan ${po?.po_number || "PO ini"}? Tindakan ini tidak dapat dibatalkan.`,
      confirmLabel: "Batalkan PO",
      danger: true,
      onConfirm: async () => {
        try {
          await axios.post(`${API}/purchase-orders/${poId}/cancel`);
          setNotice(`${po?.po_number || "PO"} berhasil dibatalkan.`);
          setConfirm(null);
          await fetchPOs();
          setSelectedPO(null);
        } catch (e) {
          setError(e.response?.data?.detail || "Gagal membatalkan PO.");
          setConfirm(null);
        }
      },
    });
  };

  const handleApprovePO = async (poId) => {
    if (!onApprovePO) return;
    const result = await onApprovePO(poId);
    if (result) {
      // Rantai approval bisa bertingkat — jangan bilang "inbound task dibuat"
      // sebelum SELURUH tingkat setuju (dulu tingkat 1 dari 2 pun dilaporkan selesai).
      const po = result?.data || result;
      const stillWaiting = (po?.status || "") === "waiting_approval";
      const chain = Array.isArray(po?.approval_chain) ? po.approval_chain : [];
      const approvedLv = chain.filter((l) => l.status === "approved").length;
      setNotice(stillWaiting
        ? `Disetujui tingkat ${approvedLv || 1} dari ${chain.length || "?"} — masih menunggu peran ${(po?.required_approval_role || "berikutnya").toUpperCase()}.`
        : "PO disetujui penuh. Inbound task dibuat.");
      await fetchPOs(); await handleViewDetail(poId);
    }
  };

  const handleCloseShort = (poId) => {
    const po = pos.find((p) => p.id === poId);
    setConfirm({
      title: "Tutup PO (Kurang Terima)",
      message: `Tutup ${po?.po_number || "PO ini"}? Tugas barang masuk yang masih terbuka akan dibatalkan.`,
      confirmLabel: "Tutup PO",
      danger: false,
      withReason: true,
      reasonLabel: "Alasan tutup-kurang",
      reasonPlaceholder: "Mis. sisa barang tidak akan dikirim supplier.",
      onConfirm: async (reason) => {
        try {
          await axios.post(`${API}/purchase-orders/${poId}/close`, { reason });
          setNotice(`${po?.po_number || "PO"} ditutup (kurang terima).`);
          setConfirm(null);
          await fetchPOs();
          await handleViewDetail(poId);
        } catch (e) {
          setError(e.response?.data?.detail || "Gagal menutup PO.");
          setConfirm(null);
        }
      },
    });
  };

  const handleCloseForm = () => {
    setShowCreateForm(false);
    setFormData(emptyForm);
  };

  // Phase 7.2 — submit amandemen PO (re-approval penuh di backend).
  const handleSubmitAmend = async (payload) => {
    if (!amendPO) return;
    setAmending(true);
    try {
      const res = await axios.post(`${API}/purchase-orders/${amendPO.id}/amend`, payload);
      const po = res.data;
      setNotice(po.approval_required
        ? `PO ${po.po_number} direvisi (v${po.version}). Menunggu APPROVAL role '${po.required_approval_role}' sebelum inbound task dibuat.`
        : `PO ${po.po_number} direvisi (v${po.version}). Inbound task diperbarui otomatis.`);
      setAmendPO(null);
      await fetchPOs();
      await handleViewDetail(po.id);
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal merevisi PO.");
    } finally {
      setAmending(false);
    }
  };

  return (
    <div data-testid="po-management-panel">
      {notice && <div className="notice-bar success" data-testid="po-mgmt-notice"><span>{notice}</span><button onClick={() => setNotice("")}>×</button></div>}
      {error && !showCreateForm && <ErrorNotice message={error || paged.error} onRetry={fetchPOs} onDismiss={() => setError("")} testId="po-mgmt-error" />}

      {/* Top bar */}
      <div className="section-card mb-3">
        <div className="section-head">
          <div className="flex items-center gap-2 min-w-0">
            <span className="kicker">Purchasing</span>
            <h2 data-testid="panel-title">Purchase Orders</h2>
          </div>
          <div className="flex items-center gap-2">
            <button data-testid="po-filter-late" onClick={() => setLateOnly((v) => !v)}
              title="Hanya PO yang lewat tanggal kirim dijanjikan supplier & masih menunggu barang"
              className={`flex items-center gap-1 rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-colors ${
                lateOnly ? "bg-[#C0341D] text-white" : "border border-red-200 bg-red-50 text-red-600 hover:bg-red-100"}`}>
              <Clock size={13} /> Terlambat
            </button>
            <LineFilter value={lineFilter} onChange={setLineFilter} storageKey="purchase-orders"
                        allowed={user?.allowed_line_codes} className="!py-1.5"
                        testId="po-line-filter" />
            <div className="relative w-56 max-w-[40vw]">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#9A9BA3]" />
              <input data-testid="po-search" value={search} onChange={(e) => setSearch(e.target.value)}
                className="field !pl-8 !py-1.5 text-[12px]" placeholder="Cari No. PO / supplier..." />
            </div>
            {user?.role !== "finance" && (
            <div className="relative">
            <button data-testid="create-po-button"
              onClick={() => setMenuOpen((o) => !o)}
              className="primary-button">
              <Plus size={13} /> Buat <ChevronDown size={13} />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-20" onClick={() => setMenuOpen(false)} />
                <div data-testid="procure-mode-menu" className="absolute right-0 z-30 mt-1 w-72 overflow-hidden rounded-xl border border-[#EFF0F2] bg-white py-1 shadow-2xl">
                  <p className="px-3 pb-1 pt-1.5 text-[10px] font-bold uppercase tracking-wide text-[#9A9BA3]">Mode Pengadaan</p>
                  <button data-testid="mode-finished-goods" className="flex w-full items-start gap-2.5 px-3 py-2 text-left hover:bg-[#F5F8FF]"
                    onClick={() => { setMenuOpen(false); setMakloonMode(null); setShowCreateForm(true); }}>
                    <ShoppingBag size={15} className="mt-0.5 shrink-0 text-[#0058CC]" />
                    <span><span className="block text-[12.5px] font-semibold text-[#1B2733]">Beli Finished Goods</span><span className="block text-[10.5px] text-[#6B6B73]">Beli putus barang jadi dari supplier (PO standar).</span></span>
                  </button>
                  <button data-testid="mode-raw-process" className="flex w-full items-start gap-2.5 px-3 py-2 text-left hover:bg-[#F5F8FF]"
                    onClick={() => { setMenuOpen(false); setShowCreateForm(false); setMakloonMode("buy_process"); }}>
                    <Boxes size={15} className="mt-0.5 shrink-0 text-[#0058CC]" />
                    <span><span className="block text-[12.5px] font-semibold text-[#1B2733]">Raw Material & Proses</span><span className="block text-[10.5px] text-[#6B6B73]">Beli bahan lalu kirim ke makloon (WIP-at-vendor).</span></span>
                  </button>
                  <button data-testid="mode-process-only" className="flex w-full items-start gap-2.5 px-3 py-2 text-left hover:bg-[#F5F8FF]"
                    onClick={() => { setMenuOpen(false); setShowCreateForm(false); setMakloonMode("process_only"); }}>
                    <GitBranch size={15} className="mt-0.5 shrink-0 text-[#0058CC]" />
                    <span><span className="block text-[12.5px] font-semibold text-[#1B2733]">Proses Saja</span><span className="block text-[10.5px] text-[#6B6B73]">Bahan dari stok sendiri, kirim ke makloon.</span></span>
                  </button>
                </div>
              </>
            )}
          </div>
            )}
          </div>
        </div>
      </div>

      {/* Create Form */}
      {/* FASE P5 — form Buat PO menjadi POP-UP: daftar PO di belakang tetap terlihat.
          Dulu kartunya menyelip di tengah halaman dan mendorong tabel PO ke bawah
          lipatan, sehingga pengguna sering tidak sadar formnya sudah terbuka. */}
      <FormModal
        open={showCreateForm}
        onClose={handleCloseForm}
        title="Buat Pesanan Pembelian Baru"
        subtitle="Pilih pemasok & gudang tujuan, lalu tambahkan barang yang dibeli"
        icon={Plus}
        size="xl"
        testId="po-create-modal"
      >
        <POCreateForm
          variant="modal"
          formData={formData} setFormData={setFormData}
          newItem={newItem} setNewItem={setNewItem}
          products={products} warehouses={warehouses} suppliers={suppliers}
          submitting={creating} error={showCreateForm ? error : ""}
          onSubmit={handleCreatePO} onCancel={handleCloseForm}
          onAddItem={handleAddItem} onRemoveItem={handleRemoveItem}
        />
      </FormModal>

      {/* Two-panel: PO table + detail */}
      <div className="grid gap-3 lg:grid-cols-[1fr_360px]">
        {/* PO Table */}
        <div className="section-card">
          <div className="overflow-x-auto">
            <div className="min-w-[860px] grid grid-cols-[115px_1fr_110px_120px_110px_62px_150px] gap-2 px-3 py-1.5 bg-[#FAFBFC] text-[10px] font-bold uppercase text-[#6B6B73] border-b border-[#EFF0F2]">
              <span>Nomor</span><span>Supplier</span><span>Gudang</span><span>Qty Pesan / Terima</span><span className="text-right">Total</span><span>Tanggal</span><span>Status</span>
            </div>
            {loading ? (
              <div className="py-8 text-center text-[12px] text-[#6B6B73]">Memuat…</div>
            ) : pos.length === 0 ? (
              <div className="py-10 text-center text-[12px] text-[#6B6B73]">
                <Package className="mx-auto mb-2 text-gray-300" size={28} />
                <p>{lateOnly ? "Tidak ada PO terlambat — semua kiriman masih dalam janji supplier. 🎉" : "Belum ada Pesanan Pembelian"}</p>
              </div>
            ) : (
              <div className="divide-y divide-[#EFF0F2]">
                {pos.map((po) => {
                  /* UI/UX 2026-06 — kolom tengah dulu kosong melompong; sekarang diisi
                     qty pesan vs terima + tanggal supaya tabel informatif tanpa buka detail. */
                  const items = po.items || [];
                  const qOrder = items.reduce((s, it) => s + Number(it.quantity || 0), 0);
                  const qRecv = items.reduce((s, it) => s + Number(it.received_qty || 0), 0);
                  const units = [...new Set(items.map((it) => it.unit).filter(Boolean))];
                  const unit = units.length === 1 ? units[0] : "";
                  // b/d — badge penagihan di baris + sembunyikan "terima 0" bila barang
                  // memang belum mungkin diterima (belum disetujui / ditolak / batal).
                  const bill = billingState(po);
                  const late = lateState(po);
                  const rvar = receiptVarianceSummary(po.receipt_variances);
                  const showReceive = !["waiting_approval", "rejected", "cancelled"].includes(po.status);
                  return (
                  <div key={po.id} data-testid={`po-card-${po.id}`}
                    className={`min-w-[860px] grid grid-cols-[115px_1fr_110px_120px_110px_62px_150px] gap-2 items-center px-3 py-2.5 cursor-pointer hover:bg-[#FAFBFC] transition-colors ${selectedPO?.id === po.id ? "bg-[#EFF4FF] border-l-2 border-[#007AFF]" : ""}`}
                    onClick={() => handleViewDetail(po.id)}>
                    <p data-testid={`po-number-${po.id}`} className="text-[12px] font-bold text-[#007AFF] whitespace-nowrap">{po.po_number}</p>
                    <div className="min-w-0">
                      <p data-testid={`po-supplier-${po.id}`} className="text-[11.5px] font-semibold truncate">{po.supplier_name}</p>
                      <p className="text-[10.5px] text-[#6B6B73]">{items.length} item</p>
                    </div>
                    <p className="text-[11px] text-[#3C3C43] truncate" title={po.warehouse_name}>{po.warehouse_name}</p>
                    <div className="text-[11px] tabular-nums" data-testid={`po-qty-${po.id}`}>
                      <p className="font-semibold">{new Intl.NumberFormat("id-ID").format(qOrder)} {unit}</p>
                      {showReceive && (
                        <p className={`text-[10px] ${qRecv >= qOrder && qOrder > 0 ? "text-green-600" : "text-[#6B6B73]"}`}>
                          terima {new Intl.NumberFormat("id-ID").format(qRecv)}{qOrder > 0 ? ` (${Math.round((qRecv / qOrder) * 100)}%)` : ""}
                        </p>
                      )}
                    </div>
                    <p className="text-right text-[11.5px] font-bold tabular-nums" data-testid={`po-total-${po.id}`}>{formatCurrency(po.grand_total ?? po.total_amount)}</p>
                    <p className="text-[10.5px] text-[#6B6B73]">{po.created_at ? new Date(po.created_at).toLocaleDateString("id-ID", { day: "2-digit", month: "short" }) : "—"}</p>
                    <div className="flex flex-col items-start gap-0.5 min-w-0">
                      {getStatusBadge(po.status)}
                      {bill && (
                        <span data-testid={`po-row-billing-${po.id}`}
                          className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[9.5px] font-semibold ${bill.cls}`}>{bill.label}</span>
                      )}
                      {late && (
                        <span data-testid={`po-row-late-${po.id}`} title={`Janji kirim supplier: ${late.eta}`}
                          className={`whitespace-nowrap rounded px-1.5 py-0.5 text-[9.5px] font-semibold ${late.cls}`}>{late.label}</span>
                      )}
                      {rvar && (
                        <span data-testid={`po-row-variance-${po.id}`} title={`Catatan gudang: ${rvar.label}`}
                          className="whitespace-nowrap rounded px-1.5 py-0.5 text-[9.5px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">Selisih terima {rvar.label}</span>
                      )}
                    </div>
                  </div>
                  );
                })}
              </div>
            )}
          </div>
          <div className="px-3 py-2 border-t border-[#EFF0F2]">
            <PaginationBar
              testId="po-pager" label="PO"
              page={paged.page} pageSize={paged.pageSize} total={paged.total}
              hasMore={paged.hasMore} loading={paged.loading}
              onPrev={paged.prev} onNext={paged.next} onPageSize={paged.setPageSize}
              exportConfig={{ columns: CSV_COLUMNS, rows: pos, fetchAll: paged.fetchAll,
                filename: "pesanan-pembelian" }}
            />
          </div>
        </div>

        {/* UI/UX 2026-06 — panel kanan = RINGKASAN + aksi lifecycle (tanpa scroll);
            isi lengkap (item, pajak, penagihan, timeline, referensi) di pop-up. */}
        <POCompactPanel
          po={selectedPO}
          currentUser={user}
          onClose={() => setSelectedPO(null)}
          onOpenFull={() => setShowFullDetail(true)}
          onApprove={handleApprovePO}
          onCancel={handleCancelPO}
          onCloseShort={handleCloseShort}
          onAmend={(po) => { setError(""); setAmendPO(po); }}
          onOpenDocument={onOpenDocument}
        />
      </div>

      <DetailPopup open={showFullDetail && !!selectedPO} onClose={() => setShowFullDetail(false)}
        title={selectedPO?.po_number} subtitle={selectedPO?.supplier_name}
        testId="po-detail-popup">
        {selectedPO && (
          <PODetailPanel
            po={selectedPO}
            currentUser={user}
            embedded
            onClose={() => setShowFullDetail(false)}
            onApprove={handleApprovePO}
            onCancel={handleCancelPO}
            onCloseShort={handleCloseShort}
            onAmend={(po) => { setShowFullDetail(false); setError(""); setAmendPO(po); }}
            onOpenDocument={onOpenDocument}
          />
        )}
      </DetailPopup>

      {makloonMode && (
        <MakloonOrderCreateModal
          selectedEntity={selectedEntity}
          initialMode={makloonMode}
          lockMode
          onClose={() => setMakloonMode(null)}
          onSaved={() => { setMakloonMode(null); setNotice("Order makloon berhasil dibuat — lihat tab 'Order Makloon'."); }}
          onError={setError}
        />
      )}

      {amendPO && (
        <POAmendModal
          po={amendPO}
          products={products}
          warehouses={warehouses}
          suppliers={suppliers}
          submitting={amending}
          onSubmit={handleSubmitAmend}
          onClose={() => setAmendPO(null)}
        />
      )}

      <ConfirmModal
        open={!!confirm}
        title={confirm?.title}
        message={confirm?.message}
        confirmLabel={confirm?.confirmLabel}
        danger={confirm?.danger}
        withReason={confirm?.withReason}
        reasonLabel={confirm?.reasonLabel}
        reasonPlaceholder={confirm?.reasonPlaceholder}
        onConfirm={confirm?.onConfirm}
        onCancel={() => setConfirm(null)}
        testId="po-confirm-modal"
      />
    </div>
  );
}
