# Model runtime for the instructor demonstration

The first live predictor is `qwen2.5:7b` served by a private Ollama process.
It receives the canonical learner snapshot and the instructor's versioned
course policy. Its raw risk score is an **uncalibrated model score**, not a
measured probability of non-success. A frozen calibrator must be evaluated on
held-out empirical data before a probability can be displayed.

## Hardware and deployment

The supplied Lobot allocation reports 8 CPU cores, 16 GB host memory and two
NVIDIA A16 devices, each with 15,356 MiB VRAM (approximately 14,963 MiB free at
the reported check). That is a promising allocation for a quantized 7B model,
but actual cold-start, context memory and inference timing must be measured
on Lobot. Two GPUs do not automatically pool their VRAM into one device, and
host RAM is separate from GPU VRAM.

Start with one model, one inference worker and one request at a time. Keep
Ollama bound to `127.0.0.1:11434`; instructors use the protected application,
not an exposed Ollama endpoint. The model is provisioned by the operator;
the application never downloads an arbitrary model requested by a browser.

Configuration:

| Variable | Default | Purpose |
| --- | --- | --- |
| `DIGITAL_TWIN_OLLAMA_URL` | `http://127.0.0.1:11434` | Local model server |
| `DIGITAL_TWIN_LLM_MODEL` | `qwen2.5:7b` | Approved primary predictor |
| `DIGITAL_TWIN_LLM_DIGEST` | unset | Optional operator pin; a mismatch stops inference |
| `DIGITAL_TWIN_LLM_TIMEOUT_SECONDS` | `120` | Bounded model request time |
| `DIGITAL_TWIN_LLM_CONTEXT` | `8192` | Context budget |
| `DIGITAL_TWIN_LLM_MAX_TOKENS` | `1200` | Maximum generated tokens |

Before making research claims, archive the actual model digest, quantization,
Ollama/driver versions, prompt/input schema versions, decoding settings and
evaluation manifest. Model tags can change: each result records the resolved
digest, and an operator can require one exact digest for a frozen experiment.

## What the LLM contributes

The LLM chooses the raw risk score and selects supported academic claims and
recommended instructor actions. The application independently checks output
structure, evidence references, exact feature values, course-policy conditions
and action eligibility. Support levels and visible factual explanations are
rendered consistently from those validated results. The rules baseline is a
separately labelled comparison and is never passed off as an LLM response.

Inference input excludes names, email addresses, sensitive demographics, final
outcomes, synthetic scenario labels and expected answers. Synthetic generation
metadata is retained outside model input so scenarios can be evaluated without
revealing their answer to the predictor. The task uses structured evidence;
external pages and student-authored instructions do not receive tool authority.

## Validation and failure behaviour

1. Check snapshot freshness, evidence completeness and policy compatibility.
2. Verify that the approved model is installed and resolve its digest.
3. Request schema-constrained JSON with temperature zero and bounded context.
4. Validate strict fields, value ranges, abstention consistency and evidence.
5. Persist the validated result and run provenance, or retain a failure reason.

Missing/stale input can produce an explicit abstention with no risk score.
Unavailable Ollama, unknown model digest, timeout, invalid JSON or unsupported
claims produce failed analysis attempts, never fabricated fallback predictions.
An existing validated result remains historical evidence; it must not be shown
as a fresh result of the failed attempt. Temperature zero improves consistency
but is not a guarantee of identical output across hardware or runtime versions.

The worker processes persisted jobs outside the dashboard request. Closing a
browser therefore does not cancel its job. A stopped JupyterHub pod still stops
the application and worker; persisted queued jobs can resume when services are
restarted. Job lease recovery and idempotent completion prevent the same attempt
from being silently installed twice after an interrupted worker.

The deployment starts `scripts/run_analysis_worker.py`. With the deployment
environment already loaded, `python scripts/run_analysis_worker.py --once`
processes at most one queued job; `--model-kind baseline` restricts a preparation
run to explicitly labelled comparison jobs. It does not substitute rules for
queued LLM jobs. The model readiness check only checks installed-model metadata;
the interface distinguishes it from successful inference.

## Evidence and policy details

The current prediction contract selects coded factual claims with exact evidence
references. It deliberately has no unconstrained narrative explanation or
generated resource URL. The instructor sees the selected facts and approved
action codes; resource selection remains an instructor action. Raw forum text,
private notes and resource-page instructions are excluded from this risk prompt.
Text understanding remains a separate, future validated integration of the
member's forum-text experiment. Activity/assessment/grade values, completion,
attendance, upcoming workload, extensions and intervention timing are available
as structured features.

The predictor uses the supplied current policy even when a snapshot was built
under an older policy. Teaching-day inactivity is recalculated from the
last-activity date, course start date, teaching weekdays and declared breaks.
Grade concerns compare actual published grades with the current grade threshold.
Obsolete policy-derived inactivity counts and low-grade counts do not enter
the prompt. A subsequent change after instructor support is observational:
neither a selected claim nor the score establishes that support caused it.

Incomplete required activity or assessment streams and stale snapshots abstain.
A missing optional grade feed does not automatically prevent a result when
observed activity and submission evidence remain usable; it is recorded as a
data limitation, and grade claims become unavailable. No-grade-yet and
not-supported states remain distinct from observed zero grades. The default
policy requires academic corroboration before a high support level can be
accepted. Completion below 50%, attendance below 50%, and a published-grade
change of at least 10 percentage points are explicit initial claim definitions,
not validated research cutoffs; they should be evaluated alongside the prompt.

## Demonstration and evidence boundaries

The locally automated tests use explicitly simulated HTTP responses. They test
the adapter, validator and failure behaviour; they do not prove that Qwen ran
locally or on Lobot. A real hosted smoke test must archive the installed model
digest, one successful validated response, latency and one deliberate
model-unavailable failure before calling the deployment verified.

Use the complete synthetic cohort first, then controlled missing/stale variants
and competing evidence (for example good grades with low activity). Record
schema pass rate, evidence pass rate, abstention behaviour, consistency across
repeats, model latency and scenario expectations separately. Passing synthetic
scenarios proves handling of those cases; it does not establish real-world
predictive accuracy or intervention benefit.
