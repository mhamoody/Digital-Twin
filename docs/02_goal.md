# 02 — Goal

Goals are split into two tiers per the supervisor's phase gate (see `06_workflow.md` for the full sequencing and gate criteria). Phase 0 must be substantially complete before Phase 1 work starts.

## Phase 0 goals (current phase)

| Goal | Concrete completion criterion |
|---|---|
| Digital-twin literature review complete | A written synthesis (feeding `01_problem.md`) covering the concept's industrial origin, at least 2–3 non-education application domains, and at least 4–5 named educational digital-twin sources, with an explicit translation table of which properties map to a course context and which don't. Done when this document exists and has been reviewed by the team — not "when we've read a few papers." |
| Target data schema defined | A schema document (`05_architecture.md`) listing every field the twin needs, each tagged with a status (confirmed available / gap / TBD) against at least the datasets in `02.3`. Done when every field has a status and every dataset has been checked against every field — not just the fields that happen to be easy to find. |
| Dataset comparison complete | Every candidate dataset (OULAD, Stanford MOOCPosts, Moodle sample data, and any other public dataset surfaced during search) is compared field-by-field against the schema, with a named handling decision (exclude / approximate / substitute / simulate) and a reason for each gap. Done when no dataset in this document set is missing this comparison. |
| System requirements defined | A functional and non-functional requirements list (`04_stack.md` / `05_architecture.md`) derived from the schema, available data, and the four proposal objectives — written *before* any model is selected. Done when every requirement can be traced back to a specific data field or proposal objective. |
| Candidate model shortlist + PoC protocol designed | At least 3–4 candidate models identified against the requirements (not general capability), with a concrete PoC test protocol (classify conceptual misunderstanding, rate confusion 1–7, generate a one-sentence gap explanation) specified and ready to run against a 20–30 post hand-labeled sample. Done when the protocol is written and at least two candidates are named for the first test round — running the PoC itself is a Phase 0→1 gate criterion, not a Phase 0 goal (see `06_workflow.md`). |
| Moodle sandbox stood up | A local or cloud Moodle instance is running and reachable by the team, seeded with at least placeholder course structure. Done when the team can log in and see a course shell — this was targeted for week 2 in the original draft and is unchanged here (see `06_workflow.md`). |

## Phase 1 goals (future build — the four proposal objectives, sharpened with concrete thresholds)

These reuse and sharpen the team's original 14-week sub-goals. Numbers are not new inventions — they come from the team's own working draft — but are now explicitly gated behind Phase 0 completion rather than tied to calendar week numbers.

| Proposal objective | Measurable Phase 1 goal | Success threshold (from the team's own draft, sharpened) |
|---|---|---|
| 1. Real-time LMS → digital twin data pipeline | Sync job moves new engagement/grade/forum data from the Moodle sandbox into the digital twin database on a schedule | Sync lag under 60 minutes end-to-end; schema holds without breaking changes for 12+ consecutive simulated weeks |
| 2. LLM-based analytics + at-risk prediction | LLM classifies forum/short-answer text (confusion, urgency, one-line gap explanation); a simple classifier (e.g., logistic regression) flags at-risk students from structured data | At-risk classifier cross-validated on OULAD's own `final_result` labels, reported honestly against the dataset's known limitations (see `02.7` in the research notes and `05_architecture.md`); LLM forum classification reaches ≥75% agreement with human-coded labels on a held-out sample, **and** is explicitly benchmarked against the classical-ML baseline established in `02.5` (~0.88 F1 for AdaBoost, ~0.90–0.92 F1 for BERT-based approaches on Stanford MOOCPosts urgency/confusion — see `03_solution.md`) rather than assumed to win by default |
| 3. Instructor dashboard + AI recommendations | A working dashboard shell showing per-student risk indicators and time trends, plus an AI-generated recommendation panel | Dashboard shell functional by the target build week; recommendation panel added once the classifier and LLM layer are validated; an instructor usability check is run before the panel is considered done |
| 4. Pilot evaluation over one semester | The full pipeline runs unattended against the sandbox (or, if approved in time, a real course) for a sustained stretch, and a written evaluation report is produced | Pipeline live and stable for 4+ consecutive weeks; evaluation report includes the explicit "done" definition below |

## Explicit definition of "done" for the pilot

The Phase 1 pilot is a **success** if, by the end of the evaluation period:
1. The sync pipeline ran for at least 4 consecutive weeks without a schema-breaking failure.
2. The at-risk classifier's cross-validated performance on the chosen dataset is reported honestly (including known dataset limitations — module/year coverage, generalization caveats), not just as a headline accuracy number.
3. The LLM forum-classification layer reaches its ≥75% agreement threshold against human-coded labels **and** its performance relative to the classical-ML baseline is reported plainly, even if the LLM does not outperform the baseline — a result showing the LLM is *not* clearly better than a cheaper classical model is still a valid, useful outcome of the evaluation.
4. The dashboard and recommendation panel pass a basic instructor usability check (the instructor can find a flagged student and understand why they were flagged, without a walkthrough).
5. The evaluation report documents what worked, what didn't, and explicit future-work recommendations, per the original proposal's deliverables list.

The pilot is **not** a failure if the LLM underperforms the classical baseline, if a dataset gap had to be handled by exclusion rather than simulation, or if the university resource-request process (see `06_workflow.md`) turns out to gate real-course access until after this pilot — those are exactly the kinds of honest findings the phase-gated, exploration-first approach is designed to surface rather than paper over.

## Explicit non-goals

Carried forward from the original proposal, plus one added per Meeting 2:
- Complex physical/multi-physics simulation of learning.
- Multi-course scaling.
- Adaptive content generation for students.
- External tutoring system integration.
- **Using Queen's internal student data before it is formally approved.**
