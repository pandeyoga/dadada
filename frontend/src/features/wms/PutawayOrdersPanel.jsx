/**
 * PutawayOrdersPanel (FASE R2) — Putaway Order (PA) antar-gedung + BTG.
 * Saran per (pemilik × kategori) berbasis storage_rules → buat PA → kirim →
 * konfirmasi tiba (validasi EPC gate/handheld) → BTG terbit; mismatch = exception.
 */
import { useEffect, useState } from "react";
import { Truck, ClipboardList, CheckCircle2, AlertTriangle, Send, Zap, RotateCcw } from "lucide-react";
import KNSelect from "../../components/KNSelect";
import axios, { API } from "../../services/apiClient";

const nf = new Intl.NumberFormat("id-ID");
const q = (v) => nf.format(Math.round((v || 0) * 100) / 100);
const PA_STATUS = {
  open: ["#0058CC", "Terbuka"], in_transit: ["#FF9500", "Dalam Perjalanan"],
  completed: ["#1B7F4B", "Selesai"], completed_with_exception: ["#8C4A00", "Selesai + Exception"],
  exception: ["#C0341D", "Exception"],
};

export default function PutawayOrdersPanel({ whId, selectedEntity }) {
  const [suggest, setSuggest] = useState(null);
  const [orders, setOrders] = useState([]);
  const [destByGroup, setDestByGroup] = useState({});
  const [confirmFor, setConfirmFor] = useState(null);
  const [epcInput, setEpcInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  const load = async () => {
    setError("");
    try {
      const [s, o] = await Promise.all([
        whId ? axios.get(`${API}/putaway-orders/suggest`, { params: { from_warehouse_id: whId } }) : Promise.resolve({ data: null }),
        axios.get(`${API}/putaway-orders`, { params: whId ? { warehouse_id: whId } : {} }),
      ]);
      setSuggest(s.data); setOrders(o.data.orders || []);
    } catch (e) { setError(e.response?.data?.detail || e.message); }
  };
  useEffect(() => { load(); setConfirmFor(null); }, [whId, selectedEntity]); // eslint-disable-line

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(""), 3500); };
  const fail = (e, f) => setError(e.response?.data?.detail || f);

  const createPA = async (gi, group) => {
    const to = destByGroup[gi] || group.candidates?.[0]?.warehouse_id;
    if (!to) { setError("Pilih gudang tujuan dulu."); return; }
    setBusy(true); setError("");
    try {
      const r = await axios.post(`${API}/putaway-orders`, {
        from_warehouse_id: whId, to_warehouse_id: to,
        roll_ids: group.rolls.map((x) => x.id),
      });
      flash(`${r.data.pa_number} dibuat → ${r.data.to_warehouse_name} (${r.data.item_count} roll).`);
      await load();
    } catch (e) { fail(e, "Gagal membuat PA"); } finally { setBusy(false); }
  };

  const dispatch = async (id) => {
    setBusy(true);
    try { await axios.post(`${API}/putaway-orders/${id}/dispatch`); flash("PA dikirim — barang menuju gudang tujuan."); await load(); }
    catch (e) { fail(e, "Gagal dispatch"); } finally { setBusy(false); }
  };

  const confirm = async (pa, epcs) => {
    setBusy(true);
    try {
      const r = await axios.post(`${API}/putaway-orders/${pa.id}/confirm-arrival`,
        { scanned_epcs: epcs && epcs.length ? epcs : null });
      const d = r.data;
      flash(d.btg_number
        ? `Tiba tervalidasi — BTG ${d.btg_number} terbit (${d.arrived_count} roll${d.exception_count ? `, ${d.exception_count} EXCEPTION` : ""}).`
        : "Semua item EXCEPTION — cek ulang dengan handheld.");
      setConfirmFor(null); setEpcInput(""); await load();
    } catch (e) { fail(e, "Gagal konfirmasi tiba"); } finally { setBusy(false); }
  };

  const resolve = async (pa, rollIds, action) => {
    setBusy(true);
    try {
      await axios.post(`${API}/putaway-orders/${pa.id}/resolve-exception`, { roll_ids: rollIds, action });
      flash(action === "accept" ? "Exception diterima — barang masuk gudang tujuan." : "Barang dikembalikan ke antrean transit.");
      await load();
    } catch (e) { fail(e, "Gagal resolve exception"); } finally { setBusy(false); }
  };

  return (
    <div className="space-y-3" data-testid="pa-panel">
      {error && <div data-testid="pa-error" className="rounded-lg bg-[#FBE9E7] px-3 py-2 text-[12px] font-semibold text-[#C0341D]">{error}</div>}
      {msg && <div data-testid="pa-msg" className="rounded-lg bg-[#E7F7EC] px-3 py-2 text-[12px] font-semibold text-[#1B7E3B]">{msg}</div>}

      {/* Saran putaway */}
      <section className="section-card">
        <div className="section-head"><h2 className="text-[13px] font-bold flex items-center gap-1.5">
          <ClipboardList size={15} className="text-[#0058CC]" /> Siap Simpan ke Rak dari {suggest?.warehouse_from?.name || "—"} ({suggest?.ready_count ?? 0} roll)</h2></div>
        <div className="section-body">
          {!suggest || suggest.groups.length === 0 ? (
            <p className="py-6 text-center text-[12px] text-[#8E8E93]" data-testid="pa-suggest-empty">
              Tidak ada roll siap disimpan ke rak (perlu tag terverifikasi + routing SIMPAN).
            </p>
          ) : suggest.groups.map((g, gi) => (
            <div key={gi} data-testid={`pa-group-${gi}`} className="mb-2 rounded-lg border border-[#EFF0F2] p-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <div className="min-w-0 flex-1">
                  <p className="text-[12.5px] font-bold">Kategori: {g.category || "—"} <span className="rounded bg-[#F3E9FA] px-1 text-[10px] font-bold text-[#6B219A]">Grade {g.grade || "A"}</span> <span className="font-normal text-[#6B6B73]">· {g.rolls.length} roll · {q(g.qty)} {g.unit || g.rolls[0]?.unit || "m"}</span></p>
                  <p className="truncate text-[10.5px] text-[#8E8E93]">{g.rolls.slice(0, 4).map((r) => r.roll_no).join(", ")}{g.rolls.length > 4 ? ` +${g.rolls.length - 4} lagi` : ""}</p>
                </div>
                <KNSelect data-testid={`pa-dest-${gi}`} value={destByGroup[gi] || g.candidates?.[0]?.warehouse_id || ""}
                  onValueChange={(v) => setDestByGroup((d) => ({ ...d, [gi]: v }))}
                  options={(g.candidates || []).map((c) => ({
                    value: c.warehouse_id,
                    label: `${c.warehouse_name}${c.same_site ? " · site sama" : ""}`,
                  }))}
                  className="field !py-1 !px-2 w-auto text-[12px]" placeholder="Gudang tujuan" />
                <button data-testid={`pa-create-${gi}`} disabled={busy || !(g.candidates || []).length}
                  onClick={() => createPA(gi, g)}
                  className="flex items-center gap-1 rounded-lg bg-[#0058CC] px-3 py-1.5 text-[12px] font-semibold text-white disabled:opacity-40">
                  <Send size={12} /> Buat PA
                </button>
              </div>
              {(g.candidates || []).length === 0 && (
                <p className="mt-1 text-[11px] font-semibold text-[#C0341D]">Tidak ada gudang tujuan yang aturannya cocok — atur aturannya di Master Gudang.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Daftar PA */}
      <section className="section-card">
        <div className="section-head"><h2 className="text-[13px] font-bold flex items-center gap-1.5">
          <Truck size={15} className="text-[#0058CC]" /> Putaway Orders ({orders.length})</h2></div>
        <div className="section-body space-y-2">
          {orders.length === 0 && <p className="py-6 text-center text-[12px] text-[#8E8E93]">Belum ada Perintah Simpan ke Rak.</p>}
          {orders.map((o) => {
            const [color, label] = PA_STATUS[o.status] || ["#6B6B73", o.status];
            const excItems = (o.items || []).filter((i) => i.status === "exception");
            return (
              <div key={o.id} data-testid={`pa-row-${o.id}`} className="rounded-lg border border-[#EFF0F2] p-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-[12.5px] font-bold">{o.pa_number}
                      {o.btg_number && <span className="ml-2 rounded bg-[#E6F6EC] px-1.5 py-0.5 text-[10px] font-bold text-[#1B7F4B]">BTG {o.btg_number}</span>}
                    </p>
                    <p className="text-[11px] text-[#6B6B73]">{o.from_warehouse_name} → <b>{o.to_warehouse_name}</b> · {o.item_count} roll · {q(o.total_qty)} {o.items?.[0]?.unit || "m"}</p>
                  </div>
                  <span className="rounded px-2 py-0.5 text-[10.5px] font-bold" style={{ color, background: `${color}18` }}>{label}</span>
                  {o.status === "open" && (
                    <button data-testid={`pa-dispatch-${o.id}`} disabled={busy} onClick={() => dispatch(o.id)}
                      className="rounded-lg bg-[#FF9500] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">Kirim</button>
                  )}
                  {["open", "in_transit"].includes(o.status) && (
                    <button data-testid={`pa-confirm-${o.id}`} disabled={busy}
                      onClick={() => { setConfirmFor(confirmFor === o.id ? null : o.id); setEpcInput(""); }}
                      className="rounded-lg bg-[#1B7F4B] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">
                      Konfirmasi Tiba
                    </button>
                  )}
                </div>

                {confirmFor === o.id && (
                  <div className="mt-2 rounded-lg border border-[#DCE6F5] bg-[#F7FAFF] p-2.5" data-testid={`pa-confirm-box-${o.id}`}>
                    <p className="text-[11.5px] font-semibold">Validasi gate-in gudang tujuan — tempel EPC hasil baca (kosongkan = semua tiba tanpa validasi RFID):</p>
                    <textarea data-testid={`pa-epc-input-${o.id}`} className="field mt-1 h-14 w-full font-mono text-[11px]"
                      value={epcInput} onChange={(e) => setEpcInput(e.target.value)} placeholder="E2XX-XXXX-…" />
                    <div className="mt-1.5 flex gap-1.5">
                      <button data-testid={`pa-confirm-submit-${o.id}`} disabled={busy}
                        onClick={() => confirm(o, epcInput.split(/[\s,;]+/).filter(Boolean))}
                        className="rounded-lg bg-[#1B7F4B] px-3 py-1.5 text-[11px] font-semibold text-white disabled:opacity-40">
                        <CheckCircle2 size={12} className="mr-1 inline" /> Validasi & Terbitkan BTG
                      </button>
                      <button data-testid={`pa-confirm-sim-${o.id}`} disabled={busy}
                        onClick={() => confirm(o, (o.items || []).map((i) => i.epc).filter(Boolean))}
                        className="flex items-center gap-1 rounded-lg border border-[#1B7F4B] px-3 py-1.5 text-[11px] font-semibold text-[#1B7F4B] disabled:opacity-40">
                        <Zap size={12} /> Simulasi Scan Semua
                      </button>
                    </div>
                  </div>
                )}

                {excItems.length > 0 && (
                  <div className="mt-2 rounded-lg bg-[#FFF4E5] p-2.5" data-testid={`pa-exceptions-${o.id}`}>
                    <p className="flex items-center gap-1 text-[11.5px] font-bold text-[#8C4A00]">
                      <AlertTriangle size={13} /> {excItems.length} roll EXCEPTION (EPC tak terbaca saat tiba)</p>
                    {excItems.map((i) => (
                      <div key={i.roll_id} className="mt-1 flex flex-wrap items-center gap-2 text-[11.5px]">
                        <span className="flex-1">{i.roll_no} · {i.sku} <span className="font-mono text-[10px] text-[#8E8E93]">{i.epc}</span></span>
                        <button data-testid={`pa-exc-accept-${i.roll_id}`} disabled={busy}
                          onClick={() => resolve(o, [i.roll_id], "accept")}
                          className="rounded bg-[#1B7F4B] px-2 py-1 text-[10.5px] font-semibold text-white disabled:opacity-40">
                          Scan ulang OK → Terima
                        </button>
                        <button data-testid={`pa-exc-return-${i.roll_id}`} disabled={busy}
                          onClick={() => resolve(o, [i.roll_id], "return_transit")}
                          className="flex items-center gap-1 rounded border border-[#8C4A00] px-2 py-1 text-[10.5px] font-semibold text-[#8C4A00] disabled:opacity-40">
                          <RotateCcw size={11} /> Kembali ke transit
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
