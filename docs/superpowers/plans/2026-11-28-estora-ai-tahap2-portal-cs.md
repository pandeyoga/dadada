# Estora AI Tahap 2a (Agen CS pembeli di portal) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pembeli yang login portal bisa bertanya ke "Tanya Estora" dan dijawab otomatis dari datanya sendiri; aksi komplain/klaim garansi lewat konfirmasi pembeli; topik sensitif/minta staf menjadi tiket "Pertanyaan dari chat"; plus tiga sisa tahap 1.

**Architecture:** Agen portal memakai mesin tahap 1 (`ai.agent.run_turn`, `ai.conversations`, `ai.actions`, `ai.budget`) dengan `ToolContext(channel="portal", role="buyer_cs")`; alatnya memanggil endpoint `/api/portal/...` in-process (`ai.tools.internal_api.call`) dengan **token portal pembeli** sehingga data otomatis terbatas pada pembeli itu. Router baru `/api/portal/ai/...` (auth portal) dengan SSE; widget React di portal. Tiket serah-ke-CS dibuat oleh kode sistem lewat helper pembuatan komplain yang diekstrak dari `portal_router.py`.

**Tech Stack:** FastAPI, Motor/MongoDB, `anthropic` 2.14.0, React 19 + Tailwind + shadcn/ui, Jest (craco).

**Spec:** `docs/superpowers/specs/2026-11-28-estora-ai-tahap2-portal-cs-design.md` (baca §3, §5, §9). Tahap 1: `docs/superpowers/specs/2026-11-28-estora-ai-agent-cs-crm-design.md`, kode di `backend/ai/`.

## Global Constraints
- Agen portal **hanya** memakai token portal pembeli; tidak ada token staf / `ai_agent`, tidak ada `api_get`/`cari_endpoint`, tidak ada riset web di kanal `portal`.
- Model jawaban `claude-opus-5-5` effort `medium`; pemilah `claude-haiku-5-5` effort `low` (keluaran JSON); ringkasan WA `claude-haiku-5-5`. Aturan Claude tahap 1 tetap: adaptive thinking, tanpa `tool_choice` paksa, `strict: true`, cek `stop_reason`, riwayat aman *preserved thinking* (pemikiran giliran lama dibuang deterministik; system+tools tetap selama satu giliran).
- Serah ke CS **deterministik**: kategori pemilah `diskon_nego`, `janji_komitmen`, `pembatalan_refund` atau pesan berisi kata staf (`consent.HUMAN_WORDS`, ≤ 4 kata) → tiket tanpa memanggil model jawaban. `lainnya_tidak_yakin` **tidak** otomatis serah; model jawaban punya alat `serahkan_ke_cs`.
- Tiket: koleksi `complaints`, `category: "layanan"`, `kind: "pertanyaan_chat"`, `source: "ai_portal"`, `ai_conversation_id`, tenggat **24 jam**; penugasan: biasa → `deal.assigned_to`; sensitif → pengguna aktif ber-peran `sales_manager` pertama di org, bila tidak ada → `owner`; tugas SM-09 + notifikasi staf; **tanpa** WA ke pembeli. Statistik mutu komplain & eskalasi/pelanggaran SLA komplain **mengecualikan** `kind: "pertanyaan_chat"`.
- Aksi pembeli: hanya `buat_komplain` dan `ajukan_klaim_garansi`; dieksekusi hanya oleh `POST /api/portal/ai/actions/{id}/confirm` milik pembeli itu, tepat sekali (klaim atomik `pending → executing`), memakai token portal; selalu mengirim `deal_id` (tanpa fallback `deals[0]`).
- Pengaturan: `ai.portal_enabled` (default `False`), `ai.portal_daily_limit` (default `30`), `ai.portal_notice` (teks default Bahasa Indonesia: menyebut asisten AI, data yang dipakai hanya milik pembeli, cara berhenti & bicara dengan CS). Anggaran AI bulanan **bersama** (berhenti di 100%).
- Privasi: pemberitahuan pada pembukaan pertama (dicatat `ai_consents` kanal `portal` per `portal_user_id`), "Berhenti pakai asisten", "Hapus riwayat chat".
- Tarif tambahan biaya: riset web **USD 10 per 1.000** `web_search_requests`; `claude-sonnet-5-5` (2 / 10 / 0,10) ditambahkan ke tabel tarif untuk fallback; model tak dikenal → tarif Opus + log peringatan.
- Batas berkas gate: `.py` ≤ 800, `.js` ≤ 500; `backend/portal_router.py` (sudah > 800, pelanggaran lama) **tidak boleh bertambah** baris. Gate: `sed 's#^ROOT = "/app"#ROOT = "<root>"#' scripts/validate_compliance.py | python3 -` (tepat 5 pelanggaran lama).
- Uji (mode cepat, keputusan pemilik): hanya uji yang disebut di tiap task; FakeClaude (`ai.client.set_override`); `export MONGO_URL=mongodb://127.0.0.1:27017`, `AI_TEST_DB` unik per agen; `cd backend && python -m pytest tests_ai -q` harus hijau.
- Teks UI Bahasa Indonesia, tanpa emoji, kontras ≥ 4,5:1, ikon `lucide-react`. Commit diakhiri `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` dan `Claude-Session: https://claude.ai/code/session_01WetgRXmuAJkoYLhyp3fN6g`.

