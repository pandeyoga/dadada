# Prototipe Aplikasi Penghuni "Rumah Dalam Genggaman" — Rencana Implementasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Membangun 60 layar prototipe frontend (data contoh, tanpa backend) untuk aplikasi penghuni Estora "Rumah Dalam Genggaman" — mode Pembeli → transisi BAST → mode Warga, plus aplikasi satpam, dasbor pengelola, dan portal mitra — di dalam frontend React Estora yang ada.

**Architecture:** Satu modul baru `frontend/src/prototype/` dimuat *lazy* di rute `/app/*` (di luar `RequireAuth`), dijaga oleh pemeriksaan hostname saat runtime. Semua data lewat satu store kecil (state + `localStorage` + sinkron antartab) dan fungsi layanan per domain yang meniru API masa depan; layar tidak pernah membaca fixture langsung. Gaya glassmorphism di-scope di bawah kelas akar `.rdg`.

**Tech Stack:** React 19, react-router-dom 7, Tailwind 3 (+ namespace warna `rdg`), lucide-react, framer-motion (opsional), Jest + @testing-library/react (via `craco test`), Playwright (skrip tangkapan layar), `@fontsource/plus-jakarta-sans`.

**Spec:** `docs/superpowers/specs/2026-11-25-aplikasi-penghuni-prototype-design.md` (baca bagian 6, 7, 8, 9, 14). Aset: `docs/superpowers/specs/assets/` (mockup v1, peta navigasi, `brand/`).

## Global Constraints

- Semua teks UI berbahasa Indonesia untuk pembeli rumah subsidi; tidak ada nama/merek "Rumah Ningrat" atau nama fitur mereka (mis. jangan "Ningrat Pay"; pakai "Bayar & Isi Ulang").
- Batas gerbang `scripts/validate_compliance.py`: file `.js` ≤ **500** baris; file di jalur yang mengandung `/services/` atau `/utils/` ≤ **300** baris; `.css` ≤ **400** baris; tidak ada string `localhost:3000` / `localhost:80xx` di `frontend/src`.
- Aplikasi admin tidak boleh berubah tampilan/perilaku: tidak mengubah `:root`, `body`, `index.css`, komponen `components/portal/*`, atau rute lain di `App.js`. Semua CSS prototipe berawalan `.rdg`.
- Prototipe tidak memanggil jaringan (tanpa `axios`, tanpa URL gambar eksternal). Gambar = SVG/ilustrasi lokal atau PNG di `public/rdg/`.
- Token warna (spek §6): `leaf #49AE42`, `green #209F59`, `tealgreen #01916F`, `teal #007F83`, `deep #006284`, `ink #00454D`, `ink900 #00353B`, `forest #006747`, `mint #E7FFEF`, `lime #B5E26B`, `sos #E5484D`. Huruf: Plus Jakarta Sans (400–800). Ikon: lucide-react.
- Kaidah glass (spek §6): blur 14–18 px hanya di kartu hero gelap, menu bawah, tombol header; maks ±4 permukaan blur per layar; kartu konten putih 75–85 %; kontras teks ≥ 4,5:1; cadangan solid via `@supports not (backdrop-filter: blur(1px))` dan `@media (prefers-reduced-transparency: reduce)`.
- Interaksi keamanan: status kunci = warna + ikon + kata; buka kunci = **geser**; SOS = **tahan 3000 ms** (lepas sebelum itu = batal); notifikasi berjenjang `darurat › keamanan › info`.
- Data dunia (spek §9, §14): proyek **"Estora Residence"**; warga **Rina Ayu**, Blok **C-12**, tipe **36/72**, rumah subsidi FLPP **Rp166.000.000**; uang muka **Rp5.000.000 dalam 5 × Rp1.000.000** dibayar ke developer; KPR "KPR Subsidi · Bank BTN" pokok Rp161.000.000, 5 %/tahun, 20 tahun → angsuran **Rp1.062.500/bulan** "dibayar ke bank setelah akad"; IPL **Rp150.000/bulan**; ±20 unit tetangga; 3 satpam; 6 kamera kawasan; 2 kamera rumah. Perjalanan: `Booking → Cek kredit → Bangun → Pengajuan KPR → Akad → Serah terima`, posisi awal **Bangun 72 %**.
- Kunci pintu terkunci otomatis **30 000 ms** setelah dibuka.
- Host yang diizinkan (spek §14.2): `localhost`, `127.0.0.1`, `""` (jsdom), dan hostname berawalan `demo.` atau `trial.`; selain itu `/app/*` → `Navigate` ke `/`.
- Label "Data contoh" hanya di peluncur demo dan layar Akun (bukan setiap layar).
- Nama bank tampil hanya sebagai data; dilarang teks "terintegrasi dengan BTN/Bank …".

## Review Focus

1. **HP sempit 360 px dan teks panjang** (nama, nominal Rp, alamat) → tidak ada gulir horizontal atau teks terpotong. Dipasang di Task 14 (skrip tangkapan layar mengukur `scrollWidth` di 360 px dan 390 px).
2. **`localStorage` tak tersedia atau berisi JSON rusak** (mode privat, data lama) → store memakai state awal di memori, tidak crash. Uji di Task 2.
3. **State tersimpan dari versi lama** (kunci versi berbeda) → diabaikan dan diganti state awal. Uji di Task 2.
4. **Dibuka di hostname produksi** (mis. `hl5.estora.id`) → `/app/*` dialihkan ke `/`, aplikasi admin/portal tidak tersentuh. Uji di Task 1.
5. **Aksi diulang** (bayar item yang sudah lunas, QR tamu dipindai dua kali, SOS saat masih ada SOS aktif, tekan bayar dua kali) → idempoten dengan pesan jelas, tidak membuat data ganda. Uji di Task 5, 7, 8, 9.

---

## Struktur file

```
frontend/src/prototype/
  PrototypeApp.js            # akar .rdg, host guard, rute /app/*, manifest swap, window.__rdgDemo
  screens.json               # daftar 60 layar: {id, path, title, surface, tier}
  lib/host.js                # isPrototypeHost()
  lib/format.js              # rupiah(), tanggal(), jam() — pembungkus utils/formatters
  theme/rdg.css              # token, glass/frost/hero, fallback, kelas komponen
  services/                  # ≤300 baris per file
    store.js  useStore.js  latency.js
    fixtures/world.js buyer.js resident.js community.js ops.js partner.js
    initialState.js
    api/session.js buyer.js security.js bills.js community.js care.js manager.js partner.js
  components/                # primitif UI bersama
    MobileShell.js DesktopShell.js Hero.js GlassCard.js ScreenHeader.js BottomNav.js
    ServiceGrid.js ListRow.js StatusChip.js Stepper.js HoldToConfirm.js SlideToConfirm.js
    CameraView.js Sheet.js PayFlow.js BrandMark.js EmptyState.js Screen.js
  surfaces/demo/   Launcher.js Login.js
  surfaces/buyer/  (P1–P11)      surfaces/transition/Welcome.js (T1)
  surfaces/resident/ (W1–W29)    surfaces/satpam/ (S1–S5)
  surfaces/manager/ (K1–K7)      surfaces/partner/ (M1–M5)
  __tests__/*.test.js
frontend/public/rdg/  manifest.json  icon-192.png  icon-512.png  logo-full.png  mark.png
frontend/scripts/prototype-screens.js     # Playwright: semua rute → PNG + cek overflow
docs/prototype/screens/                   # hasil PNG (di-commit)
```

