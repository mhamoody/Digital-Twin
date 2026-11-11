# Archive Guide

This directory contains historical project material moved during the verified Phase-2 cleanup. It is not active application source and it is not a trash folder.

## Contents

- `deliverables/`: earlier report/paper versions retained for traceability.
- `diagnostics/`: historical patches, status captures, meeting references, and preparation snapshots.
- `experiments/`: terminated, excluded, or diagnostic experiment records, including the Sprint-6 Qwen candidate history.

## Rules

- Do not import or deploy code directly from `archive/`.
- Do not use an archived paper/report as the current deliverable; see `docs/DELIVERABLES.md`.
- Do not delete excluded or failed runs. They may explain treatment validity, candidate termination, or later methodological decisions.
- Do not edit archived files to align them with current conclusions.
- Use `repo_cleanup_audit/phase2_execution/archived_files.csv` for original paths, destination paths, sizes, and before/after SHA-256 verification.
- If historical material is reactivated, copy it into a new explicitly versioned work area only after review; preserve the archived original unchanged.

All 38 Phase-2 archive moves were verified with identical pre/post SHA-256 values.

