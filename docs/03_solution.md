# 03 — Current solution

## Solution in one sentence

Build provenance-aware learner states at declared checkpoints, evaluate empirical prediction separately, validate instructor-facing model evidence, and preserve instructor triage and longitudinal support decisions without altering historical model records.

## Implemented product flow

1. Source adapters create canonical observations with origin and availability.
2. The state builder creates versioned cutoff-safe learner states.
3. A prediction or operational analysis is bound to the exact state it used.
4. Deterministic schema, grounding, policy, freshness, and quality checks decide whether an output may be saved or shown.
5. The React workspace reads through FastAPI and shows the applicable state, evidence, history, and model provenance.
6. Instructor triage is recorded independently from model state.
7. Support cases and support actions use their own lifecycle and audit history.

Streamlit remains a legacy/fallback interface.

## Separate evidence paths

| Path | Purpose | Valid claim boundary |
|---|---|---|
| E1 empirical OULAD path | Checkpoint prediction with Logistic Regression | Predictive discrimination on AAA/2013J |
| E4 provenance path | Audit temporal lineage and cutoffs | Traceability and zero violations in audited artifacts |
| E2 controlled path | Compare plain and schema-constrained LLM output | Structural, citation, semantic, abstention, and behavioral findings on 48 cases |
| Operational Qwen path | Run validated instructor-facing analyses | Runtime validation, repair, abstention, latency, and provenance |
| Synthetic Workspace path | Exercise product and worker workflows | Demonstration and operational correctness only |
| Demo rules path | Exercise legacy empirical plumbing | Uncalibrated operational/demo score only |

These paths must not be merged into one accuracy claim.

## Empirical predictor

E1 uses Logistic Regression over cutoff-safe OULAD `AAA/2013J` states. Learner-grouped splits, train-only preprocessing, validation-based threshold selection, and untouched test evaluation protect the result. The reported AUROC/AP values are discrimination metrics rather than calibrated probabilities.

## Operational Qwen analysis

The mature operational model is `qwen2.5:7b` under `risk-decision-v3`. The pipeline records model, digest, prompt, contract, snapshot, attempt, validation, repair, abstention, and saved-analysis provenance.

The application:

- supplies allow-listed state evidence;
- requires structured output;
- validates evidence references and supported actions;
- performs deterministic semantic and policy checks;
- permits bounded repair;
- records explicit quality abstention; and
- refuses unsafe output rather than silently publishing it.

Operational raw scores are not calibrated probabilities. Operational evidence does not establish empirical predictive accuracy.

## Controlled E2 experiment

E2 uses 48 frozen cases and compares `plain_llm` v2 with `schema_only` v2. Schema-only output improves structural and citation compliance, but neither treatment demonstrates successful selective abstention or improved behavioral correctness. E2 is not the operational job history and does not use the E1 outcome evaluation.

## Human workflow

The model's risk state, instructor triage, and support-case lifecycle are separate persisted concepts. Instructor actions add review and support history; they do not modify the score, evidence, model identity, state cutoff, or model provenance that existed at prediction time.

## Failure-safe behavior

- Missing or stale evidence is represented explicitly.
- A current state never borrows an older incompatible prediction.
- Temporal comparison uses only the immediately previous eligible checkpoint under compatible model semantics.
- Invalid model output is rejected, repaired within policy, or abstained.
- Idempotency prevents duplicate actions.
- Optimistic locking exposes concurrent workflow updates.
- Authorization is enforced at the course boundary.

## Research and product boundary

React, FastAPI, authentication, persistence, support workflow, deployment, and workers make the research reviewable and demonstrable. They are engineering and product contributions. The principal research contributions are temporal state construction, checkpoint-specific empirical evaluation, and the controlled E2 finding about the limits of structural/citation compliance.
