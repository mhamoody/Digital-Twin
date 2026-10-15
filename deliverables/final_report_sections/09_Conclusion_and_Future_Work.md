# 7. Conclusion and Future Work

## 7.1 Conclusion Overview

This thesis addressed the problem of transforming heterogeneous learning-management-system records into a temporally valid and auditable representation that can support predictive analysis and instructor review. The work developed and evaluated a provenance-aware, checkpointed course digital twin that reconstructs cutoff-safe learner states, measures checkpoint-specific predictive behavior, and separates validated model evidence from auditable instructor triage and longitudinal support decisions.

The research combined five distinct evidence streams across the four research questions. An empirical OULAD experiment evaluated a transparent Logistic Regression model at weeks 3, 5, 8, and 10. A deterministic provenance audit tested whether the observations linked to those states respected their declared cutoffs. A controlled 48-case experiment examined how output constraints affected the grounding and behavior of `qwen2.5:7b`. Separate operational records described validation, repair, abstention, and rejection in the implemented LLM analysis pipeline. Finally, system and persistence verification examined whether model outputs, instructor triage, and support cases remained separately versioned and auditable.

Taken together, the findings support a central conclusion: predictive learning analytics becomes more defensible when prediction is treated as one part of a wider temporal and decision-making system. Predictive discrimination must be associated with a declared checkpoint and eligible population. Every generated claim must remain linked to available evidence and subjected to deterministic checks. Human decisions must remain distinguishable from model output. The implemented digital twin brings these requirements together without treating the model, interface, or instructor as interchangeable sources of authority.

The thesis does not establish universally accurate prediction, autonomous educational decision making, or improved learner outcomes. Its contribution is a demonstrable framework for temporally bounded prediction, traceable generated analysis, and historically accountable human support within the evaluated setting.

## 7.2 Summary of Research Findings

RQ1 asked how predictive performance evolves across cutoff-safe learner states at early course checkpoints. Within OULAD `AAA/2013J`, the Logistic Regression model showed modest discrimination at weeks 3 and 5 and substantially stronger discrimination at weeks 8 and 10. AUROC and Average Precision were 0.621 and 0.379 at week 3, 0.657 and 0.531 at week 5, 0.896 and 0.819 at week 8, and 0.834 and 0.802 at week 10. Week 8 was numerically strongest under the frozen protocol. These values describe checkpoint-specific behavior in one presentation; they do not establish universal checkpoint optimality, statistical superiority between weeks, or calibrated probabilities.

RQ2 asked whether a provenance-aware temporal pipeline could prevent post-cutoff information leakage while preserving traceability. The E4 audit inspected 194,590 provenance rows and detected no case in which recorded source time exceeded the associated checkpoint cutoff. This result supports the cutoff integrity of the frozen preparation and state-building path and demonstrates that derived states can remain traceable to their source evidence. It does not prove that source records were complete or error-free, or that future adapters will automatically retain the same property.

RQ3 asked how structural constraints and deterministic validation affect evidence compliance, abstention behavior, and operational reliability of LLM-generated instructor-facing analyses. In the controlled E2 comparison, the plain treatment produced valid citations, conjunctive semantic validity, and evidence-constraint correctness in 0 of 48 cases, while the schema-only treatment produced valid citations in 48 of 48 cases, semantic validity in 42 of 48, and constraint correctness in 36 of 48. Both treatments nevertheless produced 0 of 48 abstentions and 24 of 48 behaviorally correct decisions. Structural constraints therefore substantially improved representation and evidence compliance but did not, by themselves, improve selective abstention or overall behavioral correctness.

The operational evidence provides a separate answer to the implementation component of RQ3. The versioned Qwen pipeline recorded structured validation, bounded repair, quality abstention, rejection categories, and provenance. Among saved validated outputs, v3.2 recorded a 95.775% first-pass share and a 4.225% repair share, while v3.3 recorded 97.215% and 2.785%, respectively; 12 v3.3 quality abstentions were separate. These are operational compliance observations rather than prediction-accuracy results. Failed jobs lack reliable prompt-version attribution, so no version-specific total failure rate or global operational success rate can be inferred.

