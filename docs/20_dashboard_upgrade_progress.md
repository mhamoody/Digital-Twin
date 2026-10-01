# Dashboard upgrade — durable implementation checkpoint

## Resume here

- Approved: all ten items in the instructor's dashboard-upgrade plan.
- **All three dashboard-upgrade phases complete (2026-09-30), including local
  tests, deployment, hosted UI verification and actual model-operation checks.**
- New user instruction: each phase follows build → local test → deploy → verify
  the real dashboard/model before proceeding. Phase 2 may start after Phase 1
  passes its hosted gate. Preserve this sequence at future interruptions.
- Deployed on Lobot: `82a1b81` (Phase 3 UI plus course-specific guide correction).
  Initial Phase 3 implementation: `b8039b8`. See evidence below.
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
| 1 | Teaching-style presets, explicit inactivity monitoring control, visible policy | 1 | Hosted gate passed |
| 2 | Required/optional/due resource semantics; assessed versus practice grades | 1 | Hosted gate passed |
| 3 | Quick manual flag, watchlist and instructor priority separate from model score | 2 | Hosted gate passed |
| 4 | Name + ID / ID-only privacy view, with authorized name mapping only | 2 | Hosted gate passed |
| 5 | Actionable overview, direct student opening, practical filters and sorting | 2 | Hosted gate passed |
| 6 | Compact student summary, clear score comparison, evidence-first profile | 2 | Hosted gate passed |
| 7 | Easier support recording, explicit planned/completed, action versus evidence dates | 2 | Hosted gate passed |
| 8 | Clear refresh/queue/retry controls and compact analysis status | 3 | Hosted gate passed |
| 9 | Desktop/tablet/mobile polish and locally scrollable wide tables | 3 | Hosted gate passed |
| 10 | Demonstration of quiet/high-grade, practice, extension, missing-feed and support cases | 3 | Guide and hosted navigation passed; missing-feed tests remain isolated |

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

## Local gate (completed before deployment)

2026-09-29: resumed without restarting the investigation. Implementation now exists
for policy presets and disabling inactivity, rich-features-v3 academic/resource
semantics, synthetic-education-v2 IDs, prompt v3.3 and rules-baseline-v3, plus
settings/profile/academic UI. Root also exposed checkpoint-available assessment
definitions in Store.learner.

Final local gate (2026-09-29): **268 tests passed, plus 6 subtests**. Lint passes
for changed production Python files and `git diff --check` reports no whitespace
errors. Existing dependency deprecation warnings remain; they are not test failures.
An independent read-only semantic review found no blocking issues.

The subsequent hosted gate below verifies actual v3.3 inference. Historical v3.2
results are not counted as evidence for this new prompt.

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

## Hosted gate — 2026-09-29

- Backups are additive, private, and retained on Lobot. Final pre-deployment
  backup: `var/backups/dashboard-phase1-20260929T093042754955Z`. Existing backups
  were not pruned. Exact original-row comparisons and SQLite integrity passed.
- Three v2 synthetic courses were added alongside the original four courses:
  360 fictional learners, 48,517 events, 5,760 snapshots and 120 support events.
  Original empirical/synthetic records, results and histories remain unchanged.
  Only the three new course grants were added to Mohamed's account; existing
  account identities, password hashes and deployment configuration are unchanged.
- Hosted Qwen2.5:7b / prompt `course-risk-qwen-v3.3`: 11 isolated scenarios,
  **9 validated assessments, 2 correct pre-inference abstentions, 0 final failures**.
  One assessment required a bounded correction. These are contract/grounding
  checks on synthetic scenarios, not measured predictive accuracy.
- Three more learner/checkpoint assessments were queued through the signed API,
  processed normally and read back as validated persisted results. A fourth
  validated run confirmed the new saved offline policy. The initial standalone
  smoke-runner authentication failure was fixed by loading the normal deployment
  environment; no authentication or validation checks were weakened.
