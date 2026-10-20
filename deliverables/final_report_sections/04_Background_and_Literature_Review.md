# 2. Background and Literature Review

## 2.1 Chapter Overview

Learning-management systems record a growing history of learner interactions, assessment participation, enrolment changes, and access to course resources. Learning analytics seeks to transform such records into information that can support teaching, learning, and institutional decision making. Within that broad field, predictive learning analytics and early-warning systems attempt to identify learners who may require attention before a final outcome is known. This objective is attractive because timely support may be more useful than retrospective classification, but it also creates demanding methodological and ethical requirements.

An early prediction is meaningful only in relation to a specific time. Its inputs must reflect information that was available at that time, its missing values must retain their correct meaning, and its output must not be treated as a direct account of a learner's motivation or understanding. If generated language is added to the workflow, further questions arise about whether a response follows its schema, cites the supplied evidence, interprets that evidence correctly, complies with policy, and declines to answer when the evidence is insufficient. When an instructor acts on a result, model evidence, human interpretation, and subsequent support history must remain distinguishable.

This chapter reviews the literature that motivates those requirements. It begins with learning analytics and predictive early warning, then examines prediction timing, temporal validity, provenance, missingness, and educational digital twins. It next considers explainability, ethics, LLM-generated analysis, structured output, deterministic validation, abstention, and human-in-the-loop support. The review culminates in an integrated research gap rather than a claim that any individual component is unprecedented. The gap concerns how temporal prediction, inspectable evidence, validated generated analysis, and auditable human workflow can be evaluated together without collapsing their different meanings.

The literature therefore motivates the thesis's four research questions. RQ1 concerns the evolution of predictive performance across declared checkpoints. RQ2 concerns cutoff-safe state construction and traceable temporal evidence. RQ3 concerns the relationship among structured generation, evidence compliance, abstention, and operational safeguards. RQ4 concerns the separation of model risk, instructor triage, and longitudinal support decisions. These questions are investigated through different evidence streams in later chapters; this review establishes their conceptual basis without reporting the project results.

## 2.2 Learning Analytics and Predictive Early Warning

Learning analytics draws on data generated through educational activity to understand and support learning processes. In an LMS, those data may include resource access, virtual-learning-environment interactions, assessment submissions, grades, enrolment status, and discussion activity. The records are longitudinal and often heterogeneous: some represent an explicit academic event, such as a submission, while others are indirect traces of platform use. Their availability has enabled a substantial body of work on student-performance prediction and early identification of academic risk.

A systematic review by Namoun and Alshanqiti surveys data-mining and learning-analytics approaches to predicting student performance and identifies wide variation in datasets, features, algorithms, and evaluation practices [1]. The review illustrates both the maturity of predictive work and the difficulty of comparing reported results when problem definitions and baselines differ. Akçapınar et al. demonstrate an early-warning approach based on learning-analytics evidence [2], while Bañeres et al. present an early-warning system for detecting at-risk learners in online higher education [3]. Together, these studies support the premise that learner activity and assessment traces can inform risk-oriented decision support.

The value of an early-warning system is not exhausted by classification performance. A result must arrive at a time when review or support remains possible, and it must be presented in a form that an instructor can examine. This connects predictive modelling with workflow design: the output may prioritise attention, but an instructor needs to understand the evidence basis, judge whether the record is complete, and decide what response is appropriate. Prediction is therefore better understood as decision support than as a replacement for professional judgment.

The relationship between digital traces and academic outcomes is also contextual. Gašević et al. argue against a one-size-fits-all interpretation of learning analytics and show that instructional conditions affect the prediction of academic success [4]. A click has meaning within a course design: some modules require frequent online interaction, whereas others depend more heavily on reading, offline activity, or a small number of assessments. Assessment structure, resource sequencing, communication practices, and the role of the LMS can all affect which traces are informative.

