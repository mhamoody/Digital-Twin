# 1. Introduction

## 1.1 Background and Context

Digital learning environments have become a routine part of higher education. Learning management systems (LMSs) mediate access to course resources, assessment submission, discussion, communication, and the recording of grades. In performing these functions, they accumulate longitudinal records of observable learner activity and academic progress. Learning analytics research has shown that such records can support early-warning models and help identify learners who may require timely attention [1]–[3]. However, the practical value of these models depends on more than their ability to assign a risk score. Course structure, assessment timing, instructional conditions, missing data, and the point in the semester at which a prediction is made all affect how a result should be interpreted [4].

An instructor making a support decision does not observe a learner as a single static row. Evidence develops over time: a resource is accessed, an assessment becomes due, a submission is recorded, or a period of inactivity grows. At early checkpoints this evidence may be sparse, incomplete, or ambiguous. Low recorded activity may indicate an emerging concern, a period in which little activity was required, or a limitation in what the source system captured. A representation intended for early support should therefore distinguish what was available at a particular checkpoint from what became known later, while retaining the origin and availability of the observations used to derive each feature. Without these safeguards, a nominally early prediction can contain future assessment results, withdrawal information, or end-of-course aggregates, creating temporal leakage and overstating predictive performance.

Interpretability in this setting also requires traceability. A statement that a learner is at elevated risk is of limited value if the instructor cannot identify the state assessed, the evidence available at that time, the model or rule that produced the result, and any validation applied before display. Traceability is equally important after a prediction is produced. An instructor may review the evidence, change a triage priority, open a support case, record a follow-up, or close the case. Those human decisions should form an auditable history without modifying the model output that originally informed them. This distinction supports accountability and reduces the risk that later workflow actions obscure what the system actually predicted.

The digital-twin concept offers a useful framing for these requirements. In engineering, a digital twin commonly combines an evolving representation of an entity with observations, state history, and update processes [5]. Educational applications have extended this idea to monitoring, simulation, personalization, and institutional planning, while also identifying difficulties around interoperability, privacy, faithful synchronization, and inconsistent use of the term [6], [7]. This project adopts a deliberately bounded interpretation: **a provenance-aware, checkpointed course digital twin that connects temporal learner-state reconstruction, predictive analysis, validated instructor-facing evidence, and auditable human support decisions**.

This definition does not imply a real-time or continuously synchronized system. It does not model cognition, motivation, emotion, or other unobserved psychological states, and it does not provide a causal simulation of student behavior. Instead, it represents observable course evidence at declared checkpoints and preserves the relationships among source observations, derived learner states, model results, and subsequent human decisions. The resulting twin is course-level because its state semantics depend on the course calendar, assessment schedule, checkpoint policy, and available LMS evidence. Individual learner states are components of that course representation rather than comprehensive simulations of students.

The project also examines the role of large language models (LLMs) in instructor-facing analysis. Prior work demonstrates that structured tabular records can be serialized for instruction-tuned language models [8]. LLMs may provide flexible structured analysis and concise evidence summaries, but they introduce distinct failure modes: malformed output, unsupported claims, inappropriate actions, failure to abstain, and confident interpretation of insufficient evidence. General guidance for generative-AI systems consequently emphasizes measurement, documentation, human oversight, and controls for confabulation and misuse [9]. Within this project, generated output is therefore treated as untrusted until it passes deterministic structural, evidential, semantic, and policy checks. This operational role is separate from the empirical prediction experiment described in this thesis.

## 1.2 Problem Statement

The research problem is how to construct and evaluate an auditable course-level representation that supports early predictive analysis while preserving temporal validity, evidence traceability, and the independence of human support decisions. Existing early-warning approaches demonstrate that LMS activity and assessment data can contain predictive signal [1]–[4], but a static prediction alone does not provide the complete basis required for defensible instructor support.

First, a static record can conceal the temporal conditions under which a prediction was produced. The same learner may have substantially different evidence at weeks 3, 5, 8, and 10. Predictive performance may also change across those checkpoints as assessments become available and activity patterns develop. Treating these states as equivalent can obscure when useful predictive discrimination becomes available and whether a model is appropriate for early intervention.

Second, temporal leakage can invalidate an early-warning analysis. Outcomes, future withdrawal dates, later submissions, and course-end activity totals can make a retrospective classifier appear effective while providing information that would not have existed at the intended decision point. A credible evaluation must construct each state from evidence available on or before its cutoff, fit preprocessing only within the training data, and keep each learner's related states from crossing incompatible split boundaries.

