import { useEffect, useState } from "react";
import { MapPin, LogIn, LogOut, Loader2 } from "lucide-react";
import axios, { API } from "../../../services/apiClient";
import { offlinePost } from "../../../utils/offlineQueue";
import KNSelect from "../../../components/KNSelect";
import SpecialPriceRequestForm from "../../pricing/SpecialPriceRequestForm";

/** §3-A Tahap 1 — tiga layar lapangan: Minta Harga Khusus · Kunjungan · Status Stok. */
export function MobileSpecialPrice({ selectedEntity }) {
  const [custs, setCusts] = useState([]); const [prods, setProds] = useState([]);
  const [cid, setCid] = useState(""); const [pid, setPid] = useState("");
  useEffect(() => {
    axios.get(`${API}/customers`).then((r) => setCusts(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => {});
    axios.get(`${API}/products`).then((r) => setProds(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => {});
  }, []);
  return (
    <div className="p-3 space-y-3" data-testid="m-special-price">
      <KNSelect data-testid="m-sp-customer" placeholder="Pilih pelanggan" value={cid} onValueChange={setCid} options={custs.map((c) => ({ value: c.id, label: c.name }))} />
      <KNSelect data-testid="m-sp-product" placeholder="Pilih produk" value={pid} onValueChange={setPid} options={prods.map((p) => ({ value: p.id, label: `${p.name}${p.variant_label ? ` · ${p.variant_label}` : ""}` }))} />
      {cid && pid && (
        <SpecialPriceRequestForm compact product={prods.find((p) => p.id === pid)} customer={custs.find((c) => c.id === cid)} entityId={selectedEntity || ""} />
      )}
    </div>
  );
}

export function MobileVisits() {
  const [me, setMe] = useState(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(""); const [custName, setCustName] = useState("");
  const load = () => axios.get(`${API}/hr/visits/me`).then((r) => { setMe(r.data); setErr(""); }).catch((e) => setErr(e.response?.status === 404 ? "Akun Anda belum ditautkan ke profil karyawan — minta admin SDM." : (e.response?.data?.detail || "Gagal memuat kunjungan.")));
  useEffect(() => { load(); }, []);
  const geo = () => new Promise((res) => { if (!navigator.geolocation) return res({}); navigator.geolocation.getCurrentPosition((p) => res({ lat: p.coords.latitude, lon: p.coords.longitude }), () => res({}), { timeout: 4000 }); });
  const checkIn = async () => { setBusy(true); setErr(""); try { const r = await offlinePost(`${API}/hr/visits/check-in`, { customer_name: custName, notes: note, ...(await geo()) }, { label: `Check-in ${custName}` }); setCustName(""); setNote(""); if (r.queued) setErr("Offline — check-in tersimpan di HP, dikirim saat sinyal kembali."); else await load(); } catch (e) { setErr(e.response?.data?.detail || "Check-in gagal."); } finally { setBusy(false); } };
  const checkOut = async () => { setBusy(true); setErr(""); try { const r = await offlinePost(`${API}/hr/visits/${me.ongoing.id}/check-out`, { outcome: "other", notes: note, ...(await geo()) }, { label: `Check-out ${me.ongoing.customer_name || ""}` }); setNote(""); if (r.queued) setErr("Offline — check-out tersimpan di HP, dikirim saat sinyal kembali."); else await load(); } catch (e) { setErr(e.response?.data?.detail || "Check-out gagal."); } finally { setBusy(false); } };
  if (err) return <div className="notice-bar danger m-3" data-testid="m-visits-error">{String(err)}</div>;
  if (!me) return <div className="p-6 text-center text-sm"><Loader2 size={16} className="animate-spin inline" /> Memuat…</div>;
  return (
    <div className="p-3 space-y-3" data-testid="m-visits">
      {me.ongoing ? (
        <div className="m-card p-4 space-y-2" data-testid="m-visit-ongoing">
          <div className="flex items-center gap-2 text-[#0058CC]"><MapPin size={16} /> <b>Sedang berkunjung</b></div>
          <div className="text-sm">{me.ongoing.customer_name} · mulai {String(me.ongoing.check_in?.ts || "").slice(11, 16)}</div>
          <textarea className="textarea w-full" rows={2} placeholder="Catatan hasil kunjungan" value={note} onChange={(e) => setNote(e.target.value)} data-testid="m-visit-note" />
          <button className="danger-button w-full py-3" disabled={busy} onClick={checkOut} data-testid="m-visit-checkout"><LogOut size={16} className="inline mr-1" /> Selesai (check-out)</button>
        </div>
      ) : (
        <div className="m-card p-4 space-y-2" data-testid="m-visit-start">
          <input className="w-full rounded-lg border p-3" placeholder="Nama pelanggan / toko" value={custName} onChange={(e) => setCustName(e.target.value)} data-testid="m-visit-customer" />
          <textarea className="textarea w-full" rows={2} placeholder="Tujuan kunjungan" value={note} onChange={(e) => setNote(e.target.value)} data-testid="m-visit-note" />
          <button className="primary-button w-full py-3" disabled={busy} onClick={checkIn} data-testid="m-visit-checkin"><LogIn size={16} className="inline mr-1" /> Mulai kunjungan (check-in)</button>
        </div>
      )}
      <div className="text-xs text-[#6E6E73]">Hari ini: {me.count_today || 0} kunjungan</div>
      {(me.today || []).map((v) => (
        <div key={v.id} className="m-card p-3 text-sm" data-testid={`m-visit-${v.id}`}><b>{v.customer_name}</b> · {v.status === "done" ? `${v.duration_min} menit` : "berjalan"}</div>
      ))}
    </div>
  );
}

export function MobileStock() {
  const [rows, setRows] = useState(null); const [q, setQ] = useState("");
  useEffect(() => { axios.get(`${API}/inventory/balances`).then((r) => setRows(Array.isArray(r.data) ? r.data : r.data.items || [])).catch(() => setRows([])); }, []);
  if (rows === null) return <div className="p-6 text-center text-sm">Memuat…</div>;
  const f = rows.filter((r) => !q || `${r.product_name || ""} ${r.sku || ""}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="p-3 space-y-2" data-testid="m-stock">
      <input className="w-full rounded-lg border p-3" placeholder="Cari produk / SKU" value={q} onChange={(e) => setQ(e.target.value)} data-testid="m-stock-search" />
      {!f.length && <div className="p-6 text-center text-sm text-[#6E6E73]" data-testid="m-stock-empty">Tidak ada stok yang cocok.</div>}
      {f.slice(0, 80).map((r, i) => (
        <div key={r.id || i} className="m-card p-3 flex justify-between text-sm" data-testid={`m-stock-row-${i}`}>
          <div><b>{r.product_name || r.product_id}</b><div className="text-xs text-[#6E6E73]">{r.warehouse_name || r.warehouse_id}</div></div>
          <div className="text-right tabular-nums"><div><b>{r.available ?? r.available_qty ?? r.quantity}</b> tersedia</div><div className="text-xs text-[#6E6E73]">{r.reserved ?? r.reserved_qty ?? 0} dipesan</div></div>
        </div>
      ))}
    </div>
  );
}
