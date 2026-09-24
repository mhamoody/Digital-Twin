from datetime import UTC, datetime, timedelta
import httpx
import pytest
from digital_twin.dashboard.client import DashboardApiClient, DashboardApiError
from digital_twin.dashboard.support_view import *

NOW = datetime(2026, 9, 15, tzinfo=UTC)

def learner(**kw):
    return dict(learner_id='l1', presentation_id='course', data_origin='synthetic',
                state_id='s1', prediction_id='p1', prediction_state_id='s1',
                assessment_status='assessed', risk_band='high', raw_risk_score=.65,
                calibration_version='identity-demo-v1', **kw)

def case(status='new_concern', when=None):
    return dict(case_id='c1', learner_id='l1', presentation_id='course', data_origin='synthetic',
                status=status, follow_up_due_at=when)

@pytest.mark.parametrize('status', ['new_concern', 'reviewed', 'ongoing', 'resolved', 'dismissed'])
def test_independent_counters(status):
    counts = counters([learner()], [case(status, NOW)], NOW)
    assert counts['High Attention'] == 1
    assert counts['New Concerns'] == int(status == 'new_concern')
    assert counts['Ongoing Support'] == int(status == 'ongoing')
    assert counts['Follow-up Due'] == int(status in ACTIVE)


def test_due_and_binding():
    assert not due(case('ongoing', NOW + timedelta(days=1)), NOW)
    assert not due(case('ongoing'), NOW)
    r = learner(); r['prediction_state_id'] = 'old'
    assert counters([r], [], NOW)['High Attention'] == 0
    rows = roster_rows([learner()], [case('ongoing', NOW)], NOW, due_only=True)
    assert rows[0]['Risk'] == 'High attention' and rows[0]['Case'] == 'Ongoing'
    assert not roster_rows([learner()], [case('ongoing')], NOW, status='new_concern')


def test_uncalibrated_score():
    text = score_label(learner())
    assert '65 / 100' in text and 'Uncalibrated' in text
    assert '%' not in text and 'probability' not in text

@pytest.mark.parametrize('reason', list(REASONS))
def test_unavailable_comparison(reason):
    text = comparison_text(dict(available=False, reason=reason, delta=.9, previous_value=.1))
    assert text == REASONS[reason] and '→' not in text and '90' not in text


def test_available_comparison_uses_contract():
    text = comparison_text(dict(available=True, previous_checkpoint=3, current_checkpoint=5,
                                previous_value=.1, current_value=.3, delta=.2))
    assert 'Week 3' in text and 'Week 5' in text and '+20.0' in text

@pytest.mark.parametrize('name', ['Quiz 2', None])
def test_assessment_evidence(name):
    feature = dict(evidence_id='ev1', feature_name='assessment_result', missing_reason='observed',
                   value=dict(assessment_id='A2', assessment_name=name, score=42, score_scale='percent'))
    view = evidence_view(feature)
    assert view['text'] == ('Quiz 2' if name else 'A2') + ': 42%'
    assert view['category'] == 'assessment' and view['kind'] == 'model_evidence'


def test_evidence_missing_and_notes_separate():
    view = evidence_view(dict(evidence_id='ev', feature_name='clicks_last_14', value=8, missing_reason='observed'))
    assert view['text'] == '8 recorded interactions in the last 14 days.'
    unknown = evidence_view(dict(evidence_id='ev', feature_name='unknown', value=None, missing_reason='source_missing'))
    assert 'missing' in unknown['text']
    h = history_view(dict(actor_id='instructor:x', created_at=NOW, action_type='add_note', note='Human note'))
    assert h['kind'] != view['kind'] and h['note'] == 'Human note'

@pytest.mark.parametrize('status,expected', [('new_concern',4), ('reviewed',3), ('ongoing',3), ('resolved',0), ('dismissed',0)])
def test_transition_controls(status, expected):
    assert len(TRANSITIONS.get(status, ())) == expected
    assert 'new_concern' not in TRANSITIONS.get(status, ())


