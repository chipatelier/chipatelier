import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AuthSlice, createAuthSlice } from "./authSlice";
import { JobSlice, createJobSlice } from "./jobSlice";
import { CourseSlice, createCourseSlice } from "./courseSlice";

export type AppStore = AuthSlice & JobSlice & CourseSlice;

export const useStore = create<AppStore>()(
  persist(
    (...a) => ({
      ...createAuthSlice(...a),
      ...createJobSlice(...a),
      ...createCourseSlice(...a),
    }),
    {
      name: "chipatelier-store",
      // Only persist auth state (user and accessToken)
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
      }),
    }
  )
);
