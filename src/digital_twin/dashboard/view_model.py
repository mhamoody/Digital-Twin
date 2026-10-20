"""Pure presentation helpers for the instructor dashboard.

The dashboard deliberately consumes the same stable prediction contract whether the
producer is the temporary rule model or a future LLM.  This module translates that
contract into instructor-facing language without changing model values.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

RISK_ORDER = {"high": 0, "medium": 1, "low": 2, None: 3}
RISK_LABELS = {
    "high": "High attention",
    "medium": "Watch",
    "low": "On track",
    None: "No current score",
}
STATUS_LABELS = {
    "new": "New",
    "reviewed": "Reviewed",
    "resolved": "Resolved",
    "dismissed": "Not actionable",
    None: "No alert",
}
FEATURE_LABELS = {
    "clicks_last_7": "Recorded activity · last 7 days",
    "clicks_last_14": "Recorded activity · last 14 days",
    "clicks_last_28": "Recorded activity · last 28 days",
    "clicks_cumulative": "Recorded activity · course to date",
    "active_days_last_7": "Active days · last 7 days",
    "active_days_last_14": "Active days · last 14 days",
    "active_days_last_28": "Active days · last 28 days",
    "active_days_cumulative": "Active days · course to date",
    "days_since_last_activity": "Days since last recorded activity",
    "assessments_due": "Assessments due by this checkpoint",
    "assessments_submitted": "Assessments submitted",
    "assessments_missed": "Assessments currently overdue",
    "submission_rate": "Assessment submission rate",
    "previous_attempts": "Previous course attempts",
    "studied_credits": "Current study load (credits)",
    "content_clicks_cumulative": "Content activity · course to date",
    "assessment_clicks_cumulative": "Assessment activity · course to date",
    "forum_clicks_cumulative": "Discussion activity · course to date",
    "collaboration_clicks_cumulative": "Collaboration activity · course to date",
    "other_clicks_cumulative": "Other recorded activity · course to date",
}
MISSING_LABELS = {
    "observed": "Observed",
    "structural_zero": "Observed: none recorded",
    "not_yet_applicable": "Not due yet",
    "not_applicable": "Not applicable",
    "source_missing": "Expected but missing from the source",
    "ingestion_incomplete": "Data import is incomplete",
    "not_supported": "Not supplied by this learning system",
    "suppressed_for_privacy": "Hidden for privacy",
    "no_activity_yet": "No activity recorded yet",
}
CLAIM_LABELS = {
    "INACTIVITY_GAP": "Long gap since the learner's last recorded activity",
    "LOW_RECENT_ACTIVITY": "Recent recorded activity is low",
    "MISSED_ASSESSMENT": "One or more assessments are currently overdue",
    "LIMITED_EVIDENCE": "The available data is too limited for a confident signal",
}
ACTION_LABELS = {
    "REVIEW_ACTIVITY": "Review the learner's recent course activity",
    "REVIEW_ACTIVITY_TIMELINE": "Review the learner's activity timeline",
    "CHECK_MISSED_ASSESSMENTS": "Check overdue or missing assessment work",
    "CONTACT_STUDENT": "Consider a supportive check-in with the learner",
    "MONITOR": "Continue monitoring at the next checkpoint",
}


def instructor_label(value: str | None, labels: dict[str | None, str]) -> str:
    """Return a curated label, falling back to readable title case."""

    if value in labels:
        return labels[value]
    if not value:
        return "Not available"
    return value.replace("_", " ").strip().title()


def feature_label(feature_name: str) -> str:
    return instructor_label(feature_name, FEATURE_LABELS)


def missing_label(reason: str | None) -> str:
    return instructor_label(reason, MISSING_LABELS)


def claim_label(code: str) -> str:
    return instructor_label(code, CLAIM_LABELS)


def action_label(code: str) -> str:
    return instructor_label(code, ACTION_LABELS)


def support_reason(item: dict[str, Any]) -> str:
    """Produce a low-inference queue reason from already validated state values."""

    missed = item.get("assessments_missed")
    if isinstance(missed, (int, float)) and missed > 0:
        noun = "assessment" if missed == 1 else "assessments"
        return f"{int(missed)} overdue {noun}"
    inactive_days = item.get("days_since_last_activity")
    if isinstance(inactive_days, (int, float)) and inactive_days >= 7:
        return f"No recorded activity for {int(inactive_days)} days"
    active_days = item.get("active_days_14d")
    if isinstance(active_days, (int, float)) and active_days <= 1:
        return f"Active on {int(active_days)} of the last 14 days"
    return "Open the evidence before deciding"


def trend_key(change: float | None, *, tolerance: float = 0.005) -> str:
    if change is None:
        return "unavailable"
    if change > tolerance:
        return "increasing"
    if change < -tolerance:
        return "decreasing"
    return "stable"


def trend_label(change: float | None) -> str:
    key = trend_key(change)
    if key == "increasing":
        return f"Up {abs(change or 0) * 100:.0f} percentage points"
    if key == "decreasing":
        return f"Down {abs(change or 0) * 100:.0f} percentage points"
    if key == "stable":
        return "Stable"
    return "First score"


def current_support_items(roster_items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one current alert per learner, ordered for instructor triage."""

    items = [dict(item) for item in roster_items if item.get("alert_id")]
    return sorted(
        items,
        key=lambda item: (
            RISK_ORDER.get(item.get("risk_band"), 3),
            -float(item.get("display_probability") or 0),
            -float(item.get("probability_change") or 0),
            str(item.get("learner_id", "")),
        ),
    )


