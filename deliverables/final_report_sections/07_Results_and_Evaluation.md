# 5. Results and Evaluation

## 5.1 Evaluation Overview

This chapter reports the final evaluation through four research questions evaluated using five distinct evidence streams. The streams are reported separately because they use different populations, interventions, denominators, and definitions of success. E1 evaluates temporal prediction using held-out outcomes from one empirical OULAD presentation. E4 audits whether the source observations linked to those temporal states respected their checkpoint cutoffs. E2 is a controlled experiment on synthetic evidence scenarios that compares two output treatments for the same local language model. Operational LLM evidence describes saved validation, repair, abstention, latency, and failure records from the Lobot workspace. RQ4 is evaluated through verified implementation invariants rather than through a user-effectiveness experiment.

This separation is necessary for valid interpretation. The Logistic Regression scores in E1 are the only results in this chapter associated with empirical learner outcomes and AUROC or Average Precision. E2 does not estimate student-risk prediction, and its controlled cases are not OULAD learner records. Operational Qwen records have no predictive ground-truth labels and therefore cannot be compared with E1 as accuracy results. The RQ4 evidence establishes that the system represents model and human states separately, but it does not measure whether instructors make better decisions or whether students achieve better outcomes.

**Table 5.1. Evaluation streams and claim boundaries**

| Research question | Evidence stream | Evaluation population | Primary measures | Claim boundary |
|---|---|---|---|---|
| RQ1 — Temporal Prediction | E1 empirical evaluation | OULAD `AAA/2013J`; 372 eligible learners and 1,464 checkpoint states | Test AUROC, Average Precision, validation-selected threshold metrics, bootstrap intervals | Checkpoint-specific discrimination for Logistic Regression in the evaluated presentation |
| RQ2 — Temporal Integrity | E4 deterministic provenance audit | 194,590 exported activity and assessment-submission provenance rows | Rows audited and violations where `source_time > checkpoint_time` | Cutoff integrity of the frozen artifacts and implemented preparation/state-building path |
| RQ3 — Controlled grounding | E2 frozen experiment | 48 cases across 12 scenario families | Contract, citation, semantic, constraint, abstention, and behavioral measures | Controlled behavior of `qwen2.5:7b` under the two valid treatments |
| RQ3 — Operational reliability | Archived Lobot aggregate evidence | Saved workspace analyses and retained job outcomes through 12 October 2026 | First-pass validation, repair, quality abstention, latency, and rejection categories | Operational contract behavior; not predictive accuracy or calibration |
| RQ4 — HITL Traceability | Framework and system verification | Persistence, API, React workflow, and safeguard tests | Verified categorical invariants | Separation and auditability of model, triage, and support state; not educator effectiveness |

The remainder of the chapter reports the observed results, interprets them within their declared scope, and states the limitations that prevent broader conclusions.

## 5.2 E1 Empirical Prediction Results

E1 used dataset version `oulad_AAA_2013J_v1` for presentation `oulad:AAA:2013J`. The source contained 383 enrolments, of which 372 learners produced at least one eligible checkpoint state. State construction produced 371 states at week 3, 368 at week 5, 365 at week 8, and 360 at week 10, for a total of 1,464 states. The learner-grouped split contained 260 training learners, 56 validation learners, and 56 test learners. As described in Chapter 3, a separate Logistic Regression pipeline was fitted at every checkpoint using the same ordered 20-feature manifest. Thresholds were selected by validation F1 and the test partition was used only after preprocessing, fitting, and threshold selection had been fixed.

Table 5.2 reports the frozen test discrimination results. Test sample size falls from 56 at week 3 to 51 at week 10 because eligibility was reassessed at each checkpoint. The number of positive test outcomes similarly falls from 13 to 8. These changing test populations are part of the checkpoint-specific design and should be considered when comparing values across time.

**Table 5.2. E1 checkpoint-specific empirical prediction results**

