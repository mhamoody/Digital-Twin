# 4. Design and Implementation

## 4.1 System Design Objectives

The system was designed to operationalize the research method described in Chapter 3 without treating the user interface as the research contribution. Its central engineering task was to preserve the meaning of time-specific learner evidence from ingestion to instructor review. An instructor-facing result therefore had to remain connected to the exact learner state on which it was produced, expose the supporting observations, and retain the versions of the feature, policy, model, prompt, and output contract that governed its creation. The implementation also had to preserve missing and unavailable evidence rather than silently converting it to zero.

Eight objectives guided the final design. First, state construction had to respect declared checkpoint cutoffs. Second, every analysis or prediction had to be bound to its exact learner state. Third, evidence used in a model claim had to be inspectable. Fourth, generated LLM output had to be treated as untrusted until deterministic checks accepted it. Fifth, model risk, instructor triage, and support-case status had to remain independent. Sixth, earlier states, analyses, and human actions had to remain historically available. Seventh, failures had to produce explicit rejection or abstention rather than fabricated fallback evidence. Eighth, authenticated instructors needed a practical workspace in which to inspect evidence and maintain follow-up history.

These objectives connect the research architecture to the implemented product. The cutoff-safe state and provenance contracts support the temporal-integrity contribution; the empirical and controlled evaluation paths test separate research questions; and the application makes their underlying contracts observable and auditable. React, FastAPI, persistence, authentication, and deployment are necessary engineering components of that system. They demonstrate that the contracts can be implemented, but their existence alone is not claimed as scientific novelty.

## 4.2 Overall System Architecture

The final system uses a layered architecture. Source-specific records are normalized into canonical observations or workspace events. A temporal builder converts the observations available by a checkpoint into a versioned learner state or snapshot. Relational persistence stores both the source lineage and the derived state. Separate prediction and analysis components then operate on that state: the empirical research pipeline evaluates Logistic Regression offline, the legacy product path retains `simple-rules-v1` records, and the operational workspace queues validated Qwen analyses. FastAPI exposes the stored state and workflow contracts to the React instructor workspace. Instructor triage and support actions are persisted separately and add history without rewriting model evidence.

The implementation contains two compatible persistence domains. The original empirical domain stores source datasets, ingestion runs, observations, weekly states, features, predictions, alerts, reviews, and provenance links. The additive workspace domain stores courses, enrolments, events, immutable snapshots, policies, analysis jobs and attempts, validated analyses, triage revisions, support cases, and audit events. This additive approach retained the empirical OULAD path while supporting richer multi-course operational scenarios.

The research paths remain outside the claim boundary of the online product. E1 evaluates Logistic Regression on prepared OULAD states. E4 audits the temporal provenance of those prepared artifacts. E2 runs a frozen 48-case controlled grounding protocol. The operational Qwen worker instead processes workspace snapshots and provides reliability evidence about validation, repair, abstention, and failure handling. These paths share concepts such as checkpointed state and evidence identity, but they do not form an online ensemble and their results are not interchangeable.

> **[Figure 4.1 placeholder — Overall system architecture]**  
> **Intended content:** A layered diagram from LMS/OULAD/controlled inputs through canonical representation, temporal state construction, relational persistence, analysis services, FastAPI, and the React workspace. Separate side branches should show E1, E2, and E4 as research evaluations, and the main operational branch should show Qwen validation followed by instructor triage and support.  
> **Purpose:** To distinguish shared architectural contracts from the separate empirical, controlled, operational, and synthetic evidence paths.
> **Caption:** Figure 4.1. Overall system architecture.

## 4.3 Canonical Data Representation

Canonicalization isolates higher-level state construction from source-specific table layouts. In the empirical domain, implemented records include course presentations, learners, enrolments, source observations, feature sets, weekly states, weekly features, feature-to-source samples, model versions, predictions, alerts, and review records. OULAD preparation maps course, registration, daily activity, resource, assessment-definition, and learner-assessment data into these structures. The Moodle adapter and controlled replay exercise ingestion behavior independently of the empirical prediction evaluation.

