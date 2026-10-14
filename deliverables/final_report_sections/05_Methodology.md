# 3. Methodology

## 3.1 Research Design

This study used a multi-part evaluation design because the project makes several claims that cannot be tested with a single dataset or metric. The empirical claim concerns whether cutoff-safe learner states contain predictive signal at different stages of a course. The temporal-integrity claim concerns whether the evidence used to construct those states was available by the applicable checkpoint. For LLM output, E2 tests how structural schema constraints affect contract compliance, evidence use, and assessment-versus-abstention behavior, while the separate operational analysis characterizes how deterministic checks govern acceptance, bounded repair, quality abstention, and rejection. The human-in-the-loop claim concerns whether model outputs and subsequent instructor decisions can remain distinct and auditable. Treating these as separate evidence streams prevents software completion, synthetic demonstrations, or operational model records from being interpreted as empirical educational validity.

The methodology comprised six connected components. First, OULAD records were prepared as canonical course, enrolment, resource, assessment, activity, and assessment-submission observations. Second, those observations were aggregated into versioned temporal learner states at weeks 3, 5, 8, and 10. Third, E1 evaluated a Logistic Regression model independently at each checkpoint using a learner-grouped train/validation/test design. Fourth, E4 audited the temporal provenance behind the constructed states. Fifth, E2 compared plain and schema-constrained Qwen2.5:7b generation on a frozen controlled protocol. Sixth, operational records and system invariants were examined to assess the validation pipeline and the separation of model risk, instructor triage, and support-case history.

Table 3.1 maps each final research question to its controlling evidence. E2 and the operational LLM history both inform RQ3, but they remain separate: E2 is a controlled held-out experiment, whereas the operational evidence is an aggregate record of a deployed analysis process. RQ4 is addressed through architecture, persistence invariants, and workflow verification rather than an educator-effectiveness experiment.

**Table 3.1. Research questions and evidence streams.**

| RQ | Method or evidence stream | Setting | Primary evaluation objective |
|---|---|---|---|
| RQ1 — Temporal Prediction | E1 empirical prediction | OULAD `AAA/2013J` | Measure checkpoint-specific held-out predictive discrimination |
| RQ2 — Temporal Integrity | E4 provenance audit and temporal implementation | Prepared OULAD states and source observations | Detect evidence whose source time exceeds its state cutoff and preserve traceability |
| RQ3 — LLM Grounding and Reliability | E2 controlled experiment | 48 frozen held-out cases | Compare plain and schema-constrained output for contract, evidence, and decision behavior |
| RQ3 — operational component | Operational LLM evidence | Saved Lobot workspace analysis history | Characterize validation, repair, abstention, latency, and rejection records |
| RQ4 — Human-in-the-loop Traceability | Framework and system verification | Persistence, API, and instructor workflow | Verify separation and auditability of analysis, triage, and support state |

The study did not combine these measurements into a single score. Each stream has its own population, denominator, intervention, and claim boundary. Empirical OULAD outcomes were used only for E1; controlled E2 cases were not student-performance records; operational Qwen histories did not supply predictive labels; and synthetic workspace records were used only to exercise system behavior.

> **[Figure 3.1 placeholder — Replace with the final methodology and evidence-stream diagram during visual integration.]** Educational records are converted into canonical observations and cutoff-safe learner states, which feed the E1 predictive evaluation and E4 temporal audit. A separate E2 path compares plain and schema-constrained generation on a frozen protocol. A third operational path passes workspace snapshots through Qwen, deterministic validation, bounded repair or abstention, and instructor review. Human triage and support actions remain separate from model outputs.

## 3.2 Data Sources and Evidence Classes

The project used six evidence sources, summarized in Table 3.2. Their roles were declared before interpretation so that replayed, controlled, operational, and synthetic records could not be mistaken for empirical learner-outcome evidence.

**Table 3.2. Data and evidence sources.**