**Modifikasi file yang ada (hanya ini):** `frontend/src/App.js` (satu import lazy + satu `<Route path="/app/*">`), `frontend/tailwind.config.js` (tambah `colors.rdg.*` dan `fontFamily.rdg`), `frontend/package.json` (dependensi `@fontsource/plus-jakarta-sans`).

## Antarmuka bersama (dirujuk semua task)

**Store (`services/store.js`)**
- `STORAGE_KEY = "rdg_proto_state"`, `STATE_VERSION = 1`
- `getState(): ProtoState`, `setState(updater: (s: ProtoState) => ProtoState): void`, `subscribe(fn: () => void): () => void`
- `resetState(): void` (state awal baru + simpan + beri tahu pelanggan)
- `__initStoreForTest({ storage?: Storage|null, now?: () => number }): void`
- Sinkron antartab: listener `window` `"storage"` untuk `STORAGE_KEY` → muat ulang dan beri tahu.
- `now(): number` (bisa diganti di tes).

**Hook (`services/useStore.js`)**: `useProto(selector: (s) => T): T` (via `useSyncExternalStore`), `useNow(intervalMs = 1000): number`.

**Latensi (`services/latency.js`)**: `wait(): Promise<void>` (200–600 ms acak), `setLatency(ms: number | null)` (tes memakai `0`).

**ProtoState (kunci tingkat atas):** `version, session {persona: 'buyer'|'resident'|'satpam'|'pengelola'|'mitra', loggedIn: bool, phone: string}, mode: 'buyer'|'resident', onboarding {done: bool}, location: 'inside'|'outside', world, buyer, security, bills, community, care, manager, partner, notifications: Notification[]`.

**Entitas yang dipakai lintas task**
- `Installment {id, label, amount, dueDate, status: 'unpaid'|'pending'|'paid', paidAt?, receiptId?}`
- `Bill {id, kind: 'ipl'|'air', period, amount, dueDate, status: 'unpaid'|'pending'|'paid', paidAt?, receiptId?}`
- `Payment {id, targetType: 'installment'|'bill'|'ppob'|'market', targetId, method, amount, code, expiresAt, status: 'pending'|'paid'}` — `method ∈ ['va_bri','va_bni','va_mandiri','va_btn','va_permata','qris','ewallet','wa_link']`
- `Receipt {id, targetType, targetId, title, amount, method, paidAt}` — **semua** kuitansi disimpan di satu daftar `bills.receipts` (P8 dan W11 memfilter per `targetType`).
- `SosEvent {id, type: 'kemalingan'|'kebakaran'|'medis'|'lainnya', unit: 'C-12', status: 'sent'|'accepted'|'resolved'|'cancelled', createdAt, acceptedBy?, acceptedAt?, resolvedAt?}`
- `GuestPass {id, code (6 huruf/angka kapital), guestName, date, from 'HH:mm', to 'HH:mm', status: 'active'|'used'|'expired'|'revoked', usedAt?}`
- `AccessCode {id, label, pin (4 digit), validUntil, revoked: bool}`
- `Ticket {id, kind: 'rusak'|'tanya'|'garansi', category, description, photos: string[], status: 'dibuat'|'diverifikasi'|'dikerjakan'|'selesai'|'dikonfirmasi', assignee?, rating?, history: {status, at, note}[]}`
- `Notification {id, tier: 'darurat'|'keamanan'|'info', title, body, at, read: bool, link?}`

**Primitif UI (`components/`)** — dipakai semua layar:
- `MobileShell({ children, nav?: 'buyer'|'resident'|'satpam'|'partner'|null })` kolom tengah maks 430 px, latar halaman gradasi di layar lebar.
- `DesktopShell({ children, active })` sidebar pengelola.
- `Screen({ id, children })` → membungkus layar dengan `data-screen={id}`; **setiap layar wajib memakai ini** (dipakai uji rute).
- `Hero({ height, children })`, `GlassCard`, `FrostCard` (ekspor dari `GlassCard.js`), `ScreenHeader({ title, back?, right? })`, `BottomNav({ variant })`, `ServiceGrid({ items: {icon, label, to}[] })`, `ListRow({ icon, title, subtitle, right?, to?, onClick? })`, `StatusChip({ tone: 'ok'|'warn'|'danger'|'info'|'neutral', children })`, `Stepper({ steps: string[], current: number, progress?: number })`
- `HoldToConfirm({ durationMs = 3000, onConfirm, label })` — tekan-tahan (pointer) dan tombol keyboard (tahan Space/Enter) ; lepas sebelum `durationMs` = batal.
- `SlideToConfirm({ onConfirm, label })` — konfirmasi bila digeser ≥ 90 %; alternatif keyboard: fokus + Enter.
- `CameraView({ cameraId, label, live = true })` — ilustrasi SVG + label LIVE + jam berjalan.
- `Sheet({ open, onClose, title, children })` — bottom sheet **tanpa portal** (dirender di dalam `.rdg`).
- `PayFlow({ open, onClose, target: {type, id, title, amount}, onPaid })` — pilih metode → kode VA/QRIS/tautan WA → "Saya sudah bayar" → lunas + kuitansi.
- `BrandMark({ variant: 'light'|'dark', withText = true })` — ikon Estora + teks "Rumah Dalam Genggaman".
- `EmptyState({ icon, title, body })`.

---

### Task 1: Fondasi — rute lazy, penjaga host, tema, daftar layar, uji semua rute

**Files:**
- Create: `frontend/src/prototype/PrototypeApp.js`, `prototype/lib/host.js`, `prototype/lib/format.js`, `prototype/theme/rdg.css`, `prototype/screens.json`, `prototype/components/Screen.js`, `prototype/components/MobileShell.js`, `prototype/surfaces/demo/Launcher.js` (sementara: daftar tautan semua layar), `prototype/surfaces/Placeholder.js`
- Create: `frontend/public/rdg/` (salin dari `docs/superpowers/specs/assets/brand/`: `estora_logo_full.png → logo-full.png`, `estora_mark.png → mark.png`, `rdg-icon-192.png → icon-192.png`, `rdg-icon-512.png → icon-512.png`)
- Modify: `frontend/src/App.js` (import lazy + `<Route path="/app/*">` di sebelah `/portal/*`), `frontend/tailwind.config.js`, `frontend/package.json`
- Test: `frontend/src/prototype/__tests__/host.test.js`, `__tests__/routes.test.js`

