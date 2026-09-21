# Analisis Mendalam WMS & RFID — Kain Nusantara (Juni 2026)

## A. Kondisi Saat Ini (Hasil Audit Kode)

### RFID (Fase 5 — masih SIMULATOR)
- `rfid_tags`: encode tag↔roll (EPC auto-generate), auto-encode massal, retire tag. Roll-as-SSOT (RFID tidak mengubah kuantitas stok).
- `rfid_devices`: 3 tipe (gate in/out, fixed_reader, handheld) per gudang + seed default. Status online/offline manual, heartbeat hanya di-set saat edit.
- `rfid_reads`: log event. Keputusan gate HIJAU/MERAH murni berbasis STATUS roll (available/quarantine = merah keluar; reserved/allocated = hijau keluar).
- Gate Monitor UI: SIMULASI manual (pilih gate, pilih 1 roll, klik tombol). Bukan layar live.
- Reader scan: sweep simulasi (baca SEMUA tag aktif di gudang), bukan sesi validasi.
- Lokasi RFID: deteksi drift (last-seen gudang ≠ gudang roll).

### WMS
- Inbound: task dari PO → scan-receive (input manual qty/batch/lot/grade, catch-weight, konversi UOM), eskalasi, complete.
- Outbound: task dari SO → release, scan-pick, eskalasi, dispatch + surat jalan. HANYA dari SO (sudah sesuai prinsip Anda).
- Putaway: antrean roll tanpa bin → tempatkan ke bin. Validasi: bin ada di gudang yg sama + pagar tahanan inspeksi (hold QC). Struktur Zone→Rack→Level→Bin embedded di `warehouses.zones`, ada kapasitas & utilisasi bin.
- Lain: QC inspeksi roll, grading, cycle count, transfer antar-gudang, lot genealogy.

## B. GAP vs Kebutuhan Anda (printer + 2 gate + handheld, keamanan penuh)

| # | Kebutuhan Anda | Kondisi Sekarang | Gap |
|---|---|---|---|
| 1 | Penerimaan barang → BULK PRINT tag RFID dari pembelian (PO) | Encode per-roll / auto-encode simulasi. TIDAK ada integrasi printer RFID (ZPL/Zebra), tidak ada "print job" per GR/PO | **BESAR** — perlu modul Print Job: pilih PO/GR → generate EPC batch → kirim ZPL ke printer → status printed/encoded |
| 2 | Validasi hasil print dengan HANDHELD | Reader scan = sweep simulasi semua tag. Tidak ada sesi verifikasi "expected vs actual" | **BESAR** — perlu Sesi Verifikasi: daftar EPC yang diharapkan (dari print job/GR) vs yang terbaca handheld, selisih di-highlight |
| 3 | Putaway dengan RULES per gudang (kategori/jenis kain) | Gudang TIDAK punya field rules. Putaway hanya cek bin ada + hold QC | **BESAR** — perlu `warehouses.storage_rules` (kategori/jenis kain yang diizinkan, per gudang / per zona) + enforcement di `putaway_roll` |
| 4 | Gate IN validasi barang masuk sesuai tujuan putaway/rules gudang | Keputusan gate hanya berbasis status roll, tidak melihat gudang tujuan / rules / dokumen | **BESAR** — gate IN harus cek: roll ini memang ditujukan ke gudang ini (dari GR/putaway/transfer)? Kategorinya cocok dengan rules gudang? |
| 5 | Barang keluar HANYA dari SO, gate OUT validasi | Sebagian ada (status reserved/allocated = hijau) tapi TIDAK terikat dokumen: tidak ada manifest "gate-out session untuk SO-123, roll yang sah = X,Y,Z" | **SEDANG** — perlu Gate Manifest per SO/dispatch: roll di luar manifest = MERAH + alarm, walau statusnya allocated untuk SO lain |
| 6 | Layar admin gudang di gate IN & OUT per gudang | Gate Monitor = form simulasi, bukan kiosk live | **BESAR** — perlu Layar Gate (kiosk mode): feed real-time (polling/WebSocket), lampu HIJAU/MERAH besar, antrean dokumen aktif, tombol acknowledge alarm |
| 7 | Integrasi hardware nyata (fixed gate, handheld, printer) | 100% simulator. Tidak ada endpoint ingest untuk device fisik, tidak ada API key device, tidak ada heartbeat | **BESAR** — perlu Device Ingest API: `POST /api/rfid/ingest` (device_key + list EPC terbaca), heartbeat, antifraud (device hanya boleh lapor untuk gudangnya) |
| 8 | Keamanan penuh (anti-theft) | Read MERAH hanya tercatat di log | **SEDANG** — perlu Incident/Alarm workflow: alarm → acknowledge oleh admin gudang → catatan tindakan → laporan shrinkage |
| 9 | (Bonus standar industri) Cycle count via RFID | Cycle count ada tapi manual, tidak pakai sweep RFID | **KECIL** — rekonsiliasi hasil sweep handheld vs stok sistem |

