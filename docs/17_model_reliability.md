# Reliable Qwen analysis: correction, isolation and verification

## What the supplied Lobot evidence established

The September 14 logs showed successful local Qwen requests. Three consecutive
`MODEL_RISK_NOT_SUPPORTED` failures in DS210 triggered the earlier **shared**
protective pause. Consequently ED220 could show 1,920 queued records and no current
completions even though its own records had not failed. This was not evidence of a
slow or overloaded GPU.

The historical diagnosis contained 418 validated LLM jobs, 269 failed LLM jobs
and 3,418 queued LLM jobs across courses and versions. The failures were 149
`MODEL_ACTION_INVALID`, 58 `MODEL_ACTION_NOT_SUPPORTED`, 51
`MODEL_RISK_NOT_SUPPORTED`, and 11 `MODEL_SCHEMA_INVALID`. Median successful
inference time was approximately 8.0 seconds, with p95 approximately 9.9 seconds.
These timings exclude unsuccessful requests and are **not** whole-backlog timing
or predictive-accuracy measurements. Historical counts are not the same as the
dashboard's current model/prompt/policy counts.

An absent `var/log/ollama.log` is not itself a failure: `deploy/lobot/model.sh`
reuses an already-listening local Ollama process and only creates this log when
it starts a new one.

## What changes, and what deliberately does not

Qwen2.5:7B remains the primary risk predictor. Rules remain a labelled comparison,
not a fallback passed off as model analysis. The prompt version is now
`course-risk-qwen-v2.3`.

The model receives the same bounded, pseudonymous learner evidence and course
policy. Prompt guidance now distinguishes concern claims from protective
observations and explains which actions each claim can support. Medium/high
support levels must still have grounded concern evidence; the high-attention
corroboration policy remains enforced.

```text
Current canonical snapshot + course policy + evidence catalogue
  -> quality/input checks (insufficient evidence -> explicit abstention)
  -> Qwen structured response
  -> independent schema, evidence, action and policy checks
       pass -> persist and display
       repairable rejection -> one fresh Qwen request with the SAME evidence
                               and fixed validation feedback -> repeat all checks
                                  pass -> persist, labelled corrected
                                  fail -> retain rejection; publish no Risk score
```

The correction never receives the rejected free-text answer as instructions.
It receives an allowlisted error explanation and the original evidence packet.
The code does not add a concern, invent a grade, choose a lower score, or remove
the failed validation rule to make the response pass. No more than two generation
requests occur within one job attempt. Service/configuration/input-budget errors
do not receive this semantic correction.

