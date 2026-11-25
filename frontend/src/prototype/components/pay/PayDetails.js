import React from "react";
import { PAY_METHODS } from "../../services/api/payments";
import { rupiah, tanggal, jam } from "../../lib/format";
import QrPattern from "../QrPattern";
import CopyButton from "./CopyButton";

const group4 = (s) => s.replace(/(.{4})(?=.)/g, "$1 ");

function steps(method, amount) {
  const nominal = rupiah(amount);
  switch (method.kind) {
    case "va":
      return [
        `Buka m-banking, internet banking, atau ATM ${method.bank}.`,
        "Pilih menu Transfer › Virtual Account.",
        `Masukkan nomor di atas, pastikan nominal ${nominal}, lalu konfirmasi.`,
      ];
    case "qris":
      return [
        "Buka aplikasi bank atau dompet digital apa saja.",
        "Pilih Bayar/Scan QR, arahkan kamera ke kode di atas.",
        `Periksa nominal ${nominal}, lalu konfirmasi.`,
      ];
    case "ewallet":
      return [
        "Buka aplikasi dompet digital Anda.",
        "Pilih Bayar › Masukkan kode bayar.",
        `Periksa nominal ${nominal}, lalu konfirmasi.`,
      ];
    default:
      return [
        "Salin tautan, lalu kirim ke anggota keluarga lewat WhatsApp.",
        "Mereka membayar dari ponselnya sendiri.",
        "Tekan “Saya sudah bayar” setelah pembayaran selesai.",
      ];
  }
}

/** Kode bayar sesuai metode (VA/QRIS/dompet digital/tautan WhatsApp) + langkah bayar. */
export default function PayDetails({ payment }) {
  const method = PAY_METHODS.find((m) => m.id === payment.method);
  const { code } = payment;
  let body;
  if (method.kind === "va" || method.kind === "ewallet") {
    body = (
      <>
        <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">
          {method.kind === "va" ? `Nomor virtual account ${method.bank}` : "Kode bayar dompet digital"}
        </p>
        <p className="rdg-pay-code">{group4(code)}</p>
        <CopyButton text={code} label="Salin nomor" />
      </>
    );
  } else if (method.kind === "qris") {
    body = (
      <>
        <div className="mx-auto w-fit rounded-[18px] border border-[color:var(--rdg-line)] p-2">
          <QrPattern value={code} label={`Kode QRIS untuk ${payment.title}`} size={196} />
        </div>
        <p className="mt-2 text-[12px] text-[color:var(--rdg-muted)]">ID transaksi {code}</p>
      </>
    );
  } else {
    const message = decodeURIComponent(code.split("text=")[1] || "");
    body = (
      <>
        <p className="text-[13px] font-semibold text-[color:var(--rdg-muted)]">Pesan siap dikirim</p>
        <p className="mt-1 text-[14px] leading-relaxed text-rdg-ink900">{message}</p>
        <p className="rdg-pay-link">{code}</p>
        <CopyButton text={code} label="Salin tautan" />
        <p className="mt-2 text-[12px] text-[color:var(--rdg-muted)]">Contoh tautan — tidak dibuka atau dikirim otomatis.</p>
      </>
    );
  }
  return (
    <>
      <div className="rdg-pay-code-card">
        {body}
        <p className="mt-3 text-[12.5px] font-semibold text-[#7a4f00]">
          Bayar sebelum {tanggal(payment.expiresAt)}, {jam(payment.expiresAt)} WIB
        </p>
      </div>
      <ol className="rdg-pay-steps" aria-label="Cara bayar">
        {steps(method, payment.amount).map((s) => <li key={s}>{s}</li>)}
      </ol>
    </>
  );
}
