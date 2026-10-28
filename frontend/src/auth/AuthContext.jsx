import { createContext, useContext, useEffect, useState } from "react";
import api, { TOKEN_KEY } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [booting, setBooting] = useState(Boolean(token));

  useEffect(() => {
    let cancelled = false;

    if (!token) {
      setUser(null);
      setBooting(false);
      return undefined;
    }

    api
      .get("/auth/me")
      .then(({ data }) => {
        if (!cancelled) setUser(data.user);
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY);
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (!cancelled) setBooting(false);
      });

    return () => {
      cancelled = true;
    };
  }, [token]);

  function persistSession(data) {
    localStorage.setItem(TOKEN_KEY, data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    setBooting(false);
  }

  async function login(email, password) {
    const { data } = await api.post("/auth/login", { email, password });
    persistSession(data);
    return data.user;
  }

  async function register(payload) {
    const { data } = await api.post("/auth/register", payload);
    persistSession(data);
    return data.user;
  }

  function logout() {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{ user, token, booting, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
