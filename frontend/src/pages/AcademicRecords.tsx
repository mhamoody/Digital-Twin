import { useId, useState } from "react";
import type { Fact, LearnerDetail } from "../api/contracts";
import { Badge, label, Notice, Panel } from "../components/ui";

type RecordBag = Record<string, unknown>;
type Grade = {
  id: string;
  assessment: string;
  published: number;
  percent: number;
  category: "assessed" | "practice" | "unclassified";
};
const colors = {
  assessed: "#267769",
  practice: "#9b6419",
  unclassified: "#686e7a",
};
const names = {
  assessed: "Assessed work",
  practice: "Practice / formative",
  unclassified: "Unclassified",
};
const known = new Set(["observed", "structural_zero"]);
const finite = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);
const bag = (value: unknown): RecordBag =>
  value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordBag)
    : {};
function factNumber(fact?: Fact) {
  return fact && known.has(fact.status) && finite(fact.value)
    ? fact.value
    : null;
}
function factValue(fact: Fact) {
  return fact.value === null
    ? label(fact.status)
    : `${fact.value}${fact.unit === "percent" ? "%" : ""}`;
}

// Mirror the backend classification. A missing weight must never imply assessed work.
function category(definition: RecordBag): Grade["category"] {
  if (
    ["practice", "formative"].includes(String(definition.purpose)) ||
    String(definition.kind ?? "").startsWith("practice")
  )
    return "practice";
  return finite(definition.weight) && definition.weight > 0
    ? "assessed"
    : "unclassified";
}
export function gradeRows(data: LearnerDetail): Grade[] {
  const cutoff = data.snapshot?.cutoff_day;
  if (cutoff == null) return [];
  const definitions = new Map(
    data.assessments.map((row) => [String(row.assessment_id), row]),
  );
  return data.events
    .flatMap((event, index) => {
      if (
        event.event_type !== "assessment_grade" ||
        !finite(event.available_day) ||
        !finite(event.course_day) ||
        event.available_day > cutoff ||
        event.course_day > cutoff
      )
        return [];
      const payload = bag(event.payload);
      if (
        !finite(payload.score) ||
        !finite(payload.max_score) ||
        payload.max_score <= 0
      )
        return [];
      const percent = (100 * payload.score) / payload.max_score;
      // An invalid mark is inspectable in the source records, never clipped to look valid.
      if (percent < 0 || percent > 100) return [];
      const assessment = String(payload.assessment_id ?? "Assessment");
      let definition = definitions.get(assessment) ?? {};
      if (
        !finite(definition.available_day) ||
        !Number.isInteger(definition.available_day) ||
        definition.available_day > cutoff
      )
        definition = {};
      return [
        {
          id: String(event.event_id ?? index),
          assessment,
          published: event.available_day,
          percent,
          category: category(definition),
        },
      ];
    })
    .sort((a, b) => a.published - b.published);
}