**Interfaces:**
- Produces: `isPrototypeHost(hostname: string): boolean`; `screens.json` berisi **59 rute untuk 60 entri inventaris** (P10 dan W29 berbagi `/app/ajak-teman`) dengan bentuk `{id: 'W8', path: '/app/warga/sos', title: 'SOS', surface: 'resident'|'buyer'|'demo'|'transition'|'satpam'|'manager'|'partner', tier: 'D'|'L'}`; `Screen`; `MobileShell`; `<PrototypeApp/>` mendaftarkan setiap path di `screens.json` (sementara ke `Placeholder` yang merender `<Screen id>` + judul); `rupiah(n: number): string` ("Rp166.000.000").
- Path (lihat spek §7.3 untuk isi): U1 `/app/demo`, U2 `/app/masuk`; P1 `/app/pembeli`, P2 `/app/pembeli/progres`, P3 `/app/pembeli/kavling`, P4 `/app/pembeli/bayar`, P5 `/app/pembeli/bayar/dp-3`, P6 `/app/pembeli/kpr`, P7 `/app/pembeli/pembatalan`, P8 `/app/pembeli/dokumen`, P9 `/app/pembeli/akun`, P10 `/app/ajak-teman`, P11 `/app/pembeli/promo/promo-1`; T1 `/app/selamat-datang`; W1 `/app/warga`, W2 `/app/warga/keamanan`, W3 `/app/warga/keamanan/kunci`, W4 `/app/warga/keamanan/cctv-rumah`, W5 `/app/warga/keamanan/kawasan`, W6 `/app/warga/keamanan/gerbang`, W7 `/app/warga/keamanan/tamu`, W8 `/app/warga/sos`, W9 `/app/warga/sos/kontak`, W10 `/app/warga/tagihan`, W11 `/app/warga/tagihan/riwayat`, W12 `/app/warga/tagihan/kas`, W13 `/app/warga/isi-ulang`, W14 `/app/warga/komunitas`, W15 `/app/warga/komunitas/event/ev-1`, W16 `/app/warga/komunitas/hobi`, W17 `/app/warga/komunitas/polling`, W18 `/app/warga/pasar`, W19 `/app/warga/jasa`, W20 `/app/warga/layanan`, W21 `/app/warga/lapor`, W22 `/app/warga/garansi`, W23 `/app/warga/dokumen`, W24 `/app/warga/renovasi`, W25 `/app/warga/fasilitas`, W26 `/app/warga/energi`, W27 `/app/notifikasi`, W28 `/app/warga/akun`, W29 `/app/ajak-teman`; S1 `/app/satpam`, S2 `/app/satpam/sos`, S3 `/app/satpam/tamu`, S4 `/app/satpam/cctv`, S5 `/app/satpam/patroli`; K1 `/app/pengelola`, K2 `/app/pengelola/ipl`, K3 `/app/pengelola/tiket`, K4 `/app/pengelola/pengumuman`, K5 `/app/pengelola/kas`, K6 `/app/pengelola/keamanan`, K7 `/app/pengelola/mitra`; M1 `/app/mitra/daftar`, M2 `/app/mitra`, M3 `/app/mitra/katalog`, M4 `/app/mitra/rujukan`, M5 `/app/mitra/komisi`. Rute dinamis tambahan: `/app/pembeli/bayar/:itemId`, `/app/pembeli/promo/:id`, `/app/warga/komunitas/event/:id`. `/app` (indeks) → arahkan menurut `session.persona` (Task 4); sementara → `/app/demo`.

- [ ] **Step 1: Pasang font.** `cd frontend && yarn add @fontsource/plus-jakarta-sans@5.3.0` → `package.json` berubah; jangan commit `yarn.lock` bila repo tidak memilikinya.
- [ ] **Step 2: Tulis uji gagal `host.test.js`**

```js
import { isPrototypeHost } from "@/prototype/lib/host";
test.each(["localhost", "127.0.0.1", "", "demo.estora.id", "trial.estora.id"])("%s diizinkan", (h) => expect(isPrototypeHost(h)).toBe(true));
test.each(["hl5.estora.id", "estora.id", "app.demo-estora.com", "evil-demo.estora.id"])("%s ditolak", (h) => expect(isPrototypeHost(h)).toBe(false));
```

- [ ] **Step 3: Tulis uji gagal `routes.test.js`** — untuk setiap entri `screens.json`, render `<MemoryRouter initialEntries={[path]}><Routes><Route path="/app/*" element={<PrototypeApp/>}/></Routes></MemoryRouter>` lalu `await waitFor(() => expect(document.querySelector(`[data-screen="${id}"]`)).not.toBeNull(), { timeout: 3000 })`. Tambah satu uji: `expect(new Set(screens.map(s=>s.path)).size).toBe(59)` dan `expect(ids.length).toBe(59)` serta setiap id inventaris (U1–U2, P1–P11, T1, W1–W28, S1–S5, K1–K7, M1–M5) muncul (W29 dicatat sebagai `aliasOf: 'P10'` di entri P10 → `extraIds: ['W29']`). Satu uji lagi: dengan `window.location.hostname` = `hl5.estora.id` (gunakan prop `hostname` uji pada `PrototypeApp`), render `/app/warga` → yang tampil adalah elemen `Navigate` ke `/` (assert `[data-screen]` tidak ada).
- [ ] **Step 4: Jalankan, pastikan gagal.** `cd frontend && CI=true yarn test --watchAll=false src/prototype` → FAIL (modul tidak ada).
- [ ] **Step 5: Implementasi.** `isPrototypeHost`: izinkan persis `localhost`/`127.0.0.1`/`""` atau label pertama `demo`/`trial` (`/^(demo|trial)\./`). `PrototypeApp({ hostname = window.location.hostname })`: bila tidak diizinkan → `<Navigate to="/" replace/>`; akar `<div className="rdg font-rdg">`; impor `@fontsource/plus-jakarta-sans/{400,500,600,700,800}.css` dan `./theme/rdg.css` di file ini saja. `App.js`: `const PrototypeApp = React.lazy(() => import("@/prototype/PrototypeApp"))` dan `<Route path="/app/*" element={<React.Suspense fallback={null}><PrototypeApp/></React.Suspense>} />`. `tailwind.config.js`: tambahkan `fontFamily.rdg = ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'sans-serif']` dan `colors.rdg = { leaf, green, tealgreen, teal, deep, ink, ink900, forest, mint, lime, sos }` (nilai dari Global Constraints). `rdg.css`: variabel `--rdg-*` di `.rdg`, kelas `.rdg-glass`, `.rdg-frost`, `.rdg-hero`, `.rdg-btn-primary` (gradasi `leaf → tealgreen → teal`), `.rdg-btn-sos`, fallback `@supports not (backdrop-filter: blur(1px))` dan `prefers-reduced-transparency` (latar solid `ink` 92 % untuk glass, putih 96 % untuk frost). Rujuk mockup v1 untuk radius/ukuran.
- [ ] **Step 6: Jalankan uji → PASS**, lalu `CI=true yarn build` sukses dan `python3 ../scripts/validate_compliance.py` → `COMPLIANCE PASSED`, `python3 ../scripts/check_nav_map.py` → `NAV MAP PASSED`.
- [ ] **Step 7: Commit** `feat(prototype): fondasi rute /app, penjaga host, tema rdg, daftar layar`.

