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

Phase 3 implemented locally: full course-policy editor with six teaching-style
starting points, configurable inactivity/corroboration/grade settings, teaching
weekdays, break ranges and revision-aware saves. Presets change the draft only.
Policy changes preserve old assessments and require reassessment under the new
revision. Blank or invalid values are not silently replaced by zero.

Model operations include per-learner/per-week/all-week queueing, explicit failed
job retries, versioned auto-discovery settings and course-only resume requests.
Queue actions preserve server-side reuse, retry limits and protective pauses.
Unlike idempotent support entries, uncertain policy/automation/resume responses
freeze and require a saved-state check, not a blind repeat of the request.

Course-wide progress polls sequentially every ten seconds while visible. The
interface separates student counts from student-checkpoint counts, queued jobs
from completed results, model availability from successful inference, and a
course resume request from worker acknowledgement. A shared-service pause is
not cleared by a course resume. Read failures hide unconfirmed progress counts.
Background polling does not discard an open confirmation or uncertainty dialog.

Provenance shows current versus historical results, model identity, pre-inference
quality abstention, first-pass validation, bounded model correction and audited
format normalization. Failure samples show bounded, server-sanitized field
diagnostics, not raw model replies. The synthetic scenario guide checks that the
actual learner/checkpoint exists before opening it and never queues analysis.

Phase 3 verification: production build and 94 focused Python tests passed; npm
audit reported zero vulnerabilities. Five policy and fifteen provenance/guide/
operations semantic-check groups passed, alongside the ten earlier academic
groups. The earlier 10 foundation, 7 instructor-action and 4 edge-case browser
checks passed again. All twelve new browser check groups passed with no
JavaScript errors. They exercise real isolated policy and
automation saves, lost successful responses, queue deduplication, polling,
safe diagnostics and narrow-screen forms. A policy-table min-content overflow
found at 320px was fixed so scrolling stays within the table, not the editor.

No model or backend prediction change was made in Phase 3. The local queue test
uses 240 synthetic student-checkpoint records with no inference worker running.
Failure/pause states are controlled HTTP fixtures; these checks do not establish
live Qwen accuracy, hosted operation or recovery from a real model incident.

Phase 4 closes remaining current-workspace gaps: independent due/active filters,
list-context resets and pagination recovery, no invalid cutoff for empty courses,
profile error remediation/evidence limitations, and higher precision history
with the exact stored risk score available. Authenticated legacy discovery uses
actual v1 presentations within current grants, not v2 course IDs or prefixes.
Earlier support episodes and audit history are readable separately; old edits,
alerts and activity intentionally remain in the explicitly linked Streamlit
Student support workflow. No history is silently merged or retired.

Seven new read-only browser groups cover those list/empty/legacy behaviors,
including closed episodes, wrong-course rejection, escaped notes and 320–1440px
reflow. Three legacy discovery API tests cover authorization, grant changes and
outages. This is a practical pilot gate, not complete accessibility certification.

Phase 5 uses a separate source worktree and loopback 8502 API/static process,
sharing existing data/auth/model configuration without restarting the original
services or starting another worker. Deployment and rollback steps are in
`docs/23_react_lobot.md`. Hosted verification is recorded separately after the
actual rollout; do not describe local checks as hosted or live-model results.
See `frontend/README.md` for running the preview and pilot session limits.

## Phase 5 hosted acceptance (5 October 2026)

React is deployed at `/user/group-digi2026-g12/proxy/8502/` from application
commit `21c347ed1d73d9cfef45d089fc20e19aeeb2e7ab`. The existing Streamlit/API/worker
checkout remains on `agent/align-strong-llm` at `82a1b81`, with the same running
processes and database. Release integrity was verified before installation.

Fifteen hosted read-only check groups passed after actual instructor sign-in:
authorized courses, release identity, overview, roster and student evidence,
academic/score/support history, policy-editor open/cancel, model progress,
earlier history, and mobile navigation. Layout checks covered 320, 390, 768 and
1440px widths. No JavaScript errors and no modifying requests occurred during
these checks. Authenticated API responses retain `Cache-Control: no-store`
and CSP through the HTTPS proxy. Local save/conflict/retry tests remain the
evidence for modifying workflows; real instructor records were not changed
merely to demonstrate a save. This is not full accessibility certification.

