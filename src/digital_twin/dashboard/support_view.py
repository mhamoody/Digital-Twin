"""Pure, API-backed support presentation; no prediction or database writes."""
from datetime import UTC, datetime
from uuid import uuid4
from .client import DashboardApiError
from .view_model import RISK_LABELS, missing_label

ACTIVE = {"new_concern", "reviewed", "ongoing"}
TRANSITIONS = {
    "new_concern": ("reviewed", "ongoing", "resolved", "dismissed"),
    "reviewed": ("ongoing", "resolved", "dismissed"),
    "ongoing": ("ongoing", "resolved", "dismissed"),
}
REASONS = {
    "NO_CURRENT_PREDICTION": "No prediction is available for the current checkpoint.",
    "NO_PREVIOUS_PREDICTION": "The previous eligible checkpoint was not assessed.",
    "MODEL_MISMATCH": "Scores were produced by different model versions and are not directly comparable.",
    "CALIBRATION_MISMATCH": "Displayed probabilities use different calibration versions.",
    "UNCALIBRATED": "This score is not a calibrated probability.",
    "NO_PREVIOUS_CHECKPOINT": "There is no previous eligible checkpoint.",
    "CHECKPOINT_POLICY_UNAVAILABLE": "The course checkpoint schedule is not available for comparison.",
    "ELIGIBILITY_UNKNOWN": "Checkpoint eligibility could not be established.",
    "INELIGIBLE_CHECKPOINT": "This checkpoint is outside the learner's eligible period.",
    "STATE_MISMATCH": "The predictions do not match the required learner checkpoints.",
    "ORIGIN_MISMATCH": "The observations come from different data origins.",
    "FEATURE_VERSION_MISMATCH": "The evidence definitions changed between checkpoints.",
    "ABSTAINED": "The model did not provide an assessment at one of these checkpoints.",
    "QUALITY_GATE_FAILED": "One of the predictions did not pass validation.",
    "NO_DISPLAY_PROBABILITY": "A comparable displayed value is unavailable.",
}

ACTION_LABELS = {
    "create_case": "Case opened",
    "transition_status": "Support status changed",
    "add_note": "Note added",
    "set_follow_up": "Follow-up scheduled",
    "clear_follow_up": "Follow-up cleared",
    "link_alert": "Alert linked",
}


def action_label(action_type):
    return ACTION_LABELS.get(action_type, action_type.replace("_", " ").title())


def utc(value):
    value = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if value.tzinfo is None:
        raise ValueError("Workflow time must include a timezone")
    return value.astimezone(UTC)


def time_text(value):
    return utc(value).strftime("%d %b %Y, %H:%M UTC") if value else "Not scheduled"


def due(case, now):
    return bool(case.get("status") in ACTIVE and case.get("follow_up_due_at")
                and utc(case["follow_up_due_at"]) <= utc(now))


def current_risk(item):
    bound = (item.get("state_id") and item.get("prediction_id")
             and item.get("prediction_state_id") == item["state_id"]
             and item.get("assessment_status") == "assessed")
    return item.get("risk_band") if bound else None


def counters(roster, cases, now):
    return {"Total learners": len(roster),
            "High Attention": sum(current_risk(r) == "high" for r in roster),
            "New Concerns": sum(c["status"] == "new_concern" for c in cases),
            "Ongoing Support": sum(c["status"] == "ongoing" for c in cases),
            "Follow-up Due": sum(due(c, now) for c in cases)}


def comparison_text(comparison):
    if not comparison.get("available"):
        return REASONS.get(comparison.get("reason"), "A reliable checkpoint comparison is unavailable.")
    if any(comparison.get(k) is None for k in
           ("previous_checkpoint", "current_checkpoint", "previous_value", "current_value", "delta")):
        return "A reliable checkpoint comparison is unavailable."
    return (f"Previous checkpoint: Week {comparison['previous_checkpoint']} | Previous value: "
            f"{comparison['previous_value']:.1%} → Current checkpoint: Week {comparison['current_checkpoint']} | "
            f"Current value: {comparison['current_value']:.1%} | Change: {comparison['delta']*100:+.1f} percentage points")


