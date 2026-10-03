import type { ReactNode } from "react";
import { AlertCircle, ArrowUpRight, LoaderCircle } from "lucide-react";

export function label(value: string | null | undefined) {
  return value
    ? value.replaceAll("_", " ").replace(/\b\w/g, (x) => x.toUpperCase())
    : "Not available";
}
export function score(value: number | null | undefined) {
  return value == null ? "Not assessed" : `${(value * 100).toFixed(0)} / 100`;
}
export function band(value: string | null) {
  return (
    (
      {
        high: "High attention",
        medium: "Monitor",
        low: "Lower attention",
      } as Record<string, string>
    )[value ?? ""] ?? "Not assessed"
  );
}
export function Badge({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}
export function Panel({
  title,
  note,
  children,
  action,
}: {
  title: string;
  note?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {note && <p>{note}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Notice({
  children,
  error = false,
}: {
  children: ReactNode;
  error?: boolean;
}) {
  return (
    <div
      className={`notice ${error ? "error" : ""}`}
      role={error ? "alert" : undefined}
    >
      <AlertCircle size={19} />
      <div>{children}</div>
    </div>
  );
}
export function Loading() {
  return (
    <div className="loading" role="status">
      <LoaderCircle size={22} /> Loading saved course records…
    </div>
  );
}
export function Metric({
  title,
  value,
  note,
  tone = "",
  onClick,
}: {
  title: string;
  value: number;
  note: string;
  tone?: string;
  onClick: () => void;
}) {
  return (
    <button className={`metric ${tone}`} onClick={onClick}>
      <span className="metric-label">
        {title}
        <ArrowUpRight size={17} />
      </span>
      <strong>{value.toLocaleString()}</strong>
      <span className="metric-note">{note}</span>
    </button>
  );
}