Deployment exposed and fixed a pre-exec process-identity race, missing Python
pidfd wrappers in Lobot's Conda build, and a TIME_WAIT restart-probe false alarm.
Eight deployment/release tests pass; glibc pidfds preserve identity-safe stop.
Previous frontend bundles were retained for rollback, not deleted.

Qwen2.5:7b reported ready, the original worker was idle, and saved real inference
metadata used prompt `course-risk-qwen-v3.3`. This rollout did not run new
inference or evaluate accuracy. Twelve existing failed analysis jobs remain
unchanged: CS110 original (7), CS110 v2 (4), ED220 original (1). They are not
hidden or counted as completed LLM analysis. ED220 v2 has 1,920 validated saved
checkpoints; these are synthetic demonstration records, not accuracy results.

Local ignored evidence: `artifacts/react-migration/hosted-checks.json`,
`hosted-operator-check.txt` and hosted screenshots. Instructor review is next;
Streamlit remains the operational fallback and the editor for earlier v1 cases.

## Final parity candidate (8 October 2026)

The new source closes the earlier v1 editing/activity gap: authorized roster,
learner activity/evidence and prediction timelines, all historical alerts (not
only the latest or case-linked ones), case creation/reuse, notes, transitions,
explicit UTC follow-up scheduling/clearing, alert attachment and review. Earlier
episodes stay separate from current v2 cases. No student communication is sent.
Complete learner episode lookup reads every matching page and rejects changing,
duplicate or wrongly scoped page responses instead of showing partial history.

Case actions retain body idempotency keys; alert reviews retain header keys.
Unknown save outcomes freeze the exact request; explicit retry cannot create a
second action. Conflicts preserve the draft and do not overwrite another edit.
Closed episodes remain terminal. Notes are escaped and ID-only screens warn
that free-text instructor notes may contain identifying information.

A real temporary-SQLite API check exposed a pre-existing linked-alert timestamp
serialization error. The v1 support-case response now restores UTC metadata
when SQLite returns a naive stored UTC timestamp, matching its existing
case/action serialization. No stored timestamp or schema is changed.

Profile navigation now survives Refresh data, checkpoint changes and privacy
changes while evidence is still cleared/reloaded. An API outage removes stale
data and provides an explicit retry. Gateway HTML/malformed JSON is shown as a
safe actionable error, never raw returned content; API redirects are refused.

The real hosted v2 support-note save on October 7 succeeded on one previously
untouched synthetic ED220 v2 learner. It recorded a labelled test note, resolved
the case, scheduled no follow-up and left snapshot/model data unchanged. The
post-refresh check exposed the navigation issue above; the final persistence
and cross-checkpoint browser gate must still be completed after deployment.

The paired isolated model diagnostic is complete: on twelve saved synthetic
failures, deployed v3.3 produced five accepted/seven rejected results; candidate
v3.4 produced eight first-pass plus two corrected accepted results/two rejected.
Both runs also passed 24 model-generated frozen controls and 24 separate
pre-inference quality abstentions. This measures operational consistency, not
predictive accuracy. The candidate remains uncommitted and excluded from the
release. No original failed jobs, saved scores or prompt identities are changed;
no global reanalysis or validator relaxation is performed.

Local and hosted gate evidence is recorded in the resume checkpoint and ignored
`artifacts/react-migration/`; this section does not claim the new release is
already hosted. The October 5 deployment above remains the last verified live
release until the final hosted gate is recorded.

Local acceptance: production build/typecheck and npm audit (zero findings),
14 legacy browser groups, 6 navigation/gateway groups, plus the existing
foundation 10, instructor-action 7, edge 4, model-operation 12 and parity 7
groups passed with no JavaScript errors. Thirty deterministic component groups
cover academic, policy and provenance semantics. Sixty-six focused legacy,
support and browser-auth API tests passed, including real idempotency, conflict,
linked-alert UTC and grant-revocation checks against temporary SQLite.
Legacy browser POSTs are intercepted fixtures; the new API tests perform real
writes only in a temporary test database. They are not hosted mutation tests.
Eight older `test_phase4_api.py` cases lack explicit course grants and fail
under current authorization; these obsolete fixtures are not included in the
passing count, and production authorization was not relaxed to satisfy them.

## Final hosted dashboard acceptance (8 October 2026)