| Checkpoint | Eligible states | Test states | Positive test outcomes | Validation threshold | Test AUROC | Test Average Precision |
|---|---:|---:|---:|---:|---:|---:|
| Week 3 | 371 | 56 | 13 | 0.25 | 0.621 | 0.379 |
| Week 5 | 368 | 55 | 12 | 0.41 | 0.657 | 0.531 |
| Week 8 | 365 | 54 | 11 | 0.49 | 0.896 | 0.819 |
| Week 10 | 360 | 51 | 8 | 0.58 | 0.834 | 0.802 |

> **[Figure 5.1 placeholder — Replace with the final E1 AUROC and Average Precision checkpoint chart during visual integration.]** The figure should plot the two frozen discrimination measures at weeks 3, 5, 8, and 10 without implying significance between checkpoints.

At week 3, AUROC was 0.621 and Average Precision was 0.379. This indicates modest early ranking signal, with considerable uncertainty around both estimates. At week 5, AUROC increased numerically to 0.657 and Average Precision to 0.531. By week 8, the frozen evaluation produced its highest numerical discrimination, with AUROC 0.896 and Average Precision 0.819. Week 10 remained strong at AUROC 0.834 and Average Precision 0.802, although its AUROC was numerically below the week-8 value.

The pattern answers RQ1 within the evaluated presentation: the available predictive signal changed materially across checkpoints and became substantially stronger after more course evidence had accumulated. The results do not establish that week 8 is significantly better than week 10. The checkpoint samples are related through repeated learners, their eligible populations differ, and the frozen artifacts do not contain a paired statistical test comparing checkpoint estimates. The correct conclusion is therefore that week 8 was numerically strongest in this evaluation, while week 10 also retained strong discrimination.

The values produced by `predict_proba` were used as model scores for ranking and threshold evaluation. No calibration procedure was fitted or approved. Consequently, neither the reported score nor a threshold should be interpreted as a calibrated probability of non-success. The results also apply only to Logistic Regression on `AAA/2013J`; they are not Qwen results and do not establish generalization to other presentations, courses, or institutions.

## 5.3 E1 Interpretation and Error Perspective

The threshold-dependent results provide a second view of model behavior. At week 3, the validation-selected threshold of 0.25 produced precision 0.256, recall 0.769, and F1 0.385. The confusion matrix was 14 true negatives, 29 false positives, 3 false negatives, and 10 true positives. This threshold favored sensitivity to the risk class, but the large number of false positives illustrates the limited specificity of the early checkpoint.

At week 5, the threshold was 0.41. Precision was 0.241, recall 0.583, and F1 0.341, with 21 true negatives, 22 false positives, 5 false negatives, and 7 true positives. Although AUROC and Average Precision were numerically higher than at week 3, the threshold-dependent F1 was lower. This is not contradictory: AUROC and Average Precision summarize ranking across thresholds, while F1 describes one operating point selected on validation data.

At week 8, the threshold of 0.49 produced precision 0.643, recall 0.818, and F1 0.720. The confusion matrix contained 38 true negatives, 5 false positives, 2 false negatives, and 9 true positives. At week 10, the threshold of 0.58 produced precision 0.600, recall 0.750, and F1 0.667, with 39 true negatives, 4 false positives, 2 false negatives, and 6 true positives. The later checkpoints therefore combined stronger ranking results with fewer false-positive classifications at their respective validation-selected thresholds.

The frozen percentile bootstrap intervals also show why point estimates require restraint. At week 3, the 95% intervals were 0.409–0.822 for AUROC, 0.199–0.665 for Average Precision, and 0.217–0.538 for F1. At week 5 they were 0.461–0.839, 0.270–0.757, and 0.143–0.524. At week 8 they were 0.722–0.993, 0.582–0.977, and 0.476–0.889. At week 10 they were 0.582–1.000, 0.476–1.000, and 0.333–0.880. The intervals are wide, especially where the test set contains few positive outcomes. They support the presence of useful later-course signal but do not justify fine-grained claims of superiority between checkpoints.

Several factors may accompany the temporal pattern. Later states contain longer cumulative activity histories and more assessment-participation evidence, while already unregistered learners become ineligible at later checkpoints. These are design facts, not newly tested causal explanations. No new subgroup, learner-level, or error-cluster analysis was conducted for this chapter. The observed results should therefore be interpreted as checkpoint-specific behavior of one transparent baseline under the frozen protocol.

