import { create } from "zustand";
import { persist } from "zustand/middleware";
import { AuthSlice, createAuthSlice } from "./authSlice";
import { JobSlice, createJobSlice } from "./jobSlice";

export type AppStore = AuthSlice & JobSlice;

export const useStore = create<AppStore>()(
  persist(
    (...a) => ({
      ...createAuthSlice(...a),
      ...createJobSlice(...a),
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
