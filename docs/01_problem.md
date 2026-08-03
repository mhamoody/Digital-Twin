# 01 — Problem and research position

## Project definition

This project builds a **course-level digital twin for instructor decision support**. The twin is a timestamped, queryable, and historized representation of observable student activity and academic progress. It is refreshed as new LMS evidence arrives and preserves the state that was known at each weekly checkpoint.

For this project, the term does **not** mean a simulation of a student's mind. The system observes LMS interactions, submissions, assessment results, and—only when authentic or appropriately labelled data are available—student-authored text. It may estimate risk, but it must not claim to measure motivation, understanding, or causality directly.

| Digital-twin property | Course-level interpretation | Boundary |
|---|---|---|
| Continuously updated state | Weekly student-state snapshots plus scheduled Moodle ingestion | Near-real-time means scheduled refresh, not streaming infrastructure |
| State history | Immutable observations and versioned derived states for each checkpoint | Later information must never leak into earlier predictions |
| Prediction | Calibrated probability of non-success at selected checkpoints | A prediction is uncertain evidence, not a diagnosis |
| Explanation | Observable features linked to each alert | Explanations describe model behavior, not causes of student behavior |
| Feedback loop | Instructor reviews, dismisses, or resolves an alert and records a note | The system never contacts or penalizes a student automatically |

## The problem

LMS platforms collect useful evidence, but instructors usually see it as disconnected activity reports and gradebook summaries. A slowly declining pattern—fewer active days, longer inactivity, missed work, and falling assessment progress—can remain unnoticed until the student has already failed an important assessment or withdrawn.

The technical problem is therefore not merely to train another pass/fail classifier. It is to determine whether a small, auditable system can:

1. reconstruct what was known about each student at a given point in the semester;
2. make an early, calibrated risk estimate without future-data leakage;
3. attach each alert to traceable evidence and an explicit model/data version; and
4. present that evidence to an instructor without overstating certainty or automating an educational decision.

## Research focus

The proposal originally combined many substantial studies: temporal modelling, grade forecasting, knowledge-state estimation, SHAP, DiCE counterfactuals, LLM text analysis, LLM grounding tests, alert evaluation, fairness analysis, and dashboard usability. The grading feedback correctly identified this as too broad for four students in one semester.

The revised **primary scientific contribution** is narrower:

> Design and evaluate a leakage-controlled, provenance-aware weekly student-state twin in which a capable LLM is the primary risk model, and determine whether its calibrated, evidence-grounded predictions improve on static and conventional-ML baselines.

This separates the research contribution from the engineering contribution:

| Type | Contribution |
|---|---|
| Scientific | Temporal state construction; a strong LLM as the primary predictor; leakage-aware checkpoint evaluation; calibration; comparison with majority, activity-only, grade-only, logistic, and tree baselines; analysis of grounding and model-quality gates |
| Engineering | Moodle ingestion/replay, PostgreSQL persistence, API, dashboard, alert lifecycle, and deployment packaging |
| Supporting analysis | Classical ML establishes comparison baselines rather than the intended final intelligence. SHAP may explain compatible baselines; LLM evidence references and controlled input ablations assess the primary model. DiCE and semantic forum analysis remain stretch work. |

### Research questions

- **RQ1:** At weeks 3, 5, 8, and 10, how well does a strong LLM predict non-success from leakage-controlled weekly states compared with majority, activity-only, grade-only, logistic, and tree-based baselines?
- **RQ2:** Can the LLM's risk scores be calibrated sufficiently for threshold-based instructor alerts, and how does reliability vary by module presentation and checkpoint?
- **RQ3:** Can every accepted LLM prediction cite only supplied evidence, satisfy the output contract, expose uncertainty, and remain traceable to its prompt, model, data, and state versions?
- **RQ4:** Does the LLM add useful predictive or evidence-quality value beyond conventional structured models at an acceptable latency, cost, and failure rate?

## Data problem

The investigation is complete: no verified public source supplies modern
fine-grained LMS events, linked assessment timing, a usable outcome, and
authentic labelled forum text for the same learners. The answer is therefore to
separate evidence paths, not fabricate a larger joined dataset.

- **OULAD is the empirical MVP source.** It is accessible, CC BY 4.0, linked,
  outcome-labelled, and large enough for presentation-aware checkpoint
  evaluation. Its 10,655,280 VLE rows are learner-resource-day click aggregates,
  not sessions or event timestamps.
- **The local Moodle sandbox is the operational source.** It supplies realistic
  entities, timestamps, APIs, grades, and event flow, but replayed/synthetic
  learners cannot validate predictive accuracy.
- **Open edX contributes a modern event/xAPI schema, not public cohort rows.**
  Rich MITx data require a request and data-use agreement.
- **HarvardX/MITx public data are person-course aggregates.** They cannot rebuild
  weekly states or assessment histories.
- **MORF is a restricted remote Coursera execution environment.** It requires an
  institutional data-use agreement and is not a downloadable supplement.
- **Newer Moodle releases are adapter candidates, not current training data.**
  Screened releases either lacked reproducible event-to-outcome linkage, had
  unavailable files, or still require calendar/outcome auditing.
- **Authentic forum corpora remain independent text benchmarks.** Their learner
  identities are never joined to OULAD.

The accepted combination, direct OULAD profile, missing-column policy, database
shape, feature contract, and pipeline are specified in
[`08_data_strategy.md`](08_data_strategy.md).

## Constraints

- Four team members and approximately one academic semester.
- One course/presentation at a time; multi-course deployment is future work.
- No dependence on Queen's internal student data without formal approval.
- Textual and structured LMS data only; no video or audio analysis.
- Lightweight, reproducible infrastructure suitable for student laptops.
- All personally identifiable information must be removed before storage, modelling, or external model calls.
- No autonomous intervention, grading, referral, or student-facing message.

## Explicit non-goals for the MVP

- Inferring a student's internal cognitive or emotional state.
- Claiming that a model feature caused an outcome.
- Production deployment at Queen's or institution-wide scaling.
- Combining unrelated learners across public datasets as if they were the same people.
- Using synthetic data as the principal evidence for predictive performance.
- A full causal or counterfactual-feasibility study; DiCE is a stretch experiment.
- A full semantic forum/short-answer research study unless suitable authentic text is secured.
- Adaptive content generation, tutoring-system integration, multi-agent automation, or direct student action.

## Source precedence

These documents synthesize, in order: the original supervisor proposal, weekly meeting and task documents, the July 2026 group proposal, the completed local Moodle-sandbox work, and the latest proposal feedback. Where they conflict, the latest feedback-driven MVP boundary in this document set takes precedence.
