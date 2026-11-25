import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FrostCard } from "../../components/GlassCard";
import Stepper from "../../components/Stepper";
import { Field, FIELD, Msg } from "../resident/security/ui";
import { registerPartner, checkAccount, checkPersonal, checkBank } from "../../services/api/partner";
import PartnerPage from "./PartnerPage";

const STEPS = ["Akun", "Data pribadi", "Rekening", "Media sosial"];
const BANKS = ["Bank BTN", "Bank BRI", "Bank BNI", "Bank Mandiri", "Bank BCA", "Bank Syariah Indonesia"];
const CHECKS = [(f) => checkAccount(f.account), (f) => checkPersonal(f.personal), (f) => checkBank(f.bank), () => null];

/** M1: pendaftaran mitra 4 langkah. Simulasi; tidak ada verifikasi rekening ke bank. */
export default function PartnerRegister() {
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [f, setF] = useState({
    account: { phone: "", password: "" },
    personal: { name: "", city: "" },
    bank: { bankName: "", accountNumber: "", holder: "" },
    social: { instagram: "", tiktok: "", facebook: "" },
  });
  const key = ["account", "personal", "bank", "social"][step];
  const set = (name) => (e) => setF((o) => ({ ...o, [key]: { ...o[key], [name]: e.target.value } }));
  const input = (id, label, name, props = {}) => (
    <Field id={id} label={label}>
      <input id={id} className={FIELD} value={f[key][name]} onChange={set(name)} {...props} />
    </Field>
  );

  const next = async (e) => {
    e.preventDefault();
    setError("");
    try {
      CHECKS[step](f);
      if (step < 3) { setStep(step + 1); return; }
      setBusy(true);
      await registerPartner(f);
      nav("/app/mitra");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };
  const back = () => { setError(""); setStep(step - 1); };

  return (
    <PartnerPage id="M1" title="Daftar jadi mitra" back="/app/demo" nav={null}>
      <FrostCard><Stepper steps={STEPS} current={step} /></FrostCard>
      <FrostCard>
        <form onSubmit={next} className="space-y-3" noValidate>
          <h2 className="text-[17px] font-extrabold">{`Langkah ${step + 1}: ${STEPS[step]}`}</h2>
          {step === 0 && (
            <>
              {input("m1-phone", "Nomor WhatsApp", "phone", { type: "tel", inputMode: "tel", autoComplete: "tel", placeholder: "0812-3456-7001" })}
              {input("m1-pass", "Kata sandi (minimal 6 karakter)", "password", { type: "password", autoComplete: "new-password" })}
            </>
          )}
          {step === 1 && (
            <>
              {input("m1-name", "Nama lengkap", "name", { autoComplete: "name" })}
              {input("m1-city", "Kota domisili", "city", { autoComplete: "address-level2" })}
            </>
          )}
          {step === 2 && (
            <>
              <Field id="m1-bank" label="Nama bank">
                <select id="m1-bank" className={FIELD} value={f.bank.bankName} onChange={set("bankName")}>
                  <option value="">Pilih bank</option>
                  {BANKS.map((b) => <option key={b} value={b}>{b}</option>)}
                </select>
              </Field>
              {input("m1-rek", "Nomor rekening", "accountNumber", { inputMode: "numeric" })}
              {input("m1-holder", "Nama pemilik rekening", "holder")}
              <p className="text-[12.5px] text-[color:var(--rdg-muted)]">Dipakai untuk pencairan komisi. Simulasi: rekening tidak diperiksa ke bank.</p>
            </>
          )}
          {step === 3 && (
            <>
              <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Opsional. Membantu calon pembeli mengenal Anda.</p>
              {input("m1-ig", "Instagram", "instagram", { placeholder: "@namaanda" })}
              {input("m1-tt", "TikTok", "tiktok", { placeholder: "@namaanda" })}
              {input("m1-fb", "Facebook", "facebook")}
            </>
          )}
          <Msg error={error} />
          <div className="flex gap-2 pt-1">
            {step > 0 && <button type="button" className="rdg-btn-ghost flex-1" onClick={back}>Kembali</button>}
            <button type="submit" className="rdg-btn-primary flex-1" disabled={busy}>{step < 3 ? "Lanjut" : "Selesai & daftar"}</button>
          </div>
        </form>
      </FrostCard>
    </PartnerPage>
  );
}
