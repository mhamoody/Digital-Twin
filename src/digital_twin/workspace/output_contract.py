"""Strict model wire contract; canonical outputs and safe diagnostics stay stable.

The model chooses a score or abstains. A band is a deterministic presentation of
that unchanged score, not a second prediction. Legacy responses are accepted only
when their existing band/abstention fields are internally consistent.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Literal

from pydantic import Field, ValidationError

from .contracts import Contract, GroundedClaim, ModelOutput

Action = Literal[
    "review_recent_work",
    "send_check_in",
    "offer_resources",
    "review_grades",
    "confirm_data",
    "no_action",
]
MODEL_REASONS = frozenset({"INSUFFICIENT_CONFIDENCE", "CONFLICTING_EVIDENCE"})
LEGACY_REASONS = MODEL_REASONS | {
    "STALE_STATE",
    "INSUFFICIENT_EVIDENCE",
    "MISSING_ACADEMIC_EVIDENCE",
}
ACTIONS = frozenset(
    {
        "review_recent_work",
        "send_check_in",
        "offer_resources",
        "review_grades",
        "confirm_data",
        "no_action",
    }
)
CLAIM_CODES = frozenset(
    {
        "INACTIVITY_GAP",
        "MISSED_ASSESSMENT",
        "LOW_GRADE",
        "LOW_LATEST_GRADE",
        "DECLINING_GRADES",
        "LATE_SUBMISSIONS",
        "LOW_COMPLETION",
        "LOW_ATTENDANCE",
        "RECENT_ACTIVITY",
        "ASSESSMENTS_ON_TRACK",
        "GRADE_ON_TRACK",
        "IMPROVING_GRADES",
    }
)

# This is also the allowlist for persisted diagnostic descriptions. Never use a
# Pydantic message/context directly: it can contain the rejected input itself.
EXPECTATIONS = {
    "required_field": "a required field must be present",
    "extra_field": "no undeclared fields",
    "number_type": "a JSON number",
    "boolean_type": "a JSON boolean",
    "string_type": "a string",
    "array_type": "an array",
    "object_type": "a JSON object",
    "enum_value": "an allowed enum value",
    "value_range": "a Risk score between 0 and 1, inclusive",
    "collection_size": "an allowed number of items",
    "text_length": "text within the schema length limit",
    "mixed_contract": "one response format without native/legacy field mixing",
    "assessed_score_required": "a non-null score for an assessed response",
    "assessed_band_required": "a non-null band for a legacy assessed response",
    "assessed_claims_required": "at least one claim for an assessed response",
    "score_band_mismatch": "the band corresponding to the unchanged risk score",
    "abstention_fields_conflict": "null score/band and empty claims/actions when abstaining",
    "abstention_reason_required": "an approved reason when abstaining",
    "assessed_reason_conflict": "a null abstention reason when assessing",
    "risk_requires_concern": "Scores at least 0.35 require a selected grounded concern.",
    "high_requires_academic": (
        "Scores at least 0.65 require selected academic evidence under this course policy."
    ),
    "high_requires_inactivity_threshold": (
        "Inactivity-only high risk requires this course high-inactivity threshold."
    ),
    "claim_not_eligible": "Select only distinct permitted claims supported by the snapshot.",
    "evidence_not_matched": "Citations must exactly match the selected permitted claim.",
    "action_not_supported": "Select only actions supported by selected claims and score.",
    "actions_empty_or_duplicate": "Return distinct supported actions for an assessment.",
    "actions_conflict": "no_action must be the only action at low risk.",
    "schema_invalid": "the documented output contract",
}
RECEIVED_TYPES = frozenset(
    {
        "null",
        "number",
        "integer",
        "boolean",
        "string",
        "array",
        "object",
        "missing",
        "unknown",
    }
)
NORMALIZATION_CODES = frozenset({"enum_format", "decimal_string", "json_fence", "legacy_contract"})
_PATH = re.compile(
    r"(?:\$|<unknown_field>|decision|risk_score|risk_band|abstain|abstention_reason|reason|"
    r"suggested_actions(?:\.[0-9]{1,2})?|"
    r"claims(?:\.[0-9]{1,2}(?:\.(?:code|evidence_ids)(?:\.[0-9]{1,2})?)?)?)\Z"
)
_DECIMAL = re.compile(r"(?:0|1)(?:\.[0-9]+)?\Z")
_MISSING = object()


def _safe_path(value):
    return value if isinstance(value, str) and _PATH.fullmatch(value) else "<unknown_field>"


def safe_normalizations(records):
    """Discard unexpected fields and values before a second persistence boundary."""
    if not isinstance(records, list):
        return []
    return [
        {"path": _safe_path(item.get("path")), "code": item["code"]}
        for item in records[:32]
        if isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and item["code"] in NORMALIZATION_CODES
    ]


def safe_validation_details(details):
    """Bounded fixed descriptions; no raw model text, unknown keys or exception messages."""
    if not isinstance(details, list):
        return []
    result = []
    for item in details[:8]:
        if not isinstance(item, dict):
            continue
        code = item.get("code")
        code = code if isinstance(code, str) and code in EXPECTATIONS else "schema_invalid"
        received = item.get("received_type")
        clean = {
            "path": _safe_path(item.get("path")),
            "code": code,
            "expected": EXPECTATIONS[code],
            "received_type": received
            if isinstance(received, str) and received in RECEIVED_TYPES
            else "unknown",
        }
        # Only known contract scalars can be shown. Never echo unknown keys/text,
        # arbitrary claim evidence, a whole object, or a possibly identifying number.
        value = item.get("received", _MISSING)
        path = clean["path"]
        if path == "risk_score":
            if type(value) in (int, float) and -100 <= value <= 100 and math.isfinite(value):
                clean["received"] = value
            elif isinstance(value, str) and re.fullmatch(r"[0-9]{1,2}(?:\.[0-9]{1,8})?", value):
                clean["received"] = value
            elif value is None:
                clean["received"] = None
        elif path == "abstain" and type(value) is bool:
            clean["received"] = value
        elif (
            path != "<unknown_field>"
            and isinstance(value, str)
            and value
            in (
                CLAIM_CODES
                | ACTIONS
                | LEGACY_REASONS
                | {"assess", "abstain", "low", "medium", "high"}
            )
        ):
            clean["received"] = value
        result.append(clean)
    return result


class OutputContractError(ValueError):
    def __init__(self, details, normalizations=None):
        self.code = "MODEL_SCHEMA_INVALID"
        self.details = safe_validation_details(details)
        self.normalizations = safe_normalizations(normalizations)
        super().__init__(self.code)


def _type(value):
    if value is _MISSING:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "unknown"


def _detail(path, code, value=_MISSING):
    return {"path": path, "code": code, "received_type": _type(value), "received": value}


def diagnostic_detail(code, path, received=_MISSING):
    """One safe diagnostic for an independent evidence/policy validator."""
    return safe_validation_details([_detail(path, code, received)])[0]


def pydantic_validation_details(error: ValidationError, parsed):
    """Project Pydantic failures onto a fixed taxonomy without leaking their input."""
    details = []
    for item in error.errors(include_input=False, include_context=False, include_url=False)[:8]:
        location = item.get("loc", ())
        value = parsed
        for part in location:
            try:
                value = value[part]
            except (TypeError, KeyError, IndexError):
                value = _MISSING
                break
        kind = item["type"]
        code = {
            "missing": "required_field",
            "extra_forbidden": "extra_field",
            "float_type": "number_type",
            "float_parsing": "number_type",
            "int_type": "number_type",
            "bool_type": "boolean_type",
            "string_type": "string_type",
            "list_type": "array_type",
            "model_type": "object_type",
            "dict_type": "object_type",
            "literal_error": "enum_value",
            "enum": "enum_value",
            "greater_than_equal": "value_range",
            "less_than_equal": "value_range",
            "finite_number": "value_range",
            "too_short": "collection_size",
            "too_long": "collection_size",
            "string_too_short": "text_length",
            "string_too_long": "text_length",
        }.get(kind, "schema_invalid")
        details.append(_detail(".".join(map(str, location)) or "$", code, value))
    return safe_validation_details(details)


class _Assessed(Contract):
    decision: Literal["assess"]
    risk_score: float = Field(ge=0, le=1)
    claims: list[GroundedClaim] = Field(min_length=1, max_length=8)
    suggested_actions: list[Action] = Field(min_length=1, max_length=6)


class _Abstained(Contract):
    decision: Literal["abstain"]
    reason: Literal["INSUFFICIENT_CONFIDENCE", "CONFLICTING_EVIDENCE"]


class _Legacy(Contract):
    risk_score: float | None = Field(ge=0, le=1)
    risk_band: Literal["low", "medium", "high"] | None
    claims: list[GroundedClaim] = Field(max_length=8)
    suggested_actions: list[Action] = Field(max_length=6)
    abstain: bool
    abstention_reason: str | None = Field(default=None, max_length=300)


def response_schema(eligible_codes, evidence_alias_ids, allowed_actions):
    """Complete native branches, including null-free explicit abstention.

    The schema constrains structure; independent evidence/action/policy checks
    remain authoritative. No branch prescribes a risk score from selected claims.
    """
    codes, ids, actions = (
        sorted(set(values))
        for values in (
            eligible_codes,
            evidence_alias_ids,
            allowed_actions,
        )
    )
    if (
        any(
            not isinstance(value, str) or not value
            for values in (codes, ids, actions)
            for value in values
        )
        or not set(actions) <= ACTIONS
    ):
        raise ValueError("Schema allowlists must contain approved nonempty string values.")
    abstain = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {"type": "string", "const": "abstain"},
            "reason": {"type": "string", "enum": sorted(MODEL_REASONS)},
        },
        "required": ["decision", "reason"],
    }
    if not codes or not ids or not actions:
        return {"anyOf": [abstain]}
    claim = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "code": {"type": "string", "enum": codes, "minLength": 1, "maxLength": 64},
            "evidence_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "items": {"type": "string", "enum": ids},
            },
        },
        "required": ["code", "evidence_ids"],
    }
    assess = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "decision": {"type": "string", "const": "assess"},
            "risk_score": {"type": "number", "minimum": 0, "maximum": 1},
            "claims": {"type": "array", "minItems": 1, "maxItems": 8, "items": claim},
            "suggested_actions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 6,
                "items": {"type": "string", "enum": actions},
            },
        },
        "required": ["decision", "risk_score", "claims", "suggested_actions"],
    }
    return {"anyOf": [assess, abstain]}


def _normalize_enum(container, key, allowed, path, records):
    value = container.get(key) if isinstance(container, dict) else container[key]
    if not isinstance(value, str):
        return
    canonical = next(
        (item for item in allowed if item.casefold() == value.strip().casefold()), None
    )
    if canonical is not None and canonical != value:
        container[key] = canonical
        records.append({"path": path, "code": "enum_format"})


def _normalize(parsed):
    # Copy only containers we edit. Unexpected deeply nested JSON must reach
    # schema rejection, not overflow a recursive copy before validation.
    data, records = dict(parsed), []
    for name, allowed in (
        ("decision", {"assess", "abstain"}),
        ("risk_band", {"low", "medium", "high"}),
        ("reason", MODEL_REASONS),
        ("abstention_reason", LEGACY_REASONS),
    ):
        _normalize_enum(data, name, allowed, name, records)
    score = data.get("risk_score")
    if isinstance(score, str) and len(score) <= 80 and _DECIMAL.fullmatch(score.strip()):
        decimal_score = Decimal(score.strip())
        number = float(decimal_score)
        # Do not round a long numeric string into a different decimal score.
        if (
            0 <= decimal_score <= 1
            and math.isfinite(number)
            and Decimal(str(number)) == decimal_score
        ):
            data["risk_score"] = number
            records.append({"path": "risk_score", "code": "decimal_string"})
    if isinstance(data.get("claims"), list):
        data["claims"] = list(data["claims"])
        for index, claim in enumerate(data["claims"][:8]):
            if isinstance(claim, dict):
                claim = dict(claim)
                data["claims"][index] = claim
                _normalize_enum(claim, "code", CLAIM_CODES, f"claims.{index}.code", records)
    if isinstance(data.get("suggested_actions"), list):
        data["suggested_actions"] = list(data["suggested_actions"])
        for index in range(min(6, len(data["suggested_actions"]))):
            _normalize_enum(
                data["suggested_actions"], index, ACTIONS, f"suggested_actions.{index}", records
            )
    return data, records


def _band(score):
    return "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"


def _legacy_output(wire):
    details = []
    if wire.abstain:
        if (
            wire.risk_score is not None
            or wire.risk_band is not None
            or wire.claims
            or wire.suggested_actions
        ):
            details.append(_detail("abstain", "abstention_fields_conflict", wire.abstain))
        if not wire.abstention_reason:
            details.append(
                _detail("abstention_reason", "abstention_reason_required", wire.abstention_reason)
            )
        elif wire.abstention_reason not in LEGACY_REASONS:
            details.append(_detail("abstention_reason", "enum_value", wire.abstention_reason))
    else:
        for name, code in (
            ("risk_score", "assessed_score_required"),
            ("risk_band", "assessed_band_required"),
        ):
            if getattr(wire, name) is None:
                details.append(_detail(name, code, None))
        if not wire.claims:
            details.append(_detail("claims", "assessed_claims_required", wire.claims))
        if (
            wire.risk_score is not None
            and wire.risk_band is not None
            and wire.risk_band != _band(wire.risk_score)
        ):
            details.append(_detail("risk_band", "score_band_mismatch", wire.risk_band))
        if wire.abstention_reason is not None:
            details.append(
                _detail("abstention_reason", "assessed_reason_conflict", wire.abstention_reason)
            )
    if details:
        raise OutputContractError(details)
    return ModelOutput.model_validate(wire.model_dump(), strict=True)


def parse_response(parsed):
    """Parse native v3 or coherent legacy output, preserving the model's score.

    Unknown evidence/claim references remain unchanged for independent grounding
    validation. Harmless enum/decimal formatting is normalized and explicitly
    audited; missing fields, invented actions and conflicting decisions are not.
    """
    if not isinstance(parsed, dict):
        raise OutputContractError([_detail("$", "object_type", parsed)])
    native = "decision" in parsed or "reason" in parsed
    if native and set(parsed) & {"risk_band", "abstain", "abstention_reason"}:
        raise OutputContractError([_detail("$", "mixed_contract", parsed)])
    data, normalizations = _normalize(parsed)
    try:
        if not native:
            output = _legacy_output(_Legacy.model_validate(data, strict=True))
        elif data.get("decision") == "abstain":
            wire = _Abstained.model_validate(data, strict=True)
            output = ModelOutput(
                risk_score=None,
                risk_band=None,
                claims=[],
                suggested_actions=[],
                abstain=True,
                abstention_reason=wire.reason,
            )
        else:
            wire = _Assessed.model_validate(data, strict=True)
            output = ModelOutput(
                risk_score=wire.risk_score,
                risk_band=_band(wire.risk_score),
                claims=wire.claims,
                suggested_actions=wire.suggested_actions,
                abstain=False,
                abstention_reason=None,
            )
    except OutputContractError as error:
        error.normalizations = safe_normalizations(normalizations)
        raise
    except ValidationError as error:
        raise OutputContractError(
            pydantic_validation_details(error, data), normalizations
        ) from error
    return output, safe_normalizations(normalizations)
