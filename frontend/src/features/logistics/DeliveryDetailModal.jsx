import { useEffect, useState } from "react";
import { X, Camera, MapPin, CheckCircle2, Truck, PackageCheck, Flag, AlertTriangle, RotateCcw, Save, LocateFixed, Navigation, Phone, MessageCircle, ExternalLink } from "lucide-react";
import { askConfirm, askReason } from "../../services/confirmService";
import KNDatePicker, { formatDateId } from "../../components/KNDatePicker";
import { useEscapeClose } from "../../utils/escapeLayers";
import DeliveryPhoto from "./DeliveryPhoto";
import PositionMap from "./PositionMap";
import { openOrderJourney } from "./logisticsDeepLink";
import { addPosition, deletePhoto, deletePosition, getDelivery, photoUrl, transitionDelivery, updateDelivery, uploadPhoto, STATUS_LABEL, STATUS_PILL, STEPS, PICKUP_STEPS, PICKUP_STATUS_LABEL, MODE_PILL, mapsUrl, telUrl, waUrl } from "./logisticsApi";
import PickupHandoverPanel from "./PickupHandoverPanel";
import MoneyInput from "../../components/MoneyInput";
import { formatCurrency } from "../../utils/formatters";

// FB-02 — detail pengiriman: tahapan, foto muat/POD (wajib), posisi, data ekspedisi/armada,
// serah terima pickup (kode + identitas) untuk pesanan yang diambil sendiri.
export default function DeliveryDetailModal({ id, canManage, canUpdate, canOpenOrder, onClose, onChanged }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState("");
  const [pos, setPos] = useState({ location: "", note: "", lat: null, lng: null });
  const [gpsBusy, setGpsBusy] = useState(false);
  function takeGps() {
    if (!navigator.geolocation) { setErr("Perangkat ini tidak mendukung GPS."); return; }
    setGpsBusy(true); setErr("");
    navigator.geolocation.getCurrentPosition(
      (g) => { setPos((p) => ({ ...p, lat: +g.coords.latitude.toFixed(6), lng: +g.coords.longitude.toFixed(6) })); setGpsBusy(false); },
      (e) => { setErr(`GPS gagal: ${e.message}`); setGpsBusy(false); },
      { enableHighAccuracy: true, timeout: 10000 });
  }
  const [receiver, setReceiver] = useState("");
  const [edit, setEdit] = useState(null);

  async function refresh() {
    try { const r = await getDelivery(id); setD(r); setReceiver((v) => v || r.receiver_name_hint || ""); setEdit({ courier_name: r.courier_name, tracking_no: r.tracking_no, service_level: r.service_level || "", shipping_cost: r.shipping_cost || 0, vehicle_plate: r.vehicle_plate, driver_name: r.driver_name, eta: r.eta, destination: r.destination, receiver_phone: r.receiver_phone || "" }); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memuat pengiriman."); }
  }
  useEffect(() => { refresh(); }, [id]); // eslint-disable-line
  useEscapeClose(true, onClose, !!busy);   // L-11 — Esc menutup lapisan teratas saja

  async function run(label, fn, ok) {
    setBusy(label); setErr(""); setMsg("");
    try { await fn(); setMsg(ok); await refresh(); await onChanged(); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memproses."); }
    finally { setBusy(""); }
  }
  const go = (to, extra = {}) => run(to, () => transitionDelivery(id, { to, ...extra }), `Status → ${STATUS_LABEL[to]}.`);
  const CONFIRM_TEXT = {
    loaded: ["Tandai barang sudah DIMUAT?", "Setelah ini pengiriman siap berangkat. Bila salah, gudang/manajer bisa membongkar kembali dengan alasan."],
    in_transit: ["Kendaraan BERANGKAT sekarang?", "Status menjadi Dalam perjalanan; sopir mulai mencatat posisi."],
    delivered: ["Tandai TERKIRIM?", "Nama penerima & foto POD tersimpan sebagai bukti dan tidak bisa diubah lagi."],
    completed: ["SELESAIKAN pengiriman?", "Pengiriman ditutup; foto dan data tidak bisa diubah lagi."],
  };
  async function goConfirmed(to, extra = {}) {
    const [title, description] = CONFIRM_TEXT[to] || [`Ubah status ke ${STATUS_LABEL[to]}?`, ""];
    if (await askConfirm({ title, description, confirmLabel: STATUS_LABEL[to] })) go(to, extra);
  }
  async function unload() {
    const reason = await askReason({ title: "Bongkar muatan — kembali ke Disiapkan?", description: "Untuk salah tekan \"Tandai Dimuat\". Alasan tersimpan di riwayat.", confirmLabel: "Bongkar", reasonPlaceholder: "Contoh: salah tekan / barang belum lengkap" });
    if (reason) go("prepared", { reason });
  }
  async function fail() {
    const reason = await askReason({ title: "Tandai gagal kirim?", description: "Alasan tersimpan di riwayat pengiriman.", confirmLabel: "Gagal kirim", reasonPlaceholder: "Contoh: alamat tidak ditemukan / penerima tidak ada", danger: true });
    if (reason) go("failed", { reason });
  }
  function onPick(kind) {
    return (e) => { const file = e.target.files?.[0]; e.target.value = ""; if (!file) return; run(`photo-${kind}`, () => uploadPhoto(id, file, kind), kind === "load" ? "Foto muat terunggah." : "Foto bukti terima terunggah."); };
  }

  if (!d) return <div className="modal-overlay" data-testid="logistics-detail-modal"><div className="modal-card"><p className="text-[12px] text-[#6B6B73]">{err || "Memuat…"}</p></div></div>;
  const isPickup = d.mode === "self_pickup";
  const steps = isPickup ? PICKUP_STEPS : STEPS;
  const stepLabel = (s) => (isPickup ? PICKUP_STATUS_LABEL[s] : STATUS_LABEL[s]);
  const stepIdx = d.status === "failed" ? -1 : steps.indexOf(d.status);
  const photos = d.photos || [];
  const loadP = photos.filter((p) => p.kind === "load"), podP = photos.filter((p) => p.kind === "pod");
  const editable = canManage && !["delivered", "completed"].includes(d.status);
  const active = !isPickup && ["loaded", "in_transit"].includes(d.status);

  return (
    <div className="modal-overlay" data-testid="logistics-detail-modal" onClick={(e) => { if (e.target === e.currentTarget && !busy) onClose(); }}>
      <div className="modal-card !max-w-[760px]">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <p className="modal-title !mb-0 font-mono">{d.number}</p>
            <span className={`status-pill ${STATUS_PILL[d.status]}`} data-testid="logistics-detail-status">{d.status_label}</span>
            <span className={`status-pill ${MODE_PILL[d.mode]}`} data-testid="logistics-detail-mode">{d.mode_label}</span>
          </div>
          <button className="icon-button" onClick={onClose}><X size={16} /></button>
        </div>
        <p className="text-[11.5px] text-[#6B6B73] mt-0.5 flex items-center gap-1.5 flex-wrap">
          {canOpenOrder ? (
            <button type="button" data-testid="logistics-detail-open-order" className="inline-flex items-center gap-1 font-semibold text-[#0058CC] hover:underline" title="Buka pesanan & Perjalanan Pesanan" onClick={() => { onClose(); openOrderJourney(d.order_id); }}>{d.order_number} <ExternalLink size={11} /></button>
          ) : <span className="font-semibold">{d.order_number}</span>}
          <span>· {d.customer_name} · SJ {(d.shipment_nos || []).join(", ")}</span>
        </p>
        {!isPickup && d.destination && (
          <div className="flex items-center gap-2 mt-1.5 flex-wrap">
            <span className="flex items-center gap-1 text-[11.5px] text-[#3A3B42]"><MapPin size={12} className="text-[#0058CC]" /> {d.destination}</span>
            <a data-testid="logistics-detail-nav" href={mapsUrl(d.destination)} target="_blank" rel="noopener noreferrer" className="secondary-button !py-1 !px-2 !text-[11px]" title="Buka Google Maps ke alamat tujuan"><Navigation size={12} /> Navigasi</a>
            {d.receiver_phone && (<>
              <span className="flex items-center gap-1 text-[11.5px] text-[#3A3B42] ml-1" data-testid="logistics-detail-phone"><Phone size={12} className="text-[#0058CC]" /> {d.receiver_name_hint ? `${d.receiver_name_hint} · ` : ""}<span className="font-mono">{d.receiver_phone}</span></span>
              <a data-testid="logistics-detail-call" href={telUrl(d.receiver_phone)} className="secondary-button !py-1 !px-2 !text-[11px]"><Phone size={12} /> Telepon</a>
              <a data-testid="logistics-detail-wa" href={waUrl(d.receiver_phone)} target="_blank" rel="noopener noreferrer" className="secondary-button !py-1 !px-2 !text-[11px] !border-[#1F7A45] !text-[#1F7A45]"><MessageCircle size={12} /> WA</a>
            </>)}
          </div>
        )}

        {/* Stepper */}
        <div className="flex items-center gap-1 mt-3" data-testid="logistics-stepper">
          {steps.map((s, i) => (
            <div key={s} className="flex-1 flex flex-col items-center">
              <div className={`h-2 w-full rounded-full ${i <= stepIdx ? (isPickup ? "bg-[#6B219A]" : "bg-[#0058CC]") : "bg-[#E9EBEF]"}`} />
              <span className={`text-[9.5px] mt-1 ${i === stepIdx ? `font-bold ${isPickup ? "text-[#6B219A]" : "text-[#0058CC]"}` : "text-[#9A9BA3]"}`}>{stepLabel(s)}</span>
            </div>
          ))}
        </div>
        {d.status === "failed" && <div className="notice-bar danger !my-2 !py-1.5" data-testid="logistics-fail-reason"><AlertTriangle size={13} /><span className="text-[11.5px]"><b>Gagal kirim:</b> {d.fail_reason}</span></div>}
        {err && <div className="notice-bar danger !my-2 !py-1.5" data-testid="logistics-detail-error"><span className="text-[11.5px]">{err}</span></div>}
        {msg && <div className="notice-bar success !my-2 !py-1.5" data-testid="logistics-detail-msg"><span className="text-[11.5px]">{msg}</span></div>}

        {isPickup && <PickupHandoverPanel d={d} canUpdate={canUpdate} canManage={canManage} onDone={async (m) => { setMsg(m); setErr(""); await refresh(); await onChanged(); }} />}
        {isPickup && canUpdate && d.status === "delivered" && (
          <div className="flex items-center gap-2 mt-2" data-testid="logistics-actions"><button data-testid="logistics-act-completed" className="primary-button !py-1.5" disabled={!!busy} onClick={() => goConfirmed("completed")}><CheckCircle2 size={13} /> Selesaikan</button></div>
        )}

        {/* Aksi tahapan */}
        {canUpdate && !isPickup && (
          <div className="flex flex-wrap items-center gap-2 mt-2" data-testid="logistics-actions">
            {/* L-7 — syarat tahapan ditampilkan DI ATAS tombol, sebelum ditekan */}
            <p className="w-full text-[10.5px] text-[#6B6B73] -mb-0.5" data-testid="logistics-step-hint">
              {d.status === "prepared" ? (loadP.length ? "Foto muat sudah ada — siap ditandai Dimuat." : "Wajib unggah foto muat (barang naik kendaraan) sebelum Dimuat.")
                : d.status === "loaded" ? (d.mode === "expedition" ? (d.tracking_no ? "No. resi terisi — siap berangkat." : "Wajib isi NO. RESI ekspedisi sebelum berangkat.") : (d.vehicle_plate && d.driver_name ? "Plat & sopir terisi — siap berangkat." : "Wajib isi PLAT KENDARAAN & NAMA SOPIR sebelum berangkat."))
                : d.status === "in_transit" ? `Wajib foto POD${podP.length ? " ✓" : " (belum ada)"} + nama penerima${receiver.trim() ? " ✓" : " (belum diisi)"} sebelum Terkirim.` : ""}
            </p>
            {d.status === "prepared" && <button data-testid="logistics-act-loaded" className="primary-button !py-1.5" disabled={!!busy || !loadP.length} title={!loadP.length ? "Unggah foto muat dulu" : ""} onClick={() => goConfirmed("loaded")}><Truck size={13} /> Tandai Dimuat</button>}
            {d.status === "loaded" && <button data-testid="logistics-act-in_transit" className="primary-button !py-1.5" disabled={!!busy} onClick={() => goConfirmed("in_transit")}><Flag size={13} /> Berangkat</button>}
            {d.status === "loaded" && canManage && <button data-testid="logistics-act-unload" className="secondary-button !py-1.5" disabled={!!busy} onClick={unload} title="Salah tekan Dimuat? Kembalikan ke Disiapkan dengan alasan"><RotateCcw size={13} /> Bongkar (kembali ke Disiapkan)</button>}
            {d.status === "in_transit" && (
              <div className="flex flex-wrap items-center gap-2">
                <input data-testid="logistics-receiver" className={`form-input !w-[200px] ${!receiver.trim() ? "!border-[#E0A800]" : ""}`} placeholder="Nama penerima *" value={receiver} onChange={(e) => setReceiver(e.target.value)} />
                <button data-testid="logistics-act-delivered" className="primary-button !py-1.5" disabled={!!busy || !receiver.trim() || !podP.length} title={!podP.length ? "Unggah foto POD dulu" : !receiver.trim() ? "Isi nama penerima" : ""} onClick={() => goConfirmed("delivered", { receiver_name: receiver.trim() })}><PackageCheck size={13} /> Tandai Terkirim</button>
              </div>
            )}
            {d.status === "delivered" && <button data-testid="logistics-act-completed" className="primary-button !py-1.5" disabled={!!busy} onClick={() => goConfirmed("completed")}><CheckCircle2 size={13} /> Selesaikan</button>}
            {active && <button data-testid="logistics-act-failed" className="secondary-button !py-1.5 text-[#C0341D]" disabled={!!busy} onClick={fail}><AlertTriangle size={13} /> Gagal kirim</button>}
            {d.status === "failed" && canManage && <button data-testid="logistics-act-prepared" className="secondary-button !py-1.5" disabled={!!busy} onClick={() => go("prepared")}><RotateCcw size={13} /> Jadwalkan ulang</button>}
          </div>
        )}

        {/* Foto */}
        <div className="grid sm:grid-cols-2 gap-3 mt-3">
          {!isPickup && <PhotoBlock title="Foto muat" hint="Barang naik kendaraan" kind="load" list={loadP} d={d} canUpdate={canUpdate && d.status !== "completed"} onPick={onPick("load")} onDel={(pid) => run("del", () => deletePhoto(id, pid), "Foto dihapus.")} busy={busy} />}
          <PhotoBlock title={isPickup ? "Foto bukti serah terima" : "Bukti terima (POD)"} hint={isPickup ? "Pengambil bersama barang" : "Di tujuan, bersama penerima"} kind="pod" list={podP} d={d} canUpdate={canUpdate && d.status !== "completed"} onPick={onPick("pod")} onDel={(pid) => run("del", () => deletePhoto(id, pid), "Foto dihapus.")} busy={busy} />
        </div>
        {d.pod && !isPickup && <p className="text-[11px] text-[#1F7A45] mt-1.5" data-testid="logistics-pod-info"><b>Diterima oleh {d.pod.receiver_name}</b> · {String(d.pod.received_at).slice(0, 16).replace("T", " ")}</p>}

        {/* Posisi */}
        {!isPickup && <div className="mt-3 rounded-lg border border-[#E1E4EA] p-2.5" data-testid="logistics-positions">
          <div className="flex items-center justify-between"><span className="flex items-center gap-1.5 text-[12px] font-semibold"><MapPin size={14} /> Riwayat posisi ({(d.positions || []).length})</span></div>
          {canUpdate && active && (
            <div className="flex flex-wrap gap-2 mt-2">
              <input data-testid="logistics-pos-location" className="form-input flex-1 min-w-[160px]" placeholder="Lokasi saat ini *" value={pos.location} onChange={(e) => setPos({ ...pos, location: e.target.value })} />
              <input data-testid="logistics-pos-note" className="form-input flex-1 min-w-[160px]" placeholder="Catatan" value={pos.note} onChange={(e) => setPos({ ...pos, note: e.target.value })} />
              <button type="button" data-testid="logistics-pos-gps" className={`secondary-button ${pos.lat != null ? "!border-[#1F7A45] !text-[#1F7A45]" : ""}`} disabled={gpsBusy} onClick={takeGps} title="Ambil koordinat GPS ponsel">
                <LocateFixed size={13} /> {gpsBusy ? "Mencari…" : pos.lat != null ? `${pos.lat}, ${pos.lng}` : "Ambil GPS"}
              </button>
              <button data-testid="logistics-pos-submit" className="secondary-button" disabled={!!busy || pos.location.trim().length < 2} onClick={() => run("pos", () => addPosition(id, pos), "Posisi dicatat.").then(() => setPos({ location: "", note: "", lat: null, lng: null }))}>Catat</button>
            </div>
          )}
          <div className="mt-2"><PositionMap positions={d.positions || []} /></div>
          <div className="mt-2 divide-y divide-[#F0F1F3]">
            {(d.positions || []).slice().reverse().map((p) => (
              <div key={p.id} className="py-1.5 text-[11.5px] flex items-center gap-1" data-testid={`logistics-pos-${p.id}`}><span className="flex-1 min-w-0"><b>{p.location}</b>{p.note ? ` — ${p.note}` : ""}{p.lat != null && p.lng != null && <span className="ml-1.5 text-[10px] text-[#0058CC] font-mono" data-testid={`logistics-pos-gps-${p.id}`}>⌖ {p.lat}, {p.lng}</span>}<span className="text-[10px] text-[#9A9BA3] ml-2">{String(p.at).slice(0, 16).replace("T", " ")} · {p.by}</span></span>
                {canManage && !["delivered", "completed"].includes(d.status) && <button type="button" data-testid={`logistics-pos-del-${p.id}`} className="icon-button !p-1 text-[#C0341D]" title="Hapus posisi yang salah" onClick={async () => { if (await askConfirm({ title: "Hapus posisi ini?", description: `${p.location} — penghapusan tercatat di riwayat.`, confirmLabel: "Hapus", danger: true })) run("delpos", () => deletePosition(id, p.id), "Posisi dihapus."); }}><X size={12} /></button>}</div>
            ))}
            {(d.positions || []).length === 0 && <p className="text-[10.5px] text-[#9A9BA3] py-1">Belum ada posisi tercatat.</p>}
          </div>
        </div>}

        {/* Data ekspedisi / armada */}
        <div className="grid gap-2 sm:grid-cols-3 mt-3" data-testid="logistics-info">
          {d.mode === "expedition" ? (<>
            <Field label="Kurir / Ekspedisi" k="courier_name" edit={edit} setEdit={setEdit} editable={editable} d={d} />
            <Field label="No. Resi" k="tracking_no" edit={edit} setEdit={setEdit} editable={editable} d={d} />
            <Field label="Layanan" k="service_level" edit={edit} setEdit={setEdit} editable={editable} d={d} />
            <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Biaya kirim</label>
              {editable ? <MoneyInput testId="logistics-edit-shipping_cost" value={edit?.shipping_cost ?? 0} onChange={(v) => setEdit({ ...edit, shipping_cost: v })} />
                : <p className="text-[12px] font-semibold tabular-nums" data-testid="logistics-val-shipping_cost">{d.shipping_cost ? formatCurrency(d.shipping_cost) : "—"}</p>}</div>
          </>) : d.mode === "own_fleet" ? (<>
            <Field label="Plat kendaraan" k="vehicle_plate" edit={edit} setEdit={setEdit} editable={editable} d={d} />
            <Field label="Sopir" k="driver_name" edit={edit} setEdit={setEdit} editable={editable} d={d} />
          </>) : (
            <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Tanggal ambil (pesanan)</label><p className="text-[12px] font-semibold" data-testid="logistics-val-pickup_date">{d.pickup_date ? formatDateId(d.pickup_date) : "—"}</p></div>
          )}
          <Field label={isPickup ? "Tanggal ambil" : "ETA"} k="eta" type="date" edit={edit} setEdit={setEdit} editable={editable} d={d} />
          {!isPickup && <div className="sm:col-span-2"><Field label="Tujuan" k="destination" edit={edit} setEdit={setEdit} editable={editable} d={d} /></div>}
          <Field label={isPickup ? "Telepon pelanggan" : "Telepon penerima"} k="receiver_phone" type="tel" edit={edit} setEdit={setEdit} editable={editable} d={d} />
        </div>
        {editable && <div className="flex justify-end mt-2"><button data-testid="logistics-save-info" className="secondary-button" disabled={!!busy} onClick={() => run("save", () => updateDelivery(id, { ...edit, shipping_cost: Number(edit.shipping_cost) || 0 }), "Data pengiriman tersimpan.")}><Save size={13} /> Simpan data</button></div>}

        {/* Riwayat */}
        <details className="mt-3"><summary className="text-[11px] font-bold uppercase text-[#6B6B73] cursor-pointer">Riwayat ({(d.timeline || []).length})</summary>
          <div className="mt-1 divide-y divide-[#F0F1F3]" data-testid="logistics-timeline">
            {(d.timeline || []).slice().reverse().map((t) => <div key={t.id} className="py-1 text-[11px]"><b>{t.action}</b>{t.to_status ? ` → ${STATUS_LABEL[t.to_status]}` : ""}{t.note ? ` · ${t.note}` : ""}<span className="text-[10px] text-[#9A9BA3] ml-2">{String(t.at).slice(0, 16).replace("T", " ")} · {t.by}</span></div>)}
          </div></details>
      </div>
    </div>
  );
}

function Field({ label, k, type = "text", edit, setEdit, editable, d }) {
  return (
    <div className="grid gap-1"><label className="text-[10.5px] font-bold uppercase text-[#6B6B73]">{label}</label>
      {editable ? (type === "date"
        ? <KNDatePicker data-testid={`logistics-edit-${k}`} value={edit?.[k] || ""} onChange={(v) => setEdit({ ...edit, [k]: v })} placeholder="Pilih tanggal ETA" />
        : <input data-testid={`logistics-edit-${k}`} type={type} className="form-input" value={edit?.[k] || ""} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} />)
        : <p className="text-[12px] font-semibold" data-testid={`logistics-val-${k}`}>{type === "date" ? (d[k] ? formatDateId(d[k]) : "—") : (d[k] || "—")}</p>}
    </div>
  );
}

function PhotoBlock({ title, hint, kind, list, d, canUpdate, onPick, onDel, busy }) {
  const locked = ["delivered", "completed"].includes(d.status);
  return (
    <div className="rounded-lg border border-[#E1E4EA] p-2.5" data-testid={`logistics-photos-${kind}`}>
      <div className="flex items-center justify-between"><span className="flex items-center gap-1.5 text-[12px] font-semibold"><Camera size={14} /> {title} ({list.length})</span><span className="text-[10px] text-[#9A9BA3]">{hint}</span></div>
      <div className="flex flex-wrap gap-2 mt-2">
        {list.map((p) => (
          <div key={p.id} className="relative w-[88px]" data-testid={`logistics-photo-${p.id}`}>
            <div className="aspect-square rounded-md overflow-hidden bg-[#F2F3F5] border border-[#EFF0F2]"><DeliveryPhoto url={photoUrl(d.id, p.id)} alt={title} /></div>
            <span className="block text-[9px] text-[#9A9BA3] truncate mt-0.5" title={`${String(p.at).slice(0, 16).replace("T", " ")} · ${p.by}${p.note ? ` · ${p.note}` : ""}`}>{String(p.at).slice(5, 16).replace("T", " ")} · {p.by}</span>
            {canUpdate && !locked && <button data-testid={`logistics-photo-del-${p.id}`} className="absolute -top-1.5 -right-1.5 bg-white rounded-full shadow p-0.5 text-[#C0341D]" onClick={() => onDel(p.id)}><X size={12} /></button>}
          </div>
        ))}
        {canUpdate && (
          <label data-testid={`logistics-upload-${kind}-label`} className={`w-[88px] aspect-square rounded-md border-2 border-dashed border-[#CDD2DA] flex flex-col items-center justify-center text-[#6B6B73] cursor-pointer hover:border-[#0058CC] hover:text-[#0058CC] ${busy === `photo-${kind}` ? "opacity-50 pointer-events-none" : ""}`}>
            <Camera size={16} /><span className="text-[9.5px] mt-1">{busy === `photo-${kind}` ? "Mengunggah…" : "Ambil / unggah"}</span>
            <input data-testid={`logistics-upload-${kind}`} type="file" accept="image/*" capture="environment" className="hidden" onChange={onPick} />
          </label>
        )}
      </div>
    </div>
  );
}
