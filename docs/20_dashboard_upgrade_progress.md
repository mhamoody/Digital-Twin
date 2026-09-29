# Dashboard upgrade — durable implementation checkpoint

## Resume here

- Approved: all ten items in the instructor's dashboard-upgrade plan.
- **Phase 1 is locally validated; deployment and real hosted verification now authorized.**
- New user instruction: each phase follows build → local test → deploy → verify
  the real dashboard/model before proceeding. Phase 2 may start after Phase 1
  passes its hosted gate. Preserve this sequence at future interruptions.
- No deployment, database mutation on Lobot, or Git push has been performed.
- Baseline source commit: `e725db5`, branch `agent/align-strong-llm`.
- Deployment integration base: `51b7e9b` (fast-forwarded newer team work without
  overwriting Phase 1 or unrelated local edits). Combined local run: 333 passed
  plus 6 subtests; one upstream empirical-fixture test cannot run here because it
  hard-codes a missing `G:` drive dataset. Its importer is not part of this rollout.
- Dedicated hosted browser connection restored; user signed into instructor
  dashboard. Preflight: original hosted commit e725db5; API/UI/worker reachable;
  Qwen digest 845dbda0ea48ed749caafd9e6037047aa19acfcfd82e704d7ca97d631a0b697e.
  Original courses are active; CS110 has 5 historical validation failures, other
  courses are fully assessed at v3.2. Do not misreport those as new v3.3 outcomes.
- Existing user edits to preserve: README.md, docs/02_goal.md,
  docs/05_architecture.md, docs/08_data_strategy.md, and the untracked
  docs/11_text_analysis_evaluation.md. Do not stage or rewrite them.

## Approved scope and progress

| Item | Deliverable | Phase | Status |
|---|---|---|---|
| 1 | Teaching-style presets, explicit inactivity monitoring control, visible policy | 1 | Locally complete |
| 2 | Required/optional/due resource semantics; assessed versus practice grades | 1 | Locally complete |
| 3 | Quick manual flag, watchlist and instructor priority separate from model score | 2 | Not started |
| 4 | Name + ID / ID-only privacy view, with authorized name mapping only | 2 | Not started |
| 5 | Actionable overview, direct student opening, practical filters and sorting | 2 | Not started |
| 6 | Compact student summary, clear score comparison, evidence-first profile | 2 | Not started |
| 7 | Easier support recording, explicit planned/completed, action versus evidence dates | 2 | Not started |
| 8 | Clear refresh/queue/retry controls and compact analysis status | 3 | Not started |
| 9 | Desktop/tablet/mobile polish and locally scrollable wide tables | 3 | Not started |
| 10 | Demonstration of quiet/high-grade, practice, extension, missing-feed and support cases | 3 | Not started |

## Phase 1 design decisions

- Existing policy fields, snapshots, predictions and instructor history remain
  readable. New policy fields have backward-compatible defaults.
- Teaching-style presets are editable starting points, not inferred evidence.
  Disabling inactivity must not generate a protective claim or weaken data-quality
  gates. Missing/partial essential streams still cause explicit abstention.
- Qwen remains the primary predictor. Strict grounding, bounded correction,
  missing-value rules and unchanged model scores remain authoritative.
- Resource completion concerns require explicit required status and a known due
  date available at the checkpoint. Unknown metadata must not become an obligation.
- Practice remains visible as practice, not a summative grade concern. Unknown
  classification must not be silently relabelled as assessed work.
- New feature semantics and changed prompts receive new versions. Existing results
  are never relabelled or overwritten. Legacy ambiguous completion/grade evidence
  must not be represented as newly verified required/assessed evidence.
- Revised synthetic courses use a new source namespace. Never regenerate new
  definitions over immutable existing course/event IDs or empirical OULAD records.

## File ownership during the current work

- Root: this checkpoint; dashboard UI; settings/API/store integration; docs;
  integration, browser and final regression checks.
- Feature subtask: workspace/features.py, workspace/synthetic.py and focused
  feature tests. No other source edits without coordination.
- Policy/model subtask: workspace/contracts.py, workspace/llm.py, a small policy
  preset helper, and focused policy/model tests. No dashboard/store edits.

## Validation gate

1. Test policy defaults, presets, save/reload/versioning and course authorization.
2. Confirm disabled inactivity cannot create inactivity claims or implicit success.
3. Confirm optional/future/unknown resources do not become missed required work.
4. Confirm practice grades cannot create assessed-grade or trend concerns.
5. Preserve cutoff, publication, extension, missingness and old-result safeguards.
6. Run existing workspace, reliability, output-contract and UI regressions.
7. Check prompt size and version identity; keep local/fake transport checks
   distinct from real Qwen inference.
8. Show isolated screenshots/scenario results and list any unverified live checks.

## Last completed step / next action

2026-09-29: resumed without restarting the investigation. Implementation now exists
for policy presets and disabling inactivity, rich-features-v3 academic/resource
semantics, synthetic-education-v2 IDs, prompt v3.3 and rules-baseline-v3, plus
settings/profile/academic UI. Root also exposed checkpoint-available assessment
definitions in Store.learner. Nothing has been deployed or committed.

