import { useId } from "react";
import type { LearnerDetail } from "../api/contracts";
import { band, Notice, Panel } from "../components/ui";

const preciseScore = (value: number | null) =>
  value == null ? "Not assessed" : `${Number((value * 100).toFixed(6))} / 100`;

type History = LearnerDetail["history"][number];
const provenance = [
  "model_digest",
  "prompt_version",
  "feature_version",
  "calibration_version",
] as const;
const validScore = (row: History) =>
  row.risk_score !== null &&
  Number.isFinite(row.risk_score) &&
  row.risk_score >= 0 &&
  row.risk_score <= 1;
function comparable(a: History, b: History) {
  // Unknown revisions do not prove comparability. Never bridge a missing week/result.
  const baseline = /^(rules-baseline|simple-rules)-/.test(a.model_version);
  const matchingVersion = (key: (typeof provenance)[number]) => {
    if (a[key] === null && b[key] === null)
      return (
        key === "calibration_version" ||
        (baseline && ["model_digest", "prompt_version"].includes(key))
      );
    return (
      typeof a[key] === "string" && a[key]!.length > 0 && a[key] === b[key]
    );
  };
  return (
    b.checkpoint_week === a.checkpoint_week + 1 &&
    a.model_version === b.model_version &&
    a.policy_version === b.policy_version &&
    provenance.every(matchingVersion)
  );
}

export function RiskHistory({ data }: { data: LearnerDetail }) {
  const id = useId();
  const rows = [...data.history].sort(
    (a, b) => a.checkpoint_week - b.checkpoint_week,
  );
  const points = rows.filter(validScore);
  const maxWeek = Math.max(
    1,
    data.snapshot?.checkpoint_week ?? 1,
    ...rows.map((row) => row.checkpoint_week),
  );
  const x = (week: number) =>
    52 + ((week - 1) / Math.max(1, maxWeek - 1)) * 576;
  const y = (value: number) => 208 - value * 172;
  const links = rows.flatMap((row, index) =>
    index > 0 &&
    validScore(row) &&
    validScore(rows[index - 1]) &&
    comparable(rows[index - 1], row)
      ? [[rows[index - 1], row]]
      : [],
  );
  const ticks = [
    ...new Set([1, Math.max(1, Math.round(maxWeek / 2)), maxWeek]),
  ];
  return (
    <Panel
      title="Saved risk-score history"
      note="Historical results on a fixed 0–100 risk-score scale. Uncalibrated scores are not probabilities."
    >
      {!rows.length ? (
        <p className="empty">
          No saved model results. Missing points are not zero.
        </p>
      ) : (
        <>
          {points.length > 0 && (
            <div
              className="chart-scroll"
              tabIndex={0}
              role="region"
              aria-label="Risk-score chart; exact values follow"
            >
              <svg
                className="evidence-chart"
                viewBox="0 0 660 265"
                role="img"
                aria-labelledby={id}
              >
                <title id={id}>
                  Historical risk scores. Lines connect adjacent weeks only when
                  model, policy and all version metadata match. Exact values and
                  versions are in the table below.
                </title>
                {[0, 25, 50, 75, 100].map((tick) => (
                  <g key={tick}>
                    <line
                      x1={52}
                      x2={628}
                      y1={y(tick / 100)}
                      y2={y(tick / 100)}
                      stroke="#e4e8e5"
                    />
                    <text
                      x={42}
                      y={y(tick / 100) + 4}
                      textAnchor="end"
                      fontSize={12}
                      fill="#53645d"
                    >
                      {tick}
                    </text>
                  </g>
                ))}
                {links.map(([a, b]) => (
                  <line
                    key={`${a.checkpoint_week}-${b.checkpoint_week}`}
                    x1={x(a.checkpoint_week)}
                    x2={x(b.checkpoint_week)}
                    y1={y(a.risk_score!)}
                    y2={y(b.risk_score!)}
                    stroke="#267769"
                    strokeWidth={2}
                  />
                ))}
                {points.map((row) => (
                  <circle
                    key={row.checkpoint_week}
                    cx={x(row.checkpoint_week)}
                    cy={y(row.risk_score!)}
                    r={5.5}
                    fill={
                      /rules|baseline/i.test(row.model_version)
                        ? "#9b6419"
                        : "#267769"
                    }
                    stroke="white"
                    strokeWidth={1.5}
                  >
                    <title>{`Week ${row.checkpoint_week}: ${preciseScore(row.risk_score)} · ${row.model_version} · policy ${row.policy_version}`}</title>
                  </circle>
                ))}
                {ticks.map((tick) => (
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
                  Checkpoint week · risk score 0–100
                </text>
              </svg>
            </div>
          )}
          <Notice>
            Only adjacent weeks with matching model, policy, model digest,
            prompt, feature and calibration versions are connected. Gaps,
            abstentions and missing versions break the line. Explicitly
            uncalibrated results may match; a rules baseline has no LLM prompt.
            A lower risk score does not prove that an intervention caused
            improvement.
          </Notice>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Risk-score history and provenance"
          >
            <table>
              <thead>
                <tr>
                  <th>Week</th>
                  <th>Risk score</th>
                  <th>Support level</th>
                  <th>Model</th>
                  <th>Policy</th>
                  <th>Version details</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.checkpoint_week}>
                    <td>{row.checkpoint_week}</td>
                    <td>
                      {validScore(row)
                        ? preciseScore(row.risk_score)
                        : "No published risk score"}
                    </td>
                    <td>
                      {validScore(row) ? band(row.risk_band) : "Not assessed"}
                    </td>
                    <td>
                      {row.model_version}
                      {/rules|baseline/i.test(row.model_version) && (
                        <small> · temporary rules baseline</small>
                      )}
                    </td>
                    <td>Revision {row.policy_version}</td>
                    <td>
                      <details>
                        <summary>Inspect versions</summary>
                        <dl className="key-values">
                          <dt>Stored risk score · 0–1 scale</dt>
                          <dd>
                            {row.risk_score === null
                              ? "No published risk score"
                              : String(row.risk_score)}
                          </dd>
                          {provenance.map((key) => (
                            <div key={key}>
                              <dt>{key.replaceAll("_", " ")}</dt>
                              <dd>
                                {row[key] ??
                                  "Not recorded · comparison unavailable"}
                              </dd>
                            </div>
                          ))}
                        </dl>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="fineprint">
            These are saved historical assessments, not a claim that every
            result is current. The Evidence tab shows the selected checkpoint’s
            current validation and freshness status.
          </p>
        </>
      )}
    </Panel>
  );
}
