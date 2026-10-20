import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  legacyAlertDetailSchema,
  legacyAlertsSchema,
  legacyLearnerDetailSchema,
  legacyLearnersSchema,
} from "../api/legacyEvidenceContracts";
import type {
  LegacyAlertDetail,
  LegacyAlert,
  LegacyFeature,
  LegacyLearner,
  LegacyPredictionPoint,
} from "../api/legacyEvidenceContracts";
import { Badge, band, label, Loading, Notice, Panel } from "../components/ui";
import { useEditGuard } from "../hooks/editGuard";
import { useResource } from "../hooks/useResource";

const PAGE_SIZE = 25;
function score(value: number | null) {
  return value === null ? "Not assessed" : `${Number((value * 100).toFixed(2))} / 100`;
}
const comparisonReasons: Record<string, string> = {
  NO_CURRENT_PREDICTION: "No prediction is available for the current checkpoint.",
  NO_PREVIOUS_PREDICTION: "The previous eligible checkpoint was not assessed.",
  MODEL_MISMATCH: "Different model versions are not directly comparable.",
  CALIBRATION_MISMATCH: "The checkpoints use different calibration versions.",
  UNCALIBRATED: "This score is not a calibrated probability.",
  NO_PREVIOUS_CHECKPOINT: "There is no previous eligible checkpoint.",
  CHECKPOINT_POLICY_UNAVAILABLE: "The course checkpoint schedule is unavailable.",
  ELIGIBILITY_UNKNOWN: "Checkpoint eligibility could not be established.",
  INELIGIBLE_CHECKPOINT: "This checkpoint is outside the learner's eligible period.",
  STATE_MISMATCH: "The predictions do not match the required learner checkpoints.",
  ORIGIN_MISMATCH: "The observations come from different data origins.",
  FEATURE_VERSION_MISMATCH: "Evidence definitions changed between checkpoints.",
  ABSTAINED: "The model did not assess one of these checkpoints.",
  QUALITY_GATE_FAILED: "One prediction did not pass validation.",
  NO_DISPLAY_PROBABILITY: "A comparable displayed value is unavailable.",
};

function hasCurrentPrediction(item: LegacyLearner) {
  return Boolean(
    item.state_id && item.prediction_id &&
    item.prediction_state_id === item.state_id &&
    item.assessment_status === "assessed",
  );
}

function currentScore(item: LegacyLearner) {
  return hasCurrentPrediction(item)
    ? `Risk score: ${score(item.display_probability)}`
    : "No current assessed score";
}

function freshness(value: boolean | null) {
  return value === null ? "Freshness unknown" : value ? "Fresh" : "Stale";
}

function Comparison({ learner }: { learner: LegacyLearner }) {
  const comparison = learner.comparison;
  if (
    !hasCurrentPrediction(learner) || !learner.comparison_available ||
    !comparison.available || comparison.previous_checkpoint === null ||
    comparison.current_checkpoint === null || comparison.previous_value === null ||
    comparison.current_value === null || comparison.delta === null ||
    comparison.current_checkpoint !== learner.latest_checkpoint_week
  ) {
    const reason = !hasCurrentPrediction(learner)
      ? "NO_CURRENT_PREDICTION"
      : comparison.reason ?? learner.comparison_reason;
    return <p>{comparisonReasons[reason] ?? "A reliable checkpoint comparison is unavailable."}</p>;
  }
  return (
    <p>
      Previous eligible checkpoint: week {comparison.previous_checkpoint}, {score(comparison.previous_value)}.
      {" "}Current checkpoint: week {comparison.current_checkpoint}, {score(comparison.current_value)}.
      {" "}Change: {comparison.delta >= 0 ? "+" : ""}{(comparison.delta * 100).toFixed(1)} points on the 0–100 scale.
    </p>
  );
}

function featureValue(feature: LegacyFeature) {
  if (feature.value == null || !["observed", "structural_zero"].includes(feature.missing_reason)) {
    return `Not observed: ${label(feature.missing_reason)}`;
  }
  return typeof feature.value === "object"
    ? JSON.stringify(feature.value)
    : String(feature.value);
}

