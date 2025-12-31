/**
 * PublicLayout.jsx - Layout für öffentliche Seiten ohne Cockpit-Navigation
 * 
 * Verwendet für:
 * - /book (Buchungswidget)
 * - /book?preview=1 (Admin-Preview)
 * - Andere öffentliche Seiten
 * 
 * KEINE Cockpit-Sidebar, KEINE Admin-Navigation
 * Das BookingWidget hat seinen eigenen Panorama-Hintergrund und 100vh Layout.
 */

import React from "react";
import { useSearchParams, useLocation } from "react-router-dom";

export default function PublicLayout({ children }) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const isPreview = searchParams.get("preview") === "1";
  
  // BookingWidget (/book) hat eigenes 100vh Layout
  const isBookingWidget = location.pathname === "/book";

  // Für BookingWidget: minimales Wrapper ohne zusätzlichen Hintergrund, 100vh
  if (isBookingWidget) {
    return (
      <div className="h-screen w-screen overflow-hidden">
        {/* Preview-Banner (nur wenn preview=1) */}
        {isPreview && (
          <div className="fixed top-0 left-0 right-0 z-50 bg-[#005500] text-white py-1.5 px-4 text-center text-xs">
            <span className="font-medium">
              🔍 Preview-Modus
            </span>
            <span className="ml-2 text-white/70">
              (Nur im Preview sichtbar)
            </span>
          </div>
        )}
        <div className={isPreview ? "pt-8" : ""}>
          {children}
        </div>
      </div>
    );
  }

  // Für andere öffentliche Seiten: Standard-Layout
  return (
    <div className="min-h-screen bg-gradient-to-b from-[#FAFBE0] to-white">
      {isPreview && (
        <div className="bg-[#005500] text-white py-2 px-4 text-center text-sm">
          <span className="font-medium">🔍 Preview-Modus</span>
        </div>
      )}
      <main className="w-full">{children}</main>
      <footer className="py-4 text-center text-xs text-gray-500">
        © {new Date().getFullYear()} Carlsburg
      </footer>
    </div>
  );
}