Third, a prediction must remain tied to the exact learner state it assessed. Independently selecting the latest state and the latest available prediction can pair records from different checkpoints. Similarly, a comparison that skips a missing checkpoint and searches for an older convenient result can misrepresent change over time. Exact state binding and explicit comparison availability are therefore necessary integrity properties, not merely presentation details.

Fourth, human workflow state must not overwrite model history. Model risk, instructor triage, and support-case status describe different facts. A risk result records an analysis of a particular state. Triage records an instructor's current prioritization. A support case records longitudinal human action, including review, follow-up, resolution, or dismissal. Combining these concepts into a single mutable status would make it difficult to reconstruct the evidence and reasoning available at each stage.

Finally, LLM-generated analysis creates a reliability problem that cannot be solved by valid JSON alone. An output may satisfy a structural schema while citing irrelevant evidence, contradicting the supplied values, selecting an unsupported action, or failing to abstain when assessment is not justified. Structurally constrained generation can improve format and citation behavior without guaranteeing correct selective decisions. Generated analyses consequently require deterministic validation, bounded correction, explicit abstention, and retained model and prompt provenance before they can safely support instructor review.

The project addresses these connected problems without assuming that one model or interface resolves them. Its practical educational purpose is to connect machine analysis with an instructor's traceable review, follow-up, and support decisions while preserving the evidence available at the original checkpoint. Empirical prediction, temporal integrity, controlled LLM grounding, operational LLM reliability, and human-in-the-loop traceability are evaluated as separate evidence streams. This separation prevents product completion or synthetic demonstration results from being mistaken for empirical educational validity.

## 1.3 Motivation

Timely learner support is difficult when relevant evidence is distributed across activity logs, assessment records, gradebook views, and communication tools. An instructor may need to determine whether apparent inactivity reflects an emerging concern, a period with no required activity, missing data, or a learner whose assessed work remains satisfactory. A useful decision-support system should therefore expose the evidence and its temporal context rather than reducing the learner to an unexplained label.

Temporal validity is central to that goal. If a week-3 result incorporates information first available at week 8, it cannot support a legitimate week-3 decision regardless of its apparent accuracy. A provenance-aware construction makes the cutoff inspectable and permits derived features to be traced to their contributing observations. It also makes negative findings meaningful: the system can distinguish no observed activity from unavailable data, and an assessment not yet due from a missed submission.

Trustworthy model use requires similar care. Predictive discrimination is relevant, but it does not show that a score is calibrated, that an explanation is grounded, or that an intervention will improve outcomes. For LLM-generated analyses, fluent language can further mask unsupported reasoning. The project is motivated by the need to combine model capability with deterministic controls that can reject malformed, unsupported, or policy-conflicting output and record an explicit no-score outcome when the evidence is inadequate.

Human oversight is not treated as a final approval button attached to an otherwise autonomous pipeline. Instructor review creates its own information: priority, notes, planned actions, follow-up dates, and closure decisions. Preserving that information separately enables longitudinal support while maintaining an immutable account of earlier model evidence. This approach aligns with ethical concerns in learning analytics concerning transparency, privacy, responsibility, and the distribution of decision-making authority [18]. It also avoids implying that observable clicks, submissions, or grades directly measure motivation or explain why a learner behaves in a particular way.

The research value therefore lies in connecting temporal representation, empirical evaluation, controlled LLM assessment, and auditable human workflow without collapsing their different meanings. The implemented instructor-facing prototype makes these relationships reviewable, but the interface itself is an engineering contribution rather than the source of the thesis's research novelty. Claims of value are consequently tied to defined comparisons and evidence: predictive behavior across checkpoints, provenance against cutoff rules, controlled LLM treatments, and operational validation outcomes. A formal study of educator usability or effectiveness was not completed and remains outside the evidential claims of this thesis.

## 1.4 Aim and Objectives

The overall aim of this project is:

> **To design and evaluate a provenance-aware course digital twin that reconstructs cutoff-safe temporal learner states, supports checkpoint-specific predictive analysis, validates instructor-facing LLM outputs, and preserves auditable human support decisions.**

To achieve this aim, the project pursues the following objectives:

