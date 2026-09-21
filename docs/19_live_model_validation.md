# Direct Qwen validation: September 20–21, 2026

## Purpose and boundaries

Diagnose the repeated Lobot pauses with the real deployed model, not simulated
responses. Tests use frozen synthetic snapshots in an isolated process; they do
not write learner assessments, spend production queue attempts, resume courses
or alter the source data. Raw diagnostic captures are synthetic-only and private.

Model: `qwen2.5:7b`; pinned digest:
`845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e`.
Temperature 0, seed 42, context 8,192 tokens, output budget 1,200 tokens. The
application still uses one initial generation and at most one validated correction.

These are operational validation results, **not predictive accuracy**, calibration,
fairness or intervention-effectiveness results. Scenario-family labels never enter
the model prompt and are not numeric Risk score targets.

## Confirmed failure and correction

At deployment commit `587e4f4`, the API, dashboard, model runtime and worker were
running. Four courses retained protective pauses from earlier validation failures;
the worker was idle, not demonstrably overloaded. ED220 had 1,920 current queued
checkpoints. A ready model and queued work do not override a course pause.

The original failed ED220 snapshot passed an isolated v3.0 replay on its first
generation. Expanding to a frozen test exposed remaining semantic defects:

| Original v3.0 check | Count |
|---|---:|
| Actual model cases: complete / missing grades | 12 / 12 |
| Accepted on first generation | 15 |
| Accepted after one correction | 2 |
| Rejected after correction | 7 |
| Additional partial/stale cases stopped before inference | 24 |
| Generation attempts, including corrections | 33 |
| JSON/schema rejections | 0 |
| Unsupported-risk / mismatched-evidence generation rejections | 15 / 1 |

Thus model-case acceptance was 17/24, not 41/48: the latter includes 24
application-generated abstentions. `scripts/evaluate_workspace.py` now reports
these denominators separately and deprecates its ambiguous legacy schema metric.

Direct captures confirmed a missing-grade case returned score `0.45`, selected
only `RECENT_ACTIVITY`, and recommended `no_action`; its correction repeated the
same answer. Another break-week case returned `0.68` with on-track assessment and
grade claims only. One correction omitted an ID from a two-feature claim.
These are conflicting judgments/citations, not harmless formatting differences.

Prompt v3.1 keeps the model, weights, numerical score range, one-correction limit
and independent validators unchanged. It changes:

1. Evidence selection precedes score generation.
2. Each decoding alternative binds a complete claim to its exact evidence list.
3. A per-snapshot concern summary and final consistency reminder distinguish
   uncertainty from observed problems. Unsupported judgment calls for abstention,
   not invented evidence or a server-adjusted score.

The evidence-first instruction experiment alone accepted 23/24 model cases. The
combined candidate accepted 24/24 on the first generation, with no corrections,
model abstentions or final rejections on that same development set. Scores were
not all low: academic-concern cases still received elevated model assessments.
This is a development-set finding, not an independent validation result.

## Independent follow-up

A frozen seed-2028 check covers 36 base snapshots across the same twelve scenario
families, three courses and rotating checkpoints. Complete and missing-grade
variants produce 72 model cases; partial/stale variants add 72 pre-inference
checks. The numeric histories differ from the development set; the scenario
families and generator are shared, so this is not unseen-family validation.

The isolated v3.1 candidate accepted 69/72 model cases: 68 first-pass, one corrected,
and three finally rejected (two unsupported-risk, one unsupported-action). All 72
partial/stale checks produced pre-inference abstentions. Across 76 generations,
there were no JSON/schema or citation failures, seven grounding/policy rejections,
and no runtime errors. No model-generated abstentions occurred. Median model-case
latency was 5.30 seconds; p95 was 9.30 seconds, including correction when needed.

This v3.1 result did not meet a zero-observed-failure release check. Production
was not resumed on its strength. Do not infer successful validation from the
evaluator's exit code alone.

