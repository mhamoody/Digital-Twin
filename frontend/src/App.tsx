import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { z } from "zod";
import {
  Activity,
  ArrowRight,
  BookOpen,
  HeartHandshake,
  LayoutDashboard,
  LogOut,
  Menu,
  RefreshCw,
  Settings2,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";
import { request } from "./api/client";
import { coursesSchema, sessionSchema, workspaceSchema } from "./api/contracts";
import type { Course, Privacy, Session, Workspace } from "./api/contracts";
import { useResource } from "./hooks/useResource";
import { Badge, label, Loading, Notice, Panel } from "./components/ui";
import { Overview } from "./pages/Overview";
import { initialFilters, StudentFilters, Students } from "./pages/Students";
import type { Filters } from "./pages/Students";
import { StudentProfile } from "./pages/StudentProfile";
import { EditGuard, useEditGuard } from "./hooks/editGuard";

type Page = "overview" | "students" | "support" | "settings" | "health";
const navigation = [
  { id: "overview", title: "Overview", icon: LayoutDashboard },
  { id: "students", title: "Students", icon: Users },
  { id: "support", title: "Support cases", icon: HeartHandshake },
  { id: "settings", title: "Course settings", icon: Settings2 },
  { id: "health", title: "Data & model", icon: Activity },
] as const;

export function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [ready, setReady] = useState(false);
  const [problem, setProblem] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request("browser/session", sessionSchema, { signal: controller.signal })
      .then(setSession)
      .catch((error) => {
        if (!controller.signal.aborted && error.status !== 401)
          setProblem(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setReady(true);
      });
    const expired = () => {
      setSession(null);
      setProblem("Your session ended. Please sign in again.");
    };
    window.addEventListener("session-ended", expired);
    return () => {
      controller.abort();
      window.removeEventListener("session-ended", expired);
    };
  }, []);
  if (!ready) return <Loading />;
  if (!session)
    return (
      <Login
        initialError={problem}
        signedIn={(s) => {
          setProblem("");
          setSession(s);
        }}
      />
    );
  return (
    <EditGuard>
      <WorkspaceApp
        session={session}
        signedOut={() => {
          setSession(null);
          setProblem("");
        }}
      />
    </EditGuard>
  );
}

function Login({
  signedIn,
  initialError,
}: {
  signedIn: (s: Session) => void;
  initialError: string;
}) {
  const [error, setError] = useState(initialError);
  const [busy, setBusy] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    setBusy(true);
    setError("");
    try {
      const session = await request("browser/login", sessionSchema, {
        body: {
          username: values.get("username"),
          password: values.get("password"),
        },
      });
      form.reset();
      signedIn(session);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to sign in.");
    } finally {
      setBusy(false);
    }
  }
  return (
    <main className="login-page">
      <section className="login-story">
        <div className="brand">
          <BookOpen size={28} />
          Course Twin
        </div>
        <Badge>Instructor workspace</Badge>
        <h1>
          See the evidence.
          <br />
          Support the student.
        </h1>
        <p>
          A clearer view of your course, with traceable insights and the final
          decision in your hands.
        </p>
        <div className="login-motif" aria-hidden="true">
          <div>
            <span>01</span>Understand the context
          </div>
          <div>
            <span>02</span>Review the evidence
          </div>
          <div>
            <span>03</span>Record human support
          </div>
        </div>
        <small>React migration · local instructor-workflow preview</small>
      </section>
      <section className="login-form">
        <ShieldCheck size={30} />
        <h2>Welcome back</h2>
        <p>Sign in with your instructor pilot account.</p>
        <form onSubmit={submit}>
          <label>
            Username
            <input
              name="username"
              autoComplete="username"
              required
              maxLength={64}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              autoComplete="current-password"
              required
              maxLength={512}
            />
          </label>
          {error && <Notice error>{error}</Notice>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
            <ArrowRight size={18} />
          </button>
        </form>
        <small>
          Access is limited to your assigned courses. No institutional LMS
          sign-in is claimed in this pilot.
        </small>
      </section>
    </main>
  );
}

