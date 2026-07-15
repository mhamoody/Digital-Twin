# 04 — Stack

> **Candidate stack — shortlist pending PoC and requirements sign-off, not a final commitment.** Per the supervisor's guidance, model selection follows data and requirements work, not the other way around. Every choice below is the team's best current option given free-tier/education-credit realities as of July 2026 (all pricing verified by live search on that date) — treat all of it as reviewable once the PoC in this file's model section is actually run.

## LLM / model candidates (provisional — shortlist for PoC, not a final pick)

Four candidates, sized against the requirements in `05_architecture.md`: one frontier commercial tier, one cheaper/faster commercial tier, and at least one open-weight option specifically because the supervisor flagged compute/hosting as a real constraint, not just cost.

| Candidate | Tier | Pricing (per million tokens, as of July 2026) | Context window | Compute/hosting footprint | Education/free-credit path | Rejected because... |
|---|---|---|---|---|---|---|
| **Claude Sonnet 5** (Anthropic) | Frontier-adjacent, price/performance | $2 input / $10 output introductory through Aug 31, 2026; $3/$15 standard after | 1M tokens | None — hosted API, no local compute needed | Anthropic runs a "Claude Campus" program (Builder Clubs, cohort-based) and a broader Claude for Education initiative, but as of July 2026 Claude Campus applications are closed for the current cohort with no announced reopening date, and there is no confirmed Queen's-level Claude for Education agreement — this is the open item flagged below, not a guess | — (currently the lead candidate for the PoC's "frontier" slot, precisely because it doesn't need to be rejected on cost at this project's volume) |
| **Claude Haiku 4.5** (Anthropic) | Cheap/fast | $1 input / $5 output | 200K tokens | None — hosted API | Same open item as above | Rejected as the *sole* model (not from the shortlist) because its lower cost isn't yet proven necessary at this project's token volume — the frontier tier is affordable enough that we don't need to make the cheap tier carry the whole workload; it stays shortlisted as the "cheaper tier" PoC candidate |
| **GPT-5 mini** (OpenAI) | Cheaper commercial tier | $0.25 input / $2.00 output | 400K tokens | None — hosted API | OpenAI's Researcher Access Program grants up to $1,000 in API credits to university-affiliated research projects — a real, applicable path for this specific capstone, not a guess (application not yet submitted; see `06_workflow.md`) | Rejected as the frontier-tier candidate in favor of Claude Sonnet 5 mainly on ecosystem grounds (the team already needs an Anthropic account for the Sonnet 5 PoC leg, and consolidating both PoC legs on fewer vendors reduces setup overhead); GPT-5 mini stays shortlisted as a second cheap-tier comparison point |
| **Llama 3.1 8B Instruct** (Meta, open-weight) | Open-weight | $0 in raw model cost; inference cost is the team's own compute or a pay-per-token hosted-inference bill | 128K tokens | Runs in 16-bit on ~1x A100/L40-class GPU; runs in 4-bit quantization on an 8GB consumer GPU (e.g. an RTX 3060) at usable speed, or via Hugging Face's free/PRO Inference Providers | Hugging Face's free serverless Inference tier explicitly lists Llama 3.2 8B / Mistral 7B-class models as suitable for prototyping (rate-limited); HF PRO is $9/month and adds daily ZeroGPU H200 minutes plus monthly inference credits, well within a student budget if the free tier proves too rate-limited | — (this is the required open-weight candidate; kept in the shortlist specifically because the supervisor flagged compute/hosting resources as a constraint independent of dollar cost, and this is the only candidate the team could run entirely without a paid API if credits fall through) |
| ~~Mistral 7B~~ (considered, not shortlisted) | Open-weight | $0 raw / self-hosted | 8K–32K depending on variant | Comparable footprint to Llama 3.1 8B (~14GB VRAM at FP16, ~3–4GB at 4-bit quant) | Same Hugging Face path as Llama 3.1 8B | Rejected in favor of Llama 3.1 8B as the *single* open-weight PoC candidate to keep the PoC round small (two models per `02.5`'s protocol) — Llama 3.1 8B was picked over Mistral 7B mainly because its larger native context window (128K vs. Mistral's 8K–32K) gives more headroom if the PoC prompt needs to include several forum posts of context at once; this is not a strong preference and Mistral 7B is a reasonable second open-weight candidate if Llama underperforms |

