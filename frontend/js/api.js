/**
 * API Service Client
 * Handles HTTP requests, JWT token attachment, error toasts, and response parsing.
 */

const API_BASE = "http://127.0.0.1:8000/api/v1";

const api = {
  getToken() {
    return localStorage.getItem("payroll_token");
  },

  setToken(token) {
    localStorage.setItem("payroll_token", token);
  },

  getUser() {
    const u = localStorage.getItem("payroll_user");
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    localStorage.setItem("payroll_user", JSON.stringify(user));
  },

  clearSession() {
    localStorage.removeItem("payroll_token");
    localStorage.removeItem("payroll_user");
  },

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = options.headers || {};

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const token = this.getToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(url, { ...options, headers });

      if (response.status === 401) {
        this.clearSession();
        window.location.hash = "#login";
        window.renderApp();
        throw new Error("Session expired. Please log in again.");
      }

      if (response.status === 204) return null;

      const isJson = (response.headers.get("content-type") || "").includes("application/json");
      const data = isJson ? await response.json() : await response.blob();

      if (!response.ok) {
        const errorMsg = data.detail || (typeof data === "string" ? data : "Request failed");
        throw new Error(errorMsg);
      }

      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  get(endpoint) {
    return this.request(endpoint, { method: "GET" });
  },

  post(endpoint, body) {
    return this.request(endpoint, {
      method: "POST",
      body: JSON.stringify(body)
    });
  },

  patch(endpoint, body) {
    return this.request(endpoint, {
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined
    });
  },

  delete(endpoint) {
    return this.request(endpoint, { method: "DELETE" });
  },

  async download(endpoint, defaultFilename = "download.pdf") {
    const url = `${API_BASE}${endpoint}`;
    const token = this.getToken();
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Download failed" }));
      throw new Error(err.detail || "Download failed");
    }
    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = defaultFilename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(blobUrl);
  }
};
