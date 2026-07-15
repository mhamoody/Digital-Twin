# 06 — Workflow

## Phase 0 — Planning & Exploration (current phase)

Sequence, per the supervisor's explicit instruction: **Data discovery → Data understanding → Define requirements → Explore models → (gate) → Build initial prototype → Improve gradually.** The team is currently at the discovery/exploration stage of this sequence — none of the Phase 1 build work has started.

| Task | Owner | Deadline | Notes |
|---|---|---|---|
| Public dataset search (LMS activity, learning analytics, engagement, clickstream, questions, assessment) | Mohamed Hassan | End of week 2 | Directional per Meeting 2 — Hassan focuses on data sourcing; not a final assignment, meeting captions were unclear on exact ownership |
| Digital-twin literature review (fundamentals, application domains, educational digital twins, prior datasets/models/architectures) | Team (shared) | End of week 2 | Feeds `01_problem.md`; supervisor is separately sending relevant papers — see open item below |
| Target data schema creation | Mohamed Abdel Majid, Arwa, + other teammates | End of week 3 | Directional per Meeting 2 — this group focuses on requirements/planning/models; feeds `05_architecture.md` |
| Dataset-vs-schema comparison, gap documentation | Mohamed Hassan (data) + Mohamed Abdel Majid/Arwa (schema owners) jointly | End of week 3 | Feeds `05_architecture.md`; every gap needs a stated handling decision, not just a note that it exists |
| System requirements definition (functional + non-functional) | Mohamed Abdel Majid, Arwa, + other teammates | End of week 4 | Must be written **before** any model evaluation begins, per the supervisor's explicit sequencing |
| Candidate model identification + compute estimation | Mohamed Abdel Majid, Arwa, + other teammates | End of week 4 | Feeds `04_stack.md`; includes the open-weight compute estimate specifically because the supervisor flagged this as a real constraint |
| PoC protocol design (confusion 1–7, misunderstanding classification, gap explanation) | Team (shared) | End of week 4 | Protocol only — running it against real candidates is a gate criterion below, not a Phase 0 task in itself |
| Review supervisor-provided papers/resources once received | Team (shared) | Within 1 week of receipt | Open item — see below; cannot be scheduled precisely until the materials arrive |
| Moodle sandbox stood up | Whoever owns the pipeline/infrastructure sub-task | End of week 2 | Carried over unchanged from the team's original draft — this is infrastructure setup, not a Phase 1 build task, since it supports the Phase 0 schema/gap-comparison work as much as anything downstream |

## Gate criteria — what must be true before Phase 1 starts

1. The target data schema (`05_architecture.md`) is finalized and has not changed in a way that invalidates the dataset comparison.
2. At least one dataset gap has been fully mapped and its handling decision has been accepted by the team (not just proposed) — in practice this means the OULAD/MOOCPosts gap-resolution plan in `03_solution.md` has been reviewed and agreed on, not merely drafted.
3. System requirements (`04_stack.md` / `05_architecture.md`) are signed off by the team as the basis for model evaluation.
4. The PoC model test has actually been run — not just designed — against at least the two first-round candidates named in `04_stack.md` (Claude Sonnet 5 and Llama 3.1 8B Instruct), with results compared honestly against the classical-ML baseline from `03_solution.md`.
5. A model has been chosen for Phase 1 based on the PoC results and the requirements — at that point, and only at that point, does `04_stack.md`'s "provisional shortlist" language get updated to a real decision.

Phase 1 does not start on any fixed calendar date — it starts when these five conditions are met, even if that is later than the original week-6 target in the team's draft plan.

## Phase 1 — Build (future, starts only after the gate above is passed)

The refined 14-week plan from the original draft, kept intact but explicitly re-dated as starting from the Phase 0→1 gate, not from week 1 of the calendar:

| Sub-goal (from the original 14-week draft) | Target (weeks *after* the gate, not calendar weeks) |
|---|---|
| Sandbox live (carried forward — already targeted in Phase 0, confirmed working before gate) | Pre-gate (Phase 0) |
| Sync job achieving <60 min lag | Gate + 3 |
| Schema holds for 12+ weeks (validated in a simulated run) | Gate + 4 |
| At-risk classifier cross-validated on OULAD | Gate + 4 |
| LLM forum-classification vs. human-coded labels ≥75% agreement | Gate + 7 |
| Dashboard shell | Gate + 6 |
| AI recommendation panel | Gate + 8 |
| Instructor usability check | Gate + 9 |
| Full pipeline live 4+ consecutive weeks | Gate + 11 through Gate + 15 |
| Evaluation report | Gate + 16 |

If the gate is passed close to the original week-6 target, this schedule lands close to the original 14-week draft; if the gate takes longer (e.g., because a PoC result forces a model reconsideration, or because dataset access to Stanford MOOCPosts takes longer than expected — see `05_architecture.md`'s access-process note), the whole Phase 1 schedule shifts later rather than compressing to protect the original calendar date. This is the concrete way this document "shows the phase gate explicitly," per the supervisor's instruction, rather than just listing a build timeline.

## Working responsibility split (directional, not final)

Per Meeting 2, meeting captions were unclear on exact assignment, so this is treated as directional:
- **Mohamed Hassan** — identifying data sources/datasets.
- **Mohamed Abdel Majid, Arwa, and other teammates** — system requirements, planning, candidate models, and implementation approach.

This split should be revisited once Phase 0 is further along and it's clearer where the actual workload is concentrating.

## Open items — owners, deadlines, and why they can't be resolved yet

| Open item | Owner | Deadline | Why it's open |
|---|---|---|---|
| Model PoC test (run, not just designed) | Team (shared) | Gate criterion — target end of week 4–5 | Depends on the requirements and schema work finishing first, per the supervisor's required sequencing |
| Academic credits — whether Queen's School of Computing has an existing Azure OpenAI / Anthropic academic agreement | Whoever has the department contact (unassigned as of this document) | End of week 2 | `OWNER: unassigned` — this needs someone to actually ask the department; it is not something that can be resolved by research alone |
| University resource-request process (compute/hosting/model access) | `OWNER: unassigned` | As soon as the supervisor shares details | Explicitly `OPEN — pending supervisor` per Meeting 2 — the supervisor said more detail is coming and this cannot be guessed at |
| Supervisor's incoming papers (digital twin fundamentals, prior educational digital twin work, datasets/models/architectures from past studies) | Team (shared) | Within 1 week of receipt | Cannot be scheduled precisely until the supervisor actually sends them; the literature review in `01_problem.md` should be revisited once they arrive in case they surface sources this document's independent search missed |
| Anthropic Claude Campus program reopening (affects whether student API credits are realistically available) | `OWNER: unassigned` | Monitor `claude.com/programs/campus`; recheck by week 3 | Applications are closed for the current cohort as of July 2026 with no announced reopening date — not something the team can force |
| OpenAI Researcher Access Program application (up to $1,000 in API credits) | `OWNER: unassigned` | Submit by end of week 3 | This is a concrete, actionable item — unlike the items above, this one just needs someone to do it, so it's flagged here as a deadline rather than a pure external dependency |
