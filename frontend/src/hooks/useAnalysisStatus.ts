import { useEffect, useState } from "react";
import { request } from "../api/client";
import { analysisStatusSchema } from "../api/analysisContracts";
import type { AnalysisStatus } from "../api/analysisContracts";

export function useAnalysisStatus(course: string, revision: number) {
  const [tick, setTick] = useState(0);
  const [result, setResult] = useState<{
    course: string;
    data?: AnalysisStatus;
    error?: string;
  }>({ course: "" });
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function poll() {
      if (!active) return;
      if (document.hidden) {
        timer = setTimeout(poll, 10000);
        return;
      }
      try {
        const data = await request(
          `v2/courses/${encodeURIComponent(course)}/analysis/status`,
          analysisStatusSchema,
          { signal: controller.signal },
        );
        if (active) setResult({ course, data });
      } catch (e) {
        if (active)
          setResult({
            course,
            error:
              e instanceof Error
                ? e.message
                : "Progress could not be verified.",
          });
      } finally {
        if (active) timer = setTimeout(poll, 10000);
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
      controller.abort();
    };
  }, [course, revision, tick]);
  return {
    ...(result.course === course ? result : { course }),
    refresh: () => setTick((v) => v + 1),
  };
}
