# Unified TEAM staging baseline

- TEAM base: 5e9144e07a74bde0a2c73cc2367a46d6caba0cee
- Worktree: G:\Queen's\Graduation Project\Digital-Twin-final-unified
- Branch: integration/final-team-runtime
- Staging PostgreSQL: container digital-twin-unified-staging-postgres, database digital_twin_unified_staging, volume digital-twin-unified-staging-data, host port 55435.
- Backup source: Digital-Twin-runtime-final/var/backups/production_pre_team_sync_20261002_170419.sql
- Production ports/container/database were not changed.

## Migration

The restored backup reported revision 20260924_0006. TEAM migration 20260929_0007 was applied only to staging and completed successfully. It creates audit.workspace_triage and audit.workspace_triage_event; initial triage rows are correctly zero. The restore emitted non-fatal ownership warnings for the unavailable digital_twin role; restored tables and rows were verified as the postgres owner.

## Invariants

Before and after migration:

- learners: 383
- enrolments: 383
- source observations: 152046
- weekly states: 1464
- predictions: 1464
- historical alerts: 142
- preserved case: case:a49697dfb12b4c30939ae442734c534f, learner oulad:101781, status new_concern
- preserved support actions: 1

The raw prediction table contains 142 high, 75 medium, and 1247 low rows; these are historical prediction rows and must not be reported as the current dashboard distribution (72/26/274/11), which is derived by the API current-state/alert eligibility logic.

## Backend checks

- TEAM API started against staging on port 8002.
- /health/ready returned 200 with service course-digital-twin-api, backend postgresql, revision 20260929_0007.
- TEAM test suite: 66 passed, 2 dependency deprecation warnings.
- No Qwen/Ollama inference was run.
- Static inspection confirms prediction records retain state_id; learner detail and workspace paths use state-bound prediction/evidence data. No independent latest-state/latest-prediction fallback was introduced.

Authenticated endpoint smoke coverage still requires a signed staging identity request; production remains untouched.

## Porting decision

TEAM already equivalent: workspace UI/client/API, state builder, support workflow, immutable prediction/evidence persistence, course authorization, and audit structures.

Port required: empirical runtime verification of API-derived current risk distribution (72/26/274/11) and launcher/environment settings from runtime-final. These should be ported as targeted tests/configuration, never by copying the runtime API wholesale.

Do not port: old duplicated APIs, production data/volumes, E1/E2/E4 artifacts, or any Qwen result into the empirical predictor path.
