/**
 * Typed API client for course, leaderboard, and instructor dashboard endpoints.
 */
import { apiClient } from "./client";
import { Course } from "../store/courseSlice";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface LeaderboardEntry {
  rank: number;
  score: number | null;
  wns: number | null;
  user_id: string;
  is_self: boolean;
}

export interface StudentProgress {
  display_name: string;
  user_id: string;
  run_count: number;
  last_run_status: string | null;
  submission_status: "submitted" | "not_submitted";
  score: number | null;
}

export interface QueueInfo {
  queued: number;
  running: number;
}

export interface DashboardResponse {
  students: StudentProgress[];
  queue_info: QueueInfo;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

/**
 * List courses for the current user (enrolled or teaching).
 */
export async function getCourses(): Promise<Course[]> {
  const { data } = await apiClient.get<Course[]>("/courses");
  return data;
}

/**
 * Get the anonymous leaderboard for an assignment.
 * Returns entries ordered by score DESC, WNS DESC (tiebreaker).
 */
export async function getLeaderboard(assignmentId: string): Promise<LeaderboardEntry[]> {
  const { data } = await apiClient.get<LeaderboardEntry[]>(
    `/assignments/${assignmentId}/leaderboard`
  );
  return data;
}

/**
 * Get per-student progress dashboard data for a course (instructor only).
 */
export async function getDashboard(courseId: string): Promise<DashboardResponse> {
  const { data } = await apiClient.get<DashboardResponse>(
    `/courses/${courseId}/dashboard`
  );
  return data;
}

/**
 * Returns the URL for the CSV export download link.
 * Use as `<a href={getDashboardExportUrl(courseId)} download>Export</a>`.
 */
export function getDashboardExportUrl(courseId: string): string {
  return `/api/v1/courses/${courseId}/dashboard/export`;
}
