import { useState } from "react";
import type { FormEvent } from "react";
import { legacyActive, legacyMutationSchema, legacyReviewSchema, legacyTransitions } from "../api/legacyContracts";
import type { LegacyCase, LegacyMutation } from "../api/legacyContracts";
import { legacyAlertDetailSchema, legacyLearnerDetailSchema } from "../api/legacyEvidenceContracts";
import type { LegacyAlertDetail } from "../api/legacyEvidenceContracts";
import { useResource } from "../hooks/useResource";
import { useLegacySave } from "../hooks/useLegacySave";
import { useDraftGuard } from "../hooks/editGuard";
import { label, Loading, Notice } from "../components/ui";

type MutationStatus = { pending: boolean; error: string; uncertain: boolean; conflict: boolean };
export function LegacySaveStatus({ mutation }: { mutation: MutationStatus }) {
  return <>
    {mutation.error && <Notice error>{mutation.error}</Notice>}
    {mutation.uncertain && <Notice>The save may already have reached the server. The draft is frozen. Retry the exact request below; its original request key prevents duplicate entries.</Notice>}
    {mutation.conflict && <Notice>The record changed or this action conflicts with its current state. Close this editor, refresh saved history, then review it before making another decision. No automatic overwrite was sent.</Notice>}
  </>;
}

function SaveButton({ mutation }: { mutation: MutationStatus }) {
  return <button className="primary" disabled={mutation.pending || mutation.conflict} type="submit">
    {mutation.pending ? "Saving…" : mutation.uncertain ? "Retry the same save" : "Save earlier support action"}
  </button>;
}

export function LegacyCreateCase({ course, learner, dataOrigin, alertId, csrf, saved }: {
  course: string; learner: string; dataOrigin: string; alertId?: string;
  csrf: string; saved: (result: LegacyMutation) => void;
}) {
  const [note, setNote] = useState("");
  const [attach, setAttach] = useState(false);
  const [validation, setValidation] = useState("");
  const detail = useResource(`v1/presentations/${encodeURIComponent(course)}/learners/${encodeURIComponent(learner)}`, legacyLearnerDetailSchema);
  const alert = useResource(alertId ? `v1/alerts/${encodeURIComponent(alertId)}` : null, legacyAlertDetailSchema);
  const matched = detail.data?.learner.presentation_id === course &&
    detail.data.learner.learner_id === learner && detail.data.learner.data_origin === dataOrigin;
  const alertMatched = alert.data?.alert.alert_id === alertId &&
    alert.data?.alert.presentation_id === course && alert.data?.alert.learner_id === learner &&
    alert.data?.alert.data_origin === dataOrigin;
  const mutation = useLegacySave(`v1/presentations/${encodeURIComponent(course)}/support-cases`, legacyMutationSchema, csrf);
  useDraftGuard(Boolean(note || attach) || mutation.uncertain, mutation.pending);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.uncertain) {
      const result = await mutation.retry();
      if (result) saved(result);
      return;
    }
    setValidation("");
    if (!matched || (attach && !alertMatched)) {
      setValidation("The learner or attached alert could not be verified for this course and data origin.");
      return;
    }
    const result = await mutation.save({ learner_id: learner,
      ...(note.trim() ? { note: note.trim() } : {}), ...(attach && alertId ? { alert_id: alertId } : {}),
    });
    if (result) saved(result);
  }
  return <form className="editor-form" onSubmit={submit}>
    <p>Student ID: {learner}. Open an earlier support episode. If one is already active, the server reuses it and records this action. Closed episodes stay unchanged.</p>
    <Notice>This saves to the earlier v1 support record only. It does not change a current course-operation case, model evidence or risk score, and sends no message.</Notice>
    {detail.error ? <Notice error>{detail.error}</Notice> : !detail.data ? <Loading /> : !matched ? <Notice error>The learner does not match this course and data origin.</Notice> : null}
    <fieldset disabled={!matched || mutation.pending || mutation.uncertain || mutation.conflict}>
      <label>Opening note (optional)<textarea aria-label="Earlier opening note" rows={4} maxLength={4000} value={note} onChange={(e) => setNote(e.target.value)} /></label>
      {alertId && <>
        {alert.error && <Notice error>{alert.error}</Notice>}
        {alert.data && !alertMatched && <Notice error>The alert does not match this learner, course and data origin.</Notice>}
        <label className="check-field"><input type="checkbox" disabled={!alertMatched} checked={attach} onChange={(e) => setAttach(e.target.checked)} />Attach alert {alertId} if it is not already attached to another episode</label>
      </>}
      <small>Authorized instructors can read notes. Record only necessary educational context.</small>
    </fieldset>
    {validation && <Notice error>{validation}</Notice>}
    <LegacySaveStatus mutation={mutation} />
    <button className="primary" disabled={mutation.pending || mutation.conflict || (!mutation.uncertain && !matched)} type="submit">{mutation.pending ? "Saving…" : mutation.uncertain ? "Retry the same save" : "Save earlier case"}</button>
  </form>;
}

