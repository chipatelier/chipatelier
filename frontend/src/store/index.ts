import { create } from "zustand";
import { AuthSlice, createAuthSlice } from "./authSlice";
import { JobSlice, createJobSlice } from "./jobSlice";

export type AppStore = AuthSlice & JobSlice;

export const useStore = create<AppStore>()((...a) => ({
  ...createAuthSlice(...a),
  ...createJobSlice(...a),
}));
