"""Indeks koleksi `ai_*` (spec §8.5). Idempoten (`create_index`), dipanggil sekali saat startup."""
import logging

from pymongo.errors import OperationFailure

from db import db

logger = logging.getLogger("estora.ai.indexes")
JOB_TTL_DAYS = 30  # job selesai/gagal dihapus otomatis (bidang `finished_dt` bertipe Date)

# (koleksi, kunci, opsi). Kunci mengikuti pola kueri: worker, riwayat giliran, Inbox, akurasi, anggaran.
INDEXES = [
    ("ai_jobs", [("status", 1), ("created_at", 1)], {}),
    ("ai_jobs", [("status", 1), ("locked_at", 1)], {}),
    ("ai_jobs", [("finished_dt", 1)], {"expireAfterSeconds": JOB_TTL_DAYS * 86400, "name": "ttl_ai_jobs_finished"}),
    ("ai_conversations", [("id", 1)], {}),
    ("ai_conversations", [("owner_id", 1), ("updated_at", -1)], {}),
    ("ai_conversations", [("org_id", 1), ("channel", 1), ("contact.phone", 1)], {}),
    ("ai_messages", [("conversation_id", 1), ("seq", 1)], {}),
    ("ai_messages", [("id", 1)], {}),
    ("ai_actions", [("id", 1)], {}),
    ("ai_actions", [("conversation_id", 1), ("status", 1)], {}),
    ("ai_actions", [("org_id", 1), ("status", 1), ("created_at", -1)], {}),
    ("ai_drafts", [("id", 1)], {}),
    ("ai_drafts", [("conversation_id", 1), ("status", 1), ("at", -1)], {}),
    ("ai_drafts", [("org_id", 1), ("category", 1), ("outcome_at", -1)], {}),
    ("ai_drafts", [("conversation_id", 1), ("source_message_id", 1)], {}),
    ("ai_usage", [("org_id", 1), ("month", 1)], {}),
    ("ai_lead_insights", [("org_id", 1), ("lead_id", 1)], {}),
    ("ai_artifacts", [("id", 1)], {}),
    ("ai_web_queries", [("conversation_id", 1), ("created_at", -1)], {}),
    ("complaints", [("ai_conversation_id", 1), ("created_at", -1)],  # tiket chat portal per percakapan (Tanya Estora)
     {"partialFilterExpression": {"kind": "pertanyaan_chat"}, "name": "ix_complaints_chat_conv"}),
]
UNIQUE = [("ai_consents", [("org_id", 1), ("phone", 1)], "uq_ai_consents_phone"),
          ("ai_identity", [("org_id", 1), ("phone", 1)], "uq_ai_identity_phone"),
          ("ai_portal_quota", [("org_id", 1), ("portal_user_id", 1), ("day", 1)], "uq_ai_portal_quota")]


async def ensure_indexes() -> None:
    for coll, keys, opts in INDEXES:
        try:
            await db[coll].create_index(keys, **opts)
        except OperationFailure as e:  # indeks lama dengan opsi beda: jangan gagalkan startup
            logger.warning("Indeks %s %s tidak dibuat: %s", coll, keys, str(e)[:160])
    for coll, keys, name in UNIQUE:
        try:
            await db[coll].create_index(keys, unique=True, name=name)
        except OperationFailure as e:  # data lama ganda: tetap buat indeks biasa supaya kueri cepat
            logger.warning("Indeks unik %s belum bisa dibuat (%s); memakai indeks biasa.", name, str(e)[:160])
            await db[coll].create_index(keys)