function WorkspaceApp({
  session,
  signedOut,
}: {
  session: Session;
  signedOut: () => void;
}) {
  const guard = useEditGuard();
  const [revision, setRevision] = useState(0);
  const { data: courses, error } = useResource(
    "v2/courses",
    coursesSchema,
    revision,
  );
  const [courseId, setCourseId] = useState("");
  const [selectedWeek, setWeek] = useState<number | null>(null);
  const [privacy, setPrivacy] = useState<Privacy>("name_id");
  const [page, setPage] = useState<Page>("overview");
  const [student, setStudent] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [menu, setMenu] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const course =
    courses?.items.find((c) => c.presentation_id === courseId) ??
    courses?.items[0];
  const week =
    selectedWeek !== null && course?.checkpoints.includes(selectedWeek)
      ? selectedWeek
      : Math.max(...(course?.checkpoints ?? [0]));
  function navigate(value: Page) {
    if (!guard.leave()) return;
    setPage(value);
    setStudent(null);
    setMenu(false);
    window.history.pushState(null, "", `#${value}`);
  }
  useEffect(() => {
    const change = () => {
      const value = window.location.hash.slice(1) || "overview";
      if (navigation.some((n) => n.id === value)) {
        if (!guard.leave()) {
          window.history.replaceState(null, "", `#${page}`);
          return;
        }
        setPage(value as Page);
        setStudent(null);
      }
    };
    if (window.location.hash.slice(1) !== page) change();
    window.addEventListener("hashchange", change);
    return () => {
      window.removeEventListener("hashchange", change);
    };
  }, [guard, page]);
  useEffect(() => {
    if (menu) dialog.current?.showModal();
    else dialog.current?.close();
  }, [menu]);
  useEffect(() => {
    document.getElementById("main-content")?.focus({ preventScroll: true });
  }, [page, student]);
  async function logout() {
    if (!guard.leave()) return;
    try {
      await request("browser/logout", z.object({ signed_out: z.boolean() }), {
        body: {},
        csrf: session.csrf_token,
      });
      signedOut();
    } catch (e) {
      setLogoutError(
        e instanceof Error ? e.message : "Sign-out failed. Try again.",
      );
    }
  }
  const nav = (
    <>
      <div className="brand">
        <BookOpen size={25} />
        Course Twin
      </div>
      <span className="nav-kicker">TEACHING WORKSPACE</span>
      <nav aria-label="Main navigation">
        {navigation.map((item) => (
          <button
            key={item.id}
            className={page === item.id ? "active" : ""}
            aria-current={page === item.id ? "page" : undefined}
            onClick={() => navigate(item.id)}
          >
            <item.icon size={19} />
            {item.title}
          </button>
        ))}
      </nav>
      <div className="nav-bottom">
        <div className="rail-note">
          <ShieldCheck size={25} />
          <p>
            Evidence first.
            <br />
            Instructor in control.
          </p>
        </div>
        <button onClick={logout}>
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </>
  );
  function openList(filter = "") {
    setFilters({
      ...initialFilters,
      attention: filter === "high" ? "" : filter,
      risk: filter === "high" ? "high" : "",
    });
    navigate(filter === "active_cases" ? "support" : "students");
  }
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      <aside className="sidebar">{nav}</aside>
      <dialog
        className="mobile-navigation"
        ref={dialog}
        onCancel={() => setMenu(false)}
        onClose={() => {
          setMenu(false);
          menuButton.current?.focus();
        }}
      >
        <button
          className="mobile-close"
          onClick={() => setMenu(false)}
          aria-label="Close navigation"
        >
          <X size={22} />
        </button>
        {menu && nav}
      </dialog>
      <div className="workspace-shell">
        <header className="topbar">
          <button
            ref={menuButton}
            className="mobile-menu icon-button"
            aria-label="Open navigation"
            aria-expanded={menu}
            onClick={() => setMenu(true)}
          >
            <Menu size={23} />
          </button>
          <div className="breadcrumbs">
            Instructor workspace <span>/</span>
            <strong>{navigation.find((n) => n.id === page)?.title}</strong>
          </div>
          <div className="account">
            <span className="avatar">
              {session.user.display_name.slice(0, 1)}
            </span>
            <div>
              <strong>{session.user.display_name}</strong>
              <small>{label(session.user.role)}</small>
            </div>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <div className="migration-banner">
            <span>REACT PREVIEW</span> Instructor markers and support records
            now save to the selected database. Course-policy editing and model
            controls remain in Streamlit until their migration gates pass.
          </div>
          {logoutError && <Notice error>{logoutError}</Notice>}
          {error ? (
            <Notice error>{error}</Notice>
          ) : !courses ? (
            <Loading />
          ) : !course ? (
            <Notice>No prepared courses are assigned to this account.</Notice>
          ) : (
            <>
              <div className="page-heading">
                <div>
                  <p className="eyebrow">YOUR COURSE, IN CONTEXT</p>
                  <h1>
                    {student
                      ? "Student profile"
                      : navigation.find((n) => n.id === page)?.title}
                  </h1>
                  <p>Understand what changed. Decide who needs support.</p>
                </div>
                <button
                  onClick={() => {
                    if (guard.leave()) setRevision((v) => v + 1);
                  }}
                  title="Reload saved data. Does not import records or rerun the model."
                >
                  <RefreshCw size={16} />
                  Refresh data
                </button>
              </div>
              <div className="context-bar">
                <label className="course-select">
                  Course
                  <select
                    aria-label="Course"
                    value={course.presentation_id}
                    onChange={(e) => {
                      if (!guard.leave()) return;
                      setCourseId(e.target.value);
                      setWeek(null);
                      setStudent(null);
                      setFilters(initialFilters);
                    }}
                  >
                    {courses.items.map((c) => (
                      <option key={c.presentation_id} value={c.presentation_id}>
                        {c.title ?? c.presentation_id}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Checkpoint
                  <select
                    aria-label="Checkpoint"
                    value={week}
                    onChange={(e) => {
                      if (!guard.leave()) return;
                      setWeek(Number(e.target.value));
                      setFilters({ ...filters, offset: 0 });
                    }}
                  >
                    {course.checkpoints.map((w) => (
                      <option key={w} value={w}>
                        Week {w}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Student identity
                  <select
                    aria-label="Student identity"
                    value={privacy}
                    onChange={(e) => {
                      if (!guard.leave()) return;
                      setPrivacy(e.target.value as Privacy);
                      setFilters({ ...filters, query: "", offset: 0 });
                    }}
                  >
                    <option value="name_id">Name + ID</option>
                    <option value="id_only">ID only</option>
                  </select>
                </label>
              </div>
              <div className="course-caption">
                <strong>{course.title ?? course.presentation_id}</strong>
                <span>{course.presentation_id}</span>
                <Badge tone="lilac">{label(course.data_origin)} data</Badge>
                <span>Evidence through day {week * 7 - 1}</span>
              </div>
              {["synthetic", "manual_test"].includes(course.data_origin) && (
                <p className="fineprint">
                  Demonstration course: fictional students and records. These
                  results are not evidence of predictive accuracy.
                </p>
              )}
              {privacy === "id_only" && (
                <Notice>
                  ID-only view uses server-side identity filtering and ID
                  search. Free-text instructor notes may still identify a
                  student.
                </Notice>
              )}
              {!course.checkpoints.length ? (
                <Notice>No prepared checkpoints for this course.</Notice>
              ) : student ? (
                <StudentProfile
                  key={`${course.presentation_id}|${student}|${privacy}|${week}`}
                  course={course.presentation_id}
                  id={student}
                  week={week}
                  privacy={privacy}
                  revision={revision}
                  csrf={session.csrf_token}
                  back={() => {
                    if (guard.leave()) setStudent(null);
                  }}
                />
              ) : (
                <CoursePage
                  course={course}
                  week={week}
                  privacy={privacy}
                  revision={revision}
                  page={page}
                  filters={filters}
                  setFilters={setFilters}
                  openList={openList}
                  openStudent={setStudent}
                />
              )}
            </>
          )}
          <footer className="workspace-footer">
            <span>Course Twin · Evidence-grounded instructor support</span>
            <span>Local migration · no automated student contact</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

function CoursePage({
  course,
  week,
  privacy,
  revision,
  page,
  filters,
  setFilters,
  openList,
  openStudent,
}: {
  course: Course;
  week: number;
  privacy: Privacy;
  revision: number;
  page: Page;
  filters: Filters;
  setFilters: (v: Filters) => void;
  openList: (filter?: string) => void;
  openStudent: (id: string) => void;
}) {
  const isList = page === "students" || page === "support";
  const params = new URLSearchParams({
    week: String(week),
    privacy,
    support_scope: "current",
    limit: "25",
    offset: isList ? String(filters.offset) : "0",
  });
  if (isList) {
    params.set("query", filters.query);
    params.set("risk", filters.risk);
    params.set("status", filters.status);
    params.set("sort", filters.sort);
    params.set("priority", filters.priority);
    if (filters.attention) params.set(filters.attention, "true");
  }
  const closedCases =
    page === "support" && ["resolved", "dismissed"].includes(filters.status);
  if (page === "support") {
    if (closedCases) params.delete("active_cases");
    else params.set("active_cases", "true");
  }
  const { data, error } = useResource(
    `v2/courses/${encodeURIComponent(course.presentation_id)}/workspace?${params}`,
    workspaceSchema,
    revision,
  );
  let content: ReactNode;
  if (error) content = <Notice error>{error}</Notice>;
  else if (!data) content = <Loading />;
  else if (isList)
    content = (
      <Students
        data={data}
        filters={filters}
        setFilters={setFilters}
        open={openStudent}
      />
    );
  else if (page === "overview")
    content = (
      <Overview data={data} openList={openList} openStudent={openStudent} />
    );
  else if (page === "settings") content = <PolicyView data={data} />;
  else content = <HealthView data={data} />;
  return (
    <>
      {isList && (
        <>
          <StudentFilters
            filters={filters}
            setFilters={setFilters}
            idOnly={privacy === "id_only"}
          />
          {page === "support" && (
            <p className="fineprint">
              {closedCases
                ? `Showing ${filters.status} support cases.`
                : "Active support cases: new, reviewed and ongoing."}{" "}
              Choose Resolved or Dismissed in the status filter to inspect
              closed records.
            </p>
          )}
          <p className="fineprint">
            Risk scores are uncalibrated indicators, not probabilities.
            Selecting a student does not mark them reviewed.
          </p>
        </>
      )}
      {content}
    </>
  );
}

function PolicyView({ data }: { data: Workspace }) {
  const p = data.policy;
  return (
    <>
      <Notice>
        Current saved policy, revision {p.version}. Editing and preset selection
        remain in Streamlit until the policy migration gate passes.
      </Notice>
      <Panel
        title="What counts as concerning in this course?"
        note="Course expectations are configurable, not a permanently fixed seven-day rule."
      >
        <dl className="settings-grid">
          <dt>Learning mode</dt>
          <dd>{label(p.learning_mode)}</dd>
          <dt>Inactivity monitoring</dt>
          <dd>
            {p.inactivity_monitoring_enabled
              ? "Enabled"
              : "Disabled — offline or milestone-based work is allowed"}
          </dd>
          <dt>Warning / escalation</dt>
          <dd>
            {p.inactivity_warning_days} / {p.inactivity_high_days} {p.day_basis}{" "}
            days
            {!p.inactivity_monitoring_enabled &&
              " (not applied while monitoring is disabled)"}
          </dd>
          <dt>Teaching weekdays</dt>
          <dd>
            {p.teaching_weekdays
              .map((i) => ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][i])
              .join(", ")}
          </dd>
          <dt>Breaks</dt>
          <dd>
            {p.break_ranges
              .map(([a, b]) => `Course days ${a}–${b}`)
              .join("; ") || "No configured breaks"}
          </dd>
          <dt>Academic corroboration</dt>
          <dd>
            {p.require_academic_corroboration ? "Required" : "Not required"}
          </dd>
          <dt>Low-grade reference</dt>
          <dd>{p.low_grade_percent}%</dd>
        </dl>
        <p className="fineprint">
          Policy changes retain historical assessments. Results must be
          reassessed before being presented as current under a new revision.
        </p>
      </Panel>
    </>
  );
}
function HealthView({ data }: { data: Workspace }) {
  return (
    <>
      <Panel
        title="Checkpoint data & analysis"
        note="Counts are unique students at the selected checkpoint, not the course-wide job queue."
      >
        <div className="health-grid">
          {[
            ["Not analyzed / outdated", data.summary.not_run],
            ["Queued / running", data.summary.queued],
            ["Failed analysis", data.summary.failed],
            ["Insufficient evidence", data.summary.insufficient_data],
          ].map(([name, value]) => (
            <div key={name}>
              <small>{name}</small>
              <strong>{value}</strong>
            </div>
          ))}
        </div>
      </Panel>
      <Panel
        title="Saved result sources"
        note="A temporary baseline is not an LLM result. Model versions are kept visible."
      >
        <dl className="settings-grid">
          {Object.entries(data.model_counts).map(([name, count]) => (
            <div key={name}>
              <dt>{name}</dt>
              <dd>{count} students</dd>
            </div>
          ))}
        </dl>
      </Panel>
      <Notice>
        Course-wide queue controls, live model/worker readiness and detailed
        failure diagnostics remain available in Streamlit. They will be migrated
        together; this view does not resume, retry or start inference.
      </Notice>
    </>
  );
}
