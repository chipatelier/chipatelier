/**
 * Zustand course slice: tracks courses, assignments, submissions, and grade results.
 */
import { StateCreator } from "zustand";
import { CheckpointResults, SubmissionResponse } from "../api/submissions";

// ---------------------------------------------------------------------------
// Domain types (matching backend Pydantic schemas)
// ---------------------------------------------------------------------------

export interface Course {
  id: string;
  name: string;
  term: string | null;
  enrollment_code: string;
  is_active: boolean;
  instructor_id: string;
  created_at: string;
}

export interface Assignment {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  pdk: string;
  target_stage: string;
  locked_params: Record<string, string>;
  editable_params: string[];
  checkpoint_rules: {
    hard?: Array<{ metric: string; op: string; value: number | boolean }>;
    scored?: Array<{
      metric: string;
      op: string;
      value: number;
      points: number;
      partial?: { threshold: number; points: number };
    }>;
  };
  due_at: string | null;
  is_open: boolean;
  orfs_version: string | null;
  created_at: string;
}

export interface GradeResult {
  score: number;
  checkpoint_results: CheckpointResults;
  submission_id: string;
}

// ---------------------------------------------------------------------------
// Slice type
// ---------------------------------------------------------------------------

export interface CourseSlice {
  courses: Course[];
  activeAssignment: Assignment | null;
  submissions: Record<string, SubmissionResponse[]>;  // keyed by assignment_id
  gradeResults: Record<string, GradeResult>;  // keyed by run_id

  setCourses: (courses: Course[]) => void;
  setActiveAssignment: (assignment: Assignment | null) => void;
  addSubmission: (assignmentId: string, submission: SubmissionResponse) => void;
  setGradeResult: (runId: string, result: GradeResult) => void;
  clearCourseData: () => void;
}

// ---------------------------------------------------------------------------
// Slice implementation
// ---------------------------------------------------------------------------

export const createCourseSlice: StateCreator<CourseSlice> = (set) => ({
  courses: [],
  activeAssignment: null,
  submissions: {},
  gradeResults: {},

  setCourses: (courses) => set({ courses }),

  setActiveAssignment: (assignment) => set({ activeAssignment: assignment }),

  addSubmission: (assignmentId, submission) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [assignmentId]: [
          submission,
          ...(state.submissions[assignmentId] ?? []),
        ],
      },
    })),

  setGradeResult: (runId, result) =>
    set((state) => ({
      gradeResults: {
        ...state.gradeResults,
        [runId]: result,
      },
    })),

  clearCourseData: () =>
    set({
      courses: [],
      activeAssignment: null,
      submissions: {},
      gradeResults: {},
    }),
});
