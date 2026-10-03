# Comparison evaluation status

## COMPLETED RESULT

None yet. No predictive or grounding result is claimed.

## PIPELINE VALIDATION

- E4 temporal exporter/runner: implemented, awaiting canonical OULAD state export.
- E1 Logistic Regression: runner contract defined, awaiting frozen canonical states/labels and train/validation/test split.

## READY — BLOCKED BY MODEL ACCESS

- E2 grounding protocol: held-out manifest frozen; Qwen adapter fails clearly when research runtime is unavailable.

## PRELIMINARY DEVELOPMENT RESULT

Historical development-only grounding result: 17/24 before evidence-first and 24/24 after evidence-first. This is not held-out evaluation and is not combined with future metrics.

## NOT YET EXECUTED

E2 held-out inference, E3 missingness, E5 course policy, E6 workflow, and E7 efficiency.

## Milestone execution audit (2026-10-03)

- Disposable PostgreSQL restore verified migration `20260924_0006` and counts: 383 learners, 1464 states, 1464 predictions, 142 alerts.
- E4 is **BLOCKED — missing canonical source timestamps**. `analytics.weekly_feature` has provenance references and counts but no feature-level source time; no valid temporal violation count can be asserted.
- E1 is **BLOCKED — missing evaluation labels**. `core.enrolment` contains registration/unregistration fields but no `final_result`; no Logistic Regression result was generated.
- No production database or runtime was queried or modified.