- Real dashboard: preset remains a draft until Save; save/reload works; old
  assessments become outdated after a policy change. CS110 updated demo now has
  Mainly offline / policy 3 (login inactivity excluded). A same-value save during
  verification created revision 2; no old policy or assessment was overwritten.
- Academic view renders assessed/practice grades and required resources due by
  the checkpoint separately. Desktop and 390px mobile checked, with no document
  overflow or Streamlit exceptions. More mobile polish remains Phase 3 work.
- Evidence (ignored operational artifacts):
  `artifacts/dashboard-upgrade-phase1/hosted-live-results.json`,
  `hosted-ui-settings.json`, `hosted-academic-desktop.png`, and
  `hosted-academic-mobile.png`. Remote signed-API reports are under
  `artifacts/dashboard-upgrade-phase1-20260929T093403Z/`.
- Upstream team work introduced a default **Student support** mode backed by
  legacy v1 support tables. This upgrade is under **Course operations** (rich
  v2 workspace). Phase 2 must preserve both histories, not send v2 IDs into
  legacy support tables or silently remove the upstream workflow.
- Offline mode excludes login evidence, not real academic/resource concerns.
  No claim is made that this always lowers a model score. Five old original-CS110
  v3.2 failures predate this rollout; they are not new v3.3 failures.
- Normal single-inference worker resumed after the gate (PID 55076); API and
  dashboard remained running. Existing course controls are preserved; new v2
  courses have automatic analysis enabled. The version change will cause bounded
  background catch-up. This does not mean all checkpoints are already reanalyzed.

## Phase 2 implementation and local gate

- Manual flags, course-shared watchlist, priority and notes are saved in separate
  versioned triage/audit tables, never as model inputs or altered scores. Writes
  require authorized course membership, optimistic version checks and idempotency
  keys. Removing a flag retains its audit history. A watchlist need not open a case.
- Name + ID uses only the existing authorized roster mapping. ID-only API views
  remove known display-name fields and disable name searches/sorting; free-text
  notes may still identify a person, so this is not anonymization or a new access role.
- Overview counts drill down into server-side filters. Sorting/filtering happens
  before pagination. Active cases include new, reviewed and ongoing. Direct row
  selection opens a profile; returning preserves filters and page.
- Current instructor records are explicitly separate from historical model
  evidence. The API retains cutoff-filtered `case` and adds `current_case`.
  Later actions can cite an earlier checkpoint; new events reference the current
  snapshot revision. A stale UI reference conflicts instead of silently rebinding.
- Planned actions are completed/cancelled by an appended linked record, not by
  rewriting the original. Action day, evidence week/cutoff and recorded time are
  separate. Known calendars prevent future actions being marked completed. Without
  a verified calendar, course-day input is explicitly manual. Follow-up counts use
  a labeled current-calendar or checkpoint reference, never an invented date.
- The rich Course operations workspace becomes the default. Earlier Student
  support remains available with its separate histories, showing only courses
  actually present in that authorized legacy API; service/auth errors still surface.
- Migration `20260929_0007` adds `audit.workspace_triage` and
  `audit.workspace_triage_event`. SQLite pilot initialization creates these
  additively; PostgreSQL uses Alembic. No source/model/history rows are rewritten.
- Local gate: **337 tests + 6 subtests passed**, including existing support-workflow
  regressions. Changed workspace code passes lint and `git diff --check`.
  Isolated browser gate passed flag/watchlist, privacy and later-action scenarios;
  1440px desktop and 390px mobile, no document overflow or UI exceptions.
- New validation: `tests/test_workspace_instructor_phase2.py`,
  `tests/unit/test_workspace_phase2_ui.py`, `tests/unit/test_workspace_routing.py`,
  `tests/check_dashboard_phase2_browser.py`. Screenshot evidence is under
  `artifacts/dashboard-upgrade-phase2/`. These are local/ignored as established.

## Phase 2 hosted deployment checkpoint