**PoC protocol and which two candidates go first:** reusing and sharpening the team's existing protocol — classify conceptual misunderstanding, rate confusion 1–7, generate a one-sentence gap explanation — run against a 20–30 post hand-labeled sample, scored against both inter-rater agreement with the human labels and the classical-ML baseline established in `03_solution.md` (~0.88–0.92 F1 on the closest published equivalent task). **Claude Sonnet 5 and Llama 3.1 8B Instruct should be tested first**: Sonnet 5 as the strongest zero-shot commercial candidate at an affordable price point, and Llama 3.1 8B because it is the required open-weight test and the one candidate whose viability is not just a cost question but a genuine capability question (can an 8B open-weight model match a frontier model's judgment on a nuanced, low-label-volume classification + explanation task?). If both underperform the classical baseline meaningfully, GPT-5 mini and Haiku 4.5 are the second-round candidates.

## Backend language/framework

**Candidate: Python (FastAPI)** — justification: the sync pipeline, classifier, and LLM-calling code all naturally live in Python given the team's assumed ML/AI-agent skill background; FastAPI is lightweight enough for a 3–4 person team to stand up an API layer without a heavy framework learning curve.
Rejected alternative: **Node.js/Express** — rejected because it would fragment the stack (Python for ML work, Node for the API) with no clear benefit at this scale, adding integration overhead the team doesn't have time for.

## Database

**Candidate: Supabase (managed Postgres)** — free tier gives a dedicated Postgres instance, 500MB database storage, 1GB file storage, and unlimited API requests, with 2 active projects allowed per account (verified July 2026). This is enough for a single-course, single-semester pilot's structured data (student records, engagement summaries, assessment scores, forum post metadata).
Rejected alternative: **self-hosted Postgres on a free-tier VM** — rejected because it adds ops overhead (backups, uptime, patching) the team doesn't have bandwidth for; Supabase's managed free tier removes that burden at no extra cost for this project's scale. Caveat carried into the cost table below: Supabase free projects **pause after 1 week of inactivity** and the free tier has **no automatic backups** — both need a mitigation (a scheduled keep-alive ping, and a lightweight backup script) once the pipeline is live for real.

## LMS platform + integration method

**Candidate: self-hosted Moodle (Docker-based local instance)** — justification and specific option confirmed by search: the `moodlehq/moodle-docker` repository (Moodle developer-maintained) or the newer, simpler `mutms/demo` community demo-builder (`git clone` + `bin/init-moodle`, live locally within minutes, with backup/restore scripts for reproducibility) both give the team a persistent, seedable Moodle instance — unlike Moodle's own official public demo/sandbox, which **resets to blank every hour** and is explicitly unsuitable for a research project needing persistent, growing data over weeks.
Rejected alternative: **Moodle's public hosted demo/sandbox** — rejected specifically because of the hourly reset, confirmed directly on Moodle's own demo site documentation.
Integration method: Moodle's REST web services API (standard, well-documented) for the sync job to pull engagement, grade, and forum data on a schedule.

## Prediction/ML library

