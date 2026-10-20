import { useState } from "react";
import type { FormEvent } from "react";
import { Bookmark, Flag, Settings2 } from "lucide-react";
import type { LearnerDetail } from "../api/contracts";
import { triageResponseSchema } from "../api/contracts";
import { EditDialog } from "../components/EditDialog";
import { Badge, label, Notice } from "../components/ui";
import { useDraftGuard } from "../hooks/editGuard";
import { useSave } from "../hooks/useSave";

export function InstructorActions({
  data,
  course,
  csrf,
  saved,
}: {
  data: LearnerDetail;
  course: string;
  csrf: string;
  saved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  return (
    <section className="instructor-actions" aria-label="Instructor markers">
      <div>
        <Badge tone={data.triage.flagged ? "amber" : ""}>
          <Flag size={13} />
          {data.triage.flagged ? "Flagged" : "No manual flag"}
        </Badge>
        <Badge>
          <Bookmark size={13} />
          {data.triage.watchlisted ? "On watchlist" : "Not on watchlist"}
        </Badge>
        <Badge>{label(data.triage.priority)} priority</Badge>
      </div>
      <button onClick={() => setEditing(true)}>
        <Settings2 size={16} />
        Edit instructor markers
      </button>
      <small>
        Human judgment, separate from the risk score and support record.
      </small>
      {editing && (
        <EditDialog title="Instructor markers" close={() => setEditing(false)}>
          <TriageForm
            data={data}
            course={course}
            csrf={csrf}
            saved={() => {
              setEditing(false);
              saved();
            }}
          />
        </EditDialog>
      )}
    </section>
  );
}

function TriageForm({
  data,
  course,
  csrf,
  saved,
}: {
  data: LearnerDetail;
  course: string;
  csrf: string;
  saved: () => void;
}) {
  const initial = {
    flagged: data.triage.flagged,
    watchlisted: data.triage.watchlisted,
    priority: data.triage.priority,
    note: data.triage.note ?? "",
  };
  const [form, setForm] = useState(initial);
  const mutation = useSave(
    `v2/courses/${encodeURIComponent(course)}/learners/${encodeURIComponent(data.learner_id)}/triage`,
    triageResponseSchema,
    csrf,
  );
  const dirty = JSON.stringify(initial) !== JSON.stringify(form);
  useDraftGuard(dirty || mutation.uncertain, mutation.pending);
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (await mutation.save({ expected_version: data.triage.version, ...form }))
      saved();
  }
  return (
    <form className="editor-form" onSubmit={submit}>
      <p>
        Saving these markers does not change model evidence, the risk score or
        case status.
      </p>
      <fieldset
        disabled={mutation.pending || mutation.uncertain || mutation.conflict}
      >
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.flagged}
            onChange={(e) => setForm({ ...form, flagged: e.target.checked })}
          />
          Flag for instructor review
        </label>
        <label className="check-field">
          <input
            type="checkbox"
            checked={form.watchlisted}
            onChange={(e) =>
              setForm({ ...form, watchlisted: e.target.checked })
            }
          />
          Keep on the course watchlist
        </label>
        <label>
          Instructor priority
          <select
            aria-label="Instructor priority"
            value={form.priority}
            onChange={(e) =>
              setForm({
                ...form,
                priority: e.target.value as typeof form.priority,
              })
            }
          >
            {["low", "normal", "high", "urgent"].map((v) => (
              <option key={v} value={v}>
                {label(v)}
              </option>
            ))}
          </select>
        </label>
        <label>
          Instructor note
          <textarea
            aria-label="Instructor note"
            rows={4}
            maxLength={2000}
            value={form.note}
            onChange={(e) => setForm({ ...form, note: e.target.value })}
          />
        </label>
        <small>
          Shared with authorized course instructors. Avoid unrelated personal
          information.
        </small>
      </fieldset>
      {mutation.error && <Notice error>{mutation.error}</Notice>}
      {mutation.uncertain && (
        <Notice>
          The save may already have reached the server. Retry the exact request
          below; its request key prevents duplicate entries.
        </Notice>
      )}
      {mutation.conflict && (
        <Notice>
          Close this editor and refresh the profile to inspect the latest
          version before editing again. Your changes were not overwritten onto
          another instructor's update.
        </Notice>
      )}
      <button
        className="primary"
        type="submit"
        disabled={
          mutation.pending ||
          mutation.conflict ||
          (!dirty && !mutation.uncertain)
        }
      >
        {mutation.pending
          ? "Saving…"
          : mutation.uncertain
            ? "Retry the same save"
            : "Save instructor markers"}
      </button>
    </form>
  );
}
