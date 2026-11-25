import React, { useState } from "react";
import { Phone, Plus, Trash2 } from "lucide-react";
import { FrostCard } from "../../../components/GlassCard";
import ListRow from "../../../components/ListRow";
import Sheet from "../../../components/Sheet";
import { removeContact, saveContact } from "../../../services/api/sos";
import { useProto } from "../../../services/useStore";
import Page from "../../buyer/Page";
import { FIELD, Field, Msg } from "./ui";

function ContactForm({ onDone }) {
  const [v, setV] = useState({ name: "", phone: "", relation: "Keluarga" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setV({ ...v, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await saveContact(v);
      onDone();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-3">
      <Field id="ct-name" label="Nama"><input id="ct-name" className={FIELD} value={v.name} onChange={set("name")} autoComplete="off" /></Field>
      <Field id="ct-phone" label="Nomor telepon"><input id="ct-phone" className={FIELD} inputMode="tel" value={v.phone} onChange={set("phone")} placeholder="0812…" autoComplete="off" /></Field>
      <Field id="ct-rel" label="Hubungan">
        <select id="ct-rel" className={FIELD} value={v.relation} onChange={set("relation")}>
          {["Keluarga", "Tetangga", "Ketua RT", "Keamanan", "Lainnya"].map((r) => <option key={r}>{r}</option>)}
        </select>
      </Field>
      <Msg error={error} />
      <button type="submit" className="rdg-btn-primary w-full" disabled={busy}>Simpan kontak</button>
    </form>
  );
}

export default function SosContacts() {
  const contacts = useProto((s) => s.security.contacts);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState("");
  const remove = async (id) => {
    setErr("");
    try { await removeContact(id); } catch (e) { setErr(e.message); }
  };
  return (
    <Page id="W9" title="Kontak darurat" back="/app/warga/sos" nav="resident">
      <FrostCard>
        <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Kontak ini tampil di layar SOS agar mudah dihubungi saat darurat.</p>
        <Msg error={err} />
        <ul className="mt-1 divide-y divide-[color:var(--rdg-line)]">
          {contacts.map((c) => (
            <li key={c.id}>
              <ListRow
                icon={Phone} title={c.name} subtitle={`${c.role} · ${c.phone}`}
                right={
                  <button type="button" aria-label={`Hapus ${c.name}`} className="rdg-icon-btn rdg-icon-btn--light" onClick={() => remove(c.id)}>
                    <Trash2 size={18} aria-hidden="true" />
                  </button>
                }
              />
            </li>
          ))}
        </ul>
        {!contacts.length && <p className="py-3 text-[14px] text-[color:var(--rdg-muted)]">Belum ada kontak darurat.</p>}
        <button type="button" className="rdg-btn-primary mt-3 w-full" onClick={() => setOpen(true)}><Plus size={17} aria-hidden="true" /> Tambah kontak</button>
      </FrostCard>
      <Sheet open={open} onClose={() => setOpen(false)} title="Tambah kontak">
        <ContactForm onDone={() => setOpen(false)} />
      </Sheet>
    </Page>
  );
}
