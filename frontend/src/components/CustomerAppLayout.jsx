import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Home,
  Calendar,
  CalendarDays,
  Gift,
  User,
  Menu,
  X,
  Star,
  MapPin,
  Phone,
  Mail,
} from "lucide-react";

// Carlsburg Logo Component
const CarlsburgLogo = ({ size = 40, className = "" }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    className={className}
  >
    <circle cx="50" cy="50" r="45" fill="currentColor" />
    <text
      x="50"
      y="58"
      textAnchor="middle"
      fontSize="36"
      fontFamily="Playfair Display, serif"
      fill="#00280b"
      fontWeight="bold"
    >
      C
    </text>
  </svg>
);

const navItems = [
  { path: "/app", icon: Home, label: "Start" },
  { path: "/app/reservieren", icon: Calendar, label: "Reservieren" },
  { path: "/app/events", icon: CalendarDays, label: "Events" },
  { path: "/app/punkte", icon: Star, label: "Punkte" },
  { path: "/app/praemien", icon: Gift, label: "Prämien" },
];

export const CustomerAppLayout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [customer, setCustomer] = useState(null);

  useEffect(() => {
    // Check if customer is logged in
    const storedCustomer = localStorage.getItem("carlsburg_customer");
    if (storedCustomer) {
      try {
        setCustomer(JSON.parse(storedCustomer));
      } catch (e) {
        localStorage.removeItem("carlsburg_customer");
      }
    }
  }, [location]);

  const isActive = (path) => {
    if (path === "/app") return location.pathname === "/app";
    return location.pathname.startsWith(path);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: "#fafbed" }}>
      {/* Header */}
      <header style={{ backgroundColor: "#00280b" }} className="sticky top-0 z-50 shadow-lg">
        <div className="max-w-lg mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link to="/app" className="flex items-center gap-2">
              <CarlsburgLogo size={36} className="text-[#ffed00]" />
              <div>
                <span 
                  className="text-lg font-bold text-[#ffed00]"
                  style={{ fontFamily: "'Playfair Display', serif" }}
                >
                  Carlsburg
                </span>
              </div>
            </Link>
            
            <div className="flex items-center gap-3">
              {customer ? (
                <Link
                  to="/app/profil"
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm"
                  style={{ backgroundColor: "#ffed00", color: "#00280b" }}
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">{customer.name?.split(" ")[0] || "Profil"}</span>
                </Link>
              ) : (
                <Link
                  to="/app/login"
                  className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium"
                  style={{ backgroundColor: "#ffed00", color: "#00280b" }}
                >
                  <User className="w-4 h-4" />
                  <span>Anmelden</span>
                </Link>
              )}
              
              <button
                className="md:hidden p-2 text-[#ffed00]"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              >
                {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
              </button>
            </div>
          </div>
        </div>
        
        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <nav className="md:hidden border-t border-[#ffed00]/20 px-4 py-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg mb-1 ${
                    isActive(item.path)
                      ? "bg-[#ffed00] text-[#00280b]"
                      : "text-[#fafbed] hover:bg-[#ffed00]/10"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span style={{ fontFamily: "'Lato', sans-serif" }}>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        )}
      </header>

      {/* Desktop Navigation */}
      <nav className="hidden md:block sticky top-[60px] z-40 shadow-sm" style={{ backgroundColor: "#f3f6de" }}>
        <div className="max-w-lg mx-auto px-4">
          <div className="flex justify-around py-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex flex-col items-center gap-1 px-4 py-2 rounded-lg transition-colors ${
                    isActive(item.path)
                      ? "text-[#00280b] font-semibold"
                      : "text-[#00280b]/70 hover:text-[#00280b]"
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="text-xs" style={{ fontFamily: "'Lato', sans-serif" }}>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 max-w-lg mx-auto w-full px-4 py-6">
        {children}
      </main>

      {/* Bottom Navigation (Mobile) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 shadow-[0_-2px_10px_rgba(0,0,0,0.1)]" style={{ backgroundColor: "#f3f6de" }}>
        <div className="flex justify-around py-2 px-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-1 px-3 py-2 rounded-lg min-w-[60px] ${
                  isActive(item.path)
                    ? "text-[#00280b] font-semibold"
                    : "text-[#00280b]/60"
                }`}
              >
                <Icon className="w-5 h-5" />
                <span className="text-[10px]" style={{ fontFamily: "'Lato', sans-serif" }}>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer */}
      <footer className="pb-20 md:pb-0" style={{ backgroundColor: "#002f02" }}>
        <div className="max-w-lg mx-auto px-4 py-8">
          <div className="text-center text-[#fafbed]/80 text-sm space-y-4">
            <div className="flex items-center justify-center gap-2 text-[#ffed00]">
              <CarlsburgLogo size={28} className="text-[#ffed00]" />
              <span style={{ fontFamily: "'Playfair Display', serif" }} className="text-lg font-bold">
                Carlsburg
              </span>
            </div>
            <p style={{ fontFamily: "'Playfair Display', serif" }} className="text-xs">
              Historisches Panoramarestaurant
            </p>
            
            <div className="flex flex-col gap-2 text-xs">
              <div className="flex items-center justify-center gap-2">
                <MapPin className="w-4 h-4" />
                <span>Carlsburg 1, 37308 Heilbad Heiligenstadt</span>
              </div>
              <div className="flex items-center justify-center gap-2">
                <Phone className="w-4 h-4" />
                <a href="tel:+4936064560" className="hover:text-[#ffed00]">+49 3606 4560</a>
              </div>
              <div className="flex items-center justify-center gap-2">
                <Mail className="w-4 h-4" />
                <a href="mailto:info@carlsburg.de" className="hover:text-[#ffed00]">info@carlsburg.de</a>
              </div>
            </div>
            
            <div className="flex justify-center gap-4 pt-2 text-xs">
              <a href="/datenschutz" className="hover:text-[#ffed00]">Datenschutz</a>
              <span>|</span>
              <a href="/impressum" className="hover:text-[#ffed00]">Impressum</a>
            </div>
            
            <p className="text-[10px] text-[#fafbed]/50">
              © {new Date().getFullYear()} Carlsburg. Alle Rechte vorbehalten.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default CustomerAppLayout;
