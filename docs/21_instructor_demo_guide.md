# Instructor demonstration guide

Use **Course operations**, then **Foundations of Computing · updated demo v2**.
The Overview's **Synthetic scenario guide** opens prepared fictional examples.
It changes only navigation, not records, scores, queue state or settings. Labels
describe scenario design; they are never inputs to the model or accuracy claims.

| Example | Learner ID suffix / week | What to inspect |
|---|---|---|
| Quiet activity, strong assessed grades | `1:0003` / 6 | Published grades and required work alongside quiet activity. Mainly offline policy excludes login activity, not academic concerns. |
| Practice versus assessed work | `1:0001` / 6 | Academic progress separates practice marks and optional resources from assessed grades and due required work. |
| Approved extension | `1:0006` / 4 | The effective deadline includes the approved extension known by that checkpoint. Not-yet-due extended work is not a missed assessment. |
| Support and later progress | `1:0008` / 8 | Support history retains action dates, evidence cutoff and recorded time. Compare earlier weeks without inferring causation. |
| Manual attention and later contact | `1:0002` / 3 | Existing hosted demo: flagged, watchlisted, high manual priority; planned contact on day 30, completed on day 32, citing week 3 evidence. No real message was sent. |

The same first four examples are available in the other updated demo courses
with ID prefixes `2:` or `3:`. Only available checkpoints are offered. The normal
authorized API checks that a selected learner exists; no new roster entry is invented.

## Missing or stale feeds: a separate controlled test

Do not damage the complete cohort to demonstrate a fault. The existing
`degrade_snapshot` function in `src/digital_twin/workspace/features.py` creates
isolated variants, leaving the original immutable snapshot unchanged.

- `missing_grades`: grade evidence is unavailable, not a zero mark. Other valid
  evidence may still support an assessment; missing one field does not always
  require abstention.
- `partial_activity` / `stale_activity`: essential evidence quality is inadequate;
  the current gate abstains before inference and publishes no risk score.
- Assertions also cover unavailable practice grades, cutoff-safe publication,
  extensions and disabled inactivity. They are reliability tests, not accuracy.

Phase 1 already ran these variants against the hosted configuration: 11 isolated
cases, 9 validated actual-Qwen results, 2 pre-inference abstentions, no final failures.
See `docs/20_dashboard_upgrade_progress.md` for dated evidence and limitations.
The ignored operator harness is `tests/lobot_phase1_live_gate.py`; results are
`artifacts/dashboard-upgrade-phase1/hosted-live-results.json`. These faults are
not presented as missing feeds in the normal complete-course dashboard.

## Refresh, analyze and retry are different actions

- **Refresh workspace** reads saved records. It does not import new LMS data or
  rerun the model. Other open profiles do not silently become a new checkpoint.
- **Queue student/checkpoint analysis** applies only to the displayed week.
- **Analyze all unassessed checkpoints** applies to all prepared course weeks;
  matching saved results and pending jobs are reused.
- **Retry eligible failed analysis** applies only within the attempt limit.
  Diagnose first; retry does not fix an invalid contract or clear protective pauses.
- Automatic discovery can queue new/changed evidence when enabled. Existing queued
  work can still finish after discovery is disabled. Model readiness, worker health,
  source freshness and analysis completion are distinct.

Risk scores remain uncalibrated 0–100 outputs, not failure probabilities. Validation
checks structure and evidence; comparative predictive accuracy needs separate study.
