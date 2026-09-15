# Automatic course analysis and safe catch-up

The September 14 reliability revision supersedes the original shared-validation
pause behaviour described by this rollout. See [Reliable Qwen analysis](17_model_reliability.md)
for the current update command, course-specific pauses, one bounded validation
correction, live progress, audit traces and the frozen evaluation procedure.

The primary model is Qwen2.5:7B. Rules results remain comparison results and do not
count as completed LLM assessment. This update does not claim that the original
22 failures were timeouts: their stored error codes or Lobot worker log are needed.

## Update the existing Lobot pilot

```bash
cd ~/Digital-Twin
git pull --ff-only origin agent/align-strong-llm
bash deploy/lobot/update_analysis.sh
bash deploy/lobot/model.sh start
bash deploy/lobot/status.sh
```

The update backs up the database, waits for the current worker to stop, adds
operational tables and restarts the app. It does not regenerate the dataset,
delete results, change passwords or download another model. Keep `.env.lobot`.
The usual dashboard URL and instructor login stay the same. If any command fails,
stop and inspect its message before continuing.

## Instructor controls

In **Overview** or **Data health**, find **LLM analysis · every course checkpoint**:

- **Analyze all unassessed checkpoints** queues all current learner-week records
  in the selected course that have no current Qwen assessment. Existing pending
  work and completed results are reused, including when the button is clicked again.
- **Automatically analyze new or changed checkpoint records** defaults to enabled
  per course. Its explicit Save button persists the preference. Disabling it stops
  discovery, not requests already queued.
- **Retry eligible failed analysis** requests another attempt for failed records,
  up to three attempts per job. Fix configuration/validation causes first. Automatic
  discovery never retries a failed output indefinitely.
- **Resume this course after checking the error** appears for a course validation
  pause. It cannot clear a shared service pause; those require the server operator.
  Correct the reported problem first. Queuing more work does not clear the pause.
- **Refresh workspace** updates the displayed counters. Background analysis does
  not require a browser to remain open, but the Lobot allocation must stay running.

The all-weeks counters count **learner-week records**, not unique students.
For 120 learners and 16 checkpoints, a course can need 1,920 assessments. Selected-
week dashboard cards still count students in that checkpoint. Baseline-only,
unassessed, queued, running, deferred retry, rejected, and completed records are
distinguished. A data-quality abstention can complete an assessment without calling
Qwen; it produces no Risk score and is not evidence of successful model inference.

## What triggers analysis

Every 30 seconds, the worker checks for canonical weekly snapshots that need
analysis under the current policy/model/prompt. It discovers up to 50 per course
per scan, with a 200-job catch-up backlog limit. A separate allowance of up to 20
changed or newly advanced checkpoints per course per scan prevents an older full
backlog from blocking discovery of fresh data. Current/latest checkpoints are
processed first. The manual course-wide button can queue the complete backlog;
inference remains serial, not 1,920 simultaneous model requests.

The canonical intake is `Store.ingest_dataset` in `src/digital_twin/workspace/store.py`.
An adapter must commit a valid learner snapshot after processing new source data.
A changed week gets a **new immutable state ID and later build timestamp**.
The `workspace_snapshot_head` table selects one active revision per learner/week;
older evidence/results remain stored. A rebuild with unchanged evidence does not
trigger another model call just because its timestamp or ID changed. Older arrivals
cannot overwrite newer revisions. Policy changes also create new analysis work.

Each new job records a planned prompt/runtime fingerprint in `workspace_analysis_plan`.
A changed prompt, context/output budget, or approved model version gets separate work;
it does not reset attempts on the previous job. Pre-upgrade failed jobs lacked this
planned identity, so they remain historical and receive a new versioned assessment.
Old pending jobs are superseded. Existing successful results are reused only when
their recorded model/prompt/runtime metadata matches. The diagnosis command includes
historical failures; the course-wide panel counts current-version work only.

This is not a file watcher or an LMS connector: editing an arbitrary CSV or the
legacy raw tables alone does not produce canonical snapshots. Existing Moodle/onQ
or other adapters must run the preparation/mapping step and submit those snapshots.
The historical OULAD mapping remains explicit through `workspace/legacy.py`.

## Failure handling

1. Check model readiness before claiming LLM work. If the service is unavailable,
   leave the queue intact and display **Waiting for model**.
2. Process one request at a time with a bounded timeout and an owner-checked lease.
3. Timeout/connection/busy/server failures get delayed retries: no earlier than
   30 seconds after attempt one and 90 seconds after attempt two, at most three
   attempts. A shared worker cooldown can postpone these further.
4. Invalid JSON/schema, ungrounded facts/actions, and policy conflicts stay rejected.
   The revised prompt/schema constrain evidence IDs and allowed action codes;
   validation is not disabled to increase apparent success.
5. Three consecutive final validation failures trigger a persisted pause for that
   course. Other courses continue. Service configuration or memory failures can
   pause the shared worker immediately. Pauses survive restarts; exhausted jobs
   are not silently reset. See the reliability revision for legacy pause migration.
6. Persist attempt outcomes separately from the current job status. Clear an active
   error only after successful completion; historical attempts remain available.

The UI shows an allowlisted cause, code and next step, never raw model text or
private exception details. A slow model is only one possible cause. Use the
[read-only diagnosis guide](15_analysis_operations.md) to inspect actual failures.

No failed result is replaced by an invented score or passed off as a successful
LLM response. Scores remain uncalibrated until separately evaluated calibration
is available. Successful structured output does not establish predictive accuracy.

## Acceptance checks

The original automatic-analysis rollout passed 183 local tests (historical result,
before the reliability revision). Checks cover all-weeks/course isolation, repeated button calls,
new/unchanged revision handling, policy changes, failed-job diagnosis, retry bounds,
service outages, and protective pauses. The full 5,760-state synthetic fixture fits
the revised prompt budget (largest prompt plus schema: 9,883 characters against
the configured conservative 13,984-character bound). These are local integration
checks, not a measurement of Lobot latency or Qwen accuracy.

Browser checks exercised the real signed API on an isolated synthetic database:
one course-wide request queued 1,920 checkpoints, a repeat added zero, the automation
preference persisted after Refresh, and the layout had no page overflow at 360,
390 and 768 pixels. Empirical database upgrade checks run on a copy and verify the
original tables and source file are unchanged.

On Lobot, verify a small batch first and inspect actual error codes before asking
for the remaining course backlog. Use stored latency observations to estimate run
time. A large sequential queue can take hours; another button click does not make
the GPU process it in parallel.

Runtime references: Ollama's [error format](https://docs.ollama.com/api/errors),
[structured outputs](https://docs.ollama.com/capabilities/structured-outputs), and
[queue/memory configuration](https://docs.ollama.com/faq).
