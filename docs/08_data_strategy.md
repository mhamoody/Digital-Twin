# 08 — Data strategy, canonical schema, and pipeline

## Decision record

**Decision date:** 2026-08-02

**Status:** accepted for the MVP; implementation and leakage tests remain pending

The data problem is resolved as a **separation decision**, not a dataset-merging
exercise:

1. **OULAD is the only empirical training and evaluation source for the MVP.** It
   has linked learner, presentation, daily activity, assessment, registration,
   and final-outcome records with a reproducible CC BY 4.0 download.
2. **The local Moodle sandbox is the operational source.** It proves read-only
   extraction, event-time ingestion, replay, persistence, freshness, alert
   lifecycle, and the dashboard. Its simulated learners do not validate the
   OULAD model.
3. **No public source is row-joined to OULAD.** None shares OULAD learner or
   course identifiers, so a learner-level join would be fabricated. Cross-source
   contribution occurs through a common schema, common feature definitions, and
   separately reported external checks.
4. **Open edX, HarvardX/MITx, MORF, and public Moodle releases do not enter the
   P0 training table.** Their specific roles and re-entry gates are recorded
   below.
5. **Text is absent from the structured MVP.** Forum event counts may be used,
   but forum content is not inferred or synthesized. Any authentic text study is
   an independent experiment with its own dataset card and ethics boundary.

This choice preserves one valid scientific population while still allowing the
software to support finer events from other LMS platforms.

## Source investigation

### Decision criteria

Scores use `0 = absent/unusable`, `1 = partial or costly`, and `2 = strong` for:

- `A`: timely access;
- `P`: licence/publication permission;
- `J`: learner-course linkage;
- `T`: temporal resolution;
- `S`: assessment linkage;
- `O`: outcome label;
- `R`: LMS realism;
- `X`: authentic usable text;
- `D`: documentation/quality; and
- `E`: semester-scale effort.

A high total does not override a hard failure in timely access, learner linkage,
or outcome availability.

| Candidate | A/P/J/T/S/O/R/X/D/E | Total | Verified contribution | MVP verdict |
|---|---:|---:|---|---|
| OULAD | 2/2/2/1/2/2/1/0/2/2 | 16 | Linked daily activity, assessments, registrations, and outcomes | **Select for empirical modelling** |
| Open edX tracking logs/xAPI | 0/0/2/2/2/2/2/1/2/0 | 13 | Modern event vocabulary and transport contract, but not a public cohort | Schema reference only |
| HarvardX/MITx person-course release | 1/1/2/0/0/2/1/0/2/2 | 11 | Large cross-platform aggregate table | Optional descriptive/aggregate robustness check |
| MORF | 0/1/2/2/2/2/2/1/1/0 | 13 | Restricted Coursera replication environment | Future work after DUA and live-access proof |
| EduTrackMoodle 2025 | 0/2/2/2/2/2/2/0/1/1 | 14 | Claims 241,321 events and 1,613 grade rows | Hold: metadata exists, public file listing was empty on review date |
| Moodle/SIS/eDify 2021 | 2/2/0/2/1/2/2/0/1/1 | 13 | Real Moodle logs and learner summaries | Reject for prediction: released raw event IDs could not be joined reproducibly to outcome IDs |
| Moodle FSLSM release 2026 | 2/2/2/2/2/1/2/0/1/1 | 15 | Hash-linked timestamped logs, grades, attempts, forums, and enrolments | P2 adapter test after calendar/outcome audit; not pooled with OULAD |
| “Streaming OULAD” derivative | 1/1/2/2/0/1/0/0/1/1 | 9 | Daily representation derived from OULAD for 300 profiles | Do not treat as new evidence or extra learners |

### What each named alternative actually contributes

#### Open edX event streams

