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
// Service Terminal (Sprint 8)
import ServiceTerminal from "./pages/ServiceTerminal";
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
// Staff Module (Sprint 5)
import Staff from "./pages/Staff";
import StaffDetail from "./pages/StaffDetail";
import Schedule from "./pages/Schedule";
import MyShifts from "./pages/MyShifts";
// Tax Office Module (Sprint 6)
import TaxOfficeExports from "./pages/TaxOfficeExports";
// Marketing Module (Sprint 8)
import Marketing from "./pages/Marketing";
import Unsubscribe from "./pages/Unsubscribe";
// AI Assistant Module (Sprint 9)
import AIAssistant from "./pages/AIAssistant";
// Reservation Config Module (Sprint: Reservierung Live-Ready)
import ReservationConfig from "./pages/ReservationConfig";
// Reservation Calendar (Sprint: Admin Kalender)
import ReservationCalendar from "./pages/ReservationCalendar";
// Tischplan (Sprint: Service-Terminal Erweiterungen)
import TablePlan from "./pages/TablePlan";
import TablePlanPrint from "./pages/TablePlanPrint";
// Tisch-Stammdaten Admin (Sprint: Tischplan & Belegung)
import TableAdmin from "./pages/TableAdmin";
// System Settings & Opening Hours Master Module
import SystemSettings from "./pages/SystemSettings";
import OpeningHoursAdmin from "./pages/OpeningHoursAdmin";
// Backup & Export Module
import BackupExport from "./pages/BackupExport";
// Table Import Module
import TableImport from "./pages/TableImport";
// Service Terminal Standalone (Sprint: Service-Terminal getrennt & abgesichert)
import ServiceLogin from "./pages/ServiceLogin";
import ServiceApp from "./pages/ServiceApp";
import "./App.css";

