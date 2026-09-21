import { useState } from "react";
import { X, UserPlus } from "lucide-react";
import LocationFields, { locationIncomplete } from "../../components/LocationFields";

/** EPIC5 — Buat Customer sebagai MODAL (dipanggil dari checkout step 1).
 * SALES REVAMP V2 — Kebijakan lot DIPINDAH ke Manajemen Pelanggan (CustomerFormModal).
 * Quick-add POS hanya data dasar; lot policy diatur di Manajemen Pelanggan. */
export default function CreateCustomerModal({ open, onClose, onCreateCustomer, user = null }) {
  const [form, setForm] = useState({
    name: "", pic_name: "", phone: "", city: "", address: "",
  });
  const [busy, setBusy] = useState(false);
  if (!open) return null;

  const valid = form.name.trim() && form.pic_name.trim() && form.phone.trim() && form.city && form.address.trim().length >= 3 && !locationIncomplete(form);

  async function submit() {
    if (!valid) return;
    setBusy(true);
    try {
      await onCreateCustomer(form);
      onClose();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[120] flex items-center justify-center bg-black/40 p-4" data-testid="create-customer-modal">
      <div className="w-full max-w-md rounded-xl bg-white shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#EFF0F2] px-4 py-3">
          <div className="flex items-center gap-2">
            <UserPlus size={16} className="text-[#0058CC]" />
            <h3 className="text-[14px] font-bold">Pelanggan Baru</h3>
          </div>
          <button data-testid="create-customer-close" className="icon-button" onClick={onClose} aria-label="Tutup"><X size={16} /></button>
        </div>
        <div className="grid gap-2 p-4">
          <Label>Nama toko / pelanggan <Req /></Label>
          <input data-testid="new-customer-name-input" className="field" placeholder="PT / Toko ..." value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Label>PIC toko (pihak pelanggan) <Req /></Label>
          <div className="grid gap-2 sm:grid-cols-2">
            <input data-testid="new-customer-pic-input" className="field" placeholder="Nama PIC toko" value={form.pic_name} onChange={(e) => setForm({ ...form, pic_name: e.target.value })} />
            <input data-testid="new-customer-phone-input" className="field" placeholder="No. HP / WhatsApp PIC toko" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
          </div>
          <Label>Alamat toko <Req /></Label>
          <div className="grid gap-2 sm:grid-cols-2">
            <LocationFields testId="new-customer-loc" compact value={form} onChange={(patch) => setForm((p) => ({ ...p, ...patch }))} />
            <input data-testid="new-customer-address-input" className="field" placeholder="Jalan, nomor, patokan" value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} />
          </div>
          <p data-testid="new-customer-sales-note" className="rounded-md border border-[#CDE9D6] bg-[#F4FCF6] px-2.5 py-2 text-[10.5px] text-[#1A7A3A]">
            {user?.role === "sales"
              ? <>Sales penanggung jawab: <b>{user?.name}</b> (akun Anda) — otomatis, tak perlu dipilih.</>
              : <>Sales penanggung jawab & tim sales diatur di <b>Manajemen Pelanggan</b> (akun {user?.role || "non-sales"} tidak otomatis menjadi pemilik).</>}
          </p>
          <p data-testid="new-customer-lot-note" className="rounded-md border border-[#EFF0F2] bg-[#FAFBFC] px-2.5 py-2 text-[10.5px] text-[#6B6B73]">
            Segment (untuk BI), kebijakan lot / dye-lot &amp; tim sales diatur di <b>Manajemen Pelanggan</b>.
          </p>
          <div className="mt-1 flex justify-end gap-2">
            <button className="secondary-button" onClick={onClose}>Batal</button>
            <button data-testid="create-customer-button" className="primary-button" disabled={!valid || busy} onClick={submit}>
              <UserPlus size={14} /> {busy ? "Menyimpan..." : "Buat Customer"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const Label = ({ children }) => <p className="text-[10.5px] font-semibold text-[#4A4B53] -mb-1">{children}</p>;
const Req = () => <span className="text-red-500">*</span>;