The workspace domain expresses the same separation at a richer operational level. A course owns a versioned payload; an enrolment binds a learner to that course; an event carries both a course day and an availability day; and a snapshot serializes the evidence available to one learner at one checkpoint. Course policy is independently versioned. This representation supports empirical, replayed, synthetic, and manual-test origins, which are retained explicitly rather than merged into one evidence class.

Canonical records serve four purposes. They permit one state builder to consume controlled source shapes; make feature construction repeatable; retain links from a derived value to its source observations; and allow replay and contract testing without claiming that unrelated datasets contain the same learners. The design is source-aware rather than universally source-independent. A new LMS adapter would still require explicit mapping, availability semantics, calendar interpretation, and leakage testing before its output could support research conclusions.

Missingness is part of the representation. Workspace evidence facts distinguish `observed`, `structural_zero`, `not_yet_applicable`, `not_supported`, `source_missing`, `ingestion_incomplete`, and `no_activity_yet`. Observed evidence requires a value; a structural zero must be numerically zero; and unavailable evidence must remain null. This prevents a missing feed, an assessment that is not yet due, and a genuine absence of activity from being treated as equivalent.

## 4.4 Temporal Learner-State Layer

The temporal layer materializes what was knowable at a declared checkpoint. In the workspace contract, a learner snapshot contains a state identifier, presentation and learner identifiers, checkpoint week, cutoff day, data origin, feature version, build time, freshness indicator, coverage metadata, course context, and typed evidence facts. The contract enforces the implemented weekly relationship `cutoff_day = checkpoint_week × 7 − 1`. Each evidence identifier must be unique within the snapshot, and an evidence fact with an availability day later than the cutoff is rejected.

State identity includes more than a learner and week. The stored snapshot has an input hash, and the database uniqueness constraint covers course, learner, week, and input hash. A `SnapshotHead` points to the current immutable revision for a learner-week while older snapshots remain stored. This permits corrected or enriched input to become the current head without deleting the state previously used by an analysis.

Exact state binding is enforced in both product domains. An analysis job references one snapshot, and the accepted analysis repeats that state identity. In the empirical API, the displayed prediction is selected for the exact displayed weekly state; an older prediction is not borrowed when the current state is unassessed. Temporal comparison uses the immediately previous eligible checkpoint and compatible model semantics. It does not skip a missing checkpoint merely to obtain a convenient comparison. An unavailable comparison is returned with an explicit reason.

Freshness and completeness are presentation and policy gates rather than substitutes for provenance. They help the interface qualify whether a current result is usable, while the underlying state, features, and source links explain what was present. A later checkpoint cannot silently alter the evidence shown for an earlier analysis.

> **[Figure 4.2 placeholder — Temporal learner-state lifecycle]**  
> **Intended content:** Source observations with course and availability days; cutoff filtering; feature and missingness construction; immutable snapshot revision; snapshot-head selection; exact analysis binding; and a later checkpoint retaining the earlier analysis.  
> **Purpose:** To show why current-state selection and historical-state identity are separate operations.
> **Caption:** Figure 4.2. Temporal learner-state lifecycle.

## 4.5 Prediction and Analysis Layer

The project contains four deliberately separate model/analysis paths plus a distinct synthetic workspace demonstration path. Table 4.1 summarizes their implementation and claim boundaries.

**Table 4.1. Research and operational analysis paths**

| Path | Model or data | Purpose | Execution context | Claim boundary |
|---|---|---|---|---|
| E1 empirical path | OULAD AAA/2013J and Logistic Regression | Evaluate checkpoint-specific predictive discrimination | Offline evaluation repository | Empirical results for the declared presentation and split only |
| E2 controlled path | Frozen 48-case protocol; `plain_llm` and `schema_only` | Evaluate structural, citation, semantic, abstention, and behavioral properties | Offline controlled experiment | Grounding behavior on the frozen scenarios, not student-risk accuracy |
| Operational Qwen path | Workspace snapshot and Qwen2.5:7b | Produce validated instructor-facing analysis | Queued worker and local Ollama runtime | Operational validation, repair, abstention, failure, and provenance behavior |
| Legacy rules path | `simple-rules-v1` over legacy weekly states | Exercise empirical product plumbing and demonstrations | Legacy API/product records | Uncalibrated operational/demo score; not a probability, E1 result, or Qwen output |
| Synthetic workspace | Generated courses, learners, evidence states, and policies | Exercise interface, workflow, missingness, and runtime scenarios | Workspace preparation and demonstration | Repeatable product behavior only; no empirical educational validity |

