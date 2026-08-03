# Course-Level Digital Twin for Early Warning

A graduation-project prototype that builds leakage-controlled weekly student
states from learning-management-system evidence, estimates calibrated academic
risk, and presents traceable alerts for instructor review.

The project treats a digital twin as a timestamped, queryable, and historized
representation of observable course activity and progress. It does not attempt
to simulate a student's mind, diagnose causes, or automate educational actions.

## Project status

The repository is currently in the planning and architecture phase. The reviewed
requirements, research boundaries, target architecture, and delivery workflow
are documented under `docs/`. Application code, database migrations, runnable
pipelines, and deployment assets are planned but have not yet been implemented.

## Research objective

The primary objective is to determine whether a capable LLM can reason over
leakage-controlled weekly student states and produce useful, calibrated,
evidence-grounded estimates of non-success earlier than simple majority,
activity-only, grade-only, and conventional structured-ML baselines.

The planned evaluation uses checkpoints such as weeks 3, 5, 8, and 10 and keeps
two evidence paths separate:

- **Empirical research path:** OULAD, or an approved replacement, for model
  performance, calibration, and temporal evaluation.
- **Operational test path:** a local Moodle sandbox for ingestion, replay,
  persistence, alert lifecycle, and dashboard validation.

Synthetic or replayed Moodle learners are used only to test the system. They are
not evidence of real-world predictive performance.

## Planned MVP

1. Convert empirical and Moodle records into provenance-aware canonical
   observations.
2. Build one versioned state per learner, course presentation, and checkpoint.
3. Test cutoff rules so future activity, outcomes, and assessment results cannot
   leak into earlier states.
4. Evaluate a strong LLM as the primary risk model against transparent and
   conventional-ML baselines, then calibrate its risk scores.
5. Persist observations, states, predictions, evidence, alerts, and instructor
   reviews in PostgreSQL.
6. Expose a minimal FastAPI service and Streamlit instructor dashboard.
7. Require the LLM to return schema-valid risk, uncertainty, and evidence
   references grounded only in the supplied weekly state.
8. Validate every model response and use a deterministic rule/template path
   when the LLM is unavailable, invalid, or outside its approved context.

No alert directly contacts, grades, penalizes, or refers a student. An instructor
must remain in the decision loop.

## Technology stack

| Area | Planned technology |
|---|---|
| Language and data | Python, pandas, NumPy |
| Primary modelling | A selected strong hosted or open-weight LLM behind a provider-neutral adapter |
| Baselines/calibration | scikit-learn; post-hoc calibration fitted without test leakage |
| Evidence | LLM evidence references, input ablation tests, and deterministic fallback; SHAP for compatible baselines only |
| Twin store | PostgreSQL, SQLAlchemy, Alembic |
| LMS integration | Moodle web services/API or controlled export |
| API | FastAPI |
| Dashboard | Streamlit |
| Testing and quality | pytest, pytest-cov, Ruff |

Distributed streaming systems, Kubernetes, a custom JavaScript frontend, and a
vector database are intentionally outside the MVP.

## Getting started

Python 3.11 is the recommended development version. PostgreSQL and the local
Moodle sandbox will be needed for the integrated application, but they are not
required to read the documentation or begin isolated data work.

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The dependency ranges in `requirements.txt` are an initial development baseline.
They should be resolved into a lock file after the first vertical slice is
working. The LLM is a core component, but its provider-specific SDK is not
included until the team selects the model and approved access route. Boosting
and counterfactual packages remain optional.

There is no application start command yet because the implementation has not
started. Runnable preparation, state-building, evaluation, replay, and demo
commands will be added with their corresponding source code.

## Documentation

| Document | Purpose |
|---|---|
| [`docs/01_problem.md`](docs/01_problem.md) | Problem definition, research position, and constraints |
| [`docs/02_goal.md`](docs/02_goal.md) | Priorities, acceptance criteria, and definition of done |
| [`docs/03_solution.md`](docs/03_solution.md) | Proposed solution and component contracts |
| [`docs/04_stack.md`](docs/04_stack.md) | Technology choices and selection rules |
| [`docs/05_architecture.md`](docs/05_architecture.md) | Architecture, data contracts, and evaluation boundaries |
| [`docs/06_workflow.md`](docs/06_workflow.md) | Ownership, delivery sequence, gates, and risks |
| [`docs/07_structure.md`](docs/07_structure.md) | Target repository structure and placement rules |
| [`docs/08_data_strategy.md`](docs/08_data_strategy.md) | Dataset decision, direct data profile, feature contract, database shape, and pipeline |

When these documents conflict with older proposals or meeting notes, the latest
feedback-driven MVP boundary in `docs/` takes precedence.

## Data, privacy, and research integrity

Do not commit:

- identifiable student information or unrestricted educational text;
- raw datasets that cannot legally be redistributed;
- Moodle database dumps containing user records;
- passwords, database URLs, API keys, or access tokens;
- generated models, large experiment artifacts, or unrestricted LLM logs.

Use pseudonymous learner identifiers. Preserve each record's origin, event time,
ingestion time, source identifier, and schema/adapter version. Keep empirical,
replayed, synthetic, and manual-test results explicitly labelled and report them
separately.

## Development principles

- Reusable logic belongs in `src/`, not only in notebooks.
- Every weekly state and prediction must be reproducible from versioned inputs
  and configuration.
- Preprocessing, imputation, feature selection, and calibration must be fitted
  on training data only.
- Database changes must use migrations.
- Any change to the MVP boundary, data policy, schemas, model protocol, or
  deployment assumptions must update the relevant documentation.
- Pull requests should state the satisfied requirement, test evidence, data
  origin, and documentation impact.

## Near-term roadmap

The first implementation milestone is a minimal vertical slice:

```text
tiny fixture
  -> canonical observation
  -> weekly state
  -> LLM prediction + baseline comparison
  -> evidence
  -> alert
  -> API/dashboard review
```

Full OULAD preparation, Moodle integration, the primary LLM evaluation, and
baseline attribution checks will be added incrementally after these interfaces
and leakage controls are tested.
