"""Responsive instructor workspace for the version-two course API.

The UI displays checkpoint snapshots and audited support cases. It does not
calculate risk, infer missing evidence, or generate student communications.
"""

from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st

from .client import DashboardApiError
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

WORKSPACE_CSS = """
<style>
 .block-container {max-width:1440px;padding-top:1.8rem;padding-bottom:3rem;}
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
 :focus-visible {outline:3px solid #a85a2d!important;outline-offset:3px;}
 @media(max-width:850px) {
   .block-container {padding:1.2rem .9rem 2rem;}
   [data-testid="stHorizontalBlock"] {flex-wrap:wrap!important;gap:1rem!important;}
   [data-testid="stHorizontalBlock"]>[data-testid="stColumn"] {
     width:100%!important;flex:1 1 100%!important;min-width:0!important;}
   h1 {font-size:1.8rem!important;} h2 {font-size:1.5rem!important;}
 }
 @media(max-width:430px) {
   .dt-cards {grid-template-columns:1fr 1fr;gap:.5rem;}
   .dt-card {padding:.75rem;}.dt-card-value {font-size:1.55rem;}}
</style>
"""


def label(value: Any) -> str:
    if value is None:
        return "Not available"
    return STATUS_LABELS.get(str(value), str(value).replace("_", " ").strip().capitalize())


def model_label(version: str | None) -> str:
    if not version:
        return "No model result"
    if version in {"rules-baseline-v2", "simple-rules-v1"}:
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


