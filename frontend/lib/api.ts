import axios, { AxiosInstance, AxiosRequestConfig } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

export function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: API_URL,
    headers: {
      "Content-Type": "application/json",
    },
  });

  client.interceptors.request.use((config) => {
    const token = getToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("user");
          window.location.href = "/login";
        }
      }
      return Promise.reject(error);
    }
  );

  return client;
}

export const api = createApiClient();

// Auth API
export const authApi = {
  login: (username: string, password: string) =>
    api.post("/auth/login", { username, password }),
  signup: (username: string, password: string) =>
    api.post("/auth/signup", { username, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
};

// Sessions API
export const sessionsApi = {
  list: (includeArchived = false) =>
    api.get(`/sessions?include_archived=${includeArchived}`),
  create: (title = "New Session", llm_model = "gemini") =>
    api.post("/sessions", { title, llm_model }),
  listLlmModels: () => api.get("/sessions/llm-models"),
  get: (id: string) => api.get(`/sessions/${id}`),
  update: (id: string, data: { title?: string; status?: string }) =>
    api.patch(`/sessions/${id}`, data),
  delete: (id: string) => api.delete(`/sessions/${id}`),
};

// Sources API
export const sourcesApi = {
  list: (sessionId: string) => api.get(`/sessions/${sessionId}/sources`),
  uploadFile: (sessionId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post(`/sessions/${sessionId}/sources/upload`, formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  addUrl: (sessionId: string, url: string, displayName?: string) =>
    api.post(`/sessions/${sessionId}/sources/url`, { url, display_name: displayName }),
  addText: (sessionId: string, text: string, displayName: string) =>
    api.post(`/sessions/${sessionId}/sources/text`, { text, display_name: displayName }),
  delete: (sessionId: string, sourceId: string) =>
    api.delete(`/sessions/${sessionId}/sources/${sourceId}`),
};

// Chat API
export const chatApi = {
  getMessages: (sessionId: string) =>
    api.get(`/sessions/${sessionId}/messages`),
  sendMessage: (sessionId: string, message: string) =>
    api.post(`/sessions/${sessionId}/chat`, { message }),
  getAgentRun: (sessionId: string, runId: string) =>
    api.get(`/sessions/${sessionId}/agent-runs/${runId}`),
};

// Skills API
export const skillsApi = {
  list: () => api.get("/skills"),
  upload: (file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return api.post("/skills/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  get: (id: string) => api.get(`/skills/${id}`),
  enable: (id: string) => api.post(`/skills/${id}/enable`),
  disable: (id: string) => api.post(`/skills/${id}/disable`),
  delete: (id: string) => api.delete(`/skills/${id}`),
  enableForSession: (sessionId: string, skillId: string) =>
    api.post(`/sessions/${sessionId}/skills/${skillId}/enable`),
  disableForSession: (sessionId: string, skillId: string) =>
    api.post(`/sessions/${sessionId}/skills/${skillId}/disable`),
};

// Admin API
export const adminApi = {
  getSettings: () => api.get("/admin/settings"),
  updateEmbeddingModel: (model_id: string) =>
    api.put("/admin/settings/embedding-model", { model_id }),
};

// Artifacts API
export const artifactsApi = {
  list: (sessionId: string) => api.get(`/sessions/${sessionId}/artifacts`),
  generate: (sessionId: string, data: {
    artifact_type: string;
    display_name: string;
    content: string;
    columns?: string[];
  }) => api.post(`/sessions/${sessionId}/artifacts/generate`, data),
  downloadUrl: (artifactId: string) => `${API_URL}/artifacts/${artifactId}/download`,
};
