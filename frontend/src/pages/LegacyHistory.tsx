import { useEffect, useRef, useState } from "react";
import { legacyActive, legacyCaseDetailSchema, legacyIndexSchema } from "../api/legacyContracts";
import type { LegacyCase, LegacyMutation } from "../api/legacyContracts";
import type { LegacyAlertDetail } from "../api/legacyEvidenceContracts";
import { useResource } from "../hooks/useResource";
import { useLegacyCases } from "../hooks/useLegacyCases";
import { useEditGuard } from "../hooks/editGuard";
import { EditDialog } from "../components/EditDialog";
import { Badge, label, Loading, Notice, Panel } from "../components/ui";
import { LegacyAlertEvidence, LegacyAlerts, LegacyLearners } from "./LegacyLearners";
import { LegacyAlertReview, LegacyCaseAction, LegacyCreateCase } from "./LegacyCaseActions";

export function legacyDashboardPath(path: string) {
  const match = path.match(/^(\/user\/[^/]+\/)proxy\/8502\/$/);
  return match ? `${match[1]}proxy/8501/` : null;
}

export function LegacyHistory({ revision, csrf }: { revision: number; csrf: string }) {
  const guard = useEditGuard();
  const { data, error } = useResource("v1/presentations", legacyIndexSchema, revision);
  const [selected, setSelected] = useState("");
  const confirmedCourse = data?.items.find((item) => item.presentation_id === selected) ?? data?.items[0];
  const [previousCourse, setPreviousCourse] = useState<typeof confirmedCourse>();
  useEffect(() => {
    if (data) setPreviousCourse(confirmedCourse);
  }, [data, confirmedCourse]);
  // Keep local navigation mounted while revalidating grants, but hide it until
  // discovery succeeds. Empty/revoked courses and read failures unmount it.
  const course = data ? confirmedCourse : previousCourse;
  const legacyLink = legacyDashboardPath(window.location.pathname);
  return <>
    <Panel title="Earlier support workspace" note="Separate v1 learner records and support episodes — not current course-operation cases.">
      <Notice>Earlier case actions and alert reviews below save to the original v1 records. They do not copy episodes into current cases, generate predictions or turn instructor notes into model evidence. No student messages are sent.</Notice>
      {legacyLink && <p><a href={legacyLink} target="_blank" rel="noopener noreferrer" onClick={(event) => { if (!guard.leave()) event.preventDefault(); }}>Open the earlier Streamlit workspace ↗</a> · uses its own instructor sign-in. Its active Student support view provides case editing and linked evidence; not all timeline or alert-review controls are exposed there.</p>}
      <p className="fineprint">Student IDs are shown here. Instructor-authored notes may contain identifying information; use care when sharing your screen. Follow-up entry uses UTC explicitly.</p>
      {error ? <Notice error>{error}</Notice> : !data ? <Loading /> : !course ? <p>No earlier support courses are assigned to this account. Current course operations remain separate.</p> : <>
        <label>Earlier course<select aria-label="Earlier course" value={course.presentation_id} onChange={(event) => { if (guard.leave()) setSelected(event.target.value); }}>
          {data.items.map((item) => <option key={item.presentation_id} value={item.presentation_id}>{item.module_code} / {item.presentation_code} · {item.presentation_id}</option>)}
        </select></label>
        <Badge>{label(course.data_origin)} data</Badge>
      </>}
    </Panel>
    {!error && course && <div hidden={!data} style={{ overflowWrap: "anywhere" }}>
      <LegacyCourseWorkspace key={`${course.presentation_id}:${course.data_origin}`} course={course.presentation_id} dataOrigin={course.data_origin} revision={revision} csrf={csrf} />
    </div>}
  </>;
}

type CaseReference = Pick<LegacyCase, "case_id" | "presentation_id" | "learner_id" | "data_origin">;
type Editor =
  | { kind: "create"; learner: string; alertId?: string }
  | { kind: "case"; record: LegacyCase }
  | { kind: "review"; detail: LegacyAlertDetail };

