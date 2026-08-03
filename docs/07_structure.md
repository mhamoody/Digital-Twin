# 07 — Repository structure

## Current repository

At the time of this update, the repository contains eight reviewed documentation
files. The implementation folders below are a **target structure**, not evidence
that those components already exist.

## Target structure

```text
Digital-Twin/
├── README.md
├── docs/
│   ├── 01_problem.md
│   ├── 02_goal.md
│   ├── 03_solution.md
│   ├── 04_stack.md
│   ├── 05_architecture.md
│   ├── 06_workflow.md
│   ├── 07_structure.md
│   └── 08_data_strategy.md
├── planning/
│   ├── decisions/                 # dated architecture/scope/data decision records
│   ├── dataset-cards/             # access, licence, fields, quality, final verdict
│   ├── literature/                # notes and reference mapping
│   └── protocols/                 # experiment, LLM, and walkthrough protocols
├── src/
│   └── digital_twin/
│       ├── config/
│       ├── ingestion/
│       │   ├── oulad.py
│       │   └── moodle.py
│       ├── schemas/                # canonical input/output models
│       ├── state/                  # weekly-state construction and leakage rules
│       ├── models/                 # classical baselines and shared calibration/metrics
│       ├── explanations/           # evidence validation, ablations, baseline SHAP, fallback
│       ├── llm/                    # primary predictor adapter, prompts, validators, inference
│       ├── alerts/                 # eligibility policy and lifecycle
│       ├── api/                    # FastAPI routes/services
│       └── dashboard/              # Streamlit application
├── migrations/                     # PostgreSQL schema migrations
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── leakage/
│   └── fixtures/                   # small non-identifiable test records
├── notebooks/
│   ├── exploration/                # disposable investigation only
│   └── reports/                    # reviewed, reproducible analysis notebooks
├── experiments/
│   ├── configs/                    # committed configurations/seeds/splits
│   └── README.md                   # how artifacts are generated and located
├── scripts/
│   ├── prepare_data.*
│   ├── build_states.*
│   ├── train_evaluate.*
│   ├── replay_moodle.*
│   └── run_demo.*
├── deployment/
│   ├── docker/
│   └── moodle/                     # Laragon and/or Docker setup instructions
├── data/
│   ├── README.md                   # source, download, licence, checksum instructions
│   ├── raw/                        # ignored
│   ├── interim/                    # ignored
│   ├── processed/                  # ignored unless tiny fixtures
│   └── synthetic/                  # ignored; regenerated from scripts
├── artifacts/                      # ignored model/results output; manifest may be tracked
├── .github/workflows/
├── .env.example
├── .gitignore
├── pyproject.toml
└── dependency lock file
```

Use platform-appropriate script extensions (`.py`, `.ps1`, or `.sh`) and document the supported Windows workflow. The wildcard above means “one documented entry point,” not three duplicate implementations.

## Placement rules

- `docs/` is the reviewed project truth: problem, scope, design, and process.
- `planning/` contains evidence and decisions that support the reviewed docs.
- `src/` contains reusable application code. A notebook must not be the only implementation of state construction, leakage prevention, training, or inference.
- `notebooks/exploration/` can be messy; a result cited in the report must be reproducible through a script/config or a reviewed report notebook.
- `tests/fixtures/` contains only tiny, fabricated, non-identifiable examples.
- `data/` and `artifacts/` contain local/generated files and are ignored by default. Track instructions, licences, checksums, manifests, and small summary tables instead of large datasets or models.
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

The first slice can use a tiny fixture and deterministic fallback to prove the
interfaces, but the strong-LLM prediction adapter enters before the model
evaluation is considered complete. Add full OULAD, Moodle, LLM calibration and
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

Every reproducible dataset has a dataset card containing source, access date,
licence, checksum, expected files, preparation command, and known limitations.
Every reported model has a manifest containing data version, feature version,
split, seed, code commit, model/calibrator version, and metrics. An LLM manifest
also pins provider, exact model identifier/snapshot, prompt, few-shot examples,
decoding settings, access date, latency, and cost.

## Documentation update rule

Change the relevant documentation in the same pull request when any of these changes:

- MVP versus stretch scope;
- outcome, checkpoint, feature, or leakage policy;
- dataset or licence decision;
- database/API/LLM schema;
- model-selection or evaluation protocol; or
- deployment and privacy assumptions.

This rule prevents the repository from drifting back toward the broader proposal after the feedback-driven scope correction.
