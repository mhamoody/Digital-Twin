# Final Research Evidence Matrix

This matrix keeps empirical prediction, temporal integrity, controlled grounding, operational reliability, engineering validation, and synthetic demonstration evidence separate. Engineering completion is not treated as scientific outcome evidence.

| Research area | Research question / claim | Evidence type | Dataset / setting | Experiment or implementation | Primary artifact(s) | Key metric/result | Evidence strength | Defensible conclusion | Important limitation | Thesis-safe wording | Claims NOT supported |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A. Temporal learner-state representation | Can observable learner state be reconstructed at declared checkpoints with versioned evidence? | Implementation plus empirical artifact | OULAD AAA/2013J | Cutoff-safe weekly state builder at weeks 3, 5, 8, 10 | Product `state/builder.py`; E1 manifest and comparison report | 383 source enrolments; 372 eligible learners; 1,464 states | STRONG INTEGRITY EVIDENCE | The system creates historized checkpoint states with explicit feature version and provenance | One historical presentation; fixed checkpoint calendar | A provenance-aware learner-state representation was instantiated at four course checkpoints | Real-time synchronization, psychological state, multi-course generalization |
| B. E1 empirical prediction | How does predictive signal evolve across early checkpoints? | Held-out empirical prediction evaluation | OULAD AAA/2013J | Learner-grouped Logistic Regression with train-only fitting and validation-selected thresholds | `e1_logistic_oulad_AAA_2013J_v1.csv`; `e1_feature_manifest.json`; `comparison_summary.md` | AUROC/AP: w3 .621/.379; w5 .657/.531; w8 .896/.819; w10 .834/.802 | STRONG EMPIRICAL within evaluated presentation | Predictive discrimination varied materially by checkpoint and was strongest at week 8 in this evaluation | Single presentation; test n=51–56 by checkpoint; not calibrated; no external validation | Logistic Regression produced checkpoint-specific held-out discrimination on AAA/2013J | Qwen accuracy, calibrated risk, generalization to other courses, superiority over all baselines |
| C. E4 cutoff integrity | Did any evaluated provenance link cross its checkpoint cutoff? | Deterministic temporal audit | Prepared OULAD AAA/2013J artifacts | Audit of activity and assessment-submission provenance | `e4_temporal_oulad_AAA_2013J_v1.csv`; `comparison_summary.md` | 194,590 provenance rows; 0 cutoff violations | STRONG INTEGRITY EVIDENCE | No post-cutoff provenance violation was found in the evaluated artifacts | Does not prove every future adapter or dataset is leakage-free | The audited artifacts contained no detected post-cutoff evidence across 194,590 provenance rows | Universal leakage prevention or correctness beyond audited artifacts |
| D. E2 controlled LLM grounding | Do structural constraints improve compliant evidence use and selective decisions? | Controlled held-out ablation | 48 deterministic cases, 12 families | `plain_llm` v2 vs `schema_only` v2 | Frozen v2 protocol/manifest; raw and rescored CSVs/summaries; `e2_run_validity.md`; SHA manifest | Plain: citations 0/48, behavior 24/48, abstention 0/48, constraints 0/48. Schema: full contract 48/48, citations 48/48, semantic 42/48, behavior 24/48, abstention 0/48, constraints 36/48 | CONTROLLED EXPERIMENT | Schema constraints substantially improved structural and citation compliance but did not improve abstention or behavioral accuracy | Synthetic deterministic cases; 48 cases; not predictive evaluation; conjunctive metrics | Structural control improved contract and evidence-reference compliance without solving selective decision behavior | 100% hallucination, predictive accuracy, universal reliability, real-course effectiveness |
| E. Operational LLM version reliability | How did saved validation and repair outcomes change across prompt versions? | Operational aggregate evidence | Lobot workspace database snapshot, 2026-10-12 | Versioned Qwen workspace analyses | `llm_operational_lobot_snapshot_20261012.json`; `llm_operational_version_evidence.md` | v3.2 first-pass 6,914/7,219 validated (95.775%); v3.3 12,600/12,961 (97.215%); repair shares 4.225% vs 2.785% | OPERATIONAL EVIDENCE | Among saved validated analyses, v3.3 had a higher first-pass and lower repair share than v3.2 under the same model identity and contract | Failed jobs lack prompt version; no version-specific total failure rate; no DB dump in repository | Operational compliance among saved validated outputs improved between the retained mature versions | Accuracy improvement, AUROC/AP, calibrated probabilities, causal correctness, Qwen superiority over Logistic Regression |
| F. Deterministic grounding/validation | Can unsupported or malformed generated analyses be withheld? | Implementation and operational validation | Workspace v2 analysis runtime | Schema, evidence, semantic, policy, repair, abstention, and rejection boundary | Product `workspace/llm.py`, `output_contract.py`, reliability docs/tests | 301 retained model/contract failure records across five categories; 12 quality abstentions | ENGINEERING VALIDATION plus OPERATIONAL EVIDENCE | The implemented validator can reject unsafe outputs and persist explicit abstentions | Counts are not a controlled error-rate denominator; accepted does not mean predictively correct | Generated analyses pass deterministic checks before a score is published | Elimination of hallucination or proof that every accepted decision is correct |
| G. HITL separation | Are model risk, instructor triage, and support-case status distinct? | Framework implementation and workflow tests | Product API, persistence and React workspace | Immutable analyses; versioned triage; independent support cases/events | Product workspace/persistence models, API/store, support tests | Separate tables/contracts and mutation paths; triage/support saves do not rewrite analyses | ENGINEERING VALIDATION / FRAMEWORK CONTRIBUTION | The architecture preserves distinct model, review, and support states | No educator study or outcome-effectiveness experiment | The framework separates model evidence from human review and longitudinal support records | Improved outcomes, reduced workload, or empirically proven usability |
| H. Auditability/state binding | Is each displayed analysis tied to the state it assessed and are updates auditable? | Integrity implementation and tests | v1 and v2 product paths | Exact state binding, input hashes, append-only histories, optimistic locking and idempotency | Product `api/service.py`, `api/comparison.py`, persistence/workspace stores and safeguard tests | Older predictions are not substituted for an unassessed current state; stale versions conflict | STRONG INTEGRITY EVIDENCE | Historical model evidence is preserved and workflow changes are independently versioned | Tested product invariants do not establish educational validity | Each accepted analysis is bound to a specific state and subsequent human actions remain auditable | Causal attribution or perfect concurrency safety in every deployment topology |
| I. Product/demo implementation | Can an instructor inspect evidence and record support decisions end to end? | Software and integration validation | FastAPI, React/Vite, SQLite/PostgreSQL, Lobot deployment | Login, course/checkpoint selection, roster, evidence, history, triage, cases, policy, model status | Product repository, tests and deployment documentation | Current product suite: 66 Python tests passed; TypeScript typecheck passed during final audit | ENGINEERING VALIDATION | A functioning instructor-facing workflow has been implemented | Not a formal usability study; browser evidence and deployments have environment-specific boundaries | The prototype operationalizes traceable review and support workflows | Proven adoption, usability, production LMS deployment or learning impact |
| J. Multi-course synthetic workspace | Can richer UI/workflow scenarios be exercised across courses? | Synthetic scenario and demo evidence | Generated Workspace v2 courses and learners | Synthetic generator, saved analyses and workflow demonstrations | Product `workspace/synthetic.py`, demo guide and workspace docs | Multiple synthetic courses/checkpoints support UI and operational scenarios | DEMO/SYNTHETIC ONLY | Synthetic records provide repeatable system and scenario validation | Fictional learners; no empirical predictive meaning | Synthetic courses exercise workflow, policy and interface behavior | Real-world predictive performance or multi-course empirical generalization |