def course_summary(roster_items: Iterable[dict[str, Any]]) -> dict[str, int]:
    items = list(roster_items)
    support_items = current_support_items(items)
    return {
        "learners": len(items),
        "current_data": sum(item.get("latest_checkpoint_week") is not None for item in items),
        "needs_review": sum(item.get("alert_status") == "new" for item in support_items),
        "high_attention": sum(item.get("risk_band") == "high" for item in items),
        "worsening": sum(
            trend_key(item.get("probability_change")) == "increasing" for item in items
        ),
        "stale": sum(item.get("is_fresh") is False for item in items),
    }


def risk_distribution(roster_items: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(item.get("risk_band") for item in roster_items)
    return {
        RISK_LABELS["high"]: counts["high"],
        RISK_LABELS["medium"]: counts["medium"],
        RISK_LABELS["low"]: counts["low"],
        RISK_LABELS[None]: counts[None],
    }


def trend_distribution(roster_items: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(trend_key(item.get("probability_change")) for item in roster_items)
    return {
        "Increased": counts["increasing"],
        "Stable": counts["stable"],
        "Decreased": counts["decreasing"],
        "First score": counts["unavailable"],
    }


def filter_roster(
    roster_items: Iterable[dict[str, Any]],
    *,
    query: str = "",
    risks: Iterable[str] = (),
    trends: Iterable[str] = (),
    statuses: Iterable[str] = (),
    freshness: str = "all",
) -> list[dict[str, Any]]:
    query = query.strip().lower()
    selected_risks = set(risks)
    selected_trends = set(trends)
    selected_statuses = set(statuses)
    filtered = []
    for item in roster_items:
        if query and query not in str(item.get("learner_id", "")).lower():
            continue
        if selected_risks and item.get("risk_band") not in selected_risks:
            continue
        if selected_trends and trend_key(item.get("probability_change")) not in selected_trends:
            continue
        status = item.get("alert_status") or "none"
        if selected_statuses and status not in selected_statuses:
            continue
        if freshness == "current" and item.get("is_fresh") is not True:
            continue
        if freshness == "stale" and item.get("is_fresh") is not False:
            continue
        filtered.append(dict(item))
    return sorted(
        filtered,
        key=lambda item: (
            RISK_ORDER.get(item.get("risk_band"), 3),
            -float(item.get("display_probability") or 0),
            str(item.get("learner_id", "")),
        ),
    )


def display_feature_value(feature_name: str, value: Any, missing_reason: str | None) -> str:
    if value is None:
        return missing_label(missing_reason)
    if feature_name == "submission_rate":
        return f"{float(value):.0%}"
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)
