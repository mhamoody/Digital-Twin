import { useState } from "react";
import { ArrowLeft, ShieldCheck, FileText } from "lucide-react";
import { detailSchema } from "../api/contracts";
import type { Fact, LearnerDetail, Privacy } from "../api/contracts";
import { useResource } from "../hooks/useResource";
import {
  Badge,
  band,
  label,
  Loading,
  Notice,
  Panel,
  score,
} from "../components/ui";

export function StudentProfile({
  course,
  id,
  week,
  privacy,
  revision,
  back,
}: {
  course: string;
  id: string;
  week: number;
  privacy: Privacy;
  revision: number;
  back: () => void;
}) {
  const [tab, setTab] = useState("Evidence");
  const path = `v2/courses/${encodeURIComponent(course)}/learners/${encodeURIComponent(id)}?week=${week}&privacy=${privacy}`;
  const { data, error } = useResource(path, detailSchema, revision);
  if (error)
    return (
      <>
        <button onClick={back}>
          <ArrowLeft size={16} /> Back to list
        </button>
        <Notice error>{error}</Notice>
      </>
    );
  if (!data) return <Loading />;
  const usable =
    data.analysis_status === "validated" &&
    data.snapshot?.is_fresh === true &&
    data.analysis?.policy_version === data.current_policy_version;
  const output = usable ? data.analysis?.output : null;
  const tabs = [
    "Evidence",
    "Academic records",
    "Risk history",
    "Support record",
  ];
  return (
    <>
      <button className="text-button back-button" onClick={back}>
        <ArrowLeft size={17} /> Back to list
      </button>
      <div className="profile-heading">
        <span className="avatar large">{data.display_name.slice(0, 1)}</span>
        <div>
          <h1>{data.display_name}</h1>
          <p>
            {id} · week {week} · cutoff day {week * 7 - 1}
          </p>
        </div>
        <Badge
          tone={
            output?.risk_band === "high"
              ? "coral"
              : output?.risk_band === "medium"
                ? "amber"
                : output?.risk_band === "low"
                  ? "sage"
                  : "neutral"
          }
        >
          {band(output?.risk_band ?? null)}
        </Badge>
      </div>
      <div className="profile-metrics">
        <div>
          <small>Risk score</small>
          <strong>{score(output?.risk_score)}</strong>
          <span>Uncalibrated; not a probability</span>
        </div>
        <div>
          <small>Previous → current</small>
          <strong>
            {usable &&
            data.comparable &&
            data.previous_analysis?.output.risk_score != null &&
            output?.risk_score != null
              ? `${(data.previous_analysis.output.risk_score * 100).toFixed(0)} → ${(output.risk_score * 100).toFixed(0)}`
              : "No valid comparison"}
          </strong>
          <span>Same model and policy required</span>
        </div>
        <div>
          <small>Analysis</small>
          <strong>{label(data.analysis_status)}</strong>
          <span>{data.analysis?.model_version ?? "No saved model result"}</span>
        </div>
        <div>
          <small>Current support case</small>
          <strong>
            {data.current_case ? label(data.current_case.status) : "No case"}
          </strong>
          <span>Retained across checkpoints</span>
        </div>
      </div>
      <div className="profile-markers">
        <Badge>
          {data.triage.flagged ? "Flagged by instructor" : "No manual flag"}
        </Badge>
        <Badge>
          {data.triage.watchlisted ? "On watchlist" : "Not on watchlist"}
        </Badge>
        <Badge>{label(data.triage.priority)} priority</Badge>
        <small>Instructor markers do not change the risk score.</small>
      </div>
      {(!usable || data.analysis?.output.abstain) && (
        <Notice>
          {data.analysis?.output.abstain
            ? `Assessment withheld: ${data.analysis.output.abstention_reason}`
            : `No current validated assessment. Status: ${label(data.analysis_status)}.`}{" "}
          {data.job_error && (
            <span>
              Diagnostic code: <code>{data.job_error}</code>.
            </span>
          )}{" "}
          Saved evidence remains available below.
        </Notice>
      )}
      <nav className="profile-tabs" aria-label="Student sections">
        {tabs.map((name) => (
          <button
            key={name}
            aria-current={tab === name ? "page" : undefined}
            className={tab === name ? "selected" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>
      {tab === "Evidence" && <Evidence data={data} usable={usable} />}
      {tab === "Academic records" && <Academic data={data} />}
      {tab === "Risk history" && (
        <Panel
          title="Saved risk-score history"
          note="Historical results. Different model or policy revisions must not be treated as a continuous comparable trend."
        >
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Risk history"
          >
            <table>
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Risk score</th>
                  <th>Support level</th>
                  <th>Model</th>
                  <th>Policy</th>
                </tr>
              </thead>
              <tbody>
                {data.history.map((h) => (
                  <tr key={h.checkpoint_week}>
                    <td>{h.checkpoint_week}</td>
                    <td>{score(h.risk_score)}</td>
                    <td>{band(h.risk_band)}</td>
                    <td>{h.model_version}</td>
                    <td>Revision {h.policy_version}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!data.history.length && (
            <p className="empty">
              No saved model results. Missing points are not zero.
            </p>
          )}
        </Panel>
      )}
      {tab === "Support record" && (
        <Panel
          title="Current instructor support history"
          note="Recorded actions persist even when you open an earlier evidence checkpoint. This foundation view is read-only; editing remains in Streamlit."
        >
          <div className="timeline">
            {data.current_case?.events.map((event, i) => (
              <article key={String(event.id ?? i)}>
                <span className="timeline-dot" />
                <small>
                  Course day {String(event.occurred_day ?? "unknown")} ·
                  evidence week{" "}
                  {String(
                    event.evidence_checkpoint_week ??
                      event.checkpoint_week ??
                      "unknown",
                  )}
                </small>
                <h3>
                  {label(String(event.action ?? "note"))}{" "}
                  <Badge>
                    {label(String(event.action_state ?? "unknown"))}
                  </Badge>
                </h3>
                <p>{String(event.note ?? "No note recorded")}</p>
                <p className="fineprint">
                  Case: {label(String(event.status ?? "unknown"))} · next
                  follow-up:{" "}
                  {event.follow_up_day == null
                    ? "not scheduled"
                    : `day ${event.follow_up_day}`}
                </p>
                {Array.isArray(event.resource_ids) &&
                  event.resource_ids.length > 0 && (
                    <p className="fineprint">
                      Resources: {event.resource_ids.join(", ")}
                    </p>
                  )}
              </article>
            ))}
          </div>
          {!data.current_case?.events.length && (
            <p className="empty">
              No instructor actions recorded for this student.
            </p>
          )}
          <Notice>
            Planned actions are not completed contact. No messages are sent by
            this interface. Action editing and before/after comparisons are
            scheduled for the next migration phase.
          </Notice>
        </Panel>
      )}
    </>
  );
}

function value(fact: Fact) {
  return fact.value === null
    ? label(fact.status)
    : `${fact.value}${fact.unit === "percent" ? "%" : ""}`;
}
function Evidence({ data, usable }: { data: LearnerDetail; usable: boolean }) {
  const facts = Object.entries(data.snapshot?.features ?? {});
  const output = data.analysis?.output;
  return (
    <>
      <div className="two-columns evidence-columns">
        <Panel
          title={
            usable ? "Reasons & evidence" : "Last saved reasons · historical"
          }
          note={
            usable
              ? "Validated claims linked to checkpoint evidence"
              : "Not a current assessment. Do not use these claims as a current risk judgment."
          }
        >
          {output?.claims.map((claim, i) => (
            <article className="claim" key={`${claim.code}-${i}`}>
              <h3>
                <ShieldCheck size={18} />
                {label(claim.code)}
              </h3>
              {claim.evidence_ids.map((evidenceId) => {
                const found = facts.find(
                  ([, f]) => f.evidence_id === evidenceId,
                );
                return (
                  <div key={evidenceId}>
                    {found ? (
                      <>
                        <p>
                          {label(found[0])}: <strong>{value(found[1])}</strong>
                        </p>
                        <small>
                          {found[1].window} · {label(found[1].status)}
                        </small>
                        <details>
                          <summary>Source references</summary>
                          <code>{evidenceId}</code>
                          <ul>
                            {found[1].source_ids.map((source) => (
                              <li key={source}>
                                <code>{source}</code>
                              </li>
                            ))}
                          </ul>
                          {!found[1].source_ids.length && (
                            <small>No direct source IDs in this fact.</small>
                          )}
                        </details>
                      </>
                    ) : (
                      <Notice>
                        Supporting evidence unavailable; this claim needs
                        review.
                      </Notice>
                    )}
                  </div>
                );
              })}
            </article>
          ))}
          {!output?.claims.length && (
            <p className="empty">
              No grounded claim was published. Inspect evidence availability
              below.
            </p>
          )}
          {usable && !!output?.suggested_actions.length && (
            <div className="suggestions">
              <h3>Suggested next steps</h3>
              <ul>
                {output.suggested_actions.map((action) => (
                  <li key={action}>{label(action)}</li>
                ))}
              </ul>
              <small>Suggestions only, not actions already performed.</small>
            </div>
          )}
        </Panel>
        <Panel
          title="Evidence context"
          note="Availability, freshness and analysis are different checks"
        >
          <dl className="key-values">
            <dt>Source</dt>
            <dd>{label(data.snapshot?.data_origin)}</dd>
            <dt>Cutoff</dt>
            <dd>Course day {data.snapshot?.cutoff_day ?? "not available"}</dd>
            <dt>Snapshot</dt>
            <dd>
              {data.snapshot
                ? data.snapshot.is_fresh
                  ? "Fresh"
                  : "Stale"
                : "Not prepared"}
            </dd>
            <dt>Policy</dt>
            <dd>Revision {data.current_policy_version}</dd>
            <dt>Model</dt>
            <dd>{data.analysis?.model_version ?? "Not run"}</dd>
            <dt>Built at</dt>
            <dd>{data.snapshot?.built_at ?? "Not available"}</dd>
          </dl>
          <h3>Source coverage</h3>
          <div className="coverage">
            {Object.entries(data.snapshot?.coverage ?? {}).map(
              ([key, coverage]) => (
                <div key={key}>
                  <span>{label(key)}</span>
                  <Badge tone={coverage === "complete" ? "sage" : "amber"}>
                    {label(coverage)}
                  </Badge>
                </div>
              ),
            )}
          </div>
          <details>
            <summary>Model provenance</summary>
            <dl className="key-values">
              {[
                "model_digest",
                "prompt_version",
                "feature_version",
                "calibration_version",
              ].map((key) => (
                <div key={key}>
                  <dt>{label(key)}</dt>
                  <dd>{String(data.analysis?.[key] ?? "Not recorded")}</dd>
                </div>
              ))}
            </dl>
          </details>
        </Panel>
      </div>
      <Panel
        title="All checkpoint evidence"
        note="Unknown data is never shown as zero. Source IDs link every observed fact to its input records."
      >
        <details>
          <summary>
            Inspect {facts.length} evidence features and their availability
          </summary>
          <div
            className="table-scroll evidence-table"
            tabIndex={0}
            role="region"
            aria-label="Checkpoint evidence"
          >
            <table>
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Value</th>
                  <th>Availability</th>
                  <th>Window</th>
                  <th>Unit</th>
                </tr>
              </thead>
              <tbody>
                {facts.map(([key, fact]) => (
                  <tr key={key}>
                    <td>{label(key)}</td>
                    <td>{value(fact)}</td>
                    <td>{label(fact.status)}</td>
                    <td>{fact.window}</td>
                    <td>{fact.unit}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Panel>
    </>
  );
}

function Academic({ data }: { data: LearnerDetail }) {
  const facts = data.snapshot?.features ?? {};
  return (
    <>
      <Panel
        title="Academic evidence at this checkpoint"
        note="Course records available by the cutoff. Grade percentages are not risk scores."
      >
        <div className="academic-grid">
          {[
            "weighted_grade_percent",
            "assessments_missed",
            "completion_percent",
            "active_days_last_7",
          ].map((key) => (
            <div key={key}>
              <small>{label(key)}</small>
              <strong>
                {facts[key] ? value(facts[key]) : "Not available"}
              </strong>
              <small>
                {facts[key] ? label(facts[key].status) : "Not supported"}
              </small>
            </div>
          ))}
        </div>
        <Notice>
          Detailed grade/resource charts and practice-versus-assessed views are
          in the next parity phase. Original records remain accessible below;
          this page does not invent summaries.
        </Notice>
      </Panel>
      <Panel
        title="Recorded learning events"
        note={`${data.events.length} events available by this checkpoint`}
      >
        {data.events.length === 0 ? (
          <p className="empty">No available learning events.</p>
        ) : (
          <div className="record-list">
            {data.events.map((event, i) => (
              <details key={String(event.event_id ?? i)}>
                <summary>
                  <FileText size={15} />
                  Day {String(event.course_day ?? "?")} ·{" "}
                  {label(String(event.event_type ?? "event"))}
                </summary>
                <pre>{JSON.stringify(event, null, 2)}</pre>
              </details>
            ))}
          </div>
        )}
      </Panel>
    </>
  );
}