def test_intent_network_retry_and_conflict():
    state = {}; request = Intent.prepare(state, 'x', {'action_type':'add_note', 'note':'original'})
    assert Intent.prepare(state, 'x', {'note':'changed'}) == request
    seen = []
    def send(p):
        seen.append(p.copy())
        if len(seen) == 1: raise DashboardApiError('network')
        return {'resulting_version':2}
    with pytest.raises(DashboardApiError): Intent.send(state, 'x', send, lambda:None)
    assert Intent.send(state, 'x', send, lambda:None)[0] == 'saved'
    assert seen[0] == seen[1] and 'x' not in state
    Intent.prepare(state, 'x', {'note':'another'})
    reloads = []
    def conflict(p): raise DashboardApiError('conflict',409)
    assert Intent.send(state,'x',conflict,lambda:reloads.append(True))[0] == 'conflict'
    assert reloads == [True] and 'x' not in state


def test_authorization_and_pagination():
    with pytest.raises(DashboardApiError): scoped_rows([learner()], [case()], 'other')
    calls=[]
    def fetch(**kw):
        calls.append(kw['offset']); return {'items':[case()], 'total':2}
    assert len(load_all(fetch)) == 2 and calls == [0,1]


def test_client_support_calls_and_conflicts():
    requests=[]
    def route(request):
        requests.append(request)
        return httpx.Response(409 if request.url.path.endswith('/actions') else 200,json={})
    c=DashboardApiClient(base_url='http://test',instructor_id='instructor:test',instructor_role='instructor',transport=httpx.MockTransport(route))
    c.support_cases('course');c.support_case('c1');c.create_support_case('course',{'learner_id':'l1','idempotency_key':'same-key'})
    with pytest.raises(DashboardApiError) as exc: c.support_action('c1',{'expected_version':1})
    assert exc.value.status_code==409
    assert all(r.headers['X-Instructor-ID']=='instructor:test' for r in requests)
    assert requests[2].method=='POST' and b'same-key' in requests[2].content

@pytest.mark.parametrize("terminal", ["resolved", "dismissed"])
def test_streamlit_workflow_smoke(client, seed, monkeypatch, terminal):
    from streamlit.testing.v1 import AppTest
    seed(3)
    def request(self, method, path, **kwargs):
        kwargs.pop('authenticated', None)
        response = client.request(method, path, headers=self.headers, **kwargs)
        if response.status_code >= 400:
            raise DashboardApiError('Request failed', response.status_code)
        return response.json()
    monkeypatch.setattr(DashboardApiClient, '_request', request)
    app = AppTest.from_string('''
from digital_twin.dashboard.client import DashboardApiClient
from digital_twin.dashboard.support_ui import render_workspace
client = DashboardApiClient(base_url='http://test', instructor_id='instructor:test', instructor_role='instructor')
render_workspace(client, 'oulad:AAA:2013J', 'Overview')
''', default_timeout=20).run()
    assert not app.exception
    assert any(m.label == 'High Attention' for m in app.metric)
    next(b for b in app.button if b.label == 'Open new support case').click().run()
    assert not app.exception
    next(t for t in app.text_area if 'Instructor note' in t.label).set_value('Recorded check-in')
    next(b for b in app.button if b.label == 'Save support action').click().run()
    assert not app.exception
    app.run()  # ordinary rerun is read-only
    cases = client.get('/api/v1/presentations/oulad:AAA:2013J/support-cases',
                       headers={'X-Instructor-ID':'instructor:test','X-Instructor-Role':'instructor'}).json()
    history = client.get('/api/v1/support-cases/'+cases['items'][0]['case_id'],
                         headers={'X-Instructor-ID':'instructor:test','X-Instructor-Role':'instructor'}).json()
    assert len(history['actions']) == 2
    assert history['actions'][-1]['note'] == 'Recorded check-in'

    display = {'reviewed': 'Reviewed', 'ongoing': 'Ongoing', 'set_follow_up': 'Set Follow Up',
               'clear_follow_up': 'Clear Follow Up', 'resolved': 'Resolved', 'dismissed': 'Dismissed'}
    for choice in ('reviewed', 'ongoing', 'set_follow_up', 'clear_follow_up', terminal):
        next(w for w in app.selectbox if w.label == 'Instructor action').select(display[choice]).run()
        labels = [w.label for w in app.text_area]
        date_labels = [w.label for w in app.date_input]
        time_labels = [w.label for w in app.time_input]
        if choice == 'reviewed':
            assert 'Review note' in labels and not date_labels and not time_labels
        elif choice == 'ongoing':
            assert 'Support note' in labels and not date_labels and not time_labels
        elif choice == 'set_follow_up':
            assert 'Follow-up note' in labels and 'Follow-up date' in date_labels
            assert 'Follow-up time — UTC' in time_labels
        elif choice == 'clear_follow_up':
            assert not date_labels and not time_labels
        else:
            assert not date_labels and not time_labels
            expected = 'Resolution note' if choice == 'resolved' else 'Dismissal note'
            assert expected in labels
        next(b for b in app.button if b.label == 'Save support action').click().run()
        assert not app.exception
    assert not any(w.label == 'Instructor action' for w in app.selectbox)
    assert any('Recorded check-in' in t.value for t in app.text)
    assert any('read-only' in c.value for c in app.caption)
    next(b for b in app.button if b.label == 'Open new support case').click().run()
    assert not app.exception
    assert any(w.label == 'Instructor action' for w in app.selectbox)