## Review Focus
1. Pembeli memasukkan `deal_id`/id komplain milik pembeli lain ke alat atau kartu aksi → ditolak / data kosong, tidak pernah data orang lain — uji Task 1 `test_portal_buyer_isolation`.
2. Pembeli mengetuk "Kirim" dua kali / dua tab → komplain dibuat tepat sekali — uji Task 1 `test_portal_confirm_once`.
3. "Bisa diskon kalau bayar cash?" / "Saya mau batal, uang kembali?" → tiket ke Manajer Penjualan, jawaban tanpa janji, model jawaban tidak dipanggil — uji Task 1 `test_portal_locked_topic_handoff`.
4. Pembeli mengirim pesan ke-31 hari itu, atau anggaran 100% → ditolak dengan pesan jelas, tanpa panggilan Claude — uji Task 1 `test_portal_quota_and_budget`.
5. Agen portal dimatikan di Pengaturan → status `enabled: false`, kirim pesan 403 berbahasa Indonesia; widget menampilkan "belum tersedia" — uji Task 1 `test_portal_disabled` + Task 3 Jest.

---

### Task 1: Backend agen portal (alat, serah-ke-CS, router, pengaturan)

**Files:**
- Create: `backend/ai/portal_tools.py`, `backend/ai/portal_agent.py`, `backend/ai/portal_handoff.py`, `backend/complaint_intake.py`, `backend/routers/portal_ai_router.py`, `backend/tests_ai/test_portal_agent.py`
- Modify: `backend/ai/tools/registry.py` (`ToolContext.channel` + `"portal"`, `role` + `"buyer_cs"`; `_visible` → kanal portal hanya alat `scope == "portal"` + `simulasi_kpr`), `backend/ai/tools/catalog.py` (muat alat portal), `backend/ai/actions.py` (`confirm_by_buyer`, `cancel_by_buyer`; dokumen aksi kanal portal menyimpan `owner_id`), `backend/ai/settings_defs.py` (3 kunci portal), `backend/ai/simulated.py` (kata kunci portal: "tagihan" → `tagihan_saya`, "progres" → `progres_rumah_saya`, selain itu teks "Mode simulasi"), `backend/routers/portal_router.py` (`create_complaint` memakai `complaint_intake.create_complaint`; jumlah baris tidak bertambah), `backend/routers/complaints_router.py` (statistik mengecualikan `kind: "pertanyaan_chat"`; filter `?kind=`), `backend/engine_sweepers.py` (eskalasi/pelanggaran SLA komplain mengecualikan `kind: "pertanyaan_chat"`), `backend/server.py` (daftarkan router), `backend/routers/ai_router.py` (`GET /api/ai/usage` menambah `by_channel` {web, wa, portal} dalam IDR), `backend/ai/indexes.py` (indeks `ai_portal_quota` unik `org_id+portal_user_id+day`)

