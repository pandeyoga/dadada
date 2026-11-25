import React, { useState } from "react";
import { MessageCircle } from "lucide-react";
import Sheet from "../../components/Sheet";
import QrPattern from "../../components/QrPattern";
import CopyButton from "../../components/pay/CopyButton";
import { Field, FIELD, Msg } from "../resident/security/ui";
import { shareLink, simulateKpr } from "../../services/api/partner";
import { rupiah } from "../../lib/format";

/** Sheet bagikan: tautan beratribusi (teks + salin), QR lokal, dan anchor WhatsApp. Tautan tidak pernah dibuka dari aplikasi. */
export function ShareSheet({ unit, onClose }) {
  const link = unit ? shareLink(unit.id) : null;
  const wa = link ? `https://wa.me/?text=${encodeURIComponent(`Halo, lihat unit ${unit.block} tipe ${unit.type} di Estora Residence: ${link.url}`)}` : "#";
  return (
    <Sheet open={!!unit} onClose={onClose} title={unit ? `Bagikan unit ${unit.block}` : "Bagikan unit"}>
      {unit && (
        <div className="space-y-3 text-center">
          <div className="mx-auto w-fit"><QrPattern value={link.qrText} label={`Kode QR tautan unit ${unit.block}`} size={176} /></div>
          <p className="rdg-pay-link" data-testid="share-url">{link.url}</p>
          <CopyButton text={link.url} label="Salin tautan" />
          <a href={wa} target="_blank" rel="noreferrer" className="rdg-btn-primary w-full"><MessageCircle size={18} aria-hidden="true" /> Bagikan lewat WhatsApp</a>
          <p className="text-[12.5px] text-[color:var(--rdg-muted)]">Pembeli yang memakai tautan ini tercatat sebagai rujukan Anda.</p>
        </div>
      )}
    </Sheet>
  );
}

/** Sheet simulasi KPR per unit. Simulasi, bukan penawaran bank. */
export function KprSheet({ unit, onClose }) {
  const [f, setF] = useState({ dp: "5000000", tenorYears: "20", rate: "5" });
  const set = (k) => (e) => setF((o) => ({ ...o, [k]: e.target.value }));
  let res = null;
  let error = "";
  if (unit) {
    try { res = simulateKpr({ price: unit.price, dp: Number(f.dp), tenorYears: Number(f.tenorYears), rate: Number(f.rate) }); } catch (e) { error = e.message; }
  }
  return (
    <Sheet open={!!unit} onClose={onClose} title={unit ? `Simulasi KPR · ${unit.block}` : "Simulasi KPR"}>
      {unit && (
        <div className="space-y-3">
          <p className="text-[14px] text-[color:var(--rdg-muted)]">{`Harga ${rupiah(unit.price)} · tipe ${unit.type}`}</p>
          <Field id="kpr-dp" label="Uang muka (Rp)"><input id="kpr-dp" className={FIELD} inputMode="numeric" value={f.dp} onChange={set("dp")} /></Field>
          <div className="grid grid-cols-2 gap-3">
            <Field id="kpr-tenor" label="Tenor (tahun)"><input id="kpr-tenor" className={FIELD} inputMode="numeric" value={f.tenorYears} onChange={set("tenorYears")} /></Field>
            <Field id="kpr-rate" label="Bunga (% per tahun)"><input id="kpr-rate" className={FIELD} inputMode="decimal" value={f.rate} onChange={set("rate")} /></Field>
          </div>
          <Msg error={error} />
          {res && (
            <div className="rounded-2xl bg-[#e7ffef] p-4" aria-live="polite">
              <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Angsuran per bulan</p>
              <p className="text-[28px] font-extrabold leading-tight" data-testid="kpr-monthly">{`${rupiah(res.monthly)}/bulan`}</p>
              <p className="text-[13px] text-[color:var(--rdg-muted)]">{`Pokok ${rupiah(res.principal)} · ${res.months} bulan`}</p>
            </div>
          )}
          <p className="text-[12.5px] text-[color:var(--rdg-muted)]">Simulasi, bukan penawaran bank.</p>
        </div>
      )}
    </Sheet>
  );
}
