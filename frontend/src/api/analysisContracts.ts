import { z } from "zod";
const count = z.number().int().nonnegative();
const optionalText = z.string().nullable().optional();
const safeValue = z.union([z.string(), z.number(), z.boolean(), z.null()]);
export const validationDetail = z.object({
  path: z.string(),
  code: z.string(),
  expected: z.string().optional(),
  received_type: z.string().optional(),
  received: safeValue.optional(),
});
export const generationSchema = z.object({
  attempt: count,
  kind: z.string(),
  outcome: z.string(),
  error_code: optionalText,
  latency_seconds: z.number().nullable().optional(),
  validation_details: z.array(validationDetail).optional(),
  normalizations: z
    .array(z.object({ path: z.string(), code: z.string() }))
    .optional(),
});
export const failureSchema = z.object({
  code: z.string(),
  title: z.string(),
  detail: z.string(),
  action: z.string(),
});
export const modelStatusSchema = z.object({
  status: z.string(),
  model: z.string(),
  digest: optionalText,
  error_code: optionalText,
  failure: failureSchema.nullable().optional(),
  inference_verified: z.boolean().optional(),
});
export const automationSchema = z.object({
  enabled: z.boolean(),
  version: count,
});
export const controlSchema = z.object({
  status: z.string(),
  failure_streak: count,
  last_error_code: optionalText,
  pause_scope: optionalText,
  resume_requested_at: optionalText,
  resume_acknowledged_at: optionalText,
  updated_at: optionalText,
});
const summarySchema = z.object({
  total_snapshots: count,
  validated: count,
  abstained: count,
  queued: count,
  running: count,
  retry_scheduled: count,
  failed: count,
  unassessed: count,
  baseline_only: count,
});
export const analysisStatusSchema = z.object({
  automation: automationSchema,
  model: modelStatusSchema,
  worker: z.object({
    status: z.string(),
    heartbeat_at: optionalText,
    heartbeat_age_seconds: count.nullable().optional(),
    pause_until: optionalText,
    last_error_code: optionalText,
    pause_scope: optionalText,
    active_deadline_at: optionalText,
    is_processing_this_course: z.boolean(),
    processing_another_course: z.boolean(),
    active_week: count.nullable().optional(),
  }),
  course_control: controlSchema,
  served_at: z.string(),
  summary: summarySchema,
  weeks: z.array(summarySchema.extend({ week: count })),
  failures: z.array(
    failureSchema.extend({
      count,
      diagnostic_samples: z
        .array(
          z.object({
            job_id: z.string(),
            job_attempt: count.nullable(),
            detail_available: z.boolean(),
            generations: z.array(generationSchema),
          }),
        )
        .optional(),
    }),
  ),
  max_attempts: count,
});
export type AnalysisStatus = z.infer<typeof analysisStatusSchema>;
export const queueResultSchema = z.object({
  queued: count,
  already_queued: count.optional(),
  already_assessed: count.optional(),
  failed_skipped: count.optional(),
  exhausted: count.optional(),
  model_ready: z.boolean().optional(),
  job_ids: z.array(z.string()).optional(),
});
export type QueueResult = z.infer<typeof queueResultSchema>;
export function queueMessage(result: QueueResult) {
  const details = [
    [result.already_queued, "already pending"],
    [result.already_assessed, "already assessed"],
    [result.failed_skipped, "failures skipped"],
    [result.exhausted, "at attempt limit"],
  ]
    .filter(([value]) => value !== undefined)
    .map(([value, title]) => `${value} ${title}`);
  return `Added ${result.queued} job(s). ${details.length ? `${details.join("; ")}. ` : ""}Queued is not completed. Refresh saved results after processing.`;
}
export function resumePending(control: AnalysisStatus["course_control"]) {
  if (!control.resume_requested_at) return false;
  if (!control.resume_acknowledged_at) return true;
  const requested = Date.parse(control.resume_requested_at),
    acknowledged = Date.parse(control.resume_acknowledged_at);
  return (
    !Number.isFinite(requested) ||
    !Number.isFinite(acknowledged) ||
    requested > acknowledged
  );
}