1. **Construct temporal learner states.** Transform available activity, assessment, registration, and course-context records into versioned learner states at declared checkpoints, with explicit treatment of availability and missingness.
2. **Preserve provenance and temporal integrity.** Link derived state values to their supporting observations and audit those links for evidence that occurs after the applicable checkpoint cutoff.
3. **Evaluate checkpoint-specific empirical prediction.** Measure how predictive discrimination changes across early course checkpoints using a leakage-controlled, learner-grouped evaluation protocol.
4. **Evaluate controlled LLM grounding behavior.** Compare unconstrained and schema-constrained generation on a frozen set of cases, assessing structural compliance, citation validity, semantic evidence use, abstention, and behavioral decisions.
5. **Implement operational LLM safeguards.** Apply deterministic validation, bounded repair, explicit quality abstention, and model/prompt provenance to instructor-facing generated analyses.
6. **Separate model and human state.** Represent prediction or analysis state, instructor triage, and support-case state independently so that human actions remain auditable and do not rewrite historical model evidence.
7. **Provide an instructor-facing prototype.** Operationalize the temporal, evidential, and human-in-the-loop contracts through an authenticated course workspace suitable for inspecting learner evidence and recording support decisions.

These objectives distinguish research evaluation from engineering realization. The frontend, API, persistence layer, worker, and deployment environment make the research artifacts inspectable and the workflow demonstrable; they are not treated as experimental proof of educational effectiveness.

## 1.5 Research Questions

The final investigation is organized around four research questions.

**RQ1 — Temporal Prediction:**  
How does predictive performance evolve across cutoff-safe learner states at early course checkpoints?

**RQ2 — Temporal Integrity:**  
Can a provenance-aware temporal learner-state pipeline prevent post-cutoff information leakage while preserving traceability?

**RQ3 — LLM Grounding and Reliability:**  
How do structural constraints and deterministic validation affect evidence compliance, abstention behavior, and operational reliability of LLM-generated instructor-facing analyses?

**RQ4 — Human-in-the-loop Traceability:**  
How can model risk, instructor triage, and longitudinal support decisions be represented separately while preserving historical model evidence?

RQ1 is answered through the empirical prediction experiment. RQ2 is addressed through deterministic provenance auditing and the implemented temporal contracts. RQ3 combines two explicitly separate forms of evidence: a controlled grounding experiment and operational reliability records. RQ4 is a framework and system-design question supported by persistence invariants and workflow implementation; it is not an experiment demonstrating educator effectiveness or improved learner outcomes.

## 1.6 Scope and Research Boundaries

The empirical scope is the Open University Learning Analytics Dataset (OULAD), a linked and anonymized educational dataset containing course, registration, assessment, and daily virtual-learning-environment activity records [19], [20]. The primary empirical evaluation uses the `AAA/2013J` presentation, comprising 383 source enrolments, 372 eligible learners, and 1,464 temporal states. States are evaluated at weeks 3, 5, 8, and 10. Logistic Regression is the empirical predictor used for the frozen checkpoint evaluation. Its reported AUROC and Average Precision values measure predictive discrimination; they are not Qwen results and are not calibrated probabilities.

The temporal-integrity evaluation audits the provenance connecting source observations to derived features. Its result is scoped to the evaluated artifacts and pipeline version. It does not prove that every future dataset, source adapter, or feature definition is leakage-free.

The operational LLM is `qwen2.5:7b`, used to generate structured instructor-facing analyses in the Workspace pathway. Its mature contract includes deterministic validation, bounded repair, explicit quality abstention, and retained model/prompt provenance. Operational records provide evidence about contract compliance, validation outcomes, repair, abstention, and latency. They do not establish empirical Qwen predictive accuracy, calibrated Qwen probabilities, or superiority over the Logistic Regression evaluation.

The controlled E2 experiment is also distinct from the operational history. It uses 48 frozen cases across 12 scenario families, split evenly between cases where assessment is allowed and cases where abstention is expected. Its primary comparison is `plain_llm` v2 versus `schema_only` v2. Because these cases are controlled and deterministic, the findings concern grounding and decision behavior under the protocol; they are not estimates of real-course predictive performance.

Synthetic Workspace courses and learners are used to exercise product behavior, model operations, course policy, failure handling, and human workflows. They do not represent authentic learner behavior and do not provide cross-course empirical validation. Similarly, the legacy `simple-rules-v1` path supports operational demonstration and historical alerts but does not constitute a trained or calibrated research predictor.

The project does not establish cross-institution generalization, cross-course empirical generalization, empirical Qwen predictive accuracy, calibrated Qwen probabilities, educator effectiveness, causal intervention effects, or real-time digital-twin behavior. It also does not claim that instructor support caused subsequent changes in observed activity or performance. These boundaries define future research opportunities rather than defects in the completed scoped evaluation.

## 1.7 Research Contributions

The contributions are organized according to their evidential status.

The **primary research contributions** are:

