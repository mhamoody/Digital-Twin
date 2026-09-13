# Rich demonstration data and feature dictionary

## Scope and origin

`synthetic-education-v1` creates fictional courses and learner histories with
`data_origin=synthetic`. It never edits, fills gaps in, or impersonates empirical
OULAD records. Its purpose is to exercise academic reasoning, interface behaviour,
temporal filtering, case follow-up, and missing-data handling. These scenarios do
not establish real-world predictive accuracy, calibration, or intervention effects.

The default generation is three courses, 120 enrolments per course, 16 weeks,
daily events, and 5,760 weekly learner snapshots. The courses have weekly,
fortnightly-project, and blended teaching patterns with different inactivity
policies. Event counts arise from seeded, correlated behaviour rather than a fixed
number of records per learner-day. The private scenario oracle is separate from
the model snapshots and is not imported into the dashboard database.

An applicable, completely observed history still contains legitimate nulls. No
published grade yet is different from a zero grade; unsupported attendance is
different from an absence; no forum post is different from a missing forum feed.
The source-neutral core is extensible, not a claim that every LMS exposes every
field. New adapters must declare which streams they support and their coverage.

## Raw record dictionary

| Entity | Grain and required keys | Context and values |
|---|---|---|
| Course | One course offering; `presentation_id` | Title/code, start date/timezone, weeks, pass mark, assessment definitions, approved local resources, calendar, versioned inactivity policy |
| Enrolment | `(presentation_id, learner_id)` | Fictional display alias, registration/unregistration day, status, synthetic origin |
| Event | Unique `event_id`, course, learner, type, `course_day`, `available_day` | Typed payload, exact simulated timestamp, source record, precision, origin |
| Assessment definition | Course plus `assessment_id` | Title/type/topic, published schedule day, due day, maximum score, weight, required/optional status |
| Resource definition | Course plus `resource_id` | Title/type/topics, week, availability, approved flag, local URI and fictional practice content |
| Snapshot | Course, learner, checkpoint and input-derived identity | Version, cutoff, per-stream coverage, policy/course context, typed evidence facts |
| Private oracle | Course and learner | Hidden scenario trajectory; testing only, never sent to the LLM |

Event payloads are distinct:

| Event type | Payload |
|---|---|
| `enrolment` | Enrolment status |
| `activity` | Resource, topic, interaction count, simulated session minutes, activity kind |
| `resource_completed` | Resource and topic identifiers |
| `assessment_submission` | Assessment, attempt, topics |
| `assessment_grade` | Assessment/attempt, score, maximum, publication time, topics, feedback |
| `assessment_extension` | Assessment, approved extended deadline |
| `attendance` | Scheduled session and present/absent flag; blended course only |
| `forum_post` | Fictional text, topic, thread; interpret as untrusted learner content |
| `intervention` | Recorded support action, resources, note, follow-up due date, case status |
| `follow_up` | Recorded follow-up action, note and case status |

## Cutoff and missingness rules

1. Scope by both learner and course before aggregation. An enrolment in another
   course cannot supply evidence for this course.
2. An event contributes only when both `course_day <= cutoff_day` and
   `available_day <= cutoff_day`. Grades are unavailable until publication;
   submissions and delayed grades are separate records.
3. Future deadlines may appear when the schedule itself was known by the cutoff.
   They are contextual future obligations, not future learner behaviour. Approved
   extensions replace the applicable deadline only after approval is recorded.
4. Aggregate grades over published results and their observed weights. Unmarked
   or missing grades do not contribute zero to this average.
5. Structural zero is justified only by complete supported-stream coverage.
   The complete generator supplies that guarantee. A missing/partial adapter must
   map affected values to null with an explicit reason before model invocation.
6. `observed`, `structural_zero`, `not_yet_applicable`, `not_supported`,
   `source_missing`, `ingestion_incomplete`, and `no_activity_yet` remain distinct.
   Freshness is a separate flag rather than a numeric grade or behaviour.
7. Teaching-day inactivity excludes configured weekdays and break ranges.
   Instructor policy and policy version accompany each assessment; a policy
   change must not be presented as a learner's change in behaviour.

## Exact feature dictionary: `rich-features-v2`

Each feature is an `EvidenceFact`: value, status, unit, window, evidence ID,
source IDs, and latest availability day. A null value retains a meaningful status.

