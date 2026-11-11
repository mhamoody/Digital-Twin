# Course Digital Twin

This master's project implements a provenance-aware, checkpointed course digital twin that connects temporal learner-state reconstruction, predictive analysis, validated instructor-facing evidence, and auditable human support decisions.

The twin represents observable course activity and progress at declared checkpoints. It is not real-time, causal, a continuous psychological twin, or a universal student simulator.

## Current product

The current instructor interface is the **React + TypeScript + Vite** workspace, served by FastAPI. It provides authenticated course and checkpoint selection, learner profiles, evidence, risk history, instructor triage, support cases, support history, policies, and data/model provenance. Streamlit remains a legacy operational fallback.

The empirical product serves OULAD `AAA/2013J`. Its legacy `simple-rules-v1` score is an uncalibrated operational/demo value, not a probability and not a Qwen result. Synthetic Workspace data demonstrate product and operational workflows; they do not establish empirical predictive validity.

Risk State, Instructor Triage Status, and Support Case Status are separate. Instructor actions never rewrite historical model evidence.

## Research context

This repository supports the final Master's project and the EDUCON 2027 paper, *A Provenance-Aware Course Digital Twin for Predictive Learning Analytics*. The conference abstract was accepted; the full paper is under review/preparation for submission. No DOI, publication, or full-paper acceptance is claimed.

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

### E2 — controlled LLM grounding

E2 is a separate controlled experiment with 48 frozen cases: 12 scenario families, 24 `assessment_allowed`, and 24 `abstention_expected`. The valid primary comparison is `plain_llm` v2 versus `schema_only` v2.

Schema-only generation completed the full output contract and citation checks for 48/48 cases, with semantic evidence validity in 42/48. Both treatments were behaviorally correct in 24/48 and abstained in 0/48. The supported conclusion is:

> Schema-constrained generation substantially improves structural and citation compliance, but does not by itself improve selective abstention or behavioral decision accuracy.

E2 v1, invalid schema-only r1, the defective original `evidence_first_full`, and incomplete post-hoc `evidence_first_full_v2` are excluded from the primary comparison.

### E4 — temporal integrity

The provenance audit covers **194,590 provenance rows** and reports **0 cutoff violations** in the audited artifacts. This establishes cutoff integrity and traceability for those artifacts, not predictive accuracy or universal source correctness.

### Operational Qwen evidence

Operational Qwen analysis is separate from E1 and E2. The mature path uses `qwen2.5:7b`, model digest `845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`, the `risk-decision-v3` contract, deterministic validation, bounded repair, quality abstention, and prompt/model provenance.

Among saved validated analyses, v3.3 achieved a higher first-pass validation share and a lower repair share than v3.2 under the same model identity and contract. This is operational reliability evidence, not predictive accuracy. No calibrated Qwen probability was established.

### Workflow verification

Current source, migrations, and regression tests verify exact state binding, immutable model history, independent triage/support history, authorization, idempotency, and stale-version handling. This is framework/system verification, not an educator-effectiveness or learner-outcome study.

## Contribution hierarchy

Primary research contributions:

1. Provenance-aware cutoff-safe temporal learner-state construction.
2. Checkpoint-specific empirical predictive analysis across early learner states.
3. Controlled evidence that structural/citation compliance alone does not guarantee correct selective abstention or behavioral decisions.

The versioned operational LLM pipeline is a secondary research contribution. Separating prediction/model state, instructor triage, and support-case state is a framework contribution. React, FastAPI, authentication, persistence, deployment, workers, and the Streamlit fallback are engineering/product work; the React dashboard is not claimed as research novelty.

## Architecture

```text
Course records
  -> cutoff-safe checkpointed learner state + provenance
      -> empirical prediction -------------------+
      -> validated generated analysis -----------+-> instructor workspace
                                                       -> independent triage
                                                       -> support-case history
```

The two analysis paths are distinct. The operational Qwen path runs through versioned snapshots, queued analysis, structured-output validation, bounded correction, and explicit abstention. Instructor decisions do not rewrite historical model evidence. E1 and E2 remain separate research paths.

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

## Repository layout

| Path | Purpose |
|---|---|
| `src/` | Active Python application source |
| `frontend/` | Active React workspace source and preserved build output |
| `tests/` | Current scoped Python tests |
| `scripts/` | Preparation, ingestion, operations, and runtime helpers |
| `migrations/` | Alembic/SQL schema history |
| `artifacts/` | Frozen/supporting research artifacts; do not overwrite |
| `deliverables/` | Master's and EDUCON deliverables |
| `archive/` | Historical material; not active source |
| `docs/` | Current and dated documentation |
| `repo_cleanup_audit/` | Preservation, manifests, environment validation, and cleanup records |
| `deploy/` | Lobot/VM deployment scripts and examples |
| `var/` | Local runtime data and sensitive configuration; do not publish |