## Evidence Integrity Notes

- E1 metrics are Logistic Regression test results, not Qwen results and not calibrated probabilities.
- E4 establishes zero detected violations only for the audited 194,590 provenance rows.
- E2 primary analysis includes only `plain_llm` v2 and valid `schema_only` v2. E2 v1, schema-only r1, original evidence-first, and post-hoc/incomplete evidence-first v2 are excluded.
- In the plain treatment, semantic validity and evidence constraints fail conjunctively because citation/contract requirements fail; this must not be restated as “100% hallucination.”
- `ANALYSIS_SUPERSEDED` is a lifecycle state and is excluded from the 301 model/contract validation failure total.
- Operational LLM shares use saved validated outputs as their denominator. Abstentions and failed jobs are not included.
- Operational history, E2 cases, empirical OULAD prediction, and synthetic Workspace scenarios use different evidence classes and denominators.
- `comparison_summary.md` predates the archived E2 run and still labels E2 unexecuted. The later frozen `e2_run_validity.md`, archived raw/rescored artifacts, and SHA manifest govern E2 status.

# Recommended Final Research Questions

## RQ1 — Temporal Prediction

**Question:** How does predictive performance evolve across cutoff-safe learner states at early course checkpoints?

**Evidence:** E1 empirical OULAD evaluation.

**Status:** Answered for Logistic Regression on AAA/2013J only. Performance changed by checkpoint, with the strongest observed AUROC/AP at week 8. This does not answer how Qwen performs as an empirical predictor or how results generalize to other courses.

## RQ2 — Temporal Integrity

**Question:** Can a provenance-aware temporal learner-state pipeline prevent post-cutoff information leakage while preserving traceability?

**Evidence:** E4 plus the versioned state/provenance implementation.

**Status:** Answered for the evaluated artifacts: 194,590 provenance rows produced zero detected cutoff violations. The conclusion must remain scoped to this pipeline version and artifact set.

## RQ3 — LLM Grounding and Reliability

