import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ReactNode } from "react";
import { Notice } from "../components/ui";

type State = { dirty: boolean; pending: boolean };
type Guard = {
  register: (id: string, state: State | null) => void;
  leave: () => boolean;
};
const Context = createContext<Guard | null>(null);

export function EditGuard({ children }: { children: ReactNode }) {
  const forms = useRef(new Map<string, State>());
  const [message, setMessage] = useState("");
  const register = useCallback((id: string, state: State | null) => {
    if (state) forms.current.set(id, state);
    else forms.current.delete(id);
  }, []);
  const leave = useCallback(() => {
    if ([...forms.current.values()].some((s) => s.pending)) {
      setMessage(
        "A save is in progress. Please wait for the result before leaving.",
      );
      return false;
    }
    setMessage("");
    return (
      ![...forms.current.values()].some((s) => s.dirty) ||
      window.confirm(
        "Discard this unsaved draft? If a save result was uncertain, inspect the saved history before creating another entry.",
      )
    );
  }, []);
  useEffect(() => {
    const before = (e: BeforeUnloadEvent) => {
      if ([...forms.current.values()].some((s) => s.dirty || s.pending)) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, []);
  const value = useMemo(() => ({ register, leave }), [register, leave]);
  return (
    <Context.Provider value={value}>
      {message && (
        <div className="save-status">
          <Notice>
            {message}
            <button onClick={() => setMessage("")}>Dismiss</button>
          </Notice>
        </div>
      )}
      {children}
    </Context.Provider>
  );
}
export function useEditGuard() {
  const guard = useContext(Context);
  if (!guard) throw new Error("EditGuard provider missing");
  return guard;
}
export function useDraftGuard(dirty: boolean, pending: boolean) {
  const { register } = useEditGuard();
  const id = useId();
  useEffect(() => {
    register(id, { dirty, pending });
    return () => register(id, null);
  }, [id, dirty, pending, register]);
}