function LegacyCourseWorkspace({ course, dataOrigin, revision, csrf }: {
  course: string; dataOrigin: string; revision: number; csrf: string;
}) {
  const guard = useEditGuard();
  const [localRevision, setLocalRevision] = useState(0);
  const [offset, setOffset] = useState(0);
  const [scope, setScope] = useState("all");
  const [dueOnly, setDueOnly] = useState(false);
  const [focus, setFocus] = useState<{ learner: string; alertId?: string } | null>(null);
  const [selected, setSelected] = useState<CaseReference | null>(null);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [message, setMessage] = useState("");
  const statusRef = useRef<HTMLDivElement>(null);
  const refresh = revision + localRevision;
  const cases = useLegacyCases({ course, dataOrigin, learner: focus?.learner ?? "", scope, dueOnly, offset, revision: refresh });
  useEffect(() => {
    if (cases.data && offset > 0 && offset >= cases.data.total) {
      setOffset(Math.max(0, Math.ceil(cases.data.total / 25) - 1) * 25);
      setSelected(null);
    }
  }, [cases.data, offset]);
  useEffect(() => {
    if (message) statusRef.current?.focus();
  }, [message]);
  function focusLearner(learner: string, alertId?: string) {
    if (!guard.leave()) return;
    setFocus({ learner, alertId }); setOffset(0); setScope("all"); setDueOnly(false); setSelected(null); setMessage("");
  }
  function openEditor(next: Editor) {
    if (guard.leave()) setEditor(next);
  }
  function saved(result?: LegacyMutation) {
    if (result && editor?.kind === "create") {
      setSelected({ case_id: result.case_id, presentation_id: course, learner_id: editor.learner, data_origin: dataOrigin });
    }
    setMessage(result ? `Saved earlier support action ${result.action_id}; episode revision ${result.resulting_version}.` : "Saved earlier alert review. Support-case status is unchanged.");
    setEditor(null); setLocalRevision((value) => value + 1);
  }
  function reviewAction(detail: LegacyAlertDetail) {
    if (!["new", "reviewed"].includes(detail.alert.status)) return <p>This alert is closed; its review history remains available.</p>;
    return <button onClick={() => openEditor({ kind: "review", detail })}>Review earlier alert</button>;
  }
  return <>
    {message && <div role="status" tabIndex={-1} ref={statusRef}><Notice>{message}</Notice></div>}
    <LegacyLearners course={course} dataOrigin={dataOrigin} revision={refresh} onOpenCase={focusLearner} renderAlertActions={reviewAction} />
    <LegacyAlerts course={course} dataOrigin={dataOrigin} revision={refresh} onOpenCase={focusLearner} renderAlertActions={reviewAction} />
    <Panel title="Earlier support episodes" note="All statuses are included by default. Resolved and dismissed episodes remain in the original audit history.">
      {focus ? <>
        <p>Episode history for student {focus.learner}. All matching server pages are loaded before this learner's history is filtered.</p>
        <button onClick={() => { if (guard.leave()) { setFocus(null); setOffset(0); setSelected(null); } }}>Show all earlier learners' episodes</button>
        <button className="primary" onClick={() => openEditor({ kind: "create", learner: focus.learner, alertId: focus.alertId })}>Open or reuse earlier support case</button>
      </> : <p>Select a learner above to review their complete episode history or open a case without an alert.</p>}
      <label>Case scope<select aria-label="Earlier case scope" value={scope} onChange={(event) => {
        if (!guard.leave()) return;
        setScope(event.target.value); setOffset(0); setSelected(null);
        if (event.target.value === "closed") setDueOnly(false);
      }}>
        <option value="all">All episodes</option><option value="active">Active episodes</option><option value="closed">Closed episodes</option>
      </select></label>
      <label className="check-field"><input type="checkbox" aria-label="Earlier follow-ups due only" checked={dueOnly} onChange={(event) => {
        if (!guard.leave()) return;
        setDueOnly(event.target.checked); setOffset(0); setSelected(null);
        if (event.target.checked) setScope("active");
      }} />Follow-ups due now (active episodes only, server UTC clock)</label>
      <button onClick={() => { if (guard.leave()) setLocalRevision((value) => value + 1); }}>Refresh earlier records</button>
      {cases.error ? <Notice error>{cases.error}</Notice> : !cases.data ? <Loading /> : <>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier support cases"><table>
          <thead><tr><th>Student ID</th><th>Status</th><th>Last action</th><th>Follow-up due</th><th>History</th></tr></thead>
          <tbody>{cases.data.items.map((record) => <tr key={record.case_id}>
            <td>{record.learner_id}</td><td>{label(record.status)}</td><td>{record.last_action_at}</td><td>{record.follow_up_due_at ?? "Not scheduled"}</td>
            <td><button aria-label={`Open earlier case ${record.case_id}`} onClick={() => { if (guard.leave()) setSelected(record); }}>Open history</button></td>
          </tr>)}</tbody>
        </table></div>
        {!cases.data.items.length && <p>No support episodes match this page or scope. Absence of a case is not evidence of low risk.</p>}
        <div className="pagination"><span>{cases.data.items.length ? offset + 1 : 0}–{cases.data.items.length ? offset + cases.data.items.length : 0} of {cases.data.total} episodes</span><div>
          <button disabled={!offset} onClick={() => { if (guard.leave()) { setOffset(Math.max(0, offset - 25)); setSelected(null); } }}>Previous episodes</button>
          <button disabled={offset + 25 >= cases.data.total} onClick={() => { if (guard.leave()) { setOffset(offset + 25); setSelected(null); } }}>Next episodes</button>
        </div></div>
      </>}
    </Panel>
    {selected && <LegacyCaseHistory key={selected.case_id} selected={selected} revision={refresh}
      edit={(record) => openEditor({ kind: "case", record })} focusLearner={focusLearner} reviewAction={reviewAction} />}
    {editor && <EditDialog title={editor.kind === "create" ? "Open earlier support case" : editor.kind === "case" ? "Earlier support action" : "Earlier alert review"} close={() => setEditor(null)}>
      {editor.kind === "create" ? <LegacyCreateCase course={course} learner={editor.learner} dataOrigin={dataOrigin} alertId={editor.alertId} csrf={csrf} saved={saved} />
        : editor.kind === "case" ? <LegacyCaseAction record={editor.record} csrf={csrf} saved={saved} />
          : <LegacyAlertReview detail={editor.detail} csrf={csrf} saved={() => saved()} />}
    </EditDialog>}
  </>;
}