function Features({ features }: { features: LegacyFeature[] }) {
  if (!features.length) return <p>No feature evidence was returned; missing records do not imply inactivity.</p>;
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier learner feature evidence">
      <table>
        <thead><tr><th>Feature</th><th>Observed value / missingness</th><th>Source observations</th><th>Evidence ID</th></tr></thead>
        <tbody>{features.map((feature) => (
          <tr key={feature.evidence_id}>
            <td>{label(feature.feature_name)}</td><td>{featureValue(feature)}</td>
            <td>{feature.source_observation_count} · {label(feature.missing_reason)}</td>
            <td>{feature.evidence_id}</td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function PredictionTimeline({ points }: { points: LegacyPredictionPoint[] }) {
  return (
    <>
      <p className="fineprint">
        Historical model outputs, not a continuous trend or a calibrated probability claim.
        Missing checkpoints are not interpolated. Different model versions and evidence definitions may not be comparable;
        only an explicit eligible-checkpoint comparison establishes comparability when available.
      </p>
      {!points.length ? <p>No saved prediction history.</p> : (
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier prediction timeline">
          <table>
            <thead><tr><th>Checkpoint</th><th>Cutoff course day</th><th>Historical risk score</th><th>Attention band</th><th>Model version</th><th>Generated at</th></tr></thead>
            <tbody>{points.map((point, index) => (
              <tr key={`${point.checkpoint_week}:${point.generated_at}:${index}`}>
                <td>Week {point.checkpoint_week}{point.is_selected_alert ? " · selected alert" : ""}</td>
                <td>{point.cutoff_course_day}</td><td>{score(point.display_probability)}</td>
                <td>{band(point.risk_band)}</td><td>{point.model_version}</td><td>{point.generated_at}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </>
  );
}

type AlertActions = (detail: LegacyAlertDetail) => ReactNode;

export function LegacyLearners({
  course, dataOrigin, revision, onOpenCase, renderAlertActions,
}: {
  course: string;
  dataOrigin?: string;
  revision: number;
  onOpenCase: (learnerId: string, alertId?: string) => void;
  renderAlertActions?: AlertActions;
}) {
  const guard = useEditGuard();
  const [queryDraft, setQueryDraft] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<LegacyLearner | null>(null);
  const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(offset) });
  if (query) params.set("query", query);
  const { data, error } = useResource(
    `v1/presentations/${encodeURIComponent(course)}/learners?${params}`,
    legacyLearnersSchema,
    revision,
  );
  const scoped = data && data.offset === offset && data.limit === PAGE_SIZE &&
    data.items.length <= PAGE_SIZE &&
    (!data.items.length || offset + data.items.length <= data.total) &&
    new Set(data.items.map((item) => item.learner_id)).size === data.items.length &&
    data.items.every((item) => item.presentation_id === course && (dataOrigin === undefined || item.data_origin === dataOrigin));
  useEffect(() => {
    if (scoped && offset > 0 && offset >= data.total) {
      setOffset(Math.max(0, Math.ceil(data.total / PAGE_SIZE) - 1) * PAGE_SIZE);
      setSelected(null);
    }
  }, [scoped, data, offset]);
  function navigate(nextOffset: number) {
    if (!guard.leave()) return;
    setOffset(nextOffset);
    setSelected(null);
  }
  return (
    <>
      <Panel title="Earlier learner roster" note="Existing v1 records only. These learners and episodes remain separate from current course-operation cases.">
        <form onSubmit={(event) => {
          event.preventDefault();
          if (!guard.leave()) return;
          setQuery(queryDraft.trim());
          setOffset(0);
          setSelected(null);
        }}>
          <label>Search earlier student ID
            <input aria-label="Search earlier student ID" maxLength={128} value={queryDraft} onChange={(event) => setQueryDraft(event.target.value)} />
          </label>
          <button type="submit">Search earlier learners</button>
        </form>
        <p className="fineprint">IDs only. A missing assessment or support case is not evidence of low risk. Model scores are not established probabilities.</p>
        {error ? <Notice error>{error}</Notice> : !data ? <Loading /> : !scoped ? (
          <Notice error>The earlier learner response does not match the requested course or page.</Notice>
        ) : (
          <>
            <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier learner roster">
              <table>
                <thead><tr><th>Student ID</th><th>Checkpoint</th><th>Current state-bound assessment</th><th>Provenance</th><th>Details</th></tr></thead>
                <tbody>{data.items.map((learner) => (
                  <tr key={learner.learner_id}>
                    <td>{learner.learner_id}</td>
                    <td>{learner.latest_checkpoint_week === null ? "No saved state" : `Week ${learner.latest_checkpoint_week}`}</td>
                    <td>{hasCurrentPrediction(learner) && <Badge>{band(learner.risk_band)}</Badge>} {currentScore(learner)}</td>
                    <td>{label(learner.data_origin)} · {freshness(learner.is_fresh)}</td>
                    <td><button aria-label={`Open earlier learner ${learner.learner_id}`} onClick={() => {
                      if (guard.leave()) setSelected(learner);
                    }}>Open learner</button></td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
            {!data.items.length && <p>No earlier learners match this page or search.</p>}
            <div className="pagination">
              <span>{data.items.length ? offset + 1 : 0}–{data.items.length ? offset + data.items.length : 0} of {data.total} learners</span>
              <div>
                <button disabled={!offset} onClick={() => navigate(Math.max(0, offset - PAGE_SIZE))}>Previous learners</button>
                <button disabled={offset + PAGE_SIZE >= data.total} onClick={() => navigate(offset + PAGE_SIZE)}>Next learners</button>
              </div>
            </div>
          </>
        )}
      </Panel>
      {selected && selected.presentation_id === course && (
        <LegacyLearnerDetail key={`${course}:${selected.learner_id}`} course={course} learner={selected.learner_id}
          dataOrigin={selected.data_origin} revision={revision} onOpenCase={onOpenCase} renderAlertActions={renderAlertActions} />
      )}
    </>
  );
}

export function LegacyAlerts({ course, dataOrigin, revision, onOpenCase, renderAlertActions }: {
  course: string;
  dataOrigin: string;
  revision: number;
  onOpenCase: (learnerId: string, alertId?: string) => void;
  renderAlertActions: AlertActions;
}) {
  const guard = useEditGuard();
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<LegacyAlert | null>(null);
  const params = new URLSearchParams({ presentation_id: course, limit: String(PAGE_SIZE), offset: String(offset) });
  if (status) params.set("status", status);
  const { data, error } = useResource(`v1/alerts?${params}`, legacyAlertsSchema, revision);
  const scoped = data && data.limit === PAGE_SIZE && data.offset === offset &&
    data.items.length <= PAGE_SIZE &&
    (!data.items.length || offset + data.items.length <= data.total) &&
    new Set(data.items.map((item) => item.alert_id)).size === data.items.length &&
    data.items.every((item) => item.presentation_id === course && item.data_origin === dataOrigin && (!status || item.status === status));
  useEffect(() => {
    if (scoped && offset > 0 && offset >= data.total) {
      setOffset(Math.max(0, Math.ceil(data.total / PAGE_SIZE) - 1) * PAGE_SIZE);
      setSelected(null);
    }
  }, [scoped, data, offset]);
  function navigate(next: number) {
    if (guard.leave()) { setOffset(next); setSelected(null); }
  }
  return <>
    <Panel title="Earlier alerts" note="Includes historical alerts that are not linked to a support episode. Alerts and episodes have independent statuses.">
      <label>Earlier alert status<select aria-label="Earlier alert status" value={status} onChange={(event) => {
        if (guard.leave()) { setStatus(event.target.value); setOffset(0); setSelected(null); }
      }}>
        <option value="">All alert statuses</option>
        {["new", "reviewed", "resolved", "dismissed"].map((value) => <option key={value} value={value}>{label(value)}</option>)}
      </select></label>
      <p className="fineprint">Saved alert scores describe their original checkpoints, not necessarily the latest learner state. Scores are not established probabilities. Opening evidence does not mark an alert reviewed.</p>
      {error ? <Notice error>{error}</Notice> : !data ? <Loading /> : !scoped ? <Notice error>The alert response does not match the requested course, data origin, status or page.</Notice> : <>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier alerts"><table>
          <thead><tr><th>Student ID</th><th>Checkpoint</th><th>Saved score</th><th>Alert status</th><th>Evidence</th></tr></thead>
          <tbody>{data.items.map((alert) => <tr key={alert.alert_id}>
            <td>{alert.learner_id}</td><td>Week {alert.checkpoint_week}</td>
            <td>{score(alert.display_probability)} · {band(alert.risk_band)} · {freshness(alert.is_fresh)}</td>
            <td>{label(alert.status)}</td><td><button aria-label={`Open earlier alert ${alert.alert_id}`} onClick={() => { if (guard.leave()) setSelected(alert); }}>Open alert</button></td>
          </tr>)}</tbody>
        </table></div>
        {!data.items.length && <p>No saved alerts match this page or status. Absence of an alert is not evidence of low risk.</p>}
        <div className="pagination"><span>{data.items.length ? offset + 1 : 0}–{data.items.length ? offset + data.items.length : 0} of {data.total} alerts</span><div>
          <button disabled={!offset} onClick={() => navigate(Math.max(0, offset - PAGE_SIZE))}>Previous alerts</button>
          <button disabled={offset + PAGE_SIZE >= data.total} onClick={() => navigate(offset + PAGE_SIZE)}>Next alerts</button>
        </div></div>
      </>}
    </Panel>
    {selected && <LegacyAlertEvidence key={selected.alert_id} course={course} learner={selected.learner_id} alertId={selected.alert_id} dataOrigin={dataOrigin} revision={revision}>
      {(detail) => <>
        <button onClick={() => onOpenCase(detail.alert.learner_id, detail.alert.alert_id)}>Open support episodes with this alert</button>
        {renderAlertActions(detail)}
      </>}
    </LegacyAlertEvidence>}
  </>;
}

function LegacyLearnerDetail({ course, learner, dataOrigin, revision, onOpenCase, renderAlertActions }: {
  course: string;
  learner: string;
  dataOrigin: string;
  revision: number;
  onOpenCase: (learnerId: string, alertId?: string) => void;
  renderAlertActions?: AlertActions;
}) {
  const guard = useEditGuard();
  const { data, error } = useResource(
    `v1/presentations/${encodeURIComponent(course)}/learners/${encodeURIComponent(learner)}`,
    legacyLearnerDetailSchema,
    revision,
  );
  if (error) return <Notice error>{error}</Notice>;
  if (!data) return <Loading />;
  const item = data.learner;
  if (item.presentation_id !== course || item.learner_id !== learner || item.data_origin !== dataOrigin) {
    return <Notice error>The learner evidence does not match the selected course, student ID or data origin.</Notice>;
  }
  const currentAlert = hasCurrentPrediction(item) && item.alert_id && item.state_id;
  return (
    <>
      <Panel title={`Earlier learner ${learner}`} note="Current saved state and historical evidence from the earlier workspace; no new assessment is generated.">
        <p><Badge>{label(item.data_origin)} data</Badge> {freshness(item.is_fresh)} · {currentScore(item)}</p>
        {hasCurrentPrediction(item) && <p>{band(item.risk_band)} · model {item.model_version ?? "unavailable"}</p>}
        <p>Checkpoint: {item.latest_checkpoint_week ?? "unavailable"} · cutoff course day: {item.latest_cutoff_course_day ?? "unavailable"} · evidence completeness: {item.completeness === null ? "unavailable" : `${(item.completeness * 100).toFixed(0)}%`}</p>
        <p className="fineprint">State ID: {item.state_id ?? "none"} · prediction ID: {item.prediction_id ?? "none"} · prediction state ID: {item.prediction_state_id ?? "none"}</p>
        <Notice>Scores are model outputs, not established calibrated probabilities. Stale or missing observations limit interpretation; support decisions remain with the instructor.</Notice>
        <h3>Previous / current eligible checkpoint</h3>
        <Comparison learner={item} />
        <p>Registration course day: {data.registration_day ?? label(data.registration_missing_reason)} · unregistration course day: {data.unregistration_day ?? label(data.unregistration_missing_reason)}</p>
        <button onClick={() => { if (guard.leave()) onOpenCase(learner); }}>Open support episodes for this learner</button>
        <h3>Current state evidence</h3>
        {item.state_id ? <Features features={data.features} /> : <p>No current state evidence is available.</p>}
        <h3>Recorded activity timeline</h3>
        <p className="fineprint">Recorded events only. Gaps or absent records do not establish that a learner was inactive. Course days and weeks are relative to this course.</p>
        {!data.activity_timeline.length ? <p>No recorded activity timeline.</p> : (
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Earlier activity timeline">
            <table>
              <thead><tr><th>Course week</th><th>Recorded interactions</th><th>Assessment events</th></tr></thead>
              <tbody>{data.activity_timeline.map((week) => <tr key={week.course_week}><td>{week.course_week}</td><td>{week.activity_count}</td><td>{week.assessment_event_count}</td></tr>)}</tbody>
            </table>
          </div>
        )}
        <h3>Prediction timeline</h3>
        <PredictionTimeline points={data.prediction_timeline} />
      </Panel>
      {currentAlert ? (
        <LegacyAlertEvidence course={course} learner={learner} alertId={item.alert_id!} stateId={item.state_id!} dataOrigin={dataOrigin} revision={revision}>
          {(detail) => <>
            <button onClick={() => { if (guard.leave()) onOpenCase(learner, detail.alert.alert_id); }}>Open support episodes with this alert</button>
            {renderAlertActions?.(detail)}
          </>}
        </LegacyAlertEvidence>
      ) : <Notice>No alert is linked to an assessed prediction for this learner's current state. Historical linked alerts remain available in the learner's support episodes.</Notice>}
    </>
  );
}

export function LegacyAlertEvidence({
  course, learner, alertId, revision, stateId, dataOrigin, children,
}: {
  course: string;
  learner: string;
  alertId: string;
  revision: number;
  stateId?: string;
  dataOrigin?: string;
  children?: ReactNode | AlertActions;
}) {
  const { data, error } = useResource(
    `v1/alerts/${encodeURIComponent(alertId)}`,
    legacyAlertDetailSchema,
    revision,
  );
  const matches = data && data.alert.alert_id === alertId &&
    data.alert.presentation_id === course && data.alert.learner_id === learner &&
    (stateId === undefined || data.state_id === stateId) &&
    (dataOrigin === undefined || data.alert.data_origin === dataOrigin);
  return (
    <Panel title="Earlier alert evidence and review history" note="An alert review is separate from a support-case action. Original evidence, provenance and review timestamps are retained.">
      {error ? <Notice error>{error}</Notice> : !data ? <Loading /> : !matches ? (
        <Notice error>This alert does not match the selected alert, course, learner, state or data origin. Review actions are unavailable.</Notice>
      ) : (
        <>
          <p>Alert {data.alert.alert_id} · student {data.alert.learner_id} · {label(data.alert.status)}</p>
          <p><Badge>{label(data.alert.data_origin)} data</Badge> {freshness(data.alert.is_fresh)} · {band(data.alert.risk_band)} · risk score {score(data.alert.display_probability)}</p>
          <p>Week {data.alert.checkpoint_week} · cutoff course day {data.alert.cutoff_course_day} · generated {data.alert.generated_at} · priority {label(data.alert.priority)}</p>
          <Notice>{data.uncertainty_note || "No uncertainty note was supplied."} Model scores are not established calibrated probabilities; this alert refers to its saved state, not necessarily the latest learner state.</Notice>
          <p>Model {data.alert.model_version} ({data.alert.model_kind}) · reference {data.model_ref}</p>
          <p>State {data.state_id} · feature set {data.feature_set_version} · completeness {(data.completeness * 100).toFixed(0)}%</p>
          <p>Quality gate: {data.quality_gate_passed ? "passed" : "failed"} · fallback: {data.fallback_used ? "used" : "not used"} · input hash: {data.input_hash}</p>
          <h3>Evidence-backed claims</h3>
          {data.claims.length ? data.claims.map((claim, index) => (
            <p key={`${claim.claim_code}:${index}`}>{label(claim.claim_code)} · evidence IDs: {claim.evidence_ids.join(", ") || "none supplied"}</p>
          )) : <p>No claims were returned.</p>}
          <h3>Suggested actions</h3>
          <p>{data.suggested_actions.map(label).join(" · ") || "No suggested actions were returned."}</p>
          <h3>Linked evidence ({data.alert.evidence_count})</h3>
          <Features features={data.evidence} />
          {data.evidence.map((evidence) => (
            <details key={evidence.evidence_id}>
              <summary>Source provenance for {evidence.evidence_id}</summary>
              <p>Observation hash: {evidence.source_observation_hash}</p>
              <p>Source record ID samples: {evidence.source_record_samples.join(", ") || "none supplied"}</p>
            </details>
          ))}
          <h3>Prediction timeline</h3>
          <PredictionTimeline points={data.prediction_timeline} />
          <h3>Alert review audit history</h3>
          <p className="fineprint">Instructor-authored notes may contain identifying information. Use care when sharing your screen.</p>
          {data.review_history.length ? data.review_history.map((review) => (
            <article className="diagnostic-sample" key={review.review_id}>
              <h4>{label(review.previous_status)} → {label(review.new_status)}</h4>
              <p>{review.reviewed_at} · {review.reviewer_id} ({review.reviewer_role}) · review {review.review_id}</p>
              {review.note && <p className="preserve-lines">{review.note}</p>}
            </article>
          )) : <p>No alert reviews have been recorded.</p>}
          {typeof children === "function" ? children(data) : children}
        </>
      )}
    </Panel>
  );
}
