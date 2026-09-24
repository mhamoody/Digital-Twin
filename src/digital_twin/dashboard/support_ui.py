"""Instructor support pages. All data and mutations go through the authorized API."""
from datetime import UTC, datetime, time
import streamlit as st
from .client import DashboardApiError
from .support_view import (ACTIVE, TRANSITIONS, Intent, comparison_text, counters, current_risk,
    due, evidence_view, history_view, action_label, ACTION_DISPLAY_LABELS, load_all, roster_rows,
    scoped_rows, score_label, time_text)
from .view_model import RISK_LABELS

CARD_HELP = {
    "Total learners": "All enrolled learners returned for this course.",
    "High Attention": "Learners with a high current prediction bound to their current state. Instructor actions do not change this count.",
    "New Concerns": "Active support cases with status New concern only.",
    "Ongoing Support": "Active support cases with status Ongoing only. Reviewed cases are separate.",
    "Follow-up Due": "Active cases with a scheduled follow-up at or before now. Closed cases are excluded.",
}


def choose_filter(label):
    st.session_state['support_query'] = ''
    st.session_state['support_risk'] = 'All'
    st.session_state['support_status'] = 'All'
    st.session_state['support_due'] = False
    st.session_state['support_filter'] = label
    st.session_state['dashboard_page'] = 'Students'


def render_workspace(client, presentation, page):
    scope = (client.base_url, tuple(client.headers.items()), presentation)
    if st.session_state.get('support_context') != scope:
        for key in list(st.session_state):
            if key.startswith(('intent:', 'support_', 'case-form-', 'create-form-')):
                del st.session_state[key]
        st.session_state['support_context'] = scope
    try:
        roster = load_all(lambda **kw: client.learners(presentation_id=presentation, **kw))
        cases = load_all(lambda **kw: client.support_cases(presentation, **kw))
        scoped_rows(roster, cases, presentation)
    except DashboardApiError as error:
        st.error(str(error))
        return
    now = datetime.now(UTC)
    if page == 'Overview':
        st.subheader('Course at a glance')
        columns = st.columns(5)
        for column, (label, value) in zip(columns, counters(roster, cases, now).items()):
            column.metric(label, value, help=CARD_HELP[label])
            column.button('View ' + label, key='card-' + label,
                          on_click=choose_filter, args=(label,))
        st.caption('Risk describes the current model signal. Support cases describe instructor work. Counts can overlap.')
        counts = {label: sum(current_risk(r) == band for r in roster)
                  for band, label in RISK_LABELS.items()}
        st.bar_chart(counts, horizontal=True)
        st.caption('Support level: High attention, Watch, On track, or no current score.')
    render_list(client, presentation, roster, cases, now, page)


def render_list(client, presentation, roster, cases, now, page):
    st.subheader('Learners and support' if page != 'Support queue' else 'Support cases')
    options = ['Total learners', 'High Attention', 'New Concerns', 'Ongoing Support', 'Follow-up Due']
    if st.session_state.get('support_filter') not in options:
        st.session_state['support_filter'] = 'Total learners'
    selected_filter = st.selectbox('Show', options, key='support_filter')
    query = st.text_input('Search learner identifier', key='support_query')
    cols = st.columns(3)
    risk = cols[0].selectbox('Model risk', ['All', 'high', 'medium', 'low'],
                            format_func=lambda v: RISK_LABELS.get(v, v), key='support_risk')
    status = cols[1].selectbox('Active case status', ['All', 'new_concern', 'reviewed', 'ongoing', 'none'],
                              format_func=lambda v: v.replace('_', ' ').title(), key='support_status')
    due_only = cols[2].checkbox('Follow-up due only', key='support_due')
    if selected_filter == 'High Attention': risk = 'high'
    if selected_filter == 'New Concerns': status = 'new_concern'
    if selected_filter == 'Ongoing Support': status = 'ongoing'
    due_only = due_only or selected_filter == 'Follow-up Due'
    if page == 'Support queue':
        case_learners = {c['learner_id'] for c in cases if c['status'] in ACTIVE}
        roster = [r for r in roster if r['learner_id'] in case_learners]
        st.caption('Active episodes remain here even when risk decreases or no new prediction is available. Historical episodes are in the learner profile.')
    rows = roster_rows(roster, cases, now, query=query, risk=risk, status=status, due_only=due_only)
    if not rows:
        st.info('No learners match these filters. Use Students to open a manual support case.')
        return
    st.dataframe(rows, hide_index=True, use_container_width=True)
    ids = [r['Learner'] for r in rows]
    if st.session_state.get('support_learner') not in ids:
        st.session_state['support_learner'] = ids[0]
    learner_id = st.selectbox('Open learner profile', ids, key='support_learner')
    # Selecting a learner opens the profile directly, without an additional button.
    render_profile(client, presentation, learner_id, cases, now)


