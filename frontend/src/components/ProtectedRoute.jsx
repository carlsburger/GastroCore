import React from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Loader2 } from "lucide-react";

export const ProtectedRoute = ({ children, roles = [] }) => {
  const { user, loading, isAuthenticated, hasRole } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  // Determine if we're in service area
  const isServiceArea = location.pathname.startsWith("/service");
  
  // Seiten die für ALLE authentifizierten Benutzer erlaubt sind (inkl. Mitarbeiter)
  const publicAuthPages = [
    "/login",
    "/no-access", 
    "/change-password",
    "/my-shifts",  // MyShifts ist für alle Mitarbeiter erlaubt
  ];
  const isPublicAuthPage = publicAuthPages.some(p => location.pathname === p || location.pathname.startsWith(p));
  
  const isAdminArea = !isServiceArea && !isPublicAuthPage;

  if (!isAuthenticated) {
    // Alle nicht-authentifizierten Benutzer zum Unified Login
    return <Navigate to="/login" replace />;
  }

  // Check if user needs to change password
  if (user?.must_change_password && location.pathname !== "/change-password") {
    return <Navigate to="/change-password" replace />;
  }

  // ============== ROLLEN-GUARDS ==============
  
  // Mitarbeiter: Kein Zugriff auf Admin oder Service, ABER /my-shifts ist erlaubt
  if (user?.role === "mitarbeiter") {
    if (isAdminArea || isServiceArea) {
      // Redirect zu MyShifts statt no-access (bessere UX)
      return <Navigate to="/my-shifts" replace />;
    }
  }
  
  // Service-User: Nur Service-Bereich erlaubt
  if (user?.role === "service") {
    if (isAdminArea && !isServiceArea) {
      return <Navigate to="/service" replace />;
    }
  }

  // Check role access für spezifische Routen
  if (roles.length > 0 && !roles.some((role) => hasRole(role))) {
    // Service users trying to access admin-only areas
    if (user?.role === "service") {
      return <Navigate to="/service" replace />;
    }
    // Mitarbeiter trying to access restricted area
    if (user?.role === "mitarbeiter") {
      return <Navigate to="/no-access" replace />;
    }
    return <Navigate to="/" replace />;
  }

  return children;
};

export default ProtectedRoute;
