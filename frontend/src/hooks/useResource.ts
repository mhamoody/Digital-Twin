import { useEffect, useRef, useState } from "react";
import type { z } from "zod";
import { request } from "../api/client";

export function useResource<T>(
  path: string | null,
  schema: z.ZodType<T>,
  revision = 0,
) {
  const [result, setResult] = useState<{
    key: string;
    data?: T;
    error?: string;
  }>({ key: "" });
  const schemaRef = useRef(schema);
  schemaRef.current = schema;
  const key = `${path}|${revision}`;
  useEffect(() => {
    if (!path) return;
    const controller = new AbortController();
    request(path, schemaRef.current, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setResult({ key, data });
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setResult({
            key,
            error:
              error instanceof Error ? error.message : "Unable to load data.",
          });
      });
    return () => controller.abort();
  }, [path, key]);
  // Never show a previous student's/course's data while the new context is loading.
  return result.key === key
    ? result
    : { key, data: undefined, error: undefined };
}
