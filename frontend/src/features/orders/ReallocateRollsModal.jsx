import { useEffect, useMemo, useState } from "react";
import { X, Layers, Loader2, AlertTriangle, Check, Repeat } from "lucide-react";
import axios, { API } from "../../services/apiClient";
import { formatQty } from "../../utils/formatters";

/**
 * ReallocateRollsModal — ALOKASI MANUAL Admin Sales (Ganti Roll) untuk 1 baris SO.
 * Roll lama tercentang (uncheck = dilepas kembali ke stok); roll available (FEFO)
 * bisa dipilih menggantikannya — roll terakhir otomatis DIPOTONG agar pas kebutuhan.
 * Submit → POST /sales-orders/{id}/items/{product_id}/reallocate (izin inventory.pegging).
 */
export default function ReallocateRollsModal({ order, item, onClose, onDone }) {
  const target = Math.round((Number(item.base_quantity || item.quantity) || 0) * 100) / 100;
  const currentRolls = useMemo(() => (order.allocations || [])
    .filter((a) => a.product_id === item.product_id)
    .flatMap((a) => (a.rolls || []).map((r) => ({
      id: r.roll_id, roll_no: r.roll_no, lot: r.lot, length: Number(r.length || 0),
      warehouse_name: a.warehouse_name, current: true,
    }))), [order, item]);

  const legacyAllocQty = useMemo(() => currentRolls.length > 0 ? 0 : (order.allocations || [])
    .filter((a) => a.product_id === item.product_id && !(a.rolls || []).length)
    .reduce((s, a) => s + Number(a.quantity || 0), 0), [order, item, currentRolls]);

  const [avail, setAvail] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [sel, setSel] = useState(() => currentRolls.map((r) => r.id)); // urutan pilih dijaga
  const byId = useMemo(() => {
    const m = {};
    currentRolls.forEach((r) => { m[r.id] = r; });
    avail.forEach((r) => {
      if (!m[r.id]) m[r.id] = { id: r.id, roll_no: r.roll_no, lot: r.lot,
        length: Number(r.length_remaining || 0), warehouse_name: r.warehouse_name, current: false };
    });
    return m;
  }, [currentRolls, avail]);

  useEffect(() => {
    axios.get(`${API}/inventory/rolls/available`, {
      params: { product_id: item.product_id, entity_id: order.entity_id,
                all_entities: false, sort: "fefo", skip: 0, limit: 60 },
    })
      .then((r) => setAvail(r.data?.items || []))
      .catch((e) => setError(e.response?.data?.detail || "Gagal memuat daftar roll."))
      .finally(() => setLoading(false));
  }, [item.product_id, order.entity_id]);

  // Roll LAMA dihitung penuh (backend mempertahankannya utuh); roll BARU diambil
  // berurutan sebesar sisa kebutuhan — roll terakhir dipotong (cut) agar pas.
  const plan = useMemo(() => {
    const kept = sel.map((id) => byId[id]).filter((r) => r?.current);
    const news = sel.map((id) => byId[id]).filter((r) => r && !r.current);
    const keptQty = kept.reduce((s, r) => s + r.length, 0);
    let need = Math.max(0, Math.round((target - keptQty) * 100) / 100);
    const takes = {};
    news.forEach((r) => {
      const take = Math.round(Math.min(need, r.length) * 100) / 100;
      takes[r.id] = take;
      need = Math.round((need - take) * 100) / 100;
    });
    const total = Math.round((keptQty + news.reduce((s, r) => s + (takes[r.id] || 0), 0)) * 100) / 100;
    return { keptQty: Math.round(keptQty * 100) / 100, takes, total,
             shortage: Math.max(0, Math.round((target - total) * 100) / 100),
             excess: Math.max(0, Math.round((total - target) * 100) / 100) };
  }, [sel, byId, target]);

  const toggle = (id) => {
    setSel((cur) => cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]);
  };

  const submit = async () => {
    setSaving(true); setError("");
    const roll_lines = sel
      .map((id) => byId[id])
      .filter((r) => r && (r.current || (plan.takes[r.id] || 0) > 0))
      .map((r) => ({ roll_id: r.id, take_qty: r.current ? 0 : plan.takes[r.id] }));
    try {
      await axios.post(`${API}/sales-orders/${order.id}/items/${item.product_id}/reallocate`,
        { roll_lines });
      onDone?.();
    } catch (e) {
      setError(e.response?.data?.detail || "Gagal mengganti roll.");
      setSaving(false);
    }
  };

  const Row = ({ r }) => {
    const on = sel.includes(r.id);
    const take = r.current ? r.length : (plan.takes[r.id] || 0);
    const unused = on && !r.current && take <= 0;
    return (
      <li key={r.id}>
        <button type="button" data-testid={`so-realloc-roll-${r.id}`} onClick={() => toggle(r.id)}
          className={`flex w-full items-center gap-2.5 px-3 py-2 text-left transition ${on ? "bg-[#EAF2FF]" : "hover:bg-[#FAFBFC]"}`}>
          <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded border ${on ? "border-[#0058CC] bg-[#0058CC] text-white" : "border-[#C7C7CC] bg-white"}`}>
            {on && <Check size={11} />}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="text-[12px] font-semibold text-[#1C1C1E]">{r.roll_no || r.id}</span>
              <span className="text-[10px] text-[#8E8E93]">· Lot {r.lot || "—"}</span>
              {r.current && <span className="rounded-full bg-[#E6F6EC] px-1.5 py-0.5 text-[9px] font-bold text-[#126E2C]">dipakai sekarang</span>}
              {unused && <span className="rounded-full bg-[#F5F5F7] px-1.5 py-0.5 text-[9px] font-bold text-[#8E8E93]">tidak terpakai — kebutuhan sudah penuh</span>}
            </div>
            <p className="mt-0.5 text-[10.5px] text-[#6B6B73]">{r.warehouse_name || "—"}</p>
          </div>
          <span className="shrink-0 text-right">
            <span className="block text-[12.5px] font-bold tabular-nums">{formatQty(r.length)}</span>
            {on && !r.current && take > 0 && take < r.length - 0.01 && (
              <span className="block text-[9px] font-semibold text-[#B26A00]">potong: ambil {formatQty(take)}</span>
            )}
          </span>
        </button>
      </li>
    );
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}>
      <div data-testid="so-realloc-modal" onClick={(e) => e.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-xl bg-white shadow-2xl">
        <div className="flex items-center gap-2 border-b border-[#EFF0F2] px-4 py-3">
          <Repeat size={15} className="text-[#0058CC]" />
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-bold text-[#1C1C1E]">Ganti Roll — Alokasi Manual</p>
            <p className="truncate text-[10.5px] text-[#6B6B73]">{item.product_name} · kebutuhan <b className="tabular-nums">{formatQty(target)}</b> {item.base_unit || item.unit}</p>
          </div>
          <button data-testid="so-realloc-close" className="icon-button" onClick={onClose} aria-label="Tutup"><X size={15} /></button>
        </div>

        <div className="max-h-[52vh] overflow-y-auto">
          {legacyAllocQty > 0 && (
            <p data-testid="so-realloc-no-roll-detail" className="flex items-start gap-1.5 bg-[#FFF7EF] px-3 py-2 text-[10.5px] text-[#8C4A00]">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" />
              Baris ini tercatat teralokasi <b className="tabular-nums">{formatQty(legacyAllocQty)}</b> tanpa rincian roll (alokasi lama). Memilih roll di bawah lalu menyimpan akan menggantikannya dengan alokasi roll yang jelas.
            </p>
          )}
          {currentRolls.length > 0 && (
            <>
              <p className="bg-[#FAFBFC] px-3 py-1.5 text-[10px] font-bold uppercase text-[#6B6B73]">Roll saat ini (hilangkan centang untuk melepas)</p>
              <ul className="divide-y divide-[#F2F3F5]">{currentRolls.map((r) => <Row key={r.id} r={r} />)}</ul>
            </>
          )}
          <p className="flex items-center gap-1.5 border-t border-[#EFF0F2] bg-[#FAFBFC] px-3 py-1.5 text-[10px] font-bold uppercase text-[#6B6B73]">
            <Layers size={11} className="text-[#0058CC]" /> Roll tersedia — milik entitas ini (FEFO)
          </p>
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-6 text-[12px] text-[#6B6B73]"><Loader2 size={15} className="animate-spin" /> Memuat roll…</div>
          ) : avail.length === 0 ? (
            <p className="px-3 py-5 text-center text-[12px] text-[#8E8E93]">Tidak ada roll tersedia lain untuk produk ini.</p>
          ) : (
            <ul className="divide-y divide-[#F2F3F5]">
              {avail.filter((r) => !currentRolls.some((c) => c.id === r.id)).map((r) => <Row key={r.id} r={byId[r.id]} />)}
            </ul>
          )}
        </div>

        <div className="border-t border-[#EFF0F2] bg-[#FAFBFC] px-4 py-3">
          {error && (
            <p data-testid="so-realloc-error" className="mb-2 flex items-start gap-1.5 rounded-md bg-[#FDECEA] px-2 py-1.5 text-[11px] text-[#C0392B]">
              <AlertTriangle size={12} className="mt-0.5 shrink-0" /> {error}
            </p>
          )}
          <div className="mb-2 flex items-center justify-between text-[11.5px]">
            <span className="text-[#6B6B73]">Total teralokasi</span>
            <span data-testid="so-realloc-total" className="font-bold tabular-nums">{formatQty(plan.total)} / {formatQty(target)}</span>
          </div>
          {plan.shortage > 0.01 && (
            <p className="mb-2 rounded-md bg-[#FFF7EF] px-2 py-1.5 text-[10.5px] text-[#8C4A00]">
              Kurang <b>{formatQty(plan.shortage)}</b> — sisanya akan tercatat sebagai <b>backorder</b> (menunggu stok).
            </p>
          )}
          {plan.excess > 0.01 && (
            <p className="mb-2 rounded-md bg-[#FFF7EF] px-2 py-1.5 text-[10.5px] text-[#8C4A00]">
              Roll lama yang dipertahankan melebihi kebutuhan {formatQty(plan.excess)} — lepaskan salah satu bila ingin pas.
            </p>
          )}
          <button data-testid="so-realloc-submit" disabled={saving || sel.length === 0}
            onClick={submit} className="primary-button w-full justify-center py-2 text-[12.5px] disabled:opacity-50">
            {saving ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />} Simpan Alokasi Manual
          </button>
        </div>
      </div>
    </div>
  );
}