The candidate above is now deployed and verified at
`https://lobot.cs.queensu.ca/user/group-digi2026-g12/proxy/8502/`.
Application commit: `30db8351d11049b09ae20170dafadbf8d0dcb5fc`, merging the tested
frontend changes with the team's newer commits on `reactvite`. Release SHA-256:
`12a1f7c7297a3c73d66d3924a5d2407713601a0977e4b8ef10e8c8dcb4b8e491`.

Fifteen hosted read-only groups passed again on this exact release, plus five
new earlier-workspace groups: original roster/alerts, real learner evidence and
activity, case-editor open/cancel, historical alert review open/cancel, and
responsive expanded evidence. Widths 320/390/768/1440px were checked. No browser
JavaScript errors or modifying requests occurred in those two check suites.
Earlier v1 edits are now available in React, not only in Streamlit.

The already-saved October 7 synthetic support note was read back without another
write. Exactly one event remains; the resolved case and note persist across
refresh and checkpoint changes (weeks 8 and 16), with the Support record section
retained. Its learner snapshot and model assessment are unchanged. No real
student was contacted or given an intervention by this acceptance exercise.

The original API, Streamlit and worker were found stopped after the environment
changed. They were restored only after verifying no live duplicate worker,
no queued/running historical jobs, no unassessed current checkpoints and the
unchanged approved Qwen runtime. All three HTTP services returned readiness
200; exactly one worker was running with a fresh idle heartbeat. No model jobs
were retried or newly created by that service restoration.

A private SQLite backup and prior frontend bundle were preserved in
`var/backups/react-final-release-20261008/`. Two-direction SQL comparisons across
all 41 tables found no data changes from deployment. After service restoration,
only `workspace_runtime` changed for the worker heartbeat; all other tables,
source evidence, model jobs/results, support history, accounts and environment
configuration remained unchanged. SQLite integrity was `ok`.

At this dashboard gate the seven courses contained 12,960 current validated
assessments, 12 explicit abstentions and 12 rejected analyses among 12,984
student-checkpoints. These are operational counts, not predictive accuracy.
The existing rejected cases remain an independent model-correction task; this
UI gate does not resolve or conceal them. New model experiments must remain
separate from deployment evidence and must not invalidate approved saved work.

Local ignored evidence: `hosted-checks.json`, `hosted-legacy-final.json`,
`hosted-save-acceptance.json`, `final-deploy-result.json`,
`final-services-restored.json`, `final-service-acceptance.json`, and screenshots
under `artifacts/react-migration/`. This completes the hosted dashboard phase,
not institutional SSO, full accessibility certification, or accuracy validation.

### Bounded correction follow-up; not deployed (8 October 2026)

After the dashboard gate, two isolated correction-stage experiments were run
against the same twelve saved synthetic failures and 48 frozen controls. Both
kept the deployed v3.3 primary request and independent validator unchanged.
Neither changed production code, saved analyses, queue states or learner data.

| Correction candidate | Twelve known-failure cases | Frozen controls |
| --- | --- | --- |
| Shorter evidence-focused recheck | 6 first-pass accepted; 6 rejected | 24 first-pass accepted; 24 pre-inference quality abstentions |
| Directional examples explaining non-success risk | 7 first-pass accepted; 3 correction-stage accepted; 2 rejected | 24 first-pass accepted; 24 pre-inference quality abstentions |

The final two rejections remain academic-corroboration policy conflicts. The
other inspected failures include elevated scores citing only protective facts;
this is not missing JSON fields or a general missing-data problem. The validator
appropriately withheld unsupported scores. No scores were clipped, no concern
claims were invented, and rejected outputs were not recast as model abstentions.

These are development diagnostics on known failures, not held-out accuracy or
proof of perfect reliability. First-pass outcomes varied, and the hosted Ollama
version was 0.40.0; earlier runs cannot establish a controlled causal comparison
across runtime changes. The control abstentions did not call the model and must
not be counted as 48 successful generations. These controls also do not by
themselves validate correction-stage performance on unseen cases.

Neither candidate was promoted: twelve original current failed jobs remain
visible and their scores unpublished. The final report can use the completed
dashboard evidence and these explicitly limited model diagnostics; it must not
claim that all model edge cases were solved. Any later correction-stage rollout
needs its own version/request hashes and comparison safeguards while preserving
approved primary v3.3 results, rather than triggering a whole-dataset reanalysis.
Ignored artifacts: `compact-recheck-summary.json`, `directional-recheck-summary.json`
and their matching `*-results.jsonl` files in `artifacts/react-migration/`.