def score_label(item):
    if current_risk(item) is None:
        return "No current assessed score"
    # No explicit calibrated flag exists in the current learner contract. Be conservative.
    value = item.get("raw_risk_score")
    if value is None:
        value = item.get("display_probability")
    text = "Risk score unavailable" if value is None else f"Risk score: {value*100:.0f} / 100"
    return text + (" · Uncalibrated demo score" if item.get("calibration_version") in (None, "identity-demo-v1")
                   or item.get("model_version") == "simple-rules-v1" else " · Model score")


def evidence_view(feature):
    name, value = feature.get("feature_name", "unknown"), feature.get("value")
    eid = feature.get("evidence_id", "unknown")
    category = "other"
    if value is None or feature.get("missing_reason") not in ("observed", "structural_zero"):
        text = f"{name}: {missing_label(feature.get('missing_reason'))}"
    elif name == "days_since_last_activity" and isinstance(value, (int, float)):
        category, text = "activity_gap", f"No recorded LMS activity for {value:g} days."
    elif name == "clicks_last_14" and isinstance(value, (int, float)):
        category, text = "recent_activity", f"{value:g} recorded interactions in the last 14 days."
    elif name == "assessments_missed" and isinstance(value, (int, float)):
        category, text = "missed_assessment", f"{value:g} assessments due with no submission recorded by this checkpoint."
    elif isinstance(value, dict) and value.get("assessment_id"):
        # Structured feature values may supply explicit labels. Never derive names from IDs.
        category = "assessment"
        label = value.get("assessment_name") or value["assessment_id"]
        if isinstance(value.get("score"), (int, float)) and value.get("score_scale") == "percent":
            text = f"{label}: {value['score']:g}%"
        elif value.get("submission_status") == "missed":
            text = f"{label}: due but no submission recorded by this checkpoint."
        else:
            text = f"{label}: {value}"
    else:
        text = f"{name}: {value}"
    return {"kind": "model_evidence", "category": category, "text": text, "evidence_id": eid,
            "feature_name": name}


def history_view(action):
    return {"kind": "instructor_action", "actor": action["actor_id"],
            "timestamp": time_text(action["created_at"]), "action": action["action_type"].replace("_", " "),
            "note": action.get("note"), "status": (action.get("previous_status"), action.get("new_status")),
            "follow_up": (action.get("previous_follow_up_due_at"), action.get("new_follow_up_due_at"))}


def load_all(fetch):
    items = []
    while True:
        page = fetch(limit=200, offset=len(items))
        batch = page.get("items", [])
        items.extend(batch)
        if len(items) >= page["total"]:
            return items
        if not batch:
            raise DashboardApiError("The course list changed while loading. Refresh course data.")


def scoped_rows(roster, cases, presentation):
    if any(r.get("presentation_id") != presentation for r in [*roster, *cases]):
        raise DashboardApiError("The requested course information is unavailable.", 403)
    return roster, cases


def roster_rows(roster, cases, now, *, query="", risk="All", status="All", due_only=False):
    active = {(c["learner_id"], c["data_origin"]): c for c in cases if c["status"] in ACTIVE}
    rows = []
    for learner in roster:
        case = active.get((learner["learner_id"], learner["data_origin"]))
        state = case["status"] if case else "none"
        band = current_risk(learner)
        if query.lower() not in learner["learner_id"].lower(): continue
        if risk != "All" and risk != band: continue
        if status != "All" and status != state: continue
        if due_only and (not case or not due(case, now)): continue
        rows.append({"Learner": learner["learner_id"], "Risk": RISK_LABELS.get(band, "No current score"),
                     "Case": state.replace("_", " ").title(),
                     "Follow-up": ("Follow-up due" if due(case, now) else "Follow-up scheduled")
                        if case and case.get("follow_up_due_at") else "",
                     "When (UTC)": time_text(case.get("follow_up_due_at")) if case else ""})
    return rows


class Intent:
    """Session-owned request; retries keep the exact body even after a UI rerun."""
    @staticmethod
    def prepare(state, scope, payload):
        existing = state.get(scope)
        if existing:
            return existing
        state[scope] = {**payload, "idempotency_key": "ui-" + uuid4().hex}
        return state[scope]

    @staticmethod
    def send(state, scope, send, reload):
        try:
            result = send(state[scope])
        except DashboardApiError as error:
            if error.status_code == 409:
                state.pop(scope, None)
                reload()
                return "conflict", None
            if error.status_code in (401, 403, 404, 422):
                state.pop(scope, None)
            raise
        state.pop(scope, None)
        return "saved", result
