import React, { useCallback, useState } from "react";
import { ShoppingCart, Plus, Trash2, CircleCheck } from "lucide-react";
import Page, { Loading } from "../../buyer/Page";
import { HeaderButton } from "../../../components/ScreenHeader";
import { FrostCard } from "../../../components/GlassCard";
import Sheet from "../../../components/Sheet";
import PayFlow from "../../../components/PayFlow";
import ReceiptCard from "../../../components/pay/ReceiptCard";
import MarketIllustration from "../../../components/MarketIllustration";
import { Msg } from "../security/ui";
import { listProducts, addToCart, removeFromCart, cartLines, cartTotal, checkout, completeOrder } from "../../../services/api/community";
import { useProto } from "../../../services/useStore";
import { rupiah } from "../../../lib/format";
import useLoad from "../../../lib/useLoad";


/** W18: pasar warga — grid produk, keranjang (Sheet), bayar lewat PayFlow. Simulasi; tanpa pengiriman nyata. */
export default function Market() {
  const fetcher = useCallback(() => listProducts(), []);
  const community = useProto((s) => s.community); // keranjang selalu mengikuti state langsung
  const { data, error } = useLoad(fetcher, ["community"]);
  const [open, setOpen] = useState(false);
  const [problem, setProblem] = useState("");
  const [pay, setPay] = useState(null); // dipertahankan agar kuitansi tetap tampil setelah lunas
  const [receipt, setReceipt] = useState(null);

  const run = async (fn) => {
    setProblem("");
    try { await fn(); } catch (e) { setProblem(e.message); }
  };
  const lines = data ? cartLines({ community }) : [];
  const count = lines.reduce((n, l) => n + l.qty, 0);
  const pending = async () => {
    const t = await checkout();
    setPay({ type: "market", id: t.targetId, title: t.title, amount: t.amount });
    setOpen(false);
  };

  return (
    <Page
      id="W18" title="Pasar warga" back="/app/warga/komunitas" nav="resident"
      right={<HeaderButton variant="light" icon={ShoppingCart} label={`Keranjang (${count})`} onClick={() => { setProblem(""); setOpen(true); }} badge={count > 0} />}
    >
      {!data && <Loading error={error} />}
      {data && (
        <>
          {receipt && (
            <section aria-labelledby="w18-ok" className="space-y-2">
              <h2 id="w18-ok" className="flex items-center gap-2 text-[16px] font-extrabold"><CircleCheck size={20} className="text-rdg-green" aria-hidden="true" /> Pesanan terbayar</h2>
              <ReceiptCard receipt={receipt} />
              <p className="text-[13px] text-[color:var(--rdg-muted)]">Pengambilan atau pengantaran diatur langsung dengan penjual.</p>
            </section>
          )}
          <p className="text-[13.5px] text-[color:var(--rdg-muted)]">Dagangan tetangga di Estora Residence.</p>
          <ul className="grid grid-cols-2 gap-3">
            {data.map((p) => (
              <li key={p.id}>
                <FrostCard className="flex h-full flex-col !p-2">
                  <MarketIllustration img={p.img} label={`Foto ${p.name}`} className="aspect-[16/11] w-full rounded-xl" />
                  <p className="mt-2 text-[14.5px] font-bold leading-snug">{p.name}</p>
                  <p className="text-[12.5px] text-[color:var(--rdg-muted)]">{p.seller}</p>
                  <p className="mt-auto pt-1 text-[15px] font-extrabold">{rupiah(p.price)}</p>
                  <button type="button" className="rdg-btn-ghost mt-2 !min-h-[44px] w-full" aria-label={`Tambah ${p.name}`} onClick={() => run(() => addToCart(p.id))}>
                    <Plus size={16} aria-hidden="true" /> Tambah
                  </button>
                </FrostCard>
              </li>
            ))}
          </ul>
          {!open && <Msg error={problem} />}
          <Sheet open={open} onClose={() => setOpen(false)} title="Keranjang">
            {lines.length === 0 && <p className="text-[14.5px] text-[color:var(--rdg-muted)]">Keranjang masih kosong. Tambah dagangan tetangga dari daftar.</p>}
            <ul className="divide-y divide-[color:var(--rdg-line)]">
              {lines.map((l) => (
                <li key={l.productId} className="flex items-center gap-3 py-2">
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14.5px] font-bold">{l.product.name}</span>
                    <span className="block text-[13px] text-[color:var(--rdg-muted)]">{`${l.qty} × ${rupiah(l.product.price)}`}</span>
                  </span>
                  <span className="text-[14.5px] font-extrabold">{rupiah(l.qty * l.product.price)}</span>
                  <button type="button" className="rdg-icon-btn rdg-icon-btn--light" aria-label={`Hapus ${l.product.name}`} onClick={() => run(() => removeFromCart(l.productId))}>
                    <Trash2 size={18} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-3 flex justify-between text-[16px] font-extrabold"><span>Total</span><span data-testid="cart-total">{rupiah(cartTotal({ community }))}</span></p>
            <Msg error={open ? problem : ""} />
            <button type="button" className="rdg-btn-primary mt-3 w-full" onClick={() => run(pending)}>Bayar sekarang</button>
          </Sheet>
        </>
      )}
      {pay && (
        <PayFlow
          open
          onClose={() => setPay(null)}
          target={pay}
          onPaid={async ({ receipt: r }) => { setReceipt(r); await completeOrder(pay.id); }}
        />
      )}
    </Page>
  );
}
