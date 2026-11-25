import React, { useCallback, useState } from "react";
import { Smartphone, Wifi, Zap, Droplets, CircleCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { FrostCard } from "../../../components/GlassCard";
import PayFlow from "../../../components/PayFlow";
import ReceiptCard from "../../../components/pay/ReceiptCard";
import { getTopUpCatalog, createTopUp, topUpResult } from "../../../services/api/bills";
import { FIELD } from "../security/ui";
import { rupiah } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";

const ICON = { pulsa: Smartphone, data: Wifi, pln: Zap, pdam: Droplets };
const NAME = { pulsa: "Pulsa", data: "Paket data", pln: "Token listrik", pdam: "Air PDAM" };

const chip = (on) => `rdg-btn-ghost !justify-start !text-left ${on ? "!border-rdg-forest !bg-[#e7ffef] font-extrabold" : ""}`;

/** W13: pilih produk, isi nomor, pilih nominal, bayar lewat PayFlow, lihat token/struk. Simulasi tanpa penyedia asli. */
export default function TopUp() {
  const fetcher = useCallback(() => getTopUpCatalog(), []);
  const { data: catalog, error } = useLoad(fetcher, ["bills"]);
  const [product, setProduct] = useState(null);
  const [target, setTarget] = useState("");
  const [nominal, setNominal] = useState(null);
  const [problem, setProblem] = useState("");
  const [pay, setPay] = useState(null);
  const [done, setDone] = useState(null);
  const cur = catalog && product ? catalog[product] : null;

  const pick = (id) => { setProduct(id); setNominal(null); setProblem(""); setDone(null); };
  const submit = async (e) => {
    e.preventDefault();
    setProblem("");
    try {
      setPay(await createTopUp({ product, target, nominal }));
    } catch (err) {
      setProblem(err.message);
    }
  };
  const result = done ? topUpResult(done) : null;

  return (
    <Page id="W13" title="Bayar & Isi Ulang" back="/app/warga/tagihan" nav="resident">
      {!catalog && <Loading error={error} />}
      {catalog && !result && (
        <>
          <div role="group" aria-label="Pilih produk" className="grid grid-cols-2 gap-2">
            {Object.keys(NAME).map((id) => {
              const Icon = ICON[id];
              return (
                <button key={id} type="button" aria-pressed={product === id} className={chip(product === id)} onClick={() => pick(id)}>
                  <Icon size={18} aria-hidden="true" /> {NAME[id]}
                </button>
              );
            })}
          </div>
          {cur && (
            <form onSubmit={submit} className="space-y-3" noValidate>
              <FrostCard className="space-y-2">
                <label htmlFor="w13-no" className="block text-[14px] font-bold">{cur.field}</label>
                <input
                  id="w13-no" inputMode="numeric" autoComplete="off" value={target}
                  onChange={(e) => setTarget(e.target.value)} className={FIELD}
                  placeholder={product === "pln" ? "Contoh: 12345678901" : product === "pdam" ? "Nomor pelanggan" : "Contoh: 081234567001"}
                />
              </FrostCard>
              <fieldset className="space-y-2">
                <legend className="mb-1 text-[14px] font-bold">Pilih nominal</legend>
                <div className="grid grid-cols-2 gap-2">
                  {cur.options.map((o) => (
                    <button key={o.id} type="button" aria-pressed={nominal === o.nominal} className={chip(nominal === o.nominal)} onClick={() => setNominal(o.nominal)}>
                      <span>{o.label}<span className="block text-[13px] font-semibold text-[color:var(--rdg-muted)]">{rupiah(o.price)}</span></span>
                    </button>
                  ))}
                </div>
              </fieldset>
              {problem && <p role="alert" className="text-[14px] font-semibold text-[color:var(--rdg-sos-ink)]">{problem}</p>}
              <button type="submit" className="rdg-btn-primary w-full">Lanjut bayar</button>
              <p className="text-[13px] text-[color:var(--rdg-muted)]">Isi ulang di prototipe ini disimulasikan; tidak ada pulsa atau token sungguhan yang dikirim.</p>
            </form>
          )}
        </>
      )}
      {result && (
        <>
          <FrostCard className="space-y-2">
            <p className="flex items-center gap-2 text-[17px] font-extrabold"><CircleCheck size={22} className="text-rdg-green" aria-hidden="true" /> {result.struk.label} berhasil</p>
            <p className="text-[14px] text-[color:var(--rdg-muted)]">Tujuan {result.struk.target}</p>
            {result.token && (
              <>
                <p className="pt-1 text-[13.5px] font-semibold text-[color:var(--rdg-muted)]">Token listrik</p>
                <p data-testid="pln-token" className="whitespace-nowrap text-[19px] font-extrabold tracking-[0.02em]">{result.token}</p>
              </>
            )}
          </FrostCard>
          {result.struk.receipt && <ReceiptCard receipt={result.struk.receipt} />}
          <button type="button" className="rdg-btn-ghost w-full" onClick={() => { setDone(null); setProduct(null); setTarget(""); setNominal(null); }}>Isi ulang lagi</button>
        </>
      )}
      {pay && (
        <PayFlow
          open
          onClose={() => setPay(null)}
          target={{ type: "ppob", id: pay.targetId, title: pay.title, amount: pay.amount }}
          onPaid={() => setDone(pay.targetId)}
        />
      )}
    </Page>
  );
}