**Question:** How do structural constraints and deterministic validation affect evidence compliance, abstention behavior, and operational reliability of LLM-generated instructor-facing analyses?

**Evidence:** E2 controlled ablation plus separately reported operational LLM evidence.

**Status:** Partially answered. E2 shows that schema constraints improve structural and citation compliance without improving abstention or behavioral accuracy. Operational history demonstrates validation, repair, abstention and rejection behavior, but it is not the same experiment and cannot be used to estimate predictive accuracy or version-specific total failure rates.

## RQ4 — Human-in-the-loop Traceability

**Question:** How can model risk, instructor triage, and longitudinal support decisions be represented separately while preserving historical model evidence?

**Evidence:** Implemented architecture, persistence invariants and workflow tests.

**Status:** Answered as a framework/system contribution. Educator usability, causal effectiveness and learner-outcome improvement remain unestablished.

# Research Contribution Hierarchy

## PRIMARY RESEARCH CONTRIBUTIONS

1. **Provenance-aware cutoff-safe temporal learner-state construction.** Supported by implemented state lineage and the E4 audit.
2. **Checkpoint-specific empirical analysis of predictive signal on OULAD.** Supported by E1 held-out Logistic Regression results on AAA/2013J.
3. **Controlled evidence that structural and citation compliance do not guarantee correct selective abstention or behavioral decisions.** Supported by the frozen E2 comparison of `plain_llm` and `schema_only`.

## SECONDARY RESEARCH CONTRIBUTIONS

4. **Versioned evidence-grounded operational LLM pipeline.** Deterministic validation, bounded repair, quality abstention and retained operational outcomes provide system-reliability evidence, subject to the prompt-version metadata limitation.
5. **Traceable separation of prediction, triage and support state.** Best framed as a system/framework contribution unless future educator evidence establishes human-factors outcomes.

## ENGINEERING CONTRIBUTIONS

- FastAPI contracts, course authorization and browser session/CSRF boundary.
- SQLite/PostgreSQL persistence, migrations, exact state binding, idempotency and optimistic locking.
- Workspace analysis worker, runtime diagnostics, scheduling and auditable attempts.
- OULAD ingestion, legacy compatibility and Lobot deployment tooling.

## PRODUCT FEATURES

- React instructor workspace, course/checkpoint selection, roster and learner evidence.
- Risk history, model/provenance views, course policy controls and data/model health.
- Instructor flags, watchlists, support cases, actions, follow-ups and audit history.
- Synthetic multi-course scenario demonstrations.

The React dashboard is a product interface for the contributions; it is not itself a research contribution.

# Recommended Thesis Contribution Wording

## A. One-sentence thesis contribution

This thesis presents and evaluates an auditable course digital-twin framework that constructs provenance-aware cutoff-safe learner states, measures checkpoint-specific predictive signal, validates evidence-grounded LLM analyses, and preserves a traceable separation between model risk, instructor triage and longitudinal support decisions.

## B. Contribution paragraph

This work contributes a provenance-aware temporal representation of learner activity at declared course checkpoints and evaluates it on the OULAD AAA/2013J presentation. A held-out empirical study measures how Logistic Regression discrimination changes across weeks 3, 5, 8 and 10, while a separate temporal audit finds no post-cutoff evidence among 194,590 evaluated provenance rows. A controlled 48-case LLM ablation shows that schema-constrained generation substantially improves structural and citation compliance, but does not by itself improve abstention or behavioral decision accuracy. The implemented pipeline therefore combines generated analysis with deterministic evidence and policy validation, bounded repair and explicit abstention. Finally, the system preserves model outputs as historical evidence while representing instructor triage and support actions as independently versioned, auditable human decisions.

## C. Concise supervisor explanation

The research story has three empirical layers and one framework layer. E1 measures checkpoint-specific predictive signal on real OULAD data; E4 verifies cutoff integrity and traceability; E2 tests how output structure affects LLM evidence compliance and decision behavior. Operational Qwen history then shows how validation, repair and abstention work in the deployed workspace without being treated as predictive accuracy. The product demonstrates the final framework principle: model risk, instructor review and support history remain separate and auditable.

## D. Claims We Must Not Make

- The project introduces a new neural architecture.
- Qwen is a universally accurate or empirically superior student-risk predictor.
- Qwen scores are calibrated probabilities.
- The operational LLM history establishes AUROC, Average Precision or predictive accuracy.
- Schema constraints eliminate hallucination or guarantee correct decisions.
- The system proves that interventions improve learner outcomes.
- Instructor usability or effectiveness has been empirically established.
- Results generalize across courses, institutions or populations.
- Synthetic/workspace results are empirical student-performance evidence.
- The system is a continuously synchronized real-time digital twin.
- The project is deployed as a production LMS, onQ or LTI integration.
- The excluded E2 treatments support the primary grounding conclusion.
