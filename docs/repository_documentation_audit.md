# Repository Documentation Audit

Audit date: 2026-11-11. Scope: documentation and repository organization only; no research artifact, database, deliverable, experiment, or source file was changed.

## Summary

The repository contains a scientifically reconciled root README and several accurate current boundary documents, but it also retains dated phase/deployment runbooks. Those historical documents are valuable audit context and should not be silently rewritten as current instructions. The largest practical gap was the absence of a single environment-rebuild, evidence-location, deliverables, and contributor-safety entry point after deletion of the historical root `.venv`.

## Areas inspected

- root `README.md`, `pyproject.toml`, `requirements.txt`, launchers, and environment examples;
- `docs/`, `scripts/`, `src/`, `frontend/`, `tests/`, `migrations/`, `deploy/`, and `var/` path structure;
- `artifacts/`, `deliverables/`, `archive/`, and `repo_cleanup_audit/`;
- preservation manifests, environment validation reports, cleanup reports, and canonical-deliverable designations.

`configs/` does not exist in the current checkout. Configuration is distributed among environment variables, `.env.example`, deployment examples, application source, and versioned policy/runtime records.

## Findings

| Area | Finding | Classification | Resolution in this pass |
|---|---|---|---|
| Root README | Scientifically current, but missing a complete post-clean environment/test path and repository/archive index | Current but incomplete | Expanded with validated reconstruction, test, layout, evidence, deliverable, and preservation guidance |
| Root README | Architecture wording previously placed “saved analysis or prediction” before one validation step | Ambiguous path separation | Replaced with two explicit parallel paths: empirical prediction and validated generated analysis |
| `docs/01_problem.md`–`05_architecture.md` | Reconciled high-level research/system boundaries | Current | Retained and linked |
| `docs/06_workflow.md`, `07_structure.md`, `10_remote_hosting.md` | Phase-era/Streamlit-first descriptions and paths | Historical/dates matter | Retained; not used as the primary current runbook |
| `docs/10_remote_hosting.md`, `14_workspace_upgrade.md`, `15_analysis_operations.md`, `17_model_reliability.md`, `18_output_contract.md`, `23_react_lobot.md` | Commands reference the removed historical `.venv` | Stale command | Flagged; use `REPRODUCIBILITY.md` to reconstruct an environment first |
| `frontend/README.md` | Contains machine-specific `E:\Z1\GP\Digital-Twin` examples and references historical validation files absent from current `tests/` | Stale/local operational context | Flagged; not modified because it is outside the allowed documentation set |
| `docs/20_dashboard_upgrade_progress.md` | References `tests/preview_dashboard_phase1.py`, which is absent | Broken historical path | Flagged; retained as phase history |
| Test documentation | Older documents list many historical tests; current scoped tree has six test modules and a preserved baseline of 66 collected/passed tests | Scope drift | Current baseline documented in `VALIDATED_BASELINE.md` |
| Evidence location | Authoritative evidence spans the active repository, a sibling evaluation repository, and verified preservation extracts | Discoverability risk | Added `RESEARCH_EVIDENCE_GUIDE.md` and links to manifests rather than duplicating raw data |
| Deliverables | Earlier assembled report, supervisor-corrected report, V2, and V3 coexist | Version ambiguity | Added `DELIVERABLES.md` using the preservation manifest’s designations |
| Archive | No root archive guide existed | Interpretation risk | Added `archive/README.md`; archive remains unchanged otherwise |
| Manual-review files | Twelve items intentionally survived cleanup | Safety risk | Added `MANUAL_REVIEW_ITEMS.md` without exposing secret values |
| Reproducibility | Exact Python lock and rebuild evidence existed only inside audit records | Missing entry point | Added `REPRODUCIBILITY.md` |

## Documentation precedence

1. Frozen evidence and preservation manifests.
2. `RESEARCH_EVIDENCE_GUIDE.md`, `VALIDATED_BASELINE.md`, and the root README.
3. Current boundary documents (`01_problem.md`–`05_architecture.md`).
4. Dated phase, deployment, migration, meeting, and progress documents.

Historical documents remain evidence of what was known or deployed at a stated time. They must not override later frozen results or be treated as current setup instructions without verification.

## Duplication assessment

Research boundaries recur across the README, problem/goal/solution documents, report chapters, and paper audits. This is intentional at the deliverable level but creates maintenance risk. The new guides minimize duplication by linking to hash manifests and canonical artifacts. Numeric claims in documentation should be updated only through a new versioned evidence reconciliation, not independently in multiple files.

## Unresolved documentation risks

- Dated runbooks still contain removed `.venv` and machine-specific commands; they are retained for traceability.
- The primary evaluation repository is external to this checkout. Verified copies are preserved locally, but active rerun tooling is not fully consolidated here.
- Node and Ollama are external to the exact Python lock.
- Raw OULAD CSV files are not retained in the main repository.
- Archive copies A/B remain unencrypted and on the same local volume.

## Audit verdict

The new documentation set supplies a current navigation and safety layer without rewriting historical evidence. Remaining stale references are explicitly classified rather than silently altered.