## 5.4 E4 Temporal Integrity Results

E4 tested the provenance links exported for the same empirical state-building path. Each row connected a learner state to one activity or assessment-submission observation and recorded both the source time and checkpoint time. A violation was defined before inspection as `source_time > checkpoint_time`. Table 5.3 reproduces the complete grouping present in the frozen E4 CSV.

**Table 5.3. E4 provenance audit results**

| Checkpoint | Source type | Provenance rows | Cutoff violations |
|---|---|---:|---:|
| Week 3 | Activity | 32,678 | 0 |
| Week 3 | Assessment submission | 306 | 0 |
| Week 5 | Activity | 41,834 | 0 |
| Week 5 | Assessment submission | 353 | 0 |
| Week 8 | Activity | 56,041 | 0 |
| Week 8 | Assessment submission | 600 | 0 |
| Week 10 | Activity | 62,097 | 0 |
| Week 10 | Assessment submission | 681 | 0 |
| **Total** | **All audited sources** | **194,590** | **0** |

> **[Figure 5.2 placeholder — Replace with the final E4 provenance audit summary during visual integration.]** The figure should show audited row volume by checkpoint and source type while making the zero-violation result explicit.

No provenance row in the inspected frozen export used source evidence whose source time exceeded the associated checkpoint cutoff. The zero observed violations directly support the temporal-integrity claim for the audited preparation and state-building artifacts. The increasing activity row count across checkpoints is expected because cumulative states can cite a longer history at later cutoffs; it is not a measure of prediction quality.

The result does not establish universal leakage freedom. E4 can detect a recorded source observation linked after its checkpoint, but it cannot determine whether an event was absent from the original source, whether source timestamps were themselves erroneous, or whether a future adapter would implement the same filtering rules. Its conclusion is restricted to the 194,590 inspected links, the declared source-time fields, and the frozen pipeline version.

## 5.5 E2 Controlled LLM Grounding Results

E2 evaluated `qwen2.5:7b` under the frozen `e2_grounding_heldout_v2` protocol. The canonical LF-normalized protocol SHA-256 was `6E423F63884145AD00273CF26C65B155C1EC11E3E62A1080C94F74DC807CDD0D`, and the model digest was `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`. The protocol contained 48 cases across 12 scenario families, divided evenly between 24 cases where assessment was allowed and 24 where abstention was expected. Both primary treatments used temperature 0, seed 42, `num_ctx=8192`, and `num_predict=1200`.

The valid primary comparison contains `plain_llm` v2 from source run `lobot-e2-v2-r2`, deterministically rescored as `lobot-e2-v2-r2-rescored-v1`, and `schema_only` v2 from `lobot-e2-v2-schema-only-r2`, rescored as `lobot-e2-v2-schema-only-r2-rescored-v2`. Earlier diagnostic, structurally incomplete, implementation-defective, and incomplete post-hoc evidence-first treatments were excluded and do not contribute to Table 5.4.

**Table 5.4. E2 controlled grounding results**

| Metric | `plain_llm` v2 | `schema_only` v2 |
|---|---:|---:|
| Completed model calls | 48/48 (100%) | 48/48 (100%) |
| Schema valid / full output contract valid | 48/48 (100% schema valid) | 48/48 (100% full contract valid) |
| Citation valid | 0/48 (0%) | 48/48 (100%) |
| Semantic evidence valid | 0/48 (0%) | 42/48 (87.5%) |
| Evidence-constraint correct | 0/48 (0%) | 36/48 (75%) |
| Cases with unsupported claims | 2/48 (4.17%) | 6/48 (12.5%) |
| Cases with contradictions | 2/48 (4.17%) | 6/48 (12.5%) |
| Accepted by recorded run status | 48/48 (100%) | 48/48 (100%) |
| Abstained | 0/48 (0%) | 0/48 (0%) |
| Behavioral correctness | 24/48 (50%) | 24/48 (50%) |

