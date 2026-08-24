# Course-Level Digital Twin for Early Warning

A graduation-project prototype that builds leakage-controlled weekly student
states from learning-management-system evidence, estimates calibrated academic
risk, and presents traceable alerts for instructor review.

The project treats a digital twin as a timestamped, queryable, and historized
representation of observable course activity and progress. It does not attempt
to simulate a student's mind, diagnose causes, or automate educational actions.

## Project status

The repository has entered a gated implementation process. Phase 1 profiled the
complete local OULAD release and prepared the real `AAA/2013J` presentation with
explicit missingness, provenance, restricted outcomes, and a separately labelled
Moodle replay calendar. Phase 2 now builds cutoff-safe states at weeks 3, 5, 8,
and 10 and runs a deterministic, replaceable demo predictor through the validated
result and high-risk alert contracts. Phase 3 now supplies a PostgreSQL migration
and an idempotent lineage store, validated at full volume with a local relational
backend and PostgreSQL 16.14. Phase 4 adds an instructor-restricted FastAPI read
and audited-review boundary over that store. Phase 5 adds an API-only Streamlit
instructor workspace with the ranked queue, evidence/provenance view, checkpoint
timeline, freshness state, and audited review form. Phase 6 adds migration
`20260806_0002` and a read-only Moodle/controlled-export adapter, validated by a
12-week OULAD replay into a separately labelled operational presentation. Phase
7 now packages that replay as a reproducible end-to-end demo with PostgreSQL,
checkpoint states, temporary predictions, grounded alerts, API/dashboard reads,
a runbook, a journey map, and rendered evidence. The primary strong-LLM
experiment remains a later approval-gated research phase.

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
| LMS integration | Provider-neutral adapters; future LTI 1.3 external tool for Queen's onQ/Brightspace |
| API | FastAPI |
| Dashboard | Streamlit |
| Testing and quality | pytest, pytest-cov, Ruff |

Distributed streaming systems, Kubernetes, a custom JavaScript frontend, and a
vector database are intentionally outside the MVP.

## Getting started

The tracked repository is intentionally deployment-focused. Raw OULAD files,
generated data, tests, weekly planning material, presentations, and local LMS
harnesses remain on the developers' machines and are excluded from GitHub.

Python 3.11 and PostgreSQL 16 are the supported pilot versions. For a local
installation:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --editable .
Copy-Item .env.example .env
```

Fill `.env` locally without committing it, then apply the database migrations:

```powershell
$env:DIGITAL_TWIN_DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@localhost/course_digital_twin"
python -m alembic upgrade head
```

Start the internal API and dashboard in separate terminals:

```powershell
python -m uvicorn digital_twin.api.app:app --app-dir src --host 127.0.0.1 --port 8000
```

```powershell
$env:DIGITAL_TWIN_API_URL = "http://127.0.0.1:8000"
python -m streamlit run src/digital_twin/dashboard/app.py `
    --server.address 127.0.0.1 --server.port 8501
```

Open `http://127.0.0.1:8501`. The dashboard communicates with PostgreSQL only
through FastAPI. `simple-rules-v1` remains an untrained architecture test double,
not the project's final strong-LLM predictor or research evidence.

For Lobot, run `bash deploy/lobot/probe.sh` first and follow
[`docs/10_remote_hosting.md`](docs/10_remote_hosting.md). That guide covers the
protected instructor login, PostgreSQL restore, JupyterHub proxy, service
lifecycle, backups, and the alternative always-on VM deployment.

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
| [`docs/10_remote_hosting.md`](docs/10_remote_hosting.md) | Lobot probe, protected remote pilot, VM deployment, backups, and LMS-neutral integration boundary |

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
prepared OULAD presentation
  -> canonical observation
  -> weekly state
  -> validated predictor result
  -> evidence
  -> alert
  -> API/dashboard review
```

OULAD preparation, state/prediction/alert contracts, PostgreSQL lineage, the
FastAPI boundary, the instructor dashboard, and the controlled replay boundary
have been demonstrated end to end. The tracked repository now contains only the
application and remote-deployment entry points. The primary LLM evaluation and
baseline attribution checks remain later research phases.