Final local gate (2026-09-29): **268 tests passed, plus 6 subtests**. Lint passes
for changed production Python files and `git diff --check` reports no whitespace
errors. Existing dependency deprecation warnings remain; they are not test failures.
An independent read-only semantic review found no blocking issues.

Real Qwen v3.3 inference is **NOT yet verified**. Historical v3.2 live results
must not be reused as evidence for this new prompt. No Git commit, push, live
database change, or deployment has been made during this phase.

## What can now be reviewed

- Course settings: select a teaching-style starting point, copy it into the form,
  adjust it and explicitly save. Selecting a preset alone never changes a course.
  A modified preset is labelled custom; saved values remain authoritative.
- Monitoring can be disabled without treating quiet logins as concern or frequent
  logins as reassurance. Grade/required-work evidence and quality checks remain.
- Profiles identify the active course policy; earlier results retain their own
  policy revision. Saving policy increments its revision and requires reanalysis.
- Grade dots distinguish assessed, practice/formative and unclassified work on
  the same 0–100% marks scale. Practice has a separate summary section.
- Required completion means required resources due by that checkpoint. Optional
  and not-yet-due items are separate; unknown metadata is unavailable, not failure.
- New synthetic generator/course/event IDs prevent collisions with existing
  imported v1 evidence. New snapshot semantics are `rich-features-v3`; old stored
  snapshots keep their original versions and values.

## Verification evidence and commands

```powershell
python -m pytest tests/test_workspace_data.py tests/test_workspace_evidence_v3.py tests/test_workspace_policy_v3.py tests/test_workspace_llm.py tests/test_workspace_pipeline.py tests/test_workspace_phase1_integration.py tests/test_workspace_security.py tests/test_workspace_migration.py tests/test_workspace_evaluation_reliability.py tests/test_output_contract.py tests/unit/test_workspace_ui.py tests/unit/test_workspace_phase1_ui.py -q --disable-warnings
python tests/check_phase1_prompt_budget.py
python tests/check_dashboard_phase1_browser.py
```

- API tests cover course authorization, strict boolean validation, policy
  persistence, optimistic conflicts, unchanged saved results and cutoff-bounded
  assessment definitions. UI tests cover draft versus saved settings, preset
  editing, invalid-input recovery, practice classification and historical labels.
- Budget check: 5,760 synthetic snapshots under monitoring-on/off policies;
  maximum initial input 13,106 characters and correction input 12,089 against
  the existing 13,984-character guard. This is not tokenization or inference.
  The old budget helper was corrected to measure the actual correction-specific
  system message, not incorrectly reuse the longer first-pass message. The
  runtime limit was not raised and no evidence was truncated to pass it.
- Browser check: isolated in-memory database with fictional data; desktop
  1440×1080 and mobile 390×844. Both new views render; document width equals
  viewport width on mobile. Wide tables scroll internally. Fixed the header
  overlap that clipped the first label; shortened the grade-axis title.
- Evidence files: `artifacts/dashboard-upgrade-phase1/browser-check.json`,
  `prompt-budget.json`, and screenshots `01-course-settings-desktop.png`,
  `02-academic-evidence-desktop.png`, `03-academic-evidence-mobile.png`,
  `04-course-settings-mobile.png`, `05-practice-required-resources-desktop.png`.
  All preview processes were stopped after testing.
- Tests, preview harnesses, artifacts and planning files remain locally ignored,
  respecting the existing repository policy. This tracked document preserves the
  status and exact validation commands; do not force-add ignored materials.

To inspect the isolated preview manually (no live accounts or Qwen required):

```powershell
python -m streamlit run tests/preview_dashboard_phase1.py --server.address 127.0.0.1 --server.port 18502
```

Open `http://127.0.0.1:18502`. Changes in this preview are temporary in-memory
settings, not the production database.

## Next handoff

1. User approved deployment and hosted verification on 2026-09-29. Restore the
   dedicated browser session, inspect remote Git changes, preserve live database,
   auth and logs, deploy without mass reanalysis, and run a small hosted gate.
   Then implement Phase 2 items 3–7; do not repeat completed investigation.
2. Before deployment, validate v3.3 against actual hosted Qwen on a small, isolated
   scenario set. Record the model digest and results; do not queue a whole live
   course merely to test the prompt. Keep existing output-validation boundaries.
3. Deployment needs explicit preparation: backup, add new v2 synthetic courses
   alongside old data, authorize the new presentation IDs for test instructors,
   and check policy/result version handling. Do not overwrite old source IDs or
   remove histories. Neither SQL migration nor stored output schema change is
   required for these additive JSON fields.
4. Preserve the pre-existing unrelated edits listed at the top. New source file
   `src/digital_twin/workspace/policy.py` and this checkpoint are untracked until
   a later scoped commit; do not omit them when preparing that commit.