All citation, semantic, constraint, and behavioral rates in the frozen rescored summaries used 48 evaluable cases. The `plain_llm` outputs were JSON-parseable and marked schema-valid by the applicable baseline check, but they did not cite the supplied evidence identifiers. The schema-constrained treatment required the complete top-level and claim-item contract and achieved complete structural and citation compliance.

> **[Figure 5.3 placeholder — Replace with the final E2 controlled compliance comparison during visual integration.]** The figure should compare citation validity, semantic evidence validity, evidence-constraint correctness, and behavioral correctness without combining them into an overall quality score.

## 5.6 E2 Interpretation

The clearest controlled effect was on output structure and citation behavior. Citation validity changed from 0/48 for `plain_llm` to 48/48 for `schema_only`. Full output-contract validity was 48/48 for the valid schema-constrained treatment. Semantic evidence validity rose from 0/48 to 42/48, and evidence-constraint correctness rose from 0/48 to 36/48.

The plain treatment’s semantic zero must be interpreted according to the scorer definition. Semantic evidence validity was conjunctive: it required valid evidence citations as well as the absence of future-evidence use, prohibited causal language, and scenario-specific semantic violations. Since plain generation supplied no valid evidence references, every case failed the combined measure. This result is not evidence that all plain responses were hallucinations, nor is it a direct estimate of a real-world hallucination rate.

Structural enforcement did not solve selective behavior. Neither treatment abstained in any case. Because exactly half of the protocol expected assessment and half expected abstention, both treatments achieved behavioral correctness of 24/48. Schema constraints therefore improved how answers were represented and referenced without changing the decision to answer rather than abstain.

Perfect citation validity also did not imply faithful interpretation. Six schema-constrained cases contained an unsupported claim and six contained a contradiction; semantic evidence validity was consequently 42/48 rather than 48/48. Evidence-constraint correctness was 36/48, with failures concentrated in cases that required selective handling of missing feeds, conflicting evidence, or insufficient evidence. An evidence identifier can exist and be formatted correctly while the associated claim still misinterprets its value or the applicable policy.

The frozen E2 conclusion is therefore specific: schema-constrained generation substantially improved structural and citation compliance, but did not by itself improve selective abstention or behavioral decision accuracy. The controlled comparison supports the use of structural output constraints as one layer of a reliability boundary. It also shows why deterministic semantic, evidence, policy, and abstention checks remain necessary after successful schema validation.

## 5.7 Operational LLM Reliability Results

Operational evidence was collected through read-only aggregate queries of the Lobot workspace database and archived on 12 October 2026. It describes saved analyses and retained job outcomes produced by the workspace pipeline. It is separate from E2 and has no empirical learner-outcome labels. The mature v3.2 and v3.3 records used the same `qwen2.5:7b` model digest and `risk-decision-v3` wire contract.

Table 5.5 reports only categories available under each version’s stored semantics. Versions v2.1 and v2.2 predate the modern `validation_outcome` field and therefore cannot be retrospectively divided into first-pass, repaired, or abstained outcomes.

**Table 5.5. Operational LLM version evidence**

| Version | First-pass validated | Repaired validated | Quality abstained | Available first-pass / overall latency | Repair average latency | Interpretation boundary |
|---|---:|---:|---:|---:|---:|---|
| v2.1 | Not available under earlier validation semantics | Not available | Not available | 7.944 s overall | Not available | 356 saved analyses; modern outcome breakdown unavailable |
| v2.2 | Not available under earlier validation semantics | Not available | Not available | 8.030 s overall | Not available | 67 saved analyses; modern outcome breakdown unavailable |
| v2.3 | 14 | 1 | 0 | 7.894 s | 13.189 s | Small bridge version; 15 saved validated outputs |
| v3.2 | 6,914 | 305 | 0 | 5.639 s | 12.576 s | Shares use 7,219 saved validated outputs only |
| v3.3 | 12,600 | 361 | 12 | 5.266 s | 11.115 s | Shares use 12,961 saved validated outputs; abstentions are separate |

The presence of repaired records demonstrates that the bounded correction path was exercised operationally. The higher latency of repaired outputs is consistent with the additional generation step, but the aggregates do not identify a causal performance effect of any individual prompt change. Quality abstention appears explicitly in v3.3 as a no-score outcome rather than being counted as a validated analysis.

