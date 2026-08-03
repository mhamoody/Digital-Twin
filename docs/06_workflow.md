# 06 — Workflow, ownership, and delivery plan

## Current state

Based on the meeting documents and weekly milestones, the project is still in planning/exploration with one important operational milestone completed.

| Area | Status |
|---|---|
| Original and group proposals | Complete; group proposal received 90% with scope, novelty, LLM-safety, and OULAD feedback |
| Literature and candidate datasets | Source comparison and MVP decision completed 2026-08-02; OULAD selected, alternatives assigned bounded non-merged roles in `08_data_strategy.md` |
| Target architecture and requirements | Revised in this documentation; database/API implementation not started |
| Local Moodle | Laragon Moodle, database, test course, assignments, pages, files, sections, and forum confirmed working |
| Moodle integration | Web services/token/API extraction and normalized transfer to PostgreSQL not yet demonstrated |
| OULAD preparation | Official archive directly profiled and checkpoint/feature policy specified; reproducible state builder and leakage tests not yet demonstrated |
| Structured models | Candidate baselines identified; reproducible checkpoint experiment not yet demonstrated |
| LLM | Role and safety contract now defined; proof of concept not yet run |
| Dashboard | Requirements defined; implementation not yet demonstrated |

Do not describe planned items as completed in presentations or reports.

## Recommended ownership

Ownership follows the latest task distribution while concentrating each person's work around one interface. The team should confirm this table at the next meeting.

| Lead | Primary responsibility | Required hand-off |
|---|---|---|
| Mohamed Abdel Majid | OULAD inspection, weekly-state builder, leakage controls, baseline/model evaluation | Versioned state table, tests, evaluation artifact, selected model |
| Arwa Elgazar | Alternative-dataset comparison, access/licence verification, independent text benchmark if feasible | Scored dataset matrix, access evidence, recommendation and optional prepared text sample |
| Esraa Nematalla | Moodle dataset/API investigation and canonical field mapping | Working read-only extraction, Moodle-to-canonical mapping, adapter tests |
| Mohamed Hasan | PostgreSQL/API/replay integration, provenance, alert/dashboard vertical slice | Migrations, replay scenario, API and minimal dashboard |
| Shared | Requirements review, LLM frozen-case labelling, usability walkthrough, ethics, report, demo | Signed decisions and reviewed results |

If the team's preferred spelling or task ownership differs from the source documents, update this table once and use the same names everywhere.

## Immediate decisions

| Decision | Owner(s) | Due before | Evidence required |
|---|---|---|---|
| Keep, complement, or replace OULAD | Arwa + Abdel Majid | Weekly-state implementation is locked | Completed matrix covering Open edX/HarvardX/MITx/MORF and strongest Moodle options, with access verified |
| Outcome and checkpoint definitions | Abdel Majid + team review | First model run | Written label policy, cutoff dates, withdrawal handling, and weeks to evaluate |
| Canonical observation/state schema | Esraa + Hasan + Abdel Majid | PostgreSQL migration and Moodle adapter | Field mapping from OULAD and Moodle plus provenance and missingness rules |
| Final MVP/stretch boundary | All members + supervisor | Any DiCE/forum/RAG implementation | Signed priority table from `02_goal.md` |
| Approved model/data access | Hasan or named university-contact owner | Hosted LLM test | Written confirmation of provider/credit/privacy route or decision to use local/template only |
| Human evaluators | Team + supervisor | Dashboard walkthrough | Availability and consent/ethics expectations for a small formative exercise |

## Delivery sequence

The sequence below is expressed in work weeks after this revised plan is accepted. Calendar dates should be added by the team; dependencies must not be compressed to preserve an old date.

