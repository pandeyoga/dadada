import React from "react";
import {
  KeyRound, Video, Cctv, DoorOpen, QrCode, Siren, Phone, ReceiptText, History, Landmark, Wallet,
  Users, Vote, Heart, ShoppingBasket, Wrench, ShieldPlus, FileText, Hammer, CalendarCheck, Zap,
  Bell, CircleUser, Gift,
} from "lucide-react";
import Page from "../../buyer/Page";
import ServiceGrid from "../../../components/ServiceGrid";

const GROUPS = [
  { id: "keamanan", title: "Keamanan", items: [
    { icon: KeyRound, label: "Kunci pintu", to: "/app/warga/keamanan/kunci" },
    { icon: Video, label: "CCTV rumah", to: "/app/warga/keamanan/cctv-rumah" },
    { icon: Cctv, label: "CCTV kawasan", to: "/app/warga/keamanan/kawasan" },
    { icon: DoorOpen, label: "Gerbang", to: "/app/warga/keamanan/gerbang" },
    { icon: QrCode, label: "Tamu", to: "/app/warga/keamanan/tamu" },
    { icon: Siren, label: "SOS", to: "/app/warga/sos" },
    { icon: Phone, label: "Kontak darurat", to: "/app/warga/sos/kontak" },
  ] },
  { id: "uang", title: "Tagihan dan bayar", items: [
    { icon: ReceiptText, label: "Tagihan", to: "/app/warga/tagihan" },
    { icon: History, label: "Riwayat", to: "/app/warga/tagihan/riwayat" },
    { icon: Landmark, label: "Kas kawasan", to: "/app/warga/tagihan/kas" },
    { icon: Wallet, label: "Isi ulang", to: "/app/warga/isi-ulang" },
  ] },
  { id: "komunitas", title: "Komunitas", items: [
    { icon: Users, label: "Komunitas", to: "/app/warga/komunitas" },
    { icon: Vote, label: "Polling", to: "/app/warga/komunitas/polling" },
    { icon: Heart, label: "Hobi", to: "/app/warga/komunitas/hobi" },
    { icon: ShoppingBasket, label: "Pasar warga", to: "/app/warga/pasar" },
    { icon: Wrench, label: "Jasa rumah", to: "/app/warga/jasa" },
  ] },
  { id: "rumah", title: "Rumah dan perawatan", items: [
    { icon: Wrench, label: "Lapor rusak", to: "/app/warga/lapor" },
    { icon: ShieldPlus, label: "Garansi", to: "/app/warga/garansi" },
    { icon: FileText, label: "Dokumen", to: "/app/warga/dokumen" },
    { icon: Hammer, label: "Renovasi", to: "/app/warga/renovasi" },
    { icon: CalendarCheck, label: "Fasilitas", to: "/app/warga/fasilitas" },
    { icon: Zap, label: "Energi", to: "/app/warga/energi" },
  ] },
  { id: "akun", title: "Akun", items: [
    { icon: Bell, label: "Notifikasi", to: "/app/notifikasi" },
    { icon: CircleUser, label: "Akun saya", to: "/app/warga/akun" },
    { icon: Gift, label: "Ajak teman", to: "/app/ajak-teman" },
  ] },
];

/** W20: semua layanan warga, dikelompokkan menurut kebutuhan. */
export default function AllServices() {
  return (
    <Page id="W20" title="Semua layanan" back="/app/warga" nav="resident">
      {GROUPS.map((g) => (
        <section key={g.id} aria-labelledby={`w20-${g.id}`} className="rounded-3xl bg-white/80 p-4 shadow-[var(--rdg-shadow-card)]">
          <h2 id={`w20-${g.id}`} className="mb-3 text-[16px] font-extrabold">{g.title}</h2>
          <ServiceGrid items={g.items} />
        </section>
      ))}
    </Page>
  );
}
