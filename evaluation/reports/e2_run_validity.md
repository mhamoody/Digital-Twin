# E2 protocol validity

- `lobot-e2-v1-r1`: diagnostic only — parsing semantics defect.
- `lobot-e2-v1-r2`: diagnostic only — held-out target/reference leakage.
- `lobot-e2-v1-r3`: diagnostic only — leakage-free generation, but v1 had category-only inputs and insufficient validator/reference semantics.

E2 v2 is a controlled held-out grounding ablation. It evaluates structural compliance, evidence-reference discipline, deterministic evidence/policy consistency, selective abstention, and correction effectiveness. It is not an empirical student-performance dataset and does not establish predictive accuracy, causal correctness, universal hallucination rates, or real-world generalization.

The first clean v2 Lobot run is `lobot-e2-v2-r1`.

## v2 hash metadata correction

The initially recorded v2 canonical hash (`300636...`) was incorrect. Direct LF-normalized hashing of the unchanged protocol bytes at both the creation and validator commits produced `6E423F63884145AD00273CF26C65B155C1EC11E3E62A1080C94F74DC807CDD0D`. No live v2 model run occurred before the correction. Protocol bytes and semantic content were not modified; this is an integrity metadata correction, not a protocol revision.

## `lobot-e2-v2-r2` status

The preserved r2 generation is clean and leakage-free: 48/48 model calls completed, all responses were JSON-parseable, and behavior scoring is valid at 24/48 (0.50) because `plain_llm` never abstained. The original r2 citation, semantic, and constraint summary fields are not final because diagnostic persistence, summary aggregation, and missing-feed condition scoring were incomplete in that runner revision. Raw responses are retained and can be deterministically rescored offline with `scripts/rescore_e2_v2.py`; no new model generation is required.
