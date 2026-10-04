import { useState } from "react";
import { Play } from "lucide-react";
import { OperationDialog } from "../components/OperationDialog";
import { Notice, Panel } from "../components/ui";
import { queueMessage, queueResultSchema } from "../api/analysisContracts";

export function AnalysisControls({
  course,
  week,
  learner,
  csrf,
}: {
  course: string;
  week: number;
  learner?: string;
  csrf: string;
}) {
  const [model, setModel] = useState<"llm" | "baseline">("llm");
  const [confirm, setConfirm] = useState(false);
  const [message, setMessage] = useState("");
  return (
    <Panel
      title="Request checkpoint analysis"
      note="Refresh reloads saved records. Queueing requests model work; neither imports new LMS records."
    >
      <details>
        <summary>
          {learner ? "Analyze this student" : "Analyze this course checkpoint"}{" "}
          · week {week}
        </summary>
        <p>
          Scope:{" "}
          {learner ? `student ${learner}` : "all students in this course"}, week{" "}
          {week} only. Matching pending jobs and completed results are reused,
          not force-rerun.
        </p>
        <label>
          Analysis model
          <select
            aria-label="Analysis model"
            value={model}
            onChange={(e) => setModel(e.target.value as "llm" | "baseline")}
          >
            <option value="llm">Configured Qwen instruction model</option>
            <option value="baseline">
              Temporary rules baseline · comparison only
            </option>
          </select>
        </label>
        <p className="fineprint">
          A rules result never counts as an LLM result. The worker must be
          running. Scores remain uncalibrated indicators; validation is not
          proof of predictive accuracy.
        </p>
        <button
          className="primary"
          onClick={() => {
            setMessage("");
            setConfirm(true);
          }}
        >
          <Play size={16} />
          {learner ? "Queue student analysis" : "Queue checkpoint analysis"}
        </button>
      </details>
      {message && (
        <div className="success-message" role="status">
          {message}
        </div>
      )}
      {confirm && (
        <OperationDialog
          title="Confirm checkpoint analysis"
          path={`v2/courses/${encodeURIComponent(course)}/analysis`}
          body={{
            week,
            model_kind: model,
            ...(learner ? { learner_ids: [learner] } : {}),
          }}
          schema={queueResultSchema}
          csrf={csrf}
          close={() => setConfirm(false)}
          action="Add to analysis queue"
          description={
            <>
              <p>
                {learner
                  ? `One student: ${learner}`
                  : "All students in this course"}{" "}
                · week {week} ·{" "}
                {model === "llm"
                  ? "configured Qwen model"
                  : "temporary rules baseline"}
                .
              </p>
              <Notice>
                Queued does not mean analyzed. This does not clear a
                course/service pause, change evidence or send messages. Check
                Data &amp; model for failures and worker status.
              </Notice>
            </>
          }
          saved={(result) => {
            setConfirm(false);
            setMessage(queueMessage(result));
          }}
        />
      )}
    </Panel>
  );
}