**Interfaces:**
- Consumes (tahap 1): `ai.agent.run_turn(ctx, conv_id, user_content) -> AsyncIterator[dict]` (event `step_started|step_done|text_delta|action_proposed|artifact|done|error`), `ai.conversations.create/get/list_for/append/history_for_api`, `ai.actions.create_pending(ctx, *, tool, resource, permission, method, path, json, preview, entity_id=None)`, `ai.triage.classify(org_id, text, history)`, `ai.budget.budget_state`, `ai.config.get_ai_settings`, `ai.consent` (pola `ai_consents`), `ai.tools.internal_api.call(token, method, path, *, params=None, json=None) -> (status, data)`, `portal_security.get_portal_user` (token dibaca dari header `Authorization: Bearer` lebih dulu).
- Produces:
  - `complaint_intake.create_complaint(*, org_id: str, portal_user: dict, deal: dict | None, category: str, subject: str, message: str, priority: str = "medium", sla_hours: int = 48, assigned_to: str | None = <deal.assigned_to>, extra: dict | None = None, notify_buyer_wa: bool = True) -> dict` — membuat dokumen komplain, tugas SM-09, notifikasi staf, (opsional) WA ke pembeli; dipakai `portal_router.create_complaint` (perilaku lama sama persis) dan `portal_handoff`.
  - `portal_handoff.create_ticket(ctx, *, reason: str, question: str, summary: str, sensitive: bool, deal_id: str | None) -> {"id","subject","assigned_role": "sales"|"sales_manager"|"owner","due_at"}`.
  - Alat portal (`scope="portal"`, `kind="read"` kecuali disebut): `ringkasan_saya` (`/api/portal/overview`), `kpr_saya` (`/api/portal/kpr`), `tagihan_saya` (`/api/portal/payments` + `/api/portal/payments/submissions`), `kuitansi_saya` (`/api/portal/receipts`), `progres_rumah_saya` (`/api/portal/progress`), `dokumen_saya` (`/api/portal/documents`), `komplain_saya` (`GET /api/portal/complaints`), `garansi_saya` (`/api/portal/warranty` + `/api/portal/warranty/claims`), `serah_terima_saya` (`/api/portal/handovers`), `site_plan` (`/api/portal/site-plan`), `info_umum` (`/api/portal/reference`); `deal_id` opsional menyaring hasil; usulan (`kind="propose"`): `buat_komplain(deal_id, kategori ∈ complaint_category kecuali internal, subjek, pesan)` → `POST /api/portal/complaints`, `ajukan_klaim_garansi(<field model klaim garansi portal yang ada>)` → `POST /api/portal/warranty/claims`; `serahkan_ke_cs(alasan, ringkasan, deal_id?)` → `portal_handoff.create_ticket(sensitive=False)`.
  - `portal_agent.status(portal_user) -> {"enabled","effective_mode","budget_state","quota":{"used","limit"},"notice_text","noticed","stopped"}`; `portal_agent.handle_message(portal_user, token, conv_id, text) -> AsyncIterator[dict]` urutan: nonaktif → error; berhenti → error; kuota (`$inc` atomik `ai_portal_quota`) habis → error "Batas 30 pesan hari ini tercapai…"; budget `stop` → error; pemilah → serah deterministik → event `handoff {"ticket": {...}}` + teks tetap; selain itu `run_turn`.
  - `actions.confirm_by_buyer(action_id, portal_user: dict, token: str) -> dict` / `cancel_by_buyer(action_id, portal_user) -> dict` — hanya `owner_id == portal_user["id"]`, kanal `portal`.
  - Router (`Depends(get_portal_user)`, amplop `{"data": ...}`): `GET /api/portal/ai/status`; `POST /api/portal/ai/notice/ack`; `POST /api/portal/ai/stop`; `POST /api/portal/ai/resume`; `GET|POST /api/portal/ai/conversations`; `GET|DELETE /api/portal/ai/conversations/{id}`; `DELETE /api/portal/ai/conversations` (hapus semua riwayat pembeli); `POST /api/portal/ai/conversations/{id}/messages` `{text}` → SSE (`data: <json>\n\n`; event tahap 1 + `handoff`); `POST /api/portal/ai/actions/{id}/confirm|cancel` → `{"data":{"action":{"id","status","summary","error"}}}`. Bentuk pesan di `GET conversations/{id}` sama dengan Copilot (`ai.api_views.ui_messages`) ditambah `ticket` bila ada.