Open edX documents tracking-log events with common fields and event-specific
payloads. Current Open edX analytics architecture transforms selected tracking
events into versioned xAPI statements. This is useful for designing
`event_type`, `event_at`, actor, course, resource, result, and raw-payload
lineage fields. It does **not** provide an openly downloadable, outcome-linked
learner cohort. Rich MITx data require a research request, privacy compliance,
and a data-use agreement, with transfer through BigQuery. Therefore Open edX
improves the canonical contract but adds no MVP training rows.

#### HarvardX/MITx public release

The public release represents one registration per person-course. Its 20 fields
include course and pseudonymous learner identifiers, registration/view/explore/
certificate flags, final grade, coarse start and last-event dates, and lifetime
counts such as events, active days, video plays, chapters, and forum posts. It
contains 641,138 person-course rows after de-identification, but it has no event
sequence or assessment-item history. The current Harvard Dataverse record is
public and non-restricted, while automated download still requires a guestbook
response.

It may test whether course-level aggregate relationships are directionally
similar on another platform. It cannot reconstruct weeks 3, 5, 8, and 10 and
must never be appended to the OULAD weekly-state table.

#### MORF

MORF executes submitted containers against privacy-restricted Coursera exports.
Its platform page requires a collaborative project and institutional data-use
agreement; its documentation currently describes Coursera Spark/Phoenix input,
not Moodle or Open edX. MORF contributes a reproducible remote-execution pattern
and a possible later replication population. It is not a downloadable dataset,
not a row-level supplement to OULAD, and not a dependency for the semester MVP.

#### Newer public Moodle datasets

The investigation found useful candidates but no source that should replace
OULAD now:

- **EduTrackMoodle (2025)** documents timestamped Moodle events linked to 1,613
  grade records under CC BY 4.0, but its public page returned no downloadable
  files through the repository API on 2026-08-02. Reconsider only after both
  workbooks download non-interactively and the learner key, course calendar,
  assessment dates, and outcome definition pass a data-card audit.
- **Moodle/SIS/eDify (2021)** is downloadable and CC BY 4.0. Direct inspection
  found numeric user IDs in raw Moodle descriptions and `Student N` identifiers
  in the outcome table without a released mapping. It is useful as a log-format
  fixture, but not as a reproducible event-to-outcome benchmark.
- **Anonymized Moodle interaction data (2026)** publishes hash-linked resource
  logs, grades, quiz attempts, forum metrics, and enrolments. It is the strongest
  reserve adapter candidate. Before use, verify course start/end dates, whether
  `avg_grade` is a legitimate final outcome, grade-availability timestamps,
  population size, duplication, and whether the published zero-imputation has
  erased the difference between absence and missingness. Use raw tables, not the
  authors' already-imputed feature table.

These sources can validate adapters and feature portability. They cannot fill
missing columns for the same OULAD learners.

## Direct OULAD profile

The official UCI archive was downloaded and scanned on 2026-08-02. Missing-token
counts below treat `?` as missing; a plain CSV null scan would incorrectly report
no missing values.

| Source table | Rows | Columns | Natural grain | Missing tokens |
|---|---:|---:|---|---|
| `courses` | 22 | 3 | module presentation | none |
| `assessments` | 206 | 6 | assessment item | `date`: 11, all handled as unknown exam dates |
| `vle` | 6,364 | 6 | resource in a presentation | `week_from`: 5,243; `week_to`: 5,243 |
| `studentInfo` | 32,593 | 12 | learner enrolment | `imd_band`: 1,111 |
| `studentRegistration` | 32,593 | 5 | learner enrolment | `date_registration`: 45; `date_unregistration`: 22,521 structural non-withdrawals |
| `studentAssessment` | 173,912 | 5 | learner assessment result | `score`: 173 |
| `studentVle` | 10,655,280 | 6 | learner-resource-day aggregate | none |

There are 28,785 distinct learner IDs and 32,593 enrolments. The `studentInfo`
and `studentRegistration` composite keys match exactly. Direct checks found no
orphan assessment results and no activity rows without an enrolment. Activity
days range from `-25` to `269`; 688,988 activity rows occur before course day
zero and must remain explicitly labelled as pre-start activity.

