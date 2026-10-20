# 07 — Repository structure

## Current repository

Implementation has started through an approval-gated vertical slice. Phase 1
adds the package scaffold, versioned contracts, full OULAD profiling, and a
reproducibly prepared real presentation. Phase 2 adds the cutoff-safe state
builder, replaceable demo predictor, high-risk alert policy, generated-artifact
validation, and leakage tests. Phase 3 adds SQLAlchemy persistence models, an
Alembic PostgreSQL migration, full-volume replay/lineage validation, and audited
alert review transitions. Phase 4 adds the FastAPI application factory, strict
request/response contracts, instructor authorization placeholder, query service,
live PostgreSQL validator, loopback smoke test, and API integration tests.
Phase 5 implements the API-only Streamlit dashboard client/application, its live
PostgreSQL validator, and reproducible headless-browser screenshot gate. The
Phase 6 implementation adds the read-only Moodle REST/controlled-export adapter,
accelerated replay orchestration, synchronization and quarantine persistence,
the `20260806_0002` migration, and live PostgreSQL validation. The executed path
is the controlled-export fallback because no local Moodle server was detected.
The remaining folders below are still a target structure until their corresponding
phase is approved and demonstrated.

## Tracked deployment structure

```text
Digital-Twin/
├── README.md
├── Dockerfile
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
├── docs/
│   ├── 01_problem.md
│   ├── 02_goal.md
│   ├── 03_solution.md
│   ├── 04_stack.md
│   ├── 05_architecture.md
│   ├── 06_workflow.md
│   ├── 07_structure.md
│   ├── 08_data_strategy.md
│   └── 10_remote_hosting.md
├── src/
│   └── digital_twin/
│       ├── ingestion/              # canonical and controlled replay adapters
│       ├── schemas/                # validated state/output contracts
│       ├── state/                  # cutoff-safe state construction
│       ├── models/                 # replaceable predictor boundary
│       ├── alerts/                 # eligibility and lifecycle policy
│       ├── persistence/            # PostgreSQL models and lineage store
│       ├── api/                    # internal FastAPI boundary
│       └── dashboard/              # protected instructor application
├── migrations/
│   └── versions/                   # authoritative Alembic revisions
├── scripts/
│   ├── prepare_oulad.py            # local approved-data preparation
│   ├── run_phase7_demo.py          # controlled database population
│   ├── initialize_pilot_database.py # SQLite pilot schema initialization
│   └── manage_instructor_accounts.py
└── deploy/
    ├── lobot/                      # probe and JupyterHub service lifecycle
    └── vm/                         # always-on Compose/HTTPS profile
```

Local datasets, tests, validation utilities, planning records, generated reports,
presentations, and the Moodle harness remain outside the deployment repository
through `.gitignore`. They are preserved locally and can be moved to a separate
private research repository later if the team needs shared development history.

## Placement rules

- `docs/` is the reviewed project truth: problem, scope, design, and process.
- `src/` contains reusable application code; runtime behavior must not exist only
  in a notebook or local validation script.
- `scripts/` contains only operational entry points required to prepare approved
  data, load the controlled demo, or manage pilot accounts.
- `deploy/` contains repeatable Lobot and group-VM service operations.
- Local `data/`, `artifacts/`, tests, and research working material are ignored.
- Database changes are migrations, not manual edits captured only in screenshots.
- Prompt templates and JSON schemas are versioned code. A prompt change that affects output creates a new prompt version.

## Minimum first vertical slice

Create only the paths needed to prove this flow:

```text
fixture/raw source
    -> canonical observation
    -> weekly state
    -> primary LLM prediction + baseline comparison
    -> evidence
    -> alert
    -> API/dashboard review
```

The first state-to-alert slice now uses prepared OULAD and a deterministic demo
predictor to prove the interfaces. This predictor is not the final fallback or a
research baseline. The strong-LLM prediction adapter enters before model
evaluation is considered complete. Add PostgreSQL, Moodle, LLM calibration and
grounding tests, and baseline SHAP incrementally after the contracts are tested.
This reduces the risk of four members building incompatible components in
parallel without demoting the LLM to an optional add-on.

## Data and artifact policy

The following must not be committed:

- Queen's or other identifiable student data;
- Moodle database dumps containing users;
- raw licensed datasets whose terms do not permit redistribution;
- API keys, database passwords, tokens, or `.env` files;
- large trained models, caches, or experiment directories; and
- unrestricted raw LLM requests/responses containing educational text.

Dataset cards, evaluation evidence, and model manifests remain required research
records, but this minimal deployment repository does not publish them. They must
be stored in an access-controlled research location and linked only when their
data and licensing terms permit publication.

## Documentation update rule

Change the relevant documentation in the same pull request when any of these changes:

- MVP versus stretch scope;
- outcome, checkpoint, feature, or leakage policy;
- dataset or licence decision;
- database/API/LLM schema;
- model-selection or evaluation protocol; or
- deployment and privacy assumptions.

This rule prevents the repository from drifting back toward the broader proposal after the feedback-driven scope correction.
