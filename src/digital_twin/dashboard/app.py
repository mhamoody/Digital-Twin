"""Streamlit instructor workspace backed exclusively by the Phase 4 API."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

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

RISK_COLORS = {"high": "#d1495b", "medium": "#f59e0b", "low": "#2a9d8f"}


def client_for(api_url: str, identity: str, role: str) -> DashboardApiClient:
    return DashboardApiClient(base_url=api_url, instructor_id=identity, instructor_role=role)


@st.cache_data(ttl=15, show_spinner=False)
def load_workspace(api_url: str, identity: str, role: str, presentation_id: str):
    client = client_for(api_url, identity, role)
    return (
        client.readiness(),
        client.presentation_overview(presentation_id),
        client.alerts(presentation_id=presentation_id),
    )


@st.cache_data(ttl=15, show_spinner=False)
def load_alert(api_url: str, identity: str, role: str, alert_id: str):
    return client_for(api_url, identity, role).alert_detail(alert_id)


@st.cache_data(ttl=15, show_spinner=False)
def load_learners(
    api_url: str, identity: str, role: str, presentation_id: str, query: str
):
    return client_for(api_url, identity, role).learners(
        presentation_id=presentation_id, query=query or None
    )


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
    st.title("Sign in to the course digital twin")
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


def format_alert(item: dict) -> str:
    probability = float(item["display_probability"]) * 100
    return (
        f"{item['learner_id']} · week {item['checkpoint_week']} · "
        f"{item['risk_band'].upper()} {probability:.1f}% · {item['status']}"
    )


def render_dashboard() -> None:
    st.set_page_config(
        page_title="Instructor early-warning workspace",
        page_icon="◎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
          .block-container {padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1440px;}
          [data-testid="stToolbar"] {visibility: hidden;}
          [data-testid="stHeader"] {background: transparent;}
          [data-testid="stMetric"] {background: #f6f8fb; border: 1px solid #e3e8ef;
            border-radius: 12px; padding: 14px 16px;}
          [data-testid="stMetric"] * {color: #162434 !important;}
          .eyebrow {font-size: .78rem; letter-spacing: .09em; text-transform: uppercase;
            color: #526070; font-weight: 700;}
          .status-chip {display:inline-block; padding:.2rem .55rem; border-radius:999px;
            background:#e8f5ef; color:#126343; font-size:.8rem; font-weight:700;}
          .demo-note {border-left: 5px solid #d97706; background:#fff8e8; padding: .8rem 1rem;
            border-radius: 8px; margin:.7rem 0 1rem; color:#573a08;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    if review_message := st.session_state.pop("review_success", None):
        st.success(review_message)

    default_api_url = os.environ.get("DIGITAL_TWIN_API_URL", "http://127.0.0.1:8000")
    default_presentation = os.environ.get(
        "DIGITAL_TWIN_PRESENTATION_ID", "oulad:AAA:2013J"
    )
    default_identity = os.environ.get(
        "DIGITAL_TWIN_DASHBOARD_ID", "instructor:dashboard-demo"
    )
    default_role = os.environ.get("DIGITAL_TWIN_DASHBOARD_ROLE", "instructor")

    auth_file = os.environ.get("DIGITAL_TWIN_AUTH_FILE")
    account = require_pilot_login(auth_file) if auth_file else None
    if auth_file and account is None:
        return

    with st.sidebar:
        if account:
            st.markdown(f"### {account.display_name}")
            st.caption(f"Pilot role: {account.role}")
            api_url = default_api_url
            presentation_id = st.selectbox(
                "Course", options=account.allowed_presentations, index=0
            )
            identity = account.reviewer_id
            role = account.role
            if st.button("Sign out", use_container_width=True):
                st.session_state.pop("authenticated_username", None)
                st.cache_data.clear()
                st.rerun()
        else:
            st.markdown("### Workspace connection")
            api_url = st.text_input("Instructor API", value=default_api_url)
            presentation_id = st.text_input("Course presentation", value=default_presentation)
            identity = st.text_input("Pseudonymous reviewer", value=default_identity)
            role = st.selectbox(
                "Role",
                ["instructor", "supervisor"],
                index=0 if default_role == "instructor" else 1,
            )
        if st.button("Refresh data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        if account:
            st.caption("Course access is restricted by the server-side account file.")
        else:
            st.caption("Development identity headers only — not institutional authentication.")

    st.markdown(
        '<div class="eyebrow">Course digital twin · integration demo</div>',
        unsafe_allow_html=True,
    )
    st.title("Instructor early-warning workspace")
    st.caption("Review traceable signals, inspect their evidence, and record a human decision.")
    st.markdown(
        """
        <div class="demo-note"><strong>Temporary predictor:</strong> these alerts use
        <code>simple-rules-v1</code>, a deterministic plumbing model. It is not trained,
        calibrated, or the final strong LLM, so its scores are not research findings.</div>
        """,
        unsafe_allow_html=True,
    )

    try:
        ready, overview, alert_page = load_workspace(api_url, identity, role, presentation_id)
    except (DashboardApiError, ValueError) as error:
        st.error(str(error))
        st.info("Start PostgreSQL and FastAPI, verify the course ID, then use Refresh data.")
        return

    if ready.get("status") != "ok":
        st.error("The API is reachable but its database is not ready. No alerts are displayed.")
        return

    ingestion_status = overview.get("ingestion_status", "not_configured")
    freshness = "Current" if overview["all_current_alerts_fresh"] else "Stale/failed"
    freshness_icon = "✓" if overview["all_current_alerts_fresh"] else "⚠"
    database_backend = ready.get("database_backend", "database")
    st.markdown(
        f'<span class="status-chip">{freshness_icon} API + {database_backend} ready</span>',
        unsafe_allow_html=True,
    )
    metric_columns = st.columns(5)
    metric_columns[0].metric("Learners", f"{overview['learner_count']:,}")
    metric_columns[1].metric("Weekly states", f"{overview['state_count']:,}")
    metric_columns[2].metric("Predictions", f"{overview['prediction_count']:,}")
    metric_columns[3].metric("Alerts", f"{overview['alert_count']:,}")
    metric_columns[4].metric("Freshness", freshness)
    st.caption(
        f"Presentation {overview['module_code']} / {overview['presentation_code']} · "
        f"origin: {overview['data_origin']} · latest state build: "
        f"{overview['latest_state_built_at'] or 'not available'} · "
        f"ingestion: {ingestion_status} · last success: "
        f"{overview.get('last_ingestion_success_at') or 'not configured'}"
    )
    if not overview["all_current_alerts_fresh"]:
        st.warning("Some alerts are stale. Confirm ingestion and rebuild status before acting.")
    if overview.get("active_quarantine_count", 0):
        st.error(
            f"{overview['active_quarantine_count']} ingestion record(s) require recovery."
        )

    st.divider()
    with st.expander("Course roster and learner activity", expanded=True):
        roster_query = st.text_input(
            "Find learner", placeholder="Search by pseudonymous learner ID"
        )
        try:
            roster = load_learners(api_url, identity, role, presentation_id, roster_query)
        except DashboardApiError as error:
            st.error(str(error))
        else:
            roster_items = roster.get("items", [])
            st.caption(f"{roster.get('total', 0)} learner(s) match this course view.")
            if not roster_items:
                st.info("No learners match this search.")
            else:
                roster_frame = pd.DataFrame(
                    [
                        {
                            "learner": item["learner_id"],
                            "week": item.get("latest_checkpoint_week"),
                            "risk": item.get("risk_band") or "no current score",
                            "score": item.get("display_probability"),
                            "alert": item.get("alert_status") or "none",
                            "evidence": item.get("evidence_count", 0),
                        }
                        for item in roster_items
                    ]
                )
                st.dataframe(
                    roster_frame,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "score": st.column_config.NumberColumn("risk score", format="percent")
                    },
                )
                learner_id = st.selectbox(
                    "Inspect learner activity",
                    options=[item["learner_id"] for item in roster_items],
                )
                try:
                    learner_detail = load_learner(
                        api_url, identity, role, presentation_id, learner_id
                    )
                except DashboardApiError as error:
                    st.error(str(error))
                else:
                    activity_tab, features_tab = st.tabs(
                        ["Weekly activity", "Latest state features"]
                    )
                    with activity_tab:
                        activity = pd.DataFrame(learner_detail.get("activity_timeline", []))
                        if activity.empty:
                            st.info("No dated activity is available for this learner.")
                        else:
                            st.line_chart(
                                activity,
                                x="course_week",
                                y=["activity_count", "assessment_event_count"],
                                x_label="Course week",
                                y_label="Recorded events",
                            )
                            st.dataframe(activity, hide_index=True, use_container_width=True)
                    with features_tab:
                        features = pd.DataFrame(learner_detail.get("features", []))
                        if features.empty:
                            st.info("No weekly state has been built for this learner.")
                        else:
                            st.dataframe(features, hide_index=True, use_container_width=True)

    queue_items = alert_page.get("items", [])
    st.divider()
    queue_column, detail_column = st.columns([0.9, 1.5], gap="large")
    with queue_column:
        st.subheader("Ranked review queue")
        st.caption(f"{alert_page.get('total', 0)} alerts · high priority first")
        status_filter = st.segmented_control(
            "Alert status",
            options=["all", "new", "reviewed", "resolved", "dismissed"],
            default="all",
        )
        visible_items = [
            item
            for item in queue_items
            if status_filter == "all" or item["status"] == status_filter
        ]
        if not visible_items:
            st.info("No alerts match this status in the loaded queue.")
            return
        selected_id = st.selectbox(
            "Select learner alert",
            options=[item["alert_id"] for item in visible_items],
            format_func=lambda alert_id: format_alert(
                next(item for item in visible_items if item["alert_id"] == alert_id)
            ),
            label_visibility="collapsed",
        )
        queue_frame = pd.DataFrame(
            [
                {
                    "learner": item["learner_id"],
                    "week": item["checkpoint_week"],
                    "risk": item["risk_band"],
                    "score": item["display_probability"],
                    "status": item["status"],
                    "fresh": item["is_fresh"],
                }
                for item in visible_items[:15]
            ]
        )
        st.dataframe(
            queue_frame,
            hide_index=True,
            use_container_width=True,
            column_config={
                "score": st.column_config.ProgressColumn(
                    "risk score", min_value=0.0, max_value=1.0, format="percent"
                ),
                "fresh": st.column_config.CheckboxColumn("fresh"),
            },
        )

    try:
        detail = load_alert(api_url, identity, role, selected_id)
    except DashboardApiError as error:
        with detail_column:
            st.error(str(error))
        return

    alert = detail["alert"]
    with detail_column:
        st.subheader(f"Alert evidence · {alert['learner_id']}")
        checkpoint_description = (
            f"Checkpoint week {alert['checkpoint_week']} "
            f"(course day {alert['cutoff_course_day']})"
        )
        st.caption(
            f"{checkpoint_description} · "
            f"model {alert['model_version']} · origin {alert['data_origin']}"
        )
        risk_color = RISK_COLORS.get(alert["risk_band"], "#526070")
        st.markdown(
            f"<h2 style='color:{risk_color}; margin-bottom:.1rem'>"
            f"{float(alert['display_probability']):.1%} {alert['risk_band'].upper()} risk</h2>",
            unsafe_allow_html=True,
        )
        state_columns = st.columns(4)
        state_columns[0].metric("Alert status", alert["status"])
        state_columns[1].metric("Evidence items", alert["evidence_count"])
        state_columns[2].metric("Completeness", f"{float(detail['completeness']):.0%}")
        state_columns[3].metric("Fresh", "Yes" if alert["is_fresh"] else "NO")
        if not alert["is_fresh"]:
            st.error("This alert is stale. Do not treat it as a current learner signal.")
        if detail["fallback_used"] or not detail["quality_gate_passed"]:
            st.warning(
                "Fallback or quality-gate condition is active. Inspect evidence before review."
            )

        tabs = st.tabs(["Evidence", "Learner timeline", "Human review"])
        with tabs[0]:
            st.markdown(f"**Uncertainty:** {detail['uncertainty_note']}")
            if detail["claims"]:
                st.markdown("**Grounded claims**")
                for claim in detail["claims"]:
                    st.write(f"• `{claim['claim_code']}` → {', '.join(claim['evidence_ids'])}")
            evidence_frame = pd.DataFrame(
                [
                    {
                        "feature": row["feature_name"],
                        "value": row["value"],
                        "missing reason": row["missing_reason"],
                        "source rows": row["source_observation_count"],
                    }
                    for row in detail["evidence"]
                ]
            )
            st.dataframe(evidence_frame, hide_index=True, use_container_width=True)
            with st.expander("Provenance samples and state identifiers"):
                st.code(
                    f"state_id={detail['state_id']}\n"
                    f"feature_set={detail['feature_set_version']}\n"
                    f"input_hash={detail['input_hash']}"
                )
                for row in detail["evidence"]:
                    samples = row["source_record_samples"] or ["No direct source row"]
                    st.write(f"`{row['evidence_id']}`: {', '.join(samples)}")
            if detail["suggested_actions"]:
                st.markdown("**Suggested instructor actions (not automatic)**")
                for action in detail["suggested_actions"]:
                    st.write(f"• {action}")

        with tabs[1]:
            timeline = pd.DataFrame(detail["prediction_timeline"])
            if timeline.empty:
                st.info("No prior checkpoint predictions are available.")
            else:
                timeline = timeline.sort_values("checkpoint_week")
                st.line_chart(
                    timeline,
                    x="checkpoint_week",
                    y="display_probability",
                    y_label="Displayed risk score",
                    x_label="Checkpoint week",
                )
                st.dataframe(
                    timeline[
                        [
                            "checkpoint_week",
                            "cutoff_course_day",
                            "display_probability",
                            "risk_band",
                            "model_version",
                        ]
                    ],
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "display_probability": st.column_config.NumberColumn(
                            "risk score", format="percent"
                        )
                    },
                )
                st.caption("Scores are checkpoint snapshots, not causal explanations or diagnoses.")

        with tabs[2]:
            if detail["review_history"]:
                st.markdown("**Audited history**")
                st.dataframe(pd.DataFrame(detail["review_history"]), hide_index=True)
            else:
                st.caption("No prior human review has been recorded.")
            terminal_alert = alert["status"] in {"resolved", "dismissed"}
            if terminal_alert:
                st.info("This alert is terminal; its review history remains read-only.")
            with st.form("review-alert", clear_on_submit=False):
                status_options = [
                    status
                    for status in ["reviewed", "resolved", "dismissed"]
                    if status != alert["status"]
                ]
                new_status = st.selectbox("Record decision", status_options)
                note = st.text_area(
                    "Review note (optional)",
                    max_chars=1000,
                    placeholder="Record only the minimum educationally relevant context.",
                )
                submitted = st.form_submit_button(
                    "Save audited review", type="primary", disabled=terminal_alert
                )
                if submitted:
                    try:
                        response = client_for(api_url, identity, role).review_alert(
                            alert_id=selected_id,
                            new_status=new_status,
                            note=note,
                            idempotency_key=f"dashboard-{uuid4()}",
                        )
                    except DashboardApiError as error:
                        st.error(str(error))
                    else:
                        st.session_state["review_success"] = (
                            f"Review saved: {response['status']} at {response['reviewed_at']}"
                        )
                        st.cache_data.clear()
                        st.rerun()


render_dashboard()