The overall retained job history provides additional evidence about the implemented rejection boundary. Table 5.6 reproduces the frozen categories. `ANALYSIS_SUPERSEDED` is kept separate because it records replacement in the state/job lifecycle rather than a normal model-quality failure.

**Table 5.6. Operational job outcome categories**

| Outcome or error category | Count | Interpretation |
|---|---:|---|
| Validated | 20,618 | Saved validated analyses across retained history |
| Abstained | 12 | Explicit no-score quality outcome |
| `ANALYSIS_SUPERSEDED` | 5,741 | Lifecycle/history state; not a normal model-quality failure |
| `MODEL_ACTION_INVALID` | 149 | Model/contract validation failure |
| `MODEL_RISK_NOT_SUPPORTED` | 64 | Model/contract validation failure |
| `MODEL_ACTION_NOT_SUPPORTED` | 58 | Model/contract validation failure |
| `MODEL_SCHEMA_INVALID` | 22 | Model/contract validation failure |
| `MODEL_POLICY_CONFLICT` | 8 | Model/contract validation failure |
| **Non-superseded model/contract failures** | **301** | Sum of the five validation-failure categories |

These counts demonstrate that unsupported, malformed, or policy-conflicting outputs could be retained as failed jobs instead of being published as normal analyses. They do not supply a controlled error rate because the available job categories span different lifecycle states and do not provide a scientifically comparable global denominator.

## 5.8 Operational Version Comparison

The mature comparison is restricted to saved validated v3.2 and v3.3 analyses. For v3.2, 6,914 of 7,219 saved validated outputs were first-pass validated, giving a first-pass share of 95.775%; 305 were repaired, giving a repair share of 4.225%. For v3.3, 12,600 of 12,961 saved validated outputs were first-pass validated, giving a first-pass share of 97.215%; 361 were repaired, giving a repair share of 2.785%. The 12 v3.3 quality abstentions are outside the 12,961 saved-validated denominator.

> **[Figure 5.4 placeholder — Replace with the final operational v3.2 versus v3.3 saved-validated outcome chart during visual integration.]** The figure should compare first-pass and repaired shares using each version’s saved-validated denominator and display quality abstentions separately.

Among saved validated analyses, v3.3 therefore had a numerically higher first-pass share and a lower repair share than v3.2 under the same model identity and wire contract. First-pass average latency was also numerically lower, changing from 5.639 seconds to 5.266 seconds. Repair average latency changed from 12.576 seconds to 11.115 seconds. No significance test was conducted, and the archived evidence does not establish that the prompt/runtime version alone caused the differences.

The comparison is about retained contract compliance, not predictive accuracy. It does not show that v3.3 predicted learner outcomes more accurately, produced calibrated probabilities, or generated educationally better advice. The absence of prompt-version attribution for failed jobs also means that the saved-output shares cannot be expanded into version-specific total success or failure rates.

## 5.9 Operational Failure and Abstention Analysis

Across retained LLM job history, 20,618 jobs were recorded as validated and 12 as abstained. A further 301 jobs were retained across five model or contract validation-failure categories. The largest category was `MODEL_ACTION_INVALID` with 149 records, followed by `MODEL_RISK_NOT_SUPPORTED` with 64, `MODEL_ACTION_NOT_SUPPORTED` with 58, `MODEL_SCHEMA_INVALID` with 22, and `MODEL_POLICY_CONFLICT` with 8. These categories show that the pipeline distinguished different reasons for withholding output rather than reducing all failures to one generic runtime error.

The 5,741 `ANALYSIS_SUPERSEDED` records have a different meaning. A job can be superseded when a newer snapshot or applicable configuration replaces the state for which it was queued. Retaining that record preserves lifecycle history, but it does not indicate that the model generated an invalid answer. Treating superseded jobs as ordinary model failures would overstate model-quality problems and obscure the state-management behavior that produced them.

