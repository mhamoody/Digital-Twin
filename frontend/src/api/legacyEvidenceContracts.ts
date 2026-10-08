import { z } from "zod";

// Keep v1 evidence separate from the current course-operation contracts.
const count = z.number().int().nonnegative();
const score = z.number().min(0).max(1);
const identifier = z.string().min(1);

export const legacyComparisonSchema = z.object({
  available: z.boolean(),
  reason: z.string().nullable(),
  previous_checkpoint: z.number().int().nullable(),
  current_checkpoint: z.number().int().nullable(),
  previous_value: score.nullable(),
  current_value: score.nullable(),
  delta: z.number().min(-1).max(1).nullable(),
});

export const legacyLearnerSchema = z.object({
  learner_id: identifier,
  presentation_id: identifier,
  data_origin: identifier,
  state_id: identifier.nullable(),
  latest_checkpoint_week: z.number().int().positive().nullable(),
  latest_cutoff_course_day: z.number().int().nullable(),
  completeness: score.nullable(),
  is_fresh: z.boolean().nullable(),
  display_probability: score.nullable(),
  previous_probability: score.nullable(),
  probability_change: z.number().min(-1).max(1).nullable(),
  risk_band: z.string().nullable(),
  model_version: z.string().nullable(),
  prediction_id: identifier.nullable(),
  prediction_state_id: identifier.nullable(),
  assessment_status: z.enum(["assessed", "not_assessed"]),
  comparison_available: z.boolean(),
  comparison_reason: z.string(),
  comparison: legacyComparisonSchema,
  alert_id: identifier.nullable(),
  alert_status: z.string().nullable(),
  evidence_count: count,
  activity_count_14d: count.nullable(),
  active_days_14d: count.nullable(),
  days_since_last_activity: count.nullable(),
  assessments_due: count.nullable(),
  assessments_submitted: count.nullable(),
  assessments_missed: count.nullable(),
  submission_rate: score.nullable(),
});
export type LegacyLearner = z.infer<typeof legacyLearnerSchema>;

export const legacyLearnersSchema = z.object({
  items: z.array(legacyLearnerSchema),
  total: count,
  limit: z.number().int().positive(),
  offset: count,
});

const featureSchema = z.object({
  evidence_id: identifier,
  feature_name: z.string(),
  value: z.unknown(),
  missing_reason: z.string(),
  source_observation_count: count,
});
export type LegacyFeature = z.infer<typeof featureSchema>;

const predictionPointSchema = z.object({
  checkpoint_week: z.number().int(),
  cutoff_course_day: z.number().int(),
  display_probability: score.nullable(),
  risk_band: z.string().nullable(),
  model_version: z.string(),
  generated_at: z.string(),
  is_selected_alert: z.boolean(),
});
export type LegacyPredictionPoint = z.infer<typeof predictionPointSchema>;

export const legacyLearnerDetailSchema = z.object({
  learner: legacyLearnerSchema,
  registration_day: z.number().int().nullable(),
  registration_missing_reason: z.string(),
  unregistration_day: z.number().int().nullable(),
  unregistration_missing_reason: z.string(),
  features: z.array(featureSchema),
  activity_timeline: z.array(z.object({
    course_week: z.number().int(),
    activity_count: count,
    assessment_event_count: count,
  })),
  prediction_timeline: z.array(predictionPointSchema),
});

export const legacyAlertSchema = z.object({
    alert_id: identifier,
    learner_id: identifier,
    presentation_id: identifier,
    checkpoint_week: z.number().int(),
    cutoff_course_day: z.number().int(),
    display_probability: score,
    risk_band: z.string(),
    model_kind: z.string(),
    model_version: z.string(),
    priority: z.string(),
    status: z.string(),
    is_fresh: z.boolean(),
    generated_at: z.string(),
    data_origin: identifier,
    evidence_count: count,
});
export type LegacyAlert = z.infer<typeof legacyAlertSchema>;
export const legacyAlertsSchema = z.object({
  items: z.array(legacyAlertSchema),
  total: count,
  limit: z.number().int().positive(),
  offset: count,
});

export const legacyAlertDetailSchema = z.object({
  alert: legacyAlertSchema,
  state_id: identifier,
  input_hash: z.string(),
  feature_set_version: z.string(),
  completeness: score,
  model_ref: z.string(),
  uncertainty_note: z.string(),
  quality_gate_passed: z.boolean(),
  fallback_used: z.boolean(),
  claims: z.array(z.object({
    claim_code: z.string(),
    evidence_ids: z.array(identifier),
  })),
  suggested_actions: z.array(z.string()),
  evidence: z.array(featureSchema.extend({
    source_observation_hash: z.string(),
    source_record_samples: z.array(z.string()),
  })),
  prediction_timeline: z.array(predictionPointSchema),
  review_history: z.array(z.object({
    review_id: identifier,
    reviewer_id: z.string(),
    reviewer_role: z.string(),
    previous_status: z.string(),
    new_status: z.string(),
    note: z.string().nullable(),
    reviewed_at: z.string(),
  })),
});
export type LegacyAlertDetail = z.infer<typeof legacyAlertDetailSchema>;
