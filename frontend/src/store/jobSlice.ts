/**
 * Zustand job slice: tracks active run state and stage progress.
 *
 * Stage progress is computed from stageCompleted:
 *   - All stages up to stageCompleted = "done"
 *   - Next stage after completed = "running" (if job status is running/starting)
 *   - Remaining stages = "pending"
 */
import { StateCreator } from "zustand";

export type StageState = "done" | "running" | "pending";

export const STAGES = [
  "synthesis",
  "floorplan",
  "place",
  "cts",
  "route",
  "gds",
] as const;

export type Stage = (typeof STAGES)[number];

const ACTIVE_STATUSES = new Set(["queued", "starting", "running"]);

function computeStageProgress(
  status: string | null,
  stageCompleted: string | null
): Record<Stage, StageState> {
  const progress: Record<Stage, StageState> = {
    synthesis: "pending",
    floorplan: "pending",
    place: "pending",
    cts: "pending",
    route: "pending",
    gds: "pending",
  };

  if (!status) return progress;

  const completedIdx = stageCompleted
    ? STAGES.indexOf(stageCompleted as Stage)
    : -1;
  const isActive = ACTIVE_STATUSES.has(status);

  for (let i = 0; i < STAGES.length; i++) {
    const stage = STAGES[i];
    if (i <= completedIdx) {
      progress[stage] = "done";
    } else if (i === completedIdx + 1 && isActive) {
      progress[stage] = "running";
    } else {
      progress[stage] = "pending";
    }
  }

  return progress;
}

export interface JobSlice {
  activeRunId: string | null;
  runStatus: string | null;
  stageProgress: Record<Stage, StageState>;
  setActiveRun: (runId: string | null) => void;
  setRunStatus: (status: string, stageCompleted?: string | null) => void;
  clearJob: () => void;
}

export const createJobSlice: StateCreator<JobSlice> = (set) => ({
  activeRunId: null,
  runStatus: null,
  stageProgress: {
    synthesis: "pending",
    floorplan: "pending",
    place: "pending",
    cts: "pending",
    route: "pending",
    gds: "pending",
  },

  setActiveRun: (runId) => set({ activeRunId: runId }),

  setRunStatus: (status, stageCompleted = null) =>
    set(() => ({
      runStatus: status,
      stageProgress: computeStageProgress(status, stageCompleted ?? null),
    })),

  clearJob: () =>
    set({
      activeRunId: null,
      runStatus: null,
      stageProgress: {
        synthesis: "pending",
        floorplan: "pending",
        place: "pending",
        cts: "pending",
        route: "pending",
        gds: "pending",
      },
    }),
});