## C. Perbandingan dengan Cleverence Warehouse 15

Cleverence W15 (standar industri): hybrid barcode+RFID, bulk read 200 item/3 detik, dock-gate & shrinkage control, receiving tervalidasi vs PO real-time, putaway dengan zone/category rules + rekomendasi lokasi, picking terpandu per dokumen, stock-taking full/parsial via RFID, print label on-the-spot (Bluetooth/WiFi), offline-first, hardware-agnostic (Zebra/Honeywell/Chainway), open API.

Posisi Kain Nusantara:
- ✅ SETARA/di atas: struktur lokasi 4 level, SSOT roll, pagar QC hold, lot genealogy, multi-entity — Cleverence tidak sekaya ini di sisi ERP.
- ⚠️ SETARA sebagian: receiving vs PO (ada, tapi tanpa RFID), picking dari SO (ada, tanpa RFID).
- ❌ TERTINGGAL: semua yang menyentuh hardware nyata (print, ingest, gate live), putaway rules engine, sesi verifikasi expected-vs-actual, alarm workflow, mode offline handheld.

## D. Rekomendasi Arsitektur & Roadmap (menunggu persetujuan)

### Prinsip arsitektur
1. RFID tetap TIDAK mengubah kuantitas (Roll-as-SSOT dipertahankan) — RFID = mata & satpam, ERP = otak.
2. Semua alur diikat DOKUMEN: print job ← GR/PO, gate-out manifest ← SO/dispatch, gate-in expectation ← GR/putaway/transfer.
3. Device fisik bicara lewat satu pintu: `POST /api/rfid/ingest` dengan device API key (per device, per gudang). Simulator lama tetap ada untuk demo/testing.

### Roadmap bertahap
- **FASE R1 — Penerimaan & Printing**: koleksi `rfid_print_jobs` (dari GR/PO → generate EPC per roll → payload ZPL → status queued/printed/encoded/verified), UI "Cetak Tag Massal" di Inbound, endpoint download/kirim ZPL.
- **FASE R2 — Verifikasi Handheld**: `rfid_verify_sessions` (expected EPC list vs scanned), UI sesi verifikasi (progress %, missing/extra), handheld ingest endpoint.
- **FASE R3 — Putaway Rules Engine**: `warehouses.storage_rules` (kategori/jenis kain per gudang & per zona), enforcement di putaway + saran lokasi otomatis (rule-match + kapasitas tersisa).
- **FASE R4 — Gate Live & Manifest**: gate-in validation (dokumen + rules gudang), gate-out manifest per SO, `rfid_gate_sessions`, Layar Kiosk Gate per gudang (in & out) dengan feed real-time + alarm besar HIJAU/MERAH.
- **FASE R5 — Keamanan & Ops**: incident/alarm workflow (acknowledge, catatan, laporan shrinkage), heartbeat monitor device, cycle count via sweep RFID.

## E. REVISI berdasarkan penjelasan praktik lapangan user (Juni 2026)

