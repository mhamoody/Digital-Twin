# 04 — Current technology stack and boundaries

| Layer | Current selection | Role |
|---|---|---|
| Instructor interface | React, TypeScript, Vite | Current product workspace |
| Legacy interface | Streamlit | Operational fallback and historical workflow reference |
| API | FastAPI | Authenticated course-scoped read and mutation boundary |
| Persistence | PostgreSQL, SQLAlchemy, Alembic | Primary relational state and audit store |
| Local contract support | SQLite | Local development and contract tests where supported |
| Empirical data/evaluation | Python, pandas, NumPy, scikit-learn | OULAD preparation and E1 Logistic Regression evaluation |
| Operational LLM | Qwen2.5:7b | Instructor-facing analysis under deterministic validation |
| Worker/runtime | Versioned jobs, attempts, traces, snapshots and policies | Operational analysis lifecycle |
| Quality | pytest, TypeScript checks, migration and browser validation | Regression and contract protection |

## Modelling boundary

Logistic Regression supplies the frozen E1 empirical results. Qwen supplies operational instructor-facing analyses and participates in the separate E2 controlled grounding experiment. Qwen is not the E1 predictor, and no Qwen score is presented as a calibrated probability.

The operational LLM path uses structured generation, deterministic validation, bounded repair, explicit quality abstention, and auditable prompt/model provenance. These mechanisms support operational reliability; they do not by themselves establish predictive validity.

## Data and deployment boundary

OULAD `AAA/2013J` is the primary empirical course presentation. Synthetic Workspace courses and controlled replay data exercise workflows, reliability, and UI behavior but are not empirical validation cohorts.

The system supports scheduled updates; it does not claim real-time streaming. PostgreSQL owns normalized application state and audit history. Source LMS systems remain separate and are accessed through approved adapters or exports.

## Deliberately excluded claims

- Foundation-model training from scratch.
- A calibrated Qwen failure probability.
- A vector database as a research requirement.
- Causal or psychological learner simulation.
- Institution-wide production readiness.
- Cross-course empirical generalization from synthetic demonstrations.

## Interface status

React is the current instructor interface. The Streamlit implementation is retained as legacy/fallback functionality and as historical evidence of earlier product phases. Documents written before React acceptance should be read in their dated development context.
