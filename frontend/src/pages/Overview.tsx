import type { Workspace } from "../api/contracts";
import { Badge, Metric, Notice, Panel } from "../components/ui";
import { ArrowRight, Flag, Bookmark, CalendarClock } from "lucide-react";

export function Overview({
  data,
  openList,
  openStudent,
}: {
  data: Workspace;
  openList: (filter?: string) => void;
  openStudent: (id: string) => void;
}) {
  const summary = data.summary;
  const distribution = [
    ["High attention", data.distribution.high, "coral"],
    ["Monitor", data.distribution.medium, "amber"],
    ["Lower attention", data.distribution.low, "sage"],
    ["Not assessed", data.distribution.unavailable, "neutral"],
  ] as const;
  const movement = [
    ["Risk score increased", data.movement.increased, "coral"],
    ["Risk score similar", data.movement.stable, "lilac"],
    ["Risk score decreased", data.movement.decreased, "sage"],
    ["No valid comparison", data.movement.not_comparable, "neutral"],
  ] as const;
  return (
    <>
      {Object.keys(data.model_counts).some((key) =>
        /rules|baseline/.test(key),
      ) && (
        <Notice>
          Temporary rules-baseline results are included in this view. They are
          not the final LLM or a measured prediction-accuracy result.
        </Notice>
      )}
      <p className="fineprint">
        Saved result sources:{" "}
        {Object.entries(data.model_counts)
          .map(([name, count]) => `${name}: ${count}`)
          .join(" · ")}
        .
      </p>
      <div className="metric-grid">
        <Metric
          title="Enrolled students"
          value={summary.enrolled}
          note="The whole checkpoint roster"
          onClick={() => openList()}
        />
        <Metric
          title="Needs review"
          value={summary.needs_review}
          note="Concerns or follow-ups due"
          tone="amber"
          onClick={() => openList("needs_review")}
        />
        <Metric
          title="High attention"
          value={summary.high_attention}
          note="Current model support level"
          tone="coral"
          onClick={() => openList("high")}
        />
        <Metric
          title="Insufficient evidence"
          value={summary.insufficient_data}
          note="An explicit model abstention"
          tone="lilac"
          onClick={() => openList("insufficient_data")}
        />
      </div>
      <p className="fineprint">
        Workload counts overlap. A student can need review, have high attention
        and have an active support case.
      </p>
      <div className="quick-filters">
        <button onClick={() => openList("flagged")}>
          <Flag size={16} /> Flagged <b>{summary.flagged}</b>
        </button>
        <button onClick={() => openList("watchlist")}>
          <Bookmark size={16} /> Watchlist <b>{summary.watchlist}</b>
        </button>
        <button onClick={() => openList("due")}>
          <CalendarClock size={16} /> Follow-ups due <b>{summary.due}</b>
        </button>
        <button onClick={() => openList("active_cases")}>
          Active support cases <b>{summary.active_cases}</b>
          <ArrowRight size={16} />
        </button>
      </div>
      <div className="two-columns">
        <Panel
          title="Current support levels"
          note={`One category per student · ${summary.enrolled} enrolled`}
        >
          <Bars rows={distribution} total={summary.enrolled} />
          <p className="fineprint">
            Not assessed includes missing, pending, failed or unsupported risk
            scores. It does not mean lower attention.
          </p>
        </Panel>
        <Panel
          title="Since the previous checkpoint"
          note="Direction of change, not the current support level"
        >
          <Bars rows={movement} total={summary.enrolled} />
          <p className="fineprint">
            Similar = within 0.5 risk-score points. Requires compatible model
            and policy. Both charts use the same student-count scale.
          </p>
        </Panel>
      </div>
      <Panel
        title="Start with the students who need you"
        note="First six records in the server's attention order"
        action={
          <button className="text-button" onClick={() => openList()}>
            View all students <ArrowRight size={16} />
          </button>
        }
      >
        <div className="attention-list">
          {data.items.slice(0, 6).map((student) => (
            <button
              key={student.learner_id}
              className="attention-row"
              onClick={() => openStudent(student.learner_id)}
            >
              <span className="avatar">{student.display_name.slice(0, 1)}</span>
              <span className="student-name">
                <strong>{student.display_name}</strong>
                <small>{student.learner_id}</small>
              </span>
              <Badge tone={student.needs_review ? "amber" : "neutral"}>
                {student.needs_review ? "Needs review" : "No review flag"}
              </Badge>
              <ArrowRight size={18} />
            </button>
          ))}
        </div>
        {!data.items.length && (
          <p className="empty">No enrolled students at this checkpoint.</p>
        )}
      </Panel>
      <div className="context-foot">
        Current support records · follow-ups checked through course day{" "}
        {data.as_of_day} ({data.as_of_day_basis.replaceAll("_", " ")}). Manual
        flags never change model scores.
      </div>
    </>
  );
}

function Bars({
  rows,
  total,
}: {
  rows: readonly (readonly [string, number, string])[];
  total: number;
}) {
  return (
    <div className="bars">
      {rows.map(([name, count, tone]) => (
        <div className="bar-row" key={name}>
          <span>{name}</span>
          <b>{count}</b>
          <div className="bar-track">
            <span
              className={tone}
              style={{ width: `${total ? (count / total) * 100 : 0}%` }}
            />
          </div>
        </div>
      ))}
      <div className="chart-scale">
        <span>0 students</span>
        <span>{total} students</span>
      </div>
    </div>
  );
}
