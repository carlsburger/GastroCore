import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Toaster } from "./components/ui/sonner";
import Login from "./pages/Login";
import ChangePassword from "./pages/ChangePassword";
import Dashboard from "./pages/Dashboard";
import Areas from "./pages/Areas";
import Users from "./pages/Users";
import AuditLog from "./pages/AuditLog";
import CancelReservation from "./pages/CancelReservation";
import BookingWidget from "./pages/BookingWidget";
import Waitlist from "./pages/Waitlist";
import Guests from "./pages/Guests";
import "./App.css";

// No Backoffice Access for Mitarbeiter
const NoAccess = () => (
  <div className="min-h-screen flex items-center justify-center bg-background p-4">
    <div className="text-center">
      <div className="w-16 h-16 rounded-full bg-primary mx-auto flex items-center justify-center mb-4">
        <span className="text-primary-foreground font-serif text-3xl font-bold">G</span>
      </div>
      <h1 className="font-serif text-3xl font-medium text-primary mb-2">GastroCore</h1>
      <p className="text-muted-foreground mb-4">
        Als Mitarbeiter haben Sie keinen Zugriff auf das Backoffice.
      </p>
      <p className="text-sm text-muted-foreground">
        Bitte wenden Sie sich an Ihren Schichtleiter oder Administrator.
      </p>
    </div>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<Login />} />
          
          {/* Change Password (authenticated but no role check) */}
          <Route
            path="/change-password"
            element={
              <ProtectedRoute>
                <ChangePassword />
              </ProtectedRoute>
            }
          />

          {/* Dashboard - Admin & Schichtleiter */}
          <Route
            path="/"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Areas - Admin only */}
          <Route
            path="/areas"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Areas />
              </ProtectedRoute>
            }
          />

          {/* Users - Admin only */}
          <Route
            path="/users"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Users />
              </ProtectedRoute>
            }
          />

          {/* Audit Log - Admin only */}
          <Route
            path="/audit"
            element={
              <ProtectedRoute roles={["admin"]}>
                <AuditLog />
              </ProtectedRoute>
            }
          />

          {/* No Access Page for Mitarbeiter */}
          <Route
            path="/no-access"
            element={
              <ProtectedRoute>
                <NoAccess />
              </ProtectedRoute>
            }
          />

          {/* Public Cancellation Page */}
          <Route path="/cancel/:reservationId" element={<CancelReservation />} />

          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
