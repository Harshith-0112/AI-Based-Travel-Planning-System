import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const TOKEN_KEY = "ai_travel_token";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000,
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export function getApiError(error) {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).join(", ");
  }
  if (typeof detail === "string") {
    return detail;
  }
  return error?.message || "Something went wrong. Please try again.";
}