**Candidate: scikit-learn** — justification: the at-risk classifier is explicitly scoped as a "simple classifier" (logistic regression per the team's own draft and `02.7`), and scikit-learn is the standard, well-documented tool for this at a 3–4 person team's skill level.
Rejected alternative: **a deep learning framework (PyTorch) for the classifier itself** — rejected as overkill for a logistic-regression-scale task; PyTorch may still be used indirectly if the team ends up running an open-weight LLM candidate locally, but not for the structured-data classifier.

## Dashboard framework

**Candidate: Streamlit** — justification: fastest path for a small team to build an interactive, data-driven instructor dashboard in Python without a separate frontend build step, and it deploys for free via Streamlit Community Cloud from a public GitHub repo.
Rejected alternative: **a React + Flask/FastAPI custom frontend** — rejected for Phase 1 as unnecessary engineering overhead given the team's size and timeline; revisit only if Streamlit's customization ceiling becomes a real blocker during the build phase (flagged as a possible future-work item, not a current decision).

## Hosting for each component

| Component | Candidate | Cost/footprint | Rejected alternative + reason |
|---|---|---|---|
| Moodle sandbox | Local Docker instance on a team member's machine (or a small free-tier VM if persistent uptime is needed beyond dev/testing) | $0 in the Docker case; if a persistent cloud VM is needed, Azure for Students' $100/12-month credit (see below) covers a small VM comfortably | A paid managed-Moodle host — rejected as an unnecessary cost at this project's scale |
| Backend / sync pipeline | Render free web service tier or a small Azure for Students-funded VM | $0 (Render free tier spins down on inactivity, acceptable for a scheduled-job pipeline) or drawn from the $100 Azure credit | A paid always-on server — rejected until Phase 1 proves the free/low-cost tier is actually insufficient |
| Database | Supabase free tier (see above) | $0, with the inactivity-pause caveat noted above | A paid managed Postgres (e.g. Supabase Pro at $25/month) — rejected for now as unnecessary at pilot data volumes (500MB free tier is generous for one course, one semester) |
| Dashboard front end | Streamlit Community Cloud | $0 | A paid hosting platform — rejected as unnecessary |

## Cost / resource table (estimated, assuming free tiers where available)

| Item | Estimated cost/footprint | Exposure if credits/free tier fall through |
|---|---|---|
| LLM PoC (2 candidates × 20–30 posts × short prompts) | Well under $1 in API spend at either Sonnet 5 or GPT-5 mini rates; effectively $0 for the open-weight Llama 3.1 8B leg run on free HF Inference or a team member's own GPU | Negligible — this is a small enough token volume that even standard (non-education) pricing is trivial |
| Phase 1 pilot-scale LLM usage (one semester, one course, forum-post + short-answer classification volume) | Rough order-of-magnitude estimate: a few hundred posts/answers per week × ~500–1,000 tokens each in + a short structured output ≈ well under 1M tokens/week even at generous estimates — at Sonnet 5 pricing this is a few dollars per week at worst, likely under $50 total for the semester at Sonnet 5 rates, and near-$0 at Haiku 4.5 or open-weight rates | If Anthropic/OpenAI credits don't come through, this is still a small enough absolute dollar figure to be personally affordable to a student team as a backstop — but should not be assumed; see open item below |
| Compute for open-weight fallback (Llama 3.1 8B) | $0 if run via Hugging Face's free Inference tier (rate-limited) or a team member's existing 8GB+ GPU with 4-bit quantization; $9/month if HF PRO is needed for reliability | Low — this is the specific reason the open-weight candidate is in the shortlist at all |
| Database (Supabase free tier) | $0 | Low at this data scale; upgrade path is $25/month if the 500MB limit is hit |
| Hosting (Render/Streamlit free tiers) | $0 | Low; both have documented free tiers suitable for this project's traffic |
| Azure credit backstop | $100 available per verified student for 12 months via Azure for Students (confirmed active July 2026, redeemable via `azure.microsoft.com/free/students`, includes access to Azure OpenAI for eligible students) | This is a real, currently-available backstop for hosting or model access if the primary free tiers are insufficient |

## Open items — not guessed at

- **The university resource-request process** the supervisor mentioned (for compute, hosting, or model access) is `OPEN — pending supervisor`. It has not been shared with the team as of this document, and no assumption is made here about its form, timeline, or what it covers.
- **Whether Queen's School of Computing already has an Azure OpenAI / Anthropic academic agreement** is unresolved (carried over from the team's working draft) — this must be checked directly with the department, not assumed either way.
- **Anthropic's Claude Campus program status**: applications are currently closed for the active cohort as of July 2026 with no announced reopening date — the team should monitor `claude.com/programs/campus` rather than assume access.
- **OpenAI's Researcher Access Program** (up to $1,000 in API credits for university-affiliated research) has not yet been applied for — this is a concrete, actionable next step, not a decision.
