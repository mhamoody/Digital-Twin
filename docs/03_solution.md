# 03 — Solution

## Solution in one sentence

Build weekly, leakage-free student states from empirical learning data; use a
strong LLM as the primary model for grounded risk prediction; compare and
calibrate it against classical baselines; persist the states, evidence,
predictions, and review history in a course-twin store; and expose only
traceable, human-reviewed alerts through a minimal instructor dashboard.

## Two evidence paths that must remain separate

The system deliberately separates model validation from operational validation.

| Path | Purpose | Valid claims |
|---|---|---|
| **Empirical path: OULAD or an approved replacement** | Build weekly states and evaluate early-warning models | Predictive performance, calibration, temporal behaviour, subgroup slices, and limitations on that dataset |
| **Operational path: local Moodle sandbox** | Exercise LMS entities, API/export ingestion, replay, database updates, alerts, and dashboard refresh | Integration correctness, latency, resilience, schema validity, and usability of the prototype |

Replaying OULAD-like records into Moodle connects the demonstration, but it does not turn synthetic Moodle identities into real learners. Results from the two paths are reported separately.

## MVP flow

1. **Dataset preparation** filters one or more module presentations and converts raw activity, assessment, registration, and outcome records into canonical observations.
2. **Weekly state builder** aggregates only records whose event time is at or before the checkpoint. It derives activity recency, active days, click totals, resource mix, submission status, and cumulative assessment progress.
3. **Model evaluation** sends a versioned, cutoff-safe weekly-state serialization
   to the selected strong LLM and compares its predictions with simple and
   conventional-ML baselines using presentation-aware splits. LLM probabilities
   are calibrated without touching the test labels.
4. **Evidence generation** requires the LLM to cite supplied evidence IDs and
   records its probability, uncertainty, citations, prompt, model, and data
   versions. SHAP is retained only for compatible baseline models; controlled
   feature ablation tests the LLM's evidence sensitivity.
5. **Moodle ingestion/replay** reads real sandbox entities and controlled test events, converts them to the same canonical observation schema, and updates PostgreSQL.
6. **Alert policy** creates an alert only when data are fresh, the relevant model-quality gate has passed, and a reviewed threshold or rule is met.
7. **Output validation** accepts the LLM result only when its risk fields and
   evidence references satisfy the contract. A deterministic rule/template path
   is the availability and safety fallback, not the intended intelligence.
8. **Dashboard review** lets an instructor inspect the timeline and evidence, then review, dismiss, or resolve the alert. No student action is automated.

## Primary LLM contract

The system deliberately uses a capable LLM as its primary model. Its authority
remains narrow: it predicts risk from the supplied student state and identifies
which supplied facts support that prediction. Model strength does not relax the
requirements for temporal validity, calibration, grounding, privacy, or human
review.

### Allowed

- Produce a raw non-success risk score from the supplied weekly state; the
  application applies the frozen calibrator and derives the risk band.
- Cite the supplied evidence identifiers most relevant to that prediction.
- Convert those cited facts into a short instructor-facing summary.
- Select from a small approved set of instructor review actions when appropriate.
- Abstain when the evidence is insufficient or inconsistent.
- As an independent stretch experiment, classify authentic labelled forum text.

### Not allowed

- Query raw personally identifiable student data.
- Invent causes, diagnoses, topics, or events not present in the input.
- Produce arbitrary student-facing advice.
- Trigger an email, referral, grade change, or other intervention.

### Grounding and output contract

The application provides a compact object such as:

```json
{
  "state_id": "state-123",
  "checkpoint_week": 5,
  "evidence": [
    {"id": "ev-1", "label": "days since activity", "value": 9},
    {"id": "ev-2", "label": "missed assessments", "value": 1}
  ],
  "allowed_actions": ["review recent work", "check missed assessment", "contact through approved channel"]
}
```

The model must return JSON with:

- `risk_score`: a number from 0 to 1 that is calibrated by application code;
- `summary`: at most two sentences;
- `evidence_ids`: only identifiers present in the request;
- `suggested_actions`: zero or more values from `allowed_actions`;
- `uncertainty_note`;
- `abstain`: Boolean; and
- `abstention_reason`: required when `abstain` is true.

Application code then:

1. parses against a strict schema with additional properties forbidden;
2. verifies that every evidence reference and suggested action is in the request;
3. verifies numeric ranges and prohibited or unsupported language;
4. retries once with the validation error; and
5. uses a clearly labelled deterministic fallback if validation still fails.

For an accepted result, application code applies the frozen calibrator to
`risk_score`, derives the displayed probability and risk band, and applies the
versioned alert threshold. The LLM never sees the held-out label or chooses the
operational threshold.

Only the validated object is stored and displayed, together with the
provider/model identifier, prompt and few-shot-example versions, timestamp,
validation result, calibration version, and fallback status. Raw model output
may be retained in a restricted evaluation log, never treated as trusted
application data. Training/test labels and examples from the held-out test
presentations are prohibited from the prompt context.

## Dataset strategy

The comparison is complete. OULAD is the sole empirical MVP source because it is
reproducibly accessible, linked across activity and assessments, outcome-labelled,
and feasible within the semester. The local Moodle sandbox is a separate
operational source. No alternative is concatenated with OULAD.

An alternative replaces OULAD only if it is accessible in time and supports the minimum linkage:

`learner → course/presentation → event time → activity/assessment → outcome`

Open edX contributes event/xAPI schema guidance; HarvardX/MITx may provide an
optional aggregate robustness check; MORF is future restricted replication; and
screened Moodle releases are adapter candidates subject to byte-level linkage,
calendar, outcome, and licence gates. A source with finer events but no valid
outcome may test ingestion, never predictive performance. A person-course
aggregate cannot support the weekly-state research question.

Forum corpora remain independent benchmarks. Their posts are never joined to OULAD student histories. Synthetic posts may exercise the UI and ingestion path, but they are not semantic-validation evidence.

The exact source evidence, feature contract, missingness rules, canonical
database, checkpoint cohort, and processing stages are in
[`08_data_strategy.md`](08_data_strategy.md).

## Alert policy and model-quality gate

An alert is eligible only when:

- the state was built successfully and data are not stale;
- the model is approved for that checkpoint and presentation context;
- calibration and validation results are visible;
- the probability exceeds a team-reviewed threshold or a transparent hard rule fires; and
- the alert includes at least one observable evidence record.

Each alert stores its status (`new`, `reviewed`, `resolved`, or `dismissed`), review note, timestamps, prediction, explanation, evidence, provenance, and version references. A threshold will be chosen using validation data and an explicit false-alert/false-negative trade-off, not an arbitrary score.

## Failure-safe behaviour

- If ingestion is stale, mark the dashboard stale and suppress new model alerts.
- If schema validation fails, quarantine the record and continue processing other records.
- If the model is not validated for a context, show descriptive state only.
- If baseline SHAP generation fails, report the baseline score without pretending an explanation exists.
- If the primary LLM fails, times out, cites absent evidence, or returns invalid
  JSON, suppress that output and display a clearly labelled deterministic
  fallback; never disguise the fallback as an LLM prediction.
- If a valid counterfactual cannot be produced, no counterfactual is shown; this stretch feature never blocks the MVP.

## Why this is still a digital twin

The value beyond a static dashboard is the maintained, historized state and feedback loop: source observations become versioned weekly states; states produce versioned predictions and evidence; alerts acquire an instructor-reviewed lifecycle; and each result can be replayed from its source data and cutoff. The project should demonstrate those properties clearly rather than relying on the label alone.
