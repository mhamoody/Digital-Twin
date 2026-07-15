# 01 — Problem

## What "digital twin" actually means, and where it comes from

The term traces to NASA's Apollo program, where mission engineers built full physical duplicates of spacecraft systems on the ground to rehearse failures in real time — most famously during Apollo 13. The phrase itself was coined later: Michael Grieves proposed the idea at a 2002 product-lifecycle-management conference under the names "Conceptual Ideal for PLM" and "Mirrored Spaces Model," and NASA's Glaessgen and Stargel gave the first widely-cited formal definition in 2012, describing an integrated, multi-physics, probabilistic simulation that uses sensor updates and fleet history to mirror the life of a physical vehicle. From there the concept spread into manufacturing (Industry 4.0, predictive maintenance, digital product lifecycle management), healthcare (patient-specific physiological models), and urban planning / smart cities (city-scale simulations for infrastructure and traffic). Researchers still do not agree on one canonical definition, but the common thread across all of these domains is three parts: a physical entity, a digital representation of it, and a live, bidirectional data connection that lets the digital model update as the physical one changes and, in the more advanced cases, feed predictions or interventions back into the physical system.

Education is a newer application area. A 2024 systematic review across Scopus, Web of Science, ERIC, and PubMed found roughly fifty studies on digital twins and holograms in STEM education (2018–2024), concentrating on spatial reasoning, procedural skill practice, and remote-lab access rather than learning-analytics style prediction. Other recent work proposes architectures for e-learning digital twins that mirror an LMS in a parallel data model (Jankovskis, Cirule & Carbone, 2024), frameworks for real-time, big-data-driven online education ecosystems that continuously capture engagement and instructional-quality signals (EAI Endorsed Transactions, 2026), and course-level systems that supplement instruction in specific disciplines, such as a landscape-architecture "digital twin learning system" evaluated against a control group in engineering education (Appl. Sci., 2024). Overall, the education literature is still exploratory: most papers argue for the *potential* of digital twins in the classroom rather than reporting mature, validated deployments at the scale this project targets.

**Translating the concept to a course + student context — and where the analogy breaks down:**

| Physical-system DT property | Maps to a course digital twin | Translates cleanly? |
|---|---|---|
| Real-time sensor data → live model update | LMS/VLE clickstream, submissions, and forum activity synced into a database on a schedule | Yes — this is the core mechanism this project builds |
| State history over the asset's life | Per-student engagement, grade, and interaction history across the semester | Yes — directly supported by structured LMS data |
| Predictive simulation of future failure states | At-risk classifier + LLM-based interpretation of text, flagging students likely to underperform | Partially — this project predicts risk from patterns, it does not simulate the underlying causal process the way a physics-based digital twin does |
| Bidirectional physical↔virtual actuation (the model can change the physical system, e.g. a machine adjusts itself from twin feedback) | No equivalent — the system can only *recommend* actions to an instructor, who is free to ignore them | No — students are not machines, and there is no automated "actuation" back into a person's behavior. This project deliberately treats every model output as a *recommendation*, never an automated intervention |
| High-fidelity multi-physics simulation of the asset's internal state | Understanding *why* a student is confused or disengaged | No — this project only has behavioral/textual traces, not the underlying cognitive state; any "explanation" of confusion is an inference from text, not a simulation of the student's mind |

The honest framing, then, is that this project builds a **behavioral and engagement mirror** of a course — a synced, queryable, historized data model of what students did and wrote — plus an analytics layer that tries to predict risk and surface explanations from that mirror. It intentionally does not attempt the "simulate and actuate" properties that define the more mature industrial digital twins.

## The real problem

Instructors in large or online-heavy courses only see a fraction of what is actually going on. A student who is quietly falling behind rarely announces it — they stop logging in as often, their forum posts get shorter or more confused, their assignment scores dip a little at a time. Individually, none of these signals is alarming; together, they are a pattern an instructor would recognize instantly if they had the time to look at every student's history every week. They don't. By the time a struggling student is visible through the channels instructors actually have time for — a missed deadline, a failed midterm, a direct email — a meaningful part of the term is already gone, and the intervention options left are late and blunt (extensions, referrals to academic support) rather than early and targeted.

**Who is affected, and what happens today without a system like this:**
- **Instructors** currently rely on gradebook thresholds and their own memory of who has been quiet in forums or lecture. In a course of any real size this doesn't scale, and it systematically favors students who are visibly struggling (failing a graded item) over students who are quietly disengaging (declining logins, unanswered confusion) — the latter group is often what standard grade-based early-warning systems miss entirely.
- **Students at risk** get no signal that anyone has noticed their pattern until a grade consequence has already occurred.
- **TAs**, who are often closest to the forum activity, have no structured way to surface a pattern they notice anecdotally ("a lot of people seem confused about recursion this week") into something the instructor can act on at the class level.

## Constraints that shape everything else

- **Team size and time:** 3–4 students, 3–4 months (~14 weeks), alongside coursework — this rules out building or maintaining novel ML architectures, custom-training large models, or standing up production-grade infrastructure.
- **Pilot scope:** one course, one semester, per the proposal's own scope. Multi-course scaling, adaptive content generation, complex physical simulation, and external tutoring integrations are explicitly out of scope (per the original proposal).
- **Data type:** the system works only with textual and structured engagement data (forum posts, assessment records, clickstream/login logs). No video or audio analysis.
- **No Queen's internal student data at this stage.** Per the second supervisor meeting, real institutional LMS data is likely blocked by privacy/security/research-approval processes at this stage, possibly even for read-only researcher access — the project must not depend on it, and every downstream design decision (dataset choice, sandbox use, evaluation plan) is built around public data instead. Using Queen's data before it is formally approved is an explicit non-goal (see below).
- **LMS realism:** whatever system is built must integrate with a real or realistic LMS (a self-hosted Moodle sandbox, not a bespoke mock), so that the pipeline design generalizes beyond this one project.

## The data gap (stated as a problem to solve, not assumed in advance)

No single public dataset combines everything the proposal's four objectives need. This is confirmed, not assumed: see `05_architecture.md` for the field-by-field comparison, but the shape of the gap is that the strongest structured-engagement dataset available (OULAD) has no free-text forum content at all, while the strongest labeled-forum-text dataset available (Stanford MOOCPosts) comes from different, non-credit MOOCs with no linked structured engagement or grade data for the same students. Any system built on public data alone has to explicitly decide, field by field, how it will bridge that gap rather than assuming a single dataset covers everything — see `02_goal.md` and `03_solution.md` for how this project resolves it.

## Explicit non-goals

- Complex physical or multi-physics simulation of learning (out of scope per the original proposal).
- Scaling to multiple courses simultaneously (out of scope per the original proposal).
- Adaptive content generation for students (out of scope per the original proposal).
- Integration with external tutoring systems (out of scope per the original proposal).
- **Using Queen's internal student data before it is formally approved** through the university's research/privacy process (added per Meeting 2 — this is a hard constraint on the current phase, not a permanent one).
- Automating any action that affects a student directly (e.g., auto-emailing a student, auto-flagging them to advising) — every output in this project's scope is a recommendation surfaced to an instructor, not an automated intervention.
- Treating the LLM's model choice or the system architecture as finalized during this phase — see `04_stack.md` and `05_architecture.md`.
