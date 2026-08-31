"""Instructor-facing student-support workspace backed exclusively by the API."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from digital_twin.dashboard.auth import (  # noqa: E402
    AccountConfigurationError,
    InstructorAccount,
    authenticate,
    load_accounts,
)
from digital_twin.dashboard.client import DashboardApiClient, DashboardApiError  # noqa: E402
from digital_twin.dashboard.view_model import (  # noqa: E402
    RISK_LABELS,
    STATUS_LABELS,
    action_label,
    claim_label,
    course_summary,
    current_support_items,
    display_feature_value,
    feature_label,
    filter_roster,
    missing_label,
    risk_distribution,
    support_reason,
    trend_distribution,
    trend_label,
)

PAGE_OPTIONS = ["Overview", "Students", "Support queue", "Data health"]
RISK_SYMBOLS = {"high": "▲", "medium": "◆", "low": "●", None: "○"}


def client_for(api_url: str, identity: str, role: str) -> DashboardApiClient:
    return DashboardApiClient(base_url=api_url, instructor_id=identity, instructor_role=role)


@st.cache_data(ttl=15, show_spinner=False)
def load_workspace(api_url: str, identity: str, role: str, presentation_id: str):
    client = client_for(api_url, identity, role)
    return client.readiness(), client.presentation_overview(presentation_id)


@st.cache_data(ttl=15, show_spinner=False)
def load_roster(api_url: str, identity: str, role: str, presentation_id: str):
    """Load the complete pilot roster through the paginated API."""

    client = client_for(api_url, identity, role)
    items: list[dict[str, Any]] = []
    offset = 0
    total = 0
    while offset < 5_000:
        page = client.learners(presentation_id=presentation_id, limit=200, offset=offset)
        page_items = page.get("items", [])
        total = int(page.get("total", len(items) + len(page_items)))
        items.extend(page_items)
        offset += len(page_items)
        if not page_items or offset >= total:
            break
    return {"items": items, "total": total, "truncated": len(items) < total}


@st.cache_data(ttl=15, show_spinner=False)
def load_alert(api_url: str, identity: str, role: str, alert_id: str):
    return client_for(api_url, identity, role).alert_detail(alert_id)


@st.cache_data(ttl=15, show_spinner=False)
def load_learner(api_url: str, identity: str, role: str, presentation_id: str, learner_id: str):
    return client_for(api_url, identity, role).learner_detail(
        presentation_id=presentation_id, learner_id=learner_id
    )


def require_pilot_login(auth_file: str) -> InstructorAccount | None:
    """Render the pilot login and return a course-scoped account when authenticated."""

    try:
        accounts = load_accounts(auth_file)
    except AccountConfigurationError as error:
        st.error(str(error))
        st.info("Ask the server operator to repair the instructor account file.")
        return None
    authenticated_username = st.session_state.get("authenticated_username")
    if authenticated_username in accounts:
        return accounts[authenticated_username]
    st.markdown('<div class="eyebrow">Protected instructor pilot</div>', unsafe_allow_html=True)
    st.title("Sign in to the student-support workspace")
    st.caption("Use the pilot account issued by the project operator.")
    with st.form("pilot-login"):
        username = st.text_input("Username", autocomplete="username")
        password = st.text_input("Password", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("Sign in", type="primary")
    if submitted:
        account = authenticate(accounts, username, password)
        if account is None:
            st.error("The username or password is incorrect.")
        else:
            st.session_state["authenticated_username"] = account.username
            st.rerun()
    return None


def format_presentation(presentation_id: str) -> str:
    parts = presentation_id.split(":")
    if len(parts) >= 3:
        return f"{parts[-2]} · {parts[-1]} ({parts[0].upper()})"
    return presentation_id


def format_timestamp(value: str | datetime | None) -> str:
    if not value:
        return "Not configured"
    try:
        parsed = (
            value
            if isinstance(value, datetime)
            else datetime.fromisoformat(value.replace("Z", "+00:00"))
        )
    except (TypeError, ValueError):
        return str(value)
    zone = parsed.tzname()
    suffix = f" {zone}" if zone else ""
    return f"{parsed:%d %b %Y, %H:%M}{suffix}"


def risk_text(item: dict[str, Any]) -> str:
    band = item.get("risk_band")
    return f"{RISK_SYMBOLS.get(band, '○')} {RISK_LABELS.get(band, 'No current score')}"


def score_text(value: float | None) -> str:
    return "Not available" if value is None else f"{float(value):.0%}"


def assessment_text(item: dict[str, Any]) -> str:
    due = item.get("assessments_due")
    submitted = item.get("assessments_submitted")
    missed = item.get("assessments_missed")
    if due is None:
        return "Not available"
    progress = f"{int(submitted or 0)} of {int(due)} submitted"
    if missed:
        return f"{progress} · {int(missed)} overdue"
    return progress


def count_chart(
    rows: dict[str, int],
    *,
    category_title: str,
    order: list[str],
    colors: list[str],
) -> alt.LayerChart:
    """Build a compact horizontal count chart with visible labels and tooltips."""

    frame = pd.DataFrame({category_title: list(rows), "Students": list(rows.values())})
    bars = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Students:Q", title="Students"),
            y=alt.Y(f"{category_title}:N", title=None, sort=order),
            color=alt.Color(
                f"{category_title}:N",
                scale=alt.Scale(domain=order, range=colors),
                legend=None,
            ),
            tooltip=[alt.Tooltip(f"{category_title}:N"), alt.Tooltip("Students:Q")],
        )
    )
    labels = (
        alt.Chart(frame)
        .mark_text(align="left", baseline="middle", dx=5, color="#142235")
        .encode(
            x=alt.X("Students:Q"),
            y=alt.Y(f"{category_title}:N", sort=order),
            text=alt.Text("Students:Q"),
        )
    )
    return (bars + labels).properties(height=190, width="container")


def navigate(page: str, learner_id: str | None = None) -> None:
    st.session_state["dashboard_page"] = page
    if learner_id:
        st.session_state["selected_learner_id"] = learner_id


def render_data_warning(overview: dict[str, Any], summary: dict[str, int]) -> None:
    if overview.get("ingestion_status") == "failed":
        st.error(
            "The latest data import failed. Treat displayed signals as historical until recovery."
        )
    elif overview.get("ingestion_status") == "stale" or summary["stale"]:
        st.warning("Some learner information is stale. Confirm the update time before acting.")
    if overview.get("active_quarantine_count", 0):
        quarantine_count = overview["active_quarantine_count"]
        st.error(f"{quarantine_count} source record(s) were quarantined and require review.")


def render_model_notice(roster_items: list[dict[str, Any]]) -> None:
    model_versions = sorted(
        {str(item["model_version"]) for item in roster_items if item.get("model_version")}
    )
    temporary = not model_versions or all(
        version == "simple-rules-v1" for version in model_versions
    )
    if temporary:
        st.warning(
            "Temporary rules-based signal: current risk scores and suggested actions validate the "
            "workflow only. They are not trained, calibrated, or research findings."
        )
    else:
        st.info(
            "Model-assisted support signal: use the evidence, uncertainty, and data status before "
            "recording an instructor decision."
        )


def render_overview(roster_items: list[dict[str, Any]], overview: dict[str, Any]) -> None:
    summary = course_summary(roster_items)
    render_data_warning(overview, summary)

    st.subheader("Course at a glance")
    st.caption(
        "Current learner states only. Previous checkpoints remain in each learner's history."
    )
    columns = st.columns(5)
    columns[0].metric(
        "Needs review",
        f"{summary['needs_review']:,}",
        help="Learners with a current alert that has not yet been reviewed.",
    )
    columns[1].metric(
        "High attention",
        f"{summary['high_attention']:,}",
        help="Learners whose current signal is in the high-attention band.",
    )
    columns[2].metric(
        "Score increased",
        f"{summary['worsening']:,}",
        help="Learners whose current score increased by more than 0.5 percentage points.",
    )
    columns[3].metric(
        "Current learner data",
        f"{summary['current_data']:,} / {summary['learners']:,}",
        help="Learners with at least one available weekly state.",
    )
    updated = overview.get("last_ingestion_success_at") or overview.get("latest_state_built_at")
    columns[4].metric(
        "Data status",
        "Current" if overview.get("all_current_alerts_fresh") else "Check update",
        help=f"Latest available update: {format_timestamp(updated)}",
    )

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Current support level")
        risk_counts = risk_distribution(roster_items)
        risk_order = ["High attention", "Watch", "On track", "No current score"]
        st.altair_chart(
            count_chart(
                risk_counts,
                category_title="Support level",
                order=risk_order,
                colors=["#c43d4f", "#b96a00", "#167568", "#718096"],
            )
        )
        with st.expander("View counts as a table"):
            st.dataframe(
                pd.DataFrame(
                    {"Support level": list(risk_counts), "Students": list(risk_counts.values())}
                ),
                hide_index=True,
            )
    with right:
        st.markdown("#### Change since the previous checkpoint")
        trend_counts = trend_distribution(roster_items)
        trend_order = ["Increased", "Stable", "Decreased", "First score"]
        st.altair_chart(
            count_chart(
                trend_counts,
                category_title="Change",
                order=trend_order,
                colors=["#c43d4f", "#5b6b82", "#167568", "#718096"],
            )
        )
        with st.expander("View counts as a table"):
            st.dataframe(
                pd.DataFrame(
                    {"Change": list(trend_counts), "Students": list(trend_counts.values())}
                ),
                hide_index=True,
            )

    st.markdown("#### Needs attention now")
    support_items = [
        item for item in current_support_items(roster_items) if item.get("alert_status") == "new"
    ]
    if not support_items:
        st.success("There are no new current alerts waiting for review.")
    else:
        top_items = support_items[:5]
        attention_frame = pd.DataFrame(
            [
                {
                    "Learner": item["learner_id"],
                    "Support level": risk_text(item),
                    "Score": item.get("display_probability"),
                    "Change": trend_label(item.get("probability_change")),
                    "Why review": support_reason(item),
                    "Data": "Current" if item.get("is_fresh") else "Check update",
                }
                for item in top_items
            ]
        )
        st.dataframe(
            attention_frame,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Signal score", min_value=0.0, max_value=1.0, format="percent"
                )
            },
        )
        selected = st.selectbox(
            "Choose a learner to inspect",
            options=[item["learner_id"] for item in top_items],
            key="overview_selected_learner",
        )
        st.button(
            "Open learner profile",
            type="primary",
            on_click=navigate,
            args=("Students", selected),
        )

    st.divider()
    health_left, health_right = st.columns([1.2, 1])
    with health_left:
        st.markdown("#### Course context")
        checkpoint_text = ", ".join(
            f"week {week}" for week in sorted(overview.get("states_by_checkpoint", {}))
        )
        st.write(f"**Checkpoint coverage:** {checkpoint_text or 'Not available'}")
        st.write(f"**Data source type:** {overview.get('data_origin', 'not available').title()}")
    with health_right:
        st.markdown("#### Latest update")
        st.write(format_timestamp(updated))
        st.button(
            "Open full data health",
            use_container_width=True,
            on_click=navigate,
            args=("Data health",),
        )


def roster_table(items: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Learner": item["learner_id"],
                "Support level": risk_text(item),
                "Score": item.get("display_probability"),
                "Movement": trend_label(item.get("probability_change")),
                "Engagement": (
                    f"{item['active_days_14d']} active days · 14d"
                    if item.get("active_days_14d") is not None
                    else "Not available"
                ),
                "Assessments": assessment_text(item),
                "Review status": STATUS_LABELS.get(item.get("alert_status"), "No alert"),
                "Data": (
                    "Current"
                    if item.get("is_fresh") is True
                    else "Check update"
                    if item.get("is_fresh") is False
                    else "No state"
                ),
            }
            for item in items
        ]
    )


def render_students(
    api_url: str,
    identity: str,
    role: str,
    presentation_id: str,
    roster_items: list[dict[str, Any]],
) -> None:
    st.subheader("Students")
    st.caption("Search the complete course roster and open one learner's current support picture.")

    search_column, risk_column, trend_column = st.columns([1.5, 1, 1])
    with search_column:
        query = st.text_input(
            "Find learner",
            placeholder="Search by the permitted learner identifier",
            key="student_search",
        )
    with risk_column:
        risks = st.multiselect(
            "Support level",
            options=["high", "medium", "low"],
            format_func=lambda value: RISK_LABELS[value],
            key="student_risks",
        )
    with trend_column:
        trends = st.multiselect(
            "Score movement",
            options=["increasing", "stable", "decreasing", "unavailable"],
            format_func=lambda value: {
                "increasing": "Increased",
                "stable": "Stable",
                "decreasing": "Decreased",
                "unavailable": "First score",
            }[value],
            key="student_trends",
        )
    status_column, freshness_column = st.columns(2)
    with status_column:
        statuses = st.multiselect(
            "Review status",
            options=["new", "reviewed", "resolved", "dismissed", "none"],
            format_func=lambda value: STATUS_LABELS[None if value == "none" else value],
            key="student_statuses",
        )
    with freshness_column:
        freshness = st.selectbox(
            "Data status",
            options=["all", "current", "stale"],
            format_func=lambda value: {
                "all": "All data states",
                "current": "Current only",
                "stale": "Needs an update",
            }[value],
            key="student_freshness",
        )

    filtered = filter_roster(
        roster_items,
        query=query,
        risks=risks,
        trends=trends,
        statuses=statuses,
        freshness=freshness,
    )
    st.caption(f"Showing {len(filtered):,} of {len(roster_items):,} enrolled learners.")
    if not filtered:
        st.info("No learners match the selected filters.")
        return
    st.dataframe(
        roster_table(filtered),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Signal score", min_value=0.0, max_value=1.0, format="percent"
            ),
        },
    )

    learner_options = [item["learner_id"] for item in filtered]
    selected = st.session_state.get("selected_learner_id")
    if selected not in learner_options:
        st.session_state["selected_learner_id"] = learner_options[0]
    learner_id = st.selectbox(
        "Open learner profile", options=learner_options, key="selected_learner_id"
    )
    selected_item = next(item for item in filtered if item["learner_id"] == learner_id)
    render_learner_profile(api_url, identity, role, presentation_id, selected_item)


def render_learner_profile(
    api_url: str,
    identity: str,
    role: str,
    presentation_id: str,
    learner_item: dict[str, Any],
) -> None:
    st.divider()
    st.markdown(f"### Learner profile · {learner_item['learner_id']}")
    st.caption(
        "A support signal is not a diagnosis. Confirm the evidence and available context "
        "before acting."
    )
    try:
        learner_detail = load_learner(
            api_url, identity, role, presentation_id, learner_item["learner_id"]
        )
    except DashboardApiError as error:
        st.error(str(error))
        return

    metrics = st.columns(6)
    metrics[0].metric("Support level", RISK_LABELS.get(learner_item.get("risk_band"), "No score"))
    metrics[1].metric("Signal score", score_text(learner_item.get("display_probability")))
    metrics[2].metric("Movement", trend_label(learner_item.get("probability_change")))
    metrics[3].metric(
        "Active days · 14d",
        learner_item.get("active_days_14d")
        if learner_item.get("active_days_14d") is not None
        else "N/A",
    )
    metrics[4].metric(
        "Days inactive",
        learner_item.get("days_since_last_activity")
        if learner_item.get("days_since_last_activity") is not None
        else "N/A",
    )
    metrics[5].metric(
        "Overdue assessments",
        learner_item.get("assessments_missed")
        if learner_item.get("assessments_missed") is not None
        else "N/A",
    )

    completeness = learner_item.get("completeness")
    if completeness is not None:
        st.progress(
            float(completeness),
            text=f"Available weekly-state information: {float(completeness):.0%}",
        )

    summary_tab, activity_tab, evidence_tab, history_tab = st.tabs(
        ["Current picture", "Activity and assessments", "Why flagged", "Risk history"]
    )
    with summary_tab:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Recent engagement")
            recent = learner_item.get("activity_count_14d")
            active = learner_item.get("active_days_14d")
            inactive = learner_item.get("days_since_last_activity")
            recent_text = recent if recent is not None else "Not available"
            active_text = active if active is not None else "Not available"
            inactive_text = inactive if inactive is not None else "Not available"
            st.write(f"**Recorded activity, last 14 days:** {recent_text}")
            st.write(f"**Active days, last 14 days:** {active_text}")
            st.write(f"**Days since last recorded activity:** {inactive_text}")
        with right:
            st.markdown("#### Assessment progress")
            due = learner_item.get("assessments_due")
            submitted = learner_item.get("assessments_submitted")
            missed = learner_item.get("assessments_missed")
            st.write(f"**Due by checkpoint:** {due if due is not None else 'Not available'}")
            st.write(f"**Submitted:** {submitted if submitted is not None else 'Not available'}")
            st.write(f"**Currently overdue:** {missed if missed is not None else 'Not available'}")
            st.write(f"**Submission rate:** {score_text(learner_item.get('submission_rate'))}")
        with st.expander("Registration and data-availability details"):
            registration = learner_detail.get("registration_day")
            registration_text = (
                registration
                if registration is not None
                else missing_label(learner_detail.get("registration_missing_reason"))
            )
            st.write(f"Registration course day: {registration_text}")
            features = learner_detail.get("features", [])
            missing = [row for row in features if row.get("value") is None]
            if missing:
                st.markdown("**Unavailable fields**")
                for row in missing:
                    st.write(
                        f"- {feature_label(row['feature_name'])}: "
                        f"{missing_label(row.get('missing_reason'))}"
                    )
            else:
                st.write("All fields in the current feature contract have values.")

    with activity_tab:
        activity = pd.DataFrame(learner_detail.get("activity_timeline", []))
        if activity.empty:
            st.info("No dated activity is available for this learner.")
        else:
            activity = activity.sort_values("course_week").set_index("course_week")
            left, right = st.columns(2, gap="large")
            with left:
                st.markdown("#### Recorded course activity")
                st.bar_chart(
                    activity[["activity_count"]],
                    y_label="Recorded events",
                    x_label="Course week",
                )
            with right:
                st.markdown("#### Assessment events")
                st.bar_chart(
                    activity[["assessment_event_count"]],
                    y_label="Assessment events",
                    x_label="Course week",
                )
            with st.expander("View activity chart data"):
                st.dataframe(activity.reset_index(), hide_index=True, use_container_width=True)

    with evidence_tab:
        if not learner_item.get("alert_id"):
            st.success("This learner has no current alert requiring evidence review.")
        else:
            try:
                alert_detail = load_alert(api_url, identity, role, learner_item["alert_id"])
            except DashboardApiError as error:
                st.error(str(error))
            else:
                render_evidence(alert_detail)

    with history_tab:
        render_prediction_history(learner_detail.get("prediction_timeline", []))


def render_evidence(detail: dict[str, Any]) -> None:
    alert = detail["alert"]
    if not alert.get("is_fresh"):
        st.error("This support signal is stale. Do not treat it as current.")
    if detail.get("fallback_used") or not detail.get("quality_gate_passed", False):
        st.warning(
            "A fallback or data-quality gate is active. Review the available information carefully."
        )

    st.markdown("#### Why this learner was flagged")
    claims = detail.get("claims", [])
    if claims:
        for claim in claims:
            st.write(f"- **{claim_label(claim['claim_code'])}**")
    else:
        st.info("No grounded claim was supplied for this signal.")
    uncertainty = detail.get("uncertainty_note")
    if uncertainty:
        st.info(f"Uncertainty: {uncertainty}")

    evidence_rows = detail.get("evidence", [])
    if evidence_rows:
        evidence_frame = pd.DataFrame(
            [
                {
                    "Evidence": feature_label(row["feature_name"]),
                    "Value": display_feature_value(
                        row["feature_name"], row.get("value"), row.get("missing_reason")
                    ),
                    "Availability": missing_label(row.get("missing_reason")),
                    "Source records": row.get("source_observation_count", 0),
                }
                for row in evidence_rows
            ]
        )
        st.dataframe(evidence_frame, hide_index=True, use_container_width=True)

    actions = detail.get("suggested_actions", [])
    if actions:
        st.markdown("#### Suggested instructor checks")
        for action in actions:
            st.write(f"- {action_label(action)}")
        st.caption(
            "Suggestions are not automatic actions. The instructor decides whether they are "
            "appropriate."
        )

    with st.expander("Technical audit details"):
        st.code(
            f"state_id={detail['state_id']}\n"
            f"feature_set={detail['feature_set_version']}\n"
            f"model={alert['model_version']}\n"
            f"input_hash={detail['input_hash']}"
        )
        for row in evidence_rows:
            samples = row.get("source_record_samples") or ["No direct source record"]
            st.write(f"`{row['evidence_id']}`: {', '.join(samples)}")


def render_prediction_history(timeline_rows: list[dict[str, Any]]) -> None:
    timeline = pd.DataFrame(timeline_rows)
    if timeline.empty:
        st.info("No previous checkpoint signals are available.")
        return
    timeline = timeline.sort_values("checkpoint_week")
    chart = timeline.set_index("checkpoint_week")[["display_probability"]]
    st.line_chart(chart, y_label="Signal score", x_label="Checkpoint week")
    table = timeline[
        [
            "checkpoint_week",
            "cutoff_course_day",
            "display_probability",
            "risk_band",
            "model_version",
        ]
    ].rename(
        columns={
            "checkpoint_week": "Checkpoint week",
            "cutoff_course_day": "Course day",
            "display_probability": "Signal score",
            "risk_band": "Support level",
            "model_version": "Model version",
        }
    )
    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        column_config={"Signal score": st.column_config.NumberColumn(format="percent")},
    )
    st.caption("Checkpoint scores are support signals, not diagnoses or causal explanations.")


def render_support_queue(
    api_url: str,
    identity: str,
    role: str,
    roster_items: list[dict[str, Any]],
) -> None:
    st.subheader("Support queue")
    st.caption(
        "One current item per learner. Earlier checkpoint alerts remain in the learner history."
    )
    support_items = current_support_items(roster_items)
    if not support_items:
        st.success("No current learner alerts are available.")
        return

    status_column, risk_column, trend_column = st.columns(3)
    with status_column:
        statuses = st.multiselect(
            "Review status",
            options=["new", "reviewed", "resolved", "dismissed"],
            default=["new"],
            format_func=lambda value: STATUS_LABELS[value],
            key="queue_statuses",
        )
    with risk_column:
        risks = st.multiselect(
            "Support level",
            options=["high", "medium", "low"],
            format_func=lambda value: RISK_LABELS[value],
            key="queue_risks",
        )
    with trend_column:
        trends = st.multiselect(
            "Score movement",
            options=["increasing", "stable", "decreasing", "unavailable"],
            format_func=lambda value: {
                "increasing": "Increased",
                "stable": "Stable",
                "decreasing": "Decreased",
                "unavailable": "First score",
            }[value],
            key="queue_trends",
        )
    visible = filter_roster(support_items, risks=risks, trends=trends, statuses=statuses)
    if not visible:
        st.info("No current support items match the selected filters.")
        return

    queue_column, detail_column = st.columns([1, 1.35], gap="large")
    with queue_column:
        st.caption(f"{len(visible):,} current learner support item(s)")
        queue_frame = pd.DataFrame(
            [
                {
                    "Learner": item["learner_id"],
                    "Support level": risk_text(item),
                    "Score": item.get("display_probability"),
                    "Change": trend_label(item.get("probability_change")),
                    "Why review": support_reason(item),
                    "Status": STATUS_LABELS.get(item.get("alert_status"), "No alert"),
                }
                for item in visible
            ]
        )
        st.dataframe(
            queue_frame,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Score": st.column_config.ProgressColumn(
                    "Signal score", min_value=0.0, max_value=1.0, format="percent"
                )
            },
        )
        selected_alert_id = st.selectbox(
            "Open support item",
            options=[item["alert_id"] for item in visible],
            format_func=lambda alert_id: next(
                f"{item['learner_id']} · {risk_text(item)} · "
                f"{trend_label(item.get('probability_change'))}"
                for item in visible
                if item["alert_id"] == alert_id
            ),
            key="selected_current_alert",
        )

    try:
        detail = load_alert(api_url, identity, role, selected_alert_id)
    except DashboardApiError as error:
        with detail_column:
            st.error(str(error))
        return
    with detail_column:
        alert = detail["alert"]
        st.markdown(f"### {alert['learner_id']}")
        st.caption(
            f"Checkpoint week {alert['checkpoint_week']} · course day "
            f"{alert['cutoff_course_day']} · generated "
            f"{format_timestamp(alert.get('generated_at'))}"
        )
        columns = st.columns(2)
        columns[0].metric("Support level", RISK_LABELS.get(alert.get("risk_band"), "No score"))
        columns[1].metric("Signal score", score_text(alert.get("display_probability")))
        columns = st.columns(2)
        columns[0].metric(
            "Review status", STATUS_LABELS.get(alert.get("status"), alert.get("status"))
        )
        columns[1].metric("Data", "Current" if alert.get("is_fresh") else "Check update")
        evidence_tab, history_tab, review_tab = st.tabs(
            ["Why flagged", "Risk history", "Record decision"]
        )
        with evidence_tab:
            render_evidence(detail)
        with history_tab:
            render_prediction_history(detail.get("prediction_timeline", []))
        with review_tab:
            render_review_form(api_url, identity, role, selected_alert_id, detail)


def render_review_form(
    api_url: str,
    identity: str,
    role: str,
    alert_id: str,
    detail: dict[str, Any],
) -> None:
    alert = detail["alert"]
    history = detail.get("review_history", [])
    if history:
        history_frame = pd.DataFrame(history).rename(
            columns={
                "new_status": "Decision",
                "note": "Note",
                "reviewed_at": "Recorded at",
                "reviewer_role": "Role",
            }
        )
        display_columns = [
            column
            for column in ["Decision", "Note", "Recorded at", "Role"]
            if column in history_frame
        ]
        st.dataframe(history_frame[display_columns], hide_index=True, use_container_width=True)
    else:
        st.caption("No prior instructor decision has been recorded.")

    terminal_alert = alert.get("status") in {"resolved", "dismissed"}
    if terminal_alert:
        st.info("This item is closed. Its audited history remains read-only.")
        return
    with st.form(f"review-alert-{alert_id}", clear_on_submit=False):
        status_options = [
            status
            for status in ["reviewed", "resolved", "dismissed"]
            if status != alert.get("status")
        ]
        new_status = st.selectbox(
            "Decision", status_options, format_func=lambda value: STATUS_LABELS[value]
        )
        note = st.text_area(
            "Review note (optional)",
            max_chars=1000,
            placeholder="Record only the minimum educationally relevant context.",
        )
        st.caption(
            "No message is sent to the learner. This form records the instructor's decision only."
        )
        submitted = st.form_submit_button("Save audited decision", type="primary")
        if submitted:
            try:
                response = client_for(api_url, identity, role).review_alert(
                    alert_id=alert_id,
                    new_status=new_status,
                    note=note,
                    idempotency_key=f"dashboard-{uuid4()}",
                )
            except DashboardApiError as error:
                st.error(str(error))
            else:
                status = response["status"]
                st.session_state["review_success"] = (
                    f"Decision saved as {STATUS_LABELS.get(status, status)}."
                )
                st.cache_data.clear()
                st.rerun()


def render_data_health(
    ready: dict[str, Any],
    overview: dict[str, Any],
    roster_items: list[dict[str, Any]],
) -> None:
    st.subheader("Data health and model status")
    st.caption(
        "Technical information is kept here so it does not distract from student-support work."
    )
    summary = course_summary(roster_items)
    render_data_warning(overview, summary)

    columns = st.columns(5)
    columns[0].metric("API and database", "Ready" if ready.get("status") == "ok" else "Not ready")
    ingestion_status = overview.get("ingestion_status", "not_configured")
    ingestion_label = (
        "Not set"
        if ingestion_status == "not_configured"
        else ingestion_status.replace("_", " ").title()
    )
    columns[1].metric("Data import", ingestion_label)
    columns[2].metric(
        "Learners with states", f"{summary['current_data']:,} / {summary['learners']:,}"
    )
    columns[3].metric("Stale learner states", f"{summary['stale']:,}")
    columns[4].metric("Quarantined records", f"{overview.get('active_quarantine_count', 0):,}")

    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("#### Update information")
        st.write(
            f"**Latest state build:** {format_timestamp(overview.get('latest_state_built_at'))}"
        )
        st.write(
            "**Last successful import:** "
            f"{format_timestamp(overview.get('last_ingestion_success_at'))}"
        )
        age = overview.get("ingestion_age_minutes")
        age_text = f"{age:,.0f} minutes" if age is not None else "Not configured"
        st.write(f"**Import age:** {age_text}")
        st.write(f"**Data origin:** {overview.get('data_origin', 'not available').title()}")
    with right:
        st.markdown("#### Model boundary")
        versions = sorted(
            {item.get("model_version") for item in roster_items if item.get("model_version")}
        )
        st.write(
            "**Current model version(s):** "
            f"{', '.join(versions) if versions else 'No model output'}"
        )
        st.write("**Prediction interface:** versioned weekly state → validated structured result")
        st.write("**Instructor control:** every alert requires human review")
        st.write("**Automatic learner contact:** disabled")

    st.markdown("#### Weekly-state coverage")
    checkpoint_rows = [
        {"Checkpoint week": int(week), "Learner states": int(count)}
        for week, count in sorted(
            overview.get("states_by_checkpoint", {}).items(), key=lambda item: int(item[0])
        )
    ]
    if checkpoint_rows:
        checkpoint_counts = {
            f"Week {row['Checkpoint week']}": row["Learner states"] for row in checkpoint_rows
        }
        checkpoint_order = list(checkpoint_counts)
        st.altair_chart(
            count_chart(
                checkpoint_counts,
                category_title="Checkpoint",
                order=checkpoint_order,
                colors=["#2f75b5"] * len(checkpoint_order),
            )
        )
    else:
        st.info("No weekly states are available for this course.")

    with st.expander("Technical record counts and deployment details"):
        technical = pd.DataFrame(
            [
                {"Record type": "Enrolled learners", "Count": overview.get("learner_count", 0)},
                {"Record type": "Weekly states", "Count": overview.get("state_count", 0)},
                {"Record type": "Predictions", "Count": overview.get("prediction_count", 0)},
                {
                    "Record type": "Historical alert records",
                    "Count": overview.get("alert_count", 0),
                },
            ]
        )
        st.dataframe(technical, hide_index=True, use_container_width=True)
        st.write(f"Database backend: {ready.get('database_backend', 'not available')}")
        st.write(f"Migration revision: {ready.get('migration_revision', 'not available')}")

    with st.expander("Glossary"):
        st.markdown(
            "- **Signal score:** a model output used to prioritize human review; it is not "
            "a diagnosis.\n"
            "- **Current data:** the state and source import are within the configured "
            "freshness policy.\n"
            "- **Available information:** the share of expected state fields that can be "
            "used at this checkpoint.\n"
            "- **Quarantined record:** a source record rejected because it failed "
            "validation.\n"
            "- **Data origin:** empirical, replayed, or synthetic data; these results "
            "remain separate."
        )


def render_dashboard() -> None:
    st.set_page_config(
        page_title="Student-support workspace",
        page_icon="◎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
          .block-container {padding-top: 2.5rem; padding-bottom: 3rem; max-width: 1380px;}
          [data-testid="stToolbar"] {visibility: hidden;}
          [data-testid="stHeader"] {background: transparent;}
          [data-testid="stMetric"] {background: #f7f9fc; border: 1px solid #d9e1ea;
            border-radius: 12px; padding: 14px 16px; min-height: 112px;}
          [data-testid="stMetric"] * {color: #142235 !important;}
          [data-testid="stMetricLabel"] {font-weight: 650;}
          .eyebrow {font-size: .78rem; letter-spacing: .09em; text-transform: uppercase;
            color: #607089; font-weight: 750; margin-bottom: .35rem;}
          div[role="radiogroup"] {gap: .25rem; border-bottom: 1px solid #d9e1ea;
            padding-bottom: .5rem; margin-bottom: 1rem;}
          div[role="radiogroup"] label {padding: .35rem .55rem; border-radius: .45rem;}
          div[data-testid="stDataFrame"] {border: 1px solid #d9e1ea; border-radius: 10px;}
          .stAlert {border-radius: 10px;}
          :focus-visible {outline: 3px solid #2f75b5 !important; outline-offset: 2px;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    if review_message := st.session_state.pop("review_success", None):
        st.success(review_message)

    default_api_url = os.environ.get("DIGITAL_TWIN_API_URL", "http://127.0.0.1:8000")
    default_presentation = os.environ.get("DIGITAL_TWIN_PRESENTATION_ID", "oulad:AAA:2013J")
    default_identity = os.environ.get("DIGITAL_TWIN_DASHBOARD_ID", "instructor:dashboard-demo")
    default_role = os.environ.get("DIGITAL_TWIN_DASHBOARD_ROLE", "instructor")

    auth_file = os.environ.get("DIGITAL_TWIN_AUTH_FILE")
    account = require_pilot_login(auth_file) if auth_file else None
    if auth_file and account is None:
        return

    with st.sidebar:
        if account:
            st.markdown(f"### {account.display_name}")
            st.caption(f"Role: {account.role.title()}")
            api_url = default_api_url
            presentation_id = st.selectbox(
                "Course",
                options=account.allowed_presentations,
                index=0,
                format_func=format_presentation,
            )
            identity = account.reviewer_id
            role = account.role
            if st.button("Sign out", use_container_width=True):
                st.session_state.pop("authenticated_username", None)
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("### Development connection")
            api_url = st.text_input("Instructor API", value=default_api_url)
            presentation_id = st.text_input("Course presentation", value=default_presentation)
            identity = st.text_input("Pseudonymous reviewer", value=default_identity)
            role = st.selectbox(
                "Role",
                ["instructor", "supervisor"],
                index=0 if default_role == "instructor" else 1,
            )
        if st.button("Refresh course data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.caption("Course access is restricted by the authenticated account context.")
        st.caption("No automatic messages or decisions are sent to learners.")

    st.markdown(
        '<div class="eyebrow">Course digital twin · instructor pilot</div>',
        unsafe_allow_html=True,
    )
    st.title("Student-support workspace")
    st.caption(
        "Identify learners who may need support, inspect the evidence, and record a human decision."
    )

    try:
        ready, overview = load_workspace(api_url, identity, role, presentation_id)
        roster = load_roster(api_url, identity, role, presentation_id)
    except (DashboardApiError, ValueError) as error:
        st.error(str(error))
        st.info("Check the API status and course access, then use Refresh course data.")
        return
    if ready.get("status") != "ok":
        st.error(
            "The API is reachable, but its database is not ready. No learner signals are displayed."
        )
        return
    if roster.get("truncated"):
        st.warning(
            f"Only {len(roster['items']):,} of {roster['total']:,} learners were loaded. "
            "Narrow the course scope."
        )

    roster_items = roster.get("items", [])
    render_model_notice(roster_items)

    if "dashboard_page" not in st.session_state:
        st.session_state["dashboard_page"] = "Overview"
    page = st.radio(
        "Workspace section",
        options=PAGE_OPTIONS,
        horizontal=True,
        label_visibility="collapsed",
        key="dashboard_page",
    )

    if page == "Overview":
        render_overview(roster_items, overview)
    elif page == "Students":
        render_students(api_url, identity, role, presentation_id, roster_items)
    elif page == "Support queue":
        render_support_queue(api_url, identity, role, roster_items)
    else:
        render_data_health(ready, overview, roster_items)


render_dashboard()