### Checkpoint population

End of checkpoint week `w` is relative course day `7w - 1`. A learner is eligible
when registered by that cutoff and not already unregistered. Missing registration
day does not erase a known enrolment; it produces a missingness flag. The label is
`non_success = final_result in {Fail, Withdrawn}`. An already-known withdrawal is
not scored, while a later withdrawal remains a positive outcome.

| Week | Cutoff day | Eligible states | Non-success | Any activity by cutoff | Learners with a due non-exam assessment |
|---:|---:|---:|---:|---:|---:|
| 3 | 20 | 27,887 | 12,513 (44.9%) | 26,700 (95.7%) | 15,806 |
| 5 | 34 | 27,235 | 11,855 (43.5%) | 26,452 (97.1%) | 24,806 |
| 8 | 55 | 26,523 | 11,141 (42.0%) | 25,923 (97.7%) | 24,116 |
| 10 | 69 | 26,075 | 10,692 (41.0%) | 25,552 (98.0%) | 26,075 |

The expected first state build therefore contains **107,720 eligible weekly
states**, not the naive `32,593 × 4 = 130,372` Cartesian product.

## Information OULAD does not contain

Absent information must remain absent; it must not be reconstructed through
plausible-looking values.

| Missing information | Consequence | Policy |
|---|---|---|
| Event timestamp below day resolution | No time-of-day, ordering within a day, or reliable session boundary | Store `course_day`, `time_precision = day`; do not generate timestamps or sessions |
| Login/logout and session duration | Time-on-task cannot be measured | Omit duration features; clicks are interactions, not minutes |
| Calendar start dates | Cross-source calendar joins are impossible | Use relative course day for OULAD; keep `event_at` null |
| Score publication/feedback time | TMA scores may not have been visible at submission or due date | Keep observed submission and assumed score availability separate; run sensitivity analysis |
| Exact exam date/result | Early exam features are unavailable | Exclude exams from checkpoint features and use final outcome only as a label |
| Resource title/content/topic | No knowledge-component or semantic-content claims | Collapse only documented `activity_type` values into portable groups |
| Forum post text and thread structure | No semantic confusion/urgency labels | Use forum interaction counts only; text experiment remains separate |
| Explicit absence rows | No assessment row can mean no submission, while no activity row can mean zero activity | Interpret only after checking enrolment, due date, and ingestion completeness |
| Intervention/contact history | Model cannot estimate intervention effects | Do not make causal or intervention-effectiveness claims |
| Protected-attribute completeness/precision | Demographic values are generalized and IMD is partly missing | Exclude from the primary predictor; retain restricted fairness slices with `Unknown` |

## Missingness and temporal-availability rules

1. **Cut off before joining or aggregating.** Filter every observation by its
   permitted availability time first. Joining a full-semester aggregate and then
   filtering is prohibited.
2. **Separate zero, not applicable, unknown, and stale.** Every feature has a
   `missing_reason` from `observed`, `structural_zero`, `not_yet_applicable`,
   `source_missing`, `ingestion_incomplete`, or `not_supported`.
3. **Activity absence is zero only when coverage is complete.** A known active
   enrolment with a successfully loaded OULAD activity file and no rows in a
   window has zero events. In live Moodle, a failed or stale sync yields null,
   never zero.
4. **Assessment absence is contextual.** Before the due date it is
   `not_yet_applicable`; after the due date, absence of a result row is a missed
   submission because OULAD explicitly omits results for non-submissions.
5. **A missing score is not zero.** The 173 `?` scores remain unknown. Banked
   results are excluded from current-presentation progress and receive a flag.
6. **Registration day.** The 45 missing values remain null with
   `registration_day_missing = true`; the enrolment itself is still valid.
7. **Resource schedule.** Missing `week_from/week_to` never blocks observed
   activity counts. Schedule-alignment features are excluded from feature set
   version 1.