This contextual dependence limits psychological interpretations of platform data. Recorded inactivity does not directly establish low motivation; frequent clicks do not directly establish understanding; and a missed submission does not establish why it was missed. These are observable behavioral or administrative traces, not measurements of intention or mental state. Instructor-facing analytics should therefore describe the observed evidence and its relation to the predictive model without converting association into diagnosis.

The literature consequently establishes a strong basis for predictive early warning while leaving several design questions open. How early should a model be evaluated? How is the evidence available at that moment reconstructed? How should absent or incomplete data be represented? How can generated explanations remain faithful to the evidence? How should a human response be recorded independently from the prediction? These questions motivate a broader system boundary than a model trained on a static final table.

**Table 2.1. Learning-analytics literature themes and limitations**

| Theme | Representative literature | Typical contribution | Relevant limitation for this thesis |
|---|---|---|---|
| Student-performance prediction | Systematic review of predictive and data-mining approaches [1] | Establishes common data sources, models, and evaluation practices | Heterogeneous targets, datasets, baselines, and observation periods limit direct comparison |
| Early-warning systems | Learning-analytics early warning and online at-risk detection [2], [3] | Shows that activity and assessment traces can support timely risk identification | Predictive output still requires contextual interpretation and an operational review process |
| Instructional context | Context-dependent prediction of academic success [4] | Demonstrates that instructional conditions influence predictive relationships | Portability cannot be assumed from one course or presentation |
| Digital-twin foundations | General digital-twin concepts and enabling technologies [5] | Frames an evolving digital representation linked to observations and state | Physical-system definitions do not transfer automatically to education |
| Educational digital twins | Reviews of digital twins in e-learning and education [6], [7] | Describes monitoring, simulation, personalisation, and institutional applications | Definitions and levels of implementation remain heterogeneous |
| Structured tabular use of LLMs | TabLLM [8] | Shows that tabular records can be serialized for language-model classification | Serialization does not establish educational validity, grounding, or safe abstention |
| Responsible generated AI | NIST Generative AI Profile [9] | Emphasises measurement, documentation, oversight, and controls for confabulation and misuse | General guidance must be translated into task-specific contracts and tests |
| Ethical learning analytics | Slade and Prinsloo [18] | Identifies privacy, transparency, responsibility, and power concerns | Technical accuracy alone does not settle whether use is appropriate |

## 2.3 Temporal Prediction in Online Learning

The timing of a prediction changes both its purpose and its evidence base. A prediction near the beginning of a course offers greater lead time, but the learner history may be short and important assessments may not yet be due. A later prediction can use a richer accumulated record, but it leaves less time for review and support. This produces a fundamental tension between timeliness and predictive signal.

Early-warning studies demonstrate that useful patterns can emerge from LMS activity before a final outcome is known [2], [3]. However, reported performance is meaningful only when the observation window and prediction point are explicit. A model evaluated on course-end aggregates cannot automatically be interpreted as an early-warning model. Likewise, a result reported for one early window does not reveal whether predictive behavior strengthens, weakens, or changes at later points.

Checkpointed evaluation provides one way to make timing explicit. A checkpoint defines the cutoff at which evidence is assembled and the population eligible for scoring. The same learner may appear at several checkpoints, but the corresponding states are not interchangeable: more events may have occurred, additional assessments may have become applicable, and enrolment status may have changed. Evaluation by checkpoint therefore asks a sequence of related questions rather than treating the course as one static prediction task.

This temporal framing also clarifies the interpretation of metrics. Ranking measures describe discrimination within the eligible population at a checkpoint, whereas a threshold-dependent measure reflects one operating decision selected under a particular policy. Earlier checkpoints may justify a more sensitive review policy, but additional false positives could increase the number of records requiring attention. Later checkpoints may produce a more selective queue but reduce the available response time. These are design trade-offs; predictive metrics alone do not determine the preferred intervention point.

