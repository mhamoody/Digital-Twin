# Manual-Review Items

Phase-2 cleanup intentionally left these 12 entries untouched. This document lists only safe paths/categories; it does not expose configuration or credential values.

| Path | Category | Retention reason | Required review before action |
|---|---|---|---|
| `.env` | Sensitive runtime configuration | May contain environment-specific secrets and endpoints | Secret inventory, replacement/rotation plan, runtime dependency review |
| `.vscode/settings.json` | Local editor configuration | May contain machine-specific paths/settings | Owner review |
| `var/auth/course_grants.local.json` | Sensitive authorization configuration | Active/local course grants may depend on it | Auth/runtime owner review; never print contents |
| `var/auth/instructors.before-lobot-sync.json` | Sensitive historical authentication state | Retains audit/rollback context | Security and retention review |
| `var/auth/instructors.json` | Sensitive authentication state | May be required by the current pilot profile | Security/runtime review; never expose hashes or secrets |
| `frontend/dist/assets/index-COlY1TKi.js` | Generated frontend build | Runtime/build provenance not separately revalidated | Clean build plus runtime parity check |
| `frontend/dist/assets/index-DHiuwNKM.css` | Generated frontend build | Same preserved bundle | Clean build plus visual/runtime parity check |
| `frontend/dist/favicon.svg` | Generated frontend build | Same preserved bundle | Clean build plus asset check |
| `frontend/dist/index.html` | Generated frontend build | Same preserved bundle | Clean build plus serving-path check |
| `var/data/digital_twin.sqlite3` | Development SQLite database | Retained development/application state; disposition not approved | Read-only provenance and dependency review |
| `var/data/digital_twin_demo.sqlite3` | Demo SQLite database | Retained demo state and preservation copy | Demo/runtime dependency review |
| `var/data/digital_twin_demo_pre_migration.sqlite3` | Pre-migration SQLite database | Historical migration/rollback evidence; removal not approved | Schema/provenance comparison and archival decision |

The 12 entries total 281,708,633 bytes. The four `frontend/dist` files total 516,134 bytes.

## Separate protected database

`var/data/lobot_workspace_20261011_165135.sqlite3` is not a discretionary manual-review target. It is classified as a critical restricted operational evidence source and has a byte-identical verified preservation copy. Do not mutate, publish, or remove it.

## Decision rule

No item above should be deleted, moved, printed, committed, or published merely because cleanup completed. Each requires a separate, narrow review and explicit authorization. The authoritative cleanup record is `repo_cleanup_audit/phase2_execution/remaining_manual_review.md`.

