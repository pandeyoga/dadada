# Task 8 report
Status: DONE_WITH_CONCERNS. Tests: tests_ai 31 passed (5 new in test_consent_identity_web.py). Gate: exactly the 5 pre-existing failures.

## Public signatures
- ai/consent.py: `state(org_id, phone) -> {noticed_at, stopped, pending_optin, optins{unofficial, documents}}`; `handle_keyword(org_id, phone, text) -> "stop"|"human"|"yes"|None`; `mark_noticed`; `notice_text(org_id)`; `ask_optin(org_id, phone, kind)` (sets pending so a later YA opts in that kind); `resume(org_id, phone)`.
  STOP/BERHENTI (via wa_compliance.detect_opt_out) calls existing `wa_compliance.register_opt_out` (wa_optouts) and sets ai_consents.stopped; `state.stopped` is true if either exists. `wa_channels.has_unofficial_optin` now delegates to `consent.state`.
- ai/identity.py: `is_verified`, `is_locked`, `start -> {"question"}`, `check(org, phone, answer) -> bool`, `verified_customer_id(org, phone)` (for ToolContext.contact["buyer_customer_id"]). Collection `ai_identity`; buyer from `customers` (phone variants 08/628/+628, nik). NIK never logged/returned. 3 wrong -> lock 24h + notification to super_admin/owner (wa_inbound._notify_admins). Unregistered number: False without counting attempts.
- ai/web_research.py: `extra_tools(ctx, conv_id)`, `record(ctx, conv_id, content)`, `has_pii`. agent.py: 3 additive lines (tools + extra_tools per round; record after each response). PII query -> `ai_incidents` + `ai_conversations.web_disabled` (next round has no web tools); queries in `ai_web_queries` (PII query text masked).

## Concerns
- NIK-last-4 instead of OTP (controller ruling): confirm with product owner.
- Wiring (setting ToolContext.verified/contact, calling consent.handle_keyword/mark_noticed on inbound WA) belongs to the Task 10 inbound path; not done here.
- Server tool blocks are stored verbatim in conversations; registry phone masking applies to client tool results only.
- Full suite was flaky once on a shared DB name (other agent likely using the same DB); passes with a unique AI_TEST_DB.
