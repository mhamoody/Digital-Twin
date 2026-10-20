import { useState } from "react";
import type { FormEvent } from "react";
import { Plus, ExternalLink } from "lucide-react";
import { caseSchema } from "../api/contracts";
import type { CaseEvent, Fact, LearnerDetail } from "../api/contracts";
import { EditDialog } from "../components/EditDialog";
import { Badge, label, Notice, Panel } from "../components/ui";
import { useDraftGuard, useEditGuard } from "../hooks/editGuard";
import { useSave } from "../hooks/useSave";
import { observedDelta } from "./supportComparison";

type Props = {
  data: LearnerDetail;
  course: string;
  week: number;
  csrf: string;
  saved: () => void;
};
const actionNames: Record<CaseEvent["action"], string> = {
  note: "Note / manual concern",
  contact: "Student contact",
  warning: "Warning",
  support: "Learning support",
  resource: "Learning resource",
  follow_up: "Follow-up",
};
export function openPlans(data: LearnerDetail) {
  const events = data.current_case?.events ?? [];
  const resolved = new Set(
    events.map((e) => e.resolves_event_id).filter(Boolean),
  );
  return events.filter(
    (e) => e.action_state === "planned" && !resolved.has(e.id),
  );
}
export function SupportRecord(props: Props) {
  const { data, week } = props;
  const [editing, setEditing] = useState(false);
  const [planId, setPlanId] = useState("");
  const guard = useEditGuard();
  const record = data.current_case;
  const plans = openPlans(data);
  const today = data.current_course_day ?? week * 7 - 1;
  const resolved = new Set(
    record?.events.map((e) => e.resolves_event_id).filter(Boolean),
  );
  return (
    <>
      <Panel
        title="Current instructor support history"
        note="This record persists across checkpoints. Looking at a student does not mark the case reviewed."
        action={
          <button
            className="primary"
            onClick={() => {
              setPlanId("");
              setEditing(true);
            }}
          >
            <Plus size={16} />
            Record support action
          </button>
        }
      >
        <div className="support-summary">
          <Badge tone={record?.status === "ongoing" ? "amber" : "neutral"}>
            {record ? label(record.status) : "No case"}
          </Badge>
          <span>
            Next follow-up:{" "}
            {record?.follow_up_day == null
              ? "not scheduled"
              : `course day ${record.follow_up_day}`}
            {record?.follow_up_day != null &&
            ["new", "reviewed", "ongoing"].includes(record.status) &&
            record.follow_up_day <= today
              ? " · due"
              : ""}
          </span>
          <span>{plans.length} unfinished planned action(s)</span>
        </div>
        <p className="fineprint">
          Follow-up check: course day {today} ·{" "}
          {data.current_course_day == null
            ? "selected checkpoint; verify the calendar manually"
            : "current course calendar"}
          . Evidence shown: week {week}.
        </p>
        {plans.length > 0 && (
          <div className="planned-actions">
            <h3>Actions still planned</h3>
            {plans.map((plan) => (
              <div key={plan.id}>
                <span>
                  {actionNames[plan.action]} · course day {plan.occurred_day}
                </span>
                <button
                  onClick={() => {
                    setPlanId(plan.id);
                    setEditing(true);
                  }}
                >
                  Complete or cancel plan
                </button>
              </div>
            ))}
          </div>
        )}
        {!record?.events.length && (
          <div className="empty">
            <h3>No support actions recorded</h3>
            <p>You can open a manual concern even without a model alert.</p>
          </div>
        )}
        <div className="timeline">
          {record?.events
            .slice()
            .reverse()
            .map((event) => (
              <article key={event.id}>
                <span className="timeline-dot" />
                <small>
                  Course day {event.occurred_day} · evidence week{" "}
                  {event.evidence_checkpoint_week ?? event.checkpoint_week}
                </small>
                <h3>
                  {actionNames[event.action]}{" "}
                  <Badge
                    tone={
                      event.action_state === "completed"
                        ? "sage"
                        : event.action_state === "planned"
                          ? "amber"
                          : "neutral"
                    }
                  >
                    {label(event.action_state)}
                    {event.action_state === "planned" && resolved.has(event.id)
                      ? " · subsequently updated"
                      : ""}
                  </Badge>
                </h3>
                <p>{event.note || "No note recorded."}</p>
                <p className="fineprint">
                  Case after entry: {label(event.status)} · follow-up:{" "}
                  {event.follow_up_day == null
                    ? "not scheduled"
                    : `day ${event.follow_up_day}`}
                </p>
                {event.resolves_event_id && (
                  <small>
                    Updates planned entry <code>{event.resolves_event_id}</code>
                  </small>
                )}
                {event.resource_ids.length > 0 && (
                  <p className="fineprint">
                    Resources:{" "}
                    {event.resource_ids
                      .map((id) =>
                        String(
                          data.resources.find((r) => r.resource_id === id)
                            ?.title ?? id,
                        ),
                      )
                      .join(" · ")}
                  </p>
                )}
                <details>
                  <summary>Audit details</summary>
                  <p className="fineprint">
                    Recorded by {event.actor} · {event.recorded_at}
                  </p>
                  <code>{event.id}</code>
                </details>
              </article>
            ))}
        </div>
        <p className="fineprint">
          Planned is not completed. Reviewed is not resolved. Saving records an
          instructor action; it never sends a student message.
        </p>
      </Panel>
      <BeforeAfter data={data} week={week} />
      <Resources data={data} />
      {data.triage_history.length > 0 && (
        <Panel
          title="Instructor marker history"
          note="Flags, watchlists and priority are human judgments, not model evidence."
        >
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Instructor marker history"
          >
            <table>
              <thead>
                <tr>
                  <th>Revision</th>
                  <th>Markers</th>
                  <th>Note</th>
                  <th>Recorded by / at</th>
                </tr>
              </thead>
              <tbody>
                {data.triage_history.map((e, i) => (
                  <tr key={String(e.id ?? i)}>
                    <td>{String(e.version ?? "Unknown")}</td>
                    <td>
                      {[
                        e.flagged ? "Flagged" : null,
                        e.watchlisted ? "Watchlisted" : null,
                        `${label(String(e.priority ?? "normal"))} priority`,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </td>
                    <td>{String(e.note ?? "")}</td>
                    <td>
                      {String(e.actor ?? "Not recorded")}
                      <small>{String(e.recorded_at ?? "")}</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      )}
      {editing && (
        <EditDialog
          title="Record instructor support"
          close={() => setEditing(false)}
        >
          <label className="plan-selector">
            Entry
            <select
              aria-label="Entry"
              value={planId}
              onChange={(e) => {
                if (guard.leave()) setPlanId(e.target.value);
              }}
            >
              <option value="">New entry</option>
              {plans.map((p) => (
                <option key={p.id} value={p.id}>
                  Update planned {actionNames[p.action]} · day {p.occurred_day}
                </option>
              ))}
            </select>
          </label>
          <SupportForm
            key={planId}
            {...props}
            plan={plans.find((p) => p.id === planId)}
            saved={() => {
              setEditing(false);
              props.saved();
            }}
          />
        </EditDialog>
      )}
    </>
  );
}

function SupportForm({
  data,
  course,
  week,
  csrf,
  plan,
  saved,
}: Props & { plan?: CaseEvent }) {
  const record = data.current_case;
  const today = data.current_course_day;
  const defaultDay = Math.min(36500, Math.max(0, today ?? week * 7 - 1));
  const initial = {
    action: plan?.action ?? ("note" as CaseEvent["action"]),
    state: "completed" as CaseEvent["action_state"],
    status:
      record &&
      ["new", "reviewed", "ongoing", "resolved", "dismissed"].includes(
        record.status,
      )
        ? record.status
        : "ongoing",
    note: "",
    day: String(defaultDay),
    followMode: "keep",
    followDay: String(record?.follow_up_day ?? Math.min(36500, defaultDay + 7)),
    resources: plan?.resource_ids ?? ([] as string[]),
    acknowledgeClose: false,
  };
  const [form, setForm] = useState(initial);
  const [validation, setValidation] = useState("");
  const mutation = useSave(
    `v2/courses/${encodeURIComponent(course)}/learners/${encodeURIComponent(data.learner_id)}/case`,
    caseSchema,
    csrf,
  );
  useDraftGuard(
    JSON.stringify(initial) !== JSON.stringify(form) || mutation.uncertain,
    mutation.pending,
  );
  const closing = ["resolved", "dismissed"].includes(form.status);
  const otherPlans = openPlans(data).filter((p) => p.id !== plan?.id);
  const follow =
    form.followMode === "keep"
      ? (record?.follow_up_day ?? null)
      : form.followMode === "clear"
        ? null
        : Number(form.followDay);
  const needsAcknowledgement =
    closing && (otherPlans.length > 0 || follow !== null);
  const resources = data.resources.filter(
    (r) => typeof r.resource_id === "string",
  );
  async function submit(e: FormEvent) {
    e.preventDefault();
    setValidation("");
    const day = Number(form.day);
    const dayValid = (v: number) => Number.isInteger(v) && v >= 0 && v <= 36500;
    if (
      !form.day.trim() ||
      !dayValid(day) ||
      (follow !== null &&
        (!dayValid(follow) ||
          (form.followMode === "schedule" && !form.followDay.trim())))
    ) {
      setValidation("Enter a whole course day from 0 to 36500.");
      return;
    }
    if (!record && !form.note.trim()) {
      setValidation("Describe the concern before opening a case.");
      return;
    }
    if (form.state === "completed" && today != null && day > today) {
      setValidation(
        "A completed action cannot be in the future. Choose Planned for a future action.",
      );
      return;
    }
    if (follow !== null && follow < day) {
      setValidation(
        "The existing follow-up is before this action. Explicitly reschedule or clear it; it will not be silently moved.",
      );
      return;
    }
    if (needsAcknowledgement && !form.acknowledgeClose) {
      setValidation(
        "Confirm what closing means for outstanding plans or the scheduled follow-up.",
      );
      return;
    }
    if (
      form.resources.length > 20 ||
      form.resources.some((id) => {
        const resource = resources.find((r) => r.resource_id === id);
        return !resource || Number(resource.available_day ?? 0) > day;
      })
    ) {
      setValidation(
        "Select up to 20 approved resources available by the action day.",
      );
      return;
    }
    if (
      await mutation.save({
        status: form.status,
        expected_version: record?.version ?? 0,
        note: form.note.trim(),
        action: form.action,
        action_state: form.state,
        occurred_day: day,
        follow_up_day: follow,
        resource_ids: form.resources,
        checkpoint_week: week,
        expected_state_id: data.snapshot?.state_id ?? null,
        resolves_event_id: plan?.id ?? null,
      })
    )
      saved();
  }
  return (
    <form className="editor-form" onSubmit={submit}>
      <p>
        Evidence: week {week}, through day {week * 7 - 1}. Record the actual
        action day separately. No email, warning or resource is sent
        automatically.
      </p>
      {plan && (
        <Notice>
          Updating planned {actionNames[plan.action]}. The original entry
          remains in history; a completion or cancellation will be linked to it.
        </Notice>
      )}
      <fieldset
        disabled={mutation.pending || mutation.uncertain || mutation.conflict}
      >
        <div className="form-columns">
          <label>
            Action type
            <select
              aria-label="Action type"
              disabled={!!plan}
              value={form.action}
              onChange={(e) =>
                setForm({
                  ...form,
                  action: e.target.value as typeof form.action,
                })
              }
            >
              {Object.entries(actionNames).map(([value, name]) => (
                <option key={value} value={value}>
                  {name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Action state
            <select
              aria-label="Action state"
              value={form.state}
              onChange={(e) =>
                setForm({ ...form, state: e.target.value as typeof form.state })
              }
            >
              {(plan
                ? ["completed", "cancelled"]
                : ["completed", "planned", "cancelled"]
              ).map((v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label>
          Note and observed outcome
          <textarea
            aria-label="Note and observed outcome"
            rows={4}
            maxLength={2000}
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
            placeholder="Describe the concern, the action, and any observed outcome. Avoid unrelated personal details."
          />
        </label>
        <label>
          Case status after this entry
          <select
            aria-label="Case status after this entry"
            value={form.status}
            onChange={(e) =>
              setForm({
                ...form,
                status: e.target.value,
                acknowledgeClose: false,
              })
            }
          >
            {["new", "reviewed", "ongoing", "resolved", "dismissed"].map(
              (v) => (
                <option key={v} value={v}>
                  {label(v)}
                </option>
              ),
            )}
          </select>
        </label>
        <small>
          Reviewed = checked. Ongoing = continuing support. Resolved/dismissed =
          closed, with history retained. Closing a case does not complete a
          planned action.
        </small>
        <div className="form-columns">
          <label>
            Action date · course day
            <input
              aria-label="Action date · course day"
              type="number"
              min={0}
              max={36500}
              step={1}
              required
              value={form.day}
              onChange={(e) => setForm({ ...form, day: e.target.value })}
            />
          </label>
          <label>
            Follow-up handling
            <select
              aria-label="Follow-up handling"
              value={form.followMode}
              onChange={(e) =>
                setForm({
                  ...form,
                  followMode: e.target.value,
                  acknowledgeClose: false,
                })
              }
            >
              <option value="keep">
                {record?.follow_up_day == null
                  ? "Keep: none scheduled"
                  : `Keep existing day ${record.follow_up_day}`}
              </option>
              <option value="schedule">Schedule / reschedule explicitly</option>
              <option value="clear">Clear the scheduled follow-up</option>
            </select>
          </label>
        </div>
        {form.followMode === "schedule" && (
          <label>
            Follow-up due · course day
            <input
              aria-label="Follow-up due · course day"
              type="number"
              min={0}
              max={36500}
              step={1}
              required
              value={form.followDay}
              onChange={(e) => setForm({ ...form, followDay: e.target.value })}
            />
          </label>
        )}
        {today == null && (
          <Notice>
            No verified current course calendar. Confirm the action day
            yourself; the initial value is the evidence cutoff, not today's
            date.
          </Notice>
        )}
        {needsAcknowledgement && (
          <label className="check-field">
            <input
              type="checkbox"
              checked={form.acknowledgeClose}
              onChange={(e) =>
                setForm({ ...form, acknowledgeClose: e.target.checked })
              }
            />
            I understand this closes the case without completing its other
            planned actions or scheduled follow-up.
          </label>
        )}
        {form.resources.some(
          (id) => !resources.some((r) => r.resource_id === id),
        ) && (
          <Notice>
            Some resources on this plan are not available at this evidence
            checkpoint. Close the editor and select a later checkpoint to retain
            them, or explicitly remove them below. The original plan remains in
            history.
            {form.resources
              .filter((id) => !resources.some((r) => r.resource_id === id))
              .map((id) => (
                <div key={id}>
                  <code>{id}</code>{" "}
                  <button
                    type="button"
                    onClick={() =>
                      setForm({
                        ...form,
                        resources: form.resources.filter((r) => r !== id),
                      })
                    }
                  >
                    Remove unavailable resource
                  </button>
                </div>
              ))}
          </Notice>
        )}
        <details>
          <summary>
            Resources provided or planned · {form.resources.length} selected
          </summary>
          <p className="fineprint">
            Only approved resources visible at the evidence checkpoint are
            listed. A selection records your action; it does not send the
            resource.
          </p>
          <div className="resource-picker">
            {resources.map((r) => {
              const id = String(r.resource_id);
              return (
                <label key={id} className="check-field">
                  <input
                    type="checkbox"
                    checked={form.resources.includes(id)}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        resources: e.target.checked
                          ? [...form.resources, id]
                          : form.resources.filter((x) => x !== id),
                      })
                    }
                  />
                  {String(r.title ?? id)}
                </label>
              );
            })}
          </div>
          {!resources.length && (
            <p>No approved resources are available at this checkpoint.</p>
          )}
        </details>
      </fieldset>
      {validation && <Notice error>{validation}</Notice>}
      {mutation.error && <Notice error>{mutation.error}</Notice>}
      {mutation.uncertain && (
        <Notice>
          The server may have saved this entry. Retry the same request below to
          confirm it without duplication, or close and inspect history before
          creating another entry.
        </Notice>
      )}
      {mutation.conflict && (
        <Notice>
          The case or evidence changed. Close this editor and refresh the
          profile. Compare the latest history before drafting again.
        </Notice>
      )}
      <button
        className="primary"
        type="submit"
        disabled={mutation.pending || mutation.conflict}
      >
        {mutation.pending
          ? "Saving…"
          : mutation.uncertain
            ? "Retry the same save"
            : "Save support record"}
      </button>
    </form>
  );
}

function displayFact(fact?: Fact) {
  return !fact
    ? "Not available"
    : fact.value === null
      ? label(fact.status)
      : `${fact.value}${fact.unit === "percent" ? "%" : ""}`;
}
function BeforeAfter({ data, week }: { data: LearnerDetail; week: number }) {
  const actions = (data.current_case?.events ?? []).filter(
    (e) => e.action_state === "completed" && e.action !== "note",
  );
  const [selected, setSelected] = useState("");
  const action = actions.find((e) => e.id === selected) ?? actions.at(-1);
  if (!action) return null;
  const states = data.snapshot_history
    .slice()
    .sort((a, b) => a.checkpoint_week - b.checkpoint_week);
  const before = states
    .filter(
      (s) => (s.cutoff_day ?? s.checkpoint_week * 7 - 1) < action.occurred_day,
    )
    .at(-1);
  const after = states.find(
    (s) =>
      (s.cutoff_day ?? s.checkpoint_week * 7 - 1) > action.occurred_day &&
      s.checkpoint_week <= week,
  );
  return (
    <Panel
      title="Evidence after recorded support"
      note="Observed change is not proof that the intervention caused it."
    >
      <label>
        Completed action to compare
        <select
          aria-label="Completed action to compare"
          value={action.id}
          onChange={(e) => setSelected(e.target.value)}
        >
          {actions.map((e) => (
            <option key={e.id} value={e.id}>
              {actionNames[e.action]} · day {e.occurred_day}
            </option>
          ))}
        </select>
      </label>
      {!before || !after ? (
        <Notice>
          A checkpoint before the action and a later checkpoint are required.
          Return when that evidence is available.
        </Notice>
      ) : (
        <div
          className="table-scroll"
          role="region"
          aria-label="Before and after support evidence"
          tabIndex={0}
        >
          <table>
            <thead>
              <tr>
                <th>Evidence</th>
                <th>Before · week {before.checkpoint_week}</th>
                <th>First later · week {after.checkpoint_week}</th>
                <th>Observed change</th>
              </tr>
            </thead>
            <tbody>
              {[
                "weighted_grade_percent",
                "assessments_missed",
                "active_days_last_7",
                "completion_percent",
              ].map((key) => {
                const a = before.features[key],
                  b = after.features[key];
                const delta = observedDelta(before, after, key);
                return (
                  <tr key={key}>
                    <td>{label(key)}</td>
                    <td>{displayFact(a)}</td>
                    <td>{displayFact(b)}</td>
                    <td>
                      {delta === null
                        ? "Not comparable"
                        : `${delta > 0 ? "+" : ""}${delta.toFixed(1)} ${a?.unit === "percent" ? "percentage points" : (a?.unit ?? "")}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="fineprint">
        Higher grades/completion and fewer missed assessments can be favorable.
        More activity alone does not establish learning; changing task
        difficulty and other support can also affect results.
      </p>
    </Panel>
  );
}
function Resources({ data }: { data: LearnerDetail }) {
  function safeUrl(value: unknown) {
    try {
      const url = new URL(String(value));
      return ["https:", "http:"].includes(url.protocol) &&
        !url.username &&
        !url.password
        ? url.href
        : null;
    } catch {
      return null;
    }
  }
  return (
    <Panel
      title="Available learning resources"
      note="Approved course resources available by the evidence cutoff."
    >
      <details>
        <summary>Browse {data.resources.length} resources</summary>
        <div className="resource-library">
          {data.resources.map((r, i) => {
            const url = safeUrl(r.url);
            return (
              <article key={String(r.resource_id ?? i)}>
                <h3>{String(r.title ?? "Learning resource")}</h3>
                <small>{String(r.topic ?? "")}</small>
                {r.description != null && <p>{String(r.description)}</p>}
                {r.content != null && (
                  <details>
                    <summary>Read resource content</summary>
                    <p>{String(r.content)}</p>
                  </details>
                )}
                {url && (
                  <a href={url} target="_blank" rel="noopener noreferrer">
                    Open resource <ExternalLink size={13} />
                  </a>
                )}
              </article>
            );
          })}
        </div>
      </details>
    </Panel>
  );
}
