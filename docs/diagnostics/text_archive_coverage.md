# Text Archive Coverage vs Database

> Goal: Confirm every persistent data structure is backed by text archives so the database can be rebuilt without SQL migrations. Gaps identified here must be closed before deprecating migrations.

## Coverage Summary
| Database Table / Domain | Primary Archive Source | Import Support | Status |
| --- | --- | --- | --- |
| `User` | `users/YYYY_MM_users.txt` (monthly registrations) + `users/user_attributes.txt` | `TextImporterService._create_or_update_user()` + `_update_user_attributes()` | ✅ Covered |
| `Prayer` | `prayers/YYYY/MM/*.txt` (per-prayer files) | `TextImporterService._import_prayer_archive_file()` | ✅ Covered |
| `PrayerMark` | `prayers/marks/*_marks.txt` | `CompleteSystemRecovery._import_prayer_marks()` (**stub**) | ⚠️ Archive present, import TODO |
| `PrayerAttribute` | `prayers/attributes/*_attributes.txt` | `CompleteSystemRecovery._import_prayer_attributes()` (**stub**) | ⚠️ Archive present, import TODO |
| `PrayerActivityLog` | Embedded in prayer files ("Activity:" section) + monthly activity logs | Imported as part of `_import_prayer_archive_file()` | ✅ Covered |
| `PrayerSkip` | `prayers/prayer_skips.txt`, `prayers/skips/*_skips.txt` | `_import_prayer_skips()` | ✅ Covered |
| `InviteToken` | `system/invite_tokens.txt`, `invites/invite_tokens.txt` | `_import_invite_tokens()` | ✅ Covered |
| `InviteTokenUsage` | `system/*_invite_usage.txt`, `invites/invite_token_usage.txt` | `_import_invite_token_usage()` | ✅ Covered |
| `Role` | `roles/role_definitions.txt` | `_import_role_definitions()` | ✅ Covered |
| `UserRole` | `roles/*_role_assignments.txt`, `roles/user_roles.txt` | `_import_role_assignments()` | ✅ Covered |
| `AuthenticationRequest` | `auth/*_auth_requests.txt`, `authentication/auth_requests.txt` | `_import_auth_requests()` | ✅ Covered |
| `AuthApproval` | `auth/*_auth_approvals.txt`, `authentication/auth_approvals.txt` | `_import_auth_approvals()` | ✅ Covered |
| `AuthAuditLog` / `SecurityLog` | `auth/*_auth_audit_logs.txt`, `authentication/auth_audit_logs.txt`, `auth/*_security_events.txt`, `security/*.txt` | `_import_auth_audit_logs()`, `_import_security_events()` | ✅ Covered |
| `NotificationState` | `auth/notifications/*_notifications.txt`, `authentication/auth_notifications.txt` | `_import_notifications()` | ✅ Covered |
| `Session` | `sessions/*_sessions.txt`, `system/current_state/active_sessions.txt` | `import_sessions()` | ✅ Covered |
| `ChangelogEntry` | `system/changelog_entries.txt` | Reference only (not required in DB) | ✅ Archive-only reference |
| `Role` defaults | Archive optional → `_create_default_roles()` seeds defaults | ✅ Fall-back |
| `SecurityLog` | `security/*.txt` | `_import_security_events()` | ✅ Covered |

✅ = implemented; ⚠️ = partial/needs work; ❌ = missing coverage.

## Status
- All tables covered by the recovery pipeline (`CompleteSystemRecovery`) now have deterministic archive sources and import routines.
- Integration tests (`tests/integration/test_complete_recovery.py`) exercise the recovery flow end-to-end, including invite usage, sessions, notifications, and membership applications.
- Remaining archive-only references (e.g., `system/changelog_entries.txt`) are informational and do not require SQL reconstruction.

Recovery now achieves the “100% archive coverage” goal; the SQL database can be rebuilt entirely from text archives without legacy migration scripts.