def timestamp(value: Any) -> str:
    if not value:
        return "Not recorded"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.strftime("%d %b %Y, %H:%M %Z").strip()
    except ValueError:
        return str(value)


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
    return course.get("title") or course["presentation_id"]


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
        if st.button("Refresh workspace", use_container_width=True):
            st.rerun()
        if st.button("Sign out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
        st.caption("Actions record instructor decisions. No automatic student messages are sent.")

    context = (account.reviewer_id, course_id, week)
    if st.session_state.get("workspace_context") != context:
        st.session_state["workspace_context"] = context
        st.session_state["workspace_profile"] = None
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
        workspace = client.workspace(course_id, week=week)
    except DashboardApiError as error:
        _show_error(error)
        return
    pages = ["Overview", "Students", "Support cases", "Course settings", "Data health"]
    page = st.radio(
        "Workspace section", pages, horizontal=True, key="workspace_page", on_change=_clear_profile
    )
    learner_id = st.session_state.get("workspace_profile")
    if learner_id:
        st.button("← Back to student list", on_click=_navigate, args=("Students", None))
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
    if versions and versions.issubset({"rules-baseline-v2", "simple-rules-v1"}):
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
    render_cards(
        [
            ("Enrolled students", str(total), "Entire course roster at this checkpoint."),
            (
                "Needs review",
                str(summary.get("needs_review", 0)),
                "New concerns, unreviewed high attention, or follow-ups now due.",
            ),
            (
                "High attention",
                str(summary.get("high_attention", 0)),
                "Current risk score falls in the high-attention band.",
            ),
            (
                "Insufficient evidence",
                str(summary.get("insufficient_data", 0)),
                "An assessment cannot be supported by the available information.",
            ),
            (
                "Ongoing support",
                str(summary.get("ongoing", 0)),
                "Open cases where support or follow-up is still needed.",
            ),
        ]
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
    if items:
        options = {item["learner_id"]: item for item in items}
        selected = st.selectbox(
            "Choose a student",
            list(options),
            format_func=lambda key: (
                f"{options[key].get('display_name') or key} · "
                f"{SUPPORT_LABELS.get(options[key].get('risk_band'), 'Not assessed')}"
            ),
            key=f"workspace_overview_pick_{course_id}_{week}",
        )
        st.button(
            "Open this student", type="primary", on_click=_navigate, args=("Students", selected)
        )
    else:
        st.info("There are no student records at this checkpoint.")
    render_analysis_controls(client, course_id, week)


def render_roster(
    client: WorkspaceClient, course_id: str, week: int, *, cases_only: bool = False
) -> None:
    st.subheader("Support cases" if cases_only else "Students")
    scope = f"{course_id}_{week}_{cases_only}"
    saved_filters = st.session_state.get(
        f"workspace_filter_{scope}", ("", "", "ongoing" if cases_only else "")
    )
    # Widget keys are discarded by Streamlit when their page is not rendered.
    # The separate filter snapshot lets Back restore the instructor's list.
    for name, value in zip(("search", "risk", "status"), saved_filters, strict=True):
        widget_key = f"workspace_{name}_{scope}"
        if widget_key not in st.session_state:
            st.session_state[widget_key] = value
    search, level, status = st.columns([1.5, 1, 1])
    with search:
        query = st.text_input(
            "Find student", placeholder="Name or learner ID", key=f"workspace_search_{scope}"
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
    fingerprint = (query, risk, case_status)
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
            offset=offset,
            limit=25,
        )
    except DashboardApiError as error:
        _show_error(error)
        return
    items = page.get("items", [])
    total = int(page.get("total", len(items)))
    st.caption(
        f"{total} matching student(s). Showing {offset + 1 if items else 0}–{offset + len(items)}."
    )
    if not items:
        st.info(
            "No students match these filters. Choose All levels / All statuses or clear the search."
        )
    else:
        _frame(
            [
                {
                    "Student": item.get("display_name") or item["learner_id"],
                    "Learner ID": item["learner_id"],
                    "Support level": SUPPORT_LABELS.get(item.get("risk_band"), "Not assessed"),
                    "Risk score": points(item.get("risk_score")),
                    "Previous → current": comparison(
                        item.get("risk_score"),
                        item.get("previous_score"),
                        comparable=item.get("comparable", False),
                    ),
                    "Analysis": label(item.get("analysis_status", "not_run")),
                    "Model": model_label(item.get("model_version")),
                    "Case": label(item.get("case_status"))
                    if item.get("case_status")
                    else "No case",
                    "Follow-up due": f"Course day {item['follow_up_day']}"
                    if item.get("follow_up_day") is not None
                    else "Not scheduled",
                }
                for item in items
            ]
        )
        choices = {
            item["learner_id"]: item.get("display_name") or item["learner_id"] for item in items
        }
        selected = st.selectbox(
            "Student to open",
            list(choices),
            format_func=choices.get,
            key=f"workspace_roster_pick_{scope}_{offset}",
        )
        st.button(
            "Open student profile", type="primary", on_click=_navigate, args=("Students", selected)
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
        detail = client.learner(course_id, learner_id, week=week)
    except DashboardApiError as error:
        _show_error(error)
        return
    st.subheader(detail.get("display_name") or learner_id)
    st.caption(f"Learner ID: {learner_id} · selected checkpoint: week {week}")
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
    case = detail.get("case") or {}
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
                "Case status",
                label(case.get("status")) if case else "No case",
                "Support history continues across checkpoints.",
            ),
        ]
    )
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
    if analysis:
        st.write(f"**Result source:** {model_label(analysis.get('model_version'))}")
        if analysis.get("model_kind") == "llm" and analysis.get("inference_performed") is False:
            st.info(
                "The data-quality gate abstained before calling Qwen. "
                "This is a system safety decision, not an LLM prediction."
            )
        for limitation in analysis.get("data_limitations", []):
            st.caption(f"Evidence limitation: {limitation}")
        st.caption(
            f"Result model: {analysis.get('model_version', 'Not recorded')} "
            f"· policy revision {analysis.get('policy_version', 'Not recorded')} "
            f"· generated {timestamp(analysis.get('generated_at'))}"
        )
    if snapshot and snapshot.get("is_fresh") is False:
        st.warning("The selected snapshot is marked stale. Confirm its evidence before acting.")
    tabs = st.tabs(
        ["Evidence and recommendations", "Academic progress", "Risk history", "Support history"]
    )
    with tabs[0]:
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


