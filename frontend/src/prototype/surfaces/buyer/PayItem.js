import React, { useCallback, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { CircleCheck, Wallet } from "lucide-react";
import MobileShell from "../../components/MobileShell";
import Screen from "../../components/Screen";
import Hero from "../../components/Hero";
import { GlassCard, FrostCard } from "../../components/GlassCard";
import ScreenHeader from "../../components/ScreenHeader";
import StatusChip from "../../components/StatusChip";
import PayFlow from "../../components/PayFlow";
import ReceiptCard from "../../components/pay/ReceiptCard";
import EmptyState from "../../components/EmptyState";
import { listInstallments } from "../../services/api/buyer";
import { rupiah, tanggal } from "../../lib/format";
import useLoad from "../../lib/useLoad";
import { Loading } from "./Page";

export default function PayItem() {
  const { itemId } = useParams();
  const fetcher = useCallback(() => listInstallments(), []);
  const { data, error } = useLoad(fetcher);
  const [open, setOpen] = useState(false);
  const item = data && data.find((i) => i.id === itemId);
  const paid = item && item.status === "paid";
  const pending = item && item.status === "pending";
  return (
    <MobileShell nav="buyer">
      <Screen id="P5">
        <Hero className="pb-10">
          <ScreenHeader title="Bayar uang muka" back="/app/pembeli/bayar" />
          <GlassCard className="mt-1">
            <p className="text-[13.5px] font-semibold text-white/90">{item ? item.label : "Tagihan"}</p>
            <p className="text-[34px] font-extrabold leading-tight tracking-[-0.02em]">{item ? rupiah(item.amount) : "Rp--"}</p>
            {item && (
              <p className="mt-1 text-[13.5px] text-white/90">
                {paid ? `Dibayar ${tanggal(item.paidAt)}` : `Jatuh tempo ${tanggal(item.dueDate)}`} · untuk developer
              </p>
            )}
            {item && (
              <div className="mt-3">
                {paid ? <StatusChip tone="ok">Lunas</StatusChip> : pending ? <StatusChip tone="warn">Menunggu pembayaran</StatusChip> : <StatusChip tone="neutral">Belum dibayar</StatusChip>}
              </div>
            )}
          </GlassCard>
        </Hero>
        <div className="space-y-4 px-5 pt-5">
          {!data && <Loading error={error} />}
          {data && !item && (
            <EmptyState title="Tagihan tidak ditemukan" body="Cicilan ini tidak ada di jadwal Anda.">
              <Link to="/app/pembeli/bayar" className="rdg-btn-primary">Ke jadwal cicilan</Link>
            </EmptyState>
          )}
          {item && !paid && (
            <>
              <FrostCard>
                <h2 className="text-[16px] font-extrabold">Cara bayar</h2>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-[14px] leading-relaxed text-[color:var(--rdg-muted)]">
                  <li>Pilih metode: virtual account bank, QRIS, dompet digital, atau tautan WhatsApp.</li>
                  <li>Bayar sesuai nominal dari aplikasi bank Anda.</li>
                  <li>Ketuk "Saya sudah bayar" untuk melihat kuitansi.</li>
                </ol>
              </FrostCard>
              <button type="button" className="rdg-btn-primary w-full" onClick={() => setOpen(true)}>
                <Wallet size={19} aria-hidden="true" /> {pending ? "Lanjutkan pembayaran" : "Pilih metode bayar"}
              </button>
            </>
          )}
          {paid && (
            <>
              <FrostCard className="flex items-center gap-3">
                <CircleCheck size={28} className="flex-none text-rdg-green" aria-hidden="true" />
                <div>
                  <p className="text-[16px] font-extrabold">Pembayaran lunas</p>
                  <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Terima kasih, cicilan ini sudah tercatat.</p>
                </div>
              </FrostCard>
              {item.receipt && <ReceiptCard receipt={item.receipt} />}
              <Link to="/app/pembeli/bayar" className="rdg-btn-ghost w-full">Kembali ke jadwal</Link>
            </>
          )}
        </div>
        {item && (
          <PayFlow
            open={open}
            onClose={() => setOpen(false)}
            target={{ type: "installment", id: item.id, title: item.label, amount: item.amount }}
            onPaid={() => {}}
          />
        )}
      </Screen>
    </MobileShell>
  );
}