8. **Demographics.** Missing IMD becomes an explicit `Unknown` fairness category,
   not a median band. Demographics are excluded from the primary model and alert
   evidence.
9. **Score availability.** Feature set v1 has a strict track with activity and
   submission status but no TMA score. A secondary proxy track treats CMA score
   as available on submission and TMA score as available seven days after its
   due date; repeat with 0- and 14-day TMA lags. Any gain is reported as
   availability-assumption-dependent.
10. **Outcomes are isolated.** `final_result` and future unregistration dates live
    in a restricted label table and are joined only after the feature table and
    split assignments are frozen.

## Feature contract for version 1

Features describe observable behaviour. They do not measure motivation,
understanding, intent, or causality.

### Model inputs

| Group | Features | Availability rule |
|---|---|---|
| Registration/context | registration lead days, previous attempts, studied credits, checkpoint week | Known at registration; missing flags retained |
| Activity volume | clicks in 7/14/28 days and cumulatively; event rows cumulatively | Only activity days at or before cutoff |
| Activity frequency | active days in 7/14/28 days and cumulatively; active-week ratio | A learner-resource-day may contribute many clicks but one active date |
| Recency/regularity | days since last activity, inactive streak, weekly click trend, weekly active-day trend | Undefined recency gets `no_activity_yet`, not an arbitrary large number |
| Resource mix | content, assessment, forum, collaboration, and other counts; resource-type diversity | Map source-specific types through a versioned taxonomy |
| Submission progress | non-exam assessments due, submitted, missed, late, submission rate | Due and submission times must be at or before cutoff |
| Grade proxy, secondary track | available-score count, weighted score to date, latest available score, below-40 count | Uses the declared CMA/TMA availability policy; exams and banked scores excluded |
| Data quality | activity coverage, assessment coverage, missingness flags | Quality fields gate predictions; most are not predictive inputs |

Raw OULAD activity types are not emitted as 20 fragile one-hot columns. Version 1
maps them to a small portable taxonomy and retains the original type in the
observation table for later revisions.

### Fields prohibited from model input

- `final_result`, course-end grade, certificate, or any outcome derivative;
- future or current `date_unregistration` as a predictor;
- full-semester clicks, last-event date, assessment totals, or any value computed
  after the cutoff;
- a learner ID, source record ID, ingestion time, or scenario ID;
- IP address, device fingerprint, raw forum content, or direct identifier;
- protected demographic attributes in the primary model; and
- synthetic/replayed origin as if it were empirical evidence.

## PostgreSQL shape

The database uses four logical schemas. Raw archives remain immutable files with
checksums; PostgreSQL stores imports, canonical observations, derived states, and
audit history.