export function LegacyCaseAction({ record, csrf, saved }: {
  record: LegacyCase; csrf: string; saved: (result: LegacyMutation) => void;
}) {
  // The parent supplies an immutable validated snapshot for this editor.
  const [action, setAction] = useState("add_note");
  const [note, setNote] = useState("");
  const [due, setDue] = useState("");
  const [alertInput, setAlertInput] = useState("");
  const [checkedId, setCheckedId] = useState("");
  const [validation, setValidation] = useState("");
  const mutation = useLegacySave(`v1/support-cases/${encodeURIComponent(record.case_id)}/actions`,
    legacyMutationSchema.refine((result) => result.case_id === record.case_id, "case_id"), csrf);
  const checked = useResource(checkedId && action === "link_alert" ? `v1/alerts/${encodeURIComponent(checkedId)}` : null, legacyAlertDetailSchema);
  const matches = checked.data && checked.data.alert.alert_id === checkedId &&
    checked.data.alert.presentation_id === record.presentation_id && checked.data.alert.learner_id === record.learner_id &&
    checked.data.alert.data_origin === record.data_origin && checkedId === alertInput.trim();
  useDraftGuard(Boolean(note || due || alertInput || action !== "add_note") || mutation.uncertain, mutation.pending);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.uncertain) {
      const result = await mutation.retry();
      if (result) saved(result);
      return;
    }
    setValidation("");
    if (!legacyActive.has(record.status)) { setValidation("Closed support episodes cannot be changed."); return; }
    const isTransition = legacyTransitions[record.status].includes(action);
    if (action === "add_note" && !note.trim()) { setValidation("Enter a note before saving."); return; }
    if (action === "link_alert" && !matches) { setValidation("Load an alert belonging to this student, course and data origin before linking it."); return; }
    const dueDate = new Date(`${due}Z`);
    if (action === "set_follow_up" && (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(due) || !Number.isFinite(dueDate.getTime()) || dueDate.toISOString().slice(0, 16) !== due)) {
      setValidation("Enter a valid follow-up date and time in UTC."); return;
    }
    const result = await mutation.save({ expected_version: record.version,
      action_type: isTransition ? "transition_status" : action,
      ...(isTransition ? { target_status: action } : {}),
      ...(note.trim() ? { note: note.trim() } : {}),
      ...(action === "set_follow_up" ? { follow_up_due_at: dueDate.toISOString() } : {}),
      ...(action === "link_alert" ? { alert_id: checkedId } : {}),
    });
    if (result) saved(result);
  }
  if (!legacyActive.has(record.status)) return <Notice>Closed episodes are terminal. Start a new episode for a later concern.</Notice>;
  return <form className="editor-form" onSubmit={submit}>
    <p>Student {record.learner_id} · {label(record.status)} · expected revision {record.version}. Earlier v1 case only.</p>
    <fieldset disabled={mutation.pending || mutation.uncertain || mutation.conflict}>
      <label>Earlier instructor action<select aria-label="Earlier instructor action" value={action} onChange={(e) => { setAction(e.target.value); setValidation(""); }}>
        <option value="add_note">Add note</option><option value="set_follow_up">Set follow-up</option>
        {record.follow_up_due_at && <option value="clear_follow_up">Clear follow-up</option>}
        <option value="link_alert">Attach existing alert</option>
        {legacyTransitions[record.status].map((status) => <option key={status} value={status}>Set status: {label(status)}</option>)}
      </select></label>
      <label>Instructor note{action === "add_note" ? " (required)" : " (optional)"}<textarea aria-label="Earlier instructor note" rows={4} maxLength={4000} value={note} onChange={(e) => setNote(e.target.value)} required={action === "add_note"} /></label>
      {action === "set_follow_up" && <label>Follow-up date and time — UTC<input aria-label="Earlier follow-up UTC" type="datetime-local" value={due} onChange={(e) => setDue(e.target.value)} required /><small>Entered values are interpreted as UTC, not this browser's local time.</small></label>}
      {action === "link_alert" && <>
        <label>Earlier alert ID<input aria-label="Earlier alert ID to attach" value={alertInput} maxLength={128} onChange={(e) => setAlertInput(e.target.value)} /></label>
        <button type="button" disabled={!alertInput.trim()} onClick={() => setCheckedId(alertInput.trim())}>Verify alert to attach</button>
        {checkedId && !checked.data && !checked.error && <Loading />}
        {checked.error && <Notice error>{checked.error}</Notice>}
        {checked.data && (matches ? <p>Verified for student {record.learner_id}, week {checked.data.alert.checkpoint_week}. State {checked.data.state_id}. Linking records a reference; it does not update the score. The server also verifies operational model scope and exclusive episode linkage.</p> : <Notice error>This alert does not match the selected student, course and data origin.</Notice>)}
      </>}
      {["resolved", "dismissed"].includes(action) && <Notice>This closes the episode permanently. Any later concern starts a new episode. A scheduled follow-up is retained in the audit record but closed cases are not due-work items.</Notice>}
      <small>No student communication is sent. Instructor notes do not become model evidence.</small>
    </fieldset>
    {validation && <Notice error>{validation}</Notice>}
    <LegacySaveStatus mutation={mutation} />
    <SaveButton mutation={mutation} />
  </form>;
}