def render_profile(client, presentation, learner_id, cases, now):
    try:
        detail = client.learner_detail(presentation_id=presentation, learner_id=learner_id)
        learner = detail['learner']
        if learner['presentation_id'] != presentation or learner['learner_id'] != learner_id:
            raise DashboardApiError('The requested learner information is unavailable.', 403)
        episodes = [c for c in cases if c['learner_id'] == learner_id and c['data_origin'] == learner['data_origin']]
        histories = [client.support_case(c['case_id']) for c in episodes]
        if any(h['case']['presentation_id'] != presentation or h['case']['learner_id'] != learner_id
               or h['case']['data_origin'] != learner['data_origin'] for h in histories):
            raise DashboardApiError('The requested support information is unavailable.', 403)
        alert_detail = client.alert_detail(learner['alert_id']) if learner.get('alert_id') else None
        if alert_detail and (alert_detail['state_id'] != learner.get('state_id')
                             or alert_detail['alert']['presentation_id'] != presentation
                             or alert_detail['alert']['learner_id'] != learner_id):
            raise DashboardApiError('The current evidence is unavailable.', 403)
    except DashboardApiError as error:
        st.error(str(error))
        return
    st.divider()
    st.subheader('Learner ' + learner_id)
    if message := st.session_state.pop('support_message', None):
        st.info(message)
    st.markdown('#### Current risk')
    st.write(f"Current checkpoint: Week {learner.get('latest_checkpoint_week') or 'unavailable'}")
    st.write('Risk: ' + RISK_LABELS.get(current_risk(learner), 'No current score'))
    st.write(score_label(learner))

    st.markdown('#### Previous vs Current')
    comparison = learner.get('comparison', {})

    if comparison.get('available'):
        st.info(comparison_text(comparison))
    else:
        st.info(
            'Comparison unavailable — '
            + comparison_text(comparison)
        )

    st.markdown('#### Why this learner is flagged — model evidence')
    evidence = alert_detail['evidence'] if alert_detail else detail.get('features', [])
    if not alert_detail:
        st.caption('No current alert. Available observations below are context, not a claim that this learner is at risk.')
    if not evidence: st.caption('No supporting observations are available.')
    for feature in evidence:
        view = evidence_view(feature)
        st.text(view['text'])
        with st.expander('Evidence reference: ' + view['evidence_id']):
            st.text('Feature: ' + view['feature_name'])
            for sample in feature.get('source_record_samples', []): st.text('Source record: ' + sample)
    st.markdown('#### Instructor support')
    active = next((h for h in histories if h['case']['status'] in ACTIVE), None)
    create_scope = 'intent:create:' + learner_id
    if st.session_state.get(create_scope):
        retry_panel(client, create_scope, presentation=presentation)
    if active:
        render_case(client, active, now)
        linked = {l['alert_id'] for h in histories for l in h['linked_alerts']}
        if learner.get('alert_id') and learner['alert_id'] not in linked:
            mutation_form(client, 'link:' + active['case']['case_id'],
                          {'action_type': 'link_alert', 'alert_id': learner['alert_id'],
                           'expected_version': active['case']['version']},
                          case_id=active['case']['case_id'], label='Attach current alert to this case')
    else:
        st.caption('No active support case. Opening one records instructor work; it does not change model risk.')
        payload = {'learner_id': learner_id}
        linked = {l['alert_id'] for h in histories for l in h['linked_alerts']}
        if learner.get('alert_id') and learner['alert_id'] not in linked:
            payload['alert_id'] = learner['alert_id']
        if not st.session_state.get(create_scope):
            mutation_form(client, 'create:' + learner_id, payload, presentation=presentation,
                          label='Open new support case')
    st.markdown('#### Support activity')
    if not histories: st.caption('No recorded support history.')
    for history in histories:
        case = history['case']
        for prefix in ('intent:case:', 'intent:link:'):
            pending_scope = prefix + case['case_id']
            if case['status'] not in ACTIVE and st.session_state.get(pending_scope):
                retry_panel(client, pending_scope, case_id=case['case_id'])
        with st.expander(f"{case['status'].replace('_', ' ').title()} · opened {time_text(case['opened_at'])}",
                         expanded=case['status'] in ACTIVE):
            latest = history['actions'][-1] if history['actions'] else None
            st.write('Current case: ' + case['status'].replace('_', ' ').title())
            st.write('Opened: ' + time_text(case['opened_at']))
            if latest:
                st.caption('Latest action: ' + action_label(latest['action_type']) +
                           ' · ' + time_text(latest['created_at']))
            st.caption('Closed episodes are read-only. A later concern starts a new episode.' if case['status'] not in ACTIVE
                       else 'Human support actions are shown below; model evidence is separate.')
            for action in history['actions']:
                view = history_view(action)
                st.markdown('---')
                st.write(view['timestamp'])
                st.write(action_label(action['action_type']))
                st.caption('By: ' + view['actor'])
                if view['note']: st.text('Note: ' + view['note'])
                if action['action_type'] in ('create_case', 'transition_status'):
                    st.text(f"Status: {(view['status'][0] or 'No case').replace('_', ' ').title()} → {view['status'][1].replace('_', ' ').title()}")
                if action['action_type'] in ('set_follow_up', 'clear_follow_up'):
                    st.text(f"Follow-up: {time_text(view['follow_up'][0])} → {time_text(view['follow_up'][1])}")
    st.markdown('#### Linked model evidence')
    for history in histories:
        for link in history['linked_alerts']:
            with st.expander(f"Week {link['checkpoint']} · {len(history['linked_alerts'])} linked alert(s)"):
                try:
                    linked_detail = client.alert_detail(link['alert_id'])
                    if (linked_detail['alert']['presentation_id'] != presentation or
                        linked_detail['alert']['learner_id'] != learner_id):
                        raise DashboardApiError('The requested evidence is unavailable.', 403)
                    for feature in linked_detail['evidence']:
                        view = evidence_view(feature)
                        st.text(view['text'])
                    with st.expander('Technical evidence details'):
                        for feature in linked_detail['evidence']:
                            view = evidence_view(feature)
                            st.text(view['evidence_id'])
                except DashboardApiError as error:
                    st.error(str(error))


