# Output contract v3: prevent contradictions and make failures inspectable

## Evidence and limits of the diagnosis

The supplied September 15 status report showed 15 current-version validated
results and 16 current-version failed results: 15 schema failures and one course-
policy conflict. OULAD, CS110 and ED220 had each paused after three consecutive
final validation failures. DS210 retained its earlier migrated pause. A live
heartbeat and a ready Qwen service coexisted with an idle worker because all
courses were paused. This is not evidence of GPU overload.

The historical report also contained 3,384 `ANALYSIS_SUPERSEDED` entries. Those are
old queued versions retired without inference, not 3,384 malformed model replies.

The exact old rejected fields cannot be recovered from stored output hashes.
However, local reproduction established a contract defect: the v2.3 decoding
schema admitted combinations that the Python cross-field validator rejected,
such as a high numerical score with a low band, or contradictory abstention
fields. The generic error wrapper also discarded the specific validator reason.
These are confirmed implementation weaknesses, not proof that every historical
failure had the same cause. Live acceptance of the revised prompt must be measured
on Lobot; simulated unit tests cannot supply that finding.

## What the model now returns

Qwen2.5:7B remains the predictor. Prompt `course-risk-qwen-v3.0` asks for exactly
one of two independent object shapes. The same schema is supplied in the prompt
and to Ollama's structured decoder.

Assessment example (illustrative evidence aliases, not an actual learner):

```json
{
  "decision": "assess",
  "risk_score": 0.72,
  "claims": [{"code": "LOW_GRADE", "evidence_ids": ["E001"]}],
  "suggested_actions": ["review_grades"]
}
```

Responsible model abstention:

```json
{"decision": "abstain", "reason": "INSUFFICIENT_CONFIDENCE"}
```

The other permitted model abstention reason is `CONFLICTING_EVIDENCE`. A model
abstention has no score/claims/actions fields. The server still produces the
existing canonical API output, so the dashboard and database do not need a new
student-facing schema. For an assessment the server derives the display band from
the model's **unchanged** score: `<0.35` low, `[0.35,0.65)` medium, `>=0.65` high.
The model no longer generates this duplicate deterministic label. It still
chooses the score, grounded claims, actions and whether to abstain.

An out-of-policy score is rejected, not reduced until it passes. Existing
grounding, action-support, medium/high concern and academic-corroboration checks
remain authoritative. There is no rules-model replacement, invented evidence,
silent claim insertion or calibration claim. A well-formed score may still be
inaccurate; empirical validation remains separate.

The receiver can also read a fully coherent legacy canonical response for
compatibility, but it does not fix contradictory legacy scores/bands or mix
legacy fields into a native v3 response.

## Harmless formatting versus changed meaning

| Receiver behaviour | Boundary |
|---|---|
| Strip one exact JSON Markdown fence | No prose extraction, multiple objects, duplicate keys, comments or trailing text |
| Normalize whitespace/case of a known closed-enum value | No fuzzy synonyms, unknown claims/actions, renamed fields or edited evidence IDs |
| Convert an unambiguous decimal string to a numeric score | No percent interpretation, 75-to-0.75 rescaling, booleans, NaN, clipping or rounding |
| Derive the native response's band | Fixed presentation mapping from an already validated model score, not altered model judgment |

Every normalization is audited separately from a second-generation correction.
Missing required fields, ambiguous text and extra fields remain failures. Do not
weaken these boundaries just to increase the displayed completion counter.

## Exact diagnostics and bounded correction

Generation traces retain sanitized field paths, stable subcodes, fixed expected
conditions, received types and safe scalar values where appropriate. Unknown
field names and arbitrary model text are redacted. Normalizations retain their
path and fixed code, not uncontrolled original text. The current course's failure
panel shows bounded samples; unrelated course records cannot be inspected there.

For example, a legacy score-band conflict can report `score_band_mismatch`,
instead of only `MODEL_SCHEMA_INVALID`. The existing one-correction mechanism
receives the specific trusted field diagnostics plus the unchanged evidence,
policy and schema. It never consumes the previous raw answer as instructions.
Both generations remain independently validated and audited. Service failures
remain distinct from model-content rejection.

New diagnostics do not backfill information that earlier runs discarded. The
operator tool labels that limitation explicitly. Course pauses and attempt
history are preserved; installing this revision does not silently resume courses.

## Missing data is a separate contract

Unknown input values remain null with explicit evidence/coverage status. An
observed zero is not the same as an unavailable measurement. Optional missing
grades can coexist with grounded assessment/activity evidence. Current required-
coverage and freshness gates still return a valid pre-inference abstention when
their requirements are unmet; those are not failed JSON responses or successful
Qwen inferences. This release does not relax those gates to hide output failures.

A future claim-specific sufficiency revision must distinguish reliable positive
observations from absence claims under incomplete ingestion. It needs separate
tests and outcome evaluation; changing a prompt alone cannot make an incomplete
activity export establish that a learner was inactive.

