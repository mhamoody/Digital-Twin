# Repository Map

This map describes the checkout after the verified Phase-2 cleanup. “Safe to modify” assumes the contributor has read `CONTRIBUTOR_SAFETY.md` and is not overwriting frozen evidence.

| Path | Purpose | Active/archived | Research-critical? | Safe to modify? | Notes |
|---|---|---|---|---|---|
| `src/digital_twin/` | Python application, API, state, persistence, workspace, fallback dashboard | Active | Yes for methodology/workflow source | With tests and review | Do not conflate demo predictor with E1 or Qwen |
| `frontend/` | React/TypeScript/Vite instructor workspace | Active | No direct research-result authority | Source: yes; `dist/`: manual review | `dist/` was intentionally preserved during cleanup |
| `tests/` | Current scoped Python regression suite | Active | Supports workflow/framework verification | Yes | Preserved baseline: 66 passed |
| `scripts/` | Data preparation, empirical ingestion, workspace/runtime operations | Active | Some scripts are research-critical | Carefully | Never point mutating scripts at production or frozen databases |
| `migrations/` | SQL/Alembic schema history through workspace/support/triage revisions | Active | Supports workflow provenance | Additive review only | Do not rewrite applied migration history |
| `deploy/` | Lobot and VM deployment/backup helpers | Active operational | Indirect | With operator review | Environment-specific and not a public-deployment claim |
| `docs/` | Current guides plus dated project/runbook history | Mixed | Some claim-boundary documents are important | Yes, respecting precedence | Dated documents may contain stale commands |
| `artifacts/evaluation/sprint5-aaa-2013j-v1/` | Local frozen/supporting E1 cohort, states, labels, validation records | Frozen evidence | **Yes** | **No** | Create a new version for new experiments |
| `artifacts/` (other) | Operational and historical artifacts | Mixed | Often | Only after classification | Consult preservation manifest first |
| `deliverables/final_report/` | Canonical and superseded Master's report files | Deliverable | **Yes** | **No casual edits** | Supervisor-corrected pair is canonical |
| `deliverables/final_presentation/` | Final presentation source/render | Deliverable | Yes | No casual edits | PPTX source and PDF render are canonical |
| `deliverables/educon2027/full_paper_v3/` | Current supervisor-review EDUCON paper | Deliverable | **Yes** | Versioned editorial work only | Do not overwrite with V2 content |
| `deliverables/educon2027/full_paper_v2/` | V2 supporting audits/source elements retained after archival move | Historical/supporting | Yes | No | Complete historical package is under `archive/` |
| `deliverables/final_report_assets/` | Canonical report figures and source screenshots | Deliverable | Yes | No casual edits | Indexed by its figure manifest |
| `deliverables/supervisor_sources/` | Supervisor/source documents retained for traceability | Protected | Yes | No | May contain non-public material |
| `archive/` | Historical papers, reports, diagnostics, meetings, excluded/terminated experiments | Archived | Sometimes | **No** | Not trash; see `archive/README.md` |
| `repo_cleanup_audit/preservation_phase/` | Evidence maps and hash manifests | Audit/frozen | **Yes** | **No** | Primary preservation index |
| `repo_cleanup_audit/final_preservation/` | Verified archives, recovered historical source, environment lock, DB copies | Audit/frozen | **Yes** | **No** | Contains restricted material; do not publish wholesale |
| `repo_cleanup_audit/phase2_execution/` | Cleanup inventory, verification, tests, and final reports | Audit/frozen | Yes | No | Documents authorized cleanup outcome |
| `var/data/` | Local SQLite/runtime databases | Runtime/manual review | Potentially | **No casual mutation** | Three listed DBs remain under manual review; Lobot DB is critical |
| `var/auth/` | Local grants/authentication configuration | Sensitive runtime | No research claim authority | **No; secret-safe handling only** | Never print or commit values |
| `.env` | Local runtime environment configuration | Sensitive runtime | No | **No; manual review** | Never publish values |
| `.vscode/` | Local editor configuration | Local/manual review | No | User-controlled | May contain machine-specific paths |

## Modification rule

When uncertain, locate the path in `repo_cleanup_audit/preservation_phase/cross_repository_evidence_map.csv` and `repo_cleanup_audit/final_preservation/archive_content_manifest.csv`. If it is hash-bound, frozen, canonical, archived, or a database, stop and create a versioned copy only after explicit approval.

