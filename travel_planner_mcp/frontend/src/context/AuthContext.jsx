import { createContext, useContext, useEffect, useMemo, useState } from "react";

import { clearToken, getCurrentUser, getStoredToken, loginUser } from "../api/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(getStoredToken());
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(Boolean(token));

  useEffect(() => {
    let active = true;
    async function loadUser() {
      if (!token) {
        setInitializing(false);
        return;
      }
      try {
        const currentUser = await getCurrentUser();
        if (active) {
          setUser(currentUser);
        }
      } catch {
        clearToken();
        if (active) {
          setToken(null);
          setUser(null);
        }
      } finally {
        if (active) {
          setInitializing(false);
        }
      }
    }
    loadUser();
    return () => {
      active = false;
    };
  }, [token]);

  async function login(email, password) {
    const response = await loginUser(email, password);
    setToken(response.access_token);
    const currentUser = await getCurrentUser();
    setUser(currentUser);
    return currentUser;
  }

  function logout() {
    clearToken();
    setToken(null);
    setUser(null);
  }

  const value = useMemo(
    () => ({
      token,
      user,
      initializing,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
    }),
    [token, user, initializing],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