def render_academic_progress(detail: dict[str, Any]) -> None:
    features = (detail.get("snapshot") or {}).get("features", {})
    academic = [
        {
            "Academic evidence": label(name),
            "Value": fact_value(fact),
            "Availability": label(fact.get("status")),
            "Window": fact.get("window", ""),
        }
        for name, fact in features.items()
        if any(
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
    grade_rows = []
    for event in events:
        if event.get("event_type") != "assessment_grade":
            continue
        payload = event.get("payload", {})
        score, maximum = payload.get("score"), payload.get("max_score")
        if score is not None and maximum and float(maximum) > 0:
            grade_rows.append(
                {
                    "Published course day": event.get("available_day", event.get("course_day")),
                    "Grade (%)": 100 * float(score) / float(maximum),
                    "Assessment": payload.get("assessment_id", "Assessment"),
                }
            )
    st.markdown("#### Grades and assessment progress")
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
                    title="Assessment grade (%)",
                ),
                tooltip=[
                    "Assessment:N",
                    "Published course day:Q",
                    alt.Tooltip("Grade (%):Q", format=".1f"),
                ],
            )
            .properties(height=230)
        )
        st.altair_chart(grade_chart, use_container_width=True)
        st.caption(
            "Each dot is a published assessment grade. The grade scale is a percentage "
            "of available marks; it is separate from the risk-score scale."
        )
    if academic:
        _frame(academic)
    else:
        st.info("This source has not supplied academic features at this checkpoint.")
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
    case = detail.get("case") or {}
    cutoff = week * 7 - 1
    st.markdown("#### Instructor support record")
    st.caption(
        "This record belongs to the student and course, so it stays available across "
        "checkpoints. Planned actions are distinct from completed contact or support."
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
    if case.get("follow_up_day") is not None:
        due = case["follow_up_day"]
        st.write(
            f"**Next follow-up:** course day {due}"
            + (" · due at this checkpoint" if due <= cutoff else "")
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
    with st.form(f"workspace_case_{scope}"):
        st.markdown("#### Add an action, follow-up or manual concern")
        action_col, state_col = st.columns(2)
        with action_col:
            action = st.selectbox("Action type", list(ACTION_LABELS), format_func=ACTION_LABELS.get)
        with state_col:
            action_state = st.selectbox(
                "Action state", ["completed", "planned", "cancelled"], format_func=label
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
                "Action date · course day", min_value=0, max_value=420, value=cutoff, step=1
            )
        with follow_col:
            follow_enabled = st.checkbox(
                "Schedule a follow-up", value=case.get("follow_up_day") is not None
            )
            follow_day = st.number_input(
                "Follow-up due · course day",
                min_value=0,
                max_value=420,
                value=min(420, max(cutoff + 7, int(case.get("follow_up_day") or 0))),
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
        submitted = st.form_submit_button("Save support record", type="primary")
    if submitted:
        if not case and not note.strip():
            st.error("Describe the concern before opening a case.")
            return
        if follow_enabled and follow_day < occurred:
            st.error("The follow-up date must be on or after the action date.")
            return
        if occurred > cutoff:
            st.error(
                "The action date cannot be after the selected checkpoint. "
                "Use the follow-up date to plan future work."
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


def render_settings(client: WorkspaceClient, course_id: str, policy: dict[str, Any]) -> None:
    st.subheader("Course settings")
    st.write(
        "Set the amount of inactivity that is concerning in this course. A fortnightly "
        "course can use longer thresholds than a course expecting daily participation."
    )
    st.caption(
        f"Current policy revision: {policy.get('version', 1)}. Historical predictions "
        "retain their original policy. Changed settings require a new analysis."
    )
    with st.form(f"workspace_policy_{course_id}_{policy.get('version', 1)}"):
        left, right = st.columns(2)
        with left:
            warning = st.number_input(
                "Inactivity warning after",
                min_value=1,
                max_value=120,
                value=int(policy.get("inactivity_warning_days", 7)),
                step=1,
                help="Number of eligible days since last observed activity.",
            )
        with right:
            high = st.number_input(
                "Escalated inactivity after",
                min_value=2,
                max_value=180,
                value=int(policy.get("inactivity_high_days", 14)),
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
                "inactivity_warning_days": int(warning),
                "inactivity_high_days": int(high),
                "day_basis": basis,
                "teaching_weekdays": selected_days,
                "break_ranges": parse_break_ranges(breaks_text),
                "require_academic_corroboration": corroborate,
                "low_grade_percent": float(grade),
            }
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
    _frame([{"Status": label(key), "Students": value} for key, value in summary.items()])
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