### Task 2: Store, latensi, fixture, state awal

**Files:**
- Create: `prototype/services/store.js`, `useStore.js`, `latency.js`, `initialState.js`, `fixtures/world.js`, `fixtures/buyer.js`, `fixtures/resident.js`, `fixtures/community.js`, `fixtures/ops.js`, `fixtures/partner.js`
- Test: `prototype/__tests__/store.test.js`

**Interfaces:**
- Produces: API store & hook di "Antarmuka bersama"; `buildInitialState(now: number): ProtoState` dengan nilai Global Constraints; isi fixture: `world {project: {name: 'Estora Residence', city: 'Kab. Bekasi'}, unit: {block: 'C-12', type: '36/72', price: 166000000, scheme: 'KPR Subsidi FLPP', bank: 'Bank BTN'}, resident: {name: 'Rina Ayu', phone: '0812-3456-7890'}, neighbors: 20 unit, guards: 3 nama + shift}`; `buyer {journey: {steps: [6 tahap], current: 2, progress: 72}, installments: 5 × DP Rp1.000.000 (2 lunas, `dp-3` belum, jatuh tempo 10 Des 2026) + booking Rp500.000 lunas, progressPhotos: ≥6 tahap {stage, date, caption, img}, kpr {status: 'menunggu rumah siap', principal: 161000000, rate: 5, tenorYears: 20, monthly: 1062500}, documents ≥5, promos ≥2, cancellation: null, referral {code: 'RINA-C12', invited: []}}`; `security {door: {state:'locked', changedAt}, cameras: {home: 2, area: 6}, accessCodes: 1 contoh (Bu Siti · ART), guestPasses: [], doorLog ≥3, gateLog ≥3, sos: [], contacts: 3}`; `bills {ipl: Desember 2026 Rp150.000 unpaid + 3 bulan lalu paid, payments: [], receipts: [], ppobTx: [], cashReport: 6 bulan {in, out, items}, ppobCatalog}`; `community {announcements ≥3, events ≥3 (id ev-1 "Kerja bakti Minggu, 7 Des"), groups ≥4, polls ≥2, market ≥8 produk, services ≥6, facilities ≥3, cart: [], orders: []}`; `care {tickets ≥2, warranty items ≥5 bagian rumah, renovations: [], bookings: [], family: 2, devices: 4 (kunci pintu, 2 kamera, hub)}`; `manager {units: 20 dengan status IPL, tickets (pakai care), announcements}`; `partner {registered: false, profile, points: 1250, commissions[], referrals ≥4 dengan tahap lead→booking→akad, catalog (unit tersedia ≥6)}`; `notifications ≥5` (minimal satu per tier).

- [ ] **Step 1: Tulis uji gagal `store.test.js`** dengan kasus:
  - `buildInitialState` memuat `world.unit.price === 166000000`, `buyer.installments.filter(i=>i.amount===1000000).length === 5`, `buyer.kpr.monthly === 1062500`, `bills.ipl[0].amount === 150000`, `buyer.journey.progress === 72`.
  - `setState` memicu pelanggan dan menyimpan JSON ke storage di `STORAGE_KEY`.
  - Inisialisasi dengan storage berisi `"{rusak"` → `getState().version === 1` (tidak melempar).
  - Inisialisasi dengan storage `{version: 0, …}` → diganti state awal.
  - `__initStoreForTest({storage: null})` (storage tak tersedia) → setState tetap berjalan di memori.
  - Event `storage` dengan `key === STORAGE_KEY` dan `newValue` berisi state lain → `getState()` ikut berubah dan pelanggan dipanggil.
  - `resetState()` mengembalikan `bills.ipl[0].status === 'unpaid'` setelah diubah.
- [ ] **Step 2: Jalankan → FAIL.** `CI=true yarn test --watchAll=false src/prototype/__tests__/store.test.js`
- [ ] **Step 3: Implementasi** store (try/catch di setiap akses storage; versi beda → state awal), `useProto` via `useSyncExternalStore(subscribe, () => selector(getState()))`, `useNow` (setInterval), `wait`/`setLatency`, `buildInitialState(now)` yang menyusun fixture (tanggal relatif terhadap `now` agar demo selalu "hari ini"). Pecah fixture sehingga tiap file ≤ 300 baris.
- [ ] **Step 4: Jalankan → PASS.**
- [ ] **Step 5: Commit** `feat(prototype): store state+persistensi+sinkron antartab dan data contoh`.

### Task 3: Primitif UI

**Files:**
- Create: semua file di `prototype/components/` yang tercantum di "Antarmuka bersama" (kecuali `Screen.js`, `MobileShell.js` dari Task 1 — perluas `MobileShell` dengan prop `nav`)
- Modify: `prototype/theme/rdg.css` (kelas komponen; tetap ≤ 400 baris — pecah ke `theme/rdg-components.css` bila perlu)
- Test: `prototype/__tests__/components.test.js`

