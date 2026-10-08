import { z } from "zod";

export const legacyIndexSchema = z.object({
  items: z.array(z.object({
    presentation_id: z.string(), module_code: z.string(),
    presentation_code: z.string(), data_origin: z.string(),
  })),
});
export const legacyCaseSchema = z.object({
  case_id: z.string(), presentation_id: z.string(), learner_id: z.string(),
  data_origin: z.string(),
  status: z.enum(["new_concern", "reviewed", "ongoing", "resolved", "dismissed"]),
  opened_at: z.string(), last_action_at: z.string(),
  follow_up_due_at: z.string().nullable(), closed_at: z.string().nullable(),
  version: z.number().int().positive(),
});
export const legacyCasesSchema = z.object({
  items: z.array(legacyCaseSchema), total: z.number().int().nonnegative(),
  limit: z.number().int().positive(), offset: z.number().int().nonnegative(),
});
export const legacyCaseDetailSchema = z.object({
  case: legacyCaseSchema,
  actions: z.array(z.object({
    action_id: z.string(), case_id: z.string(), action_type: z.string(), actor_id: z.string(),
    actor_role: z.string(), created_at: z.string(), resulting_version: z.number().int(),
    note: z.string().nullable(), previous_status: z.string().nullable(),
    new_status: z.string().nullable(), previous_follow_up_due_at: z.string().nullable(),
    new_follow_up_due_at: z.string().nullable(), linked_alert_id: z.string().nullable(),
  })),
  linked_alerts: z.array(z.object({
    alert_id: z.string(), prediction_id: z.string(), state_id: z.string(),
    checkpoint: z.number().int(), risk_band: z.string().nullable(),
    linked_at: z.string(), link_reason: z.string(),
  })),
});
export const legacyMutationSchema = z.object({
  case_id: z.string(), action_id: z.string(), resulting_version: z.number().int().positive(),
});
export type LegacyMutation = z.infer<typeof legacyMutationSchema>;
export const legacyReviewSchema = z.object({
  review_id: z.string(), alert_id: z.string(),
  status: z.enum(["reviewed", "resolved", "dismissed"]),
  created: z.boolean(), reviewed_at: z.string(),
});
export type LegacyCase = z.infer<typeof legacyCaseSchema>;
export type LegacyCaseDetail = z.infer<typeof legacyCaseDetailSchema>;
export const legacyActive = new Set<LegacyCase["status"]>(["new_concern", "reviewed", "ongoing"]);
export const legacyTransitions: Record<LegacyCase["status"], string[]> = {
  new_concern: ["reviewed", "ongoing", "resolved", "dismissed"],
  reviewed: ["ongoing", "resolved", "dismissed"],
  ongoing: ["ongoing", "resolved", "dismissed"], resolved: [], dismissed: [],
};