| Source | Type | Role in the thesis | Empirical status | Claim boundary |
|---|---|---|---|---|
| OULAD `AAA/2013J` | Anonymized educational records with final outcomes | Temporal-state construction, E1 prediction, and E4 provenance audit | Empirical | One historical presentation; no cross-course or institutional generalization |
| Controlled Moodle-shaped replay | Replayed LMS export and adapter events | Synchronization, idempotency, quarantine, recovery, and interface validation | Operational replay | Not an observed predictive cohort and not used for E1 |
| Stanford MOOCPosts subset | Anonymized forum text with human ratings | Earlier auxiliary semantic feasibility comparison | Empirical text, but outside the final core experiments | Not linked to OULAD learners or academic-risk outcomes |
| Workspace v2 generated records | Deterministic synthetic course and learner trajectories | Product, policy, missingness, robustness, and workflow exercises | Synthetic | No predictive or cross-course educational claim |
| E2 held-out v2 cases | Controlled deterministic scenarios | LLM grounding and abstention experiment | Synthetic controlled experiment | Measures protocol behavior, not real-course prediction |
| Lobot analysis history | Saved operational workspace analyses and job outcomes | Operational validation, repair, abstention, failure, and latency evidence | Operational | Not AUROC/AP evidence and not a controlled outcome study |

OULAD was the sole source used for the final empirical prediction and cutoff-integrity claims. It provides linked, anonymized information about module presentations, registrations, assessments, learner submissions, VLE resources, daily interaction aggregates, and final results [19], [20]. Raw files were not altered during preparation. Missing source values remained missing with explicit reasons, and repeated learner-resource-day activity rows were aggregated rather than discarded.

The controlled Moodle replay served a different purpose. It exercised adapter and persistence behavior under known inputs, including repeated synchronization and restart behavior. Its records were labelled as replayed and were excluded from empirical prediction. Similarly, the earlier MOOCPosts work investigated forum-text agreement on an independent dataset. Because those posts have no linkage to OULAD learner trajectories or the non-success target, that work is auxiliary and does not enter E1, E2, or E4.

Workspace v2 synthetic records support richer operational scenarios, including course calendars, grade availability, deadline context, missing or stale feeds, and longitudinal support actions. They enable repeatable verification of contracts and user flows, but their learners and outcomes are fictional. E2 cases are also synthetic, yet have a narrower research purpose: each case encodes a controlled evidence condition and a hidden expected assessment or abstention behavior. Finally, the Lobot evidence consists of aggregate saved records from actual workspace analysis execution. Its value lies in observing the operational validation boundary, not in estimating predictive accuracy.

## 3.3 OULAD Dataset and Empirical Cohort

The empirical study selected module `AAA`, presentation `2013J`, from OULAD. Preparation filtered every used source table to that presentation and assigned pseudonymous project identifiers such as `oulad:<student-id>` and `oulad:AAA:2013J`. The selected source contained 383 enrolments. Eligibility rules produced at least one checkpoint state for 372 learners; the remaining source enrolments did not produce an eligible state. The artifacts do not assign a single speculative reason to all exclusions.

Seven OULAD files contributed to preparation. `courses.csv` supplied the presentation identifier and length. `studentInfo.csv` and `studentRegistration.csv` supplied the enrolment key, final result, registration timing, unregistration timing, previous attempts, and studied credits. Final result was written to a restricted outcome file and was not included in predictor features. Demographic attributes were also placed in a restricted fairness file and excluded from primary prediction. `vle.csv` supplied resource metadata and the mapping from source activity type to the project’s activity groups. `studentVle.csv` supplied learner-resource-day click aggregates. `assessments.csv` supplied assessment type, due day, and weight, while `studentAssessment.csv` supplied submission day, banked status, and score availability.

Only fields required by the implemented empirical feature set were brought into E1. Assessment score values were preserved during preparation but were not among the 20 E1 features in the frozen feature manifest. Exam definitions were excluded from checkpoint assessment features because their due-day availability did not support the same checkpoint treatment. Non-banked submission observations were used to establish whether due assessments had been submitted by a cutoff.