**Interfaces:**
- Consumes: store/hook Task 2 (`PayFlow` memakai `api/buyer.startPayment`/`confirmPayment` — **buat di task ini** sebagai antarmuka generik `services/api/payments.js`: `startPayment({targetType, targetId, amount, title}, method): Promise<Payment>`, `confirmPayment(paymentId): Promise<{payment, receipt}>`; `confirmPayment` memanggil penanda lunas sesuai `targetType` (installment → `buyer.installments`, bill → `bills.ipl`, ppob → `bills.ppobTx`, market → `community.orders`).
- Produces: semua primitif; `BottomNav` varian:
  - `buyer`: Beranda `/app/pembeli`, Progres `/app/pembeli/progres`, Bayar `/app/pembeli/bayar`, Dokumen `/app/pembeli/dokumen`, Akun `/app/pembeli/akun`.
  - `resident`: Beranda `/app/warga`, Keamanan `/app/warga/keamanan`, **SOS** (tengah, bulat merah menonjol) `/app/warga/sos`, Tagihan `/app/warga/tagihan`, Komunitas `/app/warga/komunitas`.
  - `satpam`: Pos `/app/satpam`, Tamu `/app/satpam/tamu`, CCTV `/app/satpam/cctv`, Patroli `/app/satpam/patroli`.
  - `partner`: Beranda `/app/mitra`, Katalog `/app/mitra/katalog`, Rujukan `/app/mitra/rujukan`, Komisi `/app/mitra/komisi`.

- [ ] **Step 1: Tulis uji gagal `components.test.js`** (fake timers):
  - `HoldToConfirm`: `pointerDown` lalu maju 2999 ms → `onConfirm` belum; maju 1 ms → dipanggil sekali. `pointerDown`, maju 2000 ms, `pointerUp`, maju 2000 ms → tidak dipanggil. Tahan tombol Space 3000 ms → dipanggil.
  - `SlideToConfirm`: fokus + Enter → `onConfirm` dipanggil.
  - `PayFlow` (latency 0): pilih "VA BRI" → tampil kode VA 16 digit berawalan `8`; klik "Saya sudah bayar" → `onPaid` dipanggil dengan `receipt.amount === amount`; klik dua kali cepat tidak membuat dua kuitansi (`getState().bills.receipts.length` bertambah tepat 1).
  - `BottomNav variant="resident"` merender 5 tautan dengan label persis di atas, item SOS memiliki `aria-label="SOS darurat"`.
- [ ] **Step 2: Jalankan → FAIL.**
- [ ] **Step 3: Implementasi** primitif. Kode VA: awalan per bank (`8800` BRI, `8277` BNI, `8908` Mandiri, `9001` BTN, `8528` Permata) + 12 digit acak; QRIS = SVG pola acak lokal; `wa_link` = teks tautan `https://wa.me/?text=...` yang hanya ditampilkan (tidak dibuka). `Sheet` tanpa portal, `role="dialog"`, `aria-modal`, tutup dengan Esc/klik latar. `CameraView` ilustrasi SVG (rumah/pagar/jalan berbeda per `cameraId`), label `LIVE`, jam `useNow`.
- [ ] **Step 4: Jalankan → PASS.**
- [ ] **Step 5: Commit** `feat(prototype): primitif UI glass, tahan/geser untuk konfirmasi, alur bayar`.

### Task 4: Peluncur demo (U1) dan masuk OTP (U2)

**Files:**
- Create: `prototype/services/api/session.js`, `prototype/surfaces/demo/Launcher.js` (ganti versi sementara), `prototype/surfaces/demo/Login.js`
- Modify: `prototype/PrototypeApp.js` (indeks `/app` mengarah menurut persona; pasang `window.__rdgDemo` bila host diizinkan)
- Test: `prototype/__tests__/session.test.js`

**Interfaces:**
- Produces: `requestOtp(phone: string): Promise<{sentTo: string}>` (tolak bila < 10 digit: `Error('Nomor WhatsApp belum lengkap')`); `verifyOtp(code: string): Promise<void>` (kode 6 digit apa pun diterima; selain itu `Error('Kode harus 6 angka')`); `setPersona(p)` (untuk `'resident'`: `mode = 'resident'` dan `onboarding.done = true`; untuk `'buyer'`: `mode = 'buyer'`); `logout()`; `simulateBast(): void` (`mode = 'resident'`, `onboarding.done = false`, `buyer.journey.current = 5`, `progress = 100`, tambah notifikasi info "Selamat, rumah Anda resmi diserahterimakan"); `setLocation('inside'|'outside')`; `homePathFor(state): string` (buyer→`/app/pembeli`, resident→ `onboarding.done ? '/app/warga' : '/app/selamat-datang'`, satpam→`/app/satpam`, pengelola→`/app/pengelola`, mitra→`/app/mitra`, belum masuk→`/app/demo`).
- `window.__rdgDemo = { reset, setPersona, simulateBast, setLocation }` dipasang di `PrototypeApp` (Task 7 menambahkan `sendSos` dan `createGuestPass` ke objek yang sama).
- Launcher: logo `BrandMark`, label **"Data contoh"**, kartu persona (Rina · Pembeli, Rina · Warga, Pak Joko · Satpam, Pengelola kawasan, Dimas · Mitra), tombol **Simulasikan BAST**, sakelar **Lokasi: di dalam / di luar kawasan**, **Reset data contoh**, dan daftar semua layar dari `screens.json` dikelompokkan per `surface` (untuk juri). Login: input nomor WA → OTP 6 kotak (pakai `components/ui/input-otp` bila cocok di dalam `.rdg`, kalau tidak buat sendiri) → masuk.

- [ ] **Step 1: Uji gagal** untuk `requestOtp('0812')` menolak, `verifyOtp('123456')` → `session.loggedIn === true`, `simulateBast()` → `homePathFor(getState()) === '/app/selamat-datang'`, `setPersona('resident')` → `'/app/warga'`, `setPersona('satpam')` → `'/app/satpam'`.
- [ ] **Step 2: Jalankan → FAIL.**  **Step 3: Implementasi.**  **Step 4: Jalankan → PASS** (termasuk `routes.test.js`).
- [ ] **Step 5: Commit** `feat(prototype): peluncur demo dan masuk OTP simulasi`.

### Task 5: Mode Pembeli (P1–P11)

**Files:**
- Create: `prototype/services/api/buyer.js`; `prototype/surfaces/buyer/` `BuyerHome.js` (P1), `Progress.js` (P2), `PlotMap.js` (P3), `Payments.js` (P4), `PayItem.js` (P5), `Kpr.js` (P6), `Cancellation.js` (P7), `Documents.js` (P8), `BuyerAccount.js` (P9), `Referral.js` (P10/W29), `Promo.js` (P11)
- Modify: `PrototypeApp.js` (ganti Placeholder untuk rute ini)
- Test: `prototype/__tests__/buyer.test.js`

**Interfaces:**
- Consumes: `payments.startPayment/confirmPayment`, primitif Task 3.
- Produces: `getBuyerHome(): Promise<{journey, nextInstallment, progress, latestPhoto, promos}>`; `listInstallments()`, `getProgress()`, `getPlotMap()` (≥20 kavling dengan status `tersedia|dipesan|terjual|milik-anda`), `getKpr()`, `getCancellation()` (selalu `{status: 'none'}` + penjelasan aturan), `listDocuments()`, `getReferral()`, `inviteFriend({name, phone}): Promise<Referral>`.
- Isi layar (ikuti spek §7.3 & §8): P1 `Hero` + kartu perjalanan `Stepper` 6 tahap (posisi "Bangun 72 %"), kartu "Tagihan berikutnya: Cicilan DP ke-3 Rp1.000.000 · jatuh tempo 10 Des" dengan tombol Bayar → `/app/pembeli/bayar/dp-3`, kartu progres dengan foto terbaru, promo; P5 memakai `PayFlow` untuk `targetType: 'installment'`; setelah lunas tampil status "Lunas" + kuitansi dan `nextInstallment` berpindah ke `dp-4`. P6: status "Menunggu rumah siap", simulasi angsuran Rp1.062.500/bulan × 20 tahun "dibayar ke bank setelah akad", tanpa klaim integrasi.

- [ ] **Step 1: Uji gagal:** bayar `dp-3` lewat `startPayment`+`confirmPayment` → status `paid`, `getBuyerHome().nextInstallment.id === 'dp-4'`; memanggil `startPayment` untuk `dp-3` yang sudah lunas → melempar `Error('Tagihan ini sudah lunas')`; `getKpr().monthly === 1062500`; `inviteFriend` dengan nomor kosong → `Error`.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi API + 11 layar** (P1, P2, P4, P5 tingkat D: rapi sesuai mockup; lainnya tingkat L).  **Step 4: PASS** (`buyer.test.js` + `routes.test.js`).
- [ ] **Step 5: Commit** `feat(prototype): mode pembeli — perjalanan rumah, progres, bayar DP via VA`.

### Task 6: Transisi BAST (T1) dan Beranda warga (W1)

**Files:**
- Create: `prototype/surfaces/transition/Welcome.js`, `prototype/surfaces/resident/ResidentHome.js`, `prototype/services/api/resident.js`
- Test: `prototype/__tests__/resident.test.js`

**Interfaces:**
- Consumes: `security` (status pintu dari Task 7 — gunakan fungsi `doorStatus(state, now)`; **definisikan di task ini** di `services/api/security.js` sebagai fungsi murni agar Task 7 menambah fungsi lain di file yang sama).
- Produces: `doorStatus(state, now): 'locked'|'unlocked'` (terbuka bila `door.state==='unlocked'` dan `now - changedAt < 30000`); `completeOnboarding({connectDevices: bool, invites: {name, phone}[], contacts: {name, phone}[]}): Promise<void>` → `onboarding.done = true`, tambah anggota keluarga/kontak; `getResidentHome(): Promise<{homeStatus: {door, cameras: 'aktif', guardsOnDuty: number, safe: bool}, iplDue: Bill|null, announcement, energy: {kwh, deltaPct}}>`.
- T1: 4 langkah (Selamat datang → Hubungkan kunci & kamera (animasi "terhubung") → Undang keluarga → Kontak darurat) → selesai ke `/app/warga`. W1 mengikuti mockup v1 (header salam + lonceng, kartu glass "Rumah aman" dengan 3 status, kartu IPL dengan Bayar, grid layanan 8 + "Semua", pengumuman, kartu energi kecil) dengan `BottomNav variant="resident"` dan foto profil di header → `/app/warga/akun`.

- [ ] **Step 1: Uji gagal:** `doorStatus` terbuka pada `changedAt = now-29999` dan terkunci pada `now-30000`; `completeOnboarding` → `onboarding.done === true` dan `homePathFor` → `/app/warga`; `getResidentHome().iplDue.amount === 150000`.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): transisi BAST dan beranda warga`.

### Task 7: Keamanan warga (W2–W9)

**Files:**
- Modify: `prototype/services/api/security.js`
- Create: `prototype/surfaces/resident/security/` `SecurityHome.js` (W2, tab Rumah/Kawasan), `DoorLock.js` (W3), `HomeCctv.js` (W4), `AreaSecurity.js` (W5), `Gate.js` (W6), `Guests.js` (W7), `Sos.js` (W8), `SosContacts.js` (W9)
- Test: `prototype/__tests__/security.test.js`

**Interfaces:**
- Produces: `unlockDoor(method = 'aplikasi'): Promise<void>` (log "Dibuka · Rina (aplikasi)"), `lockDoor()`, `createAccessCode({label, validUntil}): Promise<AccessCode>` (pin 4 digit), `revokeAccessCode(id)`, `createGuestPass({guestName, date, from, to}): Promise<GuestPass>`, `revokeGuestPass(id)`, `openGate(direction: 'masuk'|'keluar'): Promise<void>` (melempar `Error('Anda di luar area gerbang')` bila `location === 'outside'`), `sendSos(type): Promise<SosEvent>` (melempar `Error('Masih ada laporan darurat yang aktif')` bila ada SOS `sent|accepted`; menambah notifikasi tier `darurat`), `cancelSos(id)` (hanya bila `sent`), `activeSos(state): SosEvent|null`, `listContacts()`, `saveContact({name, phone, relation})`.
- W2 tab Rumah: kartu kunci (status + `SlideToConfirm` "Geser untuk buka"; setelah terbuka tampil hitung mundur kunci otomatis), `CameraView` teras, kode tamu ringkas, riwayat hari ini. Tab Kawasan: grid 6 `CameraView`, satpam bertugas, tautan gerbang & tamu. W7: form → tampil QR (SVG lokal dari kode) + tombol "Kirim lewat WhatsApp" (hanya tampil tautan). W8: `HoldToConfirm` 3000 ms → pilih jenis (kemalingan, kebakaran, medis, lainnya; default kemalingan) → layar status langsung memantau `activeSos` (`sent` = "Menunggu satpam…", `accepted` = "Pak {acceptedBy} menuju rumah Anda", `resolved` = "Selesai") + kontak darurat; teks kecil "Laporan palsu dapat dikenai sanksi pengelola".

- [ ] **Step 1: Uji gagal:** `unlockDoor` lalu `doorStatus(now+10000) === 'unlocked'`, `doorStatus(now+30000) === 'locked'`; `createGuestPass` → `code` cocok `/^[A-Z0-9]{6}$/`, `status === 'active'`; `openGate` dengan `location='outside'` melempar pesan persis; `sendSos('kemalingan')` dua kali → panggilan kedua melempar pesan persis; `cancelSos` mengubah status jadi `cancelled` dan SOS baru boleh dikirim.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi** (W2, W3, W4, W5, W7, W8 tingkat D); tambahkan `sendSos` dan `createGuestPass` ke `window.__rdgDemo` di `PrototypeApp`.  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): keamanan rumah & kawasan — kunci pintar, CCTV, gerbang, tamu QR, SOS`.

