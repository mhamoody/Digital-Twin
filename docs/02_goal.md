# 02 — Goals, priorities, and definition of done

## Priority order

The project is now organized around one research thread and one demonstrable system. A lower item must not delay a higher one.

| Priority | Deliverable | Why it is essential |
|---|---|---|
| P0 | Reproducible weekly OULAD state builder with leakage tests and provenance | This is the empirical foundation and main research artifact |
| P0 | Baselines plus one calibrated at-risk model evaluated at multiple checkpoints | Answers the primary research question |
| P0 | Versioned PostgreSQL twin schema and a Moodle-to-twin ingestion/replay path | Demonstrates that states can be maintained operationally |
| P0 | Minimal instructor dashboard: course overview, risk queue, student evidence, alert review | Makes the result usable and closes the human-in-the-loop cycle |
| P1 | SHAP evidence for the selected model | Makes each risk estimate inspectable without adding a separate research programme |
| P1 | Constrained LLM evidence verbalizer with deterministic-template fallback | Satisfies the LLM aspect while keeping it out of risk determination |
| P1 | Small formative walkthrough with available instructors/TAs | Finds serious usability failures; it is not a full usability study |
| P2 | Grade forecasting, knowledge/progress vectors, DiCE, forum semantics, RAG, richer course-health views | Valuable only after the MVP is stable; each is independently deferrable |

## Phase 0 — decision and design gate

Phase 0 is complete only when the team has evidence for the choices below.

| Goal | Completion criterion |
|---|---|
| Dataset decision | **Resolved 2026-08-02:** OULAD remains the sole empirical MVP source; local Moodle is operational; all other sources have bounded, non-merged roles. Evidence and scores are in `08_data_strategy.md`. |
| State definition | The weekly snapshot schema, outcome definition, prediction checkpoints, allowed feature cutoffs, and missing-data policy are reviewed and frozen for the first experiment. |
| Leakage controls | Automated checks prove that a snapshot at week `t` contains no events, assessment results, or engineered values from after the cutoff. |
| Baseline protocol | Module-presentation-aware train/validation/test rules, metrics, seeds, and majority/activity-only/grade-only baselines are specified before model comparison. |
| Moodle path | The existing Laragon-hosted Moodle sandbox has test users, course activities, web services, and a successful read-only API extraction or documented export fallback. |
| LLM contract | Input evidence, output JSON schema, allowed recommendation vocabulary, abstention rule, validation/retry behaviour, and template fallback are written before any hosted-model experiment. |

The dataset criterion is complete. Phase 1 implementation starts only after the
state definition, leakage controls, and baseline protocol are reviewed and
demonstrated. Moodle and LLM work can proceed in parallel only when it does not
block the empirical core.

## MVP goals and acceptance criteria

### 1. Temporal twin and data quality

- Produce exactly one versioned state per student, module presentation, and selected week.
- Store observed, derived, replayed, and synthetic records with explicit provenance.
- Pass automated cutoff, uniqueness, referential-integrity, and schema tests.
- Rebuild the same state set from a clean environment using documented commands and fixed configuration.

### 2. Early-warning model

- Compare regularized logistic regression with at most two tree-based candidates.
- Evaluate at weeks 3, 5, 8, and 10 where data permit.
- Prevent the same module presentation from crossing incompatible split boundaries.
- Report PR-AUC, ROC-AUC, macro-F1, at-risk precision/recall, Brier score, calibration plots, and confidence intervals where practical.
- Select the simplest model that materially improves on the declared baselines and has acceptable calibration. If no model does, report that result rather than tuning until a favourable number appears.
- Publish performance by checkpoint and presentation; never present one headline accuracy as the whole result.

### 3. Operational twin

- Pull or export users, course structure, activities, grades, and forum events from Moodle into PostgreSQL through a repeatable adapter.
- Replay at least 12 simulated weeks while preserving event time, ingestion time, origin, source record, and scenario.
- Complete a four-week continuous or accelerated replay with no unrecovered schema-breaking failure.
- Record synchronization latency and rejected/quarantined records. The target scheduled lag is under 60 minutes; true streaming is not required.

### 4. Instructor dashboard and alerts

- Show course status, a ranked at-risk queue, and a student timeline.
- Every alert displays risk probability, checkpoint, model version, last data refresh, and the observed evidence that supports it.
- An instructor can mark an alert `reviewed`, `resolved`, or `dismissed` and leave a note.
- Stale or failed ingestion is visible; the dashboard must not silently show old predictions as current.
- A small walkthrough verifies that an evaluator can find a flagged student, explain the evidence, and identify stale data without developer assistance.

### 5. LLM component

The MVP LLM is an **evidence verbalizer**, not the predictor and not an autonomous recommender.

- Accept only anonymized, structured evidence selected by application code.
- Return schema-valid JSON containing a short summary, evidence references, optional allowed actions, uncertainty, and an abstention flag.
- Make no claim that cannot be traced to an input evidence identifier.
- Reject or repair invalid output once; after that, fall back to a deterministic template.
- Evaluate against that template on a small frozen set for schema validity, evidence-reference coverage, unsupported claims, abstention, latency, and cost.
- Target 100% safe application-level handling: every accepted output is schema-valid, and every invalid/unsupported output is suppressed or replaced before display.

## Definition of done

The graduation-project MVP is done when:

1. a clean checkout can reproduce weekly states and the selected model evaluation;
2. the evaluation is temporally valid and includes baselines, calibration, uncertainty, and limitations;
3. OULAD's age, aggregation, and missing-text limitations—and the alternative-dataset decision—are documented;
4. Moodle events can be ingested/replayed into the versioned twin store;
5. the dashboard exposes evidence-linked alerts and the instructor review lifecycle;
6. the LLM path cannot display unvalidated free-form output and has a working template fallback;
7. empirical OULAD results, operational Moodle results, and text/synthetic experiments are reported separately; and
8. deployment, ethics, and evaluation documentation is sufficient for another student team to reproduce the demo.

## Stretch backlog

Only begin these after the definition above is secure:

1. DiCE counterfactual generation and feasibility evaluation.
2. Separate grade-band or continuous-score forecasting.
3. Assessment-domain knowledge/progress vectors.
4. Authentic forum confusion/urgency classification against classical text baselines.
5. Retrieval-augmented recommendations or a vector database.
6. Formal multi-participant usability study.
7. Cross-platform or cross-course generalization.
8. Live institutional pilot after ethics, privacy, and access approval.

A stretch result may strengthen the thesis, but an unfinished stretch feature must never weaken the reproducibility or evaluation of the P0 core.
