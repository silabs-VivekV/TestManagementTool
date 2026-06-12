import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

// Serialize array params as repeated keys (e.g. ?release_version=a&release_version=b)
// so FastAPI parses them as list[str], not "a[]=...".
export const api = axios.create({
  baseURL,
  paramsSerializer: { indexes: null },
});

const TOKEN_KEY = "tt_token";

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error?.response?.status === 401 && getToken()) {
      setToken(null);
      if (!window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);
