import type { z } from "zod";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// Relative to the application directory, including /user/.../proxy/<port>/.
// Hash routes cannot make this escape the JupyterHub prefix.
const apiRoot = new URL("./api/", window.location.href.split("#")[0]);
export async function request<T>(
  path: string,
  schema: z.ZodType<T>,
  options: {
    signal?: AbortSignal;
    body?: unknown;
    csrf?: string;
    idempotencyKey?: string;
  } = {},
): Promise<T> {
  const response = await fetch(new URL(path, apiRoot), {
    method: options.body === undefined ? "GET" : "POST",
    credentials: "same-origin",
    cache: "no-store",
    signal: AbortSignal.any([
      ...(options.signal ? [options.signal] : []),
      AbortSignal.timeout(30000),
    ]),
    headers: {
      Accept: "application/json",
      "X-Requested-With": "CourseTwin",
      ...(options.body === undefined
        ? {}
        : { "Content-Type": "application/json" }),
      ...(options.csrf ? { "X-CSRF-Token": options.csrf } : {}),
      ...(options.idempotencyKey
        ? { "Idempotency-Key": options.idempotencyKey }
        : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  }).catch((error: unknown) => {
    if (options.signal?.aborted) throw error;
    throw new ApiError(
      504,
      "The service did not respond. Check your connection and refresh. No automatic retry was sent.",
    );
  });
  if (!response.ok) {
    if (response.status === 401 && path !== "browser/login")
      window.dispatchEvent(new Event("session-ended"));
    const messages: Record<number, string> = {
      401: "Your session ended. Please sign in again.",
      403: "This request is not permitted for your account or session.",
      404: "This record or service is not available.",
      409: "Another instructor updated this record. Refresh before saving.",
      422: "Some values were not accepted. Review the form.",
      429: "Too many sign-in attempts. Wait five minutes.",
      503: "The service is temporarily unavailable. Refresh to check saved records before repeating an action.",
    };
    let detail: unknown;
    if ([409, 422].includes(response.status)) {
      const problem: unknown = await response.json().catch(() => null);
      if (problem && typeof problem === "object" && "detail" in problem)
        detail = problem.detail;
    }
    throw new ApiError(
      response.status,
      path === "browser/login" && response.status === 401
        ? "Username or password is incorrect."
        : typeof detail === "string" && detail.length < 400
          ? detail
          : (messages[response.status] ??
            `The request failed (${response.status}). Try again or contact the operator.`),
    );
  }
  const parsed = schema.safeParse(await response.json());
  if (!parsed.success) {
    // Only field paths, never response bodies, learner records or credentials in errors.
    const fields = [
      ...new Set(parsed.error.issues.map((i) => i.path.join("."))),
    ]
      .slice(0, 6)
      .join(", ");
    throw new ApiError(
      502,
      `The API response needs an update before it can be displayed. Fields: ${fields || "response"}.`,
    );
  }
  return parsed.data;
}