E1 is an offline research evaluation. Its Logistic Regression preprocessing, threshold selection, and test evaluation do not imply that the online workspace uses the fitted classifier. E2 is also offline and independent of operational history. It compares output treatments under a controlled protocol rather than estimating academic-risk performance.

The legacy rules path remains visible for historical OULAD demonstrations. Its score is uncalibrated and must not be described as a probability. The workspace worker can also execute a separately labelled baseline branch, but its records remain distinct from Qwen analyses. The product never treats all available scores as one ensemble judgment.

## 4.6 Operational LLM Pipeline

The mature operational path uses `qwen2.5:7b` with digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e` and the `risk-decision-v3` wire contract. The worker claims a queued job under a lease, retrieves the exact snapshot and requested course-policy version, verifies the expected model digest, and invokes the local Ollama adapter. Jobs can be `queued`, `running`, `validated`, `abstained`, or `failed`. Superseded snapshot jobs are retained as lifecycle history and are not reinterpreted as current inference.

Before generation, the adapter constructs an allow-listed input. Direct learner identity, final outcomes, synthetic scenario labels, expected answers, arbitrary source prose, private notes, and raw instructions are excluded. Numeric evidence is aliased, course context is restricted to known fields, and producer-controlled evidence semantics determine whether grade, completion, or activity facts are eligible. The model receives the course policy that governs the requested analysis rather than being allowed to invent thresholds.

The response is parsed against the structured contract and then independently checked. A valid assessed output contains a raw score, deterministically consistent band, grounded claims, and allowed actions. An abstained output must omit score, band, claims, and actions and provide an abstention reason. The operational raw score is not calibrated and is not described as a probability.

Accepted analysis records retain the state identity, feature version, policy version, model kind and version, model digest, prompt version, input schema, wire contract, and creation time where available in the implemented payload. An analysis plan stores a pre-inference fingerprint, including for failed attempts. The implementation also defines analysis-attempt and inference-trace structures for safe outcome and diagnostic metadata without exposing prompts or unrestricted raw replies in trace records. However, the frozen operational evidence contained no usable inference-trace data for reliable prompt-version attribution of failed jobs; those failures therefore cannot be assigned reliably to v3.2 or v3.3.

> **[Figure 4.3 placeholder — Operational LLM validation pipeline]**  
> **Intended content:** Snapshot and policy resolution; queued job; lease claim; digest verification; allow-listed prompt construction; Ollama generation; schema and semantic validation; optional correction; quality abstention or rejection; persisted analysis; and instructor display.  
> **Purpose:** To make the trust boundary around generated output explicit.
> **Caption:** Figure 4.3. Operational LLM validation pipeline.

## 4.7 Deterministic Validation, Repair, and Abstention

Generated text is untrusted until it crosses the application validation boundary. The parser rejects unknown fields, invalid types, non-finite values, inconsistent assessment/abstention modes, unsupported claim codes, unsupported actions, and score-band disagreement. Evidence validation requires every cited identifier to exist in the supplied snapshot and to correspond to the exact typed predicate for that claim. Citing a real identifier is insufficient when its value does not satisfy the rule.

Semantic and policy checks cover missingness interpretation, course-policy thresholds, evidence-source eligibility, action support, and academic corroboration where configured. Protective observations cannot be used as concerns, missing grades cannot become low grades, and unavailable activity feeds cannot be interpreted as inactivity. Inputs that are stale or insufficient can produce quality abstention before inference. Runtime unavailability, a digest mismatch, timeout, malformed output, and unrecoverable contract violations produce failed attempts rather than fabricated predictions.

The implementation permits one bounded correction generation for eligible output defects. The correction receives application-written diagnostics plus the unchanged evidence, policy, and schema; the rejected model answer does not become an instruction. Both generations are validated independently, and at most two generations occur. Safe normalization is narrower still: it can remove one exact Markdown JSON fence, normalize a known closed-enum value, convert an unambiguous decimal string, or derive the presentation band from an already validated score. It does not clip scores, reinterpret percentages, invent fields, or change evidence identifiers.

Three distinctions are essential. Schema validity means the response has the expected structure. Semantic validity means its claims and actions satisfy deterministic evidence and policy rules. Predictive accuracy concerns agreement with an empirical outcome and requires a separate evaluation. Passing the first two does not establish the third, and deterministic validation does not guarantee educational truth.

## 4.8 Persistence and Database Design

The implementation uses SQLAlchemy models with Alembic migrations. PostgreSQL is the primary relational store for the integrated runtime, while SQLite remains supported for local contract tests and selected pilot paths. The current migration lineage is additive: empirical lineage and replay tables are followed by workspace, analysis automation, inference reliability, support workflow, and triage revisions.

**Table 4.2. Core persisted domains and responsibilities**

| Domain or entity | Purpose | Key relationships | Audit or version role |
|---|---|---|---|
| Course and enrolment | Define authorized instructional scope and learner membership | Course to enrolments and events | Stable identifiers and retained source payloads |
| Source observation or workspace event | Preserve available input records | Linked to course and learner; carries temporal availability | Enables traceability and cutoff checks |
| Weekly state or snapshot | Materialize checkpoint evidence | Bound to learner, course, week, and features | Input hash, feature version, immutable revision, snapshot head |
| Policy | Store course-specific interpretation settings | Course and analysis job | Append-only version used by each analysis |
| Analysis job, plan, attempt, and trace | Coordinate and diagnose model execution | Job references exact snapshot and policy | Status, lease, fingerprint, attempt outcome, safe diagnostics |
| Prediction or validated analysis | Preserve model output and provenance | References exact state and model identity | Historical record is not rewritten by human actions |
| Triage and triage event | Store current instructor judgment and its revisions | Course and learner | Optimistic version plus append-only history |
| Support case and case event/action | Maintain longitudinal support work | Course, learner, and referenced evidence checkpoint | Status/version, follow-up, idempotent action history |
| Alert and review | Retain legacy concern and review workflow | Prediction, evidence, and reviewer | Append-only review and provenance links |
| Runtime and course control | Coordinate worker health, automation, and pause state | Course or runtime scope | Operational status separate from saved analysis |

This schema preserves two important invariants. Model records are immutable historical evidence: triage, review, notes, and support actions do not update their score, claims, evidence, or model identity. Current workflow state is versioned separately, while event tables retain prior revisions. This makes it possible to reconstruct what the system displayed and what the instructor subsequently decided.

## 4.9 Human-in-the-Loop Workflow

The human workflow begins when a validated analysis or legacy prediction becomes available. The instructor inspects the learner state, coded claims, evidence facts, missingness, and historical context. The instructor may then set independent triage fields: flagged, watchlisted, priority (`low`, `normal`, `high`, or `urgent`), and a note. Triage has its own expected version and append-only event history.

A support case is optional and remains independent of both model risk and triage. Workspace case statuses are `new`, `reviewed`, `ongoing`, `resolved`, and `dismissed`. Actions are typed as `note`, `contact`, `warning`, `support`, `resource`, or `follow_up`, with `planned`, `completed`, or `cancelled` action state. Records can retain an action day, follow-up day, evidence checkpoint, approved resource references, and links that resolve a prior event. A later checkpoint may be compared with the checkpoint before an action, but the interface describes this as observation rather than causal intervention evidence.

The three state machines therefore remain distinct:

**Risk State ≠ Instructor Triage Status ≠ Support Case Status.**

Opening a case does not change model risk. Resolving a case does not erase the earlier analysis. Viewing a learner does not automatically mark a case reviewed. At a later checkpoint, the new state and analysis can be displayed alongside the preserved earlier evidence and support history. This structure responds to the practical need for instructor follow-up without claiming that the workflow improves decisions or learner outcomes.

> **[Figure 4.4 placeholder — Instructor review and support workflow]**  
> **Intended content:** Validated analysis; evidence inspection; independent triage; optional support case; notes/actions/follow-up; later checkpoint; and retained earlier history.  
> **Purpose:** To show that model and human states evolve independently and remain auditable.
> **Caption:** Figure 4.4. Instructor review and support workflow.

## 4.10 Backend and API Design

FastAPI provides the application boundary. The current application combines browser-session routes, workspace v2 routes, empirical/legacy v1 routes, and support routes. Service and store layers encapsulate database access, state selection, comparison rules, authorization context, and mutation invariants. Pydantic contracts reject undocumented input fields and constrain enums, ranges, and missingness modes.

The workspace API supports authorized course discovery, course/checkpoint workspace retrieval, learner detail, instructor triage, course-policy updates, support-case updates, analysis queueing, batch scheduling, automation controls, resume operations, and model/runtime status. The legacy API provides authorized presentation discovery, overview, roster, learner and alert detail, alert review, and the separate support-case workflow. The chapter does not reproduce the complete route catalogue because the architectural concern is the separation of read models, workflow mutations, and analysis coordination.

Exact-state selection occurs in the backend rather than being delegated to the browser. Course and learner access is checked before data is returned. Mutations validate expected versions and idempotency data before writing. Health endpoints distinguish process liveness, database readiness, and model readiness; the latter is a metadata check and is not evidence that inference succeeded.

## 4.11 React Instructor Workspace

The current instructor interface is implemented with React, TypeScript, and Vite. Its primary navigation labels are **Overview**, **Students**, **Support cases**, **Course settings**, and **Data & model**. The application obtains the authenticated browser session, retrieves only granted courses, and provides course and checkpoint selectors. Earlier synthetic course versions can be revealed explicitly, while data origin remains visible.

The Overview page summarizes the selected checkpoint without collapsing current risk and support workflow counts. Students provides filtering, stable course-wide sorting, and a learner roster. The learner profile displays academic records, state evidence, analysis status, grounded claims, history, triage controls, and support context. Support cases exposes active and historical records, actions, follow-ups, and checkpoint-aware comparison. Course settings manages versioned policy expectations. Data & model presents analysis provenance, runtime health, controls, and model history without converting runtime status into an accuracy claim.

The interface deliberately keeps evidence and human decisions visually separate. Missing evidence is labelled rather than rendered as an adverse value. Abstained or unavailable analysis does not become a normal risk card. Historical records are marked as historical, and the UI warns that legacy scores are uncalibrated. These are engineering mechanisms for faithful presentation; visual design is not claimed as the research contribution.

> **[Figure 4.5 placeholder — React course overview screenshot]**  
> **Intended content:** Authenticated course and checkpoint selectors, current risk summary, support counters, data-origin label, and navigation.  
> **Purpose:** To show the entry point for time-specific instructor review.
> **Caption:** Figure 4.5. React course overview.

> **[Figure 4.6 placeholder — Learner evidence and analysis screenshot]**  
> **Intended content:** Learner profile, checkpoint identity, evidence facts with availability, grounded claims, analysis status, and historical comparison.  
> **Purpose:** To demonstrate inspectability and exact state binding.
> **Caption:** Figure 4.6. Learner evidence and analysis.

> **[Figure 4.7 placeholder — Support-case workflow screenshot]**  
> **Intended content:** Case status, event history, action form, follow-up date, evidence checkpoint, and concurrency message.  
> **Purpose:** To show longitudinal human follow-up separately from model risk.
> **Caption:** Figure 4.7. Support-case workflow.

> **[Figure 4.8 placeholder — Data & Model provenance screenshot]**  
> **Intended content:** Feature, policy, model, digest, prompt, contract, job, validation, and runtime metadata available to the instructor or operator.  
> **Purpose:** To show the audit boundary without exposing secrets or raw prompts.
> **Caption:** Figure 4.8. Data and model provenance.

## 4.12 Authentication and Course Authorization

The React path uses server-side browser sessions. Login verifies a configured instructor account and creates an opaque session token stored in an HttpOnly cookie. Hosted deployments require secure-cookie settings and a configured origin/path. Session records are held by the API process; restarting that process logs browser users out. Mutating browser requests are protected with CSRF checks, while existing signed service callers and the legacy Streamlit path retain their separate authenticated request mechanism.

Authentication establishes identity; course grants determine accessible data. Each instructor account has explicit presentation grants, which are re-read for requests. The API rejects accounts with no applicable grant and checks the requested course before returning or mutating records. Development identity headers are disabled in hosted mode and require explicit development configuration when used locally.

The design does not expose passwords, password hashes, signing keys, or cookie secrets to the client. It provides an implemented authentication and course-authorization boundary, not a claim of formal security certification, institutional SSO, or production onQ integration.

## 4.13 Auditability, Concurrency, and Idempotency

Human workflows are vulnerable to duplicate submissions, stale browser drafts, and simultaneous edits. The implementation addresses these conditions through exact identifiers, append-only events, optimistic versions, request keys, and request hashes.

**Table 4.3. Integrity and reliability safeguards**

| Safeguard | Implemented mechanism | Failure or risk addressed |
|---|---|---|
| Cutoff-safe state | Availability-day validation and checkpoint cutoff | Future evidence entering an earlier state |
| Exact state binding | State foreign key and displayed-state selection | Showing an older analysis as if it assessed the current state |
| Immutable analysis history | Separate analysis and workflow records | Human action rewriting model evidence |
| Deterministic validation | Schema, evidence, semantic, policy, and action checks | Publishing malformed or unsupported generated output |
| Bounded repair | One correction generation; both generations audited | Unlimited retries or silent server editing of model judgment |
| Quality abstention | Explicit no-score record for insufficient evidence | False certainty under incomplete input |
| Optimistic locking | `expected_version` checked against current triage/case revision | Lost update from concurrent instructor edits |
| Idempotency | Actor/request-key uniqueness and request hash | Duplicate actions after retry or refresh |
| Course authorization | Explicit instructor course grants | Cross-course data access |
| Model provenance | Model, digest, prompt, policy, state, feature, and contract metadata | Untraceable analysis or silent model substitution |

If a stale expected version is submitted, the server reports a conflict rather than overwriting the newer record. Repeating an identical request key is duplicate-safe; reusing it with different content is rejected through the request hash. Job leases prevent multiple workers from treating the same queue item as independently owned, and attempt records preserve failures. These safeguards support accountability and operational recovery but do not establish educational effectiveness.

## 4.14 Deployment and Runtime Architecture

The supported runtime separates frontend, API, database, worker, and local model services. FastAPI can serve the built React assets and API from one process, while the analysis worker runs independently and communicates through persisted jobs. PostgreSQL stores normalized application and audit state. Ollama serves the approved local Qwen model. Environment configuration supplies database, authentication, browser-origin, API-signing, and model identity settings without embedding secrets in source.

The repository also contains a container-oriented VM profile with PostgreSQL, API, legacy Streamlit dashboard, and reverse proxy, plus Lobot scripts for bootstrap, backup, restore, status, model checks, worker operation, and React rollout. The verified React Lobot rollout used a separate React worktree/process on port 8502 while the earlier API/worker and Streamlit fallback remained available. Both interfaces shared the authorized database and model configuration. This was a controlled project deployment arrangement rather than an institutional production architecture.

SQLite remains useful for local tests and selected pilot execution, whereas PostgreSQL supports the integrated relational schemas and migrations. Scheduled analysis and course-scoped pause/resume controls are implemented; the system does not claim real-time streaming. No production LTI/onQ integration, institutional-scale availability guarantee, or automatic student-contact channel is claimed.

> **[Figure 4.9 placeholder — Deployment/runtime topology]**  
> **Intended content:** Browser; React/FastAPI process; PostgreSQL; analysis worker; local Ollama/Qwen service; configuration/secrets boundary; logs; and the separate legacy Streamlit fallback. A note should identify the Lobot research/demo topology as one deployment instance.  
> **Purpose:** To distinguish the supported component architecture from a specific hosted pilot arrangement.
> **Caption:** Figure 4.9. Deployment and runtime topology.

## 4.15 Legacy Streamlit Interface

Streamlit was the primary interface during earlier implementation phases and remains in the repository as a legacy operational fallback and historical workflow reference. It can still use the protected API and expose earlier support functionality. It is not the final primary frontend, and current interface descriptions should refer to the React workspace.

Retaining Streamlit reduced cutover risk during the React migration and provided a fallback while the newer interface was validated. It also preserves traceability to earlier demonstrations. The two interfaces must not be interpreted as separate research treatments, and Streamlit's continued presence does not change the current React-first architecture.

## 4.16 Design Decisions and Trade-offs

The first major decision was to build a checkpointed rather than continuously synchronized twin. OULAD supplies course-relative daily aggregates rather than a live event stream, and the research questions concern what was knowable at declared early checkpoints. Checkpointing makes the cutoff explicit and reproducible, at the cost of not representing every intervening change in real time.

Second, the system binds analyses to exact states rather than selecting the latest state and latest analysis independently. This can result in a visible “not assessed” condition even when an older result exists, but it prevents evidence from one checkpoint being presented with a judgment from another. Snapshot-head semantics allow corrected current revisions without deleting the earlier input.

Third, model state, triage state, and support state are separate. A simpler schema could store one combined learner status, but that would erase whether a label came from a model, an instructor's current judgment, or a longitudinal support process. Independent versioning preserves responsibility and history.

Fourth, deterministic validation surrounds LLM generation. Flexible text generation alone is not a sufficient reliability boundary for evidence-linked academic support. The application therefore restricts input, requires structured output, checks evidence and policy, permits only bounded correction, and withholds unsupported output. This adds implementation complexity and does not guarantee truth, but it makes important failure modes observable.

Fifth, the operational LLM runs through a local Qwen/Ollama path. Local operation supports control over model identity, digest verification, data routing, and reproducibility. It also creates hardware, latency, model-management, and deployment constraints. The design does not claim that local inference is universally preferable or that Qwen has been empirically validated as the E1 predictor.

Sixth, React, TypeScript, Vite, and FastAPI form the current interface architecture. Typed client contracts and a component-based frontend support the current multi-view instructor workflow, while FastAPI centralizes authorization and domain invariants. This is an engineering choice rather than experimental evidence.

Seventh, relational persistence and versioned records were preferred over mutable document-only state. Foreign keys, uniqueness constraints, migrations, and transactions support exact binding and audit history. JSON payloads remain within the relational model for versioned contracts and source-specific detail. The trade-off is a more complex schema and migration discipline.

Eighth, synthetic workspace courses complement rather than replace empirical OULAD research. Synthetic records permit controlled missingness, policy, failure, multi-course, and support scenarios that the historical OULAD presentation does not contain. Their value is repeatable system testing; they do not establish predictive validity or generalization.

Ninth, no completed calibration is claimed. Operational Qwen and `simple-rules-v1` scores are therefore labelled as raw or uncalibrated values rather than probabilities. Calibration remains a separate empirical task.

Finally, the term “course digital twin” is used conservatively. The implemented twin is course-level, checkpointed, provenance-aware, and historized. It does not claim continuous synchronization, causal simulation, psychological representation, or comprehensive institutional coverage. Together, these decisions preserve the boundaries established in Chapters 1 and 3: empirical prediction, temporal integrity, controlled LLM grounding, operational reliability, and human workflow remain connected through software but distinct in their evidence and claims.