- Implementation `fcc275a` pushed to `agent/align-strong-llm` and deployed on Lobot.
  Additive post-stop backup: `var/backups/dashboard-phase2-20260929T173912937545Z`.
  SQLite initialization reports 41 application tables. API, dashboard and worker
  restarted successfully; no dataset reimport, identity reset or log-backup pruning.
- Signed live API gate passed triage save/retry, ID-only/search behavior, filters,
  planned-to-completed audit, and later-action/earlier-evidence separation. The
  selected immutable snapshot and its existing model results were unchanged.
- Fictional demonstration left for inspection: **Foundations of Computing —
  updated demo v2**, learner `synthetic:learner:1:0002`, evidence week **3**.
  Flagged, watchlisted, high instructor priority; an ongoing case contains a
  planned check-in on day 30 and completion recorded on day 32, both citing week 3
  (evidence cutoff day 20). Notes explicitly label the demonstration. No real
  student contact or automated message occurred. Its risk score was not edited.
- Exact SQL comparisons preserved all original source rows, all **15,074** saved
  assessments, all **240** prior workspace support events, automation settings
  and legacy records. Account/config files are unchanged; SQLite integrity is OK.
- At verification, **26 new actual Qwen inferences** had been saved since the
  final backup, using v3.3. Latest saved job was validated. This confirms resumed
  operation, not completion of the entire queue or measured predictive accuracy.
- Evidence: `artifacts/dashboard-upgrade-phase2/hosted-api-gate.json`,
  `hosted-preservation.json` and `hosted-ui-gate.json`. After sign-in, the real
  dashboard passed watchlist drill-down, saved flag/priority, ID-only profile,
  Back with retained filters, current support history and legacy mode navigation.
  Desktop and 390px mobile screenshots inspected; no document overflow or UI
  exceptions. No further data writes were made during the visual gate.

## Phase 3 plan

- Keep the overview compact; put course-wide queue controls behind a clearly
  named expander, with the full diagnostic view still available in Data health.
- Distinguish refreshing saved results from requesting model work. State the
  current scope (one student, selected week, or all weeks), reuse and retry rules.
  Correct the misleading "remains queued" message when no jobs are queued.
- Keep pause/retry/validation safeguards unchanged. Do not change model prompts,
  scores, source data or policy revisions for presentation improvements.
- Wrap long selected labels and provide local scrolling for tab strips and wide
  tables. Verify 390px mobile, 768px tablet and desktop with real browser checks.
- Add a synthetic-only scenario guide: where to inspect quiet/high-grade,
  practice, extension, missing-feed and support examples, and what to verify.
  Scenario design is not an observed result or model input; actual evidence and
  current saved model output remain authoritative.
- Test locally, then deploy and verify the hosted dashboard and actual model
  operation. Preserve all source, model, support, triage and account records.

## Next handoff

1. All approved dashboard-upgrade phases are complete. Do not repeat deployment,
   data import or mutating acceptance scripts. The existing fictional flag/support
   example and scenario guide remain available for instructor inspection.
2. Preserve the unrelated
   edits listed at the top. Do not repeat the completed Phase 1 investigation.

## Phase 3 local checkpoint

- Implemented display-only scenario guide and cross-checkpoint navigation for
  known updated synthetic courses. The authorized API confirms the learner
  exists. Missing-feed checks remain isolated faults, not fictional failures
  inserted into the complete cohort. See `docs/21_instructor_demo_guide.md`.
- Overview's all-weeks analysis controls are collapsed by default. Refresh and
  queue scope/reuse/retry are explained, empty catch-up is disabled, and another
  busy course no longer implies this course has queued work. No scheduler,
  inference, schema, prompt or validation changes.
- Full selected course name remains readable below the selector. Tablet cards
  use two columns; mobile tabs scroll locally and grade legends stack instead of
  clipping. Data health separates manual-priority counts from model statuses.
