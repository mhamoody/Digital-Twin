# React workspace migration

## Branch and boundaries

Work branch: `reactvite`, created from `origin/agent/align-strong-llm` at
`5e9144e07a74bde0a2c73cc2367a46d6caba0cee`. The Lobot branch and live services
remain unchanged. Existing unrelated document edits are preserved.

React + TypeScript + Vite replaces the presentation layer, not the prediction
pipeline. FastAPI, course authorization, evidence cutoffs, missingness,
validation, analysis jobs, policies and audited support records remain the
sources of truth. Streamlit remains the operational fallback until parity and
hosted acceptance pass. No claims of LTI/onQ integration are added by this work.

## Design direction

Combine the teammate's TwinClass reference (warm white, deep teal navigation,
soft accent cards, generous space) with the tested Focus review workflow.
Use readable text rather than the reference's very small labels. No decorative
student rankings, invented engagement percentages or fake controls.

Navigation: Overview, Students, Support cases, Course settings, Data & model.
A student opens a dedicated profile with Evidence, Academic progress, Risk
history and Support record. Course, checkpoint and identity mode remain visible.
Tables scroll locally on small screens; primary actions and labels never clip.

## Phases and acceptance gates

1. **Secure foundation and read-only vertical slice.** New tracked `frontend/`;
   same-origin browser sessions; course/checkpoint selection; overview, paginated
   roster and evidence profile using real API contracts. Check type/build,
   revoked-account and cross-course access, CSRF, API errors, request races,
   mobile/keyboard layout. Preview only on isolated synthetic data.
2. **Instructor workflow parity.** Flag/watchlist/priority, full academic and
   risk history, case actions, planned/completed/cancelled entries, resources,
   explicit follow-up resolution, observed before/after comparison. Preserve
   idempotency and optimistic concurrency; no automatic student communication.
3. **Policies and analysis operations.** All learning modes, inactivity settings,
   teaching days/breaks, policy revisions, auto-analysis, all-week queue/retry,
   model/worker/course pause and diagnostics, provenance, demonstration guide.
   Distinguish invalid, abstained, stale, pending and historical results.
4. **Parity and usability gate.** Check every feature below against Streamlit,
   accessibility, keyboard, 320/390/768/1440px reflow, API failure handling,
   conflicts and missing/late data. Never turn missing evidence into zero.
5. **Deployment candidate.** Single-origin static hosting on Lobot proxy path,
   installation/start/status/rollback instructions and verified hosted sign-in.
   Deploy only after local parity passes and coordination with the instructor;
   do not interrupt active inference or replace the hosted UI during foundation.

Each phase records files, checks, limitations and the next exact task in
`planning/react_migration_handoff.md` (local). This document is the tracked plan.

## Feature parity checklist

- Authentication, logout, account revocation, explicit course grants; no browser
  HMAC key, trusted instructor headers or local-storage bearer tokens.
- Course names/IDs, source label, checkpoint/cutoff, authorized name + ID / ID-only
  mode (including server-side search and response redaction), refresh semantics.
- Whole-course enrolled/review/high/insufficient/active-case counts; overlapping
  workload counts versus mutually exclusive support levels; same count scale
  for current levels and checkpoint change; models and valid comparisons explicit.
- Server-side search, pagination, sort, band/status/priority/attention filters,
  flags, watchlists, due follow-ups and active cases; preserve navigation context.
- Profile evidence citations and source IDs, availability/coverage/freshness,
  validation provenance and historical-result warnings; baseline comparison.
- Academic grades, assessment/practice distinction, publication and extension
  cutoffs, due/required resource denominator, resources and activity timelines.
- Risk history with gaps and model/policy boundaries; risk score /100 is not
  calibrated probability. Manual instructor judgments never change scores.
- Current support history across historical checkpoints, idempotent actions,
  version conflicts, explicit ongoing status, planned-action completion or
  cancellation, resources and follow-ups, noncausal before/after comparisons.
- Course policy presets and custom values, monitoring off, teaching-day calendar,
  break ranges, corroboration and grade threshold; old assessments retained and
  labelled outdated, never silently reused under a new policy.
- Single learner/checkpoint and course-wide analysis; automation, retries and
  paused-course resume safeguards; model readiness, worker state, safe error
  samples and remediation; no unsafe scores published on model rejection.
- Scenario guide and explicit separation of legacy support history (v1) from
  course operations (v2); do not merge or hide legacy records without a decision.

## Status

Phase 1 implemented locally: tracked React frontend, opt-in server sessions,
same-origin static hosting, real API read views and responsive page structure.

Checks: TypeScript + Vite production build; 24 focused Python checks (including
legacy signed-client compatibility and simulated proxy-prefix/cookie routing);
ten browser workflow checks at 320/390/768/1440px; zero browser JavaScript
errors or external requests; npm audit reported no vulnerabilities at this gate.
Evidence: `artifacts/react-migration/browser-checks.json` and screenshots (local).
The isolated preview uses synthetic records with the temporary rules baseline;
no Qwen inferences or live data changes were made for this gate.

Phase 2 implemented locally: instructor flags/watchlists/priority, manual
concerns, ongoing cases, planned/completed/cancelled support actions, resource
links, explicit follow-up scheduling/clearing, current history and observed
before/after evidence. Updates retain server-side course authorization, CSRF,
expected case/triage versions, expected evidence snapshot and idempotency keys.
An uncertain save freezes its payload; only an explicit exact retry is allowed.
Conflicts retain the draft for review and never silently overwrite another edit.

Academic views separate published assessed marks from practice/unclassified
work, show required-due resource completion and recorded activity, and preserve
raw records. Risk history retains exact values and breaks lines at gaps or
incompatible provenance. Explicitly uncalibrated or rules-only metadata can
match; missing metadata cannot. Snapshot history now includes feature version,
cutoff and evidence semantics so before/after deltas cannot mix incompatible
grade or completion definitions. Such changes remain observations, not causal
proof of intervention benefit.

Validation on 2026-10-04: 37 focused Python tests passed; production TypeScript/
Vite build passed; npm audit reported zero vulnerabilities. The 10 foundation
browser scenarios, 7 instructor-save scenarios and 4 edge-case browser scenarios
passed, with no JavaScript errors. Instructor-save checks exercise actual synthetic-preview writes,
including an intentionally lost successful response. Ten deterministic
component-check groups cover academic, risk and intervention-comparison
semantics. These are integration/UX checks, not LLM accuracy evaluations.

Additional Phase 2 gates: real browser saves, lost-success-response replay with
exactly one event, version-conflict blocking, explicit closure/follow-up handling,
draft navigation/focus, older-checkpoint resource selection, future-action
blocking and academic/editor mobile layouts. Local screenshots and machine-
readable check results are under `artifacts/react-migration/`. No live model,
real course or hosted database was changed.

Full Streamlit parity and hosted React deployment are **not** complete. Next:
Phase 3 course policies and analysis controls, then the full parity/usability
gate before parallel Lobot deployment. Do not replace the operational UI yet.
See `frontend/README.md` for running the preview and pilot session limits.