The cohort produced the state counts shown in Table 3.3. Counts decline at later checkpoints because eligibility is reassessed at each cutoff: a learner must have registered by the cutoff and must not already have unregistered on or before it.

**Table 3.3. Empirical checkpoints and state counts.**

| Checkpoint | Cutoff course day | Eligible learner states |
|---|---:|---:|
| Week 3 | 20 | 371 |
| Week 5 | 34 | 368 |
| Week 8 | 55 | 365 |
| Week 10 | 69 | 360 |
| **Total** | — | **1,464** |

OULAD records dates relative to the presentation rather than providing the exact event timestamps expected from a live LMS. The study therefore retained day-level precision. A separate fixed replay calendar exists for operational Moodle-shaped demonstrations, but that synthetic anchor was not treated as historical OULAD calendar evidence and did not enter the empirical evaluation.

## 3.4 Temporal Checkpoint Definition

A checkpoint denotes the course-relative decision time at which a learner state could have been available. The implemented builder calculated the cutoff as `checkpoint_week × 7 − 1`, producing course days 20, 34, 55, and 69 for weeks 3, 5, 8, and 10. These fixed checkpoints provide repeated early and mid-course views while preserving a consistent rule across learners.

For learner *i* at checkpoint *t*, the temporal state can be expressed as

$$s_{(i,t)} = \left(x_{(i,t)}, m_{(i,t)}, p_{(i,t)}\right),$$

where `x_(i,t)` contains derived feature values, `m_(i,t)` records the availability or missingness interpretation of each value, and `p_(i,t)` records provenance. Every included activity or submission observation must have a course-relative day less than or equal to the applicable cutoff. A week-*t* state is therefore neither the learner’s full-course state nor a retrospective summary.

Registration and unregistration were also evaluated relative to the cutoff. A learner whose registration day followed the cutoff did not receive a state at that checkpoint. A learner whose unregistration day was on or before the cutoff was not scored as an active enrolment. A withdrawal that occurred after the cutoff remained a future outcome and could contribute to the final risk label without entering the checkpoint features.

Checkpoint selection was fixed before model evaluation. The same checkpoint semantics governed state identity, feature windows, provenance, split-based evaluation, and the E4 audit. This binding prevents a state assembled under one cutoff from being evaluated or displayed as though it belonged to another.

## 3.5 Cutoff-Safe Learner-State Construction

Preparation first converted source rows into canonical observations. Each observation retained its presentation, pseudonymous learner, course-relative day, data origin, source identifier, and source-specific context. VLE rows at the same learner-resource-day grain were summed because repeated OULAD rows are valid daily aggregates rather than assumed duplicates. Activity types were mapped through a declared taxonomy into content, assessment, forum, collaboration, and other groups.

The state builder then grouped observations by learner and iterated through the four checkpoints. Activity-window selection filtered rows to `course_day <= cutoff` before applying 7-, 14-, or 28-day lower bounds. Cumulative activity used all accepted history through the cutoff, including explicitly labelled pre-start activity. Assessment features were calculated only from non-exam assessments whose known due day was on or before the cutoff. A submission counted only when its recorded submission day was also on or before the cutoff.

Each state identity binds the presentation, learner, checkpoint, and feature-set version. The empirical implementation used feature-set version `oulad-demo-features-v1`. A deterministic input hash was calculated from state identity, feature values, missingness, and provenance hashes. The state also retained its cutoff day, data origin, build time, freshness flag, and completeness ratio.

Availability was represented explicitly rather than using a single blanket imputation rule. An activity window with complete source coverage and no rows was represented as `structural_zero`. The recency feature used `no_activity_yet` and a null value when no prior activity existed. Assessment counts and submission rate used `not_yet_applicable` before any included assessment was due. Prepared source fields could use `source_missing` or `not_supported` where the source did not provide a value. These categories prevent a missing feed, an assessment that is not yet due, and a confirmed zero from acquiring the same numerical meaning.

