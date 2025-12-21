import axios from "axios";

// Dynamische Backend-URL: Wenn REACT_APP_BACKEND_URL gesetzt ist, nutze diese,
// ansonsten nutze relative URL (für Produktion hinter einem Reverse Proxy)
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api` : "/api";

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: (email, password) => api.post("/auth/login", { email, password }),
  getMe: () => api.get("/auth/me"),
  changePassword: (currentPassword, newPassword) =>
    api.post("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),
};

// Users API
export const usersApi = {
  getAll: () => api.get("/users"),
  create: (data) => api.post("/users", data),
  delete: (id) => api.delete(`/users/${id}`),
};

// Areas API
export const areasApi = {
  getAll: () => api.get("/areas"),
  create: (data) => api.post("/areas", data),
  update: (id, data) => api.put(`/areas/${id}`, data),
  delete: (id) => api.delete(`/areas/${id}`),
};

// Reservations API
export const reservationsApi = {
  getAll: (params = {}) => api.get("/reservations", { params }),
  getOne: (id) => api.get(`/reservations/${id}`),
  create: (data) => api.post("/reservations", data),
  update: (id, data) => api.put(`/reservations/${id}`, data),
  updateStatus: (id, status) =>
    api.patch(`/reservations/${id}/status`, null, { params: { new_status: status } }),
  delete: (id) => api.delete(`/reservations/${id}`),
};

// Settings API
export const settingsApi = {
  getAll: () => api.get("/settings"),
  save: (data) => api.post("/settings", data),
};

// Audit Log API
export const auditApi = {
  getAll: (params = {}) => api.get("/audit-logs", { params }),
};

// Seed API
export const seedApi = {
  seed: () => api.post("/seed"),
};

export default api;