### Task 8: Aplikasi satpam (S1–S5)

**Files:**
- Create: `prototype/services/api/guard.js`; `prototype/surfaces/satpam/` `GuardHome.js` (S1), `SosAlert.js` (S2), `GuestScan.js` (S3), `GuardCctv.js` (S4), `Patrol.js` (S5)
- Test: `prototype/__tests__/guard.test.js`

**Interfaces:**
- Consumes: `security.activeSos`, `GuestPass`, sinkron antartab (Task 2).
- Produces: `acceptSos(id, guardName = 'Joko'): Promise<void>` (`sent → accepted`, notifikasi keamanan untuk warga), `resolveSos(id, note): Promise<void>` (`accepted → resolved`), `checkInGuest(code: string): Promise<{ok: true, pass} | {ok: false, reason: 'tidak-ditemukan'|'sudah-dipakai'|'kedaluwarsa'|'dicabut'}>` (berhasil → `status='used'`, notifikasi keamanan "Tamu {nama} sudah masuk"), `logPatrol({checkpoint, note})`.
- S1: status shift, kartu SOS aktif (merah, berkedip ringan) → S2; S2 layar penuh merah: jenis, Blok C-12, waktu, tombol "Terima & menuju" → "Tandai selesai"; S3: tombol "Pindai QR" (simulasi: daftar undangan hari ini bisa diketuk atau input kode manual) → hasil valid/tidak valid dengan alasan; S4 grid 6 `CameraView`; S5 log patroli + tambah.
- Demo dua tab: tab warga kirim SOS → tab satpam (persona satpam) menampilkan peringatan tanpa muat ulang (via event `storage`).

