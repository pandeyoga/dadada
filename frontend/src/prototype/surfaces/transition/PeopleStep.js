import React, { forwardRef, useImperativeHandle, useState } from "react";
import { Phone, Trash2 } from "lucide-react";
import ListRow from "../../components/ListRow";

const field = "h-12 w-full rounded-2xl border-2 border-[rgba(0,103,71,0.22)] bg-white px-4 text-[15px] font-medium text-rdg-ink900 focus:border-rdg-teal focus:outline-none";
const digits = (v) => String(v || "").replace(/\D/g, "");

// Keluarga punya `relation` tampilan ("Suami") di samping id `role` ("keluarga"); kontak darurat hanya `role` tampilan.
const subtitleOf = (p) => [p.relation || p.role || "Kontak", p.phone].filter(Boolean).join(" · ");

/**
 * Daftar orang (nama + nomor) dengan formulir tambah; dipakai langkah keluarga dan kontak darurat.
 * `ref.flush()` dipanggil saat Lanjut/Selesai: isian yang sudah diketik tapi belum ditambahkan ikut
 * ditambahkan bila valid (mengembalikan daftar baru), atau ditahan dengan pesan (mengembalikan null).
 */
const PeopleStep = forwardRef(function PeopleStep({ idPrefix, items, existing = [], onChange, addLabel = "Tambah" }, ref) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const check = () => {
    const n = name.trim();
    const d = digits(phone);
    if (!n) return { error: "Nama belum diisi" };
    if (d.length < 10) return { error: "Nomor WhatsApp belum lengkap" };
    const taken = [...existing, ...items].some((x) => x.name.toLowerCase() === n.toLowerCase() || (x.phone && digits(x.phone) === d));
    if (taken) return { error: "Nama atau nomor ini sudah ada di daftar" };
    return { item: { name: n, phone } };
  };
  const commit = (item) => {
    const next = [...items, item];
    onChange(next);
    setName(""); setPhone(""); setError("");
    return next;
  };
  const add = () => {
    const r = check();
    if (r.error) return setError(r.error);
    return commit(r.item);
  };
  useImperativeHandle(ref, () => ({
    flush() {
      if (!name.trim() && !phone.trim()) return items;
      const r = check();
      if (r.error) {
        setError(`${r.error}. Lengkapi lalu ketuk ${addLabel}, atau kosongkan isian.`);
        return null;
      }
      return commit(r.item);
    },
  }));
  return (
    <div className="space-y-3">
      {(existing.length > 0 || items.length > 0) && (
        <ul className="divide-y divide-[color:var(--rdg-line)] rounded-2xl bg-white/80 px-3" aria-label="Daftar">
          {existing.map((p) => (
            <li key={p.id}><ListRow icon={Phone} title={p.name} subtitle={subtitleOf(p)} /></li>
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
});

export default PeopleStep;
