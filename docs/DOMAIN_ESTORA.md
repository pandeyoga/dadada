# Pindah Domain ke estora.id + Instance demo & trial

Hasil akhir di VPS `187.77.116.100`:

| Domain | Isi | Catatan |
|---|---|---|
| `https://hl5.estora.id` | **Data produksi yang sekarang** (dari hl5.portalsipro.com) | Database, file, akun, sandi & sesi tidak berubah |
| `https://hl5.portalsipro.com` | Dialihkan otomatis (308) ke hl5.estora.id | Link lama (portal pembeli, WA) tetap jalan; webhook `/api/webhooks/*` tetap diterima |
| `https://demo.estora.id` | Instance baru, **database kosong** + akun demo per peran | Database terpisah total |
| `https://trial.estora.id` | Instance baru, **database kosong** + akun demo per peran | Database terpisah total |

```
Internet ──443──> Caddy bersama (deploy/edge, HTTPS otomatis semua domain)
                    ├── hl5.estora.id      → instance hl5   (mongo + backend + frontend, volume lama sipro_mongo_data)
                    ├── hl5.portalsipro.com → redirect ke hl5.estora.id
                    ├── demo.estora.id     → instance demo  (volume sipro_demo_mongo_data)
                    └── trial.estora.id    → instance trial (volume sipro_trial_mongo_data)
```

---

## Langkah 1 — Buat DNS A record (di panel domain estora.id)

Login ke tempat Anda membeli/mengelola domain **estora.id** (mis. Niagahoster, Rumahweb, Domainesia,
IDCloudHost, Cloudflare). Buka menu **DNS Management / Kelola DNS / DNS Zone**, lalu tambahkan 3 record:

| Type | Name / Host | Value / Points to | TTL |
|---|---|---|---|
| `A` | `hl5` | `187.77.116.100` | 3600 (atau Auto) |
| `A` | `demo` | `187.77.116.100` | 3600 (atau Auto) |
| `A` | `trial` | `187.77.116.100` | 3600 (atau Auto) |

Penting:
- Isi **Name** cukup `hl5` / `demo` / `trial` (bukan `hl5.estora.id`). Beberapa panel menambahkan `.estora.id` otomatis.
- **Cloudflare**: klik ikon awan sampai **abu-abu (DNS only)**. Awan oranye (proxied) membuat SSL gagal.
- Jangan hapus record domain lama `hl5.portalsipro.com` — tetap dipakai untuk pengalihan.

Cek dari komputer Anda (tunggu 5–30 menit setelah disimpan):

```bash
nslookup hl5.estora.id      # harus muncul 187.77.116.100
nslookup demo.estora.id
nslookup trial.estora.id
```

Atau buka https://dnschecker.org → ketik `hl5.estora.id` → tipe `A` → semua harus `187.77.116.100`.

## Langkah 2 — Push kode terbaru

Di Emergent klik **Save to GitHub** (branch yang dipakai VPS).

## Langkah 3 — Jalankan migrasi di VPS

```bash
ssh root@187.77.116.100
cd /opt/sipro
git fetch --all --prune && git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
bash deploy/migrate_estora.sh
```

Ketik `YA` saat diminta. Yang dilakukan skrip, berurutan:

1. **Cek** stack lama, volume data, dan DNS `hl5.estora.id` (bila DNS belum benar → berhenti, tidak ada yang diubah).
2. **Backup penuh** database + salinan `.env` lama ke `deploy/backups/migrasi-estora-<tanggal>/`
   dan mencatat jumlah dokumen tiap koleksi.
3. **Build** image baru — situs lama tetap melayani selama build.
4. **Pindah** ke Caddy bersama (jeda ±1–2 menit). Volume data lama dipakai ulang apa adanya
   (tidak disalin, tidak diubah). `JWT_SECRET`, sandi, kunci WA — semua sama seperti sebelumnya.
5. **Verifikasi**: jumlah dokumen tiap koleksi harus sama/lebih banyak dari sebelum.
   Bila ada yang berkurang atau backend gagal start → **rollback otomatis** ke situs lama.
6. Membuat instance **demo** & **trial** (database kosong + akun demo), memasang cron backup harian 02:00.

Di akhir tercetak URL dan sandi Super Admin tiap instance (juga tersimpan di `deploy/instances/<nama>.env`).

## Langkah 4 — Sesudah migrasi

1. Buka `https://hl5.estora.id` → login (semua pengguna perlu **login ulang sekali** karena cookie terikat domain).
2. **Meta / WhatsApp**: Dashboard Meta → WhatsApp → Configuration → Webhook → ganti Callback URL ke
   `https://hl5.estora.id/api/webhooks/wa` → *Verify and save*. (Domain lama tetap meneruskan webhook, tetapi sebaiknya diganti.)
3. Bila memakai Meta Pixel / Google Ads / form lead di website lain: ganti URL ke `hl5.estora.id`.
4. **demo & trial**: login Super Admin dengan sandi yang dicetak skrip; akun demo per peran
   (`owner@ manager@ marketing@ sales@ sales2@ finance@ pm@ site@sipro.co.id`) bersandi `Sipro#2026` —
   **ganti sandinya** bila domain ini dibuka untuk umum.

## Operasional sehari-hari

```bash
cd /opt/sipro
bash deploy/update.sh                          # tarik kode + backup + build SEKALI + update semua instance
bash deploy/backup.sh                          # backup semua instance (otomatis tiap 02:00, simpan 14 hari)
bash deploy/backup.sh hl5                      # backup satu instance
bash deploy/backup.sh restore hl5 deploy/backups/hl5/sipro-hl5-YYYY-MM-DD_HHMM.archive.gz
bash deploy/add_instance.sh nama sub.estora.id --empty   # instance baru (butuh A record dulu)

# status / log satu instance
source deploy/lib.sh && dc hl5 ps && dc hl5 logs -f backend
source deploy/lib.sh && dc_edge logs -f caddy  # log HTTPS/sertifikat
```

## Rollback (kembali ke hl5.portalsipro.com)

```bash
cd /opt/sipro && bash deploy/migrate_estora.sh rollback
```

Caddy bersama & instance demo/trial dihentikan, stack lama dijalankan lagi dengan volume data yang sama.
**Tidak ada volume yang dihapus** di skrip mana pun. Backup sebelum migrasi tetap ada di `deploy/backups/migrasi-estora-*`.

## Kebutuhan VPS

3 instance (masing-masing MongoDB + backend + nginx) ± 1,5–2,5 GB RAM saat jalan; build frontend
butuh ±3 GB sementara (dibangun **sekali** untuk semua instance). Disarankan ≥ 4 GB RAM; bila 4 GB pas-pasan,
tambahkan swap 2 GB: `fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab`.
