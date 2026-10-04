import { generationSchema } from "../api/analysisContracts";
import type { LearnerDetail } from "../api/contracts";
import { Badge, label, Notice, Panel, score } from "../components/ui";

const outcomes: Record<string, string> = {
  first_pass_validated: "Validated on the first model response",
  repaired_validated: "Validated after a bounded model correction",
  quality_abstained: "Evidence-quality gate abstained before inference",
};

function text(value: unknown): string | undefined {
  return typeof value === "string" && value.length <= 256 ? value : undefined;
}

export function AnalysisProvenance({ data }: { data: LearnerDetail }) {
  const analysis = data.analysis;
  const baseline = data.baseline_analysis;
  const isBaseline = analysis?.model_kind === "baseline";
  const current = Boolean(
    analysis &&
      ["validated", "abstained"].includes(data.analysis_status) &&
      data.snapshot?.is_fresh &&
      analysis.policy_version === data.current_policy_version,
  );
  const attempts = (
    Array.isArray(analysis?.inference_attempts)
      ? analysis.inference_attempts.slice(0, 2)
      : []
  ).flatMap((value) => {
    const parsed = generationSchema.safeParse(value);
    return parsed.success ? [parsed.data] : [];
  });
  const outcome = text(analysis?.validation_outcome);
  const details = attempts.flatMap((attempt) =>
    (attempt.validation_details ?? []).slice(0, 30).map((detail) => ({
      attempt: attempt.attempt,
      ...detail,
    })),
  );
  const normalizations = attempts.flatMap((attempt) =>
    (attempt.normalizations ?? []).slice(0, 30).map((entry) => ({
      attempt: attempt.attempt,
      ...entry,
    })),
  );

  return (
    <Panel
      title="Model validation & provenance"
      note="How this saved result was produced. Passing validation does not establish predictive accuracy."
    >
      {!analysis ? (
        <Notice>No saved analysis is available for this checkpoint.</Notice>
      ) : (
        <>
          <div className="support-summary">
            <Badge tone={current ? "sage" : "amber"}>
              {current
                ? "Current saved result"
                : "Historical result · not current"}
            </Badge>
            <span>{analysis.model_version}</span>
          </div>
          {isBaseline && (
            <Notice>
              This saved result is the temporary deterministic rules baseline,
              not an LLM assessment. It does not count toward LLM completion.
            </Notice>
          )}
          <p>
            {outcome
              ? (outcomes[outcome] ?? "Validation outcome not recognized")
              : "Detailed validation outcome was not retained for this result."}
          </p>
          {outcome === "repaired_validated" && (
            <p>
              The first response was rejected. The model received structured
              validation feedback and made a bounded correction; the rejected
              attempt remains in the audit history.
            </p>
          )}
          {outcome === "quality_abstained" && (
            <p>
              Essential evidence was insufficient or unsuitable. No model risk
              score was published; an abstention is not a model prediction.
            </p>
          )}
          {analysis.risk_band_origin === "server_thresholds" && (
            <p>
              The model supplies the risk score. The server assigns the support
              level using the documented score thresholds.
            </p>
          )}
          <p>
            Risk scores are uncalibrated 0–100 outputs, not probabilities of
            failure. Formatting normalization, model correction and evidence
            validation are separate checks.
          </p>
          <details>
            <summary>Saved model identity and contract</summary>
            <div
              className="table-scroll"
              tabIndex={0}
              role="region"
              aria-label="Saved model provenance"
            >
              <table>
                <thead>
                  <tr>
                    <th>Field</th>
                    <th>Saved value</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Model", analysis.model_version],
                    ["Model digest", analysis.model_digest],
                    ["Prompt version", analysis.prompt_version],
                    ["Feature version", analysis.feature_version],
                    ["Policy version", String(analysis.policy_version)],
                    ["Output contract", text(analysis.wire_contract_version)],
                    ["Calibration version", analysis.calibration_version],
                  ].map(([name, value]) => (
                    <tr key={name}>
                      <th scope="row">{name}</th>
                      <td>{value || "Not recorded"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
          <details>
            <summary>Model response and correction history</summary>
            <p>
              These records describe response validation, not student progress.
              Raw model replies are not displayed.
            </p>
            {attempts.length === 0 ? (
              <Notice>
                No response-level trace was retained. A pre-inference abstention
                has no model response.
              </Notice>
            ) : (
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Model response history"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Response</th>
                      <th>Stage</th>
                      <th>Outcome</th>
                      <th>Time (seconds)</th>
                      <th>Validation code</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attempts.map((attempt, index) => (
                      <tr key={index}>
                        <td>{attempt.attempt}</td>
                        <td>
                          {attempt.kind === "initial"
                            ? "Initial response"
                            : attempt.kind === "validation_feedback"
                              ? "Validation feedback"
                              : "Not recorded"}
                        </td>
                        <td>{label(attempt.outcome)}</td>
                        <td>
                          {typeof attempt.latency_seconds === "number" &&
                          Number.isFinite(attempt.latency_seconds)
                            ? attempt.latency_seconds.toFixed(2)
                            : "Not recorded"}
                        </td>
                        <td>{attempt.error_code || "None"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {details.length > 0 && (
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Validation field details"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Response</th>
                      <th>Field</th>
                      <th>Problem</th>
                      <th>Expected</th>
                      <th>Received type</th>
                    </tr>
                  </thead>
                  <tbody>
                    {details.map((detail, index) => (
                      <tr key={index}>
                        <td>{detail.attempt}</td>
                        <td>{detail.path}</td>
                        <td>{detail.code}</td>
                        <td>{detail.expected || "Not recorded"}</td>
                        <td>{detail.received_type || "Not recorded"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {normalizations.length > 0 && (
              <div
                className="table-scroll"
                tabIndex={0}
                role="region"
                aria-label="Formatting normalizations"
              >
                <table>
                  <thead>
                    <tr>
                      <th>Response</th>
                      <th>Field</th>
                      <th>Audited formatting normalization</th>
                    </tr>
                  </thead>
                  <tbody>
                    {normalizations.map((entry, index) => (
                      <tr key={index}>
                        <td>{entry.attempt}</td>
                        <td>{entry.path}</td>
                        <td>{entry.code}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </details>
        </>
      )}
      {baseline && !isBaseline && (
        <details>
          <summary>Temporary rules baseline · saved reference</summary>
          <p>
            This deterministic reference is not the LLM and does not count
            toward LLM completion. A difference between scores is not evidence
            that either method is more accurate.
          </p>
          <div
            className="table-scroll"
            tabIndex={0}
            role="region"
            aria-label="Saved analysis reference"
          >
            <table>
              <thead>
                <tr>
                  <th>Saved source</th>
                  <th>Risk score</th>
                  <th>Policy version</th>
                  <th>Meaning</th>
                </tr>
              </thead>
              <tbody>
                {analysis && (
                  <tr>
                    <th scope="row">{analysis.model_version}</th>
                    <td>
                      {analysis.output.abstain
                        ? "Withheld · abstained"
                        : score(analysis.output.risk_score)}
                    </td>
                    <td>{analysis.policy_version}</td>
                    <td>{current ? "Current result" : "Historical only"}</td>
                  </tr>
                )}
                <tr>
                  <th scope="row">{baseline.model_version}</th>
                  <td>
                    {baseline.output.abstain
                      ? "Withheld · abstained"
                      : score(baseline.output.risk_score)}
                  </td>
                  <td>{baseline.policy_version}</td>
                  <td>Saved rules reference; not a current LLM judgment</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p>
            Read the policy versions before comparing. Scores from different
            policies are not directly comparable.
          </p>
        </details>
      )}
    </Panel>
  );
}