Instructional context further complicates temporal comparison. A week number has meaning only in relation to the course schedule. A checkpoint before a major assessment differs from one after several graded tasks, even if both are labelled with the same calendar week in different courses. Gašević et al.'s emphasis on instructional conditions therefore applies not only across courses but also across time within a course [4]. The evidence available at a checkpoint should be interpreted against what learners were expected to do by that stage.

This motivates RQ1: predictive behavior should be measured across several cutoff-safe learner states rather than inferred from one final model score. The purpose is not to assume that later is always better or to find a universally optimal week. It is to determine how the evaluated signal changes under a declared temporal protocol and to keep the lead-time trade-off visible.

## 2.4 Temporal Leakage and Cutoff-Safe Learner States

Predictive evaluation can be undermined when information from the future enters a feature intended to represent an earlier time. In longitudinal educational data, this can occur through end-of-course totals, final grades, later submissions, future withdrawal information, or preprocessing performed before temporal filtering. A model may then appear to predict an outcome while partly observing information that was unavailable at the claimed prediction point.

Future-information leakage is distinct from ordinary overlap between training and test examples. Train/test leakage concerns information crossing the evaluation partition, while target leakage concerns inputs that encode the outcome directly or indirectly. Temporal leakage concerns availability: even a legitimate event becomes invalid for an early state if it occurred after that state's cutoff. These risks can coexist and require separate controls. A learner-grouped split does not by itself prevent post-cutoff activity from entering a feature, and a temporal cutoff does not by itself prevent the same learner from appearing in incompatible partitions.

The methodological rule adopted by this thesis is straightforward: for a prediction at time `t`, every contributing observation must have been available by `t`. Implementing that rule is less straightforward when data arrive through several tables, use different time representations, or contain aggregate fields whose temporal extent is unclear. Filtering only the final feature table may be insufficient because future information can already have been incorporated during aggregation. For the purposes of this thesis, the cutoff therefore governs state construction from the source observations onward. This is a thesis-specific control for preserving the meaning of an early prediction rather than a claim that the reviewed educational literature prescribes one universal audit procedure.

A cutoff-safe learner state makes temporal availability part of the data contract. It associates the state with a presentation, learner, checkpoint, and cutoff, then includes only eligible observations. Labels such as final outcome remain outside the predictor input and are joined only for evaluation. Features derived from cumulative activity, recent windows, or assessments are computed relative to the cutoff rather than the course end.

This framing changes the object of evaluation. The model does not receive “the learner” in an abstract sense; it receives a versioned representation of recorded learner evidence at a particular time. The question is therefore not only whether a model discriminates outcomes, but whether the representation faithfully corresponds to what could have been known when the prediction was purportedly made.

RQ2 follows from this requirement. A temporal pipeline should be capable of demonstrating its cutoff boundary rather than relying solely on an implementation claim. That motivates explicit provenance and a deterministic audit of the source times associated with each constructed state.

## 2.5 Data Provenance, Reproducibility, and Auditability

Data provenance records where a value came from and how it relates to its source. In a temporal learning-analytics pipeline, provenance can connect a derived learner-state feature to the activity or assessment records that contributed to it. This lineage is different from a feature value itself: the feature supports modelling, whereas the lineage supports inspection of how the feature was constructed.

Reproducibility frameworks in educational data mining emphasise the need to preserve defined datasets, execution conditions, and evaluation procedures. MORF, for example, addresses reproducible predictive modelling over privacy-restricted MOOC data through controlled remote execution [23]. Its setting differs from the present project, but it illustrates why educational prediction requires more than a reported metric: the data and procedure governing that metric must be recoverable within appropriate privacy boundaries.

Digital-twin literature also treats connection to observations and evolving state as central to the concept [5]. Educational reviews extend this discussion to monitoring, personalisation, and institutional uses while noting challenges around integration, privacy, interoperability, and synchronisation [6], [7]. For a checkpointed educational representation, provenance supplies a concrete link between the stored state and the observations from which it was derived.

