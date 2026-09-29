"""Responsive instructor workspace for the version-two course API.

The UI displays checkpoint snapshots and audited support cases. It does not
calculate risk, infer missing evidence, or generate student communications.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st

from digital_twin.workspace.contracts import CoursePolicy
from digital_twin.workspace.errors import describe_failure
from digital_twin.workspace.features import assessment_category
from digital_twin.workspace.policy import LEARNING_MODE_LABELS, preset_policy
from digital_twin.workspace.tracing import safe_attempts

from .client import DashboardApiError
from .demo_guide import demo_examples
from .workspace_client import WorkspaceClient

SUPPORT_LABELS = {
    "high": "High attention",
    "medium": "Watch",
    "low": "On track",
    "unavailable": "Not assessed",
    None: "Not assessed",
}
STATUS_LABELS = {
    "new": "Needs review",
    "reviewed": "Reviewed",
    "ongoing": "Ongoing",
    "resolved": "Resolved",
    "dismissed": "Not actionable",
    "queued": "Queued",
    "running": "Running",
    "validated": "Validated output",
    "abstained": "Insufficient evidence",
    "failed": "Analysis failed",
    "pending": "Awaiting analysis",
    "not_requested": "Not requested",
    "not_run": "Not analyzed",
    "outdated": "Settings changed: rerun needed",
    "planned": "Planned",
    "completed": "Completed",
    "cancelled": "Cancelled",
}
ACTION_LABELS = {
    "contact": "Contact student",
    "warning": "Record academic warning",
    "support": "Provide support",
    "resource": "Share learning resource",
    "follow_up": "Follow up",
    "note": "Record note",
}
PRIORITY_LABELS = {"low": "Low", "normal": "Normal", "high": "High", "urgent": "Urgent"}
ROSTER_SORTS = {
    "attention": "Needs attention first",
    "priority": "Instructor priority first",
    "risk_desc": "Risk score: highest first",
    "risk_asc": "Risk score: lowest first",
    "follow_up": "Follow-up: earliest first",
    "name": "Student name",
    "learner_id": "Learner ID",
}


def identity_mode() -> str:
    return st.session_state.get("workspace_privacy", "name_id")


def student_label(item: dict[str, Any], *, privacy: str | None = None) -> str:
    """Use only the authorized server mapping; never fabricate an identity."""
    learner_id = str(item.get("learner_id", "Unknown ID"))
    name = item.get("display_name")
    if (privacy or identity_mode()) == "id_only" or not name or name == learner_id:
        return learner_id
    return f"{name} · {learner_id}"


def triage_label(triage: dict[str, Any] | None) -> str:
    triage = triage or {}
    parts = [
        text
        for key, text in (("flagged", "Flagged"), ("watchlisted", "On watchlist"))
        if triage.get(key)
    ]
    priority = triage.get("priority", "normal")
    if priority != "normal":
        parts.append(f"{PRIORITY_LABELS.get(priority, priority)} priority")
    return " · ".join(parts) or "No manual flag · normal priority"


WORKSPACE_CSS = """
<style>
 .block-container {max-width:1440px;padding-top:4rem;padding-bottom:3rem;}
 h1,h2,h3,h4,p,li,label {overflow-wrap:anywhere;}
 [data-testid="stMarkdownContainer"] {min-width:0;}
 .dt-kicker {font-size:.78rem;font-weight:700;letter-spacing:.06em;
   text-transform:uppercase;color:#427c71;}
 .dt-context {border-left:4px solid #427c71;padding:.55rem 1rem;margin:.65rem 0 1.2rem;}
 .dt-cards {display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
   gap:.8rem;margin:.8rem 0 1.1rem;}
 .dt-card {border:1px solid #d7dedb;border-radius:12px;background:#f8faf8;
   color:#20352f;padding:1rem;min-width:0;}
 .dt-card-title {font-size:.88rem;font-weight:650;white-space:normal;}
 .dt-card-value {font-size:1.9rem;font-weight:720;line-height:1.4;overflow-wrap:anywhere;}
 .dt-card-detail {font-size:.78rem;color:#52665f;line-height:1.4;white-space:normal;}
 .dt-evidence {border:1px solid #d7dedb;border-left:4px solid #427c71;
   border-radius:8px;padding:.85rem 1rem;margin:.6rem 0;}
 .dt-scroll {max-width:100%;overflow-x:auto;}
 div[role="radiogroup"] {flex-wrap:wrap;gap:.2rem;}
 [data-testid="stMetricValue"] {overflow-x:auto;text-overflow:clip;}
 [data-testid="stMetricLabel"] p {white-space:normal;}
 [data-testid="stDataFrame"], [data-testid="stCode"] {max-width:100%;overflow-x:auto;}
 [data-testid="stButton"] p {white-space:normal;}
 [data-baseweb="select"] [data-baseweb="tag"],
 [data-baseweb="select"] [data-testid="stMarkdownContainer"] {
   white-space:normal;overflow-wrap:anywhere;}
 [data-baseweb="tab-list"] {max-width:100%;overflow-x:auto;scrollbar-width:thin;}
 [data-baseweb="tab"] {flex-shrink:0;white-space:nowrap;}
 :focus-visible {outline:3px solid #a85a2d!important;outline-offset:3px;}
 @media(max-width:850px) {
   .block-container {padding:4rem .9rem 2rem;}
   .dt-cards {grid-template-columns:repeat(2,minmax(0,1fr));}
   [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important;gap:1rem!important;}
   [data-testid="stHorizontalBlock"]>[data-testid="stColumn"] {
     width:100%!important;flex:1 1 100%!important;min-width:0!important;}
   h1 {font-size:1.8rem!important;} h2 {font-size:1.5rem!important;}
 }
 @media(max-width:430px) {
   .dt-cards {grid-template-columns:1fr 1fr;gap:.5rem;}
   .dt-card {padding:.75rem;}.dt-card-value {font-size:1.35rem;}}
</style>
"""


def label(value: Any) -> str:
    if value is None:
        return "Not available"
    return STATUS_LABELS.get(str(value), str(value).replace("_", " ").strip().capitalize())


def model_label(version: str | None) -> str:
    if not version:
        return "No model result"
    if version in {"rules-baseline-v3", "rules-baseline-v2", "simple-rules-v1"}:
        return f"Temporary rules baseline · {version}"
    return f"Risk model · {version}"


def points(value: Any) -> str:
    """API risk scores are fractions; show score points, never probability claims."""
    if value is None:
        return "Not assessed"
    return f"{float(value) * 100:.0f} / 100"


def comparison(current: Any, previous: Any, *, comparable: bool = True) -> str:
    if current is None:
        return "No current risk score"
    if previous is None:
        return "No earlier comparable risk score"
    if not comparable:
        return "Model or settings changed"
    delta = (float(current) - float(previous)) * 100
    return f"{float(previous) * 100:.0f} → {float(current) * 100:.0f} ({delta:+.0f} points)"


def comparison_card(current: Any, previous: Any, comparable: bool, week: Any) -> tuple[str, str]:
    if current is not None and previous is not None and comparable:
        return (
            f"{float(previous) * 100:.0f} → {float(current) * 100:.0f}",
            f"{(float(current) - float(previous)) * 100:+.0f} risk-score points "
            + (f"since week {week}." if week is not None else "since the previous checkpoint."),
        )
    return "Unavailable", comparison(current, previous, comparable=comparable)


def timestamp(value: Any, *, seconds: bool = False) -> str:
    if not value:
        return "Not recorded"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y, %H:%M:%S %Z" if seconds else "%d %b %Y, %H:%M %Z").strip()
    except ValueError:
        return str(value)


def resume_is_pending(control: dict[str, Any]) -> bool:
    requested = control.get("resume_requested_at")
    acknowledged = control.get("resume_acknowledged_at")
    if not requested:
        return False
    if not acknowledged:
        return True
    try:
        request_at = datetime.fromisoformat(str(requested).replace("Z", "+00:00"))
        acknowledged_at = datetime.fromisoformat(str(acknowledged).replace("Z", "+00:00"))
        return request_at > acknowledged_at
    except (ValueError, TypeError):
        return False


def render_cards(cards: list[tuple[str, str, str]]) -> None:
    contents = "".join(
        '<div class="dt-card"><div class="dt-card-title">'
        + html.escape(title)
        + '</div><div class="dt-card-value">'
        + html.escape(str(value))
        + '</div><div class="dt-card-detail">'
        + html.escape(detail)
        + "</div></div>"
        for title, value, detail in cards
    )
    st.markdown('<div class="dt-cards">' + contents + "</div>", unsafe_allow_html=True)


def count_chart(counts: dict[str, int], total: int) -> alt.Chart:
    rows = [{"Category": key, "Students": value} for key, value in counts.items()]
    colors = ["#ba5260", "#b78334", "#427c71", "#7c8896", "#786694", "#587da0"]
    return (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "Students:Q",
                scale=alt.Scale(domain=[0, max(1, total)], nice=False),
                axis=alt.Axis(tickMinStep=1, tickCount=5, labelFontSize=12),
                title=f"Students (out of {total})",
            ),
            y=alt.Y(
                "Category:N",
                sort=list(counts),
                title=None,
                axis=alt.Axis(labelLimit=0, labelOverlap=False, labelFontSize=12, labelPadding=8),
            ),
            color=alt.Color(
                "Category:N",
                scale=alt.Scale(domain=list(counts), range=colors[: len(counts)]),
                legend=None,
            ),
            tooltip=[alt.Tooltip("Category:N"), alt.Tooltip("Students:Q", format="d")],
        )
        .properties(height=max(240, len(rows) * 60))
    )


def mutation_key(action: str, payload: dict[str, Any]) -> str:
    """Reuse request identity after timeout; a changed payload starts a new request."""
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
    key = f"workspace_request_{action}_{digest}"
    if key not in st.session_state:
        st.session_state[key] = f"workspace-{uuid4()}"
    return st.session_state[key]


def _navigate(page: str, learner_id: str | None = None) -> None:
    st.session_state["workspace_page"] = page
    st.session_state["workspace_profile"] = learner_id


def _clear_profile() -> None:
    st.session_state["workspace_profile"] = None


def _open_profile(page: str, learner_id: str) -> None:
    st.session_state["workspace_return_page"] = page
    _navigate(page, learner_id)


def _change_identity() -> None:
    # A name typed in a search box must not remain visible after switching to ID only.
    for key in list(st.session_state):
        if key.startswith("workspace_search_") or key.startswith("workspace_lookup_"):
            st.session_state[key] = ""
        elif key.startswith("workspace_filter_") and isinstance(st.session_state[key], dict):
            st.session_state[key] = st.session_state[key] | {"search": ""}


def _filter_roster(course_id: str, week: int, page: str, filters: dict[str, Any]) -> None:
    scope = f"{course_id}_{week}_{page == 'Support cases'}"
    saved = roster_defaults(page == "Support cases") | filters
    st.session_state[f"workspace_filter_{scope}"] = saved
    st.session_state[f"workspace_offset_{scope}"] = 0
    for field, value in saved.items():
        st.session_state[f"workspace_{field}_{scope}"] = value
    _navigate(page)


def roster_defaults(cases_only: bool = False) -> dict[str, Any]:
    return {
        "search": "",
        "risk": "",
        "status": "",
        "attention": "",
        "priority": "",
        "due": False,
        "active": cases_only,
        "sort": "attention",
    }


def _open_selected_row(key: str, learners: list[str], page: str) -> None:
    selection = st.session_state.get(key, {}).get("selection", {}).get("rows", [])
    if selection and 0 <= selection[0] < len(learners):
        _open_profile(page, learners[selection[0]])


def _show_error(error: Exception) -> None:
    st.error(str(error))
    st.caption(
        "Your saved records remain in the database. Refresh to check the latest status "
        "before retrying a saved action."
    )


def _frame(rows: list[dict[str, Any]]) -> None:
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.caption("Swipe or scroll horizontally to read every table column.")


def _output(result: dict[str, Any] | None) -> dict[str, Any]:
    return (result or {}).get("output") or {}


def _course_name(course: dict[str, Any]) -> str:
    name = course.get("title") or course["presentation_id"]
    if course.get("data_origin") == "synthetic":
        updated = course["presentation_id"].endswith(":v2")
        version = "updated demo v2" if updated else "original demo"
        return f"{name} · {version}"
    return name


def render_workspace(client: WorkspaceClient, account: Any) -> None:
    """Entry point called after the existing pilot account has authenticated."""
    st.markdown(WORKSPACE_CSS, unsafe_allow_html=True)
    try:
        courses = client.courses().get("items", [])
    except DashboardApiError as error:
        _show_error(error)
        return
    if not courses:
        st.info(
            "No prepared courses are assigned to this account yet. Ask the course operator "
            "to assign a course and import its data."
        )
        return
    by_id = {item["presentation_id"]: item for item in courses}
    with st.sidebar:
        st.markdown(f"### {account.display_name}")
        st.caption(f"{label(account.role)} workspace")
        course_id = st.selectbox(
            "Course",
            list(by_id),
            format_func=lambda key: _course_name(by_id[key]),
            key="workspace_course",
        )
        st.caption(_course_name(by_id[course_id]))
        weeks = sorted(by_id[course_id].get("checkpoints", []))
        if not weeks:
            st.info("This course has no prepared checkpoints.")
            return
        week = st.selectbox(
            "Checkpoint",
            weeks,
            index=len(weeks) - 1,
            format_func=lambda value: f"Week {value}",
            key=f"workspace_week_{course_id}",
        )
        st.caption(f"Evidence available through course day {week * 7 - 1}.")
        st.radio(
            "Student identity display",
            ["name_id", "id_only"],
            format_func=lambda value: "Name + ID" if value == "name_id" else "ID only",
            key="workspace_privacy",
            horizontal=True,
            on_change=_change_identity,
            help="Names come only from your authorized course roster. "
            "ID only also limits search to IDs; free-text notes may still identify a student.",
        )
        if st.button(
            "Refresh workspace", use_container_width=True,
            help="Reload saved data and results. This does not import LMS data or rerun the model.",
        ):
            st.rerun()
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.caption("Actions record instructor decisions. No automatic student messages are sent.")

    context = (account.reviewer_id, course_id, week)
    if st.session_state.get("workspace_context") != context:
        st.session_state["workspace_context"] = context
        st.session_state["workspace_profile"] = None
    demo_target = st.session_state.pop("workspace_demo_target", None)
    if demo_target and demo_target[:2] == (course_id, week):
        _open_profile("Students", demo_target[2])
    course = by_id[course_id]
    st.markdown(
        '<div class="dt-kicker">Course digital twin · instructor workspace</div>',
        unsafe_allow_html=True,
    )
    st.title(_course_name(course))
    origin = course.get("data_origin", "unknown")
    st.markdown(
        '<div class="dt-context">'
        + html.escape(
            f"Viewing week {week} · evidence available through course day {week * 7 - 1} "
            f"· {origin.title()} data"
        )
        + "</div>",
        unsafe_allow_html=True,
    )
    if origin in {"synthetic", "manual_test"}:
        st.info(
            "Demonstration course: students, records and outcomes are synthetic. "
            "Use this course to inspect system behavior across scenarios."
        )
    if flash := st.session_state.pop("workspace_flash", None):
        st.success(flash)
    try:
        workspace = client.workspace(
            course_id, week=week, privacy=identity_mode(), support_scope="current"
        )
    except DashboardApiError as error:
        _show_error(error)
        return
    pages = ["Overview", "Students", "Support cases", "Course settings", "Data health"]
    page = st.radio(
        "Workspace section", pages, horizontal=True, key="workspace_page", on_change=_clear_profile
    )
    learner_id = st.session_state.get("workspace_profile")
    if learner_id:
        return_page = st.session_state.get("workspace_return_page", "Students")
        st.button(
            "← Back to support cases"
            if return_page == "Support cases"
            else "← Back to student list",
            on_click=_navigate,
            args=(return_page, None),
        )
        render_profile(client, course_id, week, learner_id, workspace.get("policy", {}))
        return
    if page == "Overview":
        render_overview(client, course_id, week, workspace)
    elif page in {"Students", "Support cases"}:
        render_roster(client, course_id, week, cases_only=page == "Support cases")
    elif page == "Course settings":
        render_settings(client, course_id, workspace.get("policy", {}))
    else:
        render_health(client, workspace)


def render_overview(
    client: WorkspaceClient, course_id: str, week: int, workspace: dict[str, Any]
) -> None:
    summary = workspace.get("summary", {})
    model_counts = workspace.get("model_counts", {})
    versions = {name for name in model_counts if name != "not_run"} or {
        item.get("model_version")
        for item in workspace.get("items", [])
        if item.get("risk_score") is not None and item.get("model_version")
    }
    if versions and versions.issubset(
        {"rules-baseline-v3", "rules-baseline-v2", "simple-rules-v1"}
    ):
        st.warning(
            "The visible results use the temporary rules baseline. "
            "Run Qwen analysis to inspect the LLM's contribution. "
            "Every result retains its actual model version."
        )
    elif versions:
        st.caption("Models in the visible results: " + ", ".join(sorted(versions)))
    if model_counts:
        st.caption(
            "Result sources across the course at this checkpoint: "
            + " · ".join(f"{label(name)}: {count}" for name, count in model_counts.items())
        )
    total = int(summary.get("enrolled", 0))
    cards = [
        ("Enrolled students", total, "Entire checkpoint roster.", "Students", {}),
        (
            "Needs review",
            summary.get("needs_review", 0),
            "Unreviewed concerns or follow-ups due.",
            "Students",
            {"attention": "needs_review"},
        ),
        (
            "High attention",
            summary.get("high_attention", 0),
            "Model high-attention band.",
            "Students",
            {"risk": "high"},
        ),
        (
            "Insufficient evidence",
            summary.get("insufficient_data", 0),
            "Evidence does not support an assessment.",
            "Students",
            {"attention": "insufficient_data"},
        ),
        (
            "Active support cases",
            summary.get("active_cases", summary.get("ongoing", 0)),
            "New, reviewed and ongoing cases.",
            "Support cases",
            {"active": True},
        ),
    ]
    for column, (title, count, description, page, filters) in zip(
        st.columns(5), cards, strict=True
    ):
        with column, st.container(border=True):
            st.metric(title, count)
            st.caption(description)
            st.button(
                f"View {title.lower()}",
                key=f"workspace_card_{title}",
                on_click=_filter_roster,
                args=(course_id, week, page, filters),
                use_container_width=True,
            )
    manual_cards = [
        ("Flagged", "flagged", {"attention": "flagged"}),
        ("Watchlist", "watchlist", {"attention": "watchlist"}),
        ("Follow-ups due", "due", {"due": True}),
    ]
    for column, (title, count_key, filters) in zip(st.columns(3), manual_cards, strict=True):
        with column:
            st.button(
                f"{title} · {summary.get(count_key, 0)}",
                use_container_width=True,
                on_click=_filter_roster,
                args=(course_id, week, "Students", filters),
            )
    st.caption("Manual flags, watchlists and instructor priority never change model scores.")
    if workspace.get("as_of_day") is not None:
        basis = (
            "current course calendar"
            if workspace.get("current_course_day") is not None
            else "selected checkpoint; no current course calendar"
        )
        st.caption(
            "Current support records · follow-ups checked through course day "
            f"{workspace['as_of_day']} ({basis})."
        )
    st.caption(
        "These counts overlap: a high-attention student may also need review or have "
        "an ongoing case. They are not categories to add together."
    )
    unrun = int(summary.get("not_run", 0))
    queued = int(summary.get("queued", 0))
    failed = int(summary.get("failed", 0))
    if unrun or queued or failed:
        st.caption(
            f"Analysis progress · {unrun} not analyzed · {queued} queued/running "
            f"· {failed} failed. Refresh to check progress."
        )
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("Current support levels")
        raw = workspace.get("distribution", {})
        counts = {
            SUPPORT_LABELS[key]: int(raw.get(key, 0))
            for key in ("high", "medium", "low", "unavailable")
        }
        st.altair_chart(count_chart(counts, total), use_container_width=True)
        st.caption(
            "One category per enrolled student. Not assessed includes missing, pending "
            "or unsupported risk scores."
        )
        with st.expander("Read support-level counts"):
            _frame([{"Support level": key, "Students": value} for key, value in counts.items()])
    with right:
        st.subheader("Change from previous checkpoint")
        raw = workspace.get("movement", {})
        counts = {
            "Risk score increased": int(raw.get("increased", 0)),
            "Risk score similar": int(raw.get("stable", 0)),
            "Risk score decreased": int(raw.get("decreased", 0)),
            "No valid comparison": int(raw.get("not_comparable", 0)),
        }
        st.altair_chart(count_chart(counts, total), use_container_width=True)
        st.caption(
            "Change describes direction, not the current support level. Similar means "
            "within 0.5 risk-score points. Comparisons require the same model and policy; "
            "both charts use the same student-count scale."
        )
        with st.expander("Read change counts"):
            _frame([{"Change": key, "Students": value} for key, value in counts.items()])
    st.subheader("Review a student")
    items = workspace.get("items", [])
    lookup = st.text_input(
        "Find a student to open",
        placeholder="Learner ID only" if identity_mode() == "id_only" else "Name or learner ID",
        key=f"workspace_lookup_{course_id}_{week}",
    )
    if lookup:
        try:
            items = client.workspace(
                course_id,
                week=week,
                query=lookup,
                limit=25,
                privacy=identity_mode(),
                support_scope="current",
            ).get("items", [])
        except DashboardApiError as error:
            _show_error(error)
            items = []
    elif int(workspace.get("total", len(items))) > len(items):
        st.caption(
            "Showing the first students in review order. "
            "Search the full authorized course roster above."
        )
    if items:
        options = {item["learner_id"]: item for item in items}
        selected = st.selectbox(
            "Choose a student",
            list(options),
            format_func=lambda key: (
                f"{student_label(options[key])} · "
                f"{SUPPORT_LABELS.get(options[key].get('risk_band'), 'Not assessed')}"
            ),
            key=f"workspace_overview_pick_{course_id}_{week}",
        )
        st.button(
            "Open this student", type="primary", on_click=_open_profile, args=("Students", selected)
        )
    else:
        st.info("There are no student records at this checkpoint.")
    render_demo_guide(client, workspace.get("course", {}))
    render_analysis_controls(client, course_id, week)
    with st.expander("Course analysis queue · all weeks", expanded=False):
        render_course_analysis(client, course_id)


def _open_demo(course_id: str, week: int, learner_id: str) -> None:
    """Navigation only: no queue, record, policy or model-input changes."""
    st.session_state[f"workspace_week_{course_id}"] = week
    st.session_state.pop("workspace_context", None)
    st.session_state["workspace_demo_target"] = (course_id, week, learner_id)
    _open_profile("Students", learner_id)


def render_demo_guide(client: WorkspaceClient, course: dict[str, Any]) -> None:
    examples = demo_examples(course)
    if not examples:
        return
    course_id = course["presentation_id"]
    with st.expander("Synthetic scenario guide · what to inspect"):
        st.caption(
            "Fictional scenario design, not a model finding or accuracy claim. "
            "This guide is not sent to the predictor. Open a record to inspect its "
            "actual evidence and saved analysis; opening never queues or edits anything."
        )
        selected = st.selectbox(
            "Demonstration example", range(len(examples)),
            format_func=lambda index: examples[index]["title"],
            key=f"workspace_demo_{course_id}",
        )
        example = examples[selected]
        st.write(example["check"])
        st.caption(f"Learner ID: {example['learner_id']} · week {example['week']}")
        # Check the authorized API: a small or customized imported cohort may not
        # include every generator example. Never invent a roster entry.
        try:
            client.learner(course_id, example["learner_id"], week=example["week"],
                           privacy=identity_mode())
        except DashboardApiError as error:
            _show_error(error)
        else:
            st.button(
                "Open demonstration record", key=f"workspace_demo_open_{course_id}",
                on_click=_open_demo,
                args=(course_id, example["week"], example["learner_id"]),
            )
        st.markdown("**Missing-feed check · separate controlled test**")
        st.write(
            "The main demo cohort has complete applicable feeds. Missing-feed variants "
            "are tested separately: absent grades or activity remain unavailable, never "
            "zero. If essential evidence is insufficient, the system abstains without "
            "a risk score. Refresh does not create or repair missing source records."
        )
        st.caption("Operator walkthrough and test references: docs/21_instructor_demo_guide.md")


def render_roster(
    client: WorkspaceClient, course_id: str, week: int, *, cases_only: bool = False
) -> None:
    st.subheader("Support cases" if cases_only else "Students")
    scope = f"{course_id}_{week}_{cases_only}"
    defaults = roster_defaults(cases_only)
    saved_filters = st.session_state.get(f"workspace_filter_{scope}", defaults)
    if not isinstance(saved_filters, dict):
        saved_filters = dict(zip(("search", "risk", "status"), saved_filters, strict=False))
    saved_filters = defaults | saved_filters
    # Widget keys are discarded by Streamlit when their page is not rendered.
    # The separate filter snapshot lets Back restore the instructor's list.
    for name, value in saved_filters.items():
        widget_key = f"workspace_{name}_{scope}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = value
    if identity_mode() == "id_only" and st.session_state[f"workspace_sort_{scope}"] == "name":
        st.session_state[f"workspace_sort_{scope}"] = "learner_id"
    search, level, status = st.columns([1.5, 1, 1])
    with search:
        query = st.text_input(
            "Find student",
            placeholder="Learner ID only" if identity_mode() == "id_only" else "Name or learner ID",
            key=f"workspace_search_{scope}",
        )
    with level:
        risk = st.selectbox(
            "Support level",
            ["", "high", "medium", "low", "unavailable"],
            format_func=lambda key: "All levels" if not key else SUPPORT_LABELS[key],
            key=f"workspace_risk_{scope}",
        )
    with status:
        case_status = st.selectbox(
            "Case status",
            ["", "new", "reviewed", "ongoing", "resolved", "dismissed"],
            format_func=lambda key: label(key) if key else "All statuses",
            key=f"workspace_status_{scope}",
        )
    attention_col, priority_col, order_col = st.columns(3)
    attention_labels = {
        "": "All students",
        "needs_review": "Needs review",
        "flagged": "Manually flagged",
        "watchlist": "On the course watchlist",
        "insufficient_data": "Insufficient evidence",
    }
    with attention_col:
        attention = st.selectbox(
            "Review filter",
            list(attention_labels),
            format_func=attention_labels.get,
            key=f"workspace_attention_{scope}",
        )
    with priority_col:
        priority = st.selectbox(
            "Instructor priority",
            ["", *PRIORITY_LABELS],
            format_func=lambda value: PRIORITY_LABELS.get(value, "All priorities"),
            key=f"workspace_priority_{scope}",
        )
    with order_col:
        order = st.selectbox(
            "Sort students",
            [value for value in ROSTER_SORTS if value != "name" or identity_mode() != "id_only"],
            format_func=ROSTER_SORTS.get,
            key=f"workspace_sort_{scope}",
        )
    due_col, active_col = st.columns(2)
    with due_col:
        due = st.checkbox("Follow-ups due only", key=f"workspace_due_{scope}")
    with active_col:
        active = st.checkbox(
            "Active support cases only",
            key=f"workspace_active_{scope}",
            help="Includes new, reviewed and ongoing cases. Uncheck to include closed cases.",
        )
    fingerprint = {
        "search": query,
        "risk": risk,
        "status": case_status,
        "attention": attention,
        "priority": priority,
        "sort": order,
        "due": due,
        "active": active,
    }
    previous_filter = st.session_state.get(f"workspace_filter_{scope}")
    if previous_filter != fingerprint:
        st.session_state[f"workspace_filter_{scope}"] = fingerprint
        st.session_state[f"workspace_offset_{scope}"] = 0
    offset = st.session_state.get(f"workspace_offset_{scope}", 0)
    try:
        page = client.workspace(
            course_id,
            week=week,
            query=query,
            risk=risk,
            status=case_status,
            needs_review=attention == "needs_review",
            flagged=attention == "flagged",
            watchlist=attention == "watchlist",
            insufficient_data=attention == "insufficient_data",
            priority=priority,
            due=due,
            active_cases=active,
            sort=order,
            privacy=identity_mode(),
            support_scope="current",
            offset=offset,
            limit=25,
        )
    except DashboardApiError as error:
        _show_error(error)
        return
    items = page.get("items", [])
    total = int(page.get("total", len(items)))
    if offset and offset >= total:
        st.session_state[f"workspace_offset_{scope}"] = max(0, ((total - 1) // 25) * 25)
        st.rerun()
    st.caption(
        f"{total} matching student(s). Showing {offset + 1 if items else 0}–{offset + len(items)}."
    )
    if not items:
        st.info("No students match these filters. Clear a filter or the search to widen the list.")
    else:
        rows = [
            {
                "Student": student_label(item),
                "Instructor triage": triage_label(item.get("triage")),
                "Support level": SUPPORT_LABELS.get(item.get("risk_band"), "Not assessed"),
                "Risk score": points(item.get("risk_score")),
                "Previous → current": comparison(
                    item.get("risk_score"),
                    item.get("previous_score"),
                    comparable=item.get("comparable", False),
                ),
                "Analysis": label(item.get("analysis_status", "not_run")),
                "Model": model_label(item.get("model_version")),
                "Case": label(item.get("case_status")) if item.get("case_status") else "No case",
                "Follow-up due": f"Course day {item['follow_up_day']}"
                if item.get("follow_up_day") is not None
                else "Not scheduled",
            }
            for item in items
        ]
        filter_json = json.dumps(fingerprint, sort_keys=True).encode()
        filter_id = hashlib.sha256(filter_json).hexdigest()[:12]
        table_key = f"workspace_roster_table_{scope}_{offset}_{filter_id}_{identity_mode()}"
        st.dataframe(
            pd.DataFrame(rows),
            hide_index=True,
            use_container_width=True,
            selection_mode="single-row",
            key=table_key,
            on_select=lambda: _open_selected_row(
                table_key,
                [item["learner_id"] for item in items],
                "Support cases" if cases_only else "Students",
            ),
        )
        st.caption(
            "Select a row to open the student. Filters and page are kept when you go back. "
            "Swipe or scroll for more columns."
        )
        choices = {item["learner_id"]: student_label(item) for item in items}
        selected = st.selectbox(
            "Student to open",
            list(choices),
            format_func=choices.get,
            key=f"workspace_roster_pick_{scope}_{offset}",
        )
        st.button(
            "Open student profile",
            type="primary",
            on_click=_open_profile,
            args=("Support cases" if cases_only else "Students", selected),
        )
    previous, following = st.columns(2)
    with previous:
        if st.button("Previous 25", disabled=offset == 0, key=f"workspace_prev_{scope}"):
            st.session_state[f"workspace_offset_{scope}"] = max(0, offset - 25)
            st.rerun()
    with following:
        if st.button(
            "Next 25", disabled=offset + len(items) >= total, key=f"workspace_next_{scope}"
        ):
            st.session_state[f"workspace_offset_{scope}"] = offset + 25
            st.rerun()


def render_analysis_controls(
    client: WorkspaceClient, course_id: str, week: int, learner_id: str | None = None
) -> None:
    with st.expander("Run model analysis", expanded=False):
        st.write(
            "The LLM reads the selected checkpoint's course context and evidence. "
            "Validated results appear after the worker finishes."
        )
        st.caption(
            f"Scope: {'this student' if learner_id else 'all students in this course'}, "
            f"week {week} only. Refresh workspace only reloads saved results; "
            "queuing requests model work and reuses matching existing jobs/results. "
            "It does not refresh the LMS source data."
        )
        st.caption(
            "Risk scores are currently uncalibrated 0–100 outputs, not probabilities of "
            "failure. Validation checks structure and cited evidence; it does not prove "
            "predictive accuracy."
        )
        model_kind = st.selectbox(
            "Analysis model",
            ["llm", "baseline"],
            format_func=lambda key: (
                "Qwen instruction model" if key == "llm" else "Temporary rules baseline"
            ),
            key=f"workspace_model_{course_id}_{week}_{learner_id}",
        )
        if st.button(
            "Queue student analysis" if learner_id else "Queue checkpoint analysis",
            key=f"workspace_analyze_{course_id}_{week}_{learner_id}",
        ):
            try:
                result = client.analyze(
                    course_id,
                    week=week,
                    model_kind=model_kind,
                    learner_ids=[learner_id] if learner_id else None,
                )
            except DashboardApiError as error:
                _show_error(error)
            else:
                st.session_state["workspace_flash"] = (
                    f"Analysis requested: {result.get('queued', len(result.get('job_ids', [])))} "
                    "job(s). Refresh to view the result."
                )
                st.rerun()


def render_course_analysis(client: WorkspaceClient, course_id: str) -> None:
    render_course_progress(client, course_id)
    render_automation_setting(client, course_id)


@st.fragment(run_every=10)
def render_course_progress(client: WorkspaceClient, course_id: str) -> None:
    """Course-wide progress is kept distinct from selected-checkpoint student counts."""
    st.divider()
    st.subheader("LLM analysis · every course checkpoint")
    st.caption(
        "These are student-checkpoint records across all weeks, not unique student counts. "
        "Only the current approved Qwen model and policy count as LLM analysis; "
        "a rules-baseline result does not mark a record as analyzed by the LLM."
    )
    st.caption(
        "This analysis panel refreshes automatically every 10 seconds while this page is open. "
        "Student cards and profiles update when you choose Refresh workspace or navigate."
    )
    try:
        status = client.analysis_status(course_id)
    except DashboardApiError as error:
        _show_error(error)
        st.caption("The progress read failed. Previously displayed counts are not being confirmed.")
        return
    served_at = status.get("served_at")
    read_at = datetime.now(UTC).strftime("%d %b %Y, %H:%M:%S UTC")
    verified_read = timestamp(served_at, seconds=True) if served_at else read_at
    st.caption(f"Latest verified progress read: {verified_read}")
    summary = status.get("summary", {})
    total = int(summary.get("total_snapshots", 0))
    validated = int(summary.get("validated", 0))
    abstained = int(summary.get("abstained", 0))
    queued = int(summary.get("queued", 0))
    running = int(summary.get("running", 0))
    retries = int(summary.get("retry_scheduled", 0))
    failed = int(summary.get("failed", 0))
    render_cards(
        [
            (
                "LLM analysis completed",
                f"{validated + abstained:,} / {total:,}",
                f"{validated:,} validated results; {abstained:,} abstentions without a risk score.",
            ),
            (
                "Queued / running",
                f"{queued:,} / {running:,}",
                f"{retries:,} retries scheduled. This panel updates automatically.",
            ),
            (
                "Awaiting queue",
                str(summary.get("unassessed", 0)),
                "Records without a current LLM result or pending job. Failed jobs are separate.",
            ),
            ("Failed analysis", str(failed), "See the cause and recommended next step below."),
        ]
    )
    if total:
        st.progress(
            min(1.0, (validated + abstained) / total),
            text="Course-wide LLM completion · validated results and explicit abstentions",
        )
    if summary.get("baseline_only", 0):
        st.caption(
            f"{summary['baseline_only']:,} records have a temporary rules result but no current "
            "LLM assessment. They may already be queued; this is not an additional record count."
        )
    model, worker = status.get("model", {}), status.get("worker", {})
    course_control = status.get("course_control", {})
    st.write(
        f"**Model:** {model.get('model', 'Qwen')} · {label(model.get('status'))}  \n"
        f"**Analysis worker:** {label(worker.get('status'))}"
    )
    heartbeat_age = worker.get("heartbeat_age_seconds")
    age_text = f" · {int(heartbeat_age)} seconds ago" if heartbeat_age is not None else ""
    st.caption(
        f"Last worker heartbeat: {timestamp(worker.get('heartbeat_at'), seconds=True)}{age_text}"
    )
    if worker.get("status") == "heartbeat_stale":
        st.warning(
            "The worker has not reported within its expected activity window. "
            "The server operator should check worker status and logs; refreshing or "
            "queuing more work does not restart a stopped worker."
        )
    if worker.get("is_processing_this_course") is True:
        st.caption("The worker is currently processing this course.")
    elif worker.get("processing_another_course") is True:
        st.caption(
            "The shared worker is processing another course. "
            + (
                "This course has pending work waiting for the worker."
                if queued + running + retries > 0
                else "This course currently has no queued or running work."
            )
        )
    if resume_is_pending(course_control):
        st.info(
            "A resume request for this course has been recorded. The worker has not yet "
            "acknowledged it. The heartbeat above is the last actual worker update."
        )
    if model.get("status") != "ready":
        st.info(
            "You can queue work now. Analysis will start when the model service and "
            "worker are available. Queued work is not a completed prediction."
        )
    if worker.get("pause_until"):
        st.caption(f"Worker retry pause until {timestamp(worker['pause_until'])}.")
    service_code = worker.get("last_error_code") or model.get("error_code")
    if service_code:
        service_failure = describe_failure(service_code)
        st.warning(f"{service_failure['title']}: {service_failure['detail']}")
        st.write(f"**Next step:** {service_failure['action']}")
    if worker.get("status") == "paused":
        st.warning(
            "The shared analysis service is paused. The server operator must resolve and "
            "resume this shared pause; a course resume cannot clear it."
        )
        if worker.get("pause_scope") == "legacy_validation":
            st.caption("This is an earlier shared validation pause that requires operator review.")
    if course_control.get("status") == "paused":
        st.warning(
            "Automatic analysis is paused for this course after repeated validation failures. "
            "Other courses can continue. Check the error before requesting a course resume."
        )
        if course_control.get("last_error_code"):
            course_failure = describe_failure(course_control["last_error_code"])
            st.write(f"**Course pause reason:** {course_failure['title']}")
            st.write(f"**Next step:** {course_failure['action']}")
            st.code(course_failure["code"], language=None)
        st.caption(
            f"Consecutive failures: {course_control.get('failure_streak', 0)} "
            f"· course control updated {timestamp(course_control.get('updated_at'))}"
        )
        if st.button(
            "Resume this course after checking the error", key=f"workspace_resume_{course_id}"
        ):
            try:
                client.resume_analysis(course_id)
            except DashboardApiError as error:
                _show_error(error)
            else:
                st.session_state["workspace_flash"] = (
                    "Course resume requested. The worker still checks service health; "
                    "a request does not confirm that processing has restarted."
                )
                st.rerun()
    st.caption(
        "Scope: every prepared week in this course. Analyze adds unassessed records; "
        "matching completed and pending work is reused. Retry only requeues failed "
        "records within the attempt limit. Neither button clears a protective pause."
    )
    left, right = st.columns(2)
    with left:
        if st.button(
            "Analyze all unassessed checkpoints",
            type="primary",
            disabled=total == 0 or int(summary.get("unassessed", 0)) == 0,
            help="Queue missing current LLM assessments across all prepared weeks; "
            "this does not import new LMS records or force reruns of completed results.",
            key=f"workspace_catchup_{course_id}",
        ):
            _queue_batch(client, course_id, "unassessed")
    with right:
        if st.button(
            "Retry eligible failed analysis",
            disabled=failed == 0,
            help="Check the failure details first. Repeated attempts cannot repair "
            "missing source data, configuration or an invalid output contract.",
            key=f"workspace_retry_failed_{course_id}",
        ):
            _queue_batch(client, course_id, "retry_failed")
    st.caption(
        f"Retries respect a maximum of {status.get('max_attempts', 3)} attempts. "
        "Configuration or validation failures may require a correction before retrying."
    )
    failures = status.get("failures", [])
    if failures:
        st.markdown("#### Why analysis failed")
        for failure in failures:
            st.error(
                f"{failure.get('count', 0)} record(s) · {failure.get('title', 'Analysis failed')}"
            )
            if failure.get("detail"):
                st.write(failure["detail"])
            if failure.get("action"):
                st.write(f"**Next step:** {failure['action']}")
            st.caption("Diagnostic code · use the copy control to share this with the operator")
            st.code(failure.get("code", "ANALYSIS_UNKNOWN_ERROR"), language=None)
            render_failure_samples(failure.get("diagnostic_samples", []))
    if status.get("weeks"):
        with st.expander("Progress by course week"):
            _frame([{label(key): value for key, value in row.items()} for row in status["weeks"]])


def render_automation_setting(client: WorkspaceClient, course_id: str) -> None:
    """Keep unsaved instructor choices outside the timed progress fragment."""
    try:
        automation = client.analysis_status(course_id).get("automation", {})
    except DashboardApiError as error:
        _show_error(error)
        return
    with st.form(f"workspace_automation_{course_id}_{automation.get('version', 1)}"):
        enabled = st.checkbox(
            "Automatically analyze new or changed checkpoint records",
            value=automation.get("enabled", True),
        )
        st.caption(
            "Applies to this course. New records and policy changes are picked up "
            "when the analysis worker and model are ready. Already assessed records are reused."
        )
        save = st.form_submit_button("Save automatic analysis setting")
    if save:
        try:
            client.save_automation(course_id, enabled=enabled, version=automation.get("version", 1))
        except DashboardApiError as error:
            _show_error(error)
        else:
            st.session_state["workspace_flash"] = (
                "Automatic course analysis enabled."
                if enabled
                else "Automatic discovery disabled. Work already queued may still finish."
            )
            st.rerun()


def render_failure_samples(samples: list[dict[str, Any]]) -> None:
    """Show only server-sanitized field details, never model replies or learner identifiers."""
    with st.expander("Exact validation details · recent samples"):
        st.caption(
            "Up to three current failure jobs and two model responses per job are shown. "
            "These are diagnostic samples, not a complete evaluation of every failure."
        )
        if not samples:
            st.info("Older attempt detail unavailable. No field-level diagnostic was retained.")
            return
        for index, sample in enumerate(samples[:3], 1):
            st.markdown(
                f"**Sample {index} · job attempt {sample.get('job_attempt') or 'not recorded'}**"
            )
            st.caption("Job reference for the operator")
            st.code(sample.get("job_id", "Not recorded"), language=None)
            detail_rows, normalization_rows = [], []
            generations = sample.get("generations", [])[:2]
            for generation in generations:
                stage = (
                    "Initial response"
                    if generation.get("kind") == "initial"
                    else "Validation feedback"
                )
                for detail in generation.get("validation_details", []):
                    detail_rows.append(
                        {
                            "Response": generation.get("attempt"),
                            "Stage": stage,
                            "Field": detail.get("path", "Not recorded"),
                            "Problem": detail.get("code", "Not recorded"),
                            "Expected": detail.get("expected", "Not recorded"),
                            "Received type": detail.get("received_type", "Not recorded"),
                            "Safe received value": json.dumps(
                                detail["received"], ensure_ascii=False
                            )
                            if "received" in detail
                            else "Not retained",
                        }
                    )
                for normalization in generation.get("normalizations", []):
                    normalization_rows.append(
                        {
                            "Response": generation.get("attempt"),
                            "Stage": stage,
                            "Field": normalization.get("path", "Not recorded"),
                            "Normalization": normalization.get("code", "Not recorded"),
                        }
                    )
            if detail_rows:
                _frame(detail_rows)
            else:
                st.info(
                    "Older attempt detail unavailable. The failure code was retained, "
                    "but this sample has no field-level diagnostic."
                )
            if normalization_rows:
                st.caption("Recorded normalizations")
                _frame(normalization_rows)


def _queue_batch(client: WorkspaceClient, course_id: str, mode: str) -> None:
    try:
        result = client.batch_analysis(course_id, mode=mode, scope="all_weeks")
    except DashboardApiError as error:
        _show_error(error)
    else:
        st.session_state["workspace_flash"] = (
            f"Added {result.get('queued', 0)} record(s) to the LLM queue. "
            f"{result.get('already_queued', 0)} already queued; "
            f"{result.get('already_assessed', 0)} already assessed; "
            f"{result.get('failed_skipped', 0)} failures need attention; "
            f"{result.get('exhausted', 0)} reached the attempt limit."
        )
        st.rerun()


def comparable_results(current: dict[str, Any] | None, previous: dict[str, Any] | None) -> bool:
    if not current or not previous:
        return False
    if any(
        current.get(key) is None or current.get(key) != previous.get(key)
        for key in ("model_version", "policy_version")
    ):
        return False
    return all(
        current.get(key) == previous.get(key)
        for key in ("model_digest", "prompt_version", "calibration_version", "feature_version")
    )


def fact_value(fact: dict[str, Any]) -> str:
    value = fact.get("value")
    if value is None:
        return label(fact.get("status", "source_missing"))
    unit = fact.get("unit", "")
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
    else:
        text = str(value)
    return f"{text} {unit}".strip()


def render_profile(
    client: WorkspaceClient, course_id: str, week: int, learner_id: str, policy: dict[str, Any]
) -> None:
    try:
        detail = client.learner(course_id, learner_id, week=week, privacy=identity_mode())
    except DashboardApiError as error:
        _show_error(error)
        return
    st.subheader(student_label(detail | {"learner_id": learner_id}))
    st.caption(f"Learner ID: {learner_id} · selected checkpoint: week {week}")
    st.caption(course_expectations(policy))
    snapshot = detail.get("snapshot") or {}
    analysis = detail.get("analysis") or {}
    previous = detail.get("previous_analysis") or {}
    output = _output(analysis)
    older_policy = bool(analysis and analysis.get("policy_version") != policy.get("version"))
    state_status = (
        detail.get("analysis_status")
        or analysis.get("status")
        or ("abstained" if output.get("abstain") else "validated" if output else "not_run")
    )
    if older_policy and state_status not in {"queued", "running", "failed"}:
        state_status = "outdated"
    current_valid = state_status == "validated" and snapshot.get("is_fresh") is True
    risk = output.get("risk_score") if current_valid else None
    risk_band = output.get("risk_band") if current_valid else None
    change_value, change_detail = comparison_card(
        risk,
        _output(previous).get("risk_score"),
        detail.get("comparable", comparable_results(analysis, previous)),
        detail.get("previous_week"),
    )
    case = detail.get("current_case", detail.get("case")) or {}
    render_cards(
        [
            (
                "Current support level",
                SUPPORT_LABELS.get(risk_band, "Not assessed"),
                "Based on the selected checkpoint only.",
            ),
            ("Risk score", points(risk), "Uncalibrated model output; not a probability."),
            (
                "Previous → current",
                change_value,
                change_detail,
            ),
            (
                "Current case status",
                label(case.get("status")) if case else "No case",
                "Support history continues across checkpoints.",
            ),
        ]
    )
    render_triage(client, course_id, learner_id, detail.get("triage") or {})
    st.write(f"**Analysis status:** {label(state_status)}")
    if state_status in {"queued", "running"}:
        st.info("Analysis is in progress. Refresh the workspace to check the result.")
    elif state_status == "abstained":
        st.warning(
            "No risk score was issued. "
            f"{output.get('abstention_reason') or 'Evidence was insufficient.'}"
        )
    elif state_status in {"failed", "outdated"}:
        st.warning(
            "A current validated result is unavailable. Check data/model health and "
            "request analysis again when ready."
        )
    if state_status == "failed":
        failure = detail.get("job_error_detail") or describe_failure(detail.get("job_error"))
        st.error(failure.get("title", "Analysis failed"))
        st.write(failure.get("detail", "The saved job did not produce a validated result."))
        st.write(f"**Next step:** {failure.get('action', 'Check data and model health.')} ")
        st.caption(f"Diagnostic code: {failure.get('code', 'ANALYSIS_UNKNOWN_ERROR')}")
    if analysis:
        st.write(f"**Result source:** {model_label(analysis.get('model_version'))}")
        if analysis.get("model_kind") == "llm" and analysis.get("inference_performed") is False:
            st.info(
                "The data-quality gate abstained before calling Qwen. "
                "This is a system safety decision, not an LLM prediction."
            )
        for limitation in analysis.get("data_limitations", []):
            st.caption(f"Evidence limitation: {limitation}")
        with st.expander("Result version and validation details"):
            st.caption(
                f"Result model: {analysis.get('model_version', 'Not recorded')} "
                f"· policy revision {analysis.get('policy_version', 'Not recorded')} "
                f"· generated {timestamp(analysis.get('generated_at'))}"
            )
            render_validation_provenance(analysis)
    if snapshot and snapshot.get("is_fresh") is False:
        st.warning("The selected snapshot is marked stale. Confirm its evidence before acting.")
    tabs = st.tabs(
        ["Evidence and recommendations", "Academic progress", "Risk history", "Support history"]
    )
    with tabs[0]:
        st.caption(
            f"Historical evidence checkpoint: week {week}, through course day {week * 7 - 1}. "
            "Current instructor triage and support records above do not alter this evidence."
        )
        render_evidence_summary(snapshot)
        if current_valid:
            render_claims(output, snapshot)
        elif output:
            with st.expander("Last saved analysis · historical result"):
                st.caption(
                    "This saved result is not a current assessment under the selected "
                    "status and policy."
                )
                render_claims(output, snapshot)
        baseline = detail.get("baseline_analysis")
        if baseline and analysis.get("model_version") != baseline.get("model_version"):
            with st.expander("Compare the LLM with the temporary rules baseline"):
                _frame(
                    [
                        {
                            "Model": model_label(item.get("model_version")),
                            "Risk score": points(_output(item).get("risk_score")),
                            "Evidence claims": len(_output(item).get("claims", [])),
                            "Policy revision": item.get("policy_version"),
                        }
                        for item in (analysis, baseline)
                    ]
                )
                st.caption(
                    "Both results refer to this checkpoint. Inspect policy revisions "
                    "before comparing. Agreement is not proof of accuracy."
                )
        if not output:
            st.info(
                "Analysis has not produced a result for this checkpoint. You can still "
                "inspect recorded evidence and open a manual concern."
            )
        with st.expander("All checkpoint evidence and availability"):
            _frame(
                [
                    {
                        "Feature": label(name),
                        "Value": fact_value(fact),
                        "Availability": label(fact.get("status")),
                        "Window": fact.get("window", ""),
                        "Available by course day": fact.get("available_day"),
                    }
                    for name, fact in snapshot.get("features", {}).items()
                ]
            )
        render_analysis_controls(client, course_id, week, learner_id)
    with tabs[1]:
        render_academic_progress(detail)
    with tabs[2]:
        render_risk_history(detail.get("history", []))
    with tabs[3]:
        render_case(client, course_id, week, learner_id, detail)


def render_evidence_summary(snapshot: dict[str, Any]) -> None:
    features = snapshot.get("features", {})
    candidates = [
        ("Assessed grades", "weighted_grade_percent"),
        ("Missed assessed work", "assessments_missed"),
        ("Required completion (%)", "completion_percent"),
    ]
    # Show missingness explicitly. A missing fact must never become zero or success.
    for column, (title, name) in zip(st.columns(3), candidates, strict=True):
        with column:
            fact = features.get(name) or {"value": None, "status": "not_available"}
            if (
                name == "completion_percent"
                and snapshot.get("feature_version") != "rich-features-v3"
            ):
                fact = {"value": None, "status": "unverified_required_metadata"}
            st.metric(title, fact_value(fact))
            st.caption(label(fact.get("status", "not_available")))
    if snapshot.get("feature_version") not in {None, "rich-features-v3"}:
        st.caption(
            "Historical feature definitions: inspect the academic evidence before treating "
            "grades as assessed or resources as required."
        )


def _save_triage(
    client: WorkspaceClient,
    course_id: str,
    learner_id: str,
    triage: dict[str, Any],
    **changes: Any,
) -> None:
    payload = {
        "expected_version": triage.get("version", 0),
        "flagged": bool(triage.get("flagged", False)),
        "watchlisted": bool(triage.get("watchlisted", False)),
        "priority": triage.get("priority", "normal"),
        "note": triage.get("note", ""),
    } | changes
    try:
        client.save_triage(
            course_id,
            learner_id,
            payload,
            idempotency_key=mutation_key(f"triage_{course_id}_{learner_id}", payload),
        )
    except DashboardApiError as error:
        _show_error(error)
    else:
        st.session_state["workspace_flash"] = (
            "Instructor triage saved. The model score and evidence are unchanged."
        )
        st.rerun()


def render_triage(
    client: WorkspaceClient, course_id: str, learner_id: str, triage: dict[str, Any]
) -> None:
    st.caption(f"Instructor triage · {triage_label(triage)} · separate from the model score")
    flag, watch, priority = st.columns([1, 1, 2])
    with flag:
        if st.button(
            "Remove manual flag" if triage.get("flagged") else "Flag for review",
            use_container_width=True,
        ):
            _save_triage(
                client, course_id, learner_id, triage, flagged=not triage.get("flagged", False)
            )
    with watch:
        if st.button(
            "Remove from watchlist" if triage.get("watchlisted") else "Add to watchlist",
            use_container_width=True,
        ):
            _save_triage(
                client,
                course_id,
                learner_id,
                triage,
                watchlisted=not triage.get("watchlisted", False),
            )
    with priority, st.expander("Set priority / instructor note"):
        with st.form(f"workspace_triage_{course_id}_{learner_id}_{triage.get('version', 0)}"):
            current = triage.get("priority", "normal")
            selected = st.selectbox(
                "Manual priority",
                list(PRIORITY_LABELS),
                index=list(PRIORITY_LABELS).index(current) if current in PRIORITY_LABELS else 1,
                format_func=PRIORITY_LABELS.get,
            )
            note = st.text_area(
                "Instructor triage note", value=triage.get("note", ""), max_chars=2000
            )
            st.caption(
                "Shared with authorized course instructors. "
                "This is not model evidence or a support action."
            )
            submitted = st.form_submit_button("Save instructor priority")
        if submitted:
            _save_triage(
                client, course_id, learner_id, triage, priority=selected, note=note.strip()
            )


def render_validation_provenance(analysis: dict[str, Any]) -> None:
    attempts = safe_attempts(analysis.get("inference_attempts") or [])
    outcome = analysis.get("validation_outcome")
    if not attempts and not outcome:
        return
    if analysis.get("wire_contract_version") == "risk-decision-v3":
        st.caption("Model output contract: risk-decision-v3.")
    if analysis.get("risk_band_origin") == "server_thresholds":
        st.caption(
            "The model supplies the risk score. The server assigns its support level "
            "using the documented score thresholds; this label is deterministic."
        )
    descriptions = {
        "first_pass_validated": "Validated on the first model response",
        "repaired_validated": "Validated after a model correction",
        "quality_abstained": "Quality gate abstained before model inference",
    }
    st.write(f"**Output validation:** {descriptions.get(outcome, label(outcome))}")
    if outcome == "repaired_validated":
        st.caption(
            "The model received structured feedback about a rejected response and made "
            "a bounded correction. Passing structure and evidence checks does not "
            "establish that the prediction is accurate."
        )
    elif outcome == "first_pass_validated":
        st.caption(
            "The first response passed structure and evidence checks; "
            "predictive accuracy is evaluated separately."
        )
    if attempts:
        with st.expander("Model response and correction history"):
            _frame(
                [
                    {
                        "Attempt": attempt.get("attempt"),
                        "Stage": "Initial response"
                        if attempt.get("kind") == "initial"
                        else "Validation feedback",
                        "Outcome": label(attempt.get("outcome")),
                        "Time (seconds)": attempt.get("latency_seconds"),
                        "Validation code": attempt.get("error_code") or "None",
                    }
                    for attempt in attempts
                ]
            )
            st.caption("These records describe model response validation, not student progress.")
            normalizations = [
                {
                    "Response": attempt["attempt"],
                    "Field": entry["path"],
                    "Formatting normalization": entry["code"],
                }
                for attempt in attempts
                for entry in attempt.get("normalizations", [])
            ]
            if normalizations:
                st.caption(
                    "Audited formatting normalizations are separate from a model correction "
                    "or an evidence check. They are not evidence of predictive accuracy."
                )
                _frame(normalizations)


def render_claims(output: dict[str, Any], snapshot: dict[str, Any]) -> None:
    evidence = {
        fact["evidence_id"]: (name, fact) for name, fact in snapshot.get("features", {}).items()
    }
    if output.get("claims"):
        st.markdown("#### Reasons and supporting evidence")
    for claim in output.get("claims", []):
        code = claim.get("code", claim.get("claim_code", "Recorded evidence"))
        lines = []
        for evidence_id in claim.get("evidence_ids", []):
            item = evidence.get(evidence_id)
            if item is None:
                lines.append("Supporting evidence is unavailable; this claim needs review.")
                continue
            name, fact = item
            lines.append(
                f"{label(name)}: {fact_value(fact)} "
                f"· {fact.get('window', 'through checkpoint')} · {label(fact.get('status'))}"
            )
        st.markdown(
            '<div class="dt-evidence"><strong>'
            + html.escape(label(code))
            + "</strong><br>"
            + "<br>".join(html.escape(line) for line in lines)
            + "</div>",
            unsafe_allow_html=True,
        )
    actions = output.get("suggested_actions", [])
    if actions:
        st.markdown("#### Suggested instructor actions")
        for action in actions:
            st.write(f"• {label(action)}")
        st.caption(
            "These suggestions have not been performed. "
            "Record any action you take in Support history."
        )


def academic_grade_rows(detail: dict[str, Any]) -> list[dict[str, Any]]:
    """Keep practice and unknown classifications visible without calling them graded work."""
    cutoff = (detail.get("snapshot") or {}).get("cutoff_day")
    definitions = {
        row["assessment_id"]: row for row in detail.get("assessments", []) if "assessment_id" in row
    }
    categories = {
        "assessed": "Assessed work",
        "practice": "Practice / formative",
        "unclassified": "Unclassified",
    }
    rows = []
    for event in detail.get("events", []):
        if event.get("event_type") != "assessment_grade":
            continue
        if cutoff is not None and (
            event.get("available_day", cutoff + 1) > cutoff
            or event.get("course_day", cutoff + 1) > cutoff
        ):
            continue
        payload = event.get("payload", {})
        score, maximum = payload.get("score"), payload.get("max_score")
        if score is None or not maximum or float(maximum) <= 0:
            continue
        assessment_id = payload.get("assessment_id", "Assessment")
        definition = definitions.get(assessment_id, {})
        available = definition.get("available_day")
        if (
            not isinstance(available, int)
            or isinstance(available, bool)
            or (cutoff is not None and available > cutoff)
        ):
            definition = {}
        rows.append(
            {
                "Published course day": event.get("available_day", event.get("course_day")),
                "Grade (%)": 100 * float(score) / float(maximum),
                "Assessment": assessment_id,
                "Evidence type": categories[assessment_category(definition)],
            }
        )
    return rows


def render_resource_progress(snapshot: dict[str, Any]) -> None:
    features = snapshot.get("features", {})
    if not any("resource" in name or name == "completion_percent" for name in features):
        return
    st.markdown("#### Required learning resources")
    verified = (
        snapshot.get("feature_version") == "rich-features-v3"
        and snapshot.get("course_context", {}).get("evidence_semantics", {}).get("completion_basis")
        == "required_resources_due_by_checkpoint"
    )
    if not verified:
        st.info(
            "Historical completion data does not distinguish required, optional and not-yet-due "
            "resources. It is not used as required-work evidence by the current predictor."
        )
        return
    expected, completed = (
        features.get("resources_expected", {}),
        features.get("resources_completed", {}),
    )
    if expected.get("status") in {"observed", "structural_zero"} and completed.get("status") in {
        "observed",
        "structural_zero",
    }:
        if expected.get("value") == 0:
            st.info("No required learning resources are due yet. Completion is not a concern.")
        else:
            st.write(
                f"**{completed['value']} of {expected['value']} required resources completed** "
                "· due by this checkpoint"
            )
    else:
        st.info(
            "Required-resource completion is unavailable: expectations or completion evidence "
            "are incomplete. Unknown does not mean the student failed to complete the work."
        )
    _frame(
        [
            {
                "Resource context": title,
                "Value": fact_value(features[key]),
                "Availability": label(features[key].get("status")),
            }
            for key, title in (
                ("completion_percent", "Required resources due so far · completed (%)"),
                ("optional_resources_available", "Optional resources · excluded from requirement"),
                ("required_resources_not_due", "Required resources · not yet due"),
                (
                    "resources_expectation_unknown",
                    "Resources with unknown expectation / release metadata",
                ),
            )
            if key in features
        ]
    )
    st.caption("Optional and future-due resources do not lower required completion.")


def render_academic_progress(detail: dict[str, Any]) -> None:
    snapshot = detail.get("snapshot") or {}
    features = snapshot.get("features", {})
    verified_grades = (
        snapshot.get("feature_version") == "rich-features-v3"
        and snapshot.get("course_context", {}).get("evidence_semantics", {}).get("grade_basis")
        == "graded_assessments_only"
    )
    academic = [
        {
            "Academic evidence": label(name),
            "Value": fact_value(fact),
            "Availability": label(fact.get("status")),
            "Window": fact.get("window", ""),
        }
        for name, fact in features.items()
        if not name.startswith("practice_")
        and any(
            word in name.lower()
            for word in (
                "grade",
                "assessment",
                "submission",
                "quiz",
                "mastery",
                "deadline",
                "late",
                "exam",
                "assignment",
            )
        )
    ]
    activity = [
        {
            "Activity evidence": label(name),
            "Value": fact_value(fact),
            "Availability": label(fact.get("status")),
        }
        for name, fact in features.items()
        if any(
            word in name.lower()
            for word in (
                "active",
                "activity",
                "click",
                "forum",
                "attendance",
                "session",
                "engagement",
            )
        )
    ]
    events = detail.get("events", [])
    grade_rows = academic_grade_rows(detail)
    st.markdown("#### Grades and assessment progress")
    if snapshot.get("feature_version") == "rich-features-v2":
        st.info(
            "Historical grade summaries may mix assessed and practice work. The current predictor "
            "excludes those ambiguous latest-grade and trend fields; saved results stay unchanged."
        )
    if grade_rows:
        grade_chart = (
            alt.Chart(pd.DataFrame(grade_rows))
            .mark_circle(size=80)
            .encode(
                x=alt.X(
                    "Published course day:Q",
                    title="Grade available to the system · course day",
                    axis=alt.Axis(tickMinStep=1),
                ),
                y=alt.Y(
                    "Grade (%):Q",
                    scale=alt.Scale(domain=[0, 100], nice=False),
                    title="Grade (%)",
                ),
                color=alt.Color(
                    "Evidence type:N",
                    scale=alt.Scale(
                        domain=["Assessed work", "Practice / formative", "Unclassified"],
                        range=["#267769", "#b57b29", "#797f89"],
                    ),
                    legend=alt.Legend(orient="bottom", columns=1, labelLimit=0),
                ),
                shape=alt.Shape("Evidence type:N", legend=None),
                tooltip=[
                    "Assessment:N",
                    "Evidence type:N",
                    "Published course day:Q",
                    alt.Tooltip("Grade (%):Q", format=".1f"),
                ],
            )
            .properties(height=230)
        )
        st.altair_chart(grade_chart, use_container_width=True)
        st.caption(
            "Each dot is a published grade, categorized only from definitions available at this "
            "checkpoint. Practice and unclassified work are not assessed-grade concerns. "
            "All dots use the same 0–100% marks scale, not the risk-score scale."
        )
    if verified_grades:
        st.caption(
            "Assessed-grade summaries include positive-weight, non-practice assessments only."
        )
    if academic:
        _frame(academic)
    else:
        st.info("This source has not supplied academic features at this checkpoint.")
    practice = [
        {
            "Practice evidence": label(name.removeprefix("practice_")),
            "Value": fact_value(fact),
            "Availability": label(fact.get("status")),
        }
        for name, fact in features.items()
        if name.startswith("practice_")
    ]
    if practice:
        st.markdown("#### Practice and formative work")
        st.caption("Useful learning context, kept separate from assessed-grade risk evidence.")
        _frame(practice)
    render_resource_progress(snapshot)
    st.markdown("#### Engagement and attendance")
    if activity:
        _frame(activity)
    else:
        st.info("This source has not supplied activity features at this checkpoint.")
    activity_events = [event for event in events if event.get("event_type") == "activity"]
    if activity_events:
        activity_frame = pd.DataFrame(
            {"Course week": [int(event["course_day"]) // 7 + 1 for event in activity_events]}
        )
        activity_counts = (
            activity_frame.value_counts().rename("Recorded activity events").reset_index()
        )
        activity_chart = (
            alt.Chart(activity_counts)
            .mark_bar(color="#427c71")
            .encode(
                x=alt.X("Course week:O", title="Course week"),
                y=alt.Y(
                    "Recorded activity events:Q",
                    title="Recorded activity events",
                    axis=alt.Axis(tickMinStep=1),
                ),
                tooltip=["Course week:O", "Recorded activity events:Q"],
            )
            .properties(height=210)
        )
        st.altair_chart(activity_chart, use_container_width=True)
        st.caption(
            "This chart counts recorded activity events, not hours studied. Weeks with "
            "no rows need a coverage check before interpreting inactivity."
        )
    if events:
        with st.expander("Recorded events through this checkpoint"):
            _frame(
                [
                    {
                        key: json.dumps(value, ensure_ascii=False)
                        if isinstance(value, (dict, list))
                        else value
                        for key, value in event.items()
                    }
                    for event in events
                ]
            )
    st.caption(
        "Observed zeros, missing fields and work not yet due are distinct. "
        "Later records do not explain an earlier prediction."
    )


def render_risk_history(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("No risk-score history is available yet.")
        return
    frame_rows = []
    for row in rows:
        score = row.get("risk_score", _output(row).get("risk_score"))
        frame_rows.append(
            {
                "Checkpoint": row.get("checkpoint_week"),
                "Risk score": float(score) * 100 if score is not None else None,
                "Model": row.get("model_version", "Not recorded"),
                "Policy": str(row.get("policy_version", "Not recorded")),
                "Version fingerprint": hashlib.sha256(
                    json.dumps(
                        [
                            row.get(k)
                            for k in (
                                "model_digest",
                                "prompt_version",
                                "feature_version",
                                "calibration_version",
                            )
                        ]
                    ).encode()
                ).hexdigest()[:8],
                "Status": label(
                    row.get("status", "validated" if score is not None else "abstained")
                ),
            }
        )
    frame = pd.DataFrame(frame_rows)
    chart_frame = frame.dropna(subset=["Risk score", "Checkpoint"]).copy()
    if not chart_frame.empty:
        chart_frame["Model / policy"] = (
            chart_frame["Model"]
            + " / revision "
            + chart_frame["Policy"]
            + " / "
            + chart_frame["Version fingerprint"]
        )
        chart = (
            alt.Chart(chart_frame)
            .mark_line(point=True)
            .encode(
                x=alt.X("Checkpoint:Q", axis=alt.Axis(tickMinStep=1), title="Checkpoint week"),
                y=alt.Y(
                    "Risk score:Q",
                    scale=alt.Scale(domain=[0, 100], nice=False),
                    title="Risk score (0–100)",
                ),
                color=alt.Color("Model / policy:N", title="Comparable series"),
                tooltip=[
                    "Checkpoint:Q",
                    alt.Tooltip("Risk score:Q", format=".1f"),
                    "Model:N",
                    "Policy:N",
                ],
            )
            .properties(height=250)
        )
        st.altair_chart(chart, use_container_width=True)
    _frame(frame_rows)
    st.caption(
        "Separate series identify model or policy changes. A lower risk score is an "
        "observed model change, not proof that support caused improvement."
    )


def render_case(
    client: WorkspaceClient, course_id: str, week: int, learner_id: str, detail: dict[str, Any]
) -> None:
    case = detail.get("current_case", detail.get("case")) or {}
    cutoff = week * 7 - 1
    today = detail.get("current_course_day")
    default_day = today if isinstance(today, int) and 0 <= today <= 36500 else cutoff
    st.markdown("#### Instructor support record")
    st.caption(
        "This record belongs to the student and course, so it stays available across "
        "checkpoints. This is the current support history, even when viewing an earlier "
        "evidence checkpoint. Planned actions are not completed contact or support."
    )
    history = case.get("events", [])
    completed_actions = [
        event
        for event in history
        if event.get("action_state") == "completed"
        and event.get("action") in {"contact", "warning", "support", "resource", "follow_up"}
    ]
    if completed_actions:
        with st.expander("Did the recorded evidence improve after support?", expanded=True):
            selected_action = st.selectbox(
                "Completed action to compare",
                list(range(len(completed_actions))),
                format_func=lambda i: (
                    f"Day {completed_actions[i]['occurred_day']} · "
                    f"{label(completed_actions[i]['action'])}"
                ),
                key=f"workspace_follow_compare_{course_id}_{learner_id}_{week}",
            )
            action_day = completed_actions[selected_action]["occurred_day"]
            states = detail.get("snapshot_history", detail.get("history", []))
            before = [s for s in states if int(s["checkpoint_week"]) * 7 - 1 < action_day]
            after = [s for s in states if action_day < int(s["checkpoint_week"]) * 7 - 1 <= cutoff]
            if not before or not after:
                st.info(
                    "A checkpoint before the action and a later checkpoint are required. "
                    "Return at a later checkpoint when evidence is available."
                )
            else:
                prior, later = before[-1], after[-1]
                rows = []
                for name in (
                    "weighted_grade_percent",
                    "assessments_missed",
                    "active_days_last_7",
                    "completion_percent",
                ):
                    old = prior.get("features", {}).get(name, {})
                    new = later.get("features", {}).get(name, {})
                    delta = (
                        (new["value"] - old["value"])
                        if all(isinstance(f.get("value"), (float, int)) for f in (old, new))
                        else None
                    )
                    rows.append(
                        {
                            "Evidence": label(name),
                            f"Before · week {prior['checkpoint_week']}": fact_value(old),
                            f"Later · week {later['checkpoint_week']}": fact_value(new),
                            "Observed change": f"{delta:+.1f}"
                            if delta is not None
                            else "Not comparable",
                        }
                    )
                _frame(rows)
                st.caption(
                    "This is an observed before/after comparison, not proof that the intervention "
                    "caused a change. Grades and completion: higher is generally favorable; "
                    "missed work: lower is favorable. "
                    "More activity alone does not establish learning."
                )
    if history:
        _frame(
            [
                {
                    "Action date": f"Course day {event.get('occurred_day', '?')}",
                    "Evidence used": "Week "
                    + str(event.get("evidence_checkpoint_week", event.get("checkpoint_week", "?"))),
                    "Recorded at": timestamp(event.get("recorded_at")),
                    "Updates planned entry": event.get("resolves_event_id") or "New entry",
                    "Action": ACTION_LABELS.get(event.get("action"), label(event.get("action"))),
                    "Action state": label(event.get("action_state")),
                    "Case status": label(event.get("status", event.get("new_status"))),
                    "Note / outcome": event.get("note", ""),
                    "Resources": ", ".join(event.get("resource_ids", [])),
                    "Next follow-up": f"Course day {event['follow_up_day']}"
                    if event.get("follow_up_day") is not None
                    else "Not scheduled",
                    "Recorded by": event.get(
                        "actor", event.get("reviewer_id", event.get("actor_id", "Not recorded"))
                    ),
                }
                for event in history
            ]
        )
    else:
        st.info(
            "No instructor actions have been recorded. A manual concern can be opened "
            "even when the model has not raised an alert."
        )
    if detail.get("triage_history"):
        with st.expander("Instructor flag and priority history"):
            _frame(
                [
                    {
                        "Revision": event.get("version"),
                        "Triage": triage_label(event),
                        "Instructor note": event.get("note", ""),
                        "Recorded at": timestamp(event.get("recorded_at")),
                        "Recorded by": event.get("actor"),
                    }
                    for event in detail["triage_history"]
                ]
            )
    if case.get("follow_up_day") is not None:
        due = case["follow_up_day"]
        st.write(f"**Next follow-up:** course day {due}" + (" · due" if due <= default_day else ""))
        st.caption(
            f"Follow-up check uses course day {default_day}: "
            + (
                "current course calendar."
                if today is not None
                else "selected checkpoint; no verified current calendar."
            )
        )
    resources = {
        str(item.get("resource_id", item.get("id"))): item
        for item in detail.get("resources", [])
        if item.get("resource_id", item.get("id")) is not None
    }
    if resources:
        with st.expander("Available learning resources"):
            for resource in resources.values():
                st.write(f"**{resource.get('title', 'Learning resource')}**")
                if resource.get("description"):
                    st.write(resource["description"])
                if resource.get("content"):
                    st.write(resource["content"])
                url = str(resource.get("url", ""))
                if url.startswith(("https://", "http://")):
                    st.link_button("Open resource", url)
                st.caption(resource.get("topic", ""))
    scope = f"{course_id}_{learner_id}_{case.get('version', 0)}"
    resolved = {e.get("resolves_event_id") for e in history if e.get("resolves_event_id")}
    plans = {
        e["id"]: e
        for e in history
        if e.get("action_state") == "planned" and e.get("id") not in resolved
    }
    plan_id = st.selectbox(
        "Record a new entry or update a planned action",
        ["", *plans],
        format_func=lambda value: (
            "New entry"
            if not value
            else (
                f"Planned {ACTION_LABELS.get(plans[value].get('action'), 'action')} "
                f"· day {plans[value]['occurred_day']}"
            )
        ),
        key=f"workspace_plan_{scope}",
    )
    plan = plans.get(plan_id) or {}
    with st.form(f"workspace_case_{scope}_{plan_id}"):
        st.markdown("#### Add an action, follow-up or manual concern")
        action_col, state_col = st.columns(2)
        with action_col:
            action = st.selectbox(
                "Action type",
                list(ACTION_LABELS),
                format_func=ACTION_LABELS.get,
                index=list(ACTION_LABELS).index(plan.get("action", "contact")),
                disabled=bool(plan_id),
            )
        with state_col:
            action_state = st.selectbox(
                "Action state",
                ["completed", "cancelled"] if plan_id else ["completed", "planned", "cancelled"],
                format_func=label,
            )
        note = st.text_area(
            "Note and observed outcome",
            max_chars=2000,
            placeholder=(
                "Record the concern, what was done, and any observed improvement or "
                "continuing difficulty. Avoid unrelated personal details."
            ),
        )
        status_options = ["new", "reviewed", "ongoing", "resolved", "dismissed"]
        current_status = case.get("status", "ongoing")
        next_status = st.selectbox(
            "Case status after this entry",
            status_options,
            index=status_options.index(current_status) if current_status in status_options else 2,
            format_func=label,
        )
        st.caption(
            "Reviewed means the concern was checked. Ongoing means support or follow-up "
            "is still required. Resolved closes the case; its history remains."
        )
        day_col, follow_col = st.columns(2)
        with day_col:
            occurred = st.number_input(
                "Action date · course day",
                min_value=0,
                max_value=36500,
                value=default_day,
                step=1,
                help="When the action happened (or is planned), not the evidence cutoff.",
            )
        with follow_col:
            follow_enabled = st.checkbox(
                "Schedule a follow-up", value=case.get("follow_up_day") is not None
            )
            follow_day = st.number_input(
                "Follow-up due · course day",
                min_value=0,
                max_value=36500,
                value=min(36500, max(default_day + 7, int(case.get("follow_up_day") or 0))),
                step=1,
            )
        selected_resources = st.multiselect(
            "Resources provided or planned",
            list(resources),
            format_func=lambda key: resources[key].get("title", key),
        )
        st.caption(
            f"Selected evidence is from week {week}, through course day {cutoff}. "
            "Explicit action dates keep later follow-ups separate from earlier evidence. "
            "Notes are saved only when you press Save support record."
        )
        if today is None:
            st.caption(
                "No verified course calendar is available. Confirm the action's course day "
                "yourself; the default is the evidence cutoff, not today's date."
            )
        submitted = st.form_submit_button("Save support record", type="primary")
    if submitted:
        if not case and not note.strip():
            st.error("Describe the concern before opening a case.")
            return
        if follow_enabled and follow_day < occurred:
            st.error("The follow-up date must be on or after the action date.")
            return
        if action_state == "completed" and today is not None and occurred > today:
            st.error(
                "A completed action cannot be in the future. Choose Planned for a future action."
            )
            return
        payload = {
            "status": next_status,
            "expected_version": case.get("version", 0),
            "note": note.strip(),
            "action": action,
            "action_state": action_state,
            "occurred_day": int(occurred),
            "follow_up_day": int(follow_day) if follow_enabled else None,
            "resource_ids": selected_resources,
            "checkpoint_week": week,
            "expected_state_id": (detail.get("snapshot") or {}).get("state_id"),
            "resolves_event_id": plan_id or None,
        }
        try:
            client.save_case(
                course_id,
                learner_id,
                payload,
                idempotency_key=mutation_key(f"case_{course_id}_{learner_id}", payload),
            )
        except DashboardApiError as error:
            _show_error(error)
        else:
            st.session_state["workspace_flash"] = (
                "Support record saved. No student message was sent."
            )
            st.rerun()


def parse_break_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.strip().split("-")
        if len(parts) != 2:
            raise ValueError(
                "Enter one break per line as start-end course days, for example 28-34."
            )
        start, end = (int(value.strip()) for value in parts)
        if not 0 <= start <= end <= 420:
            raise ValueError(
                "Break ranges must stay between course days 0 and 420, with start before end."
            )
        ranges.append((start, end))
    return ranges


def course_expectations(policy: dict[str, Any]) -> str:
    """Describe saved settings without claiming that an older result used them."""
    mode = LEARNING_MODE_LABELS.get(policy.get("learning_mode", "custom"), "Custom expectations")
    prefix = f"Active course expectations · {mode} · policy {policy.get('version', 1)}. "
    if policy.get("inactivity_monitoring_enabled", True) is False:
        return (
            prefix
            + "Login inactivity is excluded from risk assessment; academic evidence still applies."
        )
    basis = "teaching days" if policy.get("day_basis") == "teaching" else "calendar days"
    return (
        prefix + f"Inactivity warning: {policy.get('inactivity_warning_days', 7)} {basis}; "
        f"escalation: {policy.get('inactivity_high_days', 14)} {basis}."
    )


def render_settings(client: WorkspaceClient, course_id: str, policy: dict[str, Any]) -> None:
    st.subheader("Course settings")
    st.write(
        "Choose expectations that match how you teach. Start with a preset, adjust it, "
        "then save. A course taught mainly offline need not treat quiet LMS days as risk."
    )
    st.info(course_expectations(policy))
    st.caption(
        f"Current policy revision: {policy.get('version', 1)}. Historical predictions "
        "retain their original policy. Changed settings require a new analysis."
    )
    current = CoursePolicy.model_validate(policy)
    prefix = f"workspace_policy_{course_id}_{current.version}"
    field_defaults = {
        "inactivity_warning_days": current.inactivity_warning_days,
        "inactivity_high_days": current.inactivity_high_days,
        "inactivity_monitoring_enabled": current.inactivity_monitoring_enabled,
        "learning_mode": current.learning_mode,
    }
    for field, value in field_defaults.items():
        st.session_state.setdefault(f"{prefix}_{field}", value)
    chosen_preset = st.selectbox(
        "Teaching-style starting point",
        list(LEARNING_MODE_LABELS),
        index=list(LEARNING_MODE_LABELS).index(current.learning_mode),
        format_func=LEARNING_MODE_LABELS.get,
        key=f"{prefix}_preset",
    )
    if st.button("Use preset as starting point", key=f"{prefix}_apply"):
        # Update widgets before rendering them; this is a draft, never an API write.
        try:
            draft = preset_policy(
                chosen_preset,
                current.model_copy(
                    update={
                        field: st.session_state[f"{prefix}_{field}"] for field in field_defaults
                    }
                ),
            )
        except ValueError:
            st.error("Correct the inactivity thresholds before using this starting point.")
        else:
            for field in field_defaults:
                st.session_state[f"{prefix}_{field}"] = getattr(draft, field)
            st.info("Preset copied into the form. Review the values and save to apply them.")
    st.caption(
        "Starting points: regular online 3/7 days; weekly 7/14; fortnightly 14/28. "
        "Milestone-based and mainly offline turn inactivity monitoring off. "
        "These are editable examples, not validated cutoffs for your course."
    )
    with st.form(prefix):
        monitor = st.checkbox(
            "Use login inactivity in risk assessment",
            key=f"{prefix}_inactivity_monitoring_enabled",
            help="Turn off when logins are not expected. Other academic evidence "
            "and data-quality checks remain active.",
        )
        st.caption(
            "When unchecked, the inactivity thresholds below are retained but not used. "
            "Few logins are not treated as concern; frequent logins are not treated as protection."
        )
        left, right = st.columns(2)
        with left:
            warning = st.number_input(
                "Inactivity warning after",
                min_value=1,
                max_value=120,
                key=f"{prefix}_inactivity_warning_days",
                step=1,
                help="Number of eligible days since last observed activity.",
            )
        with right:
            high = st.number_input(
                "Escalated inactivity after",
                min_value=2,
                max_value=180,
                key=f"{prefix}_inactivity_high_days",
                step=1,
            )
        basis = st.radio(
            "How days are counted",
            ["calendar", "teaching"],
            index=1 if policy.get("day_basis") == "teaching" else 0,
            format_func=lambda value: (
                "Calendar days" if value == "calendar" else "Teaching days only"
            ),
            horizontal=True,
        )
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        selected_days = st.multiselect(
            "Teaching weekdays",
            list(range(7)),
            default=policy.get("teaching_weekdays", [0, 1, 2, 3, 4]),
            format_func=lambda value: weekdays[value],
        )
        breaks_text = st.text_area(
            "Scheduled breaks · inclusive course-day ranges",
            value="\n".join(f"{start}-{end}" for start, end in policy.get("break_ranges", [])),
            placeholder="28-34\n56-62",
            help="Use one start-end range per line. Course day 0 is the course start.",
        )
        corroborate = st.checkbox(
            "Require academic evidence to corroborate inactivity",
            value=policy.get("require_academic_corroboration", True),
        )
        grade = st.number_input(
            "Low-grade reference · percent",
            min_value=0.0,
            max_value=100.0,
            value=float(policy.get("low_grade_percent", 50)),
            step=1.0,
        )
        st.caption(
            "Missing activity logs are not proof of inactivity. The predictor must "
            "consider evidence coverage, course timing and academic context."
        )
        submitted = st.form_submit_button("Save course settings", type="primary")
    if submitted:
        try:
            if high <= warning:
                raise ValueError(
                    "The escalated threshold must be greater than the warning threshold."
                )
            if not selected_days:
                raise ValueError("Select at least one teaching weekday.")
            payload = {
                "version": policy.get("version", 1),
                "learning_mode": st.session_state[f"{prefix}_learning_mode"],
                "inactivity_monitoring_enabled": monitor,
                "inactivity_warning_days": int(warning),
                "inactivity_high_days": int(high),
                "day_basis": basis,
                "teaching_weekdays": selected_days,
                "break_ranges": parse_break_ranges(breaks_text),
                "require_academic_corroboration": corroborate,
                "low_grade_percent": float(grade),
            }
            # A preset is only a starting point; the saved numbers are authoritative.
            selected_mode = payload["learning_mode"]
            expected = preset_policy(selected_mode, current)
            if selected_mode != "custom" and any(
                payload[field] != getattr(expected, field)
                for field in (
                    "inactivity_monitoring_enabled",
                    "inactivity_warning_days",
                    "inactivity_high_days",
                )
            ):
                payload["learning_mode"] = "custom"
            payload = CoursePolicy.model_validate(payload).model_dump(mode="json")
            client.save_policy(course_id, payload)
        except (DashboardApiError, ValueError) as error:
            _show_error(error)
        else:
            st.session_state["workspace_flash"] = (
                "Course settings saved. Queue a new analysis to apply this policy; "
                "earlier results stay in the history."
            )
            st.rerun()


def render_health(client: WorkspaceClient, workspace: dict[str, Any]) -> None:
    st.subheader("Data and model health")
    course = workspace.get("course", {})
    st.write(
        "**Course:** "
        f"{_course_name(course) if course.get('presentation_id') else 'Selected course'}"
    )
    st.write(f"**Source:** {label(course.get('data_origin'))}")
    st.write(f"**Selected checkpoint:** week {workspace.get('week')}")
    st.caption(
        "Availability, freshness and model analysis are separate: a prepared snapshot "
        "can exist before the LLM has analyzed it."
    )
    summary = workspace.get("summary", {})
    _frame([
        {"Status": label(key), "Students": value}
        for key, value in summary.items() if key != "priority_counts"
    ])
    if summary.get("priority_counts"):
        st.caption("Instructor-set priority counts · separate from model support levels")
        _frame([
            {"Instructor priority": label(key), "Students": value}
            for key, value in summary["priority_counts"].items()
        ])
    try:
        runtime = client.model_status()
    except DashboardApiError as error:
        _show_error(error)
    else:
        st.markdown("#### Model service")
        st.write(f"**Status:** {label(runtime.get('status', 'See details'))}")
        st.write(
            "**Configured model:** "
            f"{runtime.get('model', runtime.get('model_name', 'See runtime details'))}"
        )
        st.caption(
            "Configured does not imply a model is downloaded, running or producing "
            "validated predictions. Check the runtime status and then queue a test."
        )
        with st.expander("Model runtime details"):
            st.json(runtime)
    with st.expander("Terms used in this workspace"):
        st.markdown(
            "- **Risk score:** an uncalibrated 0–100 model output used to prioritize "
            "instructor review.\n"
            "- **Support level:** On track, Watch or High attention for one selected checkpoint.\n"
            "- **Risk-score change:** the difference between comparable checkpoint "
            "results, measured in points.\n"
            "- **Validated output:** structure and evidence checks passed; predictive "
            "accuracy still needs evaluation.\n"
            "- **Insufficient evidence:** the system abstained or could not support "
            "a current assessment.\n"
            "- **Ongoing:** support or follow-up remains open.\n"
            "- **Completed action:** the instructor records that the action occurred; "
            "it is not an automatic message."
        )
    if course.get("presentation_id"):
        render_course_analysis(client, course["presentation_id"])