The same three cases were then replayed directly. Runs varied despite temperature
0 and a fixed seed: exact reproducibility must not be assumed. The persistently
rejected case repeated score 0.45 with only on-track observations. A concise
recheck-system experiment accepted all three (one first-pass and two corrected),
without changing the evidence or weakening validation. The model itself revised
its response; the application did not clip a score or insert a supporting claim.

Candidate `course-risk-qwen-v3.2` retains v3.1 initial generation, uses that shorter
system instruction only for the single permitted correction, and omits rejected
scalars from correction feedback while retaining them in operator traces.

The fresh seed-2029 follow-up accepted **72/72 actual model cases on the first
generation**, with no correction, final rejection, normalization or runtime error.
All **72 partial/stale cases** safely abstained before inference. Model-generated
abstentions were zero. Seed 2028 is now development evidence, not an untouched
holdout for this correction. The dedicated correction itself was exercised in
the three-case replay above, not in this all-first-pass follow-up.

The final local regression suite passed **282 tests**; Ruff and whitespace checks
passed. Across 5,760 demonstration checkpoints, the conservative initial-request
size peaked at 12,409 characters, below the 13,984-character guard. This is not
an empirical accuracy result or a guarantee of zero failures on future inputs.

## Remaining validity limitations

- Validation proves contract, citation and policy consistency, not the accuracy
  of the chosen risk magnitude. Empirical labeled outcomes and a frozen calibrator
  are still required before calling scores probabilities.
- Missing grades can leave valid submission/activity evidence without revealing
  attainment. A low support assessment is not proof of success; measure model
  abstention/coverage and sensitivity to missingness separately.
- The current completion denominator counts resources released by the checkpoint,
  excluding breaks. It does **not** distinguish mandatory/optional resources or
  completion deadlines. A synthetic learner with strong grades can consequently
  have low resource completion. Do not present this alone as proof of academic
  difficulty. A future data-contract change must add required/optional and
  due-by-checkpoint semantics before claiming that distinction is modeled.
- Concern thresholds constrain publishable support levels. They do not constitute
  independent ground truth for eventual non-success. Evaluate false reassurance,
  unwarranted escalation and score stability, not just schema acceptance.
- A finite clean run cannot guarantee zero future failures. Invalid responses
  remain withheld, traceable and bounded; protective pauses remain available.

## Reproducible evidence

Private Lobot artifacts (ignored by Git):

- `artifacts/workspace/direct-live-v3-20260920T195748Z/inputs.json`
- `artifacts/workspace/direct-live-v3-20260920T195748Z/report.json`
- The matching `results.csv` contains per-case outcomes and attempt diagnostics.
- Candidate holdout: `artifacts/workspace/direct-v31-holdout-20260921T094725Z/`;
  `inputs.json`, `report.json` and `results.csv` retain its full denominators.
- Final v3.2 holdout: `artifacts/workspace/direct-v32-holdout-20260921T100001Z/`;
  the same three artifact files preserve seed 2029 and its 72/72 model results.

Candidates were loaded into isolated processes from local source, not installed
over running services during evaluation. Prompt `course-risk-qwen-v3.2` identifies
the final protocol. The result's `input_hash` identifies its initial request;
the versioned `RECHECK_SYSTEM` identifies its correction instruction. Deployment
commit and operational rollout are recorded separately from these test results.

Relevant source:

- `src/digital_twin/workspace/output_contract.py`: exact decoder alternatives.
- `src/digital_twin/workspace/llm.py`: prompt v3.1 and independent validation.
- `scripts/evaluate_workspace.py`: frozen inputs and denominator-labeled metrics.
- `scripts/inspect_model_failure.py`: bounded, read-only saved-case replay.
- `src/digital_twin/workspace/features.py`: resource completion denominator.
- `src/digital_twin/workspace/synthetic.py`: generated demonstration trajectories.

No shared links, browser credentials, tokens, private captures or database files
belong in the repository. Existing empirical records and instructor history remain
untouched by these isolated model experiments.
