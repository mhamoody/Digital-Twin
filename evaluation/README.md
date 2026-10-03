# Research comparison framework

This framework is separate from the operational Student Support predictor. Every result row must include experiment_id, git_commit, dataset_version, presentation_id, checkpoint, model_name, model_version, policy_version, seed, data_origin, and run_timestamp. Empirical OULAD and synthetic workspace results are never pooled.

The historical 24 grounding cases are `development` only. A new held-out scenario set must be frozen before E2. Missing Qwen/Lobot access is reported as `BLOCKED BY MODEL ACCESS`; no placeholder metrics are generated.

Initial milestone utilities cover metadata/versioned result files, deterministic splits, binary metrics, cutoff violations, missingness categories, grounding diagnostics, workflow isolation, course-policy pairs, and efficiency summaries.

Planned commands after protocol freeze:

- E1: `python scripts/evaluate_predictive_baselines.py --config evaluation/configs/default.json`
- E2: `python scripts/evaluate_grounding.py --scenarios <frozen-heldout.json> --model <research-adapter>`
- E3: `python scripts/evaluate_missingness.py --config evaluation/configs/default.json`
- E4: `python scripts/evaluate_temporal_safety.py <serialized-features.json>`
- E5: `python scripts/evaluate_course_policy.py --fixture synthetic-v2`
- E6: `python scripts/evaluate_support_workflow.py --scenarios <workflow.json>`
- E7: `python scripts/evaluate_reanalysis_efficiency.py --batch <batch.json>`
- Report: `python scripts/build_evaluation_report.py`
