import axios from "axios";

const TOKEN_KEY = "leavedesk.token";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    const isAuthCall =
      url.includes("/auth/login") || url.includes("/auth/register");

    if (error.response?.status === 401 && !isAuthCall) {
      localStorage.removeItem(TOKEN_KEY);
      if (window.location.pathname !== "/login") {
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);

export function apiError(error) {
  const data = error.response?.data;
  return {
    message:
      data?.message ||
      (error.code === "ERR_NETWORK"
        ? "Could not reach the server. Is the API running on port 5001?"
        : "Something went wrong. Please try again."),
    errors: data?.errors || {},
  };
}

export { TOKEN_KEY };
export default api;