Later observations were excluded through cutoff-first filtering in the state builder. Outcome labels and restricted demographic attributes were written to separate files during preparation. Outcomes were joined only in the research evaluation layer after temporal states and learner partitions had been established. This design reduces leakage risk for the audited implementation; it does not claim that every future feature builder or adapter is automatically safe.

## 3.6 Feature Engineering and Provenance

The frozen E1 manifest contains 20 features. They form four methodological groups:

1. **Recent activity:** clicks and active days over trailing 7-, 14-, and 28-day windows.
2. **Cumulative activity and recency:** total clicks, cumulative active days, days since last activity, and cumulative clicks within content, assessment, forum, collaboration, and other activity groups.
3. **Assessment participation:** assessments due, submitted, and missed, together with the submission rate for assessments due by the checkpoint.
4. **Enrolment context:** previous attempts and studied credits.

All activity aggregates were computed after applying the applicable cutoff. `days_since_last_activity` was the difference between the cutoff and the latest accepted activity day. Assessment counts were based on distinct due assessment identifiers and submissions observed by the cutoff. Unknown assessment scores were never converted into zeros; scores were not E1 predictor fields. Direct learner identifiers, final result, future unregistration, end-of-course totals, source scenario labels, and restricted demographic attributes were prohibited from the empirical feature vector.

The frozen E1 evaluation converted the 20 feature names into a stable ordered vector. The recorded feature manifest confirms that preprocessing and model fitting were train-only. The implementation represented unavailable numeric values as zero when assembling the model matrix; this must be read together with the empirical feature design, in which most E1 absences are structural or not-yet-applicable and the complete missingness semantics remain preserved in the state artifacts. The E1 model did not separately receive the missing-reason categories as predictor columns.

Every `WeeklyFeature` includes an evidence identifier, a provenance reference, the count of supporting source observations, a hash of the complete source-ID set, and up to eight inline source identifiers for inspection. This creates a trace from a derived value back to the observations that supported it without requiring every identifier to be embedded in the state object. Provenance was exported at learner-state/source-observation grain for E4. The audit therefore evaluates source evidence rather than relying only on the feature builder’s declared cutoff.

## 3.7 Outcome and Prediction Target Definition

The supervised target was binary non-success. `Fail` and `Withdrawn` were mapped to risk (`1`), while `Pass` and `Distinction` were mapped to not-risk (`0`). This definition was applied per learner enrolment in `AAA/2013J`. It groups failure and withdrawal for the primary experiment and therefore does not imply that both outcomes share the same pathway or cause.

Final result was marked as course-end-only information and restricted from the predictor. It was retained in `outcomes_restricted.csv`, then joined to the temporal states in the evaluation layer. Thus the label could be used to train and assess the supervised baseline without becoming an input feature at weeks 3, 5, 8, or 10. Future withdrawal dates were likewise unavailable to checkpoint features.

The target supports association-based prediction of later non-success. It does not represent motivation, understanding, or the causal effect of any learner behavior. A high model score consequently means that the observed feature pattern is associated with the target under the evaluated model and dataset; it does not explain why a learner may struggle or prove that a particular intervention will change the outcome.

## 3.8 Train, Validation, and Test Strategy

The 372 eligible learners were sorted, shuffled once with seed 42, and divided using 70%, 15%, and 15% cut points. This produced 260 training learners, 56 validation learners, and 56 test learners. The assignment was stored in a versioned split manifest. Because splitting occurred by learner identifier, all eligible checkpoint states for the same learner remained in one partition.

The number of state rows within each partition varies slightly by checkpoint because not every learner remains eligible at every cutoff. The frozen E1 report records 259/56/56 train/validation/test states at week 3 and progressively smaller counts at later checkpoints. Repeated states from the same learner within a partition are related longitudinal observations; they were not treated as independent records for split assignment.

A separate Logistic Regression pipeline was fitted for each checkpoint. Standardization and Logistic Regression fitting used only the checkpoint’s training rows. Validation rows were used to select a decision threshold by maximizing F1 over thresholds from 0.10 through 0.90 in increments of 0.01. The selected thresholds were 0.25, 0.41, 0.49, and 0.58 for weeks 3, 5, 8, and 10 respectively. These thresholds belong to the frozen evaluation protocol; they are not universal intervention policies or calibrated probabilities.