def test_streamlit_submits_displayed_version_and_reloads(client, seed, monkeypatch):
    from streamlit.testing.v1 import AppTest
    seed(3)
    headers = {'X-Instructor-ID':'instructor:test', 'X-Instructor-Role':'instructor'}
    created = client.post('/api/v1/presentations/oulad:AAA:2013J/support-cases', headers=headers,
                          json={'learner_id':'l1','idempotency_key':'setup-case'}).json()
    posted = []
    def request(self, method, path, **kwargs):
        if path.endswith('/actions') and method == 'POST': posted.append(kwargs['json'].copy())
        response = client.request(method, path, headers=self.headers, **kwargs)
        if response.status_code >= 400: raise DashboardApiError('Conflict', response.status_code)
        return response.json()
    monkeypatch.setattr(DashboardApiClient, '_request', request)
    app = AppTest.from_string('''
from digital_twin.dashboard.client import DashboardApiClient
from digital_twin.dashboard.support_ui import render_workspace
c = DashboardApiClient(base_url='http://test', instructor_id='instructor:test', instructor_role='instructor')
render_workspace(c, 'oulad:AAA:2013J', 'Students')
''', default_timeout=20).run()
    path = '/api/v1/support-cases/' + created['case_id']
    assert client.post(path + '/actions', headers=headers, json={'action_type':'add_note',
        'note':'Other reviewer', 'expected_version':1, 'idempotency_key':'other-note'}).status_code == 200
    next(t for t in app.text_area).set_value('Stale draft')
    next(b for b in app.button if b.label == 'Save support action').click().run()
    assert not app.exception
    assert posted[0]['expected_version'] == 1  # not the newly fetched version 2
    assert any('reloaded' in i.value for i in app.info)
    history = client.get(path, headers=headers).json()
    assert len(history['actions']) == 2 and history['case']['version'] == 2


@pytest.mark.parametrize('mode', ['denied', 'wrong_course'])
def test_streamlit_does_not_render_unauthorized_data(monkeypatch, mode):
    from streamlit.testing.v1 import AppTest
    def request(self, method, path, **kwargs):
        if mode == 'denied': raise DashboardApiError('Access unavailable', 403)
        return {'items':[learner()], 'total':1}
    monkeypatch.setattr(DashboardApiClient, '_request', request)
    app = AppTest.from_string('''
from digital_twin.dashboard.client import DashboardApiClient
from digital_twin.dashboard.support_ui import render_workspace
c = DashboardApiClient(base_url='http://test', instructor_id='instructor:test', instructor_role='instructor')
render_workspace(c, 'another-course', 'Overview')
''', default_timeout=20).run()
    assert not app.exception and app.error
    assert not app.metric and not app.dataframe and not app.selectbox