| Feature | Unit / calculation | Interpretation and applicability |
|---|---|---|
| `clicks_last_7` | Count, last 7 calendar days | Simulated interaction volume, not learning quality |
| `active_days_last_7` | Distinct active days / 7 | Frequency rather than clicks |
| `active_days_last_14` | Distinct active days / 14 | Longer activity context |
| `activity_change_last_7` | Current 7-day clicks minus preceding 7-day clicks | Absolute interaction-count change, not Risk score change |
| `study_minutes_last_7` | Generated session minutes | Synthetic measurement only; do not infer OULAD time-on-task |
| `days_since_last_activity` | Calendar days since latest available activity | Null with `no_activity_yet` if no observation exists |
| `teaching_days_since_last_activity` | Policy teaching days after latest activity | Excludes course breaks and nonteaching weekdays |
| `resources_completed` | Distinct expected resources with completion records | Not a count of repeated views |
| `resources_expected` | Released resources scheduled through checkpoint | Excludes scheduled break weeks |
| `completion_percent` | Completed / expected resources × 100 | Course-resource progress, not academic grade |
| `assessments_due` | Required assessments with effective due day at/before cutoff | Approved extensions respected; optional practice excluded |
| `assessments_submitted` | Due assessments with available submission | Not the number of grades |
| `assessments_missed` | Due required assessments without available submission | Valid only with complete submission coverage |
| `assessments_late` | Due submissions after effective deadline | Uses extension-aware deadline |
| `submission_rate_percent` | Submitted due assessments / due × 100 | Null before any required assessment is due |
| `grades_available` | Count of published grade records | Includes optional practice grades |
| `weighted_grade_percent` | Published summative grades weighted by their observed weights | Not a projected final grade; null until a weighted grade is available |
| `latest_grade_percent` | Latest published grade / maximum × 100 | Publication order, not future grade order |
| `grade_change_points` | Mean latest two grades minus mean preceding two | Percentage-point change; needs four published grades; assessment mix may differ |
| `low_grade_count` | Published grades below policy low-grade threshold | Includes optional practice; pedagogical signal, not final outcome |
| `grade_weight_observed_percent` | Course weight represented by published summative grades | Separates an early sparse grade average from a mature one |
| `pending_grade_count` | Submitted assessments without published grades | Not a missed submission or zero mark |
| `quiz_average_percent` | Mean published quiz/practice-quiz percentages | Null before any quiz grade is available |
| `upcoming_assessments_7d` | Required unsubmitted tasks due in next 7 days | Known schedule, extension-aware |
| `upcoming_weight_7d` | Sum of weights of those upcoming tasks | Context for course workload |
| `days_to_next_deadline` | Days until next known required unsubmitted task | Null when no such future task exists |
| `extensions_active` | Recorded approved extensions with future effective deadlines | Avoids treating approved delay as missed work |
| `attendance_sessions` | Available scheduled attendance records | Null when the course does not track attendance |
| `attendance_rate_percent` | Present / recorded scheduled sessions × 100 | Not evidence of attendance outside tracked sessions |
| `forum_posts_last_14` | Post count in last 14 days | No posts may be an observed zero |
| `latest_forum_excerpt` | Up to 800 characters from latest recent post | Fictional untrusted text, not a hidden scenario label |
| `intervention_count` | Recorded support and follow-up events | Historical actions, not model suggestions |
| `last_intervention_day` | Latest available action day | Null before a recorded intervention |

Course context additionally supplies the calendar, pass mark, policy, up to nine
approved resources relevant to current or observed low-grade topics, upcoming
assessment metadata, and the three most recent recorded support events. Grade
changes across unlike assessments need instructor interpretation; the metric does
not establish a precise change in concept mastery.

## Scenario and robustness suite

The twelve hidden trajectories cover steady success, active learners with weak
grades, quiet learners with strong grades, declining grades, missing major work,
approved extensions, delayed feedback, recovery after support, persistent
difficulty, approaching deadline pressure, mixed academic evidence, and genuine
activity interruption. They vary jointly with random noise and course cadence.
Recovery after support is a simulated sequence, not a causal effectiveness claim.

`degrade_snapshot` creates a new immutable paired fixture:

| Fault | Behaviour |
|---|---|
| `missing_grades` | Grade-derived fields become null / source missing; grade-derived resource selection is removed |
| `partial_activity` | Activity-derived fields become null / ingestion incomplete; zero is not manufactured |
| `stale_activity` | Same affected evidence becomes unavailable, and the snapshot is explicitly stale |

Fault identifiers and the private oracle belong to the test harness. They do not
become predictive features. Evaluation on these fixtures measures behaviour under
controlled scenarios, not calibration or real-world academic-risk accuracy.

## Reproduction

Export independently of a database:

```bash
python scripts/generate_rich_demo.py --export-dir artifacts/rich_demo_v1 \
  --export-fault-fixtures --include-private-oracle
```

Load into the configured workspace database:

```bash
python scripts/generate_rich_demo.py
```

The loader requires `DIGITAL_TWIN_DATABASE_URL` (or explicit `--database-url`).
SQLite schema creation is additive; PostgreSQL requires migrations first. Course,
event, and snapshot identities are immutable. The seed is deterministic, but a
different seed must use a fresh demo database or a new source version because the
same source IDs cannot silently be replaced. Exports refuse to overwrite existing
files. A smaller smoke run is `--learners-per-course 2 --weeks 4`; it is not the
representative demonstration dataset.

`tests/test_workspace_data.py` checks reproducibility, scenario separation,
multi-course isolation, future-event and delayed-grade exclusion, approved
extensions, different activity/grade trajectories, missingness distinctions,
source provenance, score ranges, and teaching-day policy semantics.