The operational aggregates do not support an overall success percentage. They do not demonstrate that all retained jobs were exposed to an identical opportunity for inference, and accepted validation does not mean agreement with a future learner outcome. More importantly, `workspace_analysis_job` and `workspace_analysis_attempt` did not retain reliable `prompt_version` metadata for failures, and no usable inference-trace data were available in the inspected operational evidence for reliable prompt-version attribution. Failed records cannot therefore be assigned reliably to v3.2 or v3.3, and their versions must not be inferred from timestamps.

Quality abstention is a deliberate no-score pathway. Its presence demonstrates that the operational contract can withhold a risk assessment when the configured evidence-quality gate is not satisfied. The count of 12 does not establish an optimal abstention rate. E2 showed that the model itself did not selectively abstain under either primary controlled treatment, while the operational pipeline could still enforce a quality abstention before publication. This contrast illustrates complementary layers, but the E2 and operational counts remain separate and are not pooled.

## 5.10 RQ4 Human-in-the-Loop Traceability Evaluation

RQ4 was evaluated through system invariants verified in the persistence model, service and store layers, API contracts, frontend behavior, and safeguard tests. It was not evaluated through an educator trial. Table 5.7 records the relevant observed implementation status and the boundary of each result.

**Table 5.7. HITL traceability verification**

| Invariant | Implementation mechanism | Verification evidence | Observed status | Claim boundary |
|---|---|---|---|---|
| Exact state binding | Analysis and prediction records reference the exact state or snapshot shown | Backend selection logic and prediction-binding tests | Verified in implemented paths | Does not establish predictive correctness |
| Immutable analysis history | Model output and provenance are separate from workflow mutations | Persistence models and workflow-immutability tests | Verified | Application-level invariant within tested paths |
| Independent triage state | Flags, watchlist, priority, and note use a separate versioned record | Workspace store/API and triage-history tests | Implemented and verified | No claim that triage improves decisions |
| Independent support-case lifecycle | Case status, actions, notes, and follow-up are persisted separately | Support persistence/API/dashboard tests | Implemented and verified | No intervention-effect claim |
| Optimistic locking | Mutations submit `expected_version`; stale versions return conflicts | Store conditions and conflict tests | Verified | Does not eliminate every distributed-concurrency risk |
| Idempotent retries | Actor/request key and request hash protect supported retryable mutations | Store uniqueness checks and retry tests | Verified | Applies to endpoints that declare idempotency |
| Append-only event history | Triage and support mutations add event/action records | Event tables and history retrieval tests | Verified | Current views still depend on correct application queries |
| Adjacent-checkpoint comparison | Comparison requires the immediately previous eligible checkpoint and compatible semantics | Comparison policy and regression tests | Verified | Observational comparison, not causal attribution |

The resulting representation maintains the intended distinction: **Risk State ≠ Instructor Triage Status ≠ Support Case Status**. An instructor can update triage or open, progress, and close a support case without changing the historical score, claims, cited evidence, state identity, or model provenance. When later states arrive, prior analyses remain associated with their original checkpoints. The current view does not silently borrow an older prediction for an unassessed current state.

This evidence answers RQ4 as a framework and system result. It shows that the implemented architecture can preserve responsibility and sequence across model and human records. It does not establish that educators find the interface usable, that triage is correct, that follow-up reduces workload, or that support actions cause improved learner outcomes.

## 5.11 Results by Research Question

**RQ1 — Temporal Prediction.** Within OULAD `AAA/2013J`, Logistic Regression discrimination varied across cutoff-safe checkpoints. Early discrimination was modest at weeks 3 and 5. The numerically strongest frozen discrimination occurred at week 8, with AUROC 0.896 and Average Precision 0.819, while week 10 remained strong at 0.834 and 0.802. The result demonstrates checkpoint-dependent predictive signal in this presentation. It does not establish calibration, cross-course generalization, causal explanation, or intervention effectiveness.

**RQ2 — Temporal Integrity.** The frozen E4 export contained 194,590 provenance links across activity and assessment-submission sources. None met the predeclared violation condition `source_time > checkpoint_time`. This supports the cutoff integrity and traceability of the inspected preparation and state-building artifacts. It does not guarantee that other datasets, unrecorded events, or future adapters are leakage-free.