### Konsep baru yang HARUS ditambahkan (belum ada di kode & belum ada di plan R1-R5 awal):
1. **Tipe gudang**: `warehouses.wh_type` = "transit" | "storage". Gudang transit = titik masuk semua barang (inspect, QC, print tag, verify) & titik keluar (staging, final check, loading). Device transit: RFID printer + handheld. Device storage: gate in/out + monitor PC.
2. **Journey stage terpisah dari status stok**: JANGAN tambah status roll baru ke bucket SSOT. Tambah field terpisah `inventory_rolls.journey` = {stage, routing, putaway_order_id, ...}. Status bucket (available/reserved/dst) tetap jadi SSOT kuantitas; journey = jejak fisik.
3. **Routing decision (poin 3 user)**: `journey.routing` = "store" (putaway ke gudang penyimpanan) | "cross_dock" (tetap di transit, langsung ready-to-ship). Cross-dock terdeteksi otomatis jika PO terhubung SO (special order) atau manual oleh admin. Label UI jelas: badge "CROSS-DOCK / LANGSUNG KIRIM" vs "SIMPAN".
4. **Putaway Order (dokumen)**: putaway queue sekarang cuma antrean roll. Harus jadi DOKUMEN per gudang tujuan (PA-xxxx): daftar roll + gudang tujuan + rules-check → jadi acuan validasi gate-in.
5. **Putaway Confirmation / Bukti Terima Gudang (istilah yang user cari)**: dokumen terbit saat barang tiba di gate-in gudang penyimpanan & tervalidasi. Istilah industri: "Putaway Confirmation" (SAP: Warehouse Task Confirmation). Nama di app: **"Bukti Terima Gudang (BTG)"**.
6. **Gate Exception & Checker Session**: jika gate-in/out mismatch (tak terbaca / tak sesuai) → roll bermasalah masuk exception; yang OK tetap lanjut masuk. Operator scan ulang via handheld, UI checker DI ERP (PC per gudang) — handheld hanya alat baca (kirim EPC via ingest API).
7. **Final Loading Check**: sebelum naik mobil di transit, sesi handheld validasi vs SO (manifest). Selisih = blokir dispatch.
8. **Surat jalan supplier matching**: GR menyimpan `supplier_dn_number` untuk dicocokkan dengan surat jalan fisik pengirim.

### State machine journey (INBOUND → STORE):
`received_transit` → `qc_pending` → `qc_passed` (atau hold/quarantine) → `tag_printed` → `tag_verified` → [routing decision] →
- STORE: `putaway_assigned` (masuk Putaway Order PA-xxx) → `putaway_in_transit` → gate-in validasi → `stored` (BTG terbit) | `gate_exception` → checker → resolve
- CROSS-DOCK: `cross_dock_ready` (tetap di transit) → langsung ke alur outbound staging

### State machine journey (OUTBOUND dari SO/Transfer):
`allocated` → `picking` (picking list per gudang) → `picked` → gate-out validasi → `to_transit` → `staged_transit` → final loading check (handheld vs SO) → `loaded` → `dispatched/in_transit` → `delivered`

### Dokumen lengkap dalam siklus:
GR (ada) → Print Job RFID (baru) → Verify Session (baru) → Putaway Order (upgrade) → Gate Session in (baru) → BTG/Putaway Confirmation (baru) || Picking List (ada, perlu split per gudang) → Gate Session out (baru) → Staging/Final Check (baru) → Surat Jalan (ada)

### Roadmap DIREVISI:
- **R0 — Fondasi**: wh_type transit/storage, journey stage model, routing store/cross-dock, supplier_dn di GR
- **R1 — Print & Verify di Transit**: print job massal dari GR, sesi verifikasi handheld vs GR
- **R2 — Putaway Order + Rules**: dokumen PA per gudang tujuan, storage_rules per gudang/zona, saran gudang otomatis
- **R3 — Gate Live**: ingest API device, gate session in/out + manifest, layar monitor per gate, exception + checker session di ERP
- **R4 — Outbound penuh**: picking per gudang, staging transit, final loading check vs SO
- **R5 — Keamanan & Ops**: alarm workflow, shrinkage report, heartbeat, cycle count RFID

## F. AUDIT LANJUTAN — Entitas, Gudang, Interco, Retur (sudah ADA di kode)

