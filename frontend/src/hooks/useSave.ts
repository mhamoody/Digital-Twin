import { useRef, useState } from "react";
import type { z } from "zod";
import { ApiError, request } from "../api/client";

// Keep the exact payload/key after an uncertain response. Retrying is explicit,
// and the server deduplicates it even if the first response was lost after commit.
export function useSave<T>(path: string, schema: z.ZodType<T>, csrf: string) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [uncertain, setUncertain] = useState(false);
  const [conflict, setConflict] = useState(false);
  const locked = useRef(false);
  const attempt = useRef<{
    fingerprint: string;
    key: string;
    body: unknown;
  } | null>(null);
  async function save(body: unknown): Promise<boolean> {
    if (locked.current || conflict) return false;
    const fingerprint = JSON.stringify(body);
    if (
      uncertain &&
      attempt.current &&
      fingerprint !== attempt.current.fingerprint
    ) {
      setError(
        "The previous save has an uncertain result. Retry that exact save or reload and inspect history.",
      );
      return false;
    }
    if (attempt.current?.fingerprint !== fingerprint)
      attempt.current = { fingerprint, key: crypto.randomUUID(), body };
    locked.current = true;
    setPending(true);
    setError("");
    try {
      await request(path, schema, {
        body: attempt.current.body,
        csrf,
        idempotencyKey: attempt.current.key,
      });
      setUncertain(false);
      attempt.current = null;
      return true;
    } catch (e) {
      const status = e instanceof ApiError ? e.status : 0;
      setConflict(status === 409);
      setUncertain(status === 0 || status >= 500);
      setError(
        e instanceof Error
          ? e.message
          : "The save result could not be confirmed.",
      );
      return false;
    } finally {
      locked.current = false;
      setPending(false);
    }
  }
  return { pending, error, uncertain, conflict, save };
}
