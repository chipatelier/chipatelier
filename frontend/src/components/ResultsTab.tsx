import React from "react";
import { PpaMetricCards } from "./PpaMetricCards";
import type { PpaMetrics } from "./PpaMetricCards";
import { LayoutSnapshot } from "./LayoutSnapshot";
import type { ArtifactURLs } from "../api/artifacts";

interface Props {
  status: string | null;
  ppa: Record<string, unknown> | null | undefined;
  runId: string | undefined;
  artifacts: ArtifactURLs | null;
}

export function ResultsTab({ status, ppa, runId, artifacts }: Props): React.ReactElement {
  if (status !== "complete") {
    return (
      <div style={{ padding: 24 }}>
        <p style={{ color: "#8b949e", fontSize: 14 }}>
          Results will appear here when the job completes.
        </p>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, overflowY: "auto" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
        <div>
          <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: "0 0 16px 0" }}>
            PPA Metrics
          </h3>
          <PpaMetricCards metrics={ppa as PpaMetrics | null} runId={runId} />
        </div>
        <div>
          <h3 style={{ color: "#f0f6fc", fontSize: 15, margin: "0 0 16px 0" }}>
            Layout Preview
          </h3>
          <LayoutSnapshot
            runId={runId ?? ""}
            artifacts={artifacts}
          />
        </div>
      </div>
    </div>
  );
}