JSON-schema-constrained generation is useful but is not a substitute for the
application checks. This follows Ollama's documented combination of a schema,
prompt guidance and independent parsing/validation: [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

Each generation has an audit entry: initial/correction, accepted/rejected/runtime
failure, safe error code, elapsed time, available token counters, and an output
hash. Raw prompts/responses are not added to these audit traces. Both entries
survive even if the final response fails. The learner profile distinguishes
first-pass acceptance, acceptance after correction, and pre-inference abstention.

**Validation acceptance is not evidence of accurate risk magnitude.** Risk scores
remain uncalibrated scores, not measured probabilities. Course policy defines
which claims/actions are admissible; Qwen still chooses its score and supported
interpretation within that contract.

## Queue, pause and instructor behaviour

| Situation | Behaviour |
|---|---|
| New/changed canonical learner-week evidence | Automatic discovery creates versioned work; unchanged evidence reuses results |
| Several courses have eligible work | Choose the least recently served course, then its newest eligible checkpoint |
| Initial output fails a repairable validation check | One evidence-preserving correction; both generations audited |
| Three consecutive final validation failures in one course | Pause that course; other eligible courses continue |
| Temporary connection/timeout/busy/server failure | Bounded job retry with delay and shared cooldown |
| Shared configuration, memory or unexpected internal failure | Shared protective pause; operator investigation required |
| Instructor resumes a course | Clear only that course's pause; do not fake a worker heartbeat or clear a shared pause |
| Old shared validation pause at upgrade | Attribute it to the latest matching failed course and preserve that course's pause; if attribution is unavailable, retain an operator-review pause |

There are at most three queue attempts per job; each may contain up to two
generations. Automatic validation correction is not an unlimited retry loop.
Explicit retries retain previous attempts. A new approved prompt/runtime version
gets separate work, rather than resetting the old job's history.

The worker remains serial to avoid accidental GPU overload. Its lease covers both
bounded generation requests. A live long request is distinguished from a stale
heartbeat. Automatic discovery skips paused courses and their backlog so they do
not consume the discovery allowance for healthy courses.

The progress panel refreshes every 10 seconds while open. Its read timestamp and
worker heartbeat are separate: a successful UI read is not proof of active
inference. Timer updates issue reads, not queue/resume requests. Unsaved automation
choices and support forms stay outside the timed fragment. Other student cards
and profiles update through **Refresh workspace** or navigation. Streamlit supports
this independent refresh behaviour through [fragments](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment).

Inactivity settings, ongoing cases, intervention/resource history, follow-ups,
authentication and course authorization retain their existing workflow. No
automatic student messages or invented empirical records are introduced.

## Install on the existing Lobot allocation

Run in its JupyterLab terminal:

```bash
cd ~/Digital-Twin
git pull --ff-only origin agent/align-strong-llm
bash deploy/lobot/update_reliability.sh
bash deploy/lobot/model.sh start
bash deploy/lobot/status.sh
```

The update copies existing logs to a timestamped ignored folder, makes a database
backup, waits for the worker to stop safely, installs the package, applies additive
tables, and restarts the protected application. It does not recreate data, delete
results, change accounts, download another model or automatically clear a course
pause. Stop if any command fails. Do not repeatedly reset the database or queue.

Open the normal `/user/group-digi2026-g12/proxy/8501/` dashboard. An attributable
legacy DS210 pause remains on DS210; ED220 and other healthy courses can proceed.
After reviewing the new prompt behaviour and pause reason, use **Resume this
course after checking the error** for the affected course. **Analyze all
unassessed checkpoints** is safe to repeat: current pending/results are reused.
You should see queued -> running -> validated/abstained, or an explicit failure.
A resume request alone is not confirmation that a job has run.

Read current-version status without altering anything:

```bash
source .venv/bin/activate
set -a
source .env.lobot
set +a
python scripts/manage_analysis_runtime.py status
```

Add `--course synthetic:ED220:2026A` to restrict the report, using the actual
course ID shown by the system. For historical counts, retain
`python scripts/diagnose_analysis.py`. Neither status command consumes jobs.

Only if a **shared service pause** remains and its cause has been corrected:

```bash
python scripts/manage_analysis_runtime.py resume-service --confirm
```

This operator command checks model readiness and requests a resume; it does not
start a stopped worker. It is intentionally unavailable through instructor APIs.
It does not clear separate course pauses.

## Measure live model reliability before claiming an improvement

Local automated tests use simulated model responses to verify the mechanism.
They cannot establish Qwen's real first-pass acceptance or predictive accuracy.
Use the Lobot GPUs for a small, separate live check. To avoid queue competition
distorting latency, first stop the application safely (this temporarily takes
the dashboard offline; if stop reports an in-flight request, wait and retry):

```bash
bash deploy/lobot/stop.sh
source .venv/bin/activate
set -a
source .env.lobot
set +a
bash deploy/lobot/model.sh start
python scripts/evaluate_workspace.py --llm --limit 12 \
  --output-dir artifacts/workspace/qwen-v23-check-01
bash deploy/lobot/start.sh
```

Use a new output directory each time. The harness freezes `inputs.json` before
inference, balancing twelve scenario families across three courses and several
checkpoints. Each base has complete, missing-grade, partial-activity and stale-
activity variants: 48 cases for each evaluated predictor at `--limit 12`. Some
variants correctly abstain before any model request. The private scenario oracle
is not included in the model input and is not used as a numerical risk target.

To compare later prompt/model changes fairly, reuse the exact frozen inputs:

```bash
python scripts/evaluate_workspace.py --llm \
  --inputs artifacts/workspace/qwen-v23-check-01/inputs.json \
  --output-dir artifacts/workspace/qwen-comparison-02
```

Retain the installed model digest, prompt version, input hash, token budgets,
hardware and run conditions. Inspect `report.json` and `results.csv` for:

- First-pass scored acceptance, corrected scored acceptance, model abstention,
  pre-inference abstention, final rejection and runtime failure separately.
- Generation-level failure counts, including first responses corrected later.
- Case/attempt denominators, correction overhead, and p50/p95 timing including
  failed requests. A ready service alone never counts as executed inference.
- Results separately for each degraded-data condition. A high abstention rate
  must not be presented as high prediction accuracy.

This synthetic check measures operational behaviour, not real academic outcomes.
Before claiming accuracy improvement, use labelled empirical outcomes, leakage-
safe course/time splits, a genuinely held-out test set, comparison baselines,
abstention coverage/error rates and calibration fitted on validation data then
frozen. Reviewing difficult/repaired cases is necessary: factual grounding alone
does not show that a score is well calibrated or an intervention effective.

## Implementation references

Local verification on this revision: 217 automated tests passed, including
course authorization, retry/lease limits, both correction traces, prompt-version
eligibility, migration preservation on a copy of the empirical database, and
evaluation accounting. The complete 5,760-snapshot synthetic fixture stayed within
the conservative character budget: 12,113 maximum initial characters and 12,747
with correction feedback, against 13,984. This is not measured tokenizer usage.

The real local browser/API check observed three timed status reads and zero
mutation requests while a form edit was unsaved. Automation, policy and support
drafts survived; no page-level horizontal overflow occurred at 360, 390 or 768
pixels. A separate signed-API browser check queued 1,920 current-version records,
added zero on a repeated click, and persisted the automation preference. A support
contact record also saved and reloaded correctly in the isolated synthetic preview.
Local Qwen inference was not available: no live-model accuracy or acceptance
improvement is claimed from these checks.

- Model contract, prompt and bounded correction: `src/digital_twin/workspace/llm.py`
- Error semantics: `src/digital_twin/workspace/errors.py`
- Course/service controls: `src/digital_twin/workspace/controls.py`
- Discovery, version identity and queue: `workspace/scheduling.py`, `workspace/store.py`
  under `src/digital_twin/`
- Worker and safe generation traces: `src/digital_twin/workspace/worker.py`, `tracing.py`
- Additive migration: `migrations/versions/20260914_0005_inference_reliability.py`
  and `migrations/sql/20260914_0005_inference_reliability.sql`
- Interface: `src/digital_twin/dashboard/workspace_ui.py`
- Frozen evaluation: `scripts/evaluate_workspace.py`
- Operator diagnosis/resume: `scripts/manage_analysis_runtime.py`
- Safe update: `deploy/lobot/update_reliability.sh`
