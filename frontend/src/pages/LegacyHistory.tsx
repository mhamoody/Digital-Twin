import { useEffect, useState } from "react";
import { z } from "zod";
import { useResource } from "../hooks/useResource";
import { Badge, label, Loading, Notice, Panel } from "../components/ui";

const indexSchema = z.object({
  items: z.array(
    z.object({
      presentation_id: z.string(),
      module_code: z.string(),
      presentation_code: z.string(),
      data_origin: z.string(),
    }),
  ),
});
const caseSchema = z.object({
  case_id: z.string(),
  presentation_id: z.string(),
  learner_id: z.string(),
  data_origin: z.string(),
  status: z.string(),
  opened_at: z.string(),
  last_action_at: z.string(),
  follow_up_due_at: z.string().nullable(),
  closed_at: z.string().nullable(),
  version: z.number().int(),
});
const casesSchema = z.object({
  items: z.array(caseSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});
const detailSchema = z.object({
  case: caseSchema,
  actions: z.array(
    z.object({
      action_id: z.string(),
      action_type: z.string(),
      actor_id: z.string(),
      actor_role: z.string(),
      created_at: z.string(),
      resulting_version: z.number().int(),
      note: z.string().nullable(),
      previous_status: z.string().nullable(),
      new_status: z.string().nullable(),
      previous_follow_up_due_at: z.string().nullable(),
      new_follow_up_due_at: z.string().nullable(),
      linked_alert_id: z.string().nullable(),
    }),
  ),
  linked_alerts: z.array(
    z.object({
      alert_id: z.string(),
      prediction_id: z.string(),
      state_id: z.string(),
      checkpoint: z.number().int(),
      risk_band: z.string().nullable(),
      linked_at: z.string(),
      link_reason: z.string(),
    }),
  ),
});

export function legacyDashboardPath(path: string) {
  const match = path.match(/^(\/user\/[^/]+\/)proxy\/8502\/$/);
  return match ? `${match[1]}proxy/8501/` : null;
}

export function LegacyHistory({ revision }: { revision: number }) {
  const { data, error } = useResource(
    "v1/presentations",
    indexSchema,
    revision,
  );
  const [selected, setSelected] = useState("");
  const course =
    data?.items.find((c) => c.presentation_id === selected) ?? data?.items[0];
  const legacyLink = legacyDashboardPath(window.location.pathname);
  return (
    <>
      <Panel
        title="Earlier support history"
        note="Separate v1 support episodes — not the current course-operation cases."
      >
        <Notice>
          These records have not been merged into current support cases or used
          as new model evidence. This view is read-only. Older case editing,
          alerts and learner activity remain available in Streamlit: select
          Student support in its Workspace selector.
        </Notice>
        {legacyLink && (
          <p>
            <a href={legacyLink} target="_blank" rel="noopener noreferrer">
              Open the earlier support workspace ↗
            </a>{" "}
            · uses its own instructor sign-in
          </p>
        )}
        <p className="fineprint">
          Student IDs are shown here. Instructor-authored notes can contain
          identifying information; use care when sharing your screen.
        </p>
        {error ? (
          <Notice error>{error}</Notice>
        ) : !data ? (
          <Loading />
        ) : !course ? (
          <p>
            No earlier support courses are assigned to this account. Current
            course operations remain separate.
          </p>
        ) : (
          <>
            <label>
              Earlier course
              <select
                aria-label="Earlier course"
                value={course.presentation_id}
                onChange={(e) => setSelected(e.target.value)}
              >
                {data.items.map((c) => (
                  <option key={c.presentation_id} value={c.presentation_id}>
                    {c.module_code} / {c.presentation_code} ·{" "}
                    {c.presentation_id}
                  </option>
                ))}
              </select>
            </label>
            <Badge>{label(course.data_origin)} data</Badge>
          </>
        )}
      </Panel>
      {!error && course && (
        <LegacyCases
          key={course.presentation_id}
          course={course.presentation_id}
          revision={revision}
        />
      )}
    </>
  );
}

function LegacyCases({
  course,
  revision,
}: {
  course: string;
  revision: number;
}) {
  const [offset, setOffset] = useState(0);
  const [scope, setScope] = useState("all");
  const [selected, setSelected] = useState<string | null>(null);
  const params = new URLSearchParams({ limit: "25", offset: String(offset) });
  if (scope !== "all") params.set("active", String(scope === "active"));
  const { data, error } = useResource(
    `v1/presentations/${encodeURIComponent(course)}/support-cases?${params}`,
    casesSchema,
    revision,
  );
  const lastOffset = data
    ? Math.max(0, Math.floor((data.total - 1) / 25) * 25)
    : offset;
  useEffect(() => {
    if (offset > lastOffset) setOffset(lastOffset);
  }, [offset, lastOffset]);
  return (
    <>
      <Panel
        title="Earlier support episodes"
        note="All statuses are included by default, including resolved and dismissed cases."
      >
        <label>
          Case scope
          <select
            aria-label="Earlier case scope"
            value={scope}
            onChange={(e) => {
              setScope(e.target.value);
              setOffset(0);
              setSelected(null);
            }}
          >
            <option value="all">All episodes</option>
            <option value="active">Active episodes</option>
            <option value="closed">Closed episodes</option>
          </select>
        </label>
        {error ? (
          <Notice error>{error}</Notice>
        ) : !data || offset > lastOffset ? (
          <Loading />
        ) : data.items.some((c) => c.presentation_id !== course) ? (
          <Notice error>
            The earlier-case response does not match the selected course.
          </Notice>
        ) : (
          <>
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Earlier support cases"
            >
              <table>
                <thead>
                  <tr>
                    <th>Student ID</th>
                    <th>Status</th>
                    <th>Last action</th>
                    <th>Follow-up due</th>
                    <th>History</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((c) => (
                    <tr key={c.case_id}>
                      <td>{c.learner_id}</td>
                      <td>{label(c.status)}</td>
                      <td>{c.last_action_at}</td>
                      <td>{c.follow_up_due_at ?? "Not scheduled"}</td>
                      <td>
                        <button
                          onClick={() => setSelected(c.case_id)}
                          aria-label={`Open earlier case ${c.case_id}`}
                        >
                          Open history
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data.total && (
              <p>
                No support episodes match this scope. Absence of a case is not
                evidence of low risk.
              </p>
            )}
            <div className="pagination">
              <span>
                {data.total ? offset + 1 : 0}–
                {Math.min(offset + 25, data.total)} of {data.total} episodes
              </span>
              <div>
                <button
                  disabled={!offset}
                  onClick={() => {
                    setOffset(Math.max(0, offset - 25));
                    setSelected(null);
                  }}
                >
                  Previous episodes
                </button>
                <button
                  disabled={offset + 25 >= data.total}
                  onClick={() => {
                    setOffset(offset + 25);
                    setSelected(null);
                  }}
                >
                  Next episodes
                </button>
              </div>
            </div>
          </>
        )}
      </Panel>
      {selected && (
        <LegacyCase
          key={selected}
          course={course}
          id={selected}
          revision={revision}
        />
      )}
    </>
  );
}
function LegacyCase({
  course,
  id,
  revision,
}: {
  course: string;
  id: string;
  revision: number;
}) {
  const { data, error } = useResource(
    `v1/support-cases/${encodeURIComponent(id)}`,
    detailSchema,
    revision,
  );
  return (
    <Panel
      title="Earlier case audit history"
      note="Original timestamps, notes and revisions are retained; no current model score is inferred from these records."
    >
      {error ? (
        <Notice error>{error}</Notice>
      ) : !data ? (
        <Loading />
      ) : data.case.case_id !== id || data.case.presentation_id !== course ? (
        <Notice error>This case does not match the selected course.</Notice>
      ) : (
        <>
          <p>
            Student {data.case.learner_id} · {label(data.case.status)} ·
            revision {data.case.version}
          </p>
          <p>
            Opened {data.case.opened_at} · closed{" "}
            {data.case.closed_at ?? "Not closed"}
          </p>
          {data.actions.length ? (
            data.actions.map((a) => (
              <article className="diagnostic-sample" key={a.action_id}>
                <h3>
                  {label(a.action_type)} · revision {a.resulting_version}
                </h3>
                <p>
                  {a.created_at} · {a.actor_id} ({a.actor_role})
                </p>
                {a.note && <p className="preserve-lines">{a.note}</p>}
                {(a.previous_status || a.new_status) && (
                  <p>
                    Status: {label(a.previous_status)} → {label(a.new_status)}
                  </p>
                )}
                {(a.previous_follow_up_due_at || a.new_follow_up_due_at) && (
                  <p>
                    Follow-up: {a.previous_follow_up_due_at ?? "Not scheduled"}{" "}
                    → {a.new_follow_up_due_at ?? "Cleared"}
                  </p>
                )}
                {a.linked_alert_id && <p>Linked alert: {a.linked_alert_id}</p>}
              </article>
            ))
          ) : (
            <p>No action history was returned.</p>
          )}
          <details>
            <summary>Original linked alert references</summary>
            {data.linked_alerts.map((a) => (
              <p key={a.alert_id}>
                Week {a.checkpoint} · alert {a.alert_id} · prediction{" "}
                {a.prediction_id} · state {a.state_id} · {a.link_reason}. Linked{" "}
                {a.linked_at}.
              </p>
            ))}
          </details>
        </>
      )}
    </Panel>
  );
}
