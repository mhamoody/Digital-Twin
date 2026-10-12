# Operational LLM Version Evidence

## 1. Purpose and Scope

This report archives aggregate operational evidence about versioned Qwen-generated workspace analyses on Lobot. It describes contract compliance, validation, bounded repair, abstention, latency, and retained job history. It is not an empirical prediction study and does not report predictive accuracy.

## 2. Evidence Provenance

The source is read-only aggregate query output collected from the Lobot operational workspace database on 2026-10-12 and manually archived in `evaluation/results/llm_operational_lobot_snapshot_20261012.json`. No database dump, student-level record, raw model response, credential, or authentication material is included. The evaluation repository cannot independently reconstruct these aggregates from a database snapshot.

## 3. Fixed Model Identity

The mature v3.2 and v3.3 analyses used model `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, and wire contract `risk-decision-v3`. Holding model identity and wire contract fixed permits a limited operational comparison of saved validation outcomes. It does not create a controlled predictive comparison.

## 4. Version Evolution

Legacy versions predate the modern `validation_outcome` semantics:

| Version | Analyses | Average latency | Interpretation |
|---|---:|---:|---|
| course-risk-qwen-v2.1 | 356 | 7.944s | Modern validation outcome not recorded |
| course-risk-qwen-v2.2 | 67 | 8.030s | Modern validation outcome not recorded |

Their counts cannot be mapped retrospectively to first-pass, repaired, abstained, or rejected categories.

## 5. Validation and Repair Results

| Version | First-pass validated | Repaired | Quality abstained | First-pass share* | First-pass latency | Repair latency |
|---|---:|---:|---:|---:|---:|---:|
| v2.3 | 14 | 1 | 0 | 93.3% | 7.894s | 13.189s |
| v3.2 | 6,914 | 305 | 0 | 95.8% | 5.639s | 12.576s |
| v3.3 | 12,600 | 361 | 12 | 97.2% | 5.266s | 11.115s |

\* Share among saved validated outputs; this is not predictive accuracy. For v3.2 the validated-output denominator is 7,219; for v3.3 it is 12,961. Quality abstentions and failed jobs are not silently added to either denominator.

Among saved validated analyses, v3.3 achieved a higher first-pass validation share and a lower repair share than v3.2 under the same Qwen2.5:7b model identity and `risk-decision-v3` contract.

## 6. Overall Job Validation Outcomes

| Outcome or error category | Count | Interpretation |
|---|---:|---|
| Validated | 20,618 | Saved validated analyses across retained history |
| Abstained | 12 | Explicit no-score quality outcome |
| ANALYSIS_SUPERSEDED | 5,741 | Lifecycle/history state; not a normal model-quality failure |
| MODEL_ACTION_INVALID | 149 | Model/contract validation failure |
| MODEL_RISK_NOT_SUPPORTED | 64 | Model/contract validation failure |
| MODEL_ACTION_NOT_SUPPORTED | 58 | Model/contract validation failure |
| MODEL_SCHEMA_INVALID | 22 | Model/contract validation failure |
| MODEL_POLICY_CONFLICT | 8 | Model/contract validation failure |

The five model/contract validation categories total 301. `ANALYSIS_SUPERSEDED` records replacement in the analysis lifecycle, so combining it with rejected model outputs would misstate model quality. No overall success percentage is calculated because the retained categories do not establish a scientifically comparable denominator.

## 7. Deterministic Safety/Validation Boundary

Operational analyses pass through structured-output parsing, schema validation, evidence-reference checks, semantic and policy checks, bounded repair, and explicit quality abstention. Unsupported, malformed, or policy-conflicting outputs can be rejected instead of published as scores. This is evidence of an implemented safety boundary and operational contract compliance; it is not evidence that accepted scores predict academic outcomes accurately.

## 8. Metadata Limitation

`workspace_analysis_job` and `workspace_analysis_attempt` do not retain `prompt_version`, and no usable inference-trace table was present in the inspected live database. Failed jobs therefore cannot be reliably attributed to v3.2 or v3.3, and prompt version must not be inferred from timestamps. Because failed jobs do not retain prompt-version metadata, version-specific total failure rates cannot be reliably estimated from the current database.

## 9. What the Evidence Supports

- Versioned prompt evolution under a fixed mature model identity and wire contract.
- Deterministic validation and rejection of unsafe outputs.
- Bounded repair and explicit quality abstention.
- Lower repair share and higher first-pass share among saved validated v3.3 analyses than v3.2 analyses.
- Operational latency and retained job-category reporting.

## 10. What the Evidence Does Not Support

- Predictive accuracy, AUROC, Average Precision, or calibrated probabilities.
- Causal or educational correctness of recommendations.
- Improved learner outcomes or proven educator effectiveness.
- Generalization to real courses, institutions, or unseen populations.
- Superiority of Qwen over the empirical Logistic Regression baseline.
- A prompt-version comparison of total failure rates.

## 11. Relationship to E2

E2 is a controlled held-out research ablation: 48 frozen cases compare `plain_llm` with `schema_only` and evaluate structural, citation, semantic, constraint, abstention, and behavioral outcomes. The operational evidence is live workspace history across several prompt generations and records validation, repair, abstention, latency, and lifecycle states. Their settings, denominators, interventions, and outcome meanings differ. Their counts and rates must never be pooled.

## 12. Thesis-Safe Interpretation

The operational history demonstrates a versioned Qwen analysis pipeline with deterministic validation, bounded repair, quality abstention, and auditable saved outcomes. Among saved validated outputs, v3.3 required proportionally fewer repairs than v3.2 under the same mature model identity and wire contract. This is evidence of improved operational compliance among retained validated analyses, not improved predictive accuracy. Version-specific total failure rates remain unidentifiable because failure records do not retain prompt-version metadata.
