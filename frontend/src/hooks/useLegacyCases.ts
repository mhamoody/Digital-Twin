import { useEffect, useState } from "react";
import { request } from "../api/client";
import { legacyCasesSchema } from "../api/legacyContracts";
import type { LegacyCase } from "../api/legacyContracts";

// The v1 API has no learner filter. Load all matching server pages before
// filtering locally; never label the first page as the learner's whole history.
export function useLegacyCases({ course, dataOrigin, learner, scope, dueOnly, offset, revision }: {
  course: string; dataOrigin: string; learner: string; scope: string;
  dueOnly: boolean; offset: number; revision: number;
}) {
  const key = JSON.stringify([course, dataOrigin, learner, scope, dueOnly, offset, revision]);
  const [result, setResult] = useState<{
    key: string; data?: { items: LegacyCase[]; total: number }; error?: string;
  }>({ key: "" });
  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      const items: LegacyCase[] = [];
      let pageOffset = learner ? 0 : offset;
      const limit = learner ? 200 : 25;
      let expectedTotal: number | undefined;
      const seen = new Set<string>();
      while (true) {
        const params = new URLSearchParams({ limit: String(limit), offset: String(pageOffset) });
        if (scope !== "all") params.set("active", String(scope === "active"));
        if (dueOnly) params.set("follow_up_due", "true");
        const page = await request(
          `v1/presentations/${encodeURIComponent(course)}/support-cases?${params}`,
          legacyCasesSchema,
          { signal: controller.signal },
        );
        if (page.limit !== limit || page.offset !== pageOffset || page.items.length > limit ||
          (page.items.length > 0 && pageOffset + page.items.length > page.total) ||
          new Set(page.items.map((item) => item.case_id)).size !== page.items.length || page.items.some((item) =>
          item.presentation_id !== course || item.data_origin !== dataOrigin || seen.has(item.case_id))) {
          throw new Error("The earlier-case response does not match the requested course, data origin or page.");
        }
        if (expectedTotal !== undefined && page.total !== expectedTotal) {
          throw new Error("The episode list changed while loading. Refresh before reviewing this learner's full history.");
        }
        expectedTotal = page.total;
        for (const item of page.items) { seen.add(item.case_id); items.push(item); }
        if (!learner) return { items, total: page.total };
        if (items.length >= page.total) break;
        if (!page.items.length) throw new Error("The episode list is incomplete. Refresh to load the remaining history.");
        pageOffset += page.items.length;
      }
      const matching = items.filter((item) => item.learner_id === learner);
      return { items: matching.slice(offset, offset + 25), total: matching.length };
    }
    load().then((data) => {
      if (!controller.signal.aborted) setResult({ key, data });
    }).catch((failure: unknown) => {
      if (!controller.signal.aborted) setResult({ key, error: failure instanceof Error ? failure.message : "Unable to load earlier episodes." });
    });
    return () => controller.abort();
  }, [key, course, dataOrigin, learner, scope, dueOnly, offset]);
  return result.key === key ? result : { key, data: undefined, error: undefined };
}
