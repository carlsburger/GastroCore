import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { authApi } from "../lib/api";

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load user from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");
    
    if (token && savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {
        localStorage.removeItem("token");
        localStorage.removeItem("user");
      }
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authApi.login(email, password);
      const { access_token, user: userData } = response.data;
      
      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(userData));
      setUser(userData);
      
      return userData;
    } catch (err) {
      const message = err.response?.data?.detail || "Anmeldung fehlgeschlagen";
      setError(message);
      throw new Error(message);
    }
  };

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
  }, []);

  const updateUser = (userData) => {
    localStorage.setItem("user", JSON.stringify(userData));
    setUser(userData);
  };

  const hasRole = useCallback((...roles) => {
    if (!user) return false;
    return roles.includes(user.role);
  }, [user]);

  const isAdmin = useCallback(() => hasRole("admin"), [hasRole]);
  const isSchichtleiter = useCallback(() => hasRole("admin", "schichtleiter"), [hasRole]);

  const value = {
    user,
    loading,
    error,
    login,
    logout,
    updateUser,
    hasRole,
    isAdmin,
    isSchichtleiter,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export default AuthContext;
