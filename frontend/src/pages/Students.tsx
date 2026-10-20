import { useEffect } from "react";
import {
  Bookmark,
  Flag,
  Search,
  ChevronLeft,
  ChevronRight,
  ArrowRight,
} from "lucide-react";
import type { LearnerRow, Workspace } from "../api/contracts";
import { Badge, band, label, score } from "../components/ui";

export type Filters = {
  query: string;
  attention: string;
  risk: string;
  status: string;
  sort: string;
  priority: string;
  offset: number;
  dueOnly: boolean;
  activeOnly: boolean;
  includeClosed: boolean;
};
export const initialFilters: Filters = {
  query: "",
  attention: "",
  risk: "",
  status: "",
  sort: "attention",
  priority: "",
  offset: 0,
  dueOnly: false,
  activeOnly: false,
  includeClosed: false,
};

export function StudentFilters({
  filters,
  setFilters,
  idOnly,
  casesOnly = false,
}: {
  filters: Filters;
  setFilters: (v: Filters) => void;
  idOnly: boolean;
  casesOnly?: boolean;
}) {
  function update(key: keyof Filters, value: string) {
    const closed =
      key === "status" && ["resolved", "dismissed"].includes(value);
    setFilters({
      ...filters,
      [key]: value,
      offset: 0,
      ...(closed
        ? {
            activeOnly: false,
            attention:
              filters.attention === "active_cases" ? "" : filters.attention,
          }
        : {}),
    });
  }
  return (
    <div className="filters">
      <label className="search-field">
        <Search size={18} />
        <span className="sr-only">Find student</span>
        <input
          placeholder={
            idOnly ? "Search by student ID" : "Search by name or student ID"
          }
          value={filters.query}
          onChange={(e) => update("query", e.target.value)}
          maxLength={128}
        />
      </label>
      <label>
        Attention
        <select
          aria-label="Attention"
          value={filters.attention}
          onChange={(e) => update("attention", e.target.value)}
        >
          <option value="">Everyone</option>
          {[
            "needs_review",
            "flagged",
            "watchlist",
            "due",
            "insufficient_data",
            "active_cases",
          ].map((v) => (
            <option key={v} value={v}>
              {label(v)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Support level
        <select
          aria-label="Support level"
          value={filters.risk}
          onChange={(e) => update("risk", e.target.value)}
        >
          <option value="">All levels</option>
          {["high", "medium", "low", "unavailable"].map((v) => (
            <option key={v} value={v}>
              {band(v)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Case / analysis status
        <select
          aria-label="Case / analysis status"
          value={filters.status}
          onChange={(e) => update("status", e.target.value)}
        >
          <option value="">All statuses</option>
          {[
            "new",
            "ongoing",
            "reviewed",
            "resolved",
            "dismissed",
            "validated",
            "abstained",
            "not_run",
            "queued",
            "running",
            "failed",
            "outdated",
          ].map((v) => (
            <option key={v} value={v}>
              {label(v)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Instructor priority
        <select
          aria-label="Instructor priority"
          value={filters.priority}
          onChange={(e) => update("priority", e.target.value)}
        >
          <option value="">All priorities</option>
          {["low", "normal", "high", "urgent"].map((v) => (
            <option key={v}>{v}</option>
          ))}
        </select>
      </label>
      <label>
        Sort by
        <select
          aria-label="Sort by"
          value={filters.sort}
          onChange={(e) => update("sort", e.target.value)}
        >
          {[
            "attention",
            "risk_desc",
            "risk_asc",
            "name",
            "learner_id",
            "follow_up",
            "priority",
          ].map((v) => (
            <option key={v} value={v}>
              {label(v)}
            </option>
          ))}
        </select>
      </label>
      <label className="check-field">
        <input
          type="checkbox"
          checked={filters.dueOnly}
          onChange={(e) =>
            setFilters({ ...filters, dueOnly: e.target.checked, offset: 0 })
          }
        />
        Follow-up due only
      </label>
      {casesOnly ? (
        <label className="check-field">
          <input
            type="checkbox"
            checked={filters.includeClosed}
            onChange={(e) =>
              setFilters({
                ...filters,
                includeClosed: e.target.checked,
                offset: 0,
              })
            }
          />
          Include students without an active case
        </label>
      ) : (
        <label className="check-field">
          <input
            type="checkbox"
            checked={filters.activeOnly}
            disabled={["resolved", "dismissed"].includes(filters.status)}
            onChange={(e) =>
              setFilters({
                ...filters,
                activeOnly: e.target.checked,
                offset: 0,
              })
            }
          />
          Active cases only
        </label>
      )}
      <button
        className="text-button"
        onClick={() => setFilters(initialFilters)}
      >
        Clear filters
      </button>
    </div>
  );
}

export function Students({
  data,
  filters,
  setFilters,
  open,
}: {
  data: Workspace;
  filters: Filters;
  setFilters: (v: Filters) => void;
  open: (id: string) => void;
}) {
  const lastOffset = Math.max(0, Math.floor((data.total - 1) / 25) * 25);
  const beyondLastPage = filters.offset > lastOffset;
  useEffect(() => {
    if (beyondLastPage) setFilters({ ...filters, offset: lastOffset });
  }, [beyondLastPage, lastOffset, filters, setFilters]);
  if (beyondLastPage)
    return (
      <p role="status">The list changed. Loading the last available page…</p>
    );
  return (
    <section className="panel roster-panel">
      <div className="panel-heading">
        <div>
          <h2>{data.total.toLocaleString()} matching students</h2>
          <p>Evidence: week {data.week} · support cases: current records</p>
        </div>
        <Badge>Open a profile to record support</Badge>
      </div>
      <div
        className="table-scroll"
        role="region"
        aria-label="Student roster, scroll horizontally for all columns"
        tabIndex={0}
      >
        <table>
          <thead>
            <tr>
              <th>Student</th>
              <th>Support level</th>
              <th>Risk score</th>
              <th>Previous → current</th>
              <th>Case / follow-up</th>
              <th>Analysis</th>
              <th>
                <span className="sr-only">Open profile</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((student) => (
              <Row key={student.learner_id} student={student} open={open} />
            ))}
          </tbody>
        </table>
      </div>
      {!data.items.length && (
        <div className="empty">
          <h3>No matching students</h3>
          <p>Try clearing a filter or changing the checkpoint.</p>
        </div>
      )}
      <div className="pagination">
        <span>
          {data.total ? filters.offset + 1 : 0}–
          {Math.min(filters.offset + 25, data.total)} of {data.total}
        </span>
        <div>
          <button
            disabled={filters.offset === 0}
            onClick={() =>
              setFilters({
                ...filters,
                offset: Math.max(0, filters.offset - 25),
              })
            }
          >
            <ChevronLeft size={16} /> Previous
          </button>
          <button
            disabled={filters.offset + 25 >= data.total}
            onClick={() =>
              setFilters({ ...filters, offset: filters.offset + 25 })
            }
          >
            Next <ChevronRight size={16} />
          </button>
        </div>
      </div>
    </section>
  );
}
function Row({
  student: s,
  open,
}: {
  student: LearnerRow;
  open: (id: string) => void;
}) {
  return (
    <tr>
      <td>
        <button className="student-link" onClick={() => open(s.learner_id)}>
          <strong>{s.display_name}</strong>
          <small>{s.learner_id}</small>
        </button>
        <div className="markers">
          {s.triage.flagged && (
            <span>
              <Flag size={12} /> Flagged
            </span>
          )}
          {s.triage.watchlisted && (
            <span>
              <Bookmark size={12} /> Watchlist
            </span>
          )}
          {s.triage.priority !== "normal" && (
            <span>{label(s.triage.priority)} priority</span>
          )}
        </div>
      </td>
      <td>
        <Badge
          tone={
            s.risk_band === "high"
              ? "coral"
              : s.risk_band === "medium"
                ? "amber"
                : s.risk_band === "low"
                  ? "sage"
                  : "neutral"
          }
        >
          {band(s.risk_band)}
        </Badge>
      </td>
      <td className="numeric">{score(s.risk_score)}</td>
      <td>
        {s.comparable && s.previous_score != null && s.risk_score != null
          ? `${(s.previous_score * 100).toFixed(0)} → ${(s.risk_score * 100).toFixed(0)}`
          : "No valid comparison"}
      </td>
      <td>
        <span>{s.case_status ? label(s.case_status) : "No case"}</span>
        {s.follow_up_day != null && (
          <small className={s.due ? "due" : ""}>
            Day {s.follow_up_day}
            {s.due ? " · due" : ""}
          </small>
        )}
      </td>
      <td>
        {label(s.analysis_status)}
        <small>{s.model_version ?? "No saved model result"}</small>
      </td>
      <td>
        <button
          className="icon-button"
          onClick={() => open(s.learner_id)}
          aria-label={`Open student ${s.display_name}`}
        >
          <ArrowRight size={18} />
        </button>
      </td>
    </tr>
  );
}