- Combined local regression: **341 tests plus 6 subtests passed**; changed Python
  lint passed. Browser gate covers 1440px/768px/390px, scenario-to-week navigation,
  reachable final tab, Data health tables and no document overflow/UI exceptions.
  Evidence: `artifacts/dashboard-upgrade-phase3/` and
  `tests/check_dashboard_phase3_browser.py` (ignored operator/test materials).
- The instructor started a course analysis during this phase. Preserve it:
  **do not stop the worker or model, reset the queue, change pauses, or reimport**.
  Online consistent backup: `var/backups/dashboard-phase3-20260929T225117197916Z`.
  Baseline: 18,204 saved analyses, 242 support events, 1 triage record/event.
  Exact old-row preservation, auth/config equality and integrity passed before
  deployment; 11 additional actual Qwen inferences were saved after backup.
- Pushed and deployed `b8039b8`. No service restart: API PID 55179, dashboard
  55180, worker 55181 unchanged. Source reload reset the instructor session;
  the user has been asked to sign in again for the hosted visual gate.
- Post-deployment read-only comparison preserves every original protected row,
  including all 18,204 prior analyses and 242 support events. Auth/config unchanged;
  SQLite integrity OK. Actual Qwen inferences since backup increased from 11 to 57;
  latest was validated, v3.3. Worker/model are healthy. This is operational
  verification, not completion of the queue or an accuracy claim.
- Updated ED220 demo increased from 105 to 128 validated records during checks,
  with zero failures at that point; its remaining work is queued/running. Original
  CS110 has 7 existing failures: this rollout did not retry/reset/hide them.
  These are point-in-time reads, not a frozen cross-course snapshot.
- Evidence: `artifacts/dashboard-upgrade-phase3/hosted-preservation-before.json`
  and `hosted-preservation-after.json`.

## Phase 3 final hosted gate — passed

- After instructor sign-in, `tests/lobot_phase3_ui_gate.py` passed on the real
  dashboard. Verified scenario selection opens the correct learner and earlier
  week, final profile tab is reachable, Data health tables render, and the
  all-weeks analysis panel is collapsed in Overview. No queue/model/data writes.
- Desktop 1440px, tablet 768px and mobile 390px: document width equals viewport
  width; no UI exceptions. Screenshots inspected: grade legend fully readable on
  mobile, two-column tablet cards, local tab/table scrolling and full course-name
  caption. Initial browser automation clicked before a rerun finished; waiting
  for completion resolved it without changing application code or safeguards.
- Evidence: `artifacts/dashboard-upgrade-phase3/hosted-ui-gate.json`,
  `hosted-academic-1440.png`, `hosted-academic-768.png`, `hosted-academic-390.png`,
  `hosted-analysis-controls.png`, and `hosted-preservation-final.json`.
- Final read-only gate again preserved every prior protected row and all
  accounts/configuration; SQLite integrity OK. **165 actual Qwen inferences**
  saved since the Phase 3 backup; latest validated with prompt v3.3. Updated
  ED220 demo reached **182/1,920 validated checkpoint records**, 1,737 queued,
  1 running and 0 failed at the read. These are checkpoint records, not unique
  students. Existing original-CS110 failures remain visible and unchanged.
- No service restarts, extra inference requests, queue resets or pause changes
  were needed. The user's analysis continued. This completes the upgrade gates,
  not the background queue or a predictive-accuracy study.
- Independent final review found a guide-copy mismatch: only DS210 has marked
  practice quizzes. Corrected the guide to distinguish its practice marks from
  CS110/ED220 optional practice resources; learner IDs and model inputs unchanged.
- Correction deployed as `82a1b81` without restarting any process. Five focused
  UI tests passed. Final authenticated browser check confirmed the CS110 optional
  resource wording and DS210 practice-grade wording, then opened DS210 learner
  `synthetic:learner:2:0001` at week 6. No UI exceptions or data writes.
  Evidence: `hosted-guide-final.json` and `hosted-practice-guide-final.png` in the
  Phase 3 artifact directory. No implementation or verification gate remains open.