The test partition was not used for preprocessing, fitting, or threshold selection. It was evaluated after these decisions had been fixed. The implementation also generated percentile bootstrap intervals with 1,000 resamples and seed 42 for AUROC, Average Precision, and F1. Detailed test findings and interval interpretation are reserved for Chapter 5.

## 3.9 E1 Empirical Prediction Protocol

E1 evaluated Logistic Regression as a transparent empirical baseline over the cutoff-safe feature vectors. Logistic Regression was selected because it provides a conventional, reproducible comparison with a limited number of fitted parameters and supports direct checkpoint-specific measurement. The model used scikit-learn’s `LogisticRegression` with `class_weight="balanced"`, `max_iter=1000`, and `random_state=42`, preceded by `StandardScaler` in a training pipeline.

At each checkpoint, the state matrix was reconstructed in the feature order recorded by `e1_feature_manifest.json`. The model was fitted on training learners, produced raw class scores for validation learners, and used validation F1 to choose the threshold. The unchanged fitted pipeline then produced test scores. AUROC and Average Precision assessed ranking and precision-recall behavior independently of the chosen threshold. Precision, recall, F1, and the confusion matrix described behavior at the validation-selected threshold.

The output values from `predict_proba` were used as model scores within this baseline evaluation. No post-hoc calibration method was fitted or approved, so the project does not present them as calibrated probabilities. E1 did not use Qwen, LLM-generated claims, operational alerts, instructor actions, or synthetic workspace data. Its scope is the checkpoint-specific empirical signal available to Logistic Regression on one OULAD presentation.

## 3.10 E4 Temporal Integrity Audit

E4 independently tested whether the provenance exported for empirical states respected the declared checkpoint cutoff. The unit of audit was one link between a learner state and a source observation. Each exported row contained learner and presentation identifiers, checkpoint, source type, source identifier, source time, and checkpoint time.

For activity provenance, source time was the OULAD activity course day. For assessment-submission provenance, source time was the recorded submission course day. A row was a cutoff violation when `source_time > checkpoint_time`. Audit rows were grouped by checkpoint and source type, and the number of violations was reported alongside the number of provenance rows inspected. The final audit population contained 194,590 rows across activity and assessment-submission sources; the outcome of that comparison is reported in Chapter 5.

E4 provides a deterministic test of the artifacts used in the frozen evaluation. It does not test whether an unrecorded source event should have existed, whether the source data themselves are error-free, or whether future adapters will implement the same rules. Its claim is therefore bounded to the inspected provenance export, feature builder, and preparation version.

## 3.11 E2 Controlled LLM Grounding Protocol

E2 used the frozen `e2_grounding_heldout_v2` protocol. The LF-normalized canonical SHA-256 was `6E423F63884145AD00273CF26C65B155C1EC11E3E62A1080C94F74DC807CDD0D`. The protocol contained 48 cases across 12 scenario families, with four checkpoints represented in each family. Twenty-four cases expected assessment and 24 expected abstention.

The model saw only `checkpoint`, `course_policy`, and `evidence`. Case identifier, scenario family, expected behavior class, and expected evidence constraints remained evaluation-only fields. This separation prevented hidden targets from entering the prompt. Scenarios covered strong academic evidence with low activity, weak academic evidence with high activity, genuine inactivity, real zero grades, missing grades, not-yet-due work, awaiting marking, approved extensions, optional resources, missing feeds, conflicting evidence, and insufficient evidence.