def render_case(client, detail, now):
    case = detail['case']
    st.write('Case: ' + case['status'].replace('_', ' ').title())
    st.caption(f"Opened {time_text(case['opened_at'])} · {len(detail['linked_alerts'])} linked alert(s)")
    if case.get('follow_up_due_at'):
        st.write(('Follow-up due: ' if due(case, now) else 'Follow-up scheduled: ') + time_text(case['follow_up_due_at']))
    if detail['actions']:
        last = detail['actions'][-1]
        st.caption(f"Latest action: {last['action_type'].replace('_', ' ')} · {time_text(last['created_at'])}")
    if case['status'] not in ACTIVE: return
    scope = 'intent:case:' + case['case_id']
    if st.session_state.get(scope):
        retry_panel(client, scope, case_id=case['case_id'])
        return
    choices = ['add_note', 'set_follow_up']
    if case.get('follow_up_due_at'): choices.append('clear_follow_up')
    choices += list(TRANSITIONS.get(case['status'], ()))
    version_key = 'support_form_version:' + case['case_id']
    displayed_version = st.session_state.get(version_key, case['version'])
    with st.form('case-form-' + case['case_id'], clear_on_submit=True):
        # The widget exposes presentation labels only; all branching and payload
        # construction use the canonical internal action key.
        display_to_key = {ACTION_DISPLAY_LABELS.get(v, v): v for v in choices}
        selected_label = st.selectbox('Instructor action', list(display_to_key))
        kind = display_to_key[selected_label]
        note = None
        if kind == 'add_note':
            note = st.text_area('Instructor note', max_chars=4000)
        elif kind == 'set_follow_up':
            note = st.text_area('Follow-up note', max_chars=4000)
        elif kind in TRANSITIONS.get(case['status'], ()):
            note = st.text_area({
                'reviewed': 'Review note', 'ongoing': 'Support note',
                'resolved': 'Resolution note', 'dismissed': 'Dismissal note',
            }.get(kind, 'Support note'), max_chars=4000)
        if kind == 'set_follow_up':
            cols = st.columns(2)
            day = cols[0].date_input('Follow-up date', value=now.date())
            hour = cols[1].time_input('Follow-up time — UTC', value=time(9, 0))
        else:
            day = hour = None
        st.caption('Records your decision only. No message is sent to the learner.')
        submitted = st.form_submit_button('Save support action')
    if submitted:
        if kind == 'add_note' and not note.strip():
            st.error('Enter a note before saving.'); return
        payload = {'expected_version': displayed_version}
        if kind in TRANSITIONS.get(case['status'], ()):
            payload.update(action_type='transition_status', target_status=kind)
        else: payload['action_type'] = kind
        if note and note.strip(): payload['note'] = note.strip()
        if kind == 'set_follow_up': payload['follow_up_due_at'] = datetime.combine(day, hour, tzinfo=UTC).isoformat()
        Intent.prepare(st.session_state, scope, payload)
        submit(client, scope, case_id=case['case_id'])
    else:
        st.session_state[version_key] = case['version']


