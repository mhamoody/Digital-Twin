import type { Course } from "./api/contracts";

// Only the explicitly versioned synthetic course family has replacement semantics.
// Equal titles alone never make two LMS offerings the same course.
function versionedFamily(course: Course) {
  if (course.data_origin !== "synthetic") return null;
  const match = /^(synthetic:[^:]+:[^:]+)(?::v([1-9]\d*))?$/.exec(course.presentation_id);
  if (!match) return null;
  const version = match[2] ? Number(match[2]) : 1;
  return Number.isSafeInteger(version) ? { id: match[1], version } : null;
}

export function courseChoices(courses: Course[]) {
  const unique = [...new Map(courses.map((course) => [course.presentation_id, course])).values()];
  const latest = new Map<string, Course>();
  for (const course of unique) {
    const family = versionedFamily(course);
    if (!family) continue;
    const previous = latest.get(family.id);
    if (!previous || family.version > versionedFamily(previous)!.version) {
      latest.set(family.id, course);
    }
  }
  const replacement = (course: Course) => {
    const family = versionedFamily(course);
    const newest = family ? latest.get(family.id) : undefined;
    return family && newest && versionedFamily(newest)!.version > family.version ? newest : course;
  };
  const earlier = unique.filter((course) => replacement(course).presentation_id !== course.presentation_id);
  const current = [...new Map(unique.map((course) => {
    const selected = replacement(course);
    return [selected.presentation_id, selected] as const;
  })).values()];
  const earlierIds = new Set(earlier.map((course) => course.presentation_id));
  const baseLabel = (course: Course) => {
    const title = course.title || course.presentation_id;
    if (earlierIds.has(course.presentation_id)) {
      const version = versionedFamily(course)!.version;
      return `${title} · ${version === 1 ? "original version" : `earlier version ${version}`}`;
    }
    return title;
  };
  const optionLabel = (course: Course) => {
    const label = baseLabel(course);
    const sameLabel = unique.filter((other) => baseLabel(other) === label);
    return sameLabel.length > 1 ? `${label} · ${course.presentation_id}` : label;
  };
  return { current, earlier, earlierIds, replacement, optionLabel };
}
