import { StateCreator } from "zustand";
import { UserResponse } from "../api/auth";

export interface AuthSlice {
  user: UserResponse | null;
  accessToken: string | null;
  setAuth: (user: UserResponse, token: string) => void;
  clearAuth: () => void;
  setAccessToken: (token: string) => void;
}

export const createAuthSlice: StateCreator<AuthSlice> = (set) => ({
  user: null,
  accessToken: null,
  setAuth: (user: UserResponse, token: string) => set({ user, accessToken: token }),
  clearAuth: () => set({ user: null, accessToken: null }),
  setAccessToken: (token: string) => set({ accessToken: token }),
});