Source-level lineage supports several purposes. It allows a reviewer to inspect which events contributed to a value, helps developers diagnose unexpected aggregates, and permits an audit to test whether source times respect a state cutoff. It also assists reproducibility because a future run can compare not only the final feature value but also its contributing evidence. In an instructor-facing setting, evidence identifiers can support a trace from a generated claim back to the state and then to source observations.

Provenance does not prove that a source event is correct, that the source is complete, or that a prediction is accurate. It records the lineage available to the system. If an upstream timestamp is wrong, lineage can expose the timestamp used but cannot reconstruct the true event time. If an event was never recorded, provenance cannot reveal its content. These limitations prevent auditability from being misrepresented as truth.

The relevant research gap is therefore not that provenance has never been used. For this thesis, temporal provenance, predictive evaluation, and instructor-facing evidence are connected closely enough to answer “what was knowable at time `t`?” for the exact state behind a result. This source-to-feature temporal audit is a project-specific methodological response to the broader needs for reproducibility and inspectable state identified above. The thesis therefore makes provenance part of the evaluated state contract rather than leaving it as operational metadata.

## 2.6 Missingness and Data Availability in Learning Analytics

Educational records are incomplete for several reasons. A learner may have had no activity in a period, an assessment may not yet have been due, a source system may not provide a field, an ingestion process may be incomplete, or an event may be absent from the available dataset. These situations can all appear as an empty value, but they have different meanings for prediction and explanation.

Treating missing as zero can be appropriate only in a defined context. If an activity feed is complete and no qualifying event exists in a window, a zero may represent an observed absence. If the feed failed to load, the same zero would falsely imply inactivity. If a course does not use a particular resource type, the absence is structural rather than learner-specific. If an assessment is not yet due, recording it as missed introduces future course structure into an adverse interpretation.

The OULAD dataset illustrates both the value and limits of linked educational records. It provides course, registration, assessment, learner, resource, and daily virtual-learning-environment activity tables [19], [20]. It supports longitudinal reconstruction, but its daily click aggregates are not exact event sequences, and it does not contain every contextual observation that an instructor might use. The dataset documentation therefore grounds what fields are available; it does not justify inferring unavailable constructs.

Missingness also interacts with course context. A low count can be surprising in a course that requires daily online participation but ordinary in a period dominated by offline work. The difference between “nothing was observed” and “the system does not know” affects both a statistical feature and any generated explanation. A model may require a numeric matrix, but the canonical learner state can still retain a separate availability category so that preprocessing does not redefine unknown evidence as genuine zero.

The exact categories used by this thesis—such as observed, structural zero, no activity yet, not yet applicable, source missing, incomplete ingestion, and unsupported—are a project design rather than a taxonomy attributed to prior literature. They organise the availability distinctions required by this study and are not presented as a universal educational-data taxonomy. The thesis does not assume that typed missingness necessarily improves predictive performance. Its purpose is to preserve meaning and support safer downstream interpretation.

This issue connects all four research questions. Temporal prediction depends on what evidence is available at a checkpoint. A cutoff audit must distinguish absence from an event occurring later. An LLM should not turn incomplete evidence into a confident adverse claim. An instructor should be able to see whether a value represents behavior, course timing, or data quality.

## 2.7 Digital Twins in Education

The digital-twin concept originated in engineering contexts where a digital representation is connected to observations of a physical entity or process. Fuller et al. review enabling technologies, challenges, and open research associated with digital twins [5]. Common themes include evolving state, data connection, modelling, and the capacity to inspect or reason about the represented system. Definitions vary in how strongly they require continuous synchronisation, simulation, or bidirectional interaction.

Educational applications broaden the concept further. Reviews of digital twins in e-learning and education describe uses involving monitoring, simulation, personalisation, institutional planning, and representations of learners or learning environments [6], [7]. This diversity creates opportunity but also ambiguity. A static dashboard, a predictive model, a simulated student, and an institution-wide data platform may all be described as digital twins despite having different state, synchronisation, and evaluation properties.

