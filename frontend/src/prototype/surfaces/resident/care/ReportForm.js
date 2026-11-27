import React, { useState } from "react";
import { Check } from "lucide-react";
import { Msg, Field, FIELD } from "../security/ui";
import TicketPhoto, { PHOTO_OPTIONS } from "./TicketPhoto";
import { createTicket } from "../../../services/api/care";

export const CATEGORIES = ["Kebocoran", "Listrik", "Air dan pipa", "Dinding dan cat", "Pintu dan jendela", "Lainnya"];
const MAX_PHOTOS = 3;

/** Formulir laporan: kategori, 1–3 foto contoh (ilustrasi lokal), deskripsi. */
export default function ReportForm({ onDone }) {
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [photos, setPhotos] = useState([]);
  const [text, setText] = useState("");
  const [problem, setProblem] = useState("");
  const [busy, setBusy] = useState(false);
  const toggle = (id) => setPhotos((p) => (p.includes(id) ? p.filter((x) => x !== id) : p.length < MAX_PHOTOS ? [...p, id] : p));
  const submit = async (e) => {
    e.preventDefault();
    setProblem(""); setBusy(true);
    try { await createTicket({ kind: "rusak", category, description: text, photos }); onDone(); } catch (err) { setProblem(err.message); setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" noValidate>
      <fieldset>
        <legend className="mb-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">Kategori</legend>
        <div className="flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button key={c} type="button" aria-pressed={category === c} onClick={() => setCategory(c)}
              className={`rdg-btn-ghost !min-h-[44px] !px-3 ${category === c ? "!border-rdg-forest !bg-[#e7ffef] font-extrabold" : ""}`}>{c}</button>
          ))}
        </div>
      </fieldset>
      <fieldset>
        <legend className="mb-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">{`Foto contoh (pilih sampai ${MAX_PHOTOS})`}</legend>
        <p className="mb-2 text-[13px] text-[color:var(--rdg-muted)]">Foto contoh — ilustrasi, bukan foto rumah Anda.</p>
        <div className="grid grid-cols-4 gap-2">
          {PHOTO_OPTIONS.map((p) => {
            const on = photos.includes(p.id);
            return (
              <button key={p.id} type="button" aria-pressed={on} aria-label={`Foto ${p.label}`} onClick={() => toggle(p.id)}
                className={`relative aspect-square overflow-hidden rounded-xl border-2 ${on ? "border-rdg-forest" : "border-transparent"}`}>
                <TicketPhoto img={p.id} className="h-full w-full" tag={false} />
                {on && <span className="absolute right-1 top-1 grid h-5 w-5 place-items-center rounded-full bg-rdg-forest text-white"><Check size={13} strokeWidth={3} aria-hidden="true" /></span>}
              </button>
            );
          })}
        </div>
      </fieldset>
      <Field id="w21-desk" label="Ceritakan kerusakannya">
        <textarea id="w21-desk" rows={3} value={text} onChange={(e) => setText(e.target.value)} className={`${FIELD} py-2`} placeholder="Contoh: Atap dapur merembes saat hujan deras" />
      </Field>
      <Msg error={problem} />
      <button type="submit" className="rdg-btn-primary w-full" disabled={busy}>Kirim laporan</button>
    </form>
  );
}
