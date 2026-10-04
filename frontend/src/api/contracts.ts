import { z } from "zod";

// Parse at the network boundary: TypeScript alone cannot validate server JSON.
const count = z.number().int().nonnegative();
const scalar = z.union([z.string(), z.number(), z.boolean(), z.null()]);
const bag = z.record(z.string(), z.unknown());
export const sessionSchema = z.object({
  user: z.object({
    display_name: z.string(),
    role: z.enum(["instructor", "supervisor"]),
  }),
  csrf_token: z.string().min(1),
});
export type Session = z.infer<typeof sessionSchema>;
export const courseSchema = z.object({
  presentation_id: z.string(),
  title: z.string().optional(),
  code_module: z.string().optional(),
  data_origin: z.string(),
  checkpoints: z.array(count),
});
export type Course = z.infer<typeof courseSchema>;
export const coursesSchema = z.object({ items: z.array(courseSchema) });
export const triageSchema = z.object({
  version: count,
  flagged: z.boolean(),
  watchlisted: z.boolean(),
  priority: z.enum(["low", "normal", "high", "urgent"]),
  note: z.string().optional(),
});
export const learnerRowSchema = z.object({
  learner_id: z.string(),
  display_name: z.string(),
  checkpoint_week: count,
  state_id: z.string().nullable(),
  risk_score: z.number().min(0).max(1).nullable(),
  risk_band: z.enum(["low", "medium", "high"]).nullable(),
  previous_score: z.number().nullable(),
  change: z.number().nullable(),
  previous_week: count.nullable(),
  analysis_status: z.string(),
  model_version: z.string().nullable(),
  case_status: z.string().nullable(),
  case_version: count,
  follow_up_day: count.nullable(),
  active_case: z.boolean(),
  due: z.boolean(),
  triage: triageSchema,
  is_fresh: z.boolean(),
  comparable: z.boolean(),
  reason: z.string().nullable(),
  needs_review: z.boolean(),
});
export type LearnerRow = z.infer<typeof learnerRowSchema>;
export const policySchema = z.object({
  version: count,
  learning_mode: z.string(),
  inactivity_monitoring_enabled: z.boolean(),
  inactivity_warning_days: count,
  inactivity_high_days: count,
  day_basis: z.string(),
  teaching_weekdays: z.array(count),
  break_ranges: z.array(z.tuple([count, count])),
  require_academic_corroboration: z.boolean(),
  low_grade_percent: z.number(),
});
export type Policy = z.infer<typeof policySchema>;
export const workspaceSchema = z.object({
  course: bag,
  policy: policySchema,
  summary: z.object({
    enrolled: count,
    needs_review: count,
    high_attention: count,
    insufficient_data: count,
    active_cases: count,
    due: count,
    watchlist: count,
    flagged: count,
    not_run: count,
    queued: count,
    failed: count,
  }),
  model_counts: z.record(z.string(), count),
  distribution: z.object({
    high: count,
    medium: count,
    low: count,
    unavailable: count,
  }),
  movement: z.object({
    increased: count,
    stable: count,
    decreased: count,
    not_comparable: count,
  }),
  items: z.array(learnerRowSchema),
  total: count,
  week: count,
  support_scope: z.string(),
  as_of_day: count,
  as_of_day_basis: z.string(),
  current_course_day: z.number().nullable(),
});
export type Workspace = z.infer<typeof workspaceSchema>;
export const factSchema = z.object({
  evidence_id: z.string(),
  value: scalar,
  status: z.string(),
  unit: z.string(),
  window: z.string(),
  source_ids: z.array(z.string()),
  available_day: z.number().nullable(),
});
export type Fact = z.infer<typeof factSchema>;
const features = z.record(z.string(), factSchema);
const snapshotSchema = z.object({
  state_id: z.string(),
  checkpoint_week: count,
  cutoff_day: count,
  data_origin: z.string(),
  built_at: z.string(),
  is_fresh: z.boolean(),
  coverage: z.record(z.string(), z.string()),
  features,
  feature_version: z.string().optional(),
  course_context: bag.optional(),
});
const outputSchema = z.object({
  risk_score: z.number().min(0).max(1).nullable(),
  risk_band: z.enum(["low", "medium", "high"]).nullable(),
  abstain: z.boolean(),
  abstention_reason: z.string().nullable(),
  claims: z.array(
    z.object({ code: z.string(), evidence_ids: z.array(z.string()) }),
  ),
  suggested_actions: z.array(z.string()),
});
const analysisSchema = z
  .object({
    output: outputSchema,
    model_version: z.string(),
    policy_version: count,
    model_digest: z.string().nullable().optional(),
    prompt_version: z.string().nullable().optional(),
    feature_version: z.string().nullable().optional(),
    calibration_version: z.string().nullable().optional(),
  })
  .passthrough();
export const caseEventSchema = z.object({
  id: z.string(),
  actor: z.string(),
  recorded_at: z.string(),
  status: z.enum(["new", "reviewed", "ongoing", "resolved", "dismissed"]),
  action: z.enum([
    "note",
    "contact",
    "warning",
    "support",
    "resource",
    "follow_up",
  ]),
  action_state: z.enum(["planned", "completed", "cancelled"]),
  occurred_day: count,
  follow_up_day: count.nullable(),
  checkpoint_week: count,
  evidence_checkpoint_week: count.optional(),
  note: z.string(),
  resource_ids: z.array(z.string()),
  resolves_event_id: z.string().nullable().optional(),
});
export type CaseEvent = z.infer<typeof caseEventSchema>;
export const caseSchema = z.object({
  id: z.string(),
  status: z.string(),
  version: count,
  follow_up_day: count.nullable(),
  events: z.array(caseEventSchema),
});
export const triageResponseSchema = z.object({
  triage: triageSchema,
  triage_history: z.array(bag),
});
export const detailSchema = z.object({
  learner_id: z.string(),
  display_name: z.string(),
  current_course_day: z.number().nullable(),
  analysis_status: z.string(),
  comparable: z.boolean(),
  previous_week: count.nullable(),
  current_policy_version: count,
  snapshot: snapshotSchema.nullable(),
  analysis: analysisSchema.nullable(),
  previous_analysis: analysisSchema.nullable(),
  baseline_analysis: analysisSchema.nullable(),
  job_error: z.string().nullable(),
  job_error_detail: bag.nullable(),
  history: z.array(
    z.object({
      checkpoint_week: count,
      risk_score: z.number().nullable(),
      risk_band: z.string().nullable(),
      model_version: z.string(),
      policy_version: count,
      model_digest: z.string().nullable().optional(),
      prompt_version: z.string().nullable().optional(),
      feature_version: z.string().nullable().optional(),
      calibration_version: z.string().nullable().optional(),
      features,
    }),
  ),
  snapshot_history: z.array(
    z.object({
      checkpoint_week: count,
      cutoff_day: z.number().optional(),
      feature_version: z.string().nullable().optional(),
      course_context: bag.optional(),
      features,
    }),
  ),
  case: caseSchema.nullable(),
  current_case: caseSchema.nullable(),
  triage: triageSchema,
  triage_history: z.array(bag),
  resources: z.array(bag),
  assessments: z.array(bag),
  events: z.array(bag),
});
export type LearnerDetail = z.infer<typeof detailSchema>;
export type Privacy = "name_id" | "id_only";
