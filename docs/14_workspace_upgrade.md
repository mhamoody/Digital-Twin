# Instructor workspace upgrade and demonstration

This release adds an LMS-neutral instructor workspace and a private Qwen inference
worker. It does not connect to onQ or send messages to students. Lobot remains the
hosting location; Ollama runs the model inside that allocation.

## Upgrade the existing Lobot installation

Run in the Lobot terminal, not Windows PowerShell. Keep the existing `.env.lobot`,
database and account file. Do not copy the example over your working configuration.

```bash
cd ~/Digital-Twin
git pull --ff-only origin agent/align-strong-llm
bash deploy/lobot/upgrade_workspace.sh mohamed
bash deploy/lobot/model.sh install
bash deploy/lobot/start.sh
bash deploy/lobot/status.sh
```

The upgrade backs up the configured database, stops the application, adds the new
tables, maps archived prepared states without changing their original records,
generates fictional courses, grants those courses to the named existing account,
and computes explicitly labelled comparison baselines. Preparation may take several
minutes; progress is printed every 500 completed comparison jobs. Re-running uses
stable record/job IDs and does not replace existing empirical observations.

`model.sh install` reuses an installed Ollama binary or downloads an official Linux
release into ignored `var/tools`. It uses no sudo, Docker or GPU-driver installation.
An available publisher archive digest is checked; the release and downloaded hash
are recorded. The model weights stay outside Git. The approved model digest is
saved in `var/models/predictor.json` and pinned when starting the application.
An already-running Ollama service is reused without changing its configuration;
its operator should confirm local-only mode and its storage path.

The application, worker and model runtime have separate readiness states. A
healthy database does not prove that inference succeeded. To verify a real model
response after installation:

```bash
source .venv/bin/activate
set -a
source .env.lobot
set +a
python scripts/check_hosted_workspace.py --llm
```

The report contains a synthetic example, the actual model digest, validation
results and latency. It does not include account passwords or signing keys.
This check does not insert a demonstration result under a false model identity.
Use the dashboard's analysis button to queue and persist instructor-visible results.

Open the existing protected route:

`https://lobot.cs.queensu.ca/user/group-digi2026-g12/proxy/8501/`

Use the same instructor account. Outer JupyterHub access is still required.
Closing a browser does not stop inference; stopping/culling the allocation does.
For subsequent restarts:

```bash
bash deploy/lobot/model.sh start
bash deploy/lobot/start.sh
```

If a process is already running, use `status.sh` first. For a controlled restart,
run `stop.sh`, then the two start commands. A busy worker can take up to its bounded
inference timeout to finish; if stop reports it is still finishing, retry before
upgrading. `stop.sh` leaves the model service alone; `model.sh stop` stops only a
model process recorded by this project's launcher.

## What to inspect with the supervisor

1. Select **Foundations of Computing**, week 8. The five cards explain enrolled,
   needs review, high attention, insufficient evidence and ongoing support. Counts
   overlap; the support-level chart is the mutually exclusive breakdown.
2. Open **Students**. Search a fictional student and open the profile. The profile
   remains tied to that student, independently of saved roster filters.
3. In **Academic progress**, inspect published grades, submission status, activity,
   attendance and evidence availability. Publication dates, not future marks, govern
   what the checkpoint can use. Risk score uses 0–100 points; grades are percentages.
4. Open **Run model analysis**, choose Qwen, and queue this student. Refresh until
   the status is validated, abstained or failed. Initially visible baseline results
   are marked **Temporary rules baseline**. Failures never become invented scores.
5. Inspect each evidence-linked reason and proposed instructor action. Expand the
   same-checkpoint baseline comparison when both results exist. Valid JSON and
   grounded facts do not by themselves prove risk-prediction accuracy.
6. Record a manual concern, contact, warning, support or approved resource in
   **Support history**. Distinguish planned from completed work, select **Ongoing**,
   and schedule a follow-up. Go to a later checkpoint and inspect the history and
   before/after evidence. Improvement is observational, not proof of causation.
7. In **Course settings**, change inactivity warning/escalation days, teaching-day
   basis, breaks or corroboration. A new policy revision is created. Old results
   become historical until rerun; policy/model changes are not displayed as student
   deterioration. Changing settings never rewrites an earlier prediction.
8. Resize to a phone viewport. Cards wrap, layouts stack and wide tables scroll.
   The selected checkpoint's cutoff remains visible outside shortened selectors.

For seeded support cases, the fictional recovery trajectory has completed support
and follow-up events. Names are neutral synthetic student labels, not expected
model answers. The private scenario oracle is stored only in ignored artifacts.

## Data and model scope

The full synthetic demonstration has three courses, 120 fictional learners per
course, 16 checkpoints, 48,773 events, 5,760 states and 33 evidence features with
the default seed. Course styles differ: weekly work, a project course and blended
learning. The dataset includes grades published after submission, extensions,
attendance, resources, forum activity and support histories. Legitimate N/A values
remain N/A. It is a reproducible scenario fixture, not a statistical representation
of a real institution or a source of empirical accuracy claims.

