import { Landmark } from "lucide-react";

const EMPTY_BANK = { bank_name: "", branch: "", account_no: "", account_holder: "", swift_code: "", currency: "" };

/** PB-02 — rekening bank supplier (SWIFT wajib terasa penting untuk supplier impor). */
export function SupplierBankFields({ value, isImport, onChange }) {
  const b = { ...EMPTY_BANK, ...(value || {}) };
  const set = (k) => (e) => onChange({ ...b, [k]: e.target.value });
  const swiftOk = !b.swift_code || /^[A-Z0-9]{8}([A-Z0-9]{3})?$/.test(b.swift_code.toUpperCase().replace(/\s/g, ""));
  return (
    <div className="rounded-lg border border-[#EFF0F2] bg-[#FAFBFC] p-2.5" data-testid="supplier-bank-section">
      <p className="mb-2 flex items-center gap-1.5 text-[10.5px] font-bold uppercase text-[#6B6B73]">
        <Landmark size={12} /> Rekening Bank Supplier
        {isImport && <span className="rounded bg-[#FFF4E5] px-1.5 py-0.5 text-[9.5px] font-bold normal-case text-[#B45309]">impor — isi SWIFT</span>}
      </p>
      <div className="grid grid-cols-2 gap-2 md:grid-cols-3">
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Nama Bank</span>
          <input data-testid="supplier-bank-name" className="field" value={b.bank_name} onChange={set("bank_name")} placeholder="mis. HSBC / BCA" />
        </label>
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Cabang</span>
          <input data-testid="supplier-bank-branch" className="field" value={b.branch} onChange={set("branch")} placeholder="opsional" />
        </label>
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Nomor Rekening</span>
          <input data-testid="supplier-bank-account-no" className="field" value={b.account_no} onChange={set("account_no")} placeholder="1234567890" />
        </label>
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Nama Pemilik Rekening</span>
          <input data-testid="supplier-bank-holder" className="field" value={b.account_holder} onChange={set("account_holder")} placeholder="sesuai buku bank" />
        </label>
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Kode SWIFT / BIC {isImport && <span className="req">*</span>}</span>
          <input data-testid="supplier-bank-swift" className={`field font-mono uppercase ${swiftOk ? "" : "!border-red-400"}`}
            value={b.swift_code} onChange={set("swift_code")} placeholder="8 atau 11 karakter, mis. HSBCHKHHHKH" />
          {!swiftOk && <span data-testid="supplier-bank-swift-error" className="text-[10px] text-red-600">Format SWIFT: 8 atau 11 huruf/angka.</span>}
        </label>
        <label className="block">
          <span className="mb-1 block text-[10.5px] font-semibold text-[#6B6B73]">Mata Uang</span>
          <input data-testid="supplier-bank-currency" className="field uppercase" value={b.currency} onChange={set("currency")} placeholder={isImport ? "USD / CNY" : "IDR"} />
        </label>
      </div>
    </div>
  );
}

export const bankSummary = (bank) => {
  if (!bank || !(bank.bank_name || bank.account_no || bank.swift_code)) return "";
  return [bank.bank_name, bank.account_no, bank.swift_code ? `SWIFT ${bank.swift_code}` : "", bank.currency]
    .filter(Boolean).join(" · ");
};