RQ4 asked how model risk, instructor triage, and longitudinal support decisions could be represented separately while preserving historical model evidence. The implemented framework binds a prediction or validated analysis to the exact learner state on which it was produced, retains its model and evidence provenance, and stores instructor triage and support-case actions as independent histories. A later review or case resolution does not rewrite the earlier model record. This answers RQ4 as a framework and system-design question; it does not establish that educators make better decisions or that support actions improve learner outcomes.

**Table 7.1. Research questions, final answers, and claim boundaries**

| RQ | Final answer | Evidence basis | Boundary |
|---|---|---|---|
| RQ1 — Temporal Prediction | Predictive discrimination was modest at weeks 3 and 5 and stronger at weeks 8 and 10; week 8 was numerically strongest | E1 held-out Logistic Regression evaluation on `AAA/2013J` | One presentation, changing checkpoint populations, small test groups, and uncalibrated scores |
| RQ2 — Temporal Integrity | The frozen state-building path preserved the declared cutoff across all audited links | E4 audit: 194,590 provenance rows and 0 detected post-cutoff violations | Recorded frozen provenance only; no universal leakage-freedom claim |
| RQ3 — LLM Grounding and Reliability | Schema constraints improved structural and evidence compliance but did not improve abstention or behavioral correctness by themselves; operational safeguards separately handled validation outcomes | E2 controlled comparison plus separate operational LLM records | Synthetic cases and one model identity; operational evidence has no predictive ground truth |
| RQ4 — Human-in-the-loop Traceability | Model risk, instructor triage, and support-case state can remain distinct, versioned, and tied to exact learner states | Persistence, API, workflow, and safeguard verification | Framework evidence only; no educator-effectiveness or intervention-effect result |

## 7.3 Contributions of the Thesis

The first primary contribution is provenance-aware cutoff-safe temporal learner-state construction. Rather than treating a learner as one final course record, the framework reconstructs what was recorded as knowable at each checkpoint. Features retain availability and missingness meaning, and provenance links connect derived values to source observations. This temporal representation provides a reproducible basis for prediction and retrospective audit.

The second primary contribution is checkpoint-specific empirical predictive analysis. The thesis evaluates a transparent Logistic Regression baseline separately at weeks 3, 5, 8, and 10 using learner-grouped partitions and validation-selected thresholds. This design makes the trade-off between early lead time and later predictive discrimination visible, while avoiding a single course-wide result that obscures when evidence was available.

The third primary contribution is controlled evidence that structural and citation compliance do not guarantee selective abstention or behavioral correctness. E2 separates parseable structure, valid citation, semantic evidence support, policy constraints, abstention, and final behavior. The results show that a model can satisfy an output contract and cite existing evidence while still making an unsupported or contradictory decision. This establishes a clear boundary around what schema-constrained generation can achieve.

The versioned evidence-grounded operational LLM pipeline is a secondary contribution. It combines restricted inputs, structured generation, deterministic schema, evidence, semantic, and policy checks, bounded repair, quality abstention, explicit rejection, and retained provenance. The contribution concerns operational reliability and inspectability. It is not evidence that Qwen predicts academic outcomes accurately or produces calibrated risk probabilities.

The separation of model risk, instructor triage, and support-case state is a framework contribution. It permits an instructor to interpret, override, or act on model evidence without altering the historical prediction or analysis. This separation supports accountability and longitudinal reconstruction and establishes a basis for later human-factors evaluation.

The React workspace, FastAPI services, PostgreSQL persistence, authentication and course authorisation, worker/runtime infrastructure, deployment tooling, and Streamlit fallback enable the research contracts to operate as a coherent product. They demonstrate feasibility and make the evidence inspectable, but they are not presented as scientific novelty.

## 7.4 Practical and Scientific Implications

