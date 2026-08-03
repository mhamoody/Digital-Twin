# 05 — Architecture, data contracts, and evaluation boundaries

## Logical architecture

```text
                         EMPIRICAL RESEARCH PATH
 Raw OULAD / approved source
          |
          v
 Canonical observations --> weekly state builder --> evaluation dataset
          |                       |                         |
          |                       v                         v
          |                versioned twin store     baselines + strong LLM
          |                       ^                         |
          |                       |                         v
          |                 evidence + alerts <------ calibrated prediction + grounded citations
          |                       |
          |                       v
          |                 FastAPI / Streamlit ----> instructor review
          |                                               |
          +-----------------------------------------------+
                                  recorded feedback

                         OPERATIONAL TEST PATH
 Local Moodle --> web services/export --> canonical observations --> same twin store
      ^                                                        |
      +------------- controlled replay/test scenarios ----------+

                         OPTIONAL TEXT BENCHMARK
 Authentic labelled corpus --> isolated text evaluation --> results only
                         (never identity-joined to OULAD)
```

## Canonical data layers

The database separates facts from interpretations. A later model run must not overwrite the evidence used by an earlier alert.

| Layer | Examples | Mutability rule |
|---|---|---|
| Source registry | dataset, licence, checksum, presentation, import version | Append/version; never silently replace |
| Raw/canonical observations | activity, assessment, registration, forum event | Immutable after accepted ingestion; corrections create a new version or audit event |
| Derived weekly state | clicks to date, active days, recency, missed work, cumulative score | Rebuildable and keyed by feature-set version plus cutoff |
| Prediction | probability, checkpoint, model/calibrator version | Append-only result of a model run |
| Evidence/explanation | supplied feature values, LLM evidence citations/ablation results, baseline SHAP, validated summary | Linked to one prediction; never detached from its inputs |
| Alert | policy version, threshold, confidence, freshness, status | Status changes are audited |
| Instructor feedback | reviewer, note, decision, timestamp | Append-only audit record |

## Minimum entities

| Entity | Required fields |
|---|---|
| `source_dataset` | `source_id`, name, version, licence/access, checksum, imported_at |
| `course_presentation` | `presentation_id`, source_id, course/module code, start/end or relative calendar |
| `learner` | pseudonymous `learner_id`, source_id; optional protected attributes stored separately with restricted use |
| `enrolment` | learner_id, presentation_id, registration/withdrawal dates, outcome when legitimately available |
| `activity_observation` | observation_id, learner_id, presentation_id, activity/resource type, event_time or aggregate_date, count/value, source record, origin |
| `assessment` | assessment_id, presentation_id, type, due date, weight, optional domain/topic |
| `assessment_observation` | learner_id, assessment_id, submission date, score, missing/withdrawn status, origin |
| `text_observation` | text_id, learner/pseudonym where legitimately linkable, thread/context, event_time, content or restricted-content pointer, label provenance |
| `weekly_state` | learner_id, presentation_id, week, cutoff_at, feature_set_version, feature values, missingness flags, origin summary |
| `prediction` | state key, model_version, prompt version, raw/calibrated probability, output, generated_at, quality-gate status |
| `evidence` | prediction_id, evidence_id, supplied feature/value, citation/attribution method and value, display label |
| `llm_output` | prediction_id, provider/model, prompt/few-shot versions, parsed object, validation and abstention result, fallback used, latency/cost metadata |
| `alert` | prediction_id, policy version, type, priority, freshness, status, created_at |
| `alert_review` | alert_id, reviewer pseudonym/role, prior/new status, note, reviewed_at |

Every generated or replayed row also carries:

- `data_origin`: `empirical`, `replayed`, `synthetic`, or `manual_test`;
- `source_dataset` and `source_record_id` when applicable;
- `generation_method` and `scenario_id` when applicable;
- `event_time` and `ingested_at`; and
- schema/adapter version.

## Weekly state contract

The primary grain is:

`(learner_id, presentation_id, checkpoint_week, feature_set_version)`

Planned feature groups are:

| Group | Candidate features | Guardrail |
|---|---|---|
| Activity | weekly/cumulative clicks, active days, resource-type counts | OULAD clicks are daily aggregates, not login sessions |
| Recency/regularity | days since activity, active-week ratio, variance/regularity | Derive only from dates on or before the cutoff |
| Assessment | attempts/submissions to date, missed due work, cumulative weighted score, recent score trend | Include a score only after its legitimate availability date |
| Context | registration timing, prior attempts, presentation week | Do not let course-end or withdrawal information leak backward |
| Missingness | missing activity, missing assessment, incomplete week | Preserve missingness; do not convert all missing values to zero blindly |
| Provenance | source, origin, cutoff, feature version | Required for every state |

Potential demographics are restricted to fairness/sensitivity analysis unless the team explicitly justifies their predictive use. Report a comparison with them excluded. Demographic attributes are never actionable explanation or recommendation inputs.

### Leakage rules