function FactTable({
  entries,
  title,
}: {
  entries: [string, Fact][];
  title: string;
}) {
  if (!entries.length)
    return (
      <p className="empty">
        No {title.toLowerCase()} supplied at this checkpoint.
      </p>
    );
  return (
    <div className="table-scroll" role="region" aria-label={title} tabIndex={0}>
      <table>
        <thead>
          <tr>
            <th>Evidence</th>
            <th>Value</th>
            <th>Availability</th>
            <th>Window</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([name, fact]) => (
            <tr key={name}>
              <td>{label(name)}</td>
              <td>{factValue(fact)}</td>
              <td>{label(fact.status)}</td>
              <td>{fact.window}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function GradeChart({ rows, cutoff }: { rows: Grade[]; cutoff: number }) {
  const id = useId();
  const min = Math.min(0, ...rows.map((row) => row.published));
  const max = Math.max(min + 1, cutoff);
  const x = (day: number) => 52 + ((day - min) / (max - min)) * 576;
  const y = (percent: number) => 208 - percent * 1.72;
  return (
    <>
      <div
        className="chart-scroll"
        tabIndex={0}
        role="region"
        aria-label="Grade chart; scroll horizontally on a small screen"
      >
        <svg
          className="evidence-chart"
          viewBox="0 0 660 265"
          role="img"
          aria-labelledby={id}
        >
          <title id={id}>
            Published grades from 0 to 100 percent, separated by assessment
            type. Exact values are in the table below.
          </title>
          {[0, 25, 50, 75, 100].map((tick) => (
            <g key={tick}>
              <line
                x1={52}
                x2={628}
                y1={y(tick)}
                y2={y(tick)}
                stroke="#e4e8e5"
              />
              <text
                x={42}
                y={y(tick) + 4}
                textAnchor="end"
                fontSize={12}
                fill="#53645d"
              >
                {tick}%
              </text>
            </g>
          ))}
          {[min, Math.round((min + max) / 2), max]
            .filter((tick, index, ticks) => ticks.indexOf(tick) === index)
            .map((tick) => (
              <text
                key={tick}
                x={x(tick)}
                y={231}
                textAnchor="middle"
                fontSize={12}
                fill="#53645d"
              >
                {tick}
              </text>
            ))}
          <text
            x={340}
            y={257}
            textAnchor="middle"
            fontSize={12}
            fill="#53645d"
          >
            Published course day · available by this checkpoint
          </text>
          {rows.map((row) => (
            <g
              key={row.id}
              fill={colors[row.category]}
              stroke="white"
              strokeWidth={1.4}
            >
              <title>{`${row.assessment}: ${row.percent.toFixed(1)}%, ${names[row.category]}, published day ${row.published}`}</title>
              {row.category === "assessed" ? (
                <circle cx={x(row.published)} cy={y(row.percent)} r={5.5} />
              ) : row.category === "practice" ? (
                <rect
                  x={x(row.published) - 5}
                  y={y(row.percent) - 5}
                  width={10}
                  height={10}
                />
              ) : (
                <path
                  d={`M ${x(row.published)} ${y(row.percent) - 6} l 6 11 h -12 Z`}
                />
              )}
            </g>
          ))}
        </svg>
      </div>
      <div className="chart-legend">
        <span>● Assessed work</span>
        <span>■ Practice / formative</span>
        <span>▲ Unclassified</span>
      </div>
    </>
  );
}

function ActivityChart({ events }: { events: RecordBag[] }) {
  const id = useId();
  const counts = new Map<number, number>();
  events
    .filter(
      (event) => event.event_type === "activity" && finite(event.course_day),
    )
    .forEach((event) => {
      const week = Math.floor(Number(event.course_day) / 7) + 1;
      counts.set(week, (counts.get(week) ?? 0) + 1);
    });
  const rows = [...counts.entries()].sort((a, b) => a[0] - b[0]);
  if (!rows.length)
    return (
      <p className="empty">
        No recorded activity events at this checkpoint. Check coverage before
        interpreting inactivity.
      </p>
    );
  const largest = Math.max(...rows.map(([, count]) => count));
  const slot = 576 / rows.length;
  return (
    <>
      <div
        className="chart-scroll"
        tabIndex={0}
        role="region"
        aria-label="Recorded activity chart"
      >
        <svg
          className="evidence-chart"
          viewBox="0 0 660 248"
          role="img"
          aria-labelledby={id}
        >
          <title id={id}>
            Recorded activity events by course week. Counts are not study hours;
            omitted weeks have no event rows, not confirmed zero activity.
          </title>
          {[0, Math.ceil(largest / 2), largest]
            .filter((tick, index, ticks) => ticks.indexOf(tick) === index)
            .map((tick) => (
              <g key={tick}>
                <line
                  x1={52}
                  x2={628}
                  y1={190 - (tick / largest) * 155}
                  y2={190 - (tick / largest) * 155}
                  stroke="#e4e8e5"
                />
                <text
                  x={42}
                  y={194 - (tick / largest) * 155}
                  textAnchor="end"
                  fontSize={12}
                  fill="#53645d"
                >
                  {tick}
                </text>
              </g>
            ))}
          {rows.map(([week, count], index) => (
            <g key={week}>
              <rect
                x={52 + slot * index + slot * 0.2}
                y={190 - (count / largest) * 155}
                width={slot * 0.6}
                height={(count / largest) * 155}
                rx={3}
                fill="#427c71"
              >
                <title>{`Week ${week}: ${count} recorded events`}</title>
              </rect>
              <text
                x={52 + slot * (index + 0.5)}
                y={213}
                textAnchor="middle"
                fontSize={12}
                fill="#53645d"
              >
                {week}
              </text>
            </g>
          ))}
          <text
            x={340}
            y={240}
            textAnchor="middle"
            fontSize={12}
            fill="#53645d"
          >
            Course week · recorded activity events
          </text>
        </svg>
      </div>
      <details>
        <summary>Activity chart values</summary>
        <div
          className="table-scroll"
          tabIndex={0}
          role="region"
          aria-label="Recorded activity counts"
        >
          <table>
            <thead>
              <tr>
                <th>Week</th>
                <th>Recorded events</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([week, count]) => (
                <tr key={week}>
                  <td>{week}</td>
                  <td>{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </>
  );
}

function ResourceProgress({ data }: { data: LearnerDetail }) {
  const snapshot = data.snapshot;
  const features = snapshot?.features ?? {};
  const semantics = bag(bag(snapshot?.course_context).evidence_semantics);
  const verified =
    snapshot?.feature_version === "rich-features-v3" &&
    semantics.completion_basis === "required_resources_due_by_checkpoint";
  const expected = factNumber(features.resources_expected);
  const completed = factNumber(features.resources_completed);
  const validCount =
    expected !== null &&
    completed !== null &&
    expected >= 0 &&
    completed >= 0 &&
    completed <= expected;
  const fields = [
    "completion_percent",
    "optional_resources_available",
    "required_resources_not_due",
    "resources_expectation_unknown",
  ]
    .filter((key) => features[key])
    .map((key) => [key, features[key]] as [string, Fact]);
  return (
    <Panel
      title="Required learning resources"
      note="Only required resources due by the selected checkpoint belong in the completion denominator."
    >
      {!verified ? (
        <Notice>
          Historical completion data does not separate required, optional and
          not-yet-due resources. It is not used as required-work evidence by the
          current predictor.
        </Notice>
      ) : (
        <>
          {validCount ? (
            expected === 0 ? (
              <Notice>
                No required learning resources are due yet. There is no
                completion requirement to assess.
              </Notice>
            ) : (
              <>
                <h3>
                  {completed} of {expected} required resources completed
                </h3>
                <progress
                  className="completion-meter"
                  max={expected}
                  value={completed}
                  aria-label={`${completed} of ${expected} required resources completed`}
                />
              </>
            )
          ) : (
            <Notice>
              Required-resource completion is unavailable or inconsistent.
              Missing evidence does not mean the student failed to complete the
              work.
            </Notice>
          )}
          <FactTable entries={fields} title="Resource completion context" />
          <p className="fineprint">
            Optional resources and work not yet due do not lower required
            completion.
          </p>
        </>
      )}
    </Panel>
  );
}

export function AcademicRecords({ data }: { data: LearnerDetail }) {
  const [limit, setLimit] = useState(25);
  const snapshot = data.snapshot;
  const features = Object.entries(snapshot?.features ?? {});
  const semantics = bag(bag(snapshot?.course_context).evidence_semantics);
  const verified =
    snapshot?.feature_version === "rich-features-v3" &&
    semantics.grade_basis === "graded_assessments_only";
  const academic = features.filter(
    ([key]) =>
      !key.startsWith("practice_") &&
      /grade|assessment|submission|quiz|mastery|deadline|late|exam|assignment/.test(
        key,
      ),
  );
  const practice = features.filter(([key]) => key.startsWith("practice_"));
  const activity = features.filter(([key]) =>
    /active|activity|click|forum|attendance|session|engagement/.test(key),
  );
  const cutoff = snapshot?.cutoff_day;
  const events =
    cutoff == null
      ? []
      : data.events.filter(
          (event) =>
            finite(event.course_day) &&
            finite(event.available_day) &&
            event.course_day <= cutoff &&
            event.available_day <= cutoff,
        );
  const grades = gradeRows(data);
  const gradeEvents = events.filter(
    (event) => event.event_type === "assessment_grade",
  ).length;
  return (
    <>
      <Panel
        title="Grades and assessment progress"
        note="Published marks use a 0–100% grade scale. They are not risk scores."
      >
        {!verified && (
          <Notice>
            Grade-summary semantics are not verified for this snapshot.
            Historical summaries may mix assessed and practice work; use the
            classified records below rather than assuming a graded-work trend.
          </Notice>
        )}
        {verified && (
          <p className="fineprint">
            Assessed-grade summaries include positive-weight, non-practice
            assessments only.
          </p>
        )}
        {grades.length ? (
          <>
            <GradeChart rows={grades} cutoff={cutoff ?? 0} />
            <div
              className="table-scroll"
              role="region"
              aria-label="Published grade values"
              tabIndex={0}
            >
              <table>
                <thead>
                  <tr>
                    <th>Assessment</th>
                    <th>Published day</th>
                    <th>Grade</th>
                    <th>Evidence type</th>
                  </tr>
                </thead>
                <tbody>
                  {grades.map((row) => (
                    <tr key={row.id}>
                      <td>{row.assessment}</td>
                      <td>{row.published}</td>
                      <td>{row.percent.toFixed(1)}%</td>
                      <td>
                        <Badge
                          tone={
                            row.category === "assessed"
                              ? "sage"
                              : row.category === "practice"
                                ? "amber"
                                : "neutral"
                          }
                        >
                          {names[row.category]}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p className="empty">
            No valid published marks available by this checkpoint.
          </p>
        )}
        {gradeEvents > grades.length && (
          <Notice>
            {gradeEvents - grades.length} grade record(s) have missing or
            invalid marks and are not plotted. Inspect the source records below.
          </Notice>
        )}
        <p className="fineprint">
          Classification uses definitions available by this cutoff. Practice and
          unclassified work are not assessed-grade concerns. No later marks are
          included.
        </p>
        <details>
          <summary>All academic evidence ({academic.length})</summary>
          <FactTable entries={academic} title="Academic evidence" />
        </details>
      </Panel>
      {practice.length > 0 && (
        <Panel
          title="Practice and formative work"
          note="Learning context kept separate from assessed-grade risk evidence."
        >
          <FactTable entries={practice} title="Practice evidence" />
        </Panel>
      )}
      <ResourceProgress data={data} />
      <Panel
        title="Engagement and attendance"
        note="Activity events are observations, not hours studied or a judgment of learning quality."
      >
        <ActivityChart events={events} />
        <p className="fineprint">
          Weeks without event rows are omitted. Check source coverage before
          interpreting inactivity; an omitted week is not a confirmed zero.
        </p>
        <details>
          <summary>All activity evidence ({activity.length})</summary>
          <FactTable entries={activity} title="Activity evidence" />
        </details>
      </Panel>
      <Panel
        title="Source records through this checkpoint"
        note={`${events.length} records available by cutoff day ${cutoff ?? "unknown"}. Unknown, observed zero and not yet due remain distinct.`}
      >
        {!events.length ? (
          <p className="empty">No eligible source records available.</p>
        ) : (
          <>
            <div className="record-list">
              {events.slice(0, limit).map((event, index) => (
                <details key={String(event.event_id ?? index)}>
                  <summary>
                    Day {String(event.course_day)} ·{" "}
                    {label(String(event.event_type))} · available day{" "}
                    {String(event.available_day)}
                  </summary>
                  <pre>{JSON.stringify(event, null, 2)}</pre>
                </details>
              ))}
            </div>
            {limit < events.length && (
              <button onClick={() => setLimit((value) => value + 25)}>
                Show 25 more records ({Math.min(limit, events.length)} of{" "}
                {events.length} shown)
              </button>
            )}
          </>
        )}
      </Panel>
    </>
  );
}