const alertTransitions: Record<string, string[]> = {
  new: ["reviewed", "resolved", "dismissed"], reviewed: ["resolved", "dismissed"],
};
export function LegacyAlertReview({ detail, csrf, saved }: {
  detail: LegacyAlertDetail; csrf: string; saved: () => void;
}) {
  const transitions = alertTransitions[detail.alert.status] ?? [];
  const [decision, setDecision] = useState(transitions[0] ?? "");
  const [note, setNote] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [validation, setValidation] = useState("");
  const mutation = useLegacySave(`v1/alerts/${encodeURIComponent(detail.alert.alert_id)}/reviews`,
    legacyReviewSchema.refine((result) => result.alert_id === detail.alert.alert_id, "alert_id"), csrf, "header");
  useDraftGuard(Boolean(note || acknowledged || decision !== transitions[0]) || mutation.uncertain, mutation.pending);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mutation.uncertain) { if (await mutation.retry()) saved(); return; }
    if (!acknowledged || !transitions.includes(decision)) {
      setValidation("Choose an allowed decision and acknowledge the alert review concurrency limitation."); return;
    }
    setValidation("");
    if (await mutation.save({ new_status: decision, ...(note.trim() ? { note: note.trim() } : {}) })) saved();
  }
  if (!transitions.length) return <Notice>This alert is closed; no further alert review is available.</Notice>;
  return <form className="editor-form" onSubmit={submit}>
    <p>Alert {detail.alert.alert_id} · student {detail.alert.learner_id} · current displayed status {label(detail.alert.status)}.</p>
    <Notice>This is an alert review, not a support-case action. It does not change case status or model evidence. The v1 alert API has no expected-version check: a still-valid decision can be saved after another instructor's review. Refresh and inspect the review history before deciding.</Notice>
    <fieldset disabled={mutation.pending || mutation.uncertain || mutation.conflict}>
      <label>Earlier alert decision<select aria-label="Earlier alert decision" value={decision} onChange={(event) => setDecision(event.target.value)}>
        {transitions.map((value) => <option key={value} value={value}>{label(value)}</option>)}
      </select></label>
      <label>Alert review note (optional)<textarea aria-label="Earlier alert review note" maxLength={1000} rows={4} value={note} onChange={(event) => setNote(event.target.value)} /></label>
      <label className="check-field"><input type="checkbox" checked={acknowledged} onChange={(event) => setAcknowledged(event.target.checked)} />I understand this alert review has no version-conflict protection and have inspected the saved review history.</label>
      {["resolved", "dismissed"].includes(decision) && <Notice>This closes the alert permanently; it does not close any linked support episode.</Notice>}
    </fieldset>
    {validation && <Notice error>{validation}</Notice>}
    <LegacySaveStatus mutation={mutation} />
    <SaveButton mutation={mutation} />
  </form>;
}
