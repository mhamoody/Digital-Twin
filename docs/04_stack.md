# 04 — Technology stack and selection rules

The stack is intentionally conventional. The research value should come from temporal validity, provenance, calibration, and evaluation—not from building custom infrastructure.

## Selected MVP stack

| Layer | Selection | Status and rationale |
|---|---|---|
| Language | Python | Shared ecosystem for data preparation, modelling, API, and dashboard |
| Data processing | pandas; optional Polars only if profiling proves a need | OULAD-scale processing does not justify distributed infrastructure |
| Structured ML | scikit-learn; one supported gradient-boosting library if needed | Covers baselines, calibration, metrics, and a small candidate set |
| Explanations | SHAP | Core local feature-attribution mechanism for the selected model |
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
- A vector database: the MVP LLM receives selected structured evidence; no open-ended retrieval is required.
- Fine-tuning or training an LLM: prompt/schema evaluation is adequate for the constrained role.
- Multiple model providers in production: use one adapter and one selected provider/local model, with the template fallback always available.

## Structured-model shortlist

The experiment should remain small:

1. majority and/or prevalence baseline;
2. activity-only and grade-only transparent baselines;
3. regularized logistic regression;
4. at most two of random forest, histogram gradient boosting, or XGBoost/LightGBM.

Selection is based on checkpoint performance, calibration, stability across module presentations, interpretability, and runtime. A slightly weaker but well-calibrated and stable model may be preferable to a complex model with a marginal headline improvement.

## LLM adapter, not a fixed provider

The code should expose a provider-neutral interface such as:

```text
render_explanation(validated_evidence, prompt_version) -> validated_explanation
```

The final proposal listed GPT, Claude, and an open-weight Llama model as candidates. Those names are examples, not architecture. Model availability, pricing, context windows, and university credits change; confirm them at the time of the proof of concept rather than encoding dated claims in the design.

### Candidate evaluation

Compare at most one hosted small/efficient model and one feasible open-weight model on the same frozen cases. Score:

- schema-valid output before and after one repair attempt;
- evidence-reference precision and coverage;
- unsupported-claim rate;
- correct abstention on incomplete or contradictory input;
- compliance with the allowed-action list;
- latency and failure rate;
- cost and data-governance suitability; and
- quality relative to the deterministic template.

The chosen model must support reliable structured output or constrained decoding. If no candidate adds clear value over the template, the scientifically honest outcome is to retain the template and report the negative result.

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
| Integrated demo | End-to-end replay and presentation | Existing Laragon Moodle, PostgreSQL, FastAPI, Streamlit, selected model or template fallback |
| Reproducible package | Assessment hand-off | Dockerized application/database where practical, seed/replay command, migration and test commands, documented Moodle setup |

Public cloud deployment is optional. If used, access control and institutional privacy rules take precedence over convenience or free-tier pricing.

## Resource decisions still open

- Whether Queen's provides approved compute, hosted-model access, or cloud credits.
- Whether any external model may receive even anonymized educational text under the applicable terms.
- Whether Docker or Laragon is the final documented Moodle setup; Laragon is the current working implementation.
- Which accessible Open edX/Moodle dataset, if any, complements OULAD.

These items need named owners and dates in `06_workflow.md`; they must not be silently assumed.