| Schema/table | Grain and key columns | Purpose |
|---|---|---|
| `registry.source_dataset` | one source/version; `source_id`, licence, URI, checksum, access date | Dataset card and reproducibility |
| `registry.ingestion_run` | one adapter run; `run_id`, source, adapter/schema version, watermark, counts, status | Idempotency, freshness, and quarantine audit |
| `core.course_presentation` | one source course run; source keys, relative/calendar start/end, duration | Common course identity without false cross-source equivalence |
| `core.learner` | one pseudonymous learner within a source | Source-local identity; no cross-dataset identity resolution |
| `core.enrolment` | learner × presentation | Registration/status known at a checkpoint; no final label column |
| `core.course_outcome` | one enrolment outcome; restricted | Final label, availability time, and label version isolated from features |
| `core.learning_resource` | resource × presentation | Original resource type plus portable taxonomy |
| `core.activity_observation` | learner × resource/event × time grain | `event_at`, `course_day`, `event_count`, precision, origin, source record, ingestion run |
| `core.assessment` | assessment × presentation | Type, due time/day, weight, maximum score, availability policy |
| `core.assessment_observation` | learner × assessment attempt/result | submission time, score, maximum, score availability, banked/status flags |
| `core.text_observation` | one restricted post/document | Optional pointer and consent/provenance; content excluded from MVP ingestion |
| `quality.data_issue` | one rejected or suspicious record | Rule, severity, source record, resolution, quarantine state |
| `analytics.feature_set` | one immutable feature contract | Definition, taxonomy, cutoff and score-availability policy |
| `analytics.weekly_state` | enrolment × checkpoint × feature-set version | Cutoff, freshness, build run, completeness, origin summary |
| `analytics.weekly_feature` | state × feature name | Typed value, missing reason, and compact provenance |
| `analytics.split_assignment` | enrolment/presentation × experiment version | Frozen train/validation/test membership |
| `analytics.model_version` | one LLM or baseline model/calibrator | Provider/model, prompt/few-shot or training config, data, feature, split, seed, metrics, approval scope |
| `analytics.prediction` | state × model version | Raw/calibrated probability, structured output, calibration version, generation time, quality-gate result |
| `analytics.evidence` | prediction × evidence item | Supplied feature value, LLM citation/ablation or baseline attribution, display label, source reference |
| `analytics.alert` | one policy decision on a prediction | Threshold/policy version, freshness, priority, lifecycle status |
| `analytics.alert_review` | one append-only status transition | Reviewer pseudonym/role, prior/new state, note, timestamp |

Expected OULAD core cardinalities are 22 presentations, 28,785 learners, 32,593
enrolments, 6,364 resources, 10,655,280 activity observations, 206 assessments,
and 173,912 assessment observations. Do not explode `sum_click` into synthetic
individual click events; preserve `event_count` and `time_precision = day`.

## Source-to-canonical mapping

| Canonical field | OULAD | Local Moodle |
|---|---|---|
| learner | `id_student` scoped to source | salted hash of Moodle `userid`; mapping kept locally and restricted |
| presentation | `code_module + code_presentation` | `courseid` plus the specific course run |
| event time | relative `date`, day precision | standard-log `timecreated`, timestamp precision |
| event type | VLE `activity_type`; click aggregate | event `component/action/target` |
| resource | `id_site` | `objectid/contextinstanceid` where applicable |
| event count | `sum_click` | `1` per accepted event or a documented export aggregate |
| registration | `date_registration/date_unregistration` | enrolment start/end/status |
| assessment | `id_assessment`, type, due day, weight | grade item/activity, due timestamp, weight/max score |
| submission/result | `date_submitted`, score, banked flag | submission attempt plus grade and grade-modified time |
| outcome | `final_result`, restricted | null for replay unless a scenario supplies a clearly synthetic label |

Moodle IP addresses and direct names are dropped before canonical storage. Forum
events may produce counts; post bodies require a separate approved text path.

## Processing pipeline

```text
source manifest + checksum
        |
        v
immutable raw archive / read-only Moodle extraction
        |
        v
source staging -> schema/type/key checks -> quarantine report
        |
        v
canonical presentations, enrolments, resources, activities, assessments
        |
        v
availability-time normalization + provenance audit
        |
        v
cutoff-first observations for days 20, 34, 55, and 69
        |
        v
weekly states + typed missing reasons
        |
        +------> restricted outcome join after states are frozen
        |                              |
        v                              v
versioned state serialization + frozen splits -> strong LLM + baselines + calibration
        |
        v
validated prediction -> grounded evidence -> alert policy -> instructor review
```

### Pipeline stages and required outputs

1. **Acquire:** download by documented command where possible; record licence,
   access date, byte size, checksum, and expected file list. A manual guestbook or
   DUA route cannot be a required clean-checkout dependency.
2. **Stage:** load source fields without semantic imputation. Normalize `?`, empty
   strings, and source-specific nulls while preserving the raw token and row ID.
3. **Validate:** check composite-key uniqueness, foreign keys, date ranges,
   allowed categories, score bounds, weights, duplicate source records, and
   counts against the dataset card. Reject or quarantine; do not silently drop.