- [ ] **Step 1: Uji gagal:** setelah `sendSos` → `acceptSos` → `activeSos().status === 'accepted'` dan `acceptedBy === 'Joko'`; `resolveSos` → `activeSos(state) === null`; `checkInGuest(code)` pertama `ok: true`, kedua `{ok:false, reason:'sudah-dipakai'}`; kode acak → `tidak-ditemukan`; pass dengan `date` kemarin → `kedaluwarsa`.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi** (S1, S2, S3 tingkat D).  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): aplikasi satpam — terima SOS, pindai tamu, CCTV, patroli`.

### Task 9: Tagihan, kas, isi ulang (W10–W13)

**Files:**
- Create: `prototype/services/api/bills.js`; `prototype/surfaces/resident/bills/` `Bills.js` (W10), `BillHistory.js` (W11), `CashReport.js` (W12), `TopUp.js` (W13)
- Test: `prototype/__tests__/bills.test.js`

**Interfaces:**
- Consumes: `payments.startPayment/confirmPayment` (`targetType: 'bill'|'ppob'`).
- Produces: `listBills()`, `listReceipts()`, `getCashReport(): {months: {month, in, out, balance, items}[]}`, `getTopUpCatalog(): {pulsa, data, pln, pdam}`, `createTopUp({product: 'pulsa'|'data'|'pln'|'pdam', target, nominal}): Promise<{targetType:'ppob', targetId, amount, title}>`, `topUpResult(txId): {token?: string (20 digit, dikelompokkan 4), struk}`.
- W10 tingkat D: kartu IPL Desember Rp150.000 "Jatuh tempo 10 Des" → `PayFlow` (termasuk opsi "Kirim link bayar ke WhatsApp") → "Lunas" + kuitansi. W13: pilih produk → nomor tujuan → nominal → `PayFlow` → token PLN/struk.

- [ ] **Step 1: Uji gagal:** bayar IPL Desember → `listBills()[0].status === 'paid'` dan `listReceipts()` bertambah 1; bayar ulang → `Error('Tagihan ini sudah lunas')`; `createTopUp({product:'pln', target:'1234', nominal: 50000})` → `Error('Nomor meter belum valid')` (minimal 11 digit); token PLN setelah lunas cocok `/^(\d{4}-){4}\d{4}$/`; `getCashReport().months.length === 6` dan `balance` = saldo sebelumnya + in − out.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): tagihan IPL, laporan kas, isi ulang pulsa/PLN/PDAM`.

### Task 10: Komunitas dan pasar (W14–W19)

**Files:**
- Create: `prototype/services/api/community.js`; `prototype/surfaces/resident/community/` `Community.js` (W14), `EventDetail.js` (W15), `Groups.js` (W16), `Polls.js` (W17), `Market.js` (W18), `HomeServices.js` (W19)
- Test: `prototype/__tests__/community.test.js`

**Interfaces:**
- Consumes: `payments` (`targetType: 'market'`).
- Produces: `listAnnouncements()`, `listEvents()`, `getEvent(id)`, `joinEvent(id)` / `leaveEvent(id)`, `listGroups()`, `joinGroup(id)`, `listPolls()`, `vote(pollId, optionId)` (satu suara per polling: suara kedua `Error('Anda sudah memilih')`), `listProducts()`, `addToCart(productId, qty=1)`, `removeFromCart(productId)`, `cartTotal(state): number`, `checkout(): Promise<{targetType:'market', targetId, amount, title}>` (keranjang kosong → `Error('Keranjang masih kosong')`), `listServices()`, `bookService({serviceId, date, slot, note}): Promise<Booking>`.
- W14 tingkat D (tab Pengumuman · Agenda · Hobi · Polling, atau daftar bersegmen); W18 grid produk warga & tenant + keranjang `Sheet`; W19 daftar jasa (tukang, kebersihan, galon, servis AC, sedot WC, taman) → pilih jadwal.

- [ ] **Step 1: Uji gagal:** `joinEvent('ev-1')` menaikkan jumlah peserta 1 dan idempoten; `vote` kedua melempar pesan persis; `addToCart` dua produk → `cartTotal` = jumlah harga; `checkout` dengan keranjang kosong melempar; `bookService` tanpa `slot` melempar `Error('Pilih jam kedatangan')`.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): komunitas, event, hobi, polling, pasar warga, jasa rumah`.

### Task 11: Layanan, perawatan, dokumen, akun (W20–W28)

**Files:**
- Create: `prototype/services/api/care.js`; `prototype/surfaces/resident/care/` `AllServices.js` (W20), `ReportIssue.js` (W21), `Warranty.js` (W22), `HomeDocuments.js` (W23), `Renovation.js` (W24), `Facilities.js` (W25), `Energy.js` (W26); `prototype/surfaces/resident/Notifications.js` (W27), `ResidentAccount.js` (W28)
- Test: `prototype/__tests__/care.test.js`

**Interfaces:**
- Produces: `listTickets()`, `createTicket({kind, category, description, photos}): Promise<Ticket>` (deskripsi < 10 karakter → `Error('Ceritakan kerusakannya sedikit lebih jelas')`), `advanceTicket(id)` (urutan `dibuat → diverifikasi → dikerjakan → selesai`, dipakai pengelola), `confirmTicket(id, rating 1–5)` (hanya dari `selesai` → `dikonfirmasi`), `listWarranty()` (bagian rumah + sisa masa), `claimWarranty({itemId, description})` → membuat `Ticket` `kind:'garansi'`, `listHomeDocuments()`, `submitRenovation({type, startDate, endDate, contractor})`, `listFacilities()`, `bookFacility({facilityId, date, slot})` (slot bentrok → `Error('Jam ini sudah dipesan')`), `getEnergy(): {months: {month, kwh, waterM3}[], tips: string[]}`, `listNotifications()`, `markRead(id)`, `listFamily()`, `inviteFamily({name, phone, role: 'keluarga'|'penyewa'|'art', access: string[]})`, `listDevices()`.
- W21 tingkat D: form (kategori, foto contoh dari ilustrasi lokal, deskripsi) → linimasa tiket; tombol "Konfirmasi selesai + beri nilai" saat `selesai`. W27: kelompok tier dengan warna berbeda, urutan darurat › keamanan › info. W28: profil, anggota keluarga & penyewa (hak akses), perangkat terhubung, kontak darurat, pengaturan notifikasi, label "Data contoh", Keluar.

- [ ] **Step 1: Uji gagal:** `createTicket` deskripsi pendek melempar pesan persis; `advanceTicket` tiga kali → `selesai`, `confirmTicket(id, 5)` → `dikonfirmasi` dan `history.length === 5`; `confirmTicket` saat `dibuat` → `Error('Tiket belum selesai dikerjakan')`; `bookFacility` slot sama dua kali → pesan bentrok; `listNotifications()` terurut tier darurat dulu.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): lapor kerusakan, garansi, dokumen, renovasi, fasilitas, energi, notifikasi, akun`.

### Task 12: Dasbor pengelola kawasan (K1–K7)