See [the dictionary](12_data_dictionary.md) and [model runtime](13_model_runtime.md).
Existing OULAD states retain their available features; missing grade/calendar
information is not fabricated. The original v1 observations, predictions and alert
reviews remain in their original tables. New support cases use the additive v2
case/event tables; original alert-review rows are not converted into claimed
student-contact actions.

The primary risk adapter uses numeric academic/engagement context and constrained
claim/action selection. It excludes arbitrary forum prose, demographics, names,
final outcomes and hidden scenario labels. Gemma's forum-text interpretation and
fine-tuning remain separately evaluated future work. A frozen empirical calibrator
has not been fitted: displayed Risk scores are not calibrated probabilities.

## Repeatable evaluation

```bash
python scripts/evaluate_workspace.py --limit 24 --output-dir artifacts/workspace/eval-baseline-01
python scripts/evaluate_workspace.py --llm --limit 24 --output-dir artifacts/workspace/eval-qwen-01
```

The second command performs real inference and may take several minutes. It uses
a reserved synthetic seed and complete/missing-grade/partial-activity/stale pairs.
Reports separate attempted cases, actual inference calls, pre-inference abstentions,
schema/evidence validation failures and latency. No numeric target is copied from
the rules baseline. Real-world discrimination, calibration, fairness and intervention
benefit still require separate held-out empirical evaluation.

Choose a fresh output directory for each experiment; the evaluator refuses to
overwrite an existing report. Record the model digest and policy/prompt revisions
when comparing runs.

## Local release validation (13 September 2026)

- 136 automated checks passed, including temporal evidence handling, strict model
  validation, job leases, course authorization and interface interactions.
- A copy of the existing OULAD database imported 383 enrolments and 1,464 states.
  Original table counts and the source file hash remained unchanged; the upgraded
  copy passed SQLite's integrity check. No empirical observations were overwritten.
- The complete synthetic database passed SQLite's integrity check and contained
  5,760 explicitly labelled baseline results, 60 support cases and 120 seeded
  action/follow-up records. Each course's support-level counts reconciled to its
  120 enrolled students. Local overview reads took approximately 0.10–0.14 seconds;
  these are not Lobot performance measurements.
- A reserved-seed baseline check covered 96 complete/missing/stale variants:
  96 schema-valid and grounded results, including 48 pre-inference abstentions.
  There were **zero LLM inference calls** in this check; these figures are not
  Qwen accuracy or raw-output success rates.
- The running API and dashboard were exercised in a Chromium-based browser at
  widths of 1,440, 768, 390 and 360 pixels, with no page-wide overflow or application
  exceptions. Student navigation and completed-action before/after evidence were
  checked in the actual interface. A completed contact was saved through the
  signed API and remained visible after refresh. Wide evidence tables remain
  locally scrollable.
- Python lint checks and Bash syntax checks cover the changed implementation and
  deployment scripts. PostgreSQL migration SQL is provided, but this release's
  runtime verification used SQLite, matching the existing Lobot pilot.
- A clean export of the selected Git files built a Python wheel and prepared a
  fresh six-learner test database with 96 validated comparison results. No ignored
  local scripts, datasets or development tests were needed for that preparation.

The current machine has no running approved Qwen service. Mocked adapter tests
verify rejection/failure handling, not model capability. The live Qwen GPU call,
latency, and restart behaviour on Lobot remain operator acceptance checks after
pulling this release. Start with one student before queuing a complete course.

Repeatable operator evidence is produced by `scripts/check_hosted_workspace.py`
and `scripts/evaluate_workspace.py`; generated reports stay outside Git. Development
tests and browser screenshots remain local under the repository's existing policy.

## Storage and security

The SQLite initializer adds `workspace_*` tables; PostgreSQL uses Alembic revision
`20260913_0003` with frozen migration SQL. Existing tables and CHECK constraints
are untouched: **Ongoing** belongs to the new durable support-case lifecycle.
Snapshots, model runs, policies and action events retain separate version identities.
Inference jobs have owner-checked leases and results persist across UI restarts.

Hosted API requests are signed over method, path/query, body, reviewer and timestamp.
The API reloads account permissions and authorizes course access, including legacy
routes. Unsigned development headers alone are rejected in hosted mode. The old
unvalidated `/api/v1/llm/evaluate` experiment is retired with HTTP 410.

Account files, signing keys, databases, model weights, logs and generated reports
are ignored. This remains a controlled prototype behind JupyterHub, not institutional
SSO or an independently always-on production service. Use approved backup storage
and access/retention policies before any real institutional records are introduced.

## Runtime references

The local launcher and constrained-output adapter follow the official
[Linux installation](https://docs.ollama.com/linux) and
[structured-output](https://docs.ollama.com/capabilities/structured-outputs)
documentation. Ollama lists the A16 among its supported NVIDIA cards in its
[hardware documentation](https://docs.ollama.com/gpu). This supports the chosen
deployment approach; it does not replace the live acceptance check above.