## Deploy, inspect one case, then expand

On Lobot:

```bash
cd ~/Digital-Twin
git pull --ff-only origin agent/align-strong-llm
bash deploy/lobot/update_reliability.sh
bash deploy/lobot/model.sh start
source .venv/bin/activate
set -a
source .env.lobot
set +a
```

The existing additive update procedure preserves the database and makes a backup.
This revision needs no further database migration beyond the existing inference-
trace tables. Because the prompt contract changed, current-version assessments
are separate work; old results are preserved, not represented as new validation.

Inspect the known failed ED220 synthetic job from the supplied report:

```bash
python scripts/inspect_model_failure.py \
  --job e24c92ff1588c7eea8df02c5aa7496c82344e1d79cbb70d2c916fcf0210b4903
```

The default command does not call Qwen, consume queue attempts, save predictions,
resume a course or change data. To run an isolated diagnostic with the current
contract against that saved learner snapshot and its original policy:

```bash
python scripts/inspect_model_failure.py \
  --job e24c92ff1588c7eea8df02c5aa7496c82344e1d79cbb70d2c916fcf0210b4903 \
  --replay --capture-synthetic-output \
  --output-dir artifacts/workspace/schema-case-v3-01
```

The explicit synthetic capture stores the newly generated raw output and prepared
input privately for inspection. It refuses empirical/replayed learner data and
existing output directories. Never commit this folder or paste real learner
records, account files or environment contents into chat. A reproduction uses
the current prompt; it is not recovery of the original historical answer.

The package contains `summary.json` (safe diagnostics), `synthetic_replies.json`
(both new raw generations, if correction was needed) and `prepared_prompt.json`
(the prepared synthetic input and decoding schema). An exit code of `3` means
the diagnostic completed but the response was rejected, not that the script
crashed; `2` means a configuration/read/precondition failure. Share the summary
first. Keep raw captures private and use a new directory name for each run.

Keep courses paused during the first diagnostic. If the model identity differs
from the failed job, inspect that difference before opting into a current-runtime
comparison. A failed or successful diagnostic never changes the instructor record.

Then run a small frozen scenario evaluation in a new output folder:

```bash
python scripts/evaluate_workspace.py --llm --limit 12 \
  --output-dir artifacts/workspace/qwen-contract-v3-01
```

Inspect first-pass and corrected acceptance, normalization/subcode counts,
abstentions, rejection rates and denominators by missingness condition. If other
courses are running, stop the worker safely before measuring isolated latency.
Only after inspecting these outputs should the instructor resume one course;
verify actual queue progress and errors before resuming every course.

## Local verification and remaining live check

All 299 tests in the targeted local regression suite passed. These checks cover
native and legacy contracts, bounded correction,
grounding/policy enforcement, safe diagnostics, course isolation, read-only replay,
privacy restrictions and instructor workflows. Scripted transport responses are
not evidence of Qwen's accuracy or first-pass acceptance rate.

Browser checks passed at 1440, 768, 390 and 360 pixel widths without page-level
horizontal overflow or application exceptions. Automatic status polling issued
only reads, preserved unsaved forms, and left record counts unchanged. A completed
instructor contact saved and reloaded in the isolated synthetic preview.

All 5,760 representative synthetic checkpoints fit the existing conservative
prompt-size screen: maximum 11,446 initial characters and 12,763 correction
characters (including schema and three diagnostic details), below its 13,984
character bound. This heuristic is not a measurement of the model's actual token
count; live runtime token/latency measurements are still needed.

Oversized numeric values and deeply nested malformed JSON are also regression
cases: they must produce controlled rejection rather than crash diagnostics.
No local Qwen weights were available for this verification. Deployment therefore
requires the isolated replay and frozen evaluation above before claiming that
the historical model failures are resolved in practice.

## References and code

Ollama recommends supplying the schema to the decoder and prompt, then validating
the answer independently: [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).
Grammar implementations support a subset of JSON Schema; not every numerical or
cross-field condition is guaranteed by decoding:
[llama.cpp grammar documentation](https://github.com/ggml-org/llama.cpp/blob/master/grammars/README.md).
Pydantic exposes structured field/error details that must be sanitized before
display: [error handling](https://docs.pydantic.dev/latest/errors/errors/).

- Wire schema and receiver: `src/digital_twin/workspace/output_contract.py`
- Prompt, model call, independent validation: `src/digital_twin/workspace/llm.py`
- Safe trace persistence: `src/digital_twin/workspace/tracing.py`
- Current-version diagnostic samples: `src/digital_twin/workspace/scheduling.py`
- Instructor failure details: `src/digital_twin/dashboard/workspace_ui.py`
- Controlled reproduction: `scripts/inspect_model_failure.py`
- Scenario evaluation: `scripts/evaluate_workspace.py`
