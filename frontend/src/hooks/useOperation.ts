import { useRef, useState } from "react";
import type { z } from "zod";
import { ApiError, request } from "../api/client";

// Settings/resume endpoints do not promise idempotency. Never automatically
// repeat them or offer the support-note same-key retry flow.
export function useOperation<T>(
  path: string,
  schema: z.ZodType<T>,
  csrf: string,
) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [blocked, setBlocked] = useState(false);
  const lock = useRef(false);
  async function run(body: unknown): Promise<T | null> {
    if (lock.current || blocked) return null;
    lock.current = true;
    setPending(true);
    setError("");
    try {
      return await request(path, schema, { body, csrf });
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setBlocked(status === 409 || status === 0 || status >= 500);
      setError(
        e instanceof Error
          ? e.message
          : "The operation could not be confirmed.",
      );
      return null;
    } finally {
      lock.current = false;
      setPending(false);
    }
  }
  return { run, pending, error, blocked };
}