The variation makes an operational definition necessary. This thesis uses the conservative term “a provenance-aware, checkpointed course digital twin.” The represented entity is the course participation of a learner at declared checkpoints. The twin contains temporal learner states, predictive or generated analyses tied to those states, evidence provenance, and historical instructor support decisions. Checkpointing reflects the granularity and research design of the available data rather than claiming continuous synchronisation.

The word “course” is equally important. The representation is conditioned by the presentation, course schedule, assessments, and available LMS evidence. It is not a comprehensive student replica and does not claim to model a learner across every context. It also does not infer an internal psychological state. Its state variables describe recorded academic and platform evidence.

The digital-twin framing adds value only when it denotes maintained history and traceable relationships. A prediction alone is not the twin, and neither is the interface. The relevant representation links evidence to a time-specific state, a model result or validated analysis, an instructor interpretation, and subsequent support actions. Versioning permits earlier states and decisions to remain inspectable when new evidence arrives.

This position acknowledges rather than resolves the contested breadth of educational digital-twin definitions. It does not assert that every digital twin must be real-time or that checkpointing is the universal model. It defines the claims made by this thesis and aligns them with the implemented temporal and evidential boundaries.

## 2.8 Explainability, Ethics, and Human Oversight

Predictive learning analytics affects people and therefore raises questions beyond discrimination metrics. Slade and Prinsloo identify ethical issues involving privacy, transparency, informed participation, responsibility, and power in learning analytics [18]. These concerns are especially relevant when a model labels a learner as at risk or when an instructor uses analytics to prioritise support.

Transparency can refer to several different properties. A model may expose feature attributions, an interface may show source evidence, or an institution may disclose how data are used. SHAP provides a principled feature-attribution method for compatible predictive models [15], but an attribution explains a model's behavior rather than establishing that the model is correct or that the relationship is causal. Counterfactual explanations similarly require care because feasible changes in a feature vector may not correspond to ethical or educationally actionable interventions [16].

Recent work on explainable and prescriptive learning analytics considers how predictive outputs might be connected to explanations and suggested action, including through generated language [24]. This connection can make analytics more accessible, but it also enlarges the claim boundary. A recommendation can sound plausible while extending beyond what the model or evidence supports. Explanation quality should therefore be evaluated separately from prediction quality.

Human oversight is not achieved merely by placing a confirmation button after an automated result. Meaningful oversight requires access to the evidence, clarity about uncertainty and missingness, authority to disagree, and a record of the human decision. The model's output should remain visible as historical evidence without becoming the instructor's decision by default. Conversely, an instructor's resolution of a case should not retroactively change what the model produced.

Privacy and access control remain central. Educational records can reveal sensitive patterns even when direct identifiers are removed. Data minimisation, pseudonymisation, course-level authorisation, purpose limitation, and audit trails reduce exposure but do not eliminate governance obligations. NIST's Generative AI Profile similarly emphasises documentation, measurement, human oversight, and controls for confabulation, privacy, and misuse [9]. General principles must still be translated into the exact educational task and institutional policy.

This literature motivates an evidence-first instructor interface and the separation examined by RQ4. It does not support a claim that human review guarantees ethical use or that explanation necessarily improves decisions. Those outcomes require educator and institutional evaluation.

## 2.9 LLMs for Evidence-Grounded Instructor-Facing Analysis

Instruction-tuned LLMs can produce concise text, transform information into structured fields, and generate explanations or suggested actions. TabLLM demonstrates that tabular records can be serialized into text for few-shot classification with language models [8]. In learning analytics, a related approach can present a compact learner state to an LLM and request an instructor-facing analysis.

The attraction is flexibility. A single structured input may contain activity windows, assessment participation, missingness, and evidence identifiers, while the generated output can summarise concerns in an accessible form. Locally hostable models can also offer deployment options where sending educational data to an external service would be inappropriate. These possibilities do not establish that the generated analysis is correct or suitable for consequential use.

