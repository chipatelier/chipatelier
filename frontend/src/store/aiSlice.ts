/**
 * Zustand AI slice: caches explain results, advisor suggestions, and chat history.
 *
 * explainCache keys: "${runId}:${explainType}" — persists until a new run is submitted
 * or clearExplainCacheForRun is called (e.g., after job re-submission).
 *
 * advisorResult: last advisor response, keyed by advisorRunId so stale results
 * are detectable if the user switches to a different run.
 *
 * chatHistory: full multi-turn conversation for the current run. Cleared on run change.
 * chatStreaming: true while a streaming response is in progress.
 */
import { StateCreator } from "zustand";
import { ChatMessage } from "../api/ai";

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
  /** Full chat history for the current run (user + assistant messages). */
  chatHistory: ChatMessage[];
  /** True while a streaming chat response is in progress. */
  chatStreaming: boolean;

  setExplainCache: (key: string, text: string) => void;
  clearExplainCacheForRun: (runId: string) => void;
  setAdvisorResult: (r: AdvisorResult | null, runId: string | null) => void;
  setChatHistory: (history: ChatMessage[]) => void;
  appendChatToken: (token: string) => void;
  setChatStreaming: (v: boolean) => void;
  clearChat: () => void;
}

export const createAiSlice: StateCreator<AiSlice, [], [], AiSlice> = (set) => ({
  explainCache: {},
  advisorResult: null,
  advisorRunId: null,
  chatHistory: [],
  chatStreaming: false,

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

  setChatHistory: (history) => set({ chatHistory: history }),

  appendChatToken: (token) =>
    set((s) => {
      const hist = [...s.chatHistory];
      const last = hist[hist.length - 1];
      if (last && last.role === "assistant") {
        hist[hist.length - 1] = { ...last, content: last.content + token };
      } else {
        hist.push({ role: "assistant", content: token });
      }
      return { chatHistory: hist };
    }),

  setChatStreaming: (v) => set({ chatStreaming: v }),

  clearChat: () => set({ chatHistory: [], chatStreaming: false }),
});
