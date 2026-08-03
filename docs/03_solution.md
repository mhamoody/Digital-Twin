# 03 — Solution

## Solution in one sentence

Build weekly, leakage-free student states from empirical learning data; estimate and calibrate early risk; persist the states, evidence, predictions, and review history in a course-twin store; and expose only traceable, human-reviewed alerts through a minimal instructor dashboard.

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
3. **Model evaluation** compares simple baselines and a small candidate set using presentation-aware splits. The selected model is calibrated and evaluated at early and mid-semester checkpoints.
4. **Evidence generation** records prediction probability and SHAP attributions for the selected model. Model/data versions and feature values are stored with the prediction.
5. **Moodle ingestion/replay** reads real sandbox entities and controlled test events, converts them to the same canonical observation schema, and updates PostgreSQL.
6. **Alert policy** creates an alert only when data are fresh, the relevant model-quality gate has passed, and a reviewed threshold or rule is met.
7. **Explanation rendering** uses a deterministic template by default. A constrained LLM may rewrite the same verified evidence into concise text, subject to the contract below.
8. **Dashboard review** lets an instructor inspect the timeline and evidence, then review, dismiss, or resolve the alert. No student action is automated.

## What the LLM does—and does not do

The LLM is kept small in scope because it is a major dependency and a common source of unsupported output.

### Allowed

- Convert already-selected evidence into a short instructor-facing summary.
- Choose from a small approved set of review actions.
- Abstain when the evidence is insufficient or inconsistent.
- As an independent stretch experiment, classify authentic labelled forum text.

### Not allowed

- Calculate or change the risk probability.
- Query raw personally identifiable student data.
- Invent causes, diagnoses, topics, or events not present in the input.
- Produce arbitrary student-facing advice.
- Trigger an email, referral, grade change, or other intervention.

### Grounding and output contract

The application provides a compact object such as:

```json
{
  "alert_id": "alert-123",
  "checkpoint_week": 5,
  "risk_probability": 0.71,
  "evidence": [
    {"id": "ev-1", "label": "days since activity", "value": 9},
    {"id": "ev-2", "label": "missed assessments", "value": 1}
  ],
  "allowed_actions": ["review recent work", "check missed assessment", "contact through approved channel"]
}
```

The model must return JSON with:

- `summary`: at most two sentences;
- `evidence_ids`: only identifiers present in the request;
- `suggested_actions`: zero or more values from `allowed_actions`;
- `uncertainty_note`;
- `abstain`: Boolean; and
- `abstention_reason`: required when `abstain` is true.

Application code then:

1. parses against a strict schema with additional properties forbidden;
2. verifies that every evidence reference and suggested action is in the request;
3. rejects prohibited or unsupported language;
4. retries once with the validation error; and
5. uses the deterministic template if validation still fails.

Only the validated object is stored and displayed, together with the provider/model identifier, prompt version, timestamp, validation result, and fallback status. Raw model output may be retained in a restricted evaluation log, never treated as trusted application data.

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
- If SHAP generation fails, show feature values and the risk score without pretending an explanation exists.
- If the LLM fails, times out, cites absent evidence, or returns invalid JSON, display the deterministic template.
- If a valid counterfactual cannot be produced, no counterfactual is shown; this stretch feature never blocks the MVP.

## Why this is still a digital twin

The value beyond a static dashboard is the maintained, historized state and feedback loop: source observations become versioned weekly states; states produce versioned predictions and evidence; alerts acquire an instructor-reviewed lifecycle; and each result can be replayed from its source data and cutoff. The project should demonstrate those properties clearly rather than relying on the label alone.
