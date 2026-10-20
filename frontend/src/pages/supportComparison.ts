import type { LearnerDetail } from "../api/contracts";

type State = LearnerDetail["snapshot_history"][number];
function basis(state: State, key: string) {
  const semantics = state.course_context?.evidence_semantics;
  return semantics && typeof semantics === "object" && key in semantics
    ? (semantics as Record<string, unknown>)[key]
    : null;
}
export function observedDelta(
  before: State,
  after: State,
  key: string,
): number | null {
  const a = before.features[key],
    b = after.features[key];
  if (
    !before.feature_version ||
    before.feature_version !== after.feature_version
  )
    return null;
  if (
    key === "weighted_grade_percent" &&
    (basis(before, "grade_basis") !== "graded_assessments_only" ||
      basis(after, "grade_basis") !== "graded_assessments_only")
  )
    return null;
  if (
    key === "completion_percent" &&
    (basis(before, "completion_basis") !==
      "required_resources_due_by_checkpoint" ||
      basis(after, "completion_basis") !==
        "required_resources_due_by_checkpoint")
  )
    return null;
  return typeof a?.value === "number" &&
    typeof b?.value === "number" &&
    ["observed", "structural_zero"].includes(a.status) &&
    ["observed", "structural_zero"].includes(b.status) &&
    a.unit === b.unit &&
    a.window === b.window
    ? b.value - a.value
    : null;
}
