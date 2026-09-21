# Laporan Sesi 17 — 2026-09-06 (Pesan 452)

## Diminta
1. Leads/prospek di HP sales. 2. Inbox persetujuan HP (manajer/finance). 3. Ratchet INV-ATOMIC-01 dari 26.

## Dikerjakan
- `frontend/src/features/sales/mobile/MobileLeads.jsx` (+ menu `leads` di `MobileMore.jsx`): daftar per tahap, catat prospek (offlinePost), geser tahap, konversi → pelanggan.
- `frontend/src/features/mobile/MobileApprovalInbox.jsx` + `MobileOpsApp.jsx`: tab Persetujuan (approve/reject harga khusus `decision_notes`, pesanan khusus `notes`/`reason`), tab Notifikasi (deep-link ke Persetujuan), Antrean, Ringkas, Desktop.
- Klaim saga: `categories.py` PATCH (handler dipindah ke bawah DELETE agar guard membaca sumber PATCH), `special_orders.py` convert-to-so, `wms.py` outbound-from-order. Guard baseline 26 → 24, 67 cek, self-test hijau.
- `scripts/audit_create_modal.py`: `MobileLeads.jsx` didaftarkan INLINE_DIBOLEHKAN (form menukar layar penuh).

## Bukti
- `scripts/probe_sesi17.py` ALL PASS (14 cek). Gate `--quick` hijau. Testing agent iteration_334 (1 bug: `useEffect(load, [])` — load mengembalikan Promise → React memanggilnya sebagai cleanup → crash) → diperbaiki → iteration_335 PASS.

## Catatan
- RFID devices = koleksi tunggal (tidak masuk inventaris multi-koleksi) → tidak diklaim.
- Pemisahan tugas: pengaju harga tidak boleh memutuskan sendiri; submit price approval wajib bukti chat (probe set `pending` langsung di Mongo).
- Status: shipped + testing-agent verified, belum dikonfirmasi pengguna.