Both primary treatments used local Ollama inference with `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, family `qwen2`, parameter size 7.6B, and Q4_K_M quantization. Generation used temperature 0, seed 42, `num_ctx=8192`, and `num_predict=1200`.

**Table 3.4. E2 protocol treatments.**

| Treatment | Valid run identity | Generation constraint | Cases | Purpose |
|---|---|---|---:|---|
| `plain_llm` v2 | `lobot-e2-v2-r2` | Prompted JSON generation without the full structural schema constraint | 48 | Establish plain-generation behavior under the frozen inputs |
| `schema_only` v2 | `lobot-e2-v2-schema-only-r2` | Ollama structured-output schema requiring the complete top-level and claim-item contract | 48 | Isolate the effect of structural output constraint while holding model, inputs, and settings fixed |

The primary comparison uses the preserved raw generations and deterministic offline rescoring. E2 v1 was excluded because early runs contained parsing, target-leakage, or insufficient reference-semantics defects. `schema_only` r1 was excluded because its transmitted schema omitted `claims.items` and therefore did not enforce the intended claim structure. The original `evidence_first_full` treatment had tooling and scoring defects, and `evidence_first_full_v2` was an incomplete post-hoc corrective treatment. None contributes to the primary E2 conclusion. These exclusions preserve treatment validity rather than selecting results on performance.

## 3.12 E2 Evaluation Dimensions

E2 scoring separated completion, structure, citations, semantics, constraints, and behavior. Completion required the model call to return and the response to be JSON-parseable. Top-level schema validity required a string `assessment`, a list of `claims`, and a Boolean `abstain`. Claim-schema validity required every claim to contain a string claim and a non-empty list of string `evidence_ids`; the unsupported singular `evidence_id` form was rejected. Full output-contract validity was the conjunction of top-level and claim-schema validity.

Citation validity was evaluated only when the output could be inspected. It required every claim to contain evidence references and every referenced identifier to exist in the supplied evidence. Semantic validation then checked future-observation use, prohibited causal or psychological phrasing, and scenario-specific contradictions such as treating missing grades as zeros, not-yet-due work as overdue, awaiting marking as failure, missing activity feeds as inactivity, approved extensions as lateness, or optional resources as mandatory. Semantic evidence validity was conjunctive: the output needed valid citations, no future evidence, no prohibited causal claim, and no detected semantic violation. A semantic failure therefore identifies failure of this combined contract; it is not automatically evidence of hallucination.

Behavioral correctness compared the emitted `abstain` Boolean with the hidden expected behavior class. Evidence-constraint correctness evaluated only the constraints declared for that case. The supported constraint vocabulary included citation discipline, temporal and causal restrictions, missingness distinctions, required abstention under missing/conflicting/insufficient evidence, and respect for extension and optional-resource policy. Unknown constraint names caused scorer failure rather than being ignored.

Unsupported-claim and contradiction counts were derived from deterministic rule violations and reported separately from citation validity. Metrics were calculated with their own evaluable denominators. This matters because a structurally invalid output may make later semantic fields unevaluable, and a conjunctive zero cannot be interpreted as a universal real-world error rate.

## 3.13 Operational LLM Evidence Methodology

Operational LLM evidence was derived from read-only aggregate queries of the Lobot operational workspace database on 12 October 2026 and manually archived in the evaluation repository as a structured JSON evidence snapshot and accompanying report. The repository does not contain a production database dump from which those aggregates can be independently reconstructed. This evidence was not generated from the E2 protocol and did not use OULAD outcome labels. The mature v3.2 and v3.3 records used `qwen2.5:7b`, digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, and wire contract `risk-decision-v3`.

The operational pathway begins with an immutable workspace snapshot and the applicable course-policy version. An analysis job records the state and policy identity before a worker invokes the configured local model. The response is parsed into the wire contract, checked structurally, and validated against evidence, semantic, and policy rules. Where the configured failure category permits correction, one bounded repair generation is attempted. A valid corrected response is marked as repaired; insufficient or unsafe evidence may produce an explicit quality abstention; malformed, unsupported, or policy-conflicting outputs may be rejected without publication. Accepted analyses retain state, feature, policy, model, prompt, input-schema, and wire-contract provenance.

The archived version sequence includes v2.1, v2.2, v2.3, v3.2, and v3.3. Versions v2.1 and v2.2 predate modern `validation_outcome` semantics and cannot be retrospectively divided into first-pass, repaired, abstained, and rejected categories. V2.3 contains modern records but is a small earlier bridge version. The mature comparison is limited to saved v3.2 and v3.3 outputs with comparable model identity and contract.

Aggregate fields included first-pass validation, repaired validation, quality abstention, average latency, and retained error categories. No global success rate was computed. In particular, `workspace_analysis_job` and `workspace_analysis_attempt` in the inspected operational database did not retain `prompt_version`, and no usable inference-trace table was present there. Failed jobs therefore cannot be attributed reliably to v3.2 or v3.3, and prompt version was not inferred from timestamps. Operational records measure contract behavior among their stated denominators, not predictive accuracy, calibration, or educational effect.

## 3.14 Human-in-the-Loop Methodology

The human-in-the-loop framework treats three states as independent: **Risk State**, **Instructor Triage Status**, and **Support Case Status**. Risk state is a historical model analysis tied to a particular learner snapshot, policy version, and model provenance. Triage is an instructor-maintained judgement containing flags, watchlist status, priority, and a note. A support case is a longitudinal record with its own lifecycle: new, reviewed, ongoing, resolved, or dismissed.

The workflow begins when a model result becomes available for a specific state. The instructor can inspect its evidence and history, then update triage without changing the stored model payload. If continued action is required, the instructor can create or update a support case, record an action or note, set a follow-up day, or close the case. Later checkpoint states and analyses are appended as new evidence; they do not overwrite the earlier result that informed a prior decision.

Exact state binding is enforced through state identifiers and snapshot heads. The current view does not silently substitute an older prediction when the current state lacks a compatible analysis. Temporal comparisons require adjacent eligible checkpoints and compatible policy/model semantics. Support actions may carry the expected state identifier and checkpoint, keeping the human event anchored to the evidence visible when it was recorded.

Triage and support updates use expected versions for optimistic locking. If another change has advanced the record, the stale update receives a conflict rather than overwriting newer work. Idempotency keys and request hashes make a repeated identical request safe while rejecting reuse of the same key for different content. Triage events and case events retain actor, version or request identity, payload, and creation time, providing an auditable history even when a flag is later removed or a case is closed.

This methodology verifies traceability and state separation for RQ4. It does not test whether instructors find the system usable, whether their decisions improve, or whether support actions cause better learner outcomes.

## 3.15 Evaluation Metrics

E1 used AUROC and Average Precision as its primary discrimination metrics. AUROC measures the probability that a randomly selected positive case receives a higher score than a randomly selected negative case across possible thresholds. Average Precision summarizes precision-recall behavior and is useful when the positive class is less frequent than the negative class. The frozen test artifacts also report precision, recall, F1, and confusion-matrix counts at the validation-selected threshold, plus bootstrap intervals for AUROC, Average Precision, and F1.

E4 reported the number of provenance links audited and the number satisfying the violation condition `source_time > checkpoint_time`, stratified by checkpoint and source type. This is an integrity measurement, not a prediction metric.

E2 reported model-call completion, JSON parsing, top-level schema validity, claim-schema validity, full-contract validity, citation validity, semantic evidence validity, unsupported and contradictory claim counts, expected-constraint validity, abstention, and behavioral correctness. Each rate used its appropriate evaluable denominator. The study did not combine these dimensions into a single quality score.

Operational LLM analysis used first-pass validated count/share among saved validated outputs, repaired validated count/share, quality-abstention count, initial and repaired latency, and retained validation or rejection categories. Lifecycle state `ANALYSIS_SUPERSEDED` was not counted as a model-quality failure. Because failure records lack prompt-version metadata, they were not added to version-specific denominators.

Framework verification used categorical invariants rather than predictive metrics: exact state binding, immutable historical analyses, independent triage and case mutation paths, adjacent-checkpoint comparison rules, optimistic-lock conflicts, idempotent retries, and append-only event histories. These software checks establish implementation behavior but are not combined with E1, E2, or E4 outcomes.

## 3.16 Reproducibility and Artifact Governance

Reproducibility controls were applied at dataset, split, protocol, model, and result levels. OULAD preparation produced a manifest containing source identity, presentation, row counts, policies, and SHA-256 hashes of prepared files. The empirical evaluation recorded dataset version `oulad_AAA_2013J_v1`, a learner split manifest, seed 42, the ordered 20-feature manifest, the restricted label source, train-only fitting, and validation-F1 threshold selection.

E1 and E4 results were written to versioned CSV artifacts. E1 rows retain checkpoint sample sizes, thresholds, discrimination and threshold-dependent metrics, confusion matrices, and bootstrap intervals. E4 rows retain checkpoint, source type, audit population, and violation count. Repository-relative artifact names connect those results to the final evidence matrix.

E2 governance used a frozen protocol, a separate manifest, and cryptographic hashing. The canonical v2 protocol SHA-256 was computed after normalizing CRLF and CR line endings to LF, making integrity verification cross-platform. A legacy Windows byte hash is retained as metadata rather than accepted as an alternative semantic protocol. Raw treatment CSVs, deterministic rescored CSVs, summaries, source run identifiers, rescoring Git commits, model identity, generation settings, and a primary-artifact SHA manifest were archived. The primary treatments were frozen explicitly, and invalid or incomplete runs remained documented rather than deleted or incorporated.

Operational evidence was archived as a JSON snapshot and a narrative evidence report. The snapshot records its extraction boundary, model digest, wire contract, version aggregates, failure categories, and denominator limitations without exposing credentials. Product and evaluation Git commits provide code lineage, while stable learner, state, job, analysis, case, and event identifiers support traceability through the implemented system.

These controls improve repeatability but do not remove environmental dependencies. E2 inference depended on a particular local Ollama model build and hardware environment, and the operational snapshot does not include a restorable production database dump. Reproduction must therefore distinguish bitwise artifact verification, deterministic offline rescoring, and new inference execution.

> **Final-integration citation note:** Reconcile citations for scikit-learn (`LogisticRegression` and `StandardScaler`) and percentile bootstrap confidence intervals after the consolidated bibliography is finalized; do not assign citation numbers in this chapter yet.

## 3.17 Ethical, Privacy, and Validity Considerations

OULAD is anonymized and was handled using project pseudonyms rather than direct learner identifiers [19], [20]. Demographic attributes were separated from primary prediction and retained in restricted artifacts; no completed fairness or demographic analysis is claimed. The feature set describes observable activity, submission, and enrolment context; it does not infer motivation, intention, emotion, or a psychological profile. This boundary is consistent with learning-analytics concerns about transparency, privacy, and responsibility [18].

Temporal validity was addressed through cutoff-first construction, restricted outcome storage, learner-grouped splitting, train-only preprocessing, an untouched test partition, and the independent provenance audit. These controls reduce specific forms of leakage but do not establish that OULAD is free of measurement error or that future datasets will satisfy the same assumptions.

Generated LLM output was treated as untrusted. Structured parsing, schema checks, evidence-reference validation, semantic and policy rules, bounded repair, abstention, rejection, and retained provenance provide a layered control boundary aligned with general generative-AI risk-management principles [9]. Passing those controls means that an output met the implemented rules; it does not prove that the score is predictively correct or that all unsupported reasoning has been eliminated.

Validity claims remain separated by evidence class. The empirical findings concern one historical OULAD presentation. Controlled E2 cases do not estimate a real-world hallucination rate. Synthetic workspace records do not validate learner-risk prediction. Operational Qwen records do not establish AUROC, Average Precision, or calibrated probabilities. The project does not claim cross-institution generalization, educator effectiveness, causal intervention benefit, or real-time digital-twin behavior.

Human oversight is preserved by showing evidence and maintaining instructor decisions independently from model history. This supports review and accountability without representing the instructor as a passive approval step. Nevertheless, no formal educator study was conducted, so claims about workload, usability, decision quality, or improved learner outcomes remain future research questions rather than conclusions of the present methodology.
