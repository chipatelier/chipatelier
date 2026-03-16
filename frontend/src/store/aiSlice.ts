/**
 * Zustand AI slice: caches explain results and advisor suggestions.
 *
 * explainCache keys: "${runId}:${explainType}" — persists until a new run is submitted
 * or clearExplainCacheForRun is called (e.g., after job re-submission).
 *
 * advisorResult: last advisor response, keyed by advisorRunId so stale results
 * are detectable if the user switches to a different run.
 */
import { StateCreator } from "zustand";

export interface AdvisorResult {
  suggestions: string;
  model: string;
}

export interface AiSlice {
  /** Cache of explain responses: key = "${runId}:${explainType}" */
  explainCache: Record<string, string>;
  /** Last advisor result, or null if not yet fetched. */
  advisorResult: AdvisorResult | null;
  /** The run_id associated with the current advisorResult. */
  advisorRunId: string | null;

  setExplainCache: (key: string, text: string) => void;
  clearExplainCacheForRun: (runId: string) => void;
  setAdvisorResult: (r: AdvisorResult | null, runId: string | null) => void;
}

export const createAiSlice: StateCreator<AiSlice, [], [], AiSlice> = (set) => ({
  explainCache: {},
  advisorResult: null,
  advisorRunId: null,

  setExplainCache: (key, text) =>
    set((s) => ({ explainCache: { ...s.explainCache, [key]: text } })),

  clearExplainCacheForRun: (runId) =>
    set((s) => {
      const next: Record<string, string> = {};
      for (const [k, v] of Object.entries(s.explainCache)) {
        if (!k.startsWith(runId + ":")) next[k] = v;
      }
      return { explainCache: next };
    }),

  setAdvisorResult: (r, runId) =>
    set({ advisorResult: r, advisorRunId: runId }),
});
