# Contributor Safety Guide

This repository combines active product code with frozen research evidence, canonical deliverables, historical archives, sensitive local configuration, and preserved databases. Treat those classes differently.

## Do not

- overwrite frozen CSV, JSON, model, protocol, or result files;
- mutate archived or preservation SQLite databases;
- reuse an existing experiment output directory for a new run;
- edit hash manifests manually to make a mismatch disappear;
- silently replace EDUCON V3 or supervisor-corrected Master's deliverables;
- treat Qwen outputs as E1 predictions;
- call raw risk scores calibrated probabilities;
- merge controlled E2, operational LLM, empirical E1, synthetic, replay, and workflow evidence into one denominator;
- infer motivation, diagnosis, understanding, or causality from LMS traces;
- delete excluded or failed runs without scientific/preservation review;
- rewrite applied migrations;
- print or commit `.env`, authentication, signing, database, or password values;
- run ingestion, migrations, preparation, or tests against production data;
- assume an archived file is disposable because it is no longer active source.

## Do

- create a new, clearly versioned experiment/output directory;
- preserve exact seeds, configurations, split/protocol identity, and code revision;
- record exact model name, digest, runtime, prompt/contract version, and decoding settings;
- preserve raw model output separately from deterministic rescoring;
- write a manifest with SHA-256 values before drawing conclusions;
- keep experimental and operational evidence separate;
- retain failure/abstention records and denominator definitions;
- run the scoped tests before and after product-code changes;
- use disposable databases and explicit course grants for workflow testing;
- review `REPOSITORY_MAP.md`, `RESEARCH_EVIDENCE_GUIDE.md`, and preservation manifests before modifying an unfamiliar path.

## Change patterns

| Intended change | Safe pattern |
|---|---|
| New product feature | Modify active source, add tests, use disposable data, preserve existing workflow history |
| New experiment | New versioned protocol/config/output directory and manifest |
| Paper revision | New paper version or approved editorial update; preserve earlier version |
| Figure revision | Generate into a new approved version; retain source and hashes |
| Migration | Add a new revision; never rewrite an applied revision |
| Runtime validation | Use explicit non-production ports, grants, credentials, and database |
| Cleanup | Re-run preservation classification and obtain explicit destructive approval |

## Claim boundaries

- E1 uses Logistic Regression, not Qwen.
- E1 reports discrimination and is not calibrated.
- E4 reports zero detected post-cutoff timestamps only in its bounded exported-link scope.
- E2 schema constraints improved structural/citation compliance but did not improve behavioral correctness or abstention.
- Operational v3.2/v3.3 records support validation-path reliability statements, not global accuracy or causal superiority.
- Workflow verification is not educator-effectiveness or learner-outcome evidence.
- The Course Digital Twin is checkpointed, not real-time or autonomous.

## Stop conditions

Stop and request review if a change would alter a hash-bound artifact, database, canonical deliverable, protocol, frozen denominator, result, migration history, or sensitive runtime file. A convenient implementation is not authorization to change scientific evidence.

