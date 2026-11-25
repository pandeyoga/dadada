import React, { useState } from "react";
import { Phone, Trash2 } from "lucide-react";
import ListRow from "../../components/ListRow";

const field = "h-12 w-full rounded-2xl border-2 border-[rgba(0,103,71,0.22)] bg-white px-4 text-[15px] font-medium text-rdg-ink900 focus:border-rdg-teal focus:outline-none";

/** Daftar orang (nama + nomor) dengan formulir tambah; dipakai langkah keluarga dan kontak darurat. */
export default function PeopleStep({ idPrefix, items, existing = [], onChange, addLabel = "Tambah" }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const add = () => {
    if (!name.trim()) return setError("Nama belum diisi");
    if (phone.replace(/\D/g, "").length < 10) return setError("Nomor WhatsApp belum lengkap");
    onChange([...items, { name: name.trim(), phone }]);
    setName(""); setPhone(""); setError("");
  };
  return (
    <div className="space-y-3">
      {(existing.length > 0 || items.length > 0) && (
        <ul className="divide-y divide-[color:var(--rdg-line)] rounded-2xl bg-white/80 px-3" aria-label="Daftar">
          {existing.map((p) => (
            <li key={p.id}><ListRow icon={Phone} title={p.name} subtitle={`${p.role || "Kontak"} · ${p.phone}`} /></li>
          ))}
          {items.map((p, i) => (
            <li key={`${p.name}-${i}`}>
              <ListRow
                icon={Phone}
                title={p.name}
                subtitle={p.phone}
                right={
                  <button type="button" aria-label={`Hapus ${p.name}`} className="rdg-icon-btn rdg-icon-btn--light" onClick={() => onChange(items.filter((_, j) => j !== i))}>
                    <Trash2 size={18} aria-hidden="true" />
                  </button>
                }
              />
            </li>
          ))}
        </ul>
      )}
      <div>
        <label htmlFor={`${idPrefix}-name`} className="mb-1 block text-[13px] font-semibold text-[color:var(--rdg-muted)]">Nama</label>
        <input id={`${idPrefix}-name`} className={field} value={name} onChange={(e) => setName(e.target.value)} autoComplete="off" />
      </div>
      <div>
        <label htmlFor={`${idPrefix}-phone`} className="mb-1 block text-[13px] font-semibold text-[color:var(--rdg-muted)]">Nomor WhatsApp</label>
        <input id={`${idPrefix}-phone`} className={field} inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} autoComplete="off" />
      </div>
      {error && <p role="alert" className="text-[13px] font-semibold text-[color:var(--rdg-sos-ink)]">{error}</p>}
      <button type="button" className="rdg-btn-ghost w-full" onClick={add}>{addLabel}</button>
    </div>
  );
}