@pytest.mark.parametrize('kind', ['create', 'add_note', 'resolved'])
def test_streamlit_recovers_lost_success_response(client, seed, monkeypatch, kind):
    from streamlit.testing.v1 import AppTest
    seed(3)
    headers = {'X-Instructor-ID':'instructor:test','X-Instructor-Role':'instructor'}
    if kind != 'create':
        client.post('/api/v1/presentations/oulad:AAA:2013J/support-cases', headers=headers,
                    json={'learner_id':'l1','idempotency_key':'setup-case'})
    writes = []
    def request(self, method, path, **kwargs):
        response = client.request(method, path, headers=self.headers, **kwargs)
        if response.status_code >= 400: raise DashboardApiError('Error', response.status_code)
        if method == 'POST':
            writes.append(kwargs['json'].copy())
            if len(writes) == 1: raise DashboardApiError('Connection interrupted after submission')
        return response.json()
    monkeypatch.setattr(DashboardApiClient, '_request', request)
    app = AppTest.from_string('''
from digital_twin.dashboard.client import DashboardApiClient
from digital_twin.dashboard.support_ui import render_workspace
c=DashboardApiClient(base_url='http://test', instructor_id='instructor:test', instructor_role='instructor')
render_workspace(c, 'oulad:AAA:2013J', 'Students')
''', default_timeout=20).run()
    if kind == 'create':
        next(b for b in app.button if b.label == 'Open new support case').click().run()
    else:
        display = {'add_note': 'Add Note', 'resolved': 'Resolved'}
        next(w for w in app.selectbox if w.label == 'Instructor action').select(display[kind])
        next(w for w in app.text_area).set_value('One intended action')
        next(b for b in app.button if b.label == 'Save support action').click().run()
    assert app.error and not app.exception
    app.run()
    next(b for b in app.button if b.label == 'Retry original action').click().run()
    assert not app.exception
    assert writes[0] == writes[1]
    cases = client.get('/api/v1/presentations/oulad:AAA:2013J/support-cases', headers=headers).json()
    assert cases['total'] == 1
    detail = client.get('/api/v1/support-cases/' + cases['items'][0]['case_id'], headers=headers).json()
    assert len(detail['actions']) == (1 if kind == 'create' else 2)


def test_rejected_contract_can_be_corrected():
    state = {}
    first = Intent.prepare(state, 'x', {'action_type':'add_note', 'note':'bad'})
    def reject(payload): raise DashboardApiError('Validation rejected', 422)
    with pytest.raises(DashboardApiError): Intent.send(state, 'x', reject, lambda:None)
    second = Intent.prepare(state, 'x', {'action_type':'add_note', 'note':'corrected'})
    assert second['idempotency_key'] != first['idempotency_key']


def test_full_dashboard_card_navigation(client, seed, monkeypatch):
    from streamlit.testing.v1 import AppTest
    seed(3)
    monkeypatch.delenv('DIGITAL_TWIN_AUTH_FILE', raising=False)
    monkeypatch.setenv('DIGITAL_TWIN_DASHBOARD_ID', 'instructor:test')
    monkeypatch.setenv('DIGITAL_TWIN_PRESENTATION_ID', 'oulad:AAA:2013J')
    def request(self, method, path, **kwargs):
        kwargs.pop('authenticated', None)
        response = client.request(method, path, headers=self.headers, **kwargs)
        if response.status_code >= 400: raise DashboardApiError('Access unavailable',response.status_code)
        return response.json()
    monkeypatch.setattr(DashboardApiClient, '_request', request)
    app = AppTest.from_string('''
from digital_twin.dashboard.client import DashboardApiClient
from digital_twin.dashboard.support_ui import render_workspace
c = DashboardApiClient(base_url='http://test', instructor_id='instructor:test', instructor_role='instructor')
render_workspace(c, 'oulad:AAA:2013J', 'Overview')
''', default_timeout=20).run()
    assert not app.exception
    next(b for b in app.button if b.label == 'View High Attention').click().run()
    assert not app.exception
    assert next(s for s in app.selectbox if s.label == 'Show').value == 'High Attention'
    assert next(s for s in app.selectbox if s.label == 'Show').value == 'High Attention'
