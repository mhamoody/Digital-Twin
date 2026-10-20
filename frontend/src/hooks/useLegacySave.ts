import { useRef, useState } from "react";
import type { z } from "zod";
import { ApiError, request } from "../api/client";

// V1 case writes use body keys; alert reviews use header keys. An uncertain
// request is immutable, including its original expected_version and endpoint.
export function useLegacySave<T>(
  path: string,
  schema: z.ZodType<T>,
  csrf: string,
  keyLocation: "body" | "header" = "body",
) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const [conflict, setConflict] = useState(false);
  const locked = useRef(false);
  const attempt = useRef<{ path: string; body: Record<string, unknown>; key: string } | null>(null);

  async function send(): Promise<T | null> {
    const frozen = attempt.current;
    if (!frozen || locked.current || conflict) return null;
    if (frozen.path !== path) {
      setError("The request context changed. Inspect saved history before starting another action.");
      return null;
    }
    locked.current = true;
    setPending(true);
    setError("");
    try {
      const result = await request(frozen.path, schema, {
        body: frozen.body,
        csrf,
        ...(keyLocation === "header" ? { idempotencyKey: frozen.key } : {}),
      });
      attempt.current = null;
      setUncertain(false);
      return result;
    } catch (failure) {
      const status = failure instanceof ApiError ? failure.status : 0;
      const unknown = status === 0 || status === 408 || status >= 500;
      setConflict(status === 409);
      setUncertain(unknown);
      if (!unknown) attempt.current = null;
      setError(failure instanceof Error ? failure.message : "The save result could not be confirmed.");
      return null;
    } finally {
      locked.current = false;
      setPending(false);
    }
  }

  async function save(body: Record<string, unknown>): Promise<T | null> {
    if (locked.current || conflict) return null;
    if (attempt.current) {
      setError("An earlier save has an uncertain result. Use Retry the same save to resend the original request.");
      return null;
    }
    const key = crypto.randomUUID();
    const payload = keyLocation === "body" ? { ...body, idempotency_key: key } : body;
    attempt.current = { path, key, body: JSON.parse(JSON.stringify(payload)) as Record<string, unknown> };
    return send();
  }
  async function retry(): Promise<T | null> {
    return uncertain ? send() : null;
  }
  return { pending, error, uncertain, conflict, save, retry };
}
