# 05 — Current architecture and evidence boundaries

## Product architecture

```text
Instructor
  -> React workspace
  -> FastAPI authentication and course authorization
  -> temporal learner/course state
  -> exactly bound saved analysis or prediction
  -> deterministic schema, evidence, policy and quality validation
  -> instructor triage
  -> support-case workflow
  -> immutable/auditable history
```

Streamlit remains a legacy/fallback client. It does not define the current presentation architecture.

## Empirical path

```text
OULAD AAA/2013J
  -> canonical observations
  -> cutoff-safe weekly states
  -> provenance links
  -> E1 Logistic Regression evaluation
```

E1 is a research evaluation path. The operational product may also contain legacy `simple-rules-v1` records for empirical workflow demonstration. Those records are uncalibrated demo scores and are not E1 results.

## Operational Qwen path

```text
Workspace events
  -> versioned snapshot and snapshot head
  -> analysis job and attempt
  -> Qwen2.5:7b structured output
  -> deterministic validation
  -> bounded repair or quality abstention
  -> saved analysis with model/prompt/contract provenance
  -> React instructor review
```

This path measures operational behavior. It is not the empirical predictor and does not provide calibrated probabilities.

## Controlled E2 path

```text
Frozen 48-case E2 v2 protocol
  -> plain_llm v2 / schema_only v2
  -> deterministic offline rescoring
  -> archived raw and rescored results
```

E2 is separate from operational job history and E1 outcome evaluation.

## State and workflow separation

| Concept | Meaning | Mutation rule |
|---|---|---|
| Observation | Source fact available at a declared time | Immutable/versioned |
| Temporal state | Derived evidence at one cutoff | Rebuildable and versioned |
| Prediction/analysis | Model result bound to an exact state/snapshot | Historical result remains immutable |
| Risk state | Model-derived band or status | Does not become instructor judgment |
| Triage status | Instructor attention/priority decision | Independent audited lifecycle |
| Support case | Longitudinal human-support record | Independent versioned lifecycle |
| Support action | Note, review, follow-up or closure event | Append-only/audited history |

Risk State, Triage Status, and Support Case Status are not interchangeable. Human actions do not rewrite score, evidence, cutoff, model, prompt, or prediction provenance.

## Temporal safeguards

- Features use only observations available at or before the checkpoint.
- E4 audits 194,590 provenance rows with 0 cutoff violations.
- A displayed prediction must reference the exact displayed state.
- Missing current predictions are not replaced silently with older predictions.
- Comparisons use the immediately previous eligible checkpoint and require compatible semantics.
- Learner-grouped evaluation prevents one trajectory crossing split boundaries.
- Training-only preprocessing and validation-based threshold selection protect the untouched E1 test evaluation.

## Reliability and security safeguards

- Browser sessions and course grants protect the React/API boundary.
- Mutations use CSRF protection where applicable, idempotency keys, audit records, and optimistic version checks.
- Analysis jobs, attempts, inference traces, and snapshot heads preserve runtime lineage.
- Invalid LLM outputs are rejected, boundedly repaired, or abstained; they are not silently presented.
- Synthetic, replayed, empirical, and manual-test origins remain explicit.

## Evidence boundaries

| Evidence | Establishes | Does not establish |
|---|---|---|
| E1 OULAD evaluation | Checkpoint-specific Logistic Regression discrimination | Qwen accuracy, calibration, or cross-course generalization |
| E4 audit | Cutoff integrity and provenance for audited artifacts | Predictive quality or universal adapter correctness |
| E2 controlled experiment | Effects of schema constraints on controlled grounding behavior | Operational success rate or educational effectiveness |
| Operational Qwen history | Validation, repair, abstention, latency and provenance behavior | Predictive accuracy or calibrated probability |
| Synthetic Workspace | Product, policy, worker and workflow behavior | Authentic learner behavior or empirical validity |
| Human-in-the-loop implementation | Traceable separation of model and human states | Improved instructor decisions or student outcomes |

## Source precedence

The controlling evidence is, in order: the final research evidence matrix, E2 run-validity report, operational LLM evidence report, frozen E1/E2/E4 artifacts, current product documentation, then dated historical phase and planning documents.