- [ ] **Step 1: Tulis uji** `test_portal_agent.py`: `test_portal_buyer_isolation` (dua pembeli dengan deal masing-masing; alat `komplain_saya`/`tagihan_saya` dengan token A + `deal_id` milik B → tidak ada data B; `confirm` aksi milik A oleh B → 404), `test_portal_confirm_once` (dua `confirm_by_buyer` bersamaan → satu `executed`, satu ditolak; tepat satu dokumen `complaints` baru dengan `deal_id` yang dikirim), `test_portal_locked_topic_handoff` (FakeClaude pemilah → `diskon_nego`; tidak ada panggilan model jawaban; tiket `kind == "pertanyaan_chat"`, `assigned_to` = email `sales_manager`, tenggat ≈ 24 jam, `send_whatsapp` tidak dipanggil), `test_portal_quota_and_budget` (limit diset 2 → pesan ke-3 error tanpa panggilan Claude; budget `stop` → error), `test_portal_disabled` (`ai.portal_enabled` False → status `enabled: false`, POST pesan 403), `test_complaint_stats_exclude_chat_tickets` (statistik komplain tidak menghitung tiket chat; `?kind=pertanyaan_chat` menampilkannya).
- [ ] **Step 2: Implementasi** sesuai Interfaces; ekstraksi `complaint_intake` tanpa mengubah perilaku `POST /api/portal/complaints`.
- [ ] **Step 3: Verifikasi** suite `tests_ai` hijau + gate kepatuhan (5) + `python3 scripts/verify_ai.py` PASS.
- [ ] **Step 4: Commit** `feat(ai): agen CS pembeli di portal dengan konfirmasi aksi dan serah ke CS`.

### Task 2: Sisa tahap 1 (biaya akurat, ringkasan WA, lampiran sebagai rujukan)

**Files:**
- Modify: `backend/ai/budget.py`, `backend/ai/client.py` (catat model yang benar-benar menjawab; usage dari stream gagal bila tersedia), `backend/ai/conversations.py` (hanya fungsi lampiran/ringkasan; jangan ubah logika strip thinking), `backend/ai/wa_agent.py` (picu ringkasan), `backend/ai/api_views.py` + `backend/routers/ai_router.py` (lampiran sebagai rujukan)
- Create: `backend/ai/summarize.py`, `backend/tests_ai/test_leftovers.py`

**Interfaces:**
- Produces: `budget.cost_usd(model, usage)` menghitung `usage["server_tool_use"]["web_search_requests"] × 10 / 1000`; `PRICES["claude-sonnet-5-5"] = (2.0, 10.0, 0.10)`; `record_usage(..., model=<resp["model"]>)`. `summarize.update_wa_summary(conv_id) -> str | None` — bila pesan di luar jendela 30 bertambah ≥ 10 sejak `summary_upto_seq`, buat ringkasan Haiku (Bahasa Indonesia, ≤ 120 kata, tanpa NIK/nomor rekening) dari pesan di luar jendela + ringkasan lama; simpan `ai_conversations.summary`, `summary_upto_seq`; dipanggil di akhir `wa_agent.process_job` (kegagalan tidak menggagalkan job). Lampiran: pesan pengguna menyimpan `attachment_ids` + blok teks `[Lampiran: <nama>]` (bukan base64); `history_for_api` mengembangkan lampiran untuk **3 pesan berlampiran terakhir** menjadi blok image/document/text (cara `attachment_blocks`), yang lebih lama tetap teks; total lampiran per pesan ≤ 8 MB (ditolak 413 berbahasa Indonesia).
- [ ] **Step 1: Uji** `test_web_search_cost_counted` (usage dengan 3 `web_search_requests` → +0,03 USD), `test_fallback_model_priced` (resp model `claude-sonnet-5-5` → tarif Sonnet), `test_wa_summary_written` (FakeClaude; 45 pesan → `summary` tersimpan; `history_for_api` diawali ringkasan), `test_attachment_stored_as_ref` (`ai_messages` tidak berisi base64; giliran berikut mengembangkan lampiran).
- [ ] **Step 2: Implementasi.** **Step 3:** suite hijau + gate (5).
- [ ] **Step 4: Commit** `fix(ai): biaya riset web & fallback, ringkasan WA, lampiran sebagai rujukan`.

### Task 3: Frontend widget portal + kartu Pengaturan + label tiket chat

