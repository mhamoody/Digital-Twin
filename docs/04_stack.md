# 04 — Technology stack and selection rules

The infrastructure is intentionally conventional, while the primary modelling
component is a capable LLM. Research value comes from testing that model on
temporally valid, provenance-aware student states with reproducible baselines,
calibration, and grounding controls—not from building custom infrastructure.

## Selected MVP stack

| Layer | Selection | Status and rationale |
|---|---|---|
| Language | Python | Shared ecosystem for data preparation, modelling, API, and dashboard |
| Data processing | pandas; optional Polars only if profiling proves a need | OULAD-scale processing does not justify distributed infrastructure |
| Primary model | One selected strong hosted or feasible open-weight LLM through a provider-neutral adapter | Core risk prediction and grounded evidence reasoning |
| Structured ML | scikit-learn; one supported gradient-boosting library if needed | Baselines, calibration, metrics, and comparison experiments—not the target model |
| Evidence analysis | Evidence-ID validation and controlled LLM input ablation; SHAP for compatible baselines | Tests whether outputs remain grounded without claiming generated prose is causal explanation |
| Counterfactuals | DiCE-ML | Stretch dependency; do not install or integrate until MVP acceptance criteria are secure |
| Twin store | PostgreSQL with migrations | Versioned, relational storage for observations, states, predictions, evidence, alerts, and feedback |
| LMS sandbox | Moodle on Laragon/MySQL or MariaDB | Already running locally with a test course, assignments, pages, files, sections, and a forum |
| LMS integration | Moodle web services/API; controlled export as fallback | Avoid direct writes to `mdl_*` tables; direct reads are for inspection only |
| API | FastAPI with generated OpenAPI schema | Thin boundary around ingestion status, state, prediction, alert, and review services |
| Dashboard | Streamlit | Fastest route to a Python-only research dashboard; custom frontend is unnecessary for the MVP |
| Packaging | Docker Compose after the local path is stable | Useful for reproducibility; must not delay the already-working Laragon sandbox |
| Tests/quality | pytest, schema/migration tests, linting, CI | Leakage, provenance, and contracts require automated checks |
| Version control | Git with reviewed pull requests | Documentation, schema, and evaluation changes stay traceable |

Moodle's operational MySQL/MariaDB database and the PostgreSQL twin store must remain separate. Moodle owns LMS behaviour; PostgreSQL owns the normalized research state and analytical history.

## Deliberately excluded from the MVP

- Kafka, Spark, or other streaming/distributed systems: scheduled micro-batches are sufficient.
- Kubernetes and production orchestration: unjustified for one course and one semester.
- A React or mobile frontend: Streamlit covers the required instructor workflows.
- A vector database: the primary LLM receives a selected structured weekly state;
  no open-ended retrieval is required.
- Training a foundation model from scratch. Parameter-efficient fine-tuning may
  be tested only if prompt-based use of the selected strong model is inadequate
  and a leakage-safe training protocol is feasible.
- Multiple model providers in production: use one adapter and one selected
  strong provider/local model, with a deterministic fallback always available.

## Baseline shortlist

The experiment should remain small:

1. majority and/or prevalence baseline;
2. activity-only and grade-only transparent baselines;
3. regularized logistic regression;
4. at most two of random forest, histogram gradient boosting, or XGBoost/LightGBM.

These models establish how much value the LLM adds. They do not replace the
LLM as the intended project model. If a baseline performs better, report that
result and restrict deployment claims rather than redefining the research goal
after seeing the test set.

## Strong-LLM adapter, not a fixed provider

The code should expose a provider-neutral interface such as:

```text
predict_risk(validated_weekly_state, prompt_version) -> validated_risk_result
```

The final proposal listed GPT, Claude, and open-weight Llama-family models as
candidates. Those names are examples, not architecture. The selected model must
be strong enough for the primary prediction task; a small/cheap model may be
included as an efficiency baseline but must not silently become the target
model. Availability, pricing, context windows, and university credits must be
confirmed at proof-of-concept time.

“Strong” means the team's explicitly approved high-capability model tier, chosen
before the untouched test evaluation and pinned by provider, exact model/version,
configuration, and access date. A silent fallback to a mini/lite model is not an
equivalent experiment; any downgrade is a separately named baseline or failed
primary-model run.

### Candidate evaluation

Evaluate the selected strong model on the frozen empirical protocol. Optionally
compare one smaller/cheaper or feasible open-weight model as an efficiency
baseline. Score:

- schema-valid output before and after one repair attempt;
- evidence-reference precision and coverage;
- unsupported-claim rate;
- correct abstention on incomplete or contradictory input;
- compliance with the allowed-action list;
- latency and failure rate;
- cost and data-governance suitability; and
- predictive quality relative to classical baselines and the deterministic fallback.

The chosen model must support reliable structured output or constrained
decoding. If it does not improve on the baselines, the scientifically honest
outcome is a negative LLM result and a restricted prototype—not a claim that
basic ML was the intended goal.

## Configuration and secrets

- Store secrets in environment-specific secret management or an ignored `.env` file; commit only `.env.example`.
- Never put real student identifiers, raw text, database dumps, API tokens, or model-provider keys in Git.
- Use pseudonymous identifiers in the twin store and dashboard.
- Keep provider, model, prompt, feature, and dataset versions in normal database columns rather than only in logs.
- Pin dependencies with a lock file or fully resolved requirements once the first vertical slice works.

## Deployment profiles

| Profile | Purpose | Components |
|---|---|---|
| Developer | Individual feature work | Local Python environment, PostgreSQL, fixtures; Moodle may be shared or local |
| Integrated demo | End-to-end replay and presentation | Existing Laragon Moodle, PostgreSQL, FastAPI, Streamlit, selected strong LLM or clearly labelled deterministic fallback |
| Reproducible package | Assessment hand-off | Dockerized application/database where practical, seed/replay command, migration and test commands, documented Moodle setup |

Public cloud deployment is optional. If used, access control and institutional privacy rules take precedence over convenience or free-tier pricing.

## Resource decisions still open

- Whether Queen's provides approved compute, hosted-model access, or cloud credits.
- Whether any external model may receive even anonymized educational text under the applicable terms.
- Whether Docker or Laragon is the final documented Moodle setup; Laragon is the current working implementation.
- Whether a supplemental dataset later passes the re-entry gates in
  `08_data_strategy.md` for a separately reported external evaluation. This is
  not an MVP dependency and must not imply row-level merging with OULAD.

These items need named owners and dates in `06_workflow.md`; they must not be silently assumed.
