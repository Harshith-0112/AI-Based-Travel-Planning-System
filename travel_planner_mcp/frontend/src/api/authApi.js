import { apiClient, getApiError, TOKEN_KEY } from "./client";

export async function registerUser(payload) {
  try {
    const { data } = await apiClient.post("/auth/signup", payload);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function loginUser(email, password) {
  try {
    const form = new URLSearchParams();
    form.append("username", email);
    form.append("password", password);
    const { data } = await apiClient.post("/auth/login", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    localStorage.setItem(TOKEN_KEY, data.access_token);
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export async function getCurrentUser() {
  try {
    const { data } = await apiClient.get("/auth/me");
    return data;
  } catch (error) {
    throw new Error(getApiError(error));
  }
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}
