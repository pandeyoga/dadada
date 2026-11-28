# Uji AI (in-process)

Aplikasi FastAPI dijalankan in-process (`httpx.ASGITransport`) ke MongoDB lokal; tidak memakai
`REACT_APP_BACKEND_URL`. DB uji: `estora_ai_test` (ganti lewat env `AI_TEST_DB`), di-drop tiap sesi.
Fixture: `app`, `client`, `login(email) -> token` (async), `auth(token) -> headers`.
Sandi demo mengikuti `seed.py` (`TEST_PASSWORD` = `Sipro#2026`; super admin = `SUPERADMIN_PASSWORD`).

## Pasang MongoDB 8.0 (Ubuntu 24.04 noble)
```
curl -fsSL https://pgp.mongodb.com/server-8.0.asc | gpg --dearmor -o /usr/share/keyrings/mongodb-server-8.0.gpg
echo "deb [ signed-by=/usr/share/keyrings/mongodb-server-8.0.gpg ] https://repo.mongodb.org/apt/ubuntu noble/mongodb-org/8.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-8.0.list
apt-get update && apt-get install -y mongodb-org-server
```

## Jalankan mongod (latar; data di luar repo)
```
D=/tmp/claude-0/-home-user-dadada/4c43c2dd-1aa7-553c-9e9f-59508645de56/scratchpad
mkdir -p $D/mongo-data
nohup mongod --dbpath $D/mongo-data --bind_ip 127.0.0.1 --port 27017 --logpath $D/mongod.log >/dev/null 2>&1 &
```

## Dependensi
`emergentintegrations` dan `litellm` hanya ada di workspace Emergent (lihat `deploy/Dockerfile.backend`):
```
grep -viE '^(emergentintegrations|litellm)([=<>@ ]|$)' requirements.txt > /tmp/req.txt
pip install --ignore-installed pyparsing -r /tmp/req.txt
```

## Menjalankan
```
cd backend && python -m pytest tests_ai -q
```
`tests_ai/pytest.ini` menggantikan `backend/pytest.ini` (tanpa xdist, event loop sesi tunggal).

## Variabel lingkungan wajib

`MONGO_URL` harus diset sebelum pytest (conftest tidak menyimpan URI di kode, sesuai gate kepatuhan):

```bash
export MONGO_URL=mongodb://127.0.0.1:27017
cd backend && python -m pytest tests_ai -q
```

`AI_TEST_DB` (opsional, default `estora_ai_test`) memilih nama DB uji, berguna bila beberapa proses uji berbagi satu mongod.

