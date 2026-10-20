import { useState } from "react";
import type { ReactNode } from "react";
import type { z } from "zod";
import { useOperation } from "../hooks/useOperation";
import { useDraftGuard } from "../hooks/editGuard";
import { EditDialog } from "./EditDialog";
import { Notice } from "./ui";

export function OperationDialog<T>({
  title,
  description,
  path,
  body,
  schema,
  csrf,
  close,
  saved,
  action = "Confirm request",
}: {
  title: string;
  description: ReactNode;
  path: string;
  body: unknown;
  schema: z.ZodType<T>;
  csrf: string;
  close: () => void;
  saved: (result: T) => void;
  action?: string;
}) {
  const operation = useOperation(path, schema, csrf);
  const [confirmed, setConfirmed] = useState(false);
  useDraftGuard(confirmed || operation.blocked, operation.pending);
  return (
    <EditDialog title={title} close={close}>
      <form
        className="editor-form"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!confirmed) return;
          const result = await operation.run(body);
          if (result !== null) saved(result);
        }}
      >
        <div>{description}</div>
        <label className="check-field">
          <input
            type="checkbox"
            checked={confirmed}
            disabled={operation.pending || operation.blocked}
            onChange={(e) => setConfirmed(e.target.checked)}
          />
          I have checked the scope and consequences of this request.
        </label>
        {operation.error && <Notice error>{operation.error}</Notice>}
        {operation.blocked && (
          <Notice>
            The request may already have been applied, or its version changed.
            Close this dialog and refresh the saved status before deciding
            whether another request is needed. No automatic retry was sent.
          </Notice>
        )}
        <button
          className="primary"
          type="submit"
          disabled={!confirmed || operation.pending || operation.blocked}
        >
          {operation.pending ? "Requesting…" : action}
        </button>
      </form>
    </EditDialog>
  );
}
