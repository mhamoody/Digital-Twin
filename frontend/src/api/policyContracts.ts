import { z } from "zod";

export const learningModeLabels = {
  custom: "Custom expectations",
  regular_online: "Regular online activity",
  weekly: "Weekly work",
  fortnightly: "Fortnightly work",
  milestone: "Milestone-based work",
  mainly_offline: "Mainly offline",
} as const;
export type LearningMode = keyof typeof learningModeLabels;
export const teachingWeekdays = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];

// Mirrors CoursePolicy, including cross-field constraints. This validates the
// editor and the save response; no coercion silently changes instructor input.
export const editablePolicySchema = z
  .object({
    version: z.number().int().min(1),
    learning_mode: z.enum([
      "custom",
      "regular_online",
      "weekly",
      "fortnightly",
      "milestone",
      "mainly_offline",
    ]),
    inactivity_monitoring_enabled: z.boolean(),
    inactivity_warning_days: z.number().int().min(1).max(120),
    inactivity_high_days: z.number().int().min(2).max(180),
    day_basis: z.enum(["calendar", "teaching"]),
    teaching_weekdays: z.array(z.number().int().min(0).max(6)).min(1),
    break_ranges: z.array(
      z.tuple([
        z.number().int().min(0).max(420),
        z.number().int().min(0).max(420),
      ]),
    ),
    require_academic_corroboration: z.boolean(),
    low_grade_percent: z.number().min(0).max(100),
  })
  .strict()
  .superRefine((p, ctx) => {
    if (p.inactivity_high_days <= p.inactivity_warning_days)
      ctx.addIssue({
        code: "custom",
        path: ["inactivity_high_days"],
        message: "Escalation must be later than the warning threshold.",
      });
    if (new Set(p.teaching_weekdays).size !== p.teaching_weekdays.length)
      ctx.addIssue({
        code: "custom",
        path: ["teaching_weekdays"],
        message: "Teaching weekdays must be unique.",
      });
    if (p.break_ranges.some(([start, end]) => end < start))
      ctx.addIssue({
        code: "custom",
        path: ["break_ranges"],
        message: "Each break must end on or after its start day.",
      });
  });
export type EditablePolicy = z.infer<typeof editablePolicySchema>;
export const policySaveSchema = z.object({ policy: editablePolicySchema });

export function presetPolicy(
  mode: LearningMode,
  current: EditablePolicy,
): EditablePolicy {
  const next = { ...current, learning_mode: mode };
  const thresholds = {
    regular_online: [3, 7],
    weekly: [7, 14],
    fortnightly: [14, 28],
  } as const;
  if (mode in thresholds) {
    const [warning, escalation] = thresholds[mode as keyof typeof thresholds];
    next.inactivity_monitoring_enabled = true;
    next.inactivity_warning_days = warning;
    next.inactivity_high_days = escalation;
  } else if (mode === "milestone" || mode === "mainly_offline")
    next.inactivity_monitoring_enabled = false;
  return editablePolicySchema.parse(next);
}

export function parseBreakRanges(text: string): [number, number][] {
  return text
    .split(/\r?\n/)
    .filter((line) => line.trim())
    .map((line) => {
      const match = /^\s*(\d+)\s*-\s*(\d+)\s*$/.exec(line);
      if (!match)
        throw new Error(
          "Enter one break per line as start-end, for example 28-34. Course day 0 is the course start.",
        );
      const start = Number(match[1]);
      const end = Number(match[2]);
      if (end < start || end > 420)
        throw new Error(
          "Breaks must be inclusive course-day ranges from 0 to 420, with the end on or after the start.",
        );
      return [start, end];
    });
}

export function policyValue(
  policy: EditablePolicy,
  key: keyof EditablePolicy,
): string {
  const value = policy[key];
  if (key === "learning_mode") return learningModeLabels[policy.learning_mode];
  if (key === "teaching_weekdays")
    return policy.teaching_weekdays
      .map((day) => teachingWeekdays[day])
      .join(", ");
  if (key === "break_ranges")
    return (
      policy.break_ranges.map(([start, end]) => `${start}–${end}`).join("; ") ||
      "No breaks"
    );
  if (typeof value === "boolean") return value ? "Enabled" : "Disabled";
  if (key === "low_grade_percent") return `${value}%`;
  if (key === "day_basis")
    return value === "calendar" ? "Calendar days" : "Teaching days";
  return String(value);
}

export const policyFieldLabels: Record<
  Exclude<keyof EditablePolicy, "version">,
  string
> = {
  learning_mode: "Teaching style",
  inactivity_monitoring_enabled: "Inactivity monitoring",
  inactivity_warning_days: "Warning threshold (eligible days)",
  inactivity_high_days: "Escalation threshold (eligible days)",
  day_basis: "How days are counted",
  teaching_weekdays: "Teaching weekdays",
  break_ranges: "Scheduled breaks (course days)",
  require_academic_corroboration: "Academic corroboration",
  low_grade_percent: "Low-grade reference",
};
