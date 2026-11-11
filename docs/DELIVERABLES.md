# Deliverables Index

Statuses follow `repo_cleanup_audit/final_preservation/canonical_deliverables_manifest.md`. This index does not change any deliverable.

| Deliverable | Status | Path | Purpose |
|---|---|---|---|
| Supervisor-corrected Master's report (editable) | **Canonical source** | `deliverables/final_report/Final_Revised_Report_Supervisor_Corrected.docx` | Final editable report after supervisor corrections |
| Supervisor-corrected Master's report (rendered) | **Canonical final** | `deliverables/final_report/Final_Revised_Report_Supervisor_Corrected.pdf` | Intended report submission PDF |
| Earlier assembled report | Superseded, retained | `deliverables/final_report/Final_Master_Report.docx` and `.pdf` | Assembly/QA history; not the final authority |
| Final presentation | **Canonical source/final** | `deliverables/final_presentation/Group_12_Course_Digital_Twin_Final.pptx` and `.pdf` | Editable presentation and rendered version |
| Final report figures | **Canonical assets** | `deliverables/final_report_assets/figures/` | Fourteen report figures indexed by `figure_manifest.md` |
| EDUCON abstract | **Canonical final** | `deliverables/educon2027/educon2027_abstract_final.md` | Submitted/accepted abstract text |
| EDUCON abstract review | Supporting audit | `deliverables/educon2027/educon2027_abstract_review.md` | Scientific/editorial audit |
| EDUCON V2 manuscript package | Historical | `archive/deliverables/educon2027/full_paper_v2/` | Earlier supervisor-review version retained for traceability |
| EDUCON V2 response/scientific audits | Supporting audit | `deliverables/educon2027/full_paper_v2/supervisor_feedback_response_matrix.md` and `final_scientific_audit.md` | Maps feedback and verifies V2 claims |
| EDUCON V2 figure source | Retained canonical source for the shared figure | `deliverables/educon2027/full_paper_v2/make_figures.py` | Figure-generation source; do not run against frozen output in place |
| EDUCON V3 manuscript source | **Canonical current paper source** | `deliverables/educon2027/full_paper_v3/EDUCON_2027_Full_Paper_V3.tex` | Current supervisor-review manuscript |
| EDUCON V3 PDF | **Canonical current paper render** | `deliverables/educon2027/full_paper_v3/EDUCON_2027_Full_Paper_V3.pdf` | Current rendered manuscript |
| EDUCON V3 audits | Supporting audits | `deliverables/educon2027/full_paper_v3/v3_revision_report.md` and `v3_scientific_consistency_audit.md` | Revision and quantitative/citation consistency records |
| Phase-1 report body | Historical | `archive/deliverables/phase1/Phase_1_Report_revised_body.tex` | Earlier project-report history |

## EDUCON status wording

Safe current wording: **“Abstract accepted; full paper under review/preparation for submission.”** Do not fabricate a DOI, publication, or full-paper acceptance status. EDUCON V1 was not found during preservation and was not reconstructed.

## Precedence

1. Supervisor-corrected report pair over `Final_Master_Report.*`.
2. EDUCON V3 over V2 for the current manuscript.
3. The preservation manifest over filename assumptions.
4. Supporting audits explain a deliverable but do not replace it.

For exact SHA-256 values, use `repo_cleanup_audit/final_preservation/canonical_deliverables_manifest.md` and `repo_cleanup_audit/phase2_execution/post_cleanup_hash_verification.csv`.

