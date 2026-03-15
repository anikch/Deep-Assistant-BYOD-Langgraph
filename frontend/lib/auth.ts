export interface AuthUser {
  user_id: string;
  username: string;
  is_admin: boolean;
  access_token: string;
}

export function saveAuth(data: { access_token: string; user_id: string; username: string; is_admin: boolean }) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("user", JSON.stringify({
    user_id: data.user_id,
    username: data.username,
    is_admin: data.is_admin,
  }));
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  const token = localStorage.getItem("access_token");
  const userStr = localStorage.getItem("user");
  if (!token || !userStr) return null;
  try {
    const user = JSON.parse(userStr);
    return { ...user, access_token: token };
  } catch {
    return null;
  }
}

export function clearAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("user");
}

export function isAuthenticated(): boolean {
  return !!getStoredUser();
}
