"""Public failure descriptions; never expose model text, tracebacks or runtime secrets.

``retryable`` means a bounded automatic retry can be useful without changing the
snapshot, prompt or deployment. It is not permission to retry indefinitely.
"""

from __future__ import annotations

from typing import NamedTuple


class Failure(NamedTuple):
    title: str
    detail: str
    action: str
    category: str
    retryable: bool = False


ERRORS: dict[str, Failure] = {
    "ANALYSIS_WORKER_INTERRUPTED": Failure(
        "Worker repeatedly interrupted",
        "The worker lease expired after the maximum number of attempts without a saved result.",
        "Check process restarts and job time limits before a new controlled experiment.",
        "internal",
    ),
    "ANALYSIS_SUPERSEDED": Failure(
        "Newer evidence or settings replaced this queued job",
        "This historical job was not run because a newer snapshot, policy "
        "or approved model applies.",
        "Use the current course-wide analysis status; new evidence is queued separately.",
        "historical",
    ),
    "MODEL_TIMEOUT": Failure(
        "Model request timed out",
        "The model did not finish within the configured time limit.",
        "Allow the scheduled retry; check model load and latency if this repeats.",
        "availability",
        True,
    ),
    "MODEL_UNAVAILABLE": Failure(
        "Model service unreachable",
        "The worker could not reach the local model service.",
        "Check that Ollama is running; a bounded retry can recover a temporary interruption.",
        "availability",
        True,
    ),
    "MODEL_BUSY": Failure(
        "Model service busy",
        "The model service declined the request because it is busy.",
        "Allow the delayed retry; avoid submitting duplicate jobs.",
        "availability",
        True,
    ),
    "MODEL_SERVER_ERROR": Failure(
        "Model service error",
        "The model service returned a server-side failure.",
        "Allow a bounded retry; inspect the operator log if failures repeat.",
        "availability",
        True,
    ),
    "MODEL_OUT_OF_MEMORY": Failure(
        "Insufficient model memory",
        "The model service reported an allocation or memory failure.",
        "The operator must check available RAM/VRAM and model/context settings before retrying.",
        "configuration",
    ),
    "MODEL_NOT_INSTALLED": Failure(
        "Selected model not installed",
        "The required model is absent from the model service.",
        "Ask the operator to install the approved model, then request analysis again.",
        "configuration",
    ),
    "MODEL_ENDPOINT_UNAVAILABLE": Failure(
        "Model endpoint unavailable",
        "The configured local service does not provide the requested endpoint.",
        "Check the Ollama address and runtime version before retrying.",
        "configuration",
    ),
    "MODEL_REQUEST_REJECTED": Failure(
        "Model request rejected",
        "The model service rejected the request format or parameters.",
        "The operator should inspect runtime compatibility and request settings.",
        "configuration",
    ),
    "MODEL_ACCESS_DENIED": Failure(
        "Model service access denied",
        "The model service rejected the worker's access.",
        "Check the private model endpoint configuration before retrying.",
        "configuration",
    ),
    "MODEL_HTTP_ERROR": Failure(
        "Model HTTP request failed",
        "A model request failed; this older error code does not identify the cause.",
        "Check the operator's error summary before deciding whether to retry.",
        "configuration",
    ),
    "MODEL_DIGEST_MISSING": Failure(
        "Model identity unavailable",
        "The installed model did not provide its required digest.",
        "Check the installed model metadata and Ollama version.",
        "configuration",
    ),
    "MODEL_DIGEST_MISMATCH": Failure(
        "Model revision changed",
        "The installed model differs from the revision selected for this job.",
        "Restore the selected revision or explicitly queue a new job for the current model.",
        "configuration",
    ),
    "MODEL_DIGEST_CHANGED": Failure(
        "Model changed during analysis",
        "The model revision changed while this attempt was running.",
        "Keep the model revision fixed and queue a new analysis.",
        "configuration",
    ),
    "MODEL_IDENTITY_MISMATCH": Failure(
        "Unexpected model response",
        "The runtime identified a model different from the requested model.",
        "Check model routing and the approved model configuration.",
        "configuration",
    ),
    "MODEL_KIND_INVALID": Failure(
        "Unsupported analysis type",
        "The stored job does not select a supported analysis type.",
        "Ask the operator to inspect the job configuration.",
        "configuration",
    ),
    "MODEL_INPUT_BUDGET_EXCEEDED": Failure(
        "Evidence exceeds input budget",
        "The evidence package exceeds the configured model context budget.",
        "Review the evidence selection or validated context budget before retrying.",
        "input",
    ),
    "MODEL_INPUT_INVALID": Failure(
        "Evidence failed input checks",
        "One or more model features has an invalid type or value range.",
        "Correct the source mapping or snapshot, then create a new analysis.",
        "input",
    ),
    "MODEL_QUALITY_GATE_FAILED": Failure(
        "Evidence quality is insufficient",
        "The response attempted a score despite insufficient or stale evidence.",
        "Refresh the required evidence before requesting analysis again.",
        "input",
    ),
    "MODEL_RESPONSE_TRUNCATED": Failure(
        "Model response incomplete",
        "The response stopped before a complete result was available.",
        "Review the output token budget and prompt; the incomplete result was not published.",
        "output",
    ),
    "MODEL_RESPONSE_INVALID": Failure(
        "Invalid runtime response",
        "The model service returned a response envelope that could not be validated.",
        "Check runtime compatibility and inspect the operator log.",
        "output",
    ),
    "MODEL_JSON_INVALID": Failure(
        "Model output is not strict JSON",
        "The answer failed strict JSON checks, including duplicate or invalid fields.",
        "Review the model/prompt evaluation; the answer was not published.",
        "output",
    ),
    "MODEL_SCHEMA_INVALID": Failure(
        "Model output failed its contract",
        "The answer has missing, extra, mistyped or inconsistent output fields.",
        "Review the output contract and prompt before running the same case again.",
        "output",
    ),
    "MODEL_CLAIM_UNSUPPORTED": Failure(
        "Unsupported model claim",
        "A claim was duplicated or was not supported by the supplied evidence.",
        "Review the prompt and evidence mapping; do not weaken the grounding check.",
        "grounding",
    ),
    "MODEL_EVIDENCE_INVALID": Failure(
        "Invalid evidence reference",
        "A claim cited unknown, repeated or incorrectly matched evidence.",
        "Review the claim-to-evidence mapping before retrying.",
        "grounding",
    ),
    "MODEL_RISK_NOT_SUPPORTED": Failure(
        "Risk level lacks supporting evidence",
        "The selected support level has no validated concern claim.",
        "Review the model reasoning and evidence; the risk score was not published.",
        "grounding",
    ),
    "MODEL_POLICY_CONFLICT": Failure(
        "Response conflicts with course policy",
        "The proposed support level does not meet the instructor's evidence requirements.",
        "Review policy-aware prompting; the response was rejected rather than silently changed.",
        "grounding",
    ),
    "MODEL_ACTION_INVALID": Failure(
        "Invalid recommended actions",
        "The response contains missing, duplicate or conflicting actions.",
        "Review the action contract and prompt before retrying.",
        "grounding",
    ),
    "MODEL_ACTION_NOT_SUPPORTED": Failure(
        "Recommended action lacks evidence",
        "A recommended action is not supported by the selected claims or risk level.",
        "Review the action-to-evidence requirements; no recommendation was published.",
        "grounding",
    ),
    "MODEL_ABSTENTION_REASON_INVALID": Failure(
        "Invalid abstention explanation",
        "The model did not use an approved reason for abstaining.",
        "Review the abstention instructions; no risk score was published.",
        "output",
    ),
    "ANALYSIS_INPUT_OR_LEASE_INVALID": Failure(
        "Analysis could not be completed",
        "The saved input or worker ownership changed before completion.",
        "Refresh job status and ask the operator to inspect the attempt.",
        "internal",
    ),
    "ANALYSIS_INTERNAL_ERROR": Failure(
        "Analysis processing error",
        "An unexpected processing error occurred before a validated result was saved.",
        "Ask the operator to inspect the job's diagnostic code.",
        "internal",
    ),
    "ANALYSIS_UNKNOWN_ERROR": Failure(
        "Unclassified analysis failure",
        "The saved failure code is not recognized by this application version.",
        "Ask the operator to inspect the job's diagnostic code before retrying.",
        "internal",
    ),
}
SERVICE_BLOCKING_CODES = frozenset(
    {
        "MODEL_TIMEOUT",
        "MODEL_UNAVAILABLE",
        "MODEL_BUSY",
        "MODEL_SERVER_ERROR",
        "MODEL_OUT_OF_MEMORY",
        "MODEL_NOT_INSTALLED",
        "MODEL_ENDPOINT_UNAVAILABLE",
        "MODEL_REQUEST_REJECTED",
        "MODEL_ACCESS_DENIED",
        "MODEL_HTTP_ERROR",
        "MODEL_DIGEST_MISSING",
        "MODEL_DIGEST_MISMATCH",
        "MODEL_DIGEST_CHANGED",
        "MODEL_IDENTITY_MISMATCH",
    }
)

