# Research Evidence Guide

This guide is an index, not a replacement for the frozen artifacts. Authoritative paths and SHA-256 values are bound in:

- `repo_cleanup_audit/preservation_phase/canonical_research_evidence_manifest.md`
- `repo_cleanup_audit/preservation_phase/research_evidence_sha256_manifest.csv`
- `repo_cleanup_audit/phase2_execution/post_cleanup_hash_verification.csv`

Verified copies of sibling evaluation-repository evidence are under `repo_cleanup_audit/final_preservation/archive_verification_extract_A/research_evidence/Digital-Twin-evaluation/`. Archive B is a second verified copy.

## E1 — empirical prediction

| Field | Definition |
|---|---|
| Research question | How does predictive performance evolve across cutoff-safe learner states at early checkpoints? |
| Evidence type | Empirical predictive evaluation on OULAD `AAA/2013J` |
| Unit of analysis | Eligible learner at weeks 3, 5, 8, and 10 |
| Cohort | 383 source enrolments; 372 eligible learners; 1,464 states |
| Predictor | Logistic Regression over the frozen 20-feature model matrix |
| Canonical artifacts | Preserved `evaluation/results/e1_logistic_oulad_AAA_2013J_v1.csv`, `e1_feature_manifest.json`, and evaluation reports/source |
| Local supporting artifacts | `artifacts/evaluation/sprint5-aaa-2013j-v1/freeze/` and `validation/` |

Test AUROC/AP: week 3 0.621/0.379; week 5 0.657/0.531; week 8 0.896/0.819; week 10 0.834/0.802.

**Boundary:** these are ranking/discrimination results for Logistic Regression. Qwen did not produce E1 results. Scores are not calibrated probabilities; one course does not establish cross-course generalization; the zero-filled model matrix does not erase the canonical state’s missingness semantics.

## E2 — controlled LLM grounding

| Field | Definition |
|---|---|
| Research question | How do structural constraints affect grounding, behavioral correctness, and abstention? |
| Evidence type | Controlled designed-case experiment |
| Unit of analysis | One of 48 frozen cases across 12 families; 24 assessment-allowed and 24 abstention-expected |
| Model | `qwen2.5:7b`, with run-bound model metadata/digest |
| Canonical protocol | Preserved `evaluation/protocols/e2_grounding_heldout_v2.json`; normalized SHA-256 `6E423F63884145AD00273CF26C65B155C1EC11E3E62A1080C94F74DC807CDD0D` |
| Canonical interpretation | Preserved `evaluation/reports/e2_run_validity.md` and `final_research_evidence_matrix.md` |

Primary valid comparison:

| Treatment | Citation | Semantic contract | Constraint correctness | Behavioral correctness | Abstention |
|---|---:|---:|---:|---:|---:|
| `plain_llm` v2 | 0/48 | 0/48 | 0/48 | 24/48 | 0/48 |
| `schema_only` v2 | 48/48 | 42/48 | 36/48 | 24/48 | 0/48 |

**Boundary:** E2 uses synthetic designed cases, not student outcomes. Semantic failure is not automatically hallucination. E2 v1, invalid schema-only r1, defective original `evidence_first_full`, and incomplete post-hoc `evidence_first_full_v2` are excluded from the primary comparison. Structural compliance did not improve selective abstention or behavioral correctness.

## E4 — temporal consistency

| Field | Definition |
|---|---|
| Research question | Does the archived export respect checkpoint cutoffs while retaining traceability? |
| Evidence type | Temporal/provenance audit |
| Unit of analysis | Exported state-source link |
| Scope | 194,590 cutoff-filtered links |
| Canonical artifacts | Preserved `evaluation/results/e4_temporal_oulad_AAA_2013J_v1.csv` and evaluation source/report |

Result: zero recorded post-cutoff timestamps in the bounded archived scope.

**Boundary:** this does not independently establish complete feature-level lineage, source correctness, or universal leakage freedom.

## Operational LLM reliability

| Field | Definition |
|---|---|
| Research question | What publication/validation outcomes are recorded by the operational generated-analysis path? |
| Evidence type | Historical operational snapshot |
| Unit of analysis | Saved analysis/job lifecycle record, using the documented denominator for each measure |
| Canonical artifacts | Preserved `evaluation/results/llm_operational_lobot_snapshot_20261012.json` and `evaluation/reports/llm_operational_version_evidence.md` |
| Model/contract | `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, `risk-decision-v3` |

- v3.2: 6,914 first-pass, 305 repaired, 7,219 validated; 95.775% first-pass and 4.225% repair shares among validated outputs.
- v3.3: 12,600 first-pass, 361 repaired, 12 quality abstentions, 12,961 validated; 97.215% first-pass and 2.785% repair shares among validated outputs.
- Overall snapshot: 20,618 validated, 12 abstained, 5,741 `ANALYSIS_SUPERSEDED`, and 301 other validation/model-contract failures.

**Boundary:** selected saved-record denominators do not support a global success rate. `ANALYSIS_SUPERSEDED` is lifecycle history, not a normal quality failure. Other failed jobs cannot be reliably assigned to v3.2/v3.3. The evidence is not predictive accuracy or a controlled causal comparison, and v3.3 must not be called “more accurate.”

## Workflow/framework verification

| Field | Definition |
|---|---|
| Research question | How can model state, instructor triage, and support history remain separate and auditable? |
| Evidence type | Source, migration, API-contract, and regression-test verification |
| Unit of analysis | State/prediction binding or authenticated workflow transition |
| Canonical locations | `src/digital_twin/api/`, `persistence/`, `workspace/`; migrations `20260924_0006` and `20260929_0007`; current `tests/` |

Verified concerns include exact state binding, compatible temporal comparison, course authorization, immutable prediction/analysis history, independent triage, durable support actions, idempotency, optimistic locking, and stale-version handling.

**Boundary:** this is a framework/system contribution. It does not demonstrate educator effectiveness, improved student outcomes, causal intervention effects, or autonomous decision quality.

## Preservation rule

Do not edit any artifact to “correct” a result. New analyses require a new versioned directory, protocol/configuration record, raw output preservation, and a new manifest. Link to existing manifests rather than copying large evidence into documentation.

