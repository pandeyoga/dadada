# Deploy Kain Nusantara ERP ke VPS (Ubuntu 22.04 / 24.04 / 26.04)

Domain: **kainnusantara.cloud** · VPS: **187.77.116.148** · Repo: `github.com/pandeyoga/KNHOST`

```
Internet ──443──> edge HTTPS (otomatis dipilih deploy/edge.sh, sertifikat Let's Encrypt auto-renew)
                    └── kn-web (nginx)  ── /*     → build React (SPA)
                                        ── /api/* → kn-backend (FastAPI :8001)
                  kn-mongo (MongoDB 7, volume kn_mongo_data, TIDAK dipublikasikan ke host)
                  volume kn_uploads (berkas unggahan; storage disk lokal)
```

Tidak ada pustaka Emergent di produksi: `emergentintegrations`/`litellm` dibuang saat `pip install`
(Dockerfile.backend) dan `@emergentbase/visual-edits` dibuang saat `yarn install` (Dockerfile.frontend).
`backend/.env` & `frontend/.env` preview tidak ikut ke image; semua konfigurasi dari `deploy/.env`.

## 1. Syarat

| Item | Nilai |
|---|---|
| VPS | Ubuntu LTS, ≥2 vCPU, ≥4 GB RAM (skrip menambah swap 4 GB bila RAM kurang), CPU dengan AVX (MongoDB 7) |
| Akses | `ssh root@187.77.116.148` |
| DNS | A record `kainnusantara.cloud` → `187.77.116.148` (opsional `www` juga), **tanpa proxy Cloudflare** (DNS only) |
| Port | 22, 80, 443 terbuka (skrip mengatur ufw tanpa menghapus aturan yang ada) |

## 2. Pasang sekali jalan (dari komputer Anda)

Pastikan kode terbaru sudah di-push ke GitHub, lalu:

```bash
ssh root@187.77.116.148 'apt-get update -qq && apt-get install -y -qq git && \
  { [ -d /opt/kainnusantara/.git ] || git clone https://github.com/pandeyoga/KNHOST.git /opt/kainnusantara; } && \
  cd /opt/kainnusantara && \
  DOMAIN=kainnusantara.cloud ACME_EMAIL=pk.yogaswastika@gmail.com bash deploy/install_vps.sh'
```

Skrip: paket dasar (+swap) → Docker → firewall → cek DNS → `deploy/.env` (sandi admin acak) → build & up →
tunggu backend sehat → ganti sandi admin → **edge HTTPS tanpa bentrok** → cron backup harian. Di akhir
tercetak URL, login admin, dan mode edge.

### Bagaimana "tidak bentrok" dengan proyek yang sudah ada?

Semua container KN bernama `kn-*`, jaringan `kn`, volume `kn_*`; Mongo tidak membuka port host; `kn-web`
hanya terbuka di `127.0.0.1:<port bebas ≥18080>`. Untuk port 80/443, `deploy/edge.sh` mendeteksi:

| Yang memegang 80/443 | Tindakan | `EDGE_MODE` |
|---|---|---|
| kosong | Caddy milik KN (`kn-caddy`) — HTTPS otomatis | `caddy` |
| container Caddy proyek lain (mis. SIPRO/`dadada`) | Container Caddy itu disambungkan ke jaringan `kn`, blok situs `kainnusantara.cloud → kn-web:80` ditambahkan ke Caddyfile-nya di antara marker, lalu `caddy reload`. Situs lama tidak disentuh. | `attach` |
| nginx di host | vhost `/etc/nginx/sites-available/kainnusantara` + `certbot --nginx` (auto-renew `certbot.timer`) | `nginx` |
| lainnya | berhenti dengan instruksi manual (reverse proxy ke `127.0.0.1:KN_WEB_PORT`) | — |

> Mode `attach`: bila proyek lain menjalankan `update.sh`-nya (`git reset --hard`) sehingga Caddyfile-nya
> kembali ke versi repo, jalankan lagi `bash /opt/kainnusantara/deploy/edge.sh` (idempoten, ±2 detik).
> `deploy/update.sh` KN juga memanggilnya otomatis.

## 3. Setelah terpasang

1. Buka `https://kainnusantara.cloud`, login `admin@kainnusantara.id` dengan sandi yang tercetak
   (tersimpan di `deploy/.env` → `ADMIN_PASSWORD`).
2. Akun demo bawaan bootstrap (`md@`, `manager@`, `sales@`, `finance@`, `warehouse@` … `/demo12345`)
   → **ganti sandi atau nonaktifkan** lewat Admin → Pengguna.
3. Data demo (`seed_realistic.py`) **tidak** dijalankan di produksi (`SEED_DEMO_ENABLED=false`); hanya
   fondasi bootstrap (COA, satuan, konfigurasi, entitas).

## 4. Operasional

```bash
cd /opt/kainnusantara && bash deploy/update.sh              # tarik kode baru + rebuild + restart + edge
cd /opt/kainnusantara/deploy && docker compose ps            # status
cd /opt/kainnusantara/deploy && docker compose logs -f backend
bash /opt/kainnusantara/deploy/backup.sh                     # backup manual (otomatis 02:30 WIB, 14 hari)
bash /opt/kainnusantara/deploy/backup.sh restore deploy/backups/kainnusantara-YYYY-MM-DD_HHMM.archive.gz
```

SSL: Caddy memperbarui sertifikat otomatis; mode nginx memakai `certbot.timer`. Email notifikasi
Let's Encrypt: `pk.yogaswastika@gmail.com`.

## 5. Masalah umum

| Gejala | Penyebab / solusi |
|---|---|
| HTTPS tidak aktif | DNS belum mengarah / masih di-proxy Cloudflare; ulangi `bash deploy/edge.sh` setelah DNS benar |
| `kn-mongo` restart terus, log `AVX` | CPU tanpa AVX → ganti image `mongo:4.4` di `deploy/docker-compose.yml` |
| Build frontend `Killed` | RAM kurang → skrip sudah menambah swap; bila masih, tambah RAM VPS |
| Backend menolak start "CORS_ORIGINS wajib" | `CORS_ORIGINS` di `deploy/.env` kosong → jalankan ulang `install_vps.sh` |
| `edge.sh` berhenti "dipegang container … bukan Caddy" | Tambahkan reverse proxy manual di proxy tersebut ke `http://127.0.0.1:$(grep KN_WEB_PORT deploy/.env)` |
