# Provenance-Aware Course Digital Twin

This master's project implements a provenance-aware, checkpointed course digital twin that connects temporal learner-state reconstruction, predictive analysis, validated instructor-facing evidence, and auditable human support decisions.

The twin represents observable course activity and progress at declared checkpoints. It is not real-time, causal, a continuous psychological twin, or a universal student simulator.

## Current product

The current instructor interface is the **React + TypeScript + Vite** workspace, served by FastAPI. It provides authenticated course and checkpoint selection, learner profiles, evidence, risk history, instructor triage, support cases, support history, policies, and data/model provenance. Streamlit remains a legacy operational fallback.

The empirical product serves OULAD `AAA/2013J`. Its legacy `simple-rules-v1` score is an uncalibrated operational/demo value, not a probability and not a Qwen result. Synthetic Workspace data demonstrate product and operational workflows; they do not establish empirical predictive validity.

Risk State, Instructor Triage Status, and Support Case Status are separate. Instructor actions never rewrite historical model evidence.

## Final research questions

1. **RQ1 — Temporal Prediction:** How does predictive performance evolve across cutoff-safe learner states at early course checkpoints?
2. **RQ2 — Temporal Integrity:** Can a provenance-aware temporal learner-state pipeline prevent post-cutoff information leakage while preserving traceability?
3. **RQ3 — LLM Grounding and Reliability:** How do structural constraints and deterministic validation affect evidence compliance, abstention behavior and operational reliability of LLM-generated instructor-facing analyses?
4. **RQ4 — Human-in-the-loop Traceability:** How can model risk, instructor triage and longitudinal support decisions be represented separately while preserving historical model evidence?

RQ4 is a framework/system question, not an educator-effectiveness experiment.

## Frozen research evidence

### E1 — empirical temporal prediction

E1 evaluates Logistic Regression on OULAD `AAA/2013J`: 383 source enrolments, 372 eligible learners, and 1,464 temporal states. Learner-grouped splitting, train-only preprocessing, validation-based threshold selection, and untouched test evaluation were used.

| Checkpoint | AUROC | Average Precision |
|---|---:|---:|
| Week 3 | 0.621 | 0.379 |
| Week 5 | 0.657 | 0.531 |
| Week 8 | 0.896 | 0.819 |
| Week 10 | 0.834 | 0.802 |

These are Logistic Regression discrimination metrics, not Qwen results or calibrated probabilities.

### E4 — temporal integrity

The provenance audit covers **194,590 provenance rows** and reports **0 cutoff violations** in the audited artifacts. This establishes cutoff integrity and traceability for those artifacts, not predictive accuracy or universal source correctness.

### E2 — controlled LLM grounding

E2 is a separate controlled experiment with 48 frozen cases: 12 scenario families, 24 `assessment_allowed`, and 24 `abstention_expected`. The valid primary comparison is `plain_llm` v2 versus `schema_only` v2.

Schema-only generation completed the full output contract and citation checks for 48/48 cases, with semantic evidence validity in 42/48. Both treatments were behaviorally correct in 24/48 and abstained in 0/48. The supported conclusion is:

> Schema-constrained generation substantially improves structural and citation compliance, but does not by itself improve selective abstention or behavioral decision accuracy.

E2 v1, invalid schema-only r1, the defective original `evidence_first_full`, and incomplete post-hoc `evidence_first_full_v2` are excluded from the primary comparison.

### Operational Qwen evidence

Operational Qwen analysis is separate from E1 and E2. The mature path uses `qwen2.5:7b`, model digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, the `risk-decision-v3` contract, deterministic validation, bounded repair, quality abstention, and prompt/model provenance.

Among saved validated analyses, v3.3 achieved a higher first-pass validation share and a lower repair share than v3.2 under the same model identity and contract. This is operational reliability evidence, not predictive accuracy. No calibrated Qwen probability was established.

## Contribution hierarchy

Primary research contributions:

1. Provenance-aware cutoff-safe temporal learner-state construction.
2. Checkpoint-specific empirical predictive analysis across early learner states.
3. Controlled evidence that structural/citation compliance alone does not guarantee correct selective abstention or behavioral decisions.

The versioned operational LLM pipeline is a secondary research contribution. Separating prediction/model state, instructor triage, and support-case state is a framework contribution. React, FastAPI, authentication, persistence, deployment, workers, and the Streamlit fallback are engineering/product work; the React dashboard is not claimed as research novelty.

## Architecture

```text
Instructor -> React workspace -> FastAPI
           -> exact temporal learner/course state
           -> saved analysis or prediction
           -> deterministic validation
           -> instructor triage
           -> support workflow
           -> audit/history
```

The operational Qwen path runs through versioned snapshots, queued analysis, validated structured output, bounded correction, and explicit abstention. E1 and E2 remain separate research paths.

## Technology stack

| Area | Current implementation |
|---|---|
| Frontend | React, TypeScript, Vite |
| API | FastAPI |
| Persistence | PostgreSQL and SQLite contract/test support; SQLAlchemy/Alembic |
| Empirical evaluation | pandas, NumPy, scikit-learn |
| Operational LLM | Local Qwen2.5:7b through the workspace worker |
| Legacy interface | Streamlit fallback |
| Quality | pytest and TypeScript type/build checks |

## Running the product

Use the tracked Windows launcher for the integrated local profile:

```powershell
.\start-digital-twin.ps1
```

The launcher performs environment and port checks before starting the required services. Follow the deployment-specific runbooks for Lobot or other hosts.

## Source of truth and precedence

Current claims use this precedence:

1. `evaluation/reports/final_research_evidence_matrix.md` in the sibling `Digital-Twin-evaluation` repository.
2. `evaluation/reports/e2_run_validity.md`.
3. `evaluation/reports/llm_operational_version_evidence.md`.
4. Frozen E1, E2, and E4 result artifacts.
5. This README and current product documentation.
6. Historical phase, migration, deployment, meeting, and planning documents.

Historical documents preserve what was planned or known at their stated time; they do not override the frozen final evidence.

## Research integrity boundaries

- Keep empirical, controlled-experimental, operational, replayed, and synthetic results explicitly separated.
- Do not present raw scores as probabilities.
- Do not infer motivation, understanding, diagnosis, or causality from LMS data.
- Do not expose direct identifiers or secrets.
- Do not automate student contact, grading, penalties, or referrals.
- Preserve exact state, evidence, model, prompt, policy, and human-action history.

See [`docs/01_problem.md`](docs/01_problem.md), [`docs/02_goal.md`](docs/02_goal.md), [`docs/03_solution.md`](docs/03_solution.md), and [`docs/05_architecture.md`](docs/05_architecture.md) for the reconciled current research and system boundary.