**Files:**
- Create: `prototype/components/DesktopShell.js` (bila belum), `prototype/services/api/manager.js`; `prototype/surfaces/manager/` `ManagerHome.js` (K1), `IplAdmin.js` (K2), `TicketsAdmin.js` (K3), `AnnouncementsAdmin.js` (K4), `CashAdmin.js` (K5), `SecurityAdmin.js` (K6), `VendorsAdmin.js` (K7)
- Test: `prototype/__tests__/manager.test.js`

**Interfaces:**
- Consumes: `care.advanceTicket`, `community`, `bills`, `security`.
- Produces: `getManagerSummary(): {iplPaidPct, openTickets, sosThisMonth, occupancy}`, `issueIplBills(period: string): Promise<{created: number}>` (periode yang sudah ada → `Error('Tagihan periode ini sudah diterbitkan')`), `sendIplReminders(unitIds: string[]): Promise<{sent: number}>`, `assignTicket(id, technician)`, `postAnnouncement({title, body, tier})` (muncul di W14 warga dan notifikasi), `listVendors()`, `setVendorStatus(id, 'aktif'|'ditangguhkan')`.
- Tata letak desktop 1366 px: sidebar kiri (logo + menu 7 item), kartu ringkasan glass ringan, tabel unit/tagihan, antrean tiket bergaya kanban sederhana (Dibuat · Diverifikasi · Dikerjakan · Selesai).

- [ ] **Step 1: Uji gagal:** `issueIplBills('2027-01')` membuat 20 tagihan, kedua kali melempar pesan persis; `postAnnouncement` → `listAnnouncements()[0].title` sama dan ada notifikasi baru; `getManagerSummary().iplPaidPct` berubah setelah warga membayar IPL.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): dasbor pengelola kawasan`.

### Task 13: Portal mitra / agen (M1–M5)

**Files:**
- Create: `prototype/services/api/partner.js`; `prototype/surfaces/partner/` `PartnerRegister.js` (M1), `PartnerHome.js` (M2), `PartnerCatalog.js` (M3), `PartnerReferrals.js` (M4), `PartnerCommission.js` (M5)
- Test: `prototype/__tests__/partner.test.js`

**Interfaces:**
- Produces: `registerPartner({account, personal, bank, social})` (wizard 4 langkah: Akun · Data pribadi · Rekening · Media sosial; nomor rekening < 8 digit → `Error('Nomor rekening belum valid')`), `getPartnerHome(): {points, commissionPending, rank, leaderboard: {name, listings, rank}[]}`, `listCatalog()`, `shareLink(unitId): {url: string, qrText: string}` (url berisi `?ref=<kodeMitra>&unit=<unitId>`, ditampilkan saja), `simulateKpr({price, dp, tenorYears, rate}): {monthly}` (harus memberi 1062500 untuk 166000000/5000000/20/5 dibulatkan ke 500 terdekat), `listReferrals()` (tahap `lead → booking → akad`), `requestPayout(amount)` (melebihi saldo → `Error('Saldo komisi tidak cukup')`).

- [ ] **Step 1: Uji gagal:** nilai `simulateKpr` di atas; `shareLink('C-14').url` mengandung `ref=` dan `unit=C-14`; `requestPayout` melebihi saldo melempar; `registerPartner` rekening pendek melempar.
- [ ] **Step 2: FAIL.**  **Step 3: Implementasi.**  **Step 4: PASS.**
- [ ] **Step 5: Commit** `feat(prototype): portal mitra — daftar, katalog beratribusi, rujukan, komisi`.

### Task 14: PWA, tangkapan layar semua layar, QA visual, dokumentasi

**Files:**
- Create: `frontend/public/rdg/manifest.json` (`name: "Rumah Dalam Genggaman · Estora"`, `short_name: "Rumahku"`, `start_url: "/app"`, `scope: "/app"`, `theme_color: "#00454D"`, `background_color: "#E7FFEF"`, ikon `rdg/icon-192.png`, `rdg/icon-512.png`), `frontend/scripts/prototype-screens.js`, `docs/prototype/README.md`, `docs/prototype/screens/*.png`
- Modify: `prototype/PrototypeApp.js` (efek: ganti `href` `<link rel="manifest">` dan `<meta name="theme-color">` saat dipasang, kembalikan saat dilepas)
- Test: `prototype/__tests__/manifest.test.js`

**Interfaces:**
- Consumes: `screens.json`, `window.__rdgDemo`.
- Skrip `node frontend/scripts/prototype-screens.js [--out docs/prototype/screens] [--port 4173]`: melayani `frontend/build` (server http Node bawaan dengan fallback SPA), membuka Chromium (Playwright global: `NODE_PATH=/usr/local/lib/node_modules_global`), untuk setiap entri: siapkan state lewat `/app/demo` + `window.__rdgDemo` (persona sesuai `surface`; untuk S2 dan W8 kirim SOS lebih dulu; untuk S3 buat `createGuestPass`), buka `path`, tunggu `[data-screen]`, ambil PNG (`surface === 'manager'` → 1366×900; selain itu 390×844 `deviceScaleFactor: 2`), lalu ukur ulang di lebar **360** px: catat entri bila `document.documentElement.scrollWidth > innerWidth`. Cetak ringkasan `N layar, M overflow` dan keluar kode 1 bila ada overflow.

- [ ] **Step 1: Uji gagal `manifest.test.js`:** setelah render `PrototypeApp` di `/app/warga`, `document.querySelector('link[rel=manifest]').getAttribute('href') === '/rdg/manifest.json'`; setelah unmount kembali ke nilai semula.
- [ ] **Step 2: FAIL → Step 3: implementasi → Step 4: PASS.**
- [ ] **Step 5: Build dan jalankan skrip.** `cd frontend && CI=true yarn build && NODE_PATH=/usr/local/lib/node_modules_global node scripts/prototype-screens.js` → `59 layar, 0 overflow`.
- [ ] **Step 6: QA visual.** Susun lembar kontak dari PNG; periksa setiap layar: tidak ada teks terpotong/bertumpuk, kontras cukup, konsisten dengan mockup v1, tidak ada kata "Ningrat". Perbaiki dan ulangi Step 5 sampai bersih.
- [ ] **Step 7: Gerbang repo.** `CI=true yarn test --watchAll=false src/prototype` PASS; `python3 ../scripts/validate_compliance.py` PASS; `python3 ../scripts/check_nav_map.py` PASS (WARN untuk `/app/*` boleh); rute lama `/login`, `/portal/login`, `/showroom/x` masih merender (uji cepat Playwright: tidak ada `[data-screen]` dan tidak error).
- [ ] **Step 8: `docs/prototype/README.md`:** cara menjalankan (`yarn start` → `http://localhost:3000/app/demo` — boleh di docs), skrip alur demo (spek §8) langkah demi langkah termasuk dua jendela warga+satpam, daftar layar + PNG, batasan (data contoh, tanpa backend, host guard).
- [ ] **Step 9: Commit** `feat(prototype): manifest PWA, tangkapan layar 59 rute, panduan demo`.