### Yang SUDAH ada (kuat):
1. **Entity scoping (F0-B)**: scope registry per koleksi; inventory pakai `owner_entity_id` (dukung barang entitas A,B,C campur di 1 gudang — kebutuhan gudang central SUDAH terpenuhi di level data). RFID tags/reads ikut owner.
2. **Gudang shared/dedicated (E4.1)**: `sharing_mode` shared|dedicated + `entity_ids[]` (many-to-many). Gudang punya `city`, zones/racks/levels/bins. TIDAK ada: hierarki lokasi/site, gedung, tipe/peran gudang.
3. **Interco G-6 (jual-beli antar-PT)**: dokumen kembar (seller: SO+SJ+invoice internal; buyer: PO+vendor bill), pair_id, harga dari kontrak internal (fixed_price), PPN mode, settlement, invarian IC-AR=IC-AP, GL akun transit 1-1310, link warehouse-task. Flow: create→confirm→ship→receive→invoice→settle.
4. **Interco Return G-6b**: retur antar-PT dokumen kembar, nilai buku dipulihkan ke cost asli penjual, dual-control, faktur pengganti.
5. **Sales Returns (1.11 + R2)**: draft→pending_approval→approved→inspecting→inspected→settled (refund/store_credit/nego/reject), complaint reasons, lampiran FOTO, quarantine+release, regrading (grade A/B/C→rekomendasi outcome), **transfer-ownership per roll**, **create-purchase-return** (jembatan retur jual→retur beli), **/returns/chain/{doc_id}** (rantai dokumen retur).
6. **Purchase Returns**: submit→approve→ship-to-supplier→supplier-accept/reject→goods-back.
7. **Label printer**: sudah ada generator ZPL/ESC-POS (barcode) — pijakan bagus untuk print RFID.

### GAP terhadap penjelasan gudang & retur user:
- G1 **Hierarki gudang**: butuh Kota → Lokasi/Site (Rancamalang, Soreang, Jakarta) → Gedung → zona/rak/bin. Saat ini flat + city saja.
- G2 **Peran gudang (future-proof)**: bukan single type tapi `roles[]`: central_inbound, transit, storage, return, staging — bisa berubah tanpa migrasi. + `storage_rules` per gedung.
- G3 **Gudang retur**: belum ada tujuan fisik khusus retur; quarantine ada tapi tidak terikat gudang/gedung retur.
- G4 **RFID sebagai syarat retur**: lampiran foto ada; referensi EPC/tag untuk validasi keaslian barang retur belum.
- G5 **Routing retur multi-leg**: customer→gudang Jakarta→(simpan / kirim ke central) belum ada dokumen kaki-perjalanan; transfer antar gudang ada tapi tidak terjahit ke dokumen retur.
- G6 **Jejak Barang (Item Passport)**: /returns/chain hanya untuk retur. Butuh timeline SATU roll lintas SEMUA dokumen (PO→GR→print→verify→PA→BTG→SO→pick→gate→SJ→retur→interco→retur beli) — data sudah ada tersebar (movements, reads, refs, pair_id), tinggal API+UI timeline.
- G7 **Decision matrix pemenuhan**: keputusan "beli sendiri vs beli via entitas lain (interco) vs ambil stok; simpan dulu vs cross-dock; kirim via gudang Jakarta vs langsung" belum ada wizard/aksi terpandu — user harus merangkai dokumen manual.

### MATRIKS SKENARIO (dikembangkan sesuai permintaan):
Sumbu: (1) siapa yang beli: A sendiri | B punya kontrak (interco) ; (2) routing fisik: store central | cross-dock | via gudang tujuan | langsung customer ; (3) kepemilikan: tetap | pindah via interco ; (4) retur: ke gudang penjual | langsung central | ke supplier (via interco return bila pembeli≠pemegang kontrak) | pindah kepemilikan saja.
Detail 8 skenario inti di bagian G analisis chat (S1–S8).

### FINANCE MAPPING (anti selisih):
- Tiap perpindahan fisik TANPA ganti pemilik = transfer (tanpa jurnal AR/AP, hanya relokasi qty).
- Tiap ganti pemilik = interco (jurnal kembar, harga kontrak, 1-1310 transit netral).
- Retur customer = credit note + stok masuk quarantine dengan nilai sesuai outcome regrade.
- Retur ke supplier lintas entitas = interco return (pulihkan cost asli) DULU baru purchase return — urutan ini yang menjaga GL tidak selisih.
- Cross-dock: COGS tetap WAC entitas pemilik; tidak ada jurnal tambahan karena tidak pernah jadi stok gudang penyimpanan.

