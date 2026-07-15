# 07 — Structure

## Repository / project folder structure (reflecting Phase 0 reality)

```
course-digital-twin/
├── docs/
│   ├── 01_problem.md
│   ├── 02_goal.md
│   ├── 03_solution.md
│   ├── 04_stack.md
│   ├── 05_architecture.md
│   ├── 06_workflow.md
│   └── 07_structure.md
│
├── planning/                      # Phase 0 working area — active now
│   ├── schema/                    # target data schema drafts + revisions
│   ├── dataset-comparison/        # per-dataset gap analysis notes, raw comparison tables
│   ├── requirements/              # functional/non-functional requirements drafts
│   ├── literature-review/         # digital-twin literature notes, supervisor-provided papers once received
│   └── poc/                       # PoC protocol, hand-labeled 20-30 post sample, PoC run results
│
├── pipeline/                      # NOT YET POPULATED — Phase 1, gated behind 06_workflow.md's gate criteria
│   └── (sync job / ETL code will live here once the gate is passed)
│
├── analytics/                     # NOT YET POPULATED — Phase 1
│   ├── classifier/                # structured at-risk classifier (scikit-learn)
│   └── llm/                       # LLM forum/text analytics layer
│
├── dashboard/                     # NOT YET POPULATED — Phase 1
│   └── (Streamlit app will live here once the gate is passed)
│
├── data/                          # NOT YET POPULATED — Phase 1
│   └── (sandbox seed data, synthetic data generation scripts — no real Queen's data ever)
│
├── .github/
│   └── workflows/                 # CI, once there is code to run CI against
│
├── README.md
└── .gitignore
```

The `pipeline/`, `analytics/`, `dashboard/`, and `data/` folders are created as empty placeholders with a short `README.md` inside each explaining that they are Phase 1 targets, not yet populated — this keeps the repo structure visible and reviewable from week 1 without pretending build work has started.

## Naming/branching convention (3–4 person team)

- **Branches:** `phase0/<short-topic>` for current planning work (e.g., `phase0/target-schema`, `phase0/dataset-comparison-oulad`) and `phase1/<short-topic>` once build work actually starts (e.g., `phase1/sync-job`, `phase1/at-risk-classifier`). This makes the phase gate visible in the git history itself, not just in `06_workflow.md`.
- **Main branch:** `main`, protected — no direct pushes; all changes come through a pull request.
- **PR expectations:** every PR gets at least one teammate review before merging, even during Phase 0 documentation work — this is a 3–4 person team, so review load is light, but it catches the kind of unflagged inconsistency this whole document set is trying to avoid (e.g., a schema change in `planning/schema/` that isn't reflected in `docs/05_architecture.md`). PR descriptions should note which `docs/0X_*.md` file(s), if any, need a corresponding update.
- **Commit messages:** short imperative summary line (e.g., "Add OULAD field mapping to schema comparison"), referencing the relevant planning sub-folder or docs file where useful.

## Where the docs produced by this exercise live once the repo exists

The seven files (`01_problem.md` through `07_structure.md`) live at the repo root under `/docs`, numbered exactly as delivered here so they sort in reading order in any file browser or IDE. `planning/` holds the underlying working materials (raw dataset comparison tables, schema drafts, literature notes, PoC results) that feed into the polished `docs/` files — the `docs/` files are the synthesized, reviewed output; `planning/` is the scratch work. When a `planning/` artifact matures into something that changes a `docs/` file's content (e.g., the schema is finalized), the corresponding `docs/0X_*.md` file should be updated in the same PR, not left to drift out of sync.
