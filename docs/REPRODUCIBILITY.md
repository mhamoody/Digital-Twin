# Reproducibility Guide

This guide describes the environment and checks validated during preservation and post-cleanup verification. It does not authorize rerunning frozen experiments or mutating databases.

## 1. Supported Python

- Validated interpreter: **Python 3.11.16**.
- Project metadata permits Python `>=3.11,<3.14`, but other versions were not part of the preserved exact rebuild.
- The historical root `.venv` was intentionally deleted after validation.

## 2. Reconstruct the environment

The exact pip-compatible lock is:

`repo_cleanup_audit/final_preservation/environment_validation/candidate_requirements.lock`

PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r repo_cleanup_audit\final_preservation\environment_validation\candidate_requirements.lock
$env:PYTHONPATH="$PWD\src"
```

The lock contains 66 exact third-party distributions. The validated rebuild matched all 66 with zero missing, extra, or version-mismatched packages. It intentionally excludes the local editable package; current source is supplied with `PYTHONPATH`. Package-file hashes were unavailable from installed metadata, so this is reproducible with documented platform differences rather than a claim of byte-identical wheels.

Evidence:

- `repo_cleanup_audit/final_preservation/environment_rebuild_validation.md`
- `repo_cleanup_audit/final_preservation/environment_validation/dependency_diff.md`
- `repo_cleanup_audit/phase2_execution/post_cleanup_test_results.md`

## 3. Run the scoped tests

```powershell
$env:PYTHONPATH="$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider --basetemp="$env:TEMP\digital-twin-pytest" tests
```

Preserved baseline: **66 passed, 0 failed, 0 errors** with two third-party deprecation warnings. Run explicitly against `tests/`; broad discovery below the repository would also collect preserved historical tests inside audit extracts and is not the validated current-suite command.

## 4. Safe import validation

Avoid importing `digital_twin.dashboard.app` as a bare diagnostic because its Streamlit entry-point code expects a session. A representative non-mutating check is:

```powershell
$env:PYTHONPATH="$PWD\src"
.\.venv\Scripts\python.exe -c "import digital_twin.api.auth, digital_twin.dashboard.client, digital_twin.dashboard.support_view, digital_twin.persistence.store, digital_twin.state.builder, digital_twin.workspace.contracts; print('safe_imports_ok')"
```

Do not start workers, inference, ingestion, migration, or workspace preparation as an import test.

## 5. Locate research artifacts

- Index and scientific boundaries: `docs/RESEARCH_EVIDENCE_GUIDE.md`.
- Active/supporting E1 freeze: `artifacts/evaluation/sprint5-aaa-2013j-v1/`.
- Cross-repository map: `repo_cleanup_audit/preservation_phase/cross_repository_evidence_map.csv`.
- Canonical evidence manifest: `repo_cleanup_audit/preservation_phase/canonical_research_evidence_manifest.md`.
- Preserved sibling evidence: `repo_cleanup_audit/final_preservation/archive_verification_extract_A/research_evidence/Digital-Twin-evaluation/`.

## 6. Verify SHA-256 evidence

Use the existing post-clean manifest; do not edit expected hashes:

```powershell
$rows = Import-Csv repo_cleanup_audit\phase2_execution\post_cleanup_hash_verification.csv
$failures = foreach ($row in $rows) {
    if (-not (Test-Path -LiteralPath $row.current_verified_path -PathType Leaf)) {
        "MISSING: $($row.current_verified_path)"
    } elseif ((Get-FileHash -LiteralPath $row.current_verified_path -Algorithm SHA256).Hash -ne $row.expected_sha256) {
        "MISMATCH: $($row.current_verified_path)"
    }
}
if ($failures) { $failures } else { "All $($rows.Count) protected artifacts match." }
```

The preserved baseline is 112/112 pass, covering E1, E2, E4, operational/workflow evidence, canonical deliverables, database copies, and archives A/B.

## 7. Figure generation

The EDUCON E1 figure source is `deliverables/educon2027/full_paper_v2/make_figures.py`; compilation without execution was validated:

```powershell
.\.venv\Scripts\python.exe -m py_compile deliverables\educon2027\full_paper_v2\make_figures.py
```

Do not run it in place because its current output is frozen. To revise a figure, first create an explicitly approved new paper/version directory, copy the source into that version, and preserve the new input/output hashes. The Master's report figure PNGs are canonical assets; this checkout does not claim a complete automated regeneration pipeline for all of them.

## 8. Frozen experiments

Do not casually rerun or overwrite:

- E1 frozen cohort, split, model, or results;
- E2 v2 protocol or valid run/rescore artifacts;
- E4 archived audit result;
- operational LLM snapshot;
- terminated Sprint-6 records;
- SQLite database copies used for preservation.

Any new execution requires a new versioned output directory, immutable configuration/protocol copy, seeds, runtime/model identity, raw outputs, and a new hash manifest.

## 9. Known reproducibility limits

- Raw OULAD CSV files are not retained in the main repository. Full E1 regeneration requires documented reacquisition of the public dataset.
- Frozen evidence is sufficient to verify reported claims, but not every historical execution can be reproduced bit-for-bit.
- Canonical E1/E2/E4 evaluation source and results originated in a sibling evaluation repository; verified preservation copies are local, while the recovered source remains historical rather than merged into the active application.
- Ollama/model files and Node are external to the Python lock.
- Operational evidence depends on a restricted historical database snapshot and recorded extraction, not a public raw dataset.
- Platform-specific wheels may differ even when package versions match.