### Roadmap DIREVISI v2 (menggantikan v1):
- **R0 — Fondasi Gudang & Journey**: hierarki site/gedung, roles[] gudang, storage_rules, journey stage, routing store/cross-dock, supplier_dn
- **R1 — Print & Verify RFID di Transit** (pijakan: label_printer ZPL sudah ada)
- **R2 — Putaway Order + Rules + BTG**
- **R3 — Gate Live + monitor + checker + ingest API**
- **R4 — Outbound penuh + final loading check + jahit interco/transfer ke gate**
- **R5 — Retur fisik multi-leg + gudang retur + RFID evidence + Jejak Barang timeline**
- **R6 — Keamanan, alarm, shrinkage, heartbeat, cycle count RFID**
- **R7 — Fulfillment Decision Wizard (matriks S1–S8 jadi aksi terpandu)**

## G. FAKTA LAPANGAN FINAL (jawaban user, Juni 2026 — MENGIKAT untuk desain)

### Gudang:
- **Rancamalang (CENTRAL)**: 5 gedung — G1 Transit, G2 Woven, G3 Knitting, G4 Printing, G5 Retur
- **Soreang**: 1 gedung penyimpanan (sementara)
- **Jakarta**: 1 gedung penyimpanan (sementara)
- Rules penyimpanan = berdasarkan KATEGORI master ERP yang sudah ada, harus configurable
- Kepemilikan gudang belum pasti → semua harus configurable oleh user (roles, rules, sharing)

### Hardware:
- Semua Chainway (Android): fixed reader UR300 (gate), handheld Chainway, printer RFID Chainway
- EPC: custom (generator existing OK)
- Gate fisik: HANYA gudang penyimpanan → Central 4 gedung penyimpanan punya gate in+out fisik; Soreang punya; Jakarta TIDAK ada (handheld only) → gate_config per gedung wajib configurable

### Operasional:
- Volume: RIBUAN roll/hari → semua operasi wajib bulk + index + pagination
- Operator: 1 per gudang penyimpanan, >1 di transit → login per operator, layar per gudang
- Cross-dock: KEPUTUSAN ADMIN (manual) dengan saran otomatis bila PO terhubung SO

### Retur:
- Gedung Retur (G5) rules-nya berbasis GRADE bukan kategori (jenis boleh campur)
- Regrade BAGUS → kembali ke gudang penyimpanan asal (putaway order ke origin); grade TURUN → tetap di gudang retur
- Barang retur PERLU PRINT TAG BARU (tag lama hilang/rusak)
- Barang Sisa (BS) disimpan di gudang retur

### Case lain:
- TIDAK ada konsinyasi
- Makloon: bahan keluar TANPA rfid; barang jadi hasil makloon MASUK VIA TRANSIT, logic sama seperti pembelian
- Ambil sendiri di gudang: tetap via transit, sama seperti alur normal, hanya metode pengambilan beda

### Mandat non-fungsional dari user:
- SSOT ketat, tanpa duplikasi DB/endpoint
- IA rapi: KONSOLIDASI ke halaman existing, JANGAN buat halaman baru bila ada yang relevan
- Flow frontend intuitif mengikuti alur kerja fisik

### Keputusan desain final (R0):
- Koleksi baru `warehouse_sites` {id, name, city}; `warehouses` = GEDUNG, tambah field: site_id, roles[] (transit|storage|return|staging|central_inbound), storage_rules {mode: "category"|"grade", category_ids[], grades[]}, gate_config {physical_gate: bool}
- Semua dikonfigurasi via halaman Warehouse Master EXISTING (drawer/tab), bukan halaman baru
- IA konsolidasi: R1 print+verify → tab di Inbound existing; Gate live → upgrade Gate Monitor existing; Jejak Barang → panel di detail roll existing

### Skema data baru (ringkas)
- `rfid_print_jobs`: {id, source_type: "gr"|"po", source_id, warehouse_id, items:[{roll_id, epc, zpl, status}], status, created_by}
- `rfid_verify_sessions`: {id, print_job_id|gr_id, expected_epcs[], scanned_epcs[], missing[], extra[], status}
- `warehouses.storage_rules`: {allowed_categories[], allowed_fabric_types[], zone_overrides:[{zone_id, allowed_categories[]}]}
- `rfid_gate_sessions`: {id, gate_id, direction, source_type: "so_dispatch"|"gr"|"transfer", source_id, manifest_epcs[], reads[], alarms[], status}
- `rfid_incidents`: {id, read_id, gate_id, severity, status: open|acknowledged|resolved, notes, actor}
