# 01 — Problem and research position

## Current boundary

The project addresses the gap between disconnected LMS records and an instructor's need for traceable, time-specific evidence. It reconstructs what was observable about a learner at declared checkpoints, evaluates empirical prediction separately, and preserves subsequent instructor and support actions without rewriting historical model evidence.

The thesis-safe description is:

> A provenance-aware, checkpointed course digital twin that connects temporal learner-state reconstruction, predictive analysis, validated instructor-facing evidence, and auditable human support decisions.

The system is not real-time, causal, a continuous psychological twin, or a universal student simulator. It does not infer motivation, understanding, or unobserved causes.

## Research problem

The technical and research problem is to determine whether a small auditable system can:

1. reconstruct cutoff-safe learner state at early checkpoints;
2. retain provenance from each derived value to available observations;
3. measure how empirical predictive performance changes by checkpoint;
4. constrain and validate LLM-generated instructor-facing evidence; and
5. represent model state, instructor triage, and longitudinal support decisions as separate historical records.

## Final research questions

- **RQ1 — Temporal Prediction:** How does predictive performance evolve across cutoff-safe learner states at early course checkpoints? Evidence: E1.
- **RQ2 — Temporal Integrity:** Can a provenance-aware temporal learner-state pipeline prevent post-cutoff information leakage while preserving traceability? Evidence: E4 and implementation.
- **RQ3 — LLM Grounding and Reliability:** How do structural constraints and deterministic validation affect evidence compliance, abstention behavior and operational reliability of LLM-generated instructor-facing analyses? Evidence: E2 and separate operational LLM evidence.
- **RQ4 — Human-in-the-loop Traceability:** How can model risk, instructor triage and longitudinal support decisions be represented separately while preserving historical model evidence? Evidence: system/framework implementation.

RQ4 does not claim educator-effectiveness evidence. E2 and operational LLM history are separate evidence classes, not one experiment.

## Contribution hierarchy

### Primary research contributions

1. Provenance-aware cutoff-safe temporal learner-state construction.
2. Checkpoint-specific empirical predictive analysis across early learner states.
3. Controlled evidence showing that structural/citation compliance alone does not guarantee correct selective abstention or behavioral decisions.

### Secondary research contribution

A versioned evidence-grounded operational LLM pipeline with deterministic validation, bounded repair, quality abstention, and auditable model/prompt provenance.

### Framework contribution

Separation between prediction/model state, instructor triage, and support-case state.

React, FastAPI, authentication, persistence, deployment, workers, support UI, and Streamlit fallback are engineering/product contributions. The React dashboard is not research novelty.

## Empirical and operational boundaries

- OULAD `AAA/2013J` is the empirical E1 source.
- E1 uses Logistic Regression, not Qwen.
- Operational Qwen analysis is not empirical predictive evaluation.
- Synthetic Workspace courses validate workflows and runtime behavior, not educational predictive validity.
- Scores from `simple-rules-v1` and operational Qwen are uncalibrated and must not be called probabilities.
- Calibration was not completed.
- Multi-course empirical generalization and educator validation remain future work.

## Constraints and non-goals

- No unrelated learner identities are joined across datasets.
- No direct student intervention, grading, penalty, or referral is automated.
- No causal or psychological claim is derived from activity traces.
- No claim of institution-wide or cross-platform generalization is made.
- The empirical result is primarily scoped to one OULAD presentation.

## Source precedence

When documents conflict, use this order:

1. `evaluation/reports/final_research_evidence_matrix.md` in the sibling evaluation repository.
2. `evaluation/reports/e2_run_validity.md`.
3. `evaluation/reports/llm_operational_version_evidence.md`.
4. Frozen E1/E2/E4 artifacts.
5. Current product documentation.
6. Historical planning, phase, migration, and deployment notes.

Historical documents describe the state or intention at their stated date and do not override the final frozen evidence.