Generated text introduces distinct failure modes. A response can be syntactically malformed, use a field outside the allowed contract, cite an evidence item that was not supplied, misread an existing value, infer a cause that is not observed, recommend an unsupported action, or answer when the evidence is insufficient. Non-deterministic generation and changes in model or prompt version further complicate reproducibility. The NIST profile treats confabulation, privacy, documentation, and human oversight as risks requiring explicit management [9].

Evidence grounding narrows the allowed basis of a generated claim. Instead of inviting a free-form explanation from raw tables or student text, an application can supply a versioned learner state with allow-listed evidence identifiers. The output can then cite only those identifiers and choose from a constrained claim vocabulary. This makes validation possible, but citation presence is not the same as faithful interpretation. A claim can cite a real evidence item whose value does not satisfy the claim's rule.

The distinction between prediction and generated analysis is essential. A predictive model estimates a score or class under an empirical evaluation protocol. An LLM-generated analysis transforms supplied evidence into structured claims and actions under a different contract. Unless evaluated against learner outcomes, the latter should not inherit the predictive status or metrics of the former. Operational validation records likewise describe contract behavior, not academic-risk accuracy.

The literature supports investigating language models over structured data [8] and applying risk-management controls to generated outputs [9]. It does not, within the approved sources, establish that an LLM is a reliable student-risk predictor. The thesis therefore evaluates grounding and reliability through a separate controlled question rather than using generated fluency as evidence of educational validity.

## 2.10 Structured Generation, Validation, and Abstention

Structured generation constrains an LLM response to a declared format such as JSON. This is valuable for software integration because required fields, types, ranges, and enumerations can be checked automatically. A well-defined output can include a state identifier, risk score, claim codes, evidence identifiers, suggested actions, uncertainty, and abstention status. For the purposes of this thesis, the reliability concerns motivated by the literature are organised into distinct structural, evidential, semantic, policy, behavioral, and provenance dimensions.

Within this thesis framing, schema validity answers only whether the representation conforms. It does not establish whether a cited identifier exists, whether the cited value supports the claim, whether the action is allowed, or whether the overall decision is appropriate. These properties are treated as separate reliability dimensions rather than one binary notion of correctness; the review does not attribute this exact layered design to a single prior source.

Evidence-reference validation tests whether an output cites items included in the supplied state. Semantic validation asks whether those values satisfy the predicate associated with a claim. Policy validation checks whether a claim or action is permitted and whether privacy, freshness, or completeness rules are respected. Behavioral evaluation asks whether the system assessed or abstained as expected under the scenario. Passing an earlier layer enables later checks but does not guarantee them.

Insufficient evidence creates a special requirement. If core observations are missing, stale, contradictory, or out of scope, the appropriate response may be to abstain. Including an `abstain` field in the schema does not ensure that the model will use it selectively. Abstention is a behavioral property that requires explicit prompting, evaluation, and, where rules can be expressed deterministically, application-level sufficiency gates.

Repair can address some malformed outputs, but it also requires a bound. Unlimited retries may hide instability, increase latency, and make the final provenance unclear. A bounded repair policy can make one controlled attempt, record the original failure, and otherwise reject or abstain. Validation should similarly record its outcome rather than silently discarding problematic generations.

**Table 2.2. Reliability dimensions for instructor-facing generated analysis**

