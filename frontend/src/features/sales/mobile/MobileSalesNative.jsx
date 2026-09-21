import { useEffect, useMemo, useState } from "react";
import { Search, ChevronRight, ArrowLeft, Plus } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { formatCurrency } from "../../../utils/formatters";
import KNSelect from "../../../components/KNSelect";
import { offlinePost } from "../../../utils/offlineQueue";

const fmtDate = (s) => (s ? new Date(s).toLocaleDateString("id-ID", { day: "2-digit", month: "short" }) : "-");
const RET_STATUS = { draft: "Draf", submitted: "Diajukan", approved: "Disetujui", received: "Diterima", settled: "Selesai", rejected: "Ditolak", completed: "Selesai" };

/** Retur jual versi HP: daftar kartu + buat retur dari pesanan pelanggan (alasan + baris). */
export function MobileReturns({ user }) {
  const [rows, setRows] = useState(null);
  const [create, setCreate] = useState(false);
  const [sel, setSel] = useState(null);
  const load = () => axios.get(`${API}/sales-returns`).then((r) => setRows(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => setRows([]));
  useEffect(() => { load(); }, []);
  if (create) {
    return <MobileReturnCreate onBack={() => setCreate(false)} onDone={() => { setCreate(false); load(); }} />;
  }
  if (sel) return (
    <div className="space-y-2 p-3" data-testid="m-return-detail">
      <button className="m-subpage-back" onClick={() => setSel(null)} data-testid="m-return-back"><ArrowLeft size={17} /> Retur</button>
      <div className="m-card p-4 space-y-1 text-[12.5px]">
        <p className="text-[15px] font-bold">{sel.number}</p>
        <p className="m-muted">{sel.customer_name} · {fmtDate(sel.created_at)} · <b>{RET_STATUS[sel.status] || sel.status}</b></p>
        <p className="m-muted">Alasan: {sel.reason || sel.complaint_reason || "-"}</p>
        {(sel.items || []).map((it, i) => <div key={i} className="flex justify-between border-t border-[#EFF0F2] pt-1"><span>{it.product_name}</span><span className="tabular-nums">{it.quantity} {it.unit} · {formatCurrency(it.amount || it.subtotal || 0)}</span></div>)}
        <div className="flex justify-between border-t border-[#EFF0F2] pt-1 font-bold"><span>Total</span><span className="tabular-nums">{formatCurrency(sel.total_amount || sel.grand_total || 0)}</span></div>
      </div>
    </div>);
  return (
    <div className="space-y-2 p-3" data-testid="m-returns">
      <button className="primary-button w-full py-3 flex items-center justify-center gap-2" onClick={() => setCreate(true)} data-testid="m-return-new"><Plus size={16} /> Buat retur jual</button>
      {rows === null && <p className="text-xs m-muted">Memuat retur…</p>}
      {rows && rows.length === 0 && <p className="text-xs m-muted" data-testid="m-returns-empty">Belum ada retur.</p>}
      {(rows || []).map((r) => (
        <button key={r.id} className="m-card m-press w-full p-3 text-left" onClick={() => setSel(r)} data-testid={`m-return-${r.id}`}>
          <div className="flex items-center gap-2"><div className="min-w-0 flex-1"><p className="text-[13px] font-bold">{r.number} <span className="ml-1 rounded bg-[#F2F3F5] px-1.5 text-[10px] font-semibold">{RET_STATUS[r.status] || r.status}</span></p><p className="truncate text-[11px] m-muted">{r.customer_name} · {fmtDate(r.created_at)} · {formatCurrency(r.total_amount || r.grand_total || 0)}</p></div><ChevronRight size={16} className="text-[#C7C7CC]" /></div>
        </button>
      ))}
    </div>
  );
}

function MobileReturnCreate({ onBack, onDone }) {
  const [customers, setCustomers] = useState([]);
  const [cid, setCid] = useState("");
  const [orders, setOrders] = useState([]);
  const [oid, setOid] = useState("");
  const [reasons, setReasons] = useState([]);
  const [reason, setReason] = useState("");
  const [qty, setQty] = useState({});
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  useEffect(() => {
    axios.get(`${API}/customers`).then((r) => setCustomers(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => {});
    axios.get(`${API}/sales-returns/meta/complaint-reasons`).then((r) => setReasons(r.data?.items || r.data?.reasons || r.data || [])).catch(() => {});
  }, []);
  useEffect(() => { if (!cid) return; axios.get(`${API}/sales-orders`, { params: { customer_id: cid } }).then((r) => setOrders((Array.isArray(r.data) ? r.data : r.data.items || []).filter((o) => ["shipped", "delivered", "completed", "dispatched"].includes(o.status)))).catch(() => setOrders([])); }, [cid]);
  const order = orders.find((o) => o.id === oid);
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const items = (order?.items || []).filter((it) => Number(qty[it.product_id] || 0) > 0).map((it) => ({ product_id: it.product_id, product_name: it.product_name, quantity_returned: Number(qty[it.product_id]), unit: it.unit, reason }));
      const r = await offlinePost(`${API}/sales-returns`, { order_id: oid, return_type: "retur", complaint_code: reason, complaint_note: notes, notes, items }, { label: `Retur ${order?.number || ""}` });
      if (r.queued) { setMsg({ ok: true, text: "Offline — retur tersimpan di HP, dikirim saat sinyal kembali." }); return; }
      setMsg({ ok: true, text: `Retur ${r.data?.number || ""} dibuat (draf).` }); setTimeout(onDone, 800);
    } catch (e) { const d = e.response?.data?.detail; setMsg({ ok: false, text: (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || "Gagal membuat retur." }); }
    finally { setBusy(false); }
  };
  const reasonOpts = (reasons || []).map((x) => (typeof x === "string" ? { value: x, label: x } : { value: x.value || x.code || x.id, label: x.label || x.name }));
  return (
    <div className="space-y-2 p-3" data-testid="m-return-create">
      <button className="m-subpage-back" onClick={onBack} data-testid="m-return-create-back"><ArrowLeft size={17} /> Retur</button>
      <div className="m-card p-3 space-y-2">
        <KNSelect value={cid} onValueChange={(v) => { setCid(v); setOid(""); }} options={customers.map((c) => ({ value: c.id, label: c.name }))} placeholder="Pilih pelanggan" data-testid="m-return-customer" />
        <KNSelect value={oid} onValueChange={setOid} options={orders.map((o) => ({ value: o.id, label: `${o.number} · ${fmtDate(o.created_at)}` }))} placeholder={cid ? (orders.length ? "Pilih pesanan terkirim" : "Tidak ada pesanan terkirim") : "Pilih pelanggan dulu"} data-testid="m-return-order" />
        <KNSelect value={reason} onValueChange={setReason} options={reasonOpts} placeholder="Alasan retur" data-testid="m-return-reason" />
        {(order?.items || []).map((it) => (
          <div key={it.product_id} className="flex items-center gap-2 text-[12px]" data-testid={`m-return-line-${it.product_id}`}><div className="flex-1 min-w-0"><b className="truncate block">{it.product_name}</b><span className="m-muted">dikirim {it.quantity} {it.unit}</span></div><input type="number" inputMode="decimal" className="w-24 rounded-lg border border-[#E5E5EA] p-1.5 text-right" placeholder="0" value={qty[it.product_id] ?? ""} onChange={(e) => setQty({ ...qty, [it.product_id]: e.target.value })} data-testid={`m-return-qty-${it.product_id}`} /></div>
        ))}
        <textarea className="w-full rounded-xl border border-[#E5E5EA] p-2 text-sm" rows={2} placeholder="Catatan / keluhan pelanggan" value={notes} onChange={(e) => setNotes(e.target.value)} data-testid="m-return-notes" />
        {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"} text-xs`} data-testid="m-return-msg">{msg.text}</div>}
        <button className="primary-button w-full py-3" disabled={busy || !oid || !reason || !Object.values(qty).some((v) => Number(v) > 0)} onClick={submit} data-testid="m-return-submit">{busy ? "Menyimpan…" : "Ajukan retur"}</button>
      </div>
    </div>
  );
}

/** Pesanan khusus versi HP: daftar kartu + form ringkas (pelanggan, spesifikasi, target kirim). */
export function MobileSpecialOrders() {
  const [rows, setRows] = useState(null);
  const [create, setCreate] = useState(false);
  const load = () => axios.get(`${API}/special-orders`).then((r) => setRows(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => setRows([]));
  useEffect(() => { load(); }, []);
  if (create) {
    return <MobileSpecialOrderCreate onBack={() => setCreate(false)} onDone={() => { setCreate(false); load(); }} />;
  }
  return (
    <div className="space-y-2 p-3" data-testid="m-special-orders">
      <button className="primary-button w-full py-3 flex items-center justify-center gap-2" onClick={() => setCreate(true)} data-testid="m-special-new"><Plus size={16} /> Ajukan pesanan khusus</button>
      {rows === null && <p className="text-xs m-muted">Memuat…</p>}
      {rows && rows.length === 0 && <p className="text-xs m-muted" data-testid="m-special-empty">Belum ada pesanan khusus.</p>}
      {(rows || []).map((s) => (
        <div key={s.id} className="m-card p-3" data-testid={`m-special-${s.id}`}>
          <div className="flex justify-between text-[13px]"><b>{s.number || s.id}</b><span className="rounded bg-[#F2F3F5] px-1.5 text-[10px] font-semibold">{s.status}</span></div>
          <p className="text-[11px] m-muted truncate">{s.customer_name} · {s.custom_item?.description || s.custom_item?.name || "-"} · kirim {fmtDate(s.expected_delivery)}</p>
          {s.quoted_price != null && <p className="text-[11px] tabular-nums">Penawaran {formatCurrency(s.quoted_price)}</p>}
        </div>
      ))}
    </div>
  );
}

function MobileSpecialOrderCreate({ onBack, onDone }) {
  const [customers, setCustomers] = useState([]);
  const [f, setF] = useState({ customer_id: "", name: "", description: "", quantity: "", unit: "yard", target_price: "", expected_delivery: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  useEffect(() => { axios.get(`${API}/customers`).then((r) => setCustomers(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => {}); }, []);
  const set = (k) => (e) => setF({ ...f, [k]: e?.target ? e.target.value : e });
  const cust = customers.find((c) => c.id === f.customer_id);
  const submit = async () => {
    setBusy(true); setMsg(null);
    try {
      const body = { customer_id: f.customer_id, entity_id: cust?.entity_id || "", shipping_address_id: (cust?.addresses || [])[0]?.id || "", expected_delivery: new Date(f.expected_delivery).toISOString(), notes: f.notes, submit_for_approval: true,
        custom_item: { description: f.name, specifications: { detail: f.description }, quantity: Number(f.quantity), unit: f.unit, target_price: Number(f.target_price || 0), notes: f.description } };
      const r = await offlinePost(`${API}/special-orders`, body, { label: `Pesanan khusus ${cust?.name || ""}` });
      if (r.queued) { setMsg({ ok: true, text: "Offline — pesanan khusus tersimpan di HP." }); return; }
      setMsg({ ok: true, text: `Pesanan khusus ${r.data?.number || ""} diajukan.` }); setTimeout(onDone, 800);
    } catch (e) { const d = e.response?.data?.detail; setMsg({ ok: false, text: (d && (d.message || (typeof d === "string" ? d : JSON.stringify(d)))) || "Gagal mengajukan." }); }
    finally { setBusy(false); }
  };
  return (
    <div className="space-y-2 p-3" data-testid="m-special-create">
      <button className="m-subpage-back" onClick={onBack} data-testid="m-special-back"><ArrowLeft size={17} /> Pesanan khusus</button>
      <div className="m-card p-3 space-y-2">
        <KNSelect value={f.customer_id} onValueChange={set("customer_id")} options={customers.map((c) => ({ value: c.id, label: c.name }))} placeholder="Pilih pelanggan" data-testid="m-special-customer" />
        <input className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Nama barang (mis. Batik motif custom)" value={f.name} onChange={set("name")} data-testid="m-special-name" />
        <textarea className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" rows={3} placeholder="Spesifikasi: bahan, warna, motif, lebar, finishing…" value={f.description} onChange={set("description")} data-testid="m-special-desc" />
        <div className="flex gap-2"><input type="number" inputMode="decimal" className="flex-1 rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Jumlah" value={f.quantity} onChange={set("quantity")} data-testid="m-special-qty" /><KNSelect value={f.unit} onValueChange={set("unit")} options={[{ value: "yard", label: "yard" }, { value: "meter", label: "meter" }, { value: "roll", label: "roll" }, { value: "pcs", label: "pcs" }]} data-testid="m-special-unit" /></div>
        <input type="number" inputMode="decimal" className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" placeholder="Harga target per satuan (Rp, boleh 0)" value={f.target_price} onChange={set("target_price")} data-testid="m-special-target-price" />
        <input type="date" className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" value={f.expected_delivery} onChange={set("expected_delivery")} data-testid="m-special-date" />
        <textarea className="w-full rounded-xl border border-[#E5E5EA] p-2.5 text-sm" rows={2} placeholder="Catatan" value={f.notes} onChange={set("notes")} data-testid="m-special-notes" />
        {msg && <div className={`notice-bar ${msg.ok ? "success" : "danger"} text-xs`} data-testid="m-special-msg">{msg.text}</div>}
        <button className="primary-button w-full py-3" disabled={busy || !f.customer_id || !f.name || !f.quantity || !f.expected_delivery} onClick={submit} data-testid="m-special-submit">{busy ? "Mengirim…" : "Ajukan"}</button>
      </div>
    </div>
  );
}

/** Daftar harga versi HP: harga efektif per pelanggan (umum → PT → pelanggan → khusus) dalam kartu. */
export function MobilePricelist({ selectedEntity }) {
  const [customers, setCustomers] = useState([]);
  const [cid, setCid] = useState("");
  const [q, setQ] = useState("");
  const [grid, setGrid] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { axios.get(`${API}/customers`).then((r) => setCustomers(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => {}); }, []);
  const cust = customers.find((c) => c.id === cid);
  useEffect(() => {
    if (!cid) { setGrid(null); return; }
    setGrid(null); setErr("");
    axios.get(`${API}/customer-prices`, { params: { customer_id: cid, entity_id: (selectedEntity && selectedEntity !== "all" ? selectedEntity : cust?.entity_id) || undefined } })
      .then((r) => setGrid(r.data)).catch((e) => setErr(e.response?.data?.detail || "Gagal memuat harga."));
  }, [cid]); // eslint-disable-line
  const rows = useMemo(() => (grid?.rows || grid?.items || []).filter((r) => !q || `${r.product_name} ${r.sku}`.toLowerCase().includes(q.toLowerCase())), [grid, q]);
  const eff = (r) => r.special_price ?? r.customer_price ?? r.entity_price ?? r.global_price;
  const src = (r) => (r.special_price != null ? ["Harga khusus", "#B25E00", "#FFF4E5"] : r.customer_price != null ? ["Harga pelanggan", "#0058CC", "#EAF2FF"] : r.entity_price != null ? ["Harga PT", "#1B7F4B", "#E6F6EC"] : ["Harga umum", "#6B6B73", "#F2F3F5"]);
  return (
    <div className="space-y-2 p-3" data-testid="m-pricelist">
      <KNSelect value={cid} onValueChange={setCid} options={customers.map((c) => ({ value: c.id, label: c.name }))} placeholder="Pilih pelanggan untuk harga efektif" data-testid="m-pricelist-customer" />
      {cid && <div className="m-card flex items-center gap-2 px-3 py-2"><Search size={15} className="m-muted" /><input className="w-full bg-transparent text-sm outline-none" placeholder="Cari produk / SKU" value={q} onChange={(e) => setQ(e.target.value)} data-testid="m-pricelist-search" /></div>}
      {err && <div className="notice-bar danger text-xs">{String(err)}</div>}
      {!cid && <p className="text-xs m-muted p-2" data-testid="m-pricelist-hint">Pilih pelanggan: harga yang tampil adalah harga yang akan dipakai di keranjang (umum → PT → pelanggan → khusus disetujui).</p>}
      {cid && grid === null && !err && <p className="text-xs m-muted">Memuat harga…</p>}
      {rows.map((r) => { const [l, fg, bg] = src(r); return (
        <div key={r.product_id} className="m-card p-3" data-testid={`m-price-${r.product_id}`}>
          <div className="flex items-start gap-2"><div className="min-w-0 flex-1"><p className="truncate text-[13px] font-bold">{r.product_name}</p><p className="text-[10.5px] m-muted">{r.sku} · {r.category || ""} · per {r.base_unit}</p></div>
            <div className="text-right"><p className="text-[14px] font-bold tabular-nums" data-testid={`m-price-eff-${r.product_id}`}>{formatCurrency(eff(r))}</p>{eff(r) !== r.global_price && <p className="text-[10px] m-muted line-through tabular-nums">{formatCurrency(r.global_price)}</p>}</div></div>
          <span className="mt-1 inline-block rounded px-1.5 text-[9.5px] font-bold" style={{ color: fg, background: bg }} data-testid={`m-price-src-${r.product_id}`}>{l}</span>
        </div>); })}
      {cid && grid && rows.length === 0 && <p className="text-xs m-muted" data-testid="m-pricelist-empty">Tidak ada produk.</p>}
    </div>
  );
}
