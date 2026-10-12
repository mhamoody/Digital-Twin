# 02 — Final goals and completion boundary

## Completed research goals

| Goal | Final evidence | Status |
|---|---|---|
| Cutoff-safe temporal learner state | E4 provenance audit and implementation | Complete |
| Checkpoint-specific empirical prediction | E1 Logistic Regression on OULAD AAA/2013J | Complete within declared scope |
| Controlled LLM grounding comparison | E2 plain-LLM versus schema-only, 48 frozen cases | Complete |
| Operational evidence-grounded LLM path | Versioned Qwen2.5:7b runtime evidence | Complete as operational evidence |
| Human-in-the-loop traceability | Separate prediction, triage, support case, action, and audit records | Complete as a framework contribution |

## Exact empirical completion boundary

E1 contains 383 source enrolments, 372 eligible learners, and 1,464 temporal states at weeks 3, 5, 8, and 10. Logistic Regression achieved:

| Checkpoint | AUROC | Average Precision |
|---|---:|---:|
| Week 3 | 0.621 | 0.379 |
| Week 5 | 0.657 | 0.531 |
| Week 8 | 0.896 | 0.819 |
| Week 10 | 0.834 | 0.802 |

The split is learner-grouped; preprocessing is fitted on training data; threshold selection uses validation data; and final reporting uses the untouched test partition. These metrics are not Qwen results or calibrated probabilities.

E4 audits 194,590 provenance rows with 0 cutoff violations. This result is limited to the audited artifacts.

## Exact LLM completion boundary

E2 is a controlled grounding experiment, independent from E1 and operational runtime history. Across 48 frozen cases, schema-only generation substantially improved structural and citation compliance but did not improve abstention or behavioral correctness. The valid primary comparison excludes E2 v1, invalid schema-only r1, defective `evidence_first_full`, and incomplete post-hoc `evidence_first_full_v2`.

The operational path uses Qwen2.5:7b with the `risk-decision-v3` contract, deterministic validation, bounded repair, quality abstention, and auditable provenance. It provides operational reliability evidence, not predictive accuracy. No calibrated Qwen probability was established.

## Product definition of done

The current product satisfies the project boundary when it:

1. serves versioned temporal learner/course state through FastAPI;
2. uses React as the current instructor workspace;
3. preserves Streamlit only as a legacy/fallback interface;
4. binds every displayed prediction or analysis to its exact state;
5. exposes evidence, risk history, triage, support cases, and support history;
6. keeps Risk State, Triage Status, and Support Case Status separate;
7. authenticates users and applies course-level grants;
8. protects mutations with authorization, idempotency, audit, and optimistic concurrency; and
9. labels empirical, controlled, operational, replayed, and synthetic evidence accurately.

## Submission boundary

The current master's evidence does not require new experiments. Before final submission, controlling documentation, presentation materials, and the demo script must use the frozen evidence and claim boundaries consistently.

## Future work, not current blockers

- Probability calibration.
- Empirical Qwen risk-prediction evaluation.
- External-course replication.
- Formal educator-effectiveness or decision-quality studies.
- Production LTI/onQ integration.
- Real-time synchronization or causal simulation.
- Additional post-hoc E2 treatments.
