import { create } from "zustand";
import { AuthSlice, createAuthSlice } from "./authSlice";
// JobSlice will be added in plan 01-03

export const useStore = create<AuthSlice>()((...a) => ({
  ...createAuthSlice(...a),
}));
