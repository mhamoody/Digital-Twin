# Comparison evaluation status

## Completed empirical results

- Dataset: `oulad_AAA_2013J_v1`, presentation `oulad:AAA:2013J`.
- Authoritative prepared manifest SHA-256: `fdf7d69b09cffbd25c1ee38a7ec57772fac37f4a0d7d35b14eb425221489c014`.
- 383 source enrolments; 372 learners produced at least one eligible checkpoint state; 11 had no eligible state.
- 1,464 states: week 3 = 371, week 5 = 368, week 8 = 365, week 10 = 360.
- Restricted outcomes are joined only in the research evaluation layer. At-risk states = 352; not-at-risk = 1,112.

## E1 Logistic Regression

Executed with learner-grouped train/validation/test splits (seed 42), train-only standardisation and fitting, validation-F1 threshold selection, and a fixed test report. Results are in `evaluation/results/e1_logistic_oulad_AAA_2013J_v1.csv`; feature separation is recorded in `e1_feature_manifest.json`.

| Checkpoint | AUROC | Average Precision | Threshold |
|---|---:|---:|---:|
| Week 3 | 0.621 | 0.379 | 0.25 |
| Week 5 | 0.657 | 0.531 | 0.41 |
| Week 8 | 0.896 | 0.819 | 0.49 |
| Week 10 | 0.834 | 0.802 | 0.58 |

These are baseline test metrics, not LLM results and not calibrated probabilities.

## E4 Temporal safety

Completed from the artifact's actual activity and assessment provenance rows. 194,590 provenance rows across checkpoints 3, 5, 8, and 10 were checked; 0 cutoff violations were found. Result: `evaluation/results/e4_temporal_oulad_AAA_2013J_v1.csv`.

The checkpoint time follows the canonical builder's fixed demo calendar (`checkpoint_week * 7 - 1`). The prepared replay calendar is synthetic and is not treated as historical calendar evidence.

## Still blocked / not executed

E2 held-out Qwen grounding, E3 missingness, E5 course policy, E6 workflow, and E7 efficiency remain unexecuted. No Qwen inference, calibration, production query, or runtime change was performed.
