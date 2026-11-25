import React, { useEffect, useRef, useState } from "react";
import { ChevronRight, LoaderCircle, QrCode, Smartphone, MessageCircle, Check } from "lucide-react";
import { PAY_METHODS, startPayment, confirmPayment } from "../services/api/payments";
import { rupiah } from "../lib/format";
import Sheet from "./Sheet";
import PayDetails from "./pay/PayDetails";
import ReceiptCard from "./pay/ReceiptCard";

const TITLES = { method: "Pilih metode bayar", pay: "Selesaikan pembayaran", done: "Kuitansi" };
const OTHER_ICONS = { qris: QrCode, ewallet: Smartphone, wa_link: MessageCircle };
const HINTS = {
  va: "Dari m-banking atau ATM",
  qris: "Pindai dari aplikasi bank mana saja",
  ewallet: "Masukkan kode di aplikasi Anda",
  wa_link: "Minta keluarga membayarkan",
};

function Summary({ target }) {
  return (
    <div className="rdg-pay-summary">
      <div className="min-w-0">
        <p className="text-[12.5px] font-semibold text-white/85">Untuk</p>
        <p className="text-[15px] font-bold leading-snug">{target.title}</p>
      </div>
      <p className="flex-none text-[20px] font-extrabold tracking-[-0.01em]">{rupiah(target.amount)}</p>
    </div>
  );
}

function MethodButton({ m, busy, onPick }) {
  const Icon = OTHER_ICONS[m.id];
  return (
    <button type="button" className="rdg-pay-method" disabled={!!busy} aria-busy={busy === m.id} onClick={() => onPick(m)}>
      <span className={m.bank && m.bank.length > 4 ? "rdg-pay-badge rdg-pay-badge--long" : "rdg-pay-badge"} aria-hidden="true">
        {Icon ? <Icon size={21} /> : m.bank}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-[15px] font-bold">{m.label}</span>
        <span className="block text-[12.5px] text-[color:var(--rdg-muted)]">{HINTS[m.kind]}</span>
      </span>
      {busy === m.id ? (
        <LoaderCircle size={20} className="animate-spin text-rdg-forest" aria-hidden="true" />
      ) : (
        <ChevronRight size={18} className="text-[color:var(--rdg-muted)]" aria-hidden="true" />
      )}
    </button>
  );
}

function PayFlowSheet({ onClose, target, onPaid }) {
  const [payment, setPayment] = useState(null);
  const [receipt, setReceipt] = useState(null);
  const [busy, setBusy] = useState(null); // id metode | 'confirm' | null
  const [error, setError] = useState("");
  const lock = useRef(false); // cegah klik ganda sebelum render berikutnya
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true; // StrictMode memasang ulang efek: set lagi setiap pasang
    return () => { alive.current = false; };
  }, []);

  // Semua pembaruan state setelah `await` berjalan sinkron dalam satu giliran.
  const run = async (key, task) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(key);
    setError("");
    let apply;
    try {
      apply = await task();
    } catch (e) {
      apply = () => setError(e.message || "Pembayaran gagal, coba lagi.");
    }
    lock.current = false;
    if (alive.current) {
      setBusy(null);
      apply();
    }
  };

  const pick = (m) =>
    run(m.id, async () => {
      const p = await startPayment({ targetType: target.type, targetId: target.id, amount: target.amount, title: target.title }, m.id);
      return () => setPayment(p);
    });

  const confirm = () =>
    run("confirm", async () => {
      const res = await confirmPayment(payment.id);
      onPaid?.(res);
      return () => setReceipt(res.receipt);
    });

  const step = receipt ? "done" : payment ? "pay" : "method";
  const err = error && <p role="alert" className="rdg-pay-error">{error}</p>;

  return (
    <Sheet open onClose={onClose} title={TITLES[step]}>
      {step === "method" && (
        <>
          <Summary target={target} />
          <p className="rdg-pay-group">Transfer virtual account</p>
          {PAY_METHODS.filter((m) => m.kind === "va").map((m) => <MethodButton key={m.id} m={m} busy={busy} onPick={pick} />)}
          <p className="rdg-pay-group">Cara lain</p>
          {PAY_METHODS.filter((m) => m.kind !== "va").map((m) => <MethodButton key={m.id} m={m} busy={busy} onPick={pick} />)}
          {err}
        </>
      )}
      {step === "pay" && (
        <>
          <Summary target={target} />
          <PayDetails payment={payment} />
          {err}
          <div className="rdg-sheet-footer">
            <button type="button" className="rdg-btn-primary w-full" disabled={!!busy} onClick={confirm}>
              {busy === "confirm" && <LoaderCircle size={18} className="animate-spin" aria-hidden="true" />}
              Saya sudah bayar
            </button>
            <button type="button" className="rdg-btn-ghost w-full" disabled={!!busy} onClick={() => setPayment(null)}>
              Ganti metode
            </button>
          </div>
        </>
      )}
      {step === "done" && (
        <div className="pt-2 text-center">
          <span className="rdg-success"><Check size={38} strokeWidth={3} aria-hidden="true" /></span>
          <h3 className="mt-5 text-[20px] font-extrabold tracking-[-0.01em]">Pembayaran berhasil</h3>
          <p className="mt-1 text-[14px] text-[color:var(--rdg-muted)]">Kuitansi tersimpan di riwayat pembayaran.</p>
          <ReceiptCard receipt={receipt} />
          <div className="rdg-sheet-footer">
            <button type="button" className="rdg-btn-primary w-full" onClick={onClose}>Selesai</button>
          </div>
        </div>
      )}
    </Sheet>
  );
}

/**
 * Alur bayar dalam bottom sheet: pilih metode → kode VA/QRIS/dompet/tautan WA →
 * "Saya sudah bayar" → lunas + kuitansi. `target = {type, id, title, amount}`
 * dengan `type` ∈ installment|bill|ppob|market. `onPaid({payment, receipt})`
 * dipanggil sekali setelah lunas. State direset setiap kali dibuka.
 */
export default function PayFlow({ open, onClose, target, onPaid }) {
  if (!open) return null;
  return <PayFlowSheet onClose={onClose} target={target} onPaid={onPaid} />;
}