See [`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) for modification rules.

## Environment setup

The historical root `.venv` was intentionally removed after a successful clean rebuild. The validated environment uses Python **3.11.16** and the exact 66-package lock at `repo_cleanup_audit/final_preservation/environment_validation/candidate_requirements.lock`.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r repo_cleanup_audit\final_preservation\environment_validation\candidate_requirements.lock
$env:PYTHONPATH="$PWD\src"
```

The validated process supplies the local project through `PYTHONPATH`; it does not rely on an editable install. Node and Ollama are external runtimes and are not covered by the Python lock. See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## Running tests

From the repository root, after setting `PYTHONPATH`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\digital-twin-pytest" tests
```

The preserved post-clean baseline is **66 passed, 0 failed, 0 errors**. This is a dated baseline, not a guarantee after future code changes.

## Running the product

The tracked Windows launcher requires an operator-approved database and authentication configuration. It does not create, migrate, reset, or seed a database:

```powershell
$env:DIGITAL_TWIN_PYTHON=(Resolve-Path .\.venv\Scripts\python.exe).Path
$env:DIGITAL_TWIN_DATABASE_URL='<operator-approved database URL>'
# Set the approved auth/API-key/presentation variables for the intended runtime.
.\start-digital-twin.ps1
```

The launcher performs environment and port checks before starting FastAPI and the Streamlit fallback. Do not point development commands at production data. The current React workspace requires Node 22.12+ and can be built with `npm.cmd ci` followed by `npm.cmd run build` from `frontend/`. `frontend/dist/` is currently preserved pending a separate runtime/build review. Local Qwen/Ollama support is optional and must not be confused with E1. No public deployment is claimed by this documentation.

## Research artifacts and deliverables

Start evidence review with:

- [`repo_cleanup_audit/preservation_phase/canonical_research_evidence_manifest.md`](repo_cleanup_audit/preservation_phase/canonical_research_evidence_manifest.md)
- [`repo_cleanup_audit/preservation_phase/research_evidence_sha256_manifest.csv`](repo_cleanup_audit/preservation_phase/research_evidence_sha256_manifest.csv)
- [`repo_cleanup_audit/final_preservation/archive_content_manifest.csv`](repo_cleanup_audit/final_preservation/archive_content_manifest.csv)
- [`repo_cleanup_audit/phase2_execution/post_cleanup_hash_verification.csv`](repo_cleanup_audit/phase2_execution/post_cleanup_hash_verification.csv)

Frozen outputs are immutable evidence. Create a new versioned experiment directory instead of overwriting an existing artifact.

- Canonical Master's report: `deliverables/final_report/Final_Revised_Report_Supervisor_Corrected.docx` and `.pdf`.
- Final presentation: `deliverables/final_presentation/Group_12_Course_Digital_Twin_Final.pptx` and `.pdf`.
- EDUCON abstract: `deliverables/educon2027/educon2027_abstract_final.md`.
- Current EDUCON supervisor-review paper: `deliverables/educon2027/full_paper_v3/`.
- Historical EDUCON V2 package: `archive/deliverables/educon2027/full_paper_v2/`; its supporting audits remain in the active deliverable tree.

See [`docs/DELIVERABLES.md`](docs/DELIVERABLES.md) and [`docs/RESEARCH_EVIDENCE_GUIDE.md`](docs/RESEARCH_EVIDENCE_GUIDE.md).

## Preservation and cleanup

Preservation and Phase-2 cleanup completed successfully. Protected evidence reverified with zero hash mismatches; 66 scoped tests and a fresh environment rebuild passed. Two local preservation archives exist, while manual-review files and `frontend/dist` remain intentionally untouched. The archives are unencrypted and on the same local volume, so one verified copy should be encrypted and stored off-device.

## Known limitations

- Evaluation covers one OULAD course presentation with small/changing checkpoint test populations.
- E1 uses a zero-filled model matrix and reports discrimination, not calibrated probabilities.
- Cross-course validation and calibration were not completed.
- E4 is a bounded exported-link audit, not universal leakage proof.
- E2 uses designed synthetic cases.
- Operational evidence uses selected saved-record denominators and does not establish predictive accuracy.
- No educator-effectiveness or learner-outcome study was performed.

## Source of truth and precedence

Current claims use this precedence:

1. `evaluation/reports/final_research_evidence_matrix.md` in the sibling `Digital-Twin-evaluation` repository, preserved under `repo_cleanup_audit/final_preservation/archive_verification_extract_A/research_evidence/`.
2. The preserved `evaluation/reports/e2_run_validity.md`.
3. The preserved `evaluation/reports/llm_operational_version_evidence.md`.
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

See [`docs/01_problem.md`](docs/01_problem.md), [`docs/02_goal.md`](docs/02_goal.md), [`docs/03_solution.md`](docs/03_solution.md), [`docs/05_architecture.md`](docs/05_architecture.md), and [`docs/CONTRIBUTOR_SAFETY.md`](docs/CONTRIBUTOR_SAFETY.md) for the current research, system, and contribution boundaries.
