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
import Settings from "./pages/Settings";
import ConfirmReservation from "./pages/ConfirmReservation";
import MessageLogs from "./pages/MessageLogs";
// Events Module (Sprint 4)
import Events from "./pages/Events";
import EventProducts from "./pages/EventProducts";
import EventBookings from "./pages/EventBookings";
import PublicEventsList from "./pages/PublicEventsList";
import PublicEventDetail from "./pages/PublicEventDetail";
import PublicEventBooking from "./pages/PublicEventBooking";
// Payment Module (Sprint 4)
import PaymentRules from "./pages/PaymentRules";
import PaymentTransactions from "./pages/PaymentTransactions";
import { PaymentSuccess, PaymentCancel } from "./pages/PaymentPages";
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
          {/* Public Routes - No Authentication Required */}
          <Route path="/login" element={<Login />} />
          <Route path="/book" element={<BookingWidget />} />
          <Route path="/cancel/:reservationId" element={<CancelReservation />} />
          <Route path="/confirm/:reservationId" element={<ConfirmReservation />} />
          {/* Public Events */}
          <Route path="/events-public" element={<PublicEventsList />} />
          <Route path="/events/:eventId" element={<PublicEventDetail />} />
          <Route path="/events/:eventId/book" element={<PublicEventBooking />} />
          
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

          {/* Waitlist - Admin & Schichtleiter */}
          <Route
            path="/waitlist"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Waitlist />
              </ProtectedRoute>
            }
          />

          {/* Guests - Admin & Schichtleiter */}
          <Route
            path="/guests"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Guests />
              </ProtectedRoute>
            }
          />

          {/* Settings - Admin only */}
          <Route
            path="/settings"
            element={
              <ProtectedRoute roles={["admin"]}>
                <Settings />
              </ProtectedRoute>
            }
          />

          {/* Message Logs - Admin only */}
          <Route
            path="/message-logs"
            element={
              <ProtectedRoute roles={["admin"]}>
                <MessageLogs />
              </ProtectedRoute>
            }
          />

          {/* Events Management - Admin & Schichtleiter */}
          <Route
            path="/events-admin"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Events />
              </ProtectedRoute>
            }
          />
          <Route
            path="/events/:eventId/products"
            element={
              <ProtectedRoute roles={["admin"]}>
                <EventProducts />
              </ProtectedRoute>
            }
          />
          <Route
            path="/events/:eventId/bookings"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <EventBookings />
              </ProtectedRoute>
            }
          />

          {/* Catch all - redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