**Files:**
- Create: `frontend/src/components/portal/ai/` (`PortalAiButton.js`, `PortalAiPanel.js`, `PortalAiMessage.js`, `PortalAiConfirmCard.js`, `portalAiApi.js`, `portalAiStream.js`), tes `frontend/src/components/portal/ai/__tests__/*.test.js`, `frontend/src/components/ai/settings/PortalAgentCard.js`
- Modify: komponen portal yang merender dasbor (`frontend/src/components/portal/PortalDashboard.js` atau `PortalApp.js`) untuk memasang tombol, halaman Pengaturan AI (`frontend/src/pages/AiSettingsPage.js`) untuk kartu portal, `frontend/src/pages/ComplaintsPage.js` (label "Pertanyaan dari chat" + filter)

**Interfaces:**
- Consumes: endpoint Task 1 (lihat Produces Task 1); SSE dibaca dengan `fetch` + header `Authorization: Bearer <token portal>` sama seperti klien API portal yang ada; event sama dengan Copilot (`aiStream` boleh dipakai ulang bila tidak bergantung token staf) + `handoff`. Pengaturan: `GET/PUT /api/ai/settings` kunci `portal_enabled`, `portal_daily_limit`, `portal_notice`; pemakaian per kanal dari `GET /api/ai/usage` (`by_channel.portal`). Komplain: `kind === "pertanyaan_chat"`; filter `GET /api/complaints?kind=pertanyaan_chat`.
- Produces: tombol mengambang "Tanya Estora" (kanan bawah; layar penuh di < 640 px), panel chat (pemberitahuan pertama dengan tombol "Mengerti", banner "Mode simulasi" bila `effective_mode !== "live"`, sisa kuota "x/30 pesan hari ini", langkah ringkas, kartu konfirmasi "Kirim komplain ini?" dengan Kirim/Batal, kartu tiket "Diteruskan ke CS · No. … · dibalas paling lambat …", tombol "Bicara dengan CS", menu "Berhenti pakai asisten" & "Hapus riwayat chat"); bila `enabled === false` tombol tetap ada tetapi panel berkata "Asisten belum tersedia".
- [ ] **Step 1: Uji Jest (hanya ini):** `portalAiStream` mengurai SSE terpotong + event `handoff`; `PortalAiConfirmCard` memanggil confirm sekali walau diklik dua kali; panel menampilkan "Asisten belum tersedia" saat `enabled: false` dan pemberitahuan pada pembukaan pertama.
- [ ] **Step 2: Implementasi.** **Step 3:** `CI=true npx craco test --watchAll=false src/components/portal/ai src/components/ai` + `REACT_APP_BACKEND_URL=http://127.0.0.1:8001 yarn build`.
- [ ] **Step 4: Commit** `feat(ai): widget Tanya Estora di portal, kartu pengaturan, label tiket chat`.

### Task 4: Gate, panduan, tangkapan layar

**Files:**
- Modify: `scripts/verify_ai.py` (invarian portal), `docs/ai/README.md` (bagian "Agen portal"), `docs/ai/screens/` (tambah `05-portal-tanya-estora.png`, `06-portal-konfirmasi.png`, `07-portal-tiket-cs.png`, `08-pengaturan-portal.png`)

**Interfaces:**
- Produces: invarian `verify_ai.py` baru: (6) setiap `ai_actions` kanal `portal` yang `executed` dieksekusi oleh pemiliknya (`owner_id == executed_by`) dan tidak memakai token staf; (7) tidak ada `ai_usage` kanal `portal` saat `ai.portal_enabled` False; (8) tiket `kind: "pertanyaan_chat"` tidak terhitung di statistik komplain.
- [ ] **Step 1:** Tambah invarian; buktikan bisa GAGAL (rusak sementara satu invarian, lihat FAIL, kembalikan, PASS).
- [ ] **Step 2:** Tangkapan layar Playwright 1440×900 @2x (dan satu 390×844 untuk panel portal di ponsel) dengan backend lokal mode simulasi, `ai.portal_enabled` dinyalakan.
- [ ] **Step 3:** Suite `tests_ai`, `verify_ai.py`, gate kepatuhan, Jest, build.
- [ ] **Step 4: Commit** `docs(ai): gate portal, panduan agen portal, tangkapan layar`.
