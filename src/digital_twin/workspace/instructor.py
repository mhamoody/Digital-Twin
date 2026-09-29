"""Display/workflow helpers, never predictive inputs or changes to stored evidence."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ACTIVE_CASE_STATUSES = frozenset({"new", "reviewed", "ongoing"})
PRIORITIES = {"low": 0, "normal": 1, "high": 2, "urgent": 3}
SORTS = frozenset(
    {"attention", "risk_desc", "risk_asc", "name", "learner_id", "follow_up", "priority"}
)


def current_course_day(course: dict) -> int | None:
    """Return real calendar day when known; do not invent a calendar for archives."""
    try:
        zone = ZoneInfo(course.get("timezone", "UTC"))
        moment = datetime.now(UTC).astimezone(zone)
        if course.get("start_date"):
            start = date.fromisoformat(course["start_date"])
        elif course.get("start_at"):
            instant = datetime.fromisoformat(course["start_at"].replace("Z", "+00:00"))
            if instant.tzinfo is None:
                return None
            start = instant.astimezone(zone).date()
        else:
            return None
        return (moment.date() - start).days
    except (ValueError, TypeError, ZoneInfoNotFoundError):
        return None


def triage_payload(row=None) -> dict:
    return {
        "flagged": False,
        "watchlisted": False,
        "priority": "normal",
        "note": "",
        **(row.payload if row else {}),
        "version": row.version if row else 0,
        "updated_at": row.updated_at.isoformat() if row else None,
    }


def identity_view(value, privacy: str):
    """Hide known identity-display fields, not arbitrary instructor notes/evidence text."""
    if privacy not in {"name_id", "id_only"}:
        raise ValueError("Unknown identity display mode.")
    if privacy == "name_id":
        return value
    if isinstance(value, list):
        return [identity_view(item, privacy) for item in value]
    if isinstance(value, dict):
        return {
            key: value["learner_id"] if key == "display_name" else identity_view(item, privacy)
            for key, item in value.items()
            if key != "display_name" or "learner_id" in value
        }
    return value


def historical_case_event(event, cutoff: int) -> bool:
    """Neither a later action nor later referenced evidence belongs to an older view."""
    week = event.payload.get("evidence_checkpoint_week", event.payload.get("checkpoint_week"))
    evidence_cutoff = event.payload.get("evidence_cutoff_day")
    if evidence_cutoff is None and week is not None:
        evidence_cutoff = week * 7 - 1
    return event.occurred_day <= cutoff and (evidence_cutoff is None or evidence_cutoff <= cutoff)


def sort_workspace(items: list[dict], sort: str, privacy: str):
    """Stable course-wide ordering before pagination; names never sort ID-only views."""
    if sort not in SORTS:
        raise ValueError("Unknown workspace sort.")
    if privacy not in {"name_id", "id_only"}:
        raise ValueError("Unknown identity display mode.")

    def key(row):
        score = row["risk_score"]
        priority = -PRIORITIES[row["triage"]["priority"]]
        due = row["follow_up_day"]
        identity = row["learner_id"]
        if sort == "risk_desc":
            return score is None, -(score or 0), identity
        if sort == "risk_asc":
            return score is None, score or 0, identity
        if sort == "name" and privacy == "name_id":
            return row["display_name"].casefold(), identity
        if sort in {"learner_id", "name"}:
            return (identity,)
        if sort == "follow_up":
            return not row["active_case"], due is None, due or 0, identity
        if sort == "priority":
            return priority, not row["triage"]["flagged"], identity
        return (
            not row["needs_review"],
            priority,
            not row["due"],
            not row["triage"]["flagged"],
            score is None,
            -(score or 0),
            identity,
        )

    items.sort(key=key)