| Dimension | Question | Failure example | Design implication |
|---|---|---|---|
| Structure | Does the output satisfy the declared schema and field types? | Missing required field or undocumented property | Enforce a versioned schema before accepting output |
| Evidence reference | Does every cited identifier exist in the supplied state? | Claim cites an assessment absent from the input | Reject fabricated or cross-state references |
| Semantic support | Does the cited value satisfy the claim predicate? | A valid activity identifier is cited as low activity although its value is above the rule threshold | Recompute deterministic claim predicates |
| Policy compliance | Are claims and actions permitted under the application policy? | Generated action exceeds the instructor-support allowlist | Apply allowlists, privacy gates, and state-origin checks |
| Missingness handling | Is availability interpreted according to its recorded meaning? | Incomplete ingestion is described as learner inactivity | Preserve typed missingness and block unsupported interpretation |
| Abstention | Does the system decline when minimum evidence is absent or conflicting? | A confident score is returned for a stale or empty state | Evaluate selective behavior and implement sufficiency gates |
| Provenance | Can the accepted or rejected output be reconstructed? | Prompt, model, state, or validation version is absent | Persist versions, evidence links, attempts, and outcomes |

This layered distinction motivates RQ3. The question is not merely whether an LLM can produce JSON, but how structural constraints and deterministic validation affect evidence compliance, abstention, and operational reliability. The controlled evaluation is introduced later; no outcome is assumed by the literature review.

## 2.11 Human-in-the-Loop Learning Support

Early-warning analytics is often intended to inform human action. An instructor may review a learner's evidence, set a priority, add contextual knowledge, schedule follow-up, or decide that no support case is warranted. These actions create information that was not present in the model output. For this thesis, the human-in-the-loop architecture is therefore designed to represent that information explicitly rather than treating the instructor as a passive confirmation step.

Model state, human interpretation, and support workflow operate on different timescales. A risk state belongs to a particular learner checkpoint and model version. Triage can change as an instructor reviews the evidence or gains additional context. A support case may remain open across several checkpoints and contain notes, actions, follow-up dates, and closure decisions. Collapsing these states can destroy historical meaning.

For example, resolving a support case should not alter the score or evidence that originally prompted review. A later low-risk state should not erase the fact that support was previously provided, and an older prediction should not be silently attached to a newer learner state. Exact binding and immutable historical records allow a later reviewer to reconstruct what the system showed and what the instructor decided.

Human authority also requires the ability to disagree. The system may prioritise attention, but the instructor remains responsible for interpreting evidence within the course context. Ethical learning-analytics literature stresses the need to consider transparency, privacy, responsibility, and the distribution of power rather than treating analytics as neutral [18]. The audit trail should therefore include both automated and human events without implying that either is infallible.

An unresolved design concern is how to maintain a usable longitudinal workflow while preserving these distinctions. Existing early-warning research establishes the predictive and alerting context [2], [3], and responsible-learning-analytics literature establishes the importance of accountability [18]. The thesis addresses the representation problem through independently versioned risk, triage, and support-case states. RQ4 evaluates whether this separation can be implemented and kept auditable; it does not assume that the resulting interface improves educator effectiveness.

## 2.12 Synthesis of the Research Gap

The reviewed literature establishes that LMS activity and assessment evidence can support predictive learning analytics and early-warning systems [1]–[3]. It also establishes that course and instructional context affect prediction [4], that digital-twin concepts emphasise evolving representations connected to observations [5]–[7], that structured records can be presented to LLMs [8], and that generated-AI and learning-analytics systems require oversight, documentation, privacy, and accountability [9], [18]. The gap addressed by this thesis lies in integrating and evaluating these concerns within one bounded framework.

First, temporal prediction must be checkpoint-aware. An early-warning claim requires a declared observation cutoff, and performance at one point should not be assumed to represent another. The thesis responds by constructing learner states and evaluating predictive behavior separately at several checkpoints. This directly motivates RQ1.

Second, temporal claims require cutoff-safe evidence. Strong metrics are not credible if feature construction uses information that became available later. The thesis responds by applying the cutoff during state construction, excluding final outcomes from inputs, and auditing the time of every recorded provenance link. This motivates RQ2 without claiming that one audit proves universal leakage freedom.

Third, provenance and missingness require explicit representation. A derived value should remain traceable to its sources, and an absent value should retain whether it means observed zero, not yet applicable, unavailable, incomplete, or unsupported. These properties are not claimed to improve prediction automatically. They make the state semantically inspectable and create a safer basis for modelling and explanation.