# A single new generation with corrective contract feedback is distinct from
# retrying a failed service request. These errors stay non-retryable at job level.
# No runtime/input/identity/quality failure is included. Values are fixed trusted
# instructions, never arbitrary validation messages or rejected model content.
REPAIR_FEEDBACK: dict[str, str] = {
    "MODEL_JSON_INVALID": "Return one strict JSON object: no markdown, duplicate keys or NaN.",
    "MODEL_SCHEMA_INVALID": (
        "Follow every required field, type and score-band boundary in required_output_schema. "
        "Scored mode requires nonempty claims/actions; abstention requires null score/band, "
        "empty claims/actions and an approved reason."
    ),
    "MODEL_CLAIM_UNSUPPORTED": (
        "Select unique codes only from permitted_claims; copy the exact matched evidence list."
    ),
    "MODEL_EVIDENCE_INVALID": (
        "Each selected code must use exactly its permitted_claims evidence_ids, without repeats."
    ),
    "MODEL_RISK_NOT_SUPPORTED": (
        "The previous medium/high answer selected no eligible concern claim. Protective "
        "observations alone do not justify that level. Reassess evidence and claim_semantics; "
        "do not invent a concern to preserve the previous judgment."
    ),
    "MODEL_POLICY_CONFLICT": (
        "High risk requires a selected academic concern when academic corroboration is required. "
        "Otherwise inactivity-only high risk still requires this course's "
        "high inactivity threshold."
    ),
    "MODEL_ACTION_INVALID": (
        "Use 1 to 6 distinct actions for scored mode, empty actions for abstention. "
        "no_action is allowed only alone at low risk."
    ),
    "MODEL_ACTION_NOT_SUPPORTED": (
        "Each action must be supported by a selected claim's supports_actions, not merely an "
        "unselected eligible claim. no_action is permitted only alone at low risk."
    ),
    "MODEL_ABSTENTION_REASON_INVALID": (
        "Use one of the approved abstention reason codes, not free text; use null for scored mode."
    ),
}


def describe_failure(code: str | None) -> dict:
    """Return only allowlisted public text, never echo an unknown raw error string."""
    public_code = code if isinstance(code, str) and code in ERRORS else "ANALYSIS_UNKNOWN_ERROR"
    return {
        "code": public_code,
        **ERRORS[public_code]._asdict(),
        "service_blocking": public_code in SERVICE_BLOCKING_CODES,
    }


def is_retryable(code: str | None) -> bool:
    return describe_failure(code)["retryable"]
