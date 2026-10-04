import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { useEditGuard } from "../hooks/editGuard";
import { Notice } from "./ui";

export function EditDialog({
  title,
  children,
  close,
}: {
  title: string;
  children: ReactNode;
  close: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const guard = useEditGuard();
  const [keptOpen, setKeptOpen] = useState(false);
  useEffect(() => {
    const dialog = ref.current;
    const opener = document.activeElement;
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, []);
  function dismiss() {
    if (guard.leave()) close();
    else setKeptOpen(true);
  }
  return (
    <dialog
      ref={ref}
      className="edit-dialog"
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault();
        dismiss();
      }}
    >
      <header>
        <h2 id={titleId}>{title}</h2>
        <button
          type="button"
          aria-label="Close editor"
          className="icon-button"
          onClick={dismiss}
        >
          <X size={20} />
        </button>
      </header>
      {keptOpen && (
        <Notice>
          The editor is still open. Wait for any pending save, or finish or
          discard your draft before leaving.
        </Notice>
      )}
      {children}
    </dialog>
  );
}
