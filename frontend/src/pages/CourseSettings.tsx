import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { Settings2 } from "lucide-react";
import type { Workspace } from "../api/contracts";
import { ApiError, request } from "../api/client";
import {
  editablePolicySchema,
  learningModeLabels,
  parseBreakRanges,
  policyFieldLabels,
  policySaveSchema,
  policyValue,
  presetPolicy,
  teachingWeekdays,
} from "../api/policyContracts";
import type { EditablePolicy, LearningMode } from "../api/policyContracts";
import { EditDialog } from "../components/EditDialog";
import { Badge, Notice, Panel } from "../components/ui";
import { useDraftGuard } from "../hooks/editGuard";

type Props = {
  course: string;
  data: Workspace;
  csrf: string;
  saved: () => void;
};

export function CourseSettings({ course, data, csrf, saved }: Props) {
  const [editing, setEditing] = useState(false);
  const [flash, setFlash] = useState("");
  const parsed = editablePolicySchema.safeParse(data.policy);
  if (!parsed.success)
    return (
      <Notice error>
        The saved policy could not be validated. Refresh or contact the operator
        before editing course expectations.
      </Notice>
    );
  const policy = parsed.data;
  const schedule = [
    [
      "Course start",
      data.course.start_date ??
        data.course.course_start_date ??
        data.course.start_at,
    ],
    ["Course end", data.course.end_at],
    ["Time zone", data.course.timezone],
  ].filter((entry) => typeof entry[1] === "string") as [string, string][];
  return (
    <>
      {flash && (
        <div className="success-message" role="status">
          {flash}
        </div>
      )}
      <Panel
        title="What counts as concerning in this course?"
        note="Match expectations to how you teach. Quiet LMS days do not have to mean a student is at risk."
        action={
          <button
            onClick={() => {
              setFlash("");
              setEditing(true);
            }}
          >
            <Settings2 size={16} />
            Edit course expectations
          </button>
        }
      >
        <div className="support-summary">
          <Badge>Policy revision {policy.version}</Badge>
          <Badge tone={policy.inactivity_monitoring_enabled ? "" : "amber"}>
            {policy.inactivity_monitoring_enabled
              ? "Inactivity monitored"
              : "Inactivity monitoring off"}
          </Badge>
        </div>
        <dl className="settings-grid">
          {Object.entries(policyFieldLabels).map(([key, title]) => (
            <div key={key}>
              <dt>{title}</dt>
              <dd>{policyValue(policy, key as keyof EditablePolicy)}</dd>
            </div>
          ))}
        </dl>
        <p className="fineprint">
          {policy.inactivity_monitoring_enabled
            ? "Warning and escalation use eligible days since the last observed activity."
            : "The saved inactivity thresholds are retained but not used. Neither quiet days nor frequent logins are used as inactivity-based concern or protection."}{" "}
          {policy.day_basis === "teaching"
            ? "Only selected teaching weekdays count; scheduled breaks are excluded."
            : "Calendar days include weekends and breaks. Teaching weekdays and break ranges are retained, but only used when teaching-day counting is selected."}
        </p>
      </Panel>
      <Panel
        title="Changes are traceable"
        note="Course-wide expectations, not a change to one student's evidence."
      >
        <p>
          Saving creates a new policy revision with your instructor identity and
          a timestamp. Historical assessments keep the policy under which they
          were produced.
        </p>
        <p className="fineprint">
          Existing results need a new analysis before they count as current
          under the changed policy. Old-policy queued work is superseded. Use
          Data &amp; model health to inspect and queue the new assessment;
          saving settings does not itself run the model.
        </p>
        <Notice>
          Missing logs are not proof of inactivity. Academic evidence,
          data-quality checks and abstention rules remain active even when
          inactivity monitoring is disabled.
        </Notice>
      </Panel>
      <Panel
        title="Course calendar"
        note="Source metadata — changing expectations does not rewrite the course schedule."
      >
        {schedule.length ? (
          <dl className="settings-grid">
            {schedule.map(([name, value]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p>
            The source has not supplied a course calendar. Teaching-day
            interpretation requires a known course start date; an unknown value
            must not be invented.
          </p>
        )}
      </Panel>
      {editing && (
        <EditDialog
          title="Edit course expectations"
          close={() => setEditing(false)}
        >
          <PolicyEditor
            policy={policy}
            course={course}
            csrf={csrf}
            saved={() => {
              setEditing(false);
              setFlash(
                "Course expectations saved. Historical results are preserved; queue a new analysis to apply the new policy.",
              );
              saved();
            }}
            refresh={() => {
              setEditing(false);
              setFlash("");
              saved();
            }}
          />
        </EditDialog>
      )}
    </>
  );
}

export function toForm(policy: EditablePolicy) {
  return {
    ...policy,
    warning: String(policy.inactivity_warning_days),
    high: String(policy.inactivity_high_days),
    grade: String(policy.low_grade_percent),
    breaks: policy.break_ranges
      .map(([start, end]) => `${start}-${end}`)
      .join("\n"),
  };
}
type PolicyForm = ReturnType<typeof toForm>;
export function readForm(
  form: PolicyForm,
  original: EditablePolicy,
): EditablePolicy {
  if (
    ![form.warning, form.high, form.grade].every((value) => value.trim() !== "")
  )
    throw new Error(
      "Enter both inactivity thresholds and the low-grade reference. Empty values are not zero.",
    );
  const raw = {
    version: original.version,
    learning_mode: form.learning_mode,
    inactivity_monitoring_enabled: form.inactivity_monitoring_enabled,
    inactivity_warning_days: Number(form.warning),
    inactivity_high_days: Number(form.high),
    day_basis: form.day_basis,
    teaching_weekdays: [...form.teaching_weekdays].sort((a, b) => a - b),
    break_ranges: parseBreakRanges(form.breaks),
    require_academic_corroboration: form.require_academic_corroboration,
    low_grade_percent: Number(form.grade),
  };
  const checked = editablePolicySchema.safeParse(raw);
  if (!checked.success)
    throw new Error(
      checked.error.issues
        .map((issue) => {
          const field = issue.path[0] as keyof typeof policyFieldLabels;
          return `${policyFieldLabels[field] ?? "Policy"}: ${issue.message}`;
        })
        .join(" "),
    );
  const next = checked.data;
  const preset = presetPolicy(next.learning_mode, original);
  if (
    next.learning_mode !== "custom" &&
    (
      [
        "inactivity_monitoring_enabled",
        "inactivity_warning_days",
        "inactivity_high_days",
      ] as const
    ).some((field) => next[field] !== preset[field])
  )
    next.learning_mode = "custom";
  return next;
}

function PolicyEditor({
  policy,
  course,
  csrf,
  saved,
  refresh,
}: {
  policy: EditablePolicy;
  course: string;
  csrf: string;
  saved: () => void;
  refresh: () => void;
}) {
  const initial = toForm(policy);
  const [form, setForm] = useState(initial);
  const [preset, setPreset] = useState<LearningMode>(policy.learning_mode);
  const [confirmed, setConfirmed] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [halted, setHalted] = useState<"" | "conflict" | "uncertain">("");
  const lock = useRef(false);
  const dirty = JSON.stringify(initial) !== JSON.stringify(form);
  useDraftGuard(dirty || !!halted, pending);
  let next: EditablePolicy | null = null;
  let validation = "";
  try {
    next = readForm(form, policy);
  } catch (problem) {
    validation =
      problem instanceof Error ? problem.message : "Review the settings.";
  }
  const changes = next
    ? (
        Object.keys(policyFieldLabels) as (keyof typeof policyFieldLabels)[]
      ).filter(
        (key) => JSON.stringify(next![key]) !== JSON.stringify(policy[key]),
      )
    : [];
  const disabled = pending || !!halted;
  function change(updates: Partial<PolicyForm>) {
    setForm((old) => ({ ...old, ...updates }));
    setConfirmed(false);
    setError("");
  }
  function usePreset() {
    try {
      const current = readForm(form, policy);
      change(toForm(presetPolicy(preset, current)));
    } catch (problem) {
      setError(
        problem instanceof Error
          ? problem.message
          : "Correct the current settings before applying a preset.",
      );
    }
  }
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (lock.current || halted || !next || !changes.length || !confirmed)
      return;
    lock.current = true;
    setPending(true);
    setError("");
    try {
      await request(
        `v2/courses/${encodeURIComponent(course)}/policy`,
        policySaveSchema,
        { body: next, csrf },
      );
      saved();
    } catch (problem) {
      setError(
        problem instanceof Error
          ? problem.message
          : "The policy save could not be confirmed.",
      );
      if (problem instanceof ApiError && problem.status === 409)
        setHalted("conflict");
      else if (
        !(problem instanceof ApiError) ||
        problem.status === 0 ||
        problem.status >= 500
      )
        setHalted("uncertain");
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  function reload() {
    if (
      window.confirm(
        "Close this draft and load the server's saved policy? Check its revision and values before making another change.",
      )
    )
      refresh();
  }
  return (
    <form className="editor-form" onSubmit={submit}>
      <p>
        Editing revision {policy.version}. Presets fill the draft only; nothing
        changes until you confirm and save.
      </p>
      <fieldset disabled={disabled}>
        <legend>Teaching style</legend>
        <label>
          Teaching-style starting point
          <select
            aria-label="Teaching-style starting point"
            value={preset}
            onChange={(e) => setPreset(e.target.value as LearningMode)}
          >
            {Object.entries(learningModeLabels).map(([key, name]) => (
              <option key={key} value={key}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <button type="button" onClick={usePreset}>
          Use preset as starting point
        </button>
        <small>
          Regular online: 3/7 days; weekly: 7/14; fortnightly: 14/28.
          Milestone-based and mainly offline disable inactivity monitoring.
          These are editable examples, not validated cutoffs.
        </small>
        <label className="check-field">
          <input
            aria-label="Use inactivity in risk assessment"
            type="checkbox"
            checked={form.inactivity_monitoring_enabled}
            onChange={(e) =>
              change({ inactivity_monitoring_enabled: e.target.checked })
            }
          />
          Use inactivity in risk assessment
        </label>
        {!form.inactivity_monitoring_enabled && (
          <Notice>
            Inactivity is off. Thresholds remain saved for later, but quiet or
            frequent LMS activity is not used as concern or protection from
            inactivity.
          </Notice>
        )}
        <div className="form-columns">
          <label>
            Warning after eligible days
            <input
              aria-label="Warning after eligible days"
              type="number"
              required
              min={1}
              max={120}
              step={1}
              value={form.warning}
              onChange={(e) => change({ warning: e.target.value })}
            />
          </label>
          <label>
            Escalation after eligible days
            <input
              aria-label="Escalation after eligible days"
              type="number"
              required
              min={2}
              max={180}
              step={1}
              value={form.high}
              onChange={(e) => change({ high: e.target.value })}
            />
          </label>
        </div>
        <label>
          How days are counted
          <select
            aria-label="How days are counted"
            value={form.day_basis}
            onChange={(e) =>
              change({ day_basis: e.target.value as "calendar" | "teaching" })
            }
          >
            <option value="calendar">Calendar days</option>
            <option value="teaching">Teaching days only</option>
          </select>
        </label>
      </fieldset>
      <fieldset disabled={disabled}>
        <legend>Teaching calendar</legend>
        <p className="fineprint">
          {form.day_basis === "calendar"
            ? "Calendar counting includes weekends and breaks. These selections are retained but only affect teaching-day counting."
            : "Count only selected weekdays, excluding the break ranges below. Course day 0 is the course start."}
        </p>
        <fieldset>
          <legend>Teaching weekdays · select at least one</legend>
          <div className="policy-weekdays">
            {teachingWeekdays.map((day, index) => (
              <label className="check-field" key={day}>
                <input
                  aria-label={day}
                  type="checkbox"
                  checked={form.teaching_weekdays.includes(index)}
                  onChange={(e) =>
                    change({
                      teaching_weekdays: e.target.checked
                        ? [...form.teaching_weekdays, index].sort(
                            (a, b) => a - b,
                          )
                        : form.teaching_weekdays.filter((v) => v !== index),
                    })
                  }
                />
                {day}
              </label>
            ))}
          </div>
        </fieldset>
        <label>
          Scheduled breaks · inclusive course-day ranges
          <textarea
            aria-label="Scheduled breaks"
            rows={3}
            value={form.breaks}
            placeholder={"28-34\n56-62"}
            onChange={(e) => change({ breaks: e.target.value })}
          />
        </label>
        <small>
          One start-end range per line, within course days 0–420. For example,
          28-34 excludes all seven days when teaching-day counting is active.
        </small>
      </fieldset>
      <fieldset disabled={disabled}>
        <legend>Academic context</legend>
        <label className="check-field">
          <input
            aria-label="Require academic evidence to corroborate inactivity"
            type="checkbox"
            checked={form.require_academic_corroboration}
            onChange={(e) =>
              change({ require_academic_corroboration: e.target.checked })
            }
          />
          Require academic evidence to corroborate inactivity
        </label>
        <label>
          Low-grade reference · percent
          <input
            aria-label="Low-grade reference percent"
            type="number"
            min={0}
            max={100}
            step="any"
            required
            value={form.grade}
            onChange={(e) => change({ grade: e.target.value })}
          />
        </label>
        <small>
          This is a concern reference, not a grade change or a new course pass
          mark. Missing evidence remains unknown.
        </small>
      </fieldset>
      {dirty && validation && <Notice error>{validation}</Notice>}
      {next && changes.length > 0 && (
        <section aria-label="Review policy changes">
          <h3>Review changes</h3>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Policy changes table"
          >
            <table>
              <thead>
                <tr>
                  <th>Setting</th>
                  <th>Saved</th>
                  <th>New revision</th>
                </tr>
              </thead>
              <tbody>
                {changes.map((key) => (
                  <tr key={key}>
                    <th scope="row">{policyFieldLabels[key]}</th>
                    <td>{policyValue(policy, key)}</td>
                    <td>{policyValue(next!, key)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="fineprint">
            If preset thresholds were customized, the teaching-style label
            becomes Custom expectations. The saved numbers are authoritative.
          </p>
        </section>
      )}
      <fieldset disabled={disabled}>
        <label className="check-field">
          <input
            aria-label="Confirm course-wide policy change"
            type="checkbox"
            checked={confirmed}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I understand this applies course-wide, keeps historical results, and
          requires a new analysis for current assessments.
        </label>
      </fieldset>
      {error && <Notice error>{error}</Notice>}
      {halted && (
        <>
          <Notice>
            {halted === "conflict"
              ? "Another instructor saved a newer policy. Your draft was not applied over it."
              : "The server may already have saved this revision. This endpoint does not provide an idempotent retry, so no second save will be sent from this draft."}{" "}
            Load saved settings and check the revision before editing again.
          </Notice>
          <button type="button" onClick={reload}>
            Check saved settings
          </button>
        </>
      )}
      <button
        type="submit"
        className="primary"
        disabled={disabled || !next || !changes.length || !confirmed}
      >
        {pending
          ? "Saving policy…"
          : `Save policy revision ${policy.version + 1}`}
      </button>
    </form>
  );
}