- A week `t` state uses only observations with an allowed availability time at or before the week `t` cutoff.
- Course-end outcome, final grade, withdrawal date, and future assessment results are labels/context, not early features.
- Fitted preprocessing, imputation, feature selection, and calibration use training folds only.
- Multiple weekly rows from the same learner/presentation must not be split in a way that leaks one trajectory across train and test.
- Prefer module-presentation-aware evaluation; document any weaker split forced by sample size.
- Automated tests deliberately inject future records and assert that earlier states do not change.

## Dataset decision matrix

Each candidate receives `0 = absent/unusable`, `1 = partial or costly`, or `2 = strong`. Record evidence and access date beside every score in the working comparison artifact.

| Criterion | Why it matters | Minimum to replace OULAD |
|---|---|---|
| Timely access | The project cannot wait on an uncertain request | Files or approved environment available by the Phase 0 gate |
| Licence/publication | Results and derived artifacts must be publishable for assessment | Clear research/academic use and reporting permission |
| Learner/course linkage | Required to build trajectories | Stable pseudonymous learner and course/presentation identifiers |
| Time resolution | Required for weekly states | Events or aggregates with usable relative dates |
| Assessment linkage | Connects behaviour to progress | Assessment/submission/score data linked to the learner |
| Outcome label | Required for empirical early-warning evaluation | Pass/fail/withdrawal/grade or a justified equivalent |
| LMS realism | Tests transfer to an operational LMS | Event/resource types and timestamps beyond person-course totals |
| Authentic text | Supports the optional LLM semantic task | Raw, ethically usable text with labels or a feasible labelling plan |
| Documentation/quality | Controls implementation risk | Data dictionary, manageable missingness, reproducible download |
| Effort/size | Must fit four people and one semester | A first weekly-state table can be built within roughly one week |

The completed source scores, access checks, and evidence links are recorded in
[`08_data_strategy.md`](08_data_strategy.md). Stanford MOOCPosts or another
authentic corpus can only be an **independent text benchmark**, never replacement
structured data.

## Current data decision

The comparison was resolved on 2026-08-02:

- OULAD is the sole empirical structured source for MVP training and evaluation.
- Local Moodle is the operational sandbox and is reported separately.
- Open edX is a schema reference; HarvardX/MITx is at most an optional aggregate
  check; MORF and public Moodle cohorts stay outside P0 until their access and
  linkage gates pass.
- Fine-grained session/login fields absent from OULAD remain absent; daily
  activity aggregates retain day precision and an event count.
- Authentic text corpora are evaluated independently.
- Synthetic/replayed data are limited to API, integration, rare-state,
  failure-recovery, and UI tests.

The normalized table shape and source mappings in `08_data_strategy.md` refine
the minimum entities above without changing their provenance and immutability
rules.

## Component contracts

### Ingestion

- Idempotent: re-reading the same source record does not duplicate it.
- Incremental: stores a cursor or last successful watermark.
- Observable: records accepted, rejected, quarantined, and delayed rows.
- Recoverable: an interrupted batch can resume without corrupting state.
- Read-only toward Moodle through supported interfaces; no direct production-table writes.

### State builder

- Pure/reproducible from canonical observations, configuration, and cutoff.
- Emits validation counts and leakage-test results.
- Versions feature definitions; changing a feature creates a new feature-set version.

### Prediction service

- Accepts a persisted state key, not arbitrary dashboard values.
- Serializes only cutoff-safe state fields through a versioned prompt contract.
- Uses the selected strong LLM as the primary predictor and returns its model,
  prompt, few-shot, and calibrator versions with raw and calibrated probability.
- Refuses unsupported checkpoint/presentation contexts.
- Persists the exact state/model reference used for every prediction.

### LLM validation and evidence service

- LLM input is an allow-listed projection of the persisted weekly state.
- The LLM must cite only evidence identifiers present in that projection.
- Strict JSON/schema and semantic validation occur before persistence/display.
- Controlled input ablation tests evidence sensitivity; SHAP is used only for
  compatible structured baselines and is never presented as an LLM explanation.
- A clearly labelled deterministic fallback is mandatory when the primary LLM
  cannot return a safe result.

### Dashboard/API

- Role-restricted instructor/research access.
- No public student or prediction endpoints.
- Freshness and failure state visible on every relevant page.
- Alert-status mutations are authenticated and audited.

## Evaluation boundaries

| Evidence source | Evaluate | Do not claim |
|---|---|---|
| OULAD/approved empirical dataset | primary LLM and baseline early-warning performance, calibration, temporal generalization, subgroup slices | live Moodle performance or modern-session behaviour without evidence |
| Moodle replay/synthetic data | ingestion, latency, schema, failure recovery, alert lifecycle, interface | real-world predictive validity or authentic learner behaviour |
| Authentic independent text corpus | text classification/verbalization metrics | joint risk prediction for OULAD learners |
| Frozen LLM audit cases | grounding, schema, abstention, evidence sensitivity, latency, cost, reviewer interpretation | educational intervention effectiveness or hidden chain-of-thought validity |
| Small dashboard walkthrough | task completion and major usability problems | generalizable usability or learning-outcome improvement |

This separation is a core integrity requirement and should appear in the final report's results structure.
