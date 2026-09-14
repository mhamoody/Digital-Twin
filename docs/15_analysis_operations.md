# Diagnosing pending or failed analysis

A counter such as “22 failed” tells us how many jobs failed, not why. A running
dashboard/API also does not establish that the model worker or Qwen inference is
working. Inspect the stored error-code breakdown before changing model settings.

For the update commands, automatic discovery and all-weeks queue controls, see
[Automatic course analysis and safe catch-up](16_automatic_analysis.md).

## Read-only diagnosis on Lobot

In the JupyterLab terminal, load the application's environment, then run:

```bash
cd ~/Digital-Twin
source .venv/bin/activate
set -a
source .env.lobot
set +a
python scripts/diagnose_analysis.py
```

To inspect one course and retain a new report:

```bash
python scripts/diagnose_analysis.py --course synthetic:CS110:2026A \
  --output artifacts/workspace/diagnosis-first.json
```

The command reads existing tables and bounded model metadata. It does not run a
prediction, initialize a database, retry jobs, change settings, or modify learner
data. It refuses to create a missing SQLite database or overwrite an existing
report. The optional report file is the only write.

The report contains job counts by model kind/status, failures by code, counts per
course and checkpoint, the latest 20 failure job hashes, retry attempt counts,
and latency summaries from successful stored LLM inferences. It omits learner
names/IDs, posts, prompts, raw model responses, account files, credentials, and
environment values. Do not paste `.env.lobot` or instructor account files into
chat as part of diagnosis.

## Reading the result

| Result | Meaning | Next investigation |
|---|---|---|
| `queued` | A job is awaiting an eligible worker | Run `bash deploy/lobot/status.sh`; confirm the worker is running |
| `running` | A worker claimed the job | Allow model load/inference time; inspect whether the lease is progressing |
| `validated` | A returned result passed the application checks | Check the selected checkpoint and policy version in the interface |
| `abstained` | Insufficient evidence or a permitted model abstention | Inspect coverage/freshness; this is not a model-server failure |
| `MODEL_NOT_INSTALLED` | Local service cannot find configured Qwen weights | Check `bash deploy/lobot/model.sh status`; installation is a separate operator action |
| `MODEL_UNAVAILABLE` | Worker could not reach the local model endpoint | Check the model process and its loopback address |
| `MODEL_TIMEOUT` | A model request exceeded the configured time limit | Check available memory/GPU, first-load time, and concurrent work |
| `MODEL_INPUT_BUDGET_EXCEEDED` | Evidence packet exceeds the input budget | Review input size and configured context; do not discard important evidence silently |
| `MODEL_RESPONSE_TRUNCATED` | Model output ended before completion | Inspect output/context budget and structured-output behaviour |
| `MODEL_JSON_INVALID` / `MODEL_SCHEMA_INVALID` | Output was not parseable or failed the contract | Review prompt/schema behaviour using the operational evaluation harness |
| `MODEL_CLAIM_UNSUPPORTED` / `MODEL_EVIDENCE_INVALID` | Claim or citation could not be grounded | Investigate the failed scenario; keep the validation check enabled |
| `MODEL_POLICY_CONFLICT` / `MODEL_ACTION_NOT_SUPPORTED` | Risk/action conflicts with policy or evidence | Inspect course policy and prompt guidance |
| `MODEL_DIGEST_MISMATCH` / `MODEL_DIGEST_CHANGED` | Model identity differs from the expected queued version | Verify the installed version; rerun using an explicitly selected matching model |
| `ANALYSIS_INTERNAL_ERROR` | Unexpected worker error | Inspect operator logs locally and report the error class safely |
| `workspace_tables_missing` | Workspace migrations/initialization are absent | Check the deployment upgrade step before attempting inference |

`model_readiness.status=ready` means the configured model is listed by the local
service. It does not prove a prediction succeeded or that the inference worker is
running. Successful inference latency is reported only when an actual stored
result records `inference_performed=true`; abstentions and rules outputs do not
become fictitious model-timing measurements.

Counts include persisted historical jobs. A failed job for an old model/policy
version can coexist with a later success. Compare the course, checkpoint, version,
and recent timestamps before concluding that the current learner view failed.

## After identifying the cause

Correct the particular operational problem, then request analysis again through
the instructor interface. The queue supports explicit retry of failed jobs; keep
the original error evidence. Restarting everything or replacing rejected LLM
results with rules scores would obscure the cause.

For a controlled, separate behaviour check:

```bash
python scripts/evaluate_workspace.py --llm --limit 12 \
  --output-dir artifacts/workspace/evaluation-qwen-first
```

That command performs real local Qwen inference on a reserved synthetic seed and
records schema, grounding, abstention, and latency results. It reports model
unavailability rather than inventing LLM output. Its findings measure operational
behaviour under fictional scenarios, not academic-risk accuracy or calibration.