For predictive learning analytics, the study shows why evaluation should remain explicitly temporal. A model assessed at an early checkpoint answers a different operational question from one assessed later, because the available evidence and eligible population have changed. Reporting checkpoint-specific discrimination, threshold behavior, and uncertainty gives a more faithful account of early-warning capability than one aggregate result.

For temporal validity, the findings establish provenance as part of the scientific evidence rather than merely database metadata. Predictive metrics are credible only if their inputs respect the claimed time boundary. A retained link from each state feature to eligible source observations supports leakage testing, debugging, and later review. The zero detected violations in the frozen audit make the evaluated results more defensible while remaining bounded to the inspected artifacts.

For LLM reliability, the thesis demonstrates that output structure is necessary but insufficient. Schemas make responses machine-readable and allow evidence references to be checked, but neither valid structure nor citation presence guarantees faithful reasoning or appropriate abstention. Instructor-facing generation therefore benefits from a layered boundary: restricted evidence, structured output, deterministic validation, bounded repair, explicit abstention or rejection, and retained history.

For human decision support, the separation of model and instructor state prevents automation from silently becoming a support decision. Exact state binding tells the reviewer which evidence governed an analysis, while independent triage and support histories preserve later human judgment. This structure supports accountability but does not remove the need for institutional policy, educator training, or empirical evaluation of how the interface affects decisions.

For course digital twin design, the work supports a conservative definition. The implemented system is a provenance-aware, checkpointed course digital twin connecting temporal learner-state reconstruction, predictive analysis, validated instructor-facing evidence, and auditable support decisions. It is not a real-time replica, causal simulator, or psychological learner model. Its value lies in maintaining a versioned historical relationship among evidence, analysis, and action.

## 7.5 Limitations

The empirical prediction study uses one OULAD presentation, a modest cohort, and one baseline model. Checkpoint populations change as eligibility is recalculated, and the target combines Fail and Withdrawn despite their potentially different pathways. The model scores were not calibrated, no external dataset was evaluated, and the findings do not establish cross-course or cross-institutional generalisation.

The E4 conclusion is limited to the recorded provenance, declared timestamps, and frozen implementation. It cannot establish source completeness, timestamp correctness, or the behavior of a future adapter. E2 uses 48 synthetic controlled cases and one LLM identity. Its results diagnose defined grounding and abstention behaviors but do not estimate their real-course prevalence. The plain semantic score is conjunctive and must not be interpreted as a universal hallucination rate.

The operational LLM evidence is observational and lacks predictive ground truth. Failed jobs cannot be attributed reliably to prompt versions, preventing valid version-specific total failure rates. The operational evidence also cannot be combined with E2 or E1 to infer predictive accuracy. No global operational success rate is supported.

Finally, the study did not include a formal educator usability, trust, workload, decision-quality, or automation-bias evaluation. It did not test whether support actions caused improved learner outcomes. Production onQ or LTI integration was not validated, and no fairness or subgroup-performance study was completed. These omissions bound the present thesis to technical, empirical-prediction, controlled-grounding, and framework conclusions.

## 7.6 Future Work

### 7.6.1 Broader Empirical Validation

Future evaluation should repeat the cutoff-safe protocol across additional OULAD presentations and, where compatible data are available, other LMS datasets. Whole-presentation or course-held-out designs would test whether the observed temporal pattern transfers beyond `AAA/2013J`. External institutional data should be used only under appropriate consent, governance, privacy, and access controls. Each new source should undergo schema-conformance, missingness, and provenance audits before its results are compared.

The temporal twin could also be extended to more checkpoints and richer course events. Such extensions should preserve versioned state definitions, cutoff rules, and source-level provenance. More frequent checkpoints would not make the system real-time unless continuous synchronisation and its operational guarantees were actually implemented and evaluated.

### 7.6.2 Predictive Modelling and Calibration

Stronger transparent baselines should include carefully tuned tree-based methods, gradient boosting, temporal models, and lightweight neural approaches. Comparisons should retain learner-grouped and checkpoint-safe evaluation, fit all transformations on training data, select policies using validation data, and leave test partitions untouched. Model complexity should be justified by reproducible improvement rather than assumed superiority.

