import { useState } from "react";
import { RefreshCw } from "lucide-react";
import type { Workspace } from "../api/contracts";
import type { AnalysisStatus } from "../api/analysisContracts";
import {
  automationSchema,
  controlSchema,
  queueMessage,
  queueResultSchema,
  resumePending,
} from "../api/analysisContracts";
import { useAnalysisStatus } from "../hooks/useAnalysisStatus";
import { OperationDialog } from "../components/OperationDialog";
import { Badge, label, Loading, Notice, Panel } from "../components/ui";
import { AnalysisControls } from "./AnalysisControls";

type RequestChoice =
  | { kind: "batch"; mode: "unassessed" | "retry_failed" }
  | { kind: "automation"; enabled: boolean; version: number }
  | { kind: "resume"; reason: string | null | undefined };
export function ModelHealth({
  data,
  course,
  csrf,
  revision,
}: {
  data: Workspace;
  course: string;
  csrf: string;
  revision: number;
}) {
  return (
    <>
      <Panel
        title="Checkpoint data & analysis"
        note={`Unique students at week ${data.week}. Availability, freshness and completed analysis are different checks.`}
      >
        <div className="health-grid">
          {[
            ["Enrolled", data.summary.enrolled],
            ["Needs review", data.summary.needs_review],
            ["High attention", data.summary.high_attention],
            ["Insufficient evidence", data.summary.insufficient_data],
            ["Not analyzed / outdated", data.summary.not_run],
            ["Queued / running", data.summary.queued],
            ["Failed analysis", data.summary.failed],
          ].map(([name, value]) => (
            <div key={name}>
              <small>{name}</small>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
        <p className="fineprint">
          Workload categories can overlap. These student counts refresh with
          Refresh data; the separate course-wide progress panel polls
          automatically.
        </p>
        <details>
          <summary>Saved result sources at this checkpoint</summary>
          <dl className="settings-grid">
            {Object.entries(data.model_counts).map(([name, count]) => (
              <div key={name}>
                <dt>{name}</dt>
                <dd>{count} students</dd>
              </div>
            ))}
          </dl>
          <p>A rules baseline is not an LLM result.</p>
        </details>
      </Panel>
      <CourseAnalysis course={course} csrf={csrf} revision={revision} />
      <AnalysisControls course={course} week={data.week} csrf={csrf} />
      <Panel title="What these terms mean">
        <dl className="key-values">
          <dt>Risk score</dt>
          <dd>
            Uncalibrated 0–100 output for review priority, not a probability of
            failure.
          </dd>
          <dt>Support level</dt>
          <dd>
            Server label derived from the model risk score for one checkpoint.
          </dd>
          <dt>Validated</dt>
          <dd>
            Structure and evidence checks passed. Accuracy must be evaluated
            separately.
          </dd>
          <dt>Abstained</dt>
          <dd>
            No risk score issued; evidence or model certainty was insufficient.
          </dd>
          <dt>Ongoing</dt>
          <dd>Support or follow-up is still open, not merely viewed.</dd>
        </dl>
      </Panel>
    </>
  );
}

export function CourseAnalysis({
  course,
  csrf,
  revision,
}: {
  course: string;
  csrf: string;
  revision: number;
}) {
  const { data, error, refresh } = useAnalysisStatus(course, revision);
  const [choice, setChoice] = useState<RequestChoice | null>(null);
  const [message, setMessage] = useState("");
  function finished(text: string) {
    setChoice(null);
    setMessage(text);
    refresh();
  }
  const root = `v2/courses/${encodeURIComponent(course)}/analysis`;
  return (
    <>
      {message && (
        <div className="success-message" role="status">
          {message}
        </div>
      )}
      <Panel
        title="LLM analysis · every course checkpoint"
        note="Student-checkpoint records across all prepared weeks, not unique students. Only the current approved model and policy count."
        action={
          <button onClick={refresh}>
            <RefreshCw size={16} />
            Refresh analysis status
          </button>
        }
      >
        <p className="fineprint">
          Progress refreshes every 10 seconds while this page is visible (after
          the previous read finishes). It does not run or restart the model.
          Student cards and profiles update with Refresh data.
        </p>
        {error ? (
          <Notice error>
            {error} Previously displayed counts are not confirmed and have been
            hidden. Try Refresh analysis status.
          </Notice>
        ) : !data ? (
          <Loading />
        ) : (
          <>
            <p className="fineprint">
              Latest verified progress read:{" "}
              <time dateTime={data.served_at}>{data.served_at}</time>
            </p>
            <Progress data={data} />
            <Runtime data={data} />
            {data.course_control.status === "paused" && (
              <div className="course-pause">
                <Notice>
                  Automatic analysis is paused for this course after repeated
                  validation failures. Other courses may continue. Queueing more
                  work does not resume it.
                </Notice>
                <p>
                  Course pause code:{" "}
                  <code>
                    {data.course_control.last_error_code ?? "Not recorded"}
                  </code>{" "}
                  · consecutive failures: {data.course_control.failure_streak}
                </p>
                <p className="fineprint">
                  Updated: {data.course_control.updated_at ?? "Not recorded"}.
                  Review the failure details and correction before requesting
                  resume.
                </p>
                <button
                  onClick={() =>
                    setChoice({
                      kind: "resume",
                      reason: data.course_control.last_error_code,
                    })
                  }
                >
                  Resume this course after checking the error
                </button>
              </div>
            )}
            {resumePending(data.course_control) && (
              <Notice>
                A course resume was requested, but the worker has not
                acknowledged it yet. This is not proof that processing
                restarted.
              </Notice>
            )}
            <div className="operation-buttons">
              <button
                className="primary"
                disabled={
                  data.summary.total_snapshots === 0 ||
                  data.summary.unassessed === 0
                }
                onClick={() => setChoice({ kind: "batch", mode: "unassessed" })}
              >
                Analyze all unassessed checkpoints
              </button>
              <button
                disabled={data.summary.failed === 0}
                onClick={() =>
                  setChoice({ kind: "batch", mode: "retry_failed" })
                }
              >
                Retry eligible failed analysis
              </button>
            </div>
            <p className="fineprint">
              All prepared weeks in this course. Reuse matching
              completed/pending work; retry only failed jobs within{" "}
              {data.max_attempts} attempts. Neither action clears a protective
              pause. Fix configuration, evidence or validation causes before
              retrying.
            </p>
            <details>
              <summary>Progress by course week</summary>
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Analysis progress by week"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Week</th>
                      <th>Records</th>
                      <th>Validated</th>
                      <th>Abstained</th>
                      <th>Queued</th>
                      <th>Running</th>
                      <th>Retry scheduled</th>
                      <th>Awaiting queue</th>
                      <th>Failed</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.weeks.map((row) => (
                      <tr key={row.week}>
                        <td>{row.week}</td>
                        <td>{row.total_snapshots}</td>
                        <td>{row.validated}</td>
                        <td>{row.abstained}</td>
                        <td>{row.queued}</td>
                        <td>{row.running}</td>
                        <td>{row.retry_scheduled}</td>
                        <td>{row.unassessed}</td>
                        <td>{row.failed}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <Failures data={data} />
            <section className="automation-card">
              <h3>Automatic analysis of new or changed checkpoints</h3>
              <Badge tone={data.automation.enabled ? "sage" : "neutral"}>
                {data.automation.enabled ? "Enabled" : "Disabled"} · revision{" "}
                {data.automation.version}
              </Badge>
              <p>
                When the worker and model are ready, newly prepared or changed
                records and policy changes are discovered. Matching results are
                reused. Turning this off does not cancel work already queued or
                running.
              </p>
              <button
                onClick={() =>
                  setChoice({
                    kind: "automation",
                    enabled: !data.automation.enabled,
                    version: data.automation.version,
                  })
                }
              >
                {data.automation.enabled
                  ? "Disable automatic discovery"
                  : "Enable automatic discovery"}
              </button>
            </section>
          </>
        )}
      </Panel>
      {choice?.kind === "batch" && (
        <OperationDialog
          title={
            choice.mode === "unassessed"
              ? "Queue all unassessed checkpoints"
              : "Retry eligible failed analysis"
          }
          description={
            <>
              <p>
                Scope: every prepared student-checkpoint in this course ·
                configured Qwen model.
              </p>
              <Notice>
                {choice.mode === "retry_failed"
                  ? "Check the failure reason and any correction first. A retry cannot fix missing data, a stopped worker or a broken contract. Jobs at their attempt limit stay failed."
                  : "Only unassessed records are added. Existing jobs and current results are reused. Failed records require a separate explicit retry."}{" "}
                Queuing never clears a pause and does not import data.
              </Notice>
            </>
          }
          path={`${root}/batch`}
          body={{ scope: "all_weeks", mode: choice.mode }}
          schema={queueResultSchema}
          csrf={csrf}
          close={() => setChoice(null)}
          saved={(result) => finished(queueMessage(result))}
        />
      )}
      {choice?.kind === "automation" && (
        <OperationDialog
          title={
            choice.enabled
              ? "Enable automatic discovery"
              : "Disable automatic discovery"
          }
          description={
            <p>
              Change automation revision {choice.version} for this course.{" "}
              {choice.enabled
                ? "Prepared new/changed checkpoints may be queued when the worker and model are ready; protective pauses still apply."
                : "Already queued or running analysis may still finish. This is not a stop-worker control."}
            </p>
          }
          path={`${root}/automation`}
          body={{ enabled: choice.enabled, version: choice.version }}
          schema={automationSchema}
          csrf={csrf}
          close={() => setChoice(null)}
          saved={(result) =>
            finished(
              result.enabled
                ? "Automatic discovery enabled for this course."
                : "Automatic discovery disabled. Already queued or running work may still finish.",
            )
          }
        />
      )}
      {choice?.kind === "resume" && (
        <OperationDialog
          title="Request course resume"
          description={
            <>
              <p>
                Pause reason reviewed:{" "}
                <code>{choice.reason ?? "Not recorded"}</code>.
              </p>
              <Notice>
                Confirm you reviewed the validation error and its correction.
                This resets this course's failure streak and requests resumed
                work. It cannot clear a shared service pause or start a stopped
                worker. Wait for an actual heartbeat and acknowledgement.
              </Notice>
            </>
          }
          path={`${root}/resume`}
          body={{}}
          schema={controlSchema}
          csrf={csrf}
          close={() => setChoice(null)}
          saved={() =>
            finished(
              "Course resume requested. Worker acknowledgement and successful processing have not been confirmed.",
            )
          }
        />
      )}
    </>
  );
}

function Progress({ data }: { data: AnalysisStatus }) {
  const s = data.summary,
    completed = s.validated + s.abstained;
  return (
    <>
      <div className="health-grid analysis-metrics">
        <div>
          <small>LLM analysis completed</small>
          <strong>
            {completed.toLocaleString()} / {s.total_snapshots.toLocaleString()}
          </strong>
          <small>
            {s.validated} validated · {s.abstained} abstained without a risk
            score
          </small>
        </div>
        <div>
          <small>Queued / running</small>
          <strong>
            {s.queued.toLocaleString()} / {s.running.toLocaleString()}
          </strong>
          <small>{s.retry_scheduled} retries scheduled</small>
        </div>
        <div>
          <small>Awaiting queue</small>
          <strong>{s.unassessed.toLocaleString()}</strong>
          <small>
            No current LLM result or pending job; failures are separate
          </small>
        </div>
        <div>
          <small>Failed analysis</small>
          <strong>{s.failed.toLocaleString()}</strong>
          <small>See recent failure reasons below</small>
        </div>
      </div>
      {s.total_snapshots > 0 && (
        <label>
          Course-wide completion · validated and explicit abstentions
          <progress
            className="completion-meter"
            max={s.total_snapshots}
            value={Math.min(completed, s.total_snapshots)}
            aria-label={`${completed} of ${s.total_snapshots} LLM records completed`}
          />
        </label>
      )}
      {s.baseline_only > 0 && (
        <p className="fineprint">
          {s.baseline_only} records have only a rules-baseline assessment, not a
          current LLM result. They may already be queued; this is an overlapping
          count, not extra records.
        </p>
      )}
    </>
  );
}
function Runtime({ data }: { data: AnalysisStatus }) {
  const { model, worker } = data;
  return (
    <div className="runtime-status">
      <div className="support-summary">
        <strong>Model: {model.model}</strong>
        <Badge tone={model.status === "ready" ? "sage" : "amber"}>
          {label(model.status)}
        </Badge>
        <strong>Worker: {label(worker.status)}</strong>
      </div>
      <p className="fineprint">
        Model readiness checks availability, not successful inference. Last
        actual worker heartbeat: {worker.heartbeat_at ?? "Not recorded"}
        {worker.heartbeat_age_seconds != null
          ? ` (${worker.heartbeat_age_seconds}s ago)`
          : ""}
        .
      </p>
      {model.status !== "ready" && (
        <Notice>
          Work can be queued now, but analysis needs a ready model and running
          worker. Refreshing or queuing does not start either service.
        </Notice>
      )}
      {model.failure && (
        <Notice error>
          {model.failure.title}: {model.failure.detail}
          <p>Next step: {model.failure.action}</p>
          <code>{model.failure.code}</code>
        </Notice>
      )}
      {worker.status === "heartbeat_stale" && (
        <Notice error>
          The worker has not reported within its expected window. Ask the
          operator to check its process and logs; more queued work will not
          restart it.
        </Notice>
      )}
      {worker.status === "not_started" && (
        <Notice>
          No worker has reported yet. A server operator must start the analysis
          worker.
        </Notice>
      )}
      {worker.status === "paused" && (
        <Notice error>
          The shared analysis service is paused. Only the server operator can
          resolve and resume this service pause; a course resume cannot clear
          it.
        </Notice>
      )}
      {worker.is_processing_this_course && (
        <p>
          Processing this course
          {worker.active_week != null ? `, week ${worker.active_week}` : ""}.
        </p>
      )}
      {worker.processing_another_course && (
        <p>
          The shared worker is processing another course. This course's pending
          work must wait; no other-course identity is exposed.
        </p>
      )}
      {worker.pause_until && (
        <p>Worker retry pause until {worker.pause_until}.</p>
      )}
      {worker.last_error_code && (
        <p>
          Worker diagnostic: <code>{worker.last_error_code}</code>. Check the
          failure guidance below or share this code with the operator.
        </p>
      )}
      <details>
        <summary>Model identity and worker timing</summary>
        <dl className="key-values">
          <dt>Model digest</dt>
          <dd>{model.digest ?? "Not verified"}</dd>
          <dt>Active inference deadline</dt>
          <dd>{worker.active_deadline_at ?? "Not recorded"}</dd>
          <dt>Pause scope</dt>
          <dd>{worker.pause_scope ?? "None reported"}</dd>
        </dl>
      </details>
    </div>
  );
}
function Failures({ data }: { data: AnalysisStatus }) {
  if (!data.failures.length) return null;
  return (
    <section className="analysis-failures">
      <h3>Recent failure reasons · including retried work</h3>
      <p className="fineprint">
        These groups can include queued/running retries carrying their last
        error, so their counts need not equal currently failed records. No raw
        model replies or student text are shown.
      </p>
      {data.failures.map((failure) => (
        <article key={failure.code}>
          <Notice error>
            {failure.count} record(s) · {failure.title}
            <p>{failure.detail}</p>
            <p>Next step: {failure.action}</p>
            <code>{failure.code}</code>
          </Notice>
          <details>
            <summary>Exact validation details · recent samples</summary>
            <p className="fineprint">
              Up to three jobs and two responses per job. Samples do not
              represent all failed records.
            </p>
            {!failure.diagnostic_samples?.length && (
              <p>
                Older attempt detail unavailable. No field-level diagnostic was
                retained.
              </p>
            )}
            {failure.diagnostic_samples?.slice(0, 3).map((sample, i) => (
              <div key={sample.job_id} className="diagnostic-sample">
                <h4>
                  Sample {i + 1} · job attempt{" "}
                  {sample.job_attempt ?? "not recorded"}
                </h4>
                <p>
                  Operator reference: <code>{sample.job_id}</code>
                </p>
                {sample.generations.slice(0, 2).map((generation, j) => (
                  <div key={j}>
                    <p>
                      {label(generation.kind)} · {label(generation.outcome)} ·{" "}
                      {generation.latency_seconds ?? "Unknown"} seconds
                    </p>
                    {generation.validation_details?.length ? (
                      <div
                        className="table-scroll"
                        tabIndex={0}
                        role="region"
                        aria-label="Field-level validation diagnostics"
                      >
                        <table>
                          <thead>
                            <tr>
                              <th>Field</th>
                              <th>Problem</th>
                              <th>Expected</th>
                              <th>Received type</th>
                              <th>Safe value</th>
                            </tr>
                          </thead>
                          <tbody>
                            {generation.validation_details.map((d, k) => (
                              <tr key={k}>
                                <td>
                                  <code>{d.path}</code>
                                </td>
                                <td>{d.code}</td>
                                <td>{d.expected ?? "Not recorded"}</td>
                                <td>{d.received_type ?? "Unknown"}</td>
                                <td>
                                  {d.received === undefined
                                    ? "Not retained"
                                    : JSON.stringify(d.received)}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p>
                        No field-level diagnostic retained for this response.
                      </p>
                    )}
                    {generation.normalizations?.map((n, k) => (
                      <p className="fineprint" key={k}>
                        Formatting normalization: <code>{n.path}</code> ·{" "}
                        {n.code}
                      </p>
                    ))}
                  </div>
                ))}
                {!sample.generations.length && (
                  <p>Older attempt detail unavailable.</p>
                )}
              </div>
            ))}
          </details>
        </article>
      ))}
    </section>
  );
}
