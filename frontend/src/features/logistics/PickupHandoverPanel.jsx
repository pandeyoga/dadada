import { useState } from "react";
import { KeyRound, ShieldCheck, Copy, MessageCircle, EyeOff } from "lucide-react";
import { askConfirm } from "../../services/confirmService";
import { pickupHandover, waUrl } from "./logisticsApi";

// Serah terima barang ke pelanggan yang AMBIL SENDIRI: petugas memasukkan kode pickup yang
// disebut pengambil + nama & no. identitas. Kode salah → barang TIDAK boleh diserahkan.
export default function PickupHandoverPanel({ d, canUpdate, canManage, onDone }) {
  const [f, setF] = useState({ pickup_code: "", picker_name: "", picker_id_no: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const waText = `Halo ${d.customer_name}, pesanan ${d.order_number} sudah SIAP DIAMBIL di gudang${d.pickup_date ? ` (tgl ${d.pickup_date})` : ""}. Tunjukkan KODE PICKUP: ${d.pickup_code} dan bawa identitas pengambil. Terima kasih.`;

  async function submit() {
    setErr("");
    if (!(await askConfirm({ title: "Serahkan barang ke pengambil?", description: `${f.picker_name}${f.picker_id_no ? ` (ID ${f.picker_id_no})` : ""} — kode akan diverifikasi sistem. Setelah diserahkan tidak bisa dibatalkan.`, confirmLabel: "Serahkan" }))) return;
    setBusy(true);
    try { await pickupHandover(d.id, f); await onDone("Barang diserahkan — kode pickup tervalidasi."); }
    catch (e) { setErr(e.response?.data?.detail || "Gagal memproses serah terima."); }
    finally { setBusy(false); }
  }

  return (
    <div className="rounded-lg border border-[#D9C6EA] bg-[#F8F3FC] p-3 mt-3" data-testid="pickup-panel">
      <p className="text-[12px] font-bold flex items-center gap-1.5 text-[#6B219A]"><KeyRound size={14} /> Pelanggan ambil sendiri — tanpa alamat kirim, sopir, atau kendaraan</p>
      {d.status === "prepared" && (
        <div className="grid gap-3 sm:grid-cols-2 mt-2">
          <div className="rounded-md bg-white border border-[#E9DDF3] p-2.5" data-testid="pickup-code-box">
            <p className="text-[10.5px] font-bold uppercase text-[#6B6B73]">Kode pickup (dibagikan ke pelanggan)</p>
            {d.pickup_code ? (<>
              <p className="font-mono text-[26px] font-bold tracking-[0.25em] text-[#6B219A]" data-testid="pickup-code">{d.pickup_code}</p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                <button type="button" data-testid="pickup-code-copy" className="secondary-button !py-1 !px-2 !text-[11px]" onClick={() => navigator.clipboard?.writeText(d.pickup_code)}><Copy size={11} /> Salin</button>
                {d.receiver_phone && <a data-testid="pickup-code-wa" href={waUrl(d.receiver_phone, waText)} target="_blank" rel="noopener noreferrer" className="secondary-button !py-1 !px-2 !text-[11px] !border-[#1F7A45] !text-[#1F7A45]"><MessageCircle size={11} /> Kirim via WA</a>}
              </div>
              <p className="text-[10px] text-[#9A9BA3] mt-1">Sales/admin membagikan kode ini ke pelanggan. Petugas gudang tidak melihat kode — ia hanya mencocokkan kode yang disebut pengambil.</p>
            </>) : (
              <p className="text-[11.5px] text-[#6B6B73] flex items-center gap-1.5 mt-1" data-testid="pickup-code-hidden"><EyeOff size={13} /> Kode disembunyikan untuk peran Anda. Minta pengambil menyebutkan kode dari sales/konfirmasi pesanan.</p>
            )}
            {d.pickup_attempts > 0 && <p className="text-[10.5px] text-[#C62828] mt-1" data-testid="pickup-attempts">{d.pickup_attempts}× percobaan kode salah tercatat.</p>}
          </div>
          <div className="rounded-md bg-white border border-[#E9DDF3] p-2.5" data-testid="pickup-handover-form">
            <p className="text-[10.5px] font-bold uppercase text-[#6B6B73] flex items-center gap-1"><ShieldCheck size={12} /> Serah terima (petugas gudang)</p>
            {canUpdate ? (<>
              <input data-testid="pickup-input-code" className="form-input font-mono uppercase tracking-widest mt-1" placeholder="Kode pickup dari pengambil *" value={f.pickup_code} onChange={set("pickup_code")} maxLength={12} />
              <input data-testid="pickup-input-name" className="form-input mt-1.5" placeholder="Nama pengambil *" value={f.picker_name} onChange={set("picker_name")} />
              <input data-testid="pickup-input-id" className="form-input mt-1.5" placeholder="No. KTP / SIM pengambil (disarankan)" value={f.picker_id_no} onChange={set("picker_id_no")} />
              <input data-testid="pickup-input-note" className="form-input mt-1.5" placeholder="Catatan (opsional)" value={f.note} onChange={set("note")} />
              {err && <p className="text-[11px] text-[#C62828] font-semibold mt-1.5" data-testid="pickup-error">{err}</p>}
              <button data-testid="pickup-submit" className="primary-button !bg-[#6B219A] w-full mt-2" disabled={busy || f.pickup_code.trim().length < 4 || f.picker_name.trim().length < 2} onClick={submit}><ShieldCheck size={13} /> {busy ? "Memverifikasi…" : "Verifikasi & serahkan"}</button>
              <p className="text-[9.5px] text-[#9A9BA3] mt-1">Foto bukti serah terima (POD) bisa diunggah di bawah — disarankan foto pengambil bersama barang.</p>
            </>) : <p className="text-[11.5px] text-[#6B6B73] mt-1">Serah terima dilakukan petugas gudang saat pelanggan datang.</p>}
          </div>
        </div>
      )}
      {d.pod && (
        <div className="mt-2 text-[11.5px] text-[#1F7A45]" data-testid="pickup-pod-info">
          <b>Diserahkan ke {d.pod.receiver_name}</b>{d.pod.id_no ? ` · ID ${d.pod.id_no}` : ""} · {String(d.pod.received_at).slice(0, 16).replace("T", " ")} · oleh {d.pod.by}{d.pod.verified_by_code ? " · kode pickup tervalidasi ✓" : ""}
        </div>
      )}
    </div>
  );
}
