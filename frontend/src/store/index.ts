import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AuthSlice, createAuthSlice } from "./authSlice";
import { JobSlice, createJobSlice } from "./jobSlice";
import { CourseSlice, createCourseSlice } from "./courseSlice";
import { AiSlice, createAiSlice } from "./aiSlice";

export type AppStore = AuthSlice & JobSlice & CourseSlice & AiSlice;

export const useStore = create<AppStore>()(
  persist(
    (...a) => ({
      ...createAuthSlice(...a),
      ...createJobSlice(...a),
      ...createCourseSlice(...a),
      ...createAiSlice(...a),
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