// No Backoffice Access for Mitarbeiter
const NoAccess = () => (
  <div className="min-h-screen flex items-center justify-center bg-[#FAFBE0] p-4">
    <div className="text-center">
      <div className="w-16 h-16 rounded-full bg-[#005500] mx-auto flex items-center justify-center mb-4">
        <span className="text-[#FFFF00] font-serif text-3xl font-bold">C</span>
      </div>
      <h1 className="font-serif text-3xl font-bold text-[#005500] mb-2">Carlsburg Cockpit</h1>
      <p className="text-[#005500]/70 mb-4">
        Als Mitarbeiter haben Sie keinen Zugriff auf das Backoffice.
      </p>
      <p className="text-sm text-[#005500]/50">
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
          <Route path="/unsubscribe/:customerId" element={<Unsubscribe />} />
          {/* Public Events */}
          <Route path="/events-public" element={<PublicEventsList />} />
          <Route path="/event/:eventId" element={<PublicEventDetail />} />
          <Route path="/event/:eventId/book" element={<PublicEventBooking />} />
          
          {/* Change Password (authenticated but no role check) */}
          <Route
            path="/change-password"
            element={
              <ProtectedRoute>
                <ChangePassword />
              </ProtectedRoute>
            }
          />

          {/* Meine Schichten - Für alle authentifizierten Benutzer */}
          <Route
            path="/my-shifts"
            element={
              <ProtectedRoute>
                <MyShifts />
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

          {/* Service Terminal - Admin & Schichtleiter (Legacy Route) */}
          <Route
            path="/service-terminal"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter", "service"]}>
                <ServiceTerminal />
              </ProtectedRoute>
            }
          />

          {/* ============================================================ */}
          {/* SERVICE TERMINAL STANDALONE - Separater Bereich für Kellner  */}
          {/* Sprint: Service-Terminal getrennt & abgesichert (iPad)       */}
          {/* ============================================================ */}
          
          {/* Service Login - Public, aber eigener Login-Screen */}
          <Route path="/service/login" element={<ServiceLogin />} />
          
          {/* Service App Wrapper mit Nested Routes */}
          <Route
            path="/service"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter", "service"]}>
                <ServiceApp />
              </ProtectedRoute>
            }
          >
            {/* Service Hauptansicht (Heute) */}
            <Route index element={<ServiceTerminal standalone />} />
            {/* Tischplan im Service-Bereich */}
            <Route path="tischplan" element={<TablePlan standalone />} />
            {/* Warteliste im Service-Bereich */}
            <Route path="warteliste" element={<Waitlist standalone />} />
            {/* Walk-in Schnellerfassung */}
            <Route path="walkin" element={<ServiceTerminal walkInMode standalone />} />
          </Route>

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

          {/* System Settings - Admin only */}
          <Route
            path="/admin/settings/system"
            element={
              <ProtectedRoute roles={["admin"]}>
                <SystemSettings />
              </ProtectedRoute>
            }
          />

          {/* Opening Hours Admin - Admin only */}
          <Route
            path="/admin/settings/opening-hours"
            element={
              <ProtectedRoute roles={["admin"]}>
                <OpeningHoursAdmin />
              </ProtectedRoute>
            }
          />

          {/* Backup & Export - Admin only */}
          <Route
            path="/admin/settings/backup"
            element={
              <ProtectedRoute roles={["admin"]}>
                <BackupExport />
              </ProtectedRoute>
            }
          />

          {/* Table Import - Admin only */}
          <Route
            path="/admin/reservations/import"
            element={
              <ProtectedRoute roles={["admin"]}>
                <TableImport />
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
            path="/events"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Events />
              </ProtectedRoute>
            }
          />
          <Route
            path="/aktionen"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Events category="AKTION" />
              </ProtectedRoute>
            }
          />
          <Route
            path="/menue-aktionen"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Events category="AKTION_MENUE" />
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

          {/* Payment Module - Admin & Schichtleiter */}
          <Route
            path="/payments"
            element={
              <ProtectedRoute roles={["admin"]}>
                <PaymentRules />
              </ProtectedRoute>
            }
          />
          <Route
            path="/payments/transactions"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <PaymentTransactions />
              </ProtectedRoute>
            }
          />
          {/* Public Payment Routes */}
          <Route path="/payment/success" element={<PaymentSuccess />} />
          <Route path="/payment/cancel" element={<PaymentCancel />} />

          {/* Staff Module (Sprint 5) - Admin & Schichtleiter */}
          <Route
            path="/staff"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Staff />
              </ProtectedRoute>
            }
          />
          <Route
            path="/staff/:memberId"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <StaffDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/schedule"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Schedule />
              </ProtectedRoute>
            }
          />

          {/* Tax Office Module (Sprint 6) - Admin only */}
          <Route
            path="/taxoffice"
            element={
              <ProtectedRoute roles={["admin"]}>
                <TaxOfficeExports />
              </ProtectedRoute>
            }
          />

          {/* Marketing Module (Sprint 8) - Admin & Schichtleiter */}
          <Route
            path="/marketing"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <Marketing />
              </ProtectedRoute>
            }
          />

          {/* Reservierungsübersicht - Weiterleitung zu Service-Terminal */}
          <Route
            path="/reservations"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <ServiceTerminal />
              </ProtectedRoute>
            }
          />

          {/* AI Assistant Module (Sprint 9) - Admin & Schichtleiter */}
          <Route
            path="/ai-assistant"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <AIAssistant />
              </ProtectedRoute>
            }
          />

          {/* Reservation Config Module (Sprint: Reservierung Live-Ready) - Admin only */}
          <Route
            path="/reservation-config"
            element={
              <ProtectedRoute roles={["admin"]}>
                <ReservationConfig />
              </ProtectedRoute>
            }
          />

          {/* Reservation Calendar (Sprint: Admin Kalender) - Admin & Schichtleiter */}
          <Route
            path="/reservation-calendar"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <ReservationCalendar />
              </ProtectedRoute>
            }
          />

          {/* Tischplan (Sprint: Service-Terminal Erweiterungen) - Admin & Schichtleiter */}
          <Route
            path="/table-plan"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <TablePlan />
              </ProtectedRoute>
            }
          />

          {/* Tischplan Druckansicht (Sprint: Tischplan Druck) */}
          <Route
            path="/table-plan/print"
            element={
              <ProtectedRoute roles={["admin", "schichtleiter"]}>
                <TablePlanPrint />
              </ProtectedRoute>
            }
          />

          {/* Tisch-Stammdaten Admin (Sprint: Tischplan & Belegung) - Admin only */}
          <Route
            path="/table-admin"
            element={
              <ProtectedRoute roles={["admin"]}>
                <TableAdmin />
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