| Work week | Outcome | Exit evidence |
|---|---|---|
| 1 | Scope and data gate | Approved MVP, completed dataset matrix, frozen state grain/outcome/checkpoints |
| 2 | First weekly-state slice | One presentation produces valid states; cutoff and uniqueness tests pass |
| 3 | Reproducible baselines | Majority, activity-only, grade-only, and logistic baselines run through one evaluation command |
| 4 | Selected calibrated model + SHAP | Model comparison, calibration plots, checkpoint table, stored evidence for sample predictions |
| 5 | Twin store vertical slice | Migrations persist source → observation → state → prediction → evidence → alert → review |
| 6 | Moodle adapter | Web-service/API or controlled-export extraction maps test users/course/activities/grades/forums into canonical observations |
| 7 | Replay and recovery | Controlled scenario updates states; idempotency, quarantine, retry, and freshness behaviour tested |
| 8 | Minimal dashboard | Course status, risk queue, student evidence, freshness, and alert review work end to end |
| 9 | LLM/template evaluation | Frozen cases, strict schema validation, fallback, and grounding report complete |
| 10 | Integrated MVP freeze | All P0/P1 components pass integration tests; no new features enter the MVP |
| 11–12 | Evaluation | Empirical, operational, LLM, fairness/sensitivity, and small walkthrough results recorded separately |
| 13 | Buffer and at most one stretch item | Critical defects resolved; one stretch feature only if the MVP remains reproducible |
| 14–16 | Final analysis, report, deployment guide, demo rehearsal | Reproducible package, limitations, negative results, slides, and live/fallback demo |

## Gates

### Gate A — data and experiment

- Dataset decision is recorded with evidence.
- Weekly-state schema, labels, checkpoints, and leakage policy are frozen.
- One complete state build and baseline evaluation are reproducible.

### Gate B — model and storage

- A model is selected using declared metrics and baselines.
- Calibration and checkpoint limitations are understood.
- The store preserves source, state, prediction, evidence, and versions.

### Gate C — integrated MVP

- Moodle-to-store ingestion/replay works.
- Dashboard and alert lifecycle work.
- Stale data and component failures are visible.
- LLM output is validated or safely replaced by a template.
- Empirical and synthetic/replayed results are not mixed.

### Gate D — stretch authorization

The team may select **one** stretch research task only if Gate C is passed with a reproducible demo and the report skeleton already contains the core results. The supervisor's feedback makes this a hard scope-control rule.

## Weekly working rhythm

1. Before the meeting, each owner updates a short artifact: code/notebook, decision record, dataset card, test result, or screenshot—not only a verbal status.
2. During the meeting, review current evidence, blocked interfaces, and scope changes.
3. Record decisions in the relevant `docs/` file and create issues with an owner and acceptance criterion.
4. Merge through pull requests with at least one teammate review. Any schema or metric change updates its documentation in the same pull request.
5. End each week with a runnable integration check, even if some components use fixtures.

## Branch and review convention

- Use short branches such as `data/weekly-state`, `lms/moodle-adapter`, `model/calibration`, or `app/alert-review`.
- Keep commits small and imperative.
- Do not commit datasets, database dumps, keys, or identifiable records.
- A pull request must state which requirement it satisfies, how it was tested, what data origin was used, and whether documentation changed.
- Model-result pull requests include configuration, seed, split, metrics, and artifact location.

## Project-risk controls

| Risk | Trigger | Response |
|---|---|---|
| Scope expansion | A second stretch feature is proposed before MVP freeze | Defer it automatically |
| Alternative-data delay | Access is still uncertain at Gate A | Keep OULAD; document the alternative as future validation |
| Weak early prediction | Model does not beat baselines or calibrate acceptably | Report the result; restrict dashboard to descriptive state or later checkpoints |
| LLM hallucination/invalid output | Unsupported evidence/action or schema failure | Suppress, retry once, then use template; record failure |
| Moodle API delay | Web services remain blocked | Use a controlled export/fixture adapter while resolving API access |
| Synthetic-result confusion | Replay metrics appear beside empirical metrics | Separate result sections/tables and require origin labels in queries |
| Usability recruitment failure | Fewer than the planned evaluators are available | Conduct a clearly labelled formative expert walkthrough; do not claim a usability study |

## Open items to assign now

- University process for compute, hosting, model access, and educational-data handling.
- Formal access outcome for supervisor-suggested Open edX/MORF data.
- Preferred Moodle deployment path for final reproduction: document Laragon fully or add Docker after the vertical slice.
- Ethics/consent requirement for instructor/TA walkthroughs.
- Repository decision on storing large public datasets locally versus scripted download with checksums.