Calibration is a separate priority. With sufficient validation data, future work should evaluate post-hoc calibration, reliability diagrams, Brier score, and expected calibration error. Calibration must be fitted without test-label leakage and reported separately for each relevant checkpoint or population. Until such evidence exists, model scores should continue to be described as scores rather than probabilities.

Uncertainty-aware prediction and review-capacity policies should also be evaluated. Selective prediction, confidence-aware queues, and thresholds tied to review capacity could help balance missed cases and false alerts. These policies require prospective validation and should not be inferred from discrimination metrics alone.

### 7.6.3 Missingness, LLM Grounding, and Selective Abstention

Future missingness studies should introduce controlled missing-feed conditions, compare typed missingness representations, and measure robustness to incomplete ingestion. Such experiments could determine when models confuse unavailable evidence with genuine inactivity and whether explicit availability indicators improve prediction or explanation quality.

The LLM evaluation should expand beyond 48 cases and one model identity. Larger frozen scenario sets could cover additional missingness, contradiction, stale-data, policy, and adversarial conditions. Additional local instruction-tuned models could be compared under identical inputs, schemas, validators, and decoding settings. Ground-truthed instructor-facing samples would help connect controlled grounding results with realistic course evidence.

Selective abstention requires direct treatment. Future experiments should compare explicit abstention prompts, deterministic minimum-evidence gates, and model-plus-validator policies while preserving the distinction between structure and behavior. Stronger semantic evaluators may improve diagnosis, but their own validity and reproducibility must be established. Excluded or post-hoc E2 treatments should remain separate from pre-specified primary comparisons.

### 7.6.4 Educator and Intervention Evaluation

A formal educator study should evaluate task completion, comprehension of evidence and uncertainty, trust calibration, automation bias, workload, and decision quality. The study should compare interface and explanation conditions rather than assuming that evidence display automatically produces appropriate reliance. It should also examine whether instructors understand the separation between model risk, triage, and support-case status.

Intervention effectiveness requires a prospective, ethically governed design. Future work could evaluate whether particular support actions affect engagement or academic outcomes, with appropriate consent, institutional oversight, and controls for confounding. The current predictions and support records should not be treated as causal recommendations before such evidence is available.

### 7.6.5 Operational and LMS Integration

Operational metadata should be strengthened by persisting prompt version and sufficient trace information for every attempt, including failed jobs. This would permit valid version-specific failure analysis and clearer reconstruction of repair and rejection paths without exposing sensitive learner data.

Production-grade LMS integration should evaluate onQ or another approved platform through appropriate LTI and data-access mechanisms. Future work must address identity federation, course authorisation, consent, retention, security review, adapter reliability, and institutional permissions. Pilot deployment should proceed separately from research claims and should preserve the same cutoff, provenance, and audit requirements.

### 7.6.6 Fairness and Governance

Fairness and subgroup analysis should be conducted only where protected attributes can be handled ethically and lawfully. Future evaluation should assess error rates, calibration, coverage, and intervention allocation across sufficiently represented groups while suppressing unsafe small-cell reporting. Demographic attributes should not become unsupported causal explanations or direct recommendation triggers.

Governance should define who may view evidence, change policies, review cases, and audit model behavior. It should also specify retention, appeal, incident response, model-update approval, and procedures for suspending predictions when data quality or distribution changes. These institutional controls are necessary complements to the technical safeguards developed in this thesis.

## 7.7 Final Conclusion

This thesis demonstrates, within its evaluated setting, that a provenance-aware, checkpointed course digital twin can be designed around temporal validity, predictive analysis, grounded generated analysis, and independent human decision history. The contribution is not a claim of universally accurate prediction or autonomous educational decision making. It is a demonstrable framework for building a provenance-aware, checkpointed course digital twin in which predictive models, validated generated analyses, instructor triage, and longitudinal support decisions remain distinct but connected. The completed evaluations identify both the value and the limits of each layer, providing a reproducible foundation for broader empirical validation, stronger uncertainty handling, educator studies, and governed institutional integration.