**RQ3 — LLM Grounding and Reliability.** Under the controlled E2 protocol, schema constraints changed citation validity from 0/48 to 48/48, semantic evidence validity from 0/48 to 42/48, and constraint correctness from 0/48 to 36/48. They did not change abstention or behavioral correctness: both treatments abstained in 0/48 cases and were behaviorally correct in 24/48. Separately, operational records demonstrated structured validation, bounded repair, explicit abstention, and retained rejection categories. Among saved validated outputs, v3.3 had a higher first-pass and lower repair share than v3.2, but predictive accuracy and version-specific total failure rates remain unidentified.

**RQ4 — Human-in-the-Loop Traceability.** The implemented framework stores model risk, instructor triage, and longitudinal support state independently. Exact state binding, immutable historical analyses, expected-version conflicts, idempotent retries, append-only events, and adjacent-checkpoint comparison were verified in the implemented paths. This is evidence of traceability and state separation, not of educator effectiveness or improved learner outcomes.

Together, the four results support an auditable course digital-twin framework in which empirical prediction, temporal integrity, controlled LLM behavior, operational reliability, and human workflow are connected but evaluated according to different claim boundaries.

## 5.12 Evaluation Limitations

E1 is limited to one historical OULAD presentation and one transparent model family. The eligible cohort contained 372 learners, while the test population ranged from 56 states at week 3 to 51 at week 10 and contained only 8–13 positive outcomes per checkpoint. This produces wide bootstrap intervals and limits fine-grained comparisons. The target combines `Fail` and `Withdrawn`, although those outcomes may reflect different pathways. No external course or institutional validation was completed, no calibration method was approved, and the output scores must not be treated as calibrated probabilities. The study also does not compare every plausible baseline or establish causal reasons for the temporal pattern.

E4 is a deterministic audit of an exported artifact, not a universal proof. It verifies that the inspected links did not reference recorded evidence after their cutoffs. It cannot detect source events that were never recorded, establish that every source timestamp is correct, or guarantee that a different adapter will implement availability semantics correctly. Zero observed violations therefore means zero detected violations within the frozen 194,590-row export and implemented path.

E2 uses 48 synthetic controlled cases and one local model identity. The cases permit precise testing of missingness, policy, citation, and abstention conditions, but they do not reproduce the full distribution of real instructor-facing decisions. The deterministic evaluator operationalizes declared rules and can itself omit forms of semantic error that were not encoded. The primary conclusion uses only `plain_llm` v2 and the valid `schema_only` v2 treatment. Earlier diagnostics, schema-only r1, the implementation-defective original evidence-first treatment, and the incomplete post-hoc evidence-first v2 treatment are excluded. The plain treatment’s conjunctive semantic zero is not a real-world hallucination rate.

Operational evidence is observational aggregate history from one runtime environment. It was not produced through a randomized prompt experiment. Hardware, model serving, job scheduling, and workload affect latency and retained outcomes. Failed jobs lack reliable prompt-version attribution, which prevents version-specific total failure or success rates. No global operational success rate is reported. Saved validation means that an output passed implemented contract checks; it does not mean the score predicted an academic outcome correctly. Operational records contain no predictive ground-truth labels and cannot establish AUROC, Average Precision, calibration, educational correctness, or causal benefit.

RQ4 is limited to implementation and framework verification. Automated tests and persistence constraints demonstrate the intended behavior under covered conditions, but they are not a formal educator usability study. No study measured instructor comprehension, workload, decision agreement, automation bias, adoption, or decision quality. No intervention-effect experiment assessed whether support cases or actions changed learner outcomes. Institutional onQ/LTI production integration and cross-institution operation also remain outside the evaluated evidence.

These limitations define the scope of the final conclusions. The project provides held-out empirical evidence for checkpoint-specific prediction, deterministic integrity evidence for the inspected provenance, controlled evidence about structural LLM constraints, operational evidence about validation and repair, and system evidence for traceable human oversight. It does not combine those results into a claim of universally accurate, calibrated, causal, real-time, or institutionally validated prediction.