4. **Canonicalize:** create source-local pseudonymous identities and typed
   observations. Record `data_origin`, adapter/schema version, source record,
   event time, ingestion time, and precision.
5. **Normalize availability:** assign the earliest defensible `available_at` or
   relative availability day. Assumptions are feature-set configuration, not
   hidden preprocessing code.
6. **Build states:** select eligible enrolments, filter observations at the cutoff,
   aggregate features, attach missing reasons, and hash the sorted feature input.
7. **Audit leakage:** inject post-cutoff activity, grades, withdrawals, and course
   outcomes; earlier state hashes must not change. Also audit preprocessing and
   calibration fit boundaries.
8. **Freeze splits:** use all `2014J` presentations as the untouched temporal test
   set. Use earlier presentations for grouped model selection and out-of-fold
   calibration; no presentation or learner trajectory may cross a split.
9. **Evaluate:** use the selected strong LLM as the primary model and compare it
   with majority/prevalence, activity-only, submission/grade-only, regularized
   logistic, and at most two tree-based baselines. Freeze the LLM model version,
   prompt, state serialization, and any few-shot examples before the untouched
   test run. Calibrate only on earlier-presentation validation/OOF outputs.
   Report each checkpoint separately with PR-AUC, ROC-AUC, macro-F1, at-risk
   precision/recall, Brier score, calibration, uncertainty, schema/grounding
   failures, latency, and cost.
10. **Operationalize:** run the local Moodle adapter into the same canonical
    schema and compute the supported feature subset. A primary-LLM or baseline
    prediction on replayed Moodle data is a demo output, not an
    external-validity result.

## Re-entry gates for a supplemental dataset

A candidate can enter a separately reported external evaluation only when all of
the following are proven with downloaded data, not metadata claims:

- stable pseudonymous learner-to-course linkage across event, assessment, and
  outcome tables;
- event or aggregate times that support the declared checkpoint cutoffs;
- course calendar and assessment availability rules;
- an outcome known only after the prediction cutoff;
- licence and ethics permission for the intended analysis and publication;
- a reproducible acquisition route, checksum, schema profile, and missingness
  report; and
- enough independent course presentations for a non-random evaluation split.

If the source lacks one of these, it may still test ingestion or schema
portability, but it does not add empirical predictive evidence.

## Primary sources

- [OULAD dataset and CC BY 4.0 licence — UCI](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset)
- [OULAD data descriptor and table semantics — Scientific Data](https://pmc.ncbi.nlm.nih.gov/articles/PMC5704676/)
- [Open edX tracking-log event reference](https://docs.openedx.org/en/latest/developers/references/internal_data_formats/index.html)
- [Open edX decision to use xAPI for analytics](https://docs.openedx.org/projects/openedx-aspects/en/open-release-quince.master/decisions/0002_xapi.html)
- [MITx research-data request and DUA process](https://ir.mit.edu/services/mitx-data-requests/)
- [HarvardX/MITx person-course release announcement — MIT](https://news.mit.edu/2014/mit-and-harvard-release-de-identified-learning-data-open-online-courses)
- [HarvardX/MITx person-course dataset DOI](https://doi.org/10.7910/DVN/26147)
- [MORF platform access requirements](https://educational-technology-collective.github.io/morf/platform/)
- [MORF input and execution documentation](https://educational-technology-collective.github.io/morf/documentation/)
- [EduTrackMoodle dataset record](https://data.mendeley.com/datasets/j8fnp6xns7/1)
- [Moodle/SIS/eDify public release](https://zenodo.org/records/5591907)
- [Anonymized Moodle interaction release](https://zenodo.org/records/18624789)
- [Moodle Events, Logging, and External APIs](https://moodledev.io/docs/5.1/apis)
- [Moodle external-services framework](https://moodledev.io/docs/5.0/apis/subsystems/external)