1. **Provenance-aware cutoff-safe temporal learner-state construction.** The project defines and implements checkpointed learner states in which derived evidence is linked to source observations and governed by explicit availability cutoffs.
2. **Checkpoint-specific empirical predictive analysis across early learner states.** The empirical study evaluates how held-out Logistic Regression discrimination develops at weeks 3, 5, 8, and 10 rather than reporting a single course-level performance value.
3. **Controlled evidence about the limits of structural and citation compliance.** The E2 experiment shows that schema-constrained generation can substantially improve structural and citation compliance without, by itself, improving selective abstention or behavioral decision accuracy.

The **secondary research contribution** is a versioned, evidence-grounded operational LLM pipeline with deterministic validation, bounded repair, explicit quality abstention, and auditable prompt/model provenance. This contribution concerns operational reliability and safe handling of generated analyses. It is not evidence of predictive accuracy.

The **framework contribution** is the separation of prediction or model state, instructor triage, and support-case state. This separation preserves the evidence and provenance associated with a historical analysis while allowing instructors to maintain independent priorities and longitudinal support records.

The project also includes substantial **engineering and product contributions**: a React instructor workspace, FastAPI services, authentication and course authorization, relational persistence, worker and runtime infrastructure, support workflows, deployment tooling, and a Streamlit fallback. These components operationalize and demonstrate the research contracts. They are not presented as research novelty in themselves.

## 1.8 Overview of the Evaluation Strategy

The evaluation separates four principal evidence streams so that each conclusion retains an appropriate denominator and claim boundary.

**E1, empirical prediction**, evaluates Logistic Regression on cutoff-safe OULAD `AAA/2013J` states. It uses learner-grouped splitting, train-only preprocessing, validation-based threshold selection, and an untouched test partition. It addresses how predictive discrimination varies across the four selected checkpoints.

**E4, temporal integrity**, audits the provenance links used to construct temporal learner states against the declared checkpoint cutoffs. It supports RQ2 by providing deterministic evidence about traceability and post-cutoff leakage for the audited artifacts, without generalizing the result to every possible source or implementation.

**E2, controlled LLM grounding**, compares plain and schema-constrained generation on 48 frozen cases. It evaluates structural output, evidence citations, semantic support, constraints, abstention, and behavioral correctness. The central finding is that schema constraints substantially improve structural and citation compliance but do not alone improve selective abstention or behavioral decision accuracy.

**Operational LLM evidence** examines saved Qwen analyses under the operational validation pipeline. It supports the reliability component of RQ3 through records of structured validation, bounded repair, quality abstention, latency, failure categories, and model/prompt provenance. Comparisons between mature prompt versions are limited to operational first-pass and repair behavior where attribution and denominators permit them. Because failed jobs do not retain prompt-version metadata and the records are not an empirical outcome study, this evidence is reported as operational reliability rather than predictive performance.

Implementation and workflow evidence complements these streams. Automated tests and persistence contracts examine exact state binding, temporal comparison, course authorization, idempotency, optimistic locking, immutable analyses, independent triage, and support-case history. Together, these checks establish that the instructor-facing prototype implements the intended human-in-the-loop traceability. They do not substitute for a formal educator usability or effectiveness study.

## 1.9 Report Organization

The remainder of this report is organized into six chapters. **Chapter 2, Background and Literature Review**, reviews early-warning learning analytics, temporal educational data, digital-twin concepts, LLM use with structured evidence, grounding and abstention, and responsible human oversight. It identifies the gap addressed by connecting these concerns within one provenance-aware and auditable framework.

**Chapter 3, Methodology**, describes the datasets, temporal-state construction rules, prediction target, split strategy, evaluation protocols, provenance audit, controlled E2 experiment, operational evidence collection, and validity safeguards. It explains why the empirical, controlled, operational, and synthetic evidence streams are reported separately.

**Chapter 4, Design and Implementation**, presents the system architecture, canonical observations, temporal state and prediction binding, validation pipeline, persistence design, API boundary, React workspace, operational worker, triage model, support-case workflow, and audit mechanisms.

**Chapter 5, Results and Evaluation**, reports the E1 checkpoint metrics, E4 audit findings, E2 treatment results, operational Qwen evidence, and relevant software verification. Detailed tables, diagnostic counts, and comparisons are reserved for that chapter.

**Chapter 6, Discussion**, interprets the results against the research questions, considers the relationship between structural compliance and decision reliability, evaluates the digital-twin claim, and discusses validity, ethics, generalization, and practical limitations.

**Chapter 7, Conclusion and Future Work**, summarizes the completed contributions, states the defensible conclusions, and outlines future work in calibration, empirical Qwen evaluation, cross-course replication, educator studies, institutional integration, and richer temporal modeling.