Fourth, LLM-generated analysis needs evaluation beyond formatting. Structured output can enable parsing and citation checks, but schema validity, citation existence, semantic support, policy compliance, and behavioral correctness remain distinct. The thesis responds with a controlled comparison and deterministic validators rather than treating fluent or parseable output as reliable by default.

Fifth, abstention requires explicit treatment. A model that can populate an abstention field may still answer when evidence is insufficient. The thesis therefore treats abstention as a behavior to be tested and as an application-level quality outcome supported by evidence sufficiency rules, bounded repair, and rejection paths.

Sixth, model and human workflow states require auditable separation. A model output is evidence for review, not the instructor's decision, and a triage decision is not the same as a longitudinal support case. The thesis responds by binding prediction or validated analysis to the exact learner state while storing triage and support histories independently. This motivates RQ4.

**Table 2.3. Literature-gap-to-research-question mapping**

| Identified gap | Why it matters | Thesis response | RQ |
|---|---|---|---|
| Predictive behavior can vary with observation time and course context | A single aggregate result can obscure whether useful signal exists early enough for support | Checkpoint-specific state construction and empirical evaluation | RQ1 |
| Early-warning inputs may include information unavailable at the claimed prediction time | Future-information leakage can produce scientifically misleading performance | Cutoff-first feature construction and deterministic temporal provenance audit | RQ2 |
| Derived values can lose source lineage and absence can have several meanings | Reviewers cannot distinguish observed behavior from unavailable or inapplicable evidence | Source-linked provenance and explicit availability/missingness semantics | RQ2 and RQ3 |
| Structured or cited generated output can still be semantically unsupported | Machine-readable format does not establish faithful interpretation or safe action | Controlled grounding evaluation plus deterministic evidence and policy validation | RQ3 |
| An abstention field does not guarantee selective response | Insufficient evidence may still produce a confident analysis | Explicit abstention scenarios, sufficiency rules, bounded repair, and rejection | RQ3 |
| Model evidence, instructor interpretation, and support history have different meanings | Collapsing them weakens accountability and historical reconstruction | Exact state binding and independent versioned triage and support-case state | RQ4 |

The thesis thus addresses an integration and evaluation gap, not an absolute absence of related work. Prior research informs each component, and some systems may implement subsets of the same concerns. The contribution is to connect cutoff-safe temporal state, source provenance, typed availability, empirical prediction, controlled LLM reliability evaluation, and human workflow separation while preserving distinct claim boundaries for each evidence stream.

## 2.13 Chapter Summary

This chapter has established the conceptual basis for the methodology that follows. Learning-analytics and early-warning research supports the use of LMS activity and assessment evidence but also demonstrates contextual dependence. Temporal prediction requires explicit checkpoints and creates a trade-off between lead time and accumulated signal. Cutoff-safe construction and provenance make the evidence available at each checkpoint auditable, while explicit missingness semantics protect the distinction between observed absence and unavailable data.

Educational digital-twin literature motivates a stateful representation linked to observations, but its heterogeneous definitions require a conservative scope. The thesis therefore uses a provenance-aware, checkpointed course digital twin rather than claiming a real-time or causal replica. Explainability and ethics literature motivates evidence presentation, privacy, accountability, and human oversight. Work on LLMs over structured data motivates generated analysis, while generative-AI risk guidance motivates deterministic controls and retained provenance.

The resulting research gap connects four questions: how prediction changes over time, whether the temporal state remains cutoff-safe, whether generated analysis is grounded and selectively reliable, and whether human decisions remain auditable but independent from model state. Chapter 3 translates these questions into separate empirical, controlled, operational, and framework methodologies without treating their evidence as interchangeable.

<!-- FINAL INTEGRATION NOTE:
No temporary references were added in this pass, and no unresolved citation markers remain. Existing numbered citations retain their current identities pending global bibliography assembly.
-->