function LegacyCaseHistory({ selected, revision, edit, focusLearner, reviewAction }: {
  selected: CaseReference; revision: number; edit: (record: LegacyCase) => void;
  focusLearner: (learner: string) => void; reviewAction: (detail: LegacyAlertDetail) => React.ReactNode;
}) {
  const guard = useEditGuard();
  const [selectedAlert, setSelectedAlert] = useState("");
  const { data, error } = useResource(`v1/support-cases/${encodeURIComponent(selected.case_id)}`, legacyCaseDetailSchema, revision);
  const matches = data && data.case.case_id === selected.case_id &&
    data.case.presentation_id === selected.presentation_id && data.case.learner_id === selected.learner_id &&
    data.case.data_origin === selected.data_origin &&
    data.actions.every((action) => action.case_id === selected.case_id);
  const alert = matches ? data.linked_alerts.find((item) => item.alert_id === selectedAlert) : undefined;
  return <>
    <Panel title="Earlier case audit history" note="Original timestamps, notes and revisions are retained; no current model score is inferred from these records.">
      {error ? <Notice error>{error}</Notice> : !data ? <Loading /> : !matches ? <Notice error>This case does not match the selected course, student or data origin.</Notice> : <>
        <p>Student {data.case.learner_id} · {label(data.case.status)} · revision {data.case.version} · episode {data.case.case_id}</p>
        <p>Opened {data.case.opened_at} · closed {data.case.closed_at ?? "Not closed"} · follow-up {data.case.follow_up_due_at ?? "Not scheduled"}</p>
        <button onClick={() => focusLearner(data.case.learner_id)}>Show this learner's episode history</button>
        {legacyActive.has(data.case.status) ? <button className="primary" onClick={() => edit(data.case)}>Manage earlier case</button> : <Notice>This episode is closed and cannot be changed. Select this learner's history to open a new episode for a later concern.</Notice>}
        {data.actions.length ? data.actions.map((action) => <article className="diagnostic-sample" key={action.action_id}>
          <h3>{label(action.action_type)} · revision {action.resulting_version}</h3>
          <p>{action.created_at} · {action.actor_id} ({action.actor_role}) · action {action.action_id}</p>
          {action.note && <p className="preserve-lines">{action.note}</p>}
          {(action.previous_status || action.new_status) && <p>Status: {label(action.previous_status)} → {label(action.new_status)}</p>}
          {(action.previous_follow_up_due_at || action.new_follow_up_due_at) && <p>Follow-up: {action.previous_follow_up_due_at ?? "Not scheduled"} → {action.new_follow_up_due_at ?? "Cleared"}</p>}
          {action.linked_alert_id && <p>Linked alert: {action.linked_alert_id}</p>}
        </article>) : <p>No action history was returned.</p>}
        <h3>Original linked alert references</h3>
        {data.linked_alerts.length ? data.linked_alerts.map((linked) => <article className="diagnostic-sample" key={linked.alert_id}>
          <p>Week {linked.checkpoint} · alert {linked.alert_id} · prediction {linked.prediction_id} · state {linked.state_id} · {linked.link_reason}. Linked {linked.linked_at}.</p>
          <button onClick={() => { if (guard.leave()) setSelectedAlert(linked.alert_id); }}>View linked alert {linked.alert_id}</button>
        </article>) : <p>No alerts are linked to this episode.</p>}
      </>}
    </Panel>
    {alert && <LegacyAlertEvidence key={alert.alert_id} course={selected.presentation_id} learner={selected.learner_id} alertId={alert.alert_id}
      stateId={alert.state_id} dataOrigin={selected.data_origin} revision={revision}>{reviewAction}</LegacyAlertEvidence>}
  </>;
}
