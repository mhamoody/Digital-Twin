"""Explicit course presets; applying one never changes records or policy revisions."""

from __future__ import annotations

from .contracts import CoursePolicy

LEARNING_MODE_LABELS = {
    "custom": "Custom expectations",
    "regular_online": "Regular online activity",
    "weekly": "Weekly work",
    "fortnightly": "Fortnightly work",
    "milestone": "Milestone-based work",
    "mainly_offline": "Mainly offline",
}

_ACTIVITY_THRESHOLDS = {
    "regular_online": (3, 7),
    "weekly": (7, 14),
    "fortnightly": (14, 28),
}


def preset_policy(mode: str, current: CoursePolicy) -> CoursePolicy:
    """Return a validated draft, preserving grade, calendar and revision settings.

    Selecting custom preserves every setting other than the preset label. Disabling
    inactivity does not alter data coverage or waive the independent quality gates.
    Persistence must still increment the revision through the usual policy service.
    """
    if mode not in LEARNING_MODE_LABELS:
        raise ValueError("Unknown learning mode.")
    values = current.model_dump(mode="json")
    values["learning_mode"] = mode
    if mode in _ACTIVITY_THRESHOLDS:
        warning, high = _ACTIVITY_THRESHOLDS[mode]
        values.update(
            inactivity_monitoring_enabled=True,
            inactivity_warning_days=warning,
            inactivity_high_days=high,
        )
    elif mode in {"milestone", "mainly_offline"}:
        values["inactivity_monitoring_enabled"] = False
    return CoursePolicy.model_validate(values)
