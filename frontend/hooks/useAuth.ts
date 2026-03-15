"use client";

import { create } from "zustand";
import { AuthUser, getStoredUser, saveAuth, clearAuth } from "@/lib/auth";
import { authApi } from "@/lib/api";

interface AuthState {
  user: AuthUser | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  signup: (username: string, password: string) => Promise<void>;
  logout: () => void;
  initialize: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  initialize: () => {
    const user = getStoredUser();
    set({ user, isLoading: false });
  },

  login: async (username: string, password: string) => {
    const res = await authApi.login(username, password);
    const data = res.data;
    saveAuth(data);
    set({
      user: {
        user_id: data.user_id,
        username: data.username,
        is_admin: data.is_admin,
        access_token: data.access_token,
      },
    });
  },

  signup: async (username: string, password: string) => {
    const res = await authApi.signup(username, password);
    const data = res.data;
    saveAuth(data);
    set({
      user: {
        user_id: data.user_id,
        username: data.username,
        is_admin: data.is_admin,
        access_token: data.access_token,
      },
    });
  },

  logout: () => {
    clearAuth();
    set({ user: null });
  },
}));