def mutation_form(client, key, payload, *, case_id=None, presentation=None, label):
    scope = 'intent:' + key
    if st.session_state.get(scope):
        retry_panel(client, scope, case_id=case_id, presentation=presentation)
    elif st.button(label, key=key):
        Intent.prepare(st.session_state, scope, st.session_state.get('support_payload:' + key, payload))
        submit(client, scope, case_id=case_id, presentation=presentation)
    else:
        st.session_state['support_payload:' + key] = payload


def retry_panel(client, scope, *, case_id=None, presentation=None):
    st.warning('The last request has not been confirmed. Retry the original action before submitting another.')
    pending = st.session_state[scope]
    st.text('Pending action: ' + pending.get('action_type', 'open support case').replace('_', ' '))
    if pending.get('note'): st.text('Instructor note: ' + pending['note'])
    if pending.get('follow_up_due_at'): st.text(time_text(pending['follow_up_due_at']))
    if st.button('Retry original action', key='retry-' + scope):
        submit(client, scope, case_id=case_id, presentation=presentation)


def submit(client, scope, *, case_id=None, presentation=None):
    send = (lambda p: client.support_action(case_id, p)) if case_id else (lambda p: client.create_support_case(presentation, p))
    try:
        status, result = Intent.send(st.session_state, scope, send,
                                    lambda: client.support_case(case_id) if case_id else client.support_cases(presentation))
    except DashboardApiError as error:
        st.error(str(error))
        return
    st.session_state['support_message'] = (
        'This case changed or the request conflicts with its current state. The latest version has been reloaded. Review it before acting again.'
        if status == 'conflict' else 'Support action saved. Model risk is unchanged by this action.')
    st.cache_data.clear()
    st.rerun()
