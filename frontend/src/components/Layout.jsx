import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { t } from "../lib/i18n";
import { Button } from "./ui/button";
import {
  LayoutDashboard,
  CalendarDays,
  MapPin,
  Users,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Clock,
  UserX,
  Mail,
  Calendar,
  CreditCard,
  UserCog,
  CalendarClock,
  Building2,
  Utensils,
  Megaphone,
  Bot,
} from "lucide-react";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "nav.dashboard", roles: ["admin", "schichtleiter"] },
  { path: "/service-terminal", icon: Utensils, label: "Service-Terminal", roles: ["admin", "schichtleiter"] },
  { path: "/table-plan", icon: MapPin, label: "Tischplan", roles: ["admin", "schichtleiter"] },
  { path: "/events-admin", icon: Calendar, label: "nav.events", roles: ["admin", "schichtleiter"] },
  { path: "/marketing", icon: Megaphone, label: "Marketing", roles: ["admin", "schichtleiter"] },
  { path: "/ai-assistant", icon: Bot, label: "KI-Assistent", roles: ["admin", "schichtleiter"] },
  { path: "/schedule", icon: CalendarClock, label: "nav.schedule", roles: ["admin", "schichtleiter"] },
  { path: "/staff", icon: UserCog, label: "nav.staff", roles: ["admin", "schichtleiter"] },
  { path: "/reservation-config", icon: Clock, label: "Reservierungs-Konfig", roles: ["admin"] },
  { path: "/taxoffice", icon: Building2, label: "nav.taxoffice", roles: ["admin"] },
  { path: "/payments", icon: CreditCard, label: "nav.payments", roles: ["admin"] },
  { path: "/waitlist", icon: Clock, label: "nav.waitlist", roles: ["admin", "schichtleiter"] },
  { path: "/guests", icon: UserX, label: "nav.guests", roles: ["admin", "schichtleiter"] },
  { path: "/areas", icon: MapPin, label: "nav.areas", roles: ["admin"] },
  { path: "/users", icon: Users, label: "nav.users", roles: ["admin"] },
  { path: "/audit", icon: FileText, label: "nav.auditLog", roles: ["admin"] },
  { path: "/settings", icon: Settings, label: "nav.settings", roles: ["admin"] },
  { path: "/message-logs", icon: Mail, label: "nav.messageLogs", roles: ["admin"] },
];

// Carlsburg Logo Component (simplified building with curved base)
const CarlsburgLogo = ({ size = 40, className = "" }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 100 100"
    className={className}
    xmlns="http://www.w3.org/2000/svg"
  >
    {/* Building with curved base */}
    <path
      d="M50 10 L70 30 L70 60 L30 60 L30 30 Z"
      fill="currentColor"
    />
    {/* Roof peak */}
    <path
      d="M50 5 L75 30 L70 30 L50 10 L30 30 L25 30 Z"
      fill="currentColor"
    />
    {/* Window */}
    <rect x="42" y="35" width="16" height="12" fill="#005500" />
    <line x1="50" y1="35" x2="50" y2="47" stroke="#FFFF00" strokeWidth="2" />
    <line x1="42" y1="41" x2="58" y2="41" stroke="#FFFF00" strokeWidth="2" />
    {/* Curved base */}
    <path
      d="M10 85 Q50 60 90 85"
      stroke="currentColor"
      strokeWidth="6"
      fill="none"
    />
    {/* Door */}
    <rect x="44" y="50" width="12" height="10" fill="#005500" />
  </svg>
);

export const Layout = ({ children }) => {
  const { user, logout, hasRole } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);
  const [buildId, setBuildId] = React.useState(null);

  // Fetch build info for admin/schichtleiter
  React.useEffect(() => {
    if (hasRole("admin") || hasRole("schichtleiter")) {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || "";
      fetch(`${backendUrl}/api/version`)
        .then((res) => res.json())
        .then((data) => setBuildId(data.build_id))
        .catch(() => setBuildId(null));
    }
  }, [hasRole]);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const filteredNavItems = navItems.filter((item) =>
    item.roles.some((role) => hasRole(role))
  );

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-[#005500] text-[#FAFBE0]">
        <div className="flex h-16 items-center justify-between px-4 md:px-8">
          <div className="flex items-center gap-4">
            <button
              className="md:hidden p-2 hover:bg-[#003300] rounded-lg"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              data-testid="mobile-menu-toggle"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <Link to="/" className="flex items-center gap-3">
              <CarlsburgLogo size={40} className="text-[#FFFF00]" />
              <div className="hidden sm:block">
                <span className="font-serif text-xl font-bold text-[#FFFF00] block leading-tight">
                  Carlsburg
                </span>
                <span className="text-xs text-[#FAFBE0]/80 block">
                  Cockpit
                </span>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden lg:flex items-center gap-1">
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.path.replace("/", "") || "dashboard"}`}
                  className={`flex items-center gap-2 px-3 py-2 rounded-full text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-[#FFFF00] text-[#005500]"
                      : "hover:bg-[#003300] text-[#FAFBE0]"
                  }`}
                >
                  <Icon size={16} />
                  {t(item.label)}
                </Link>
              );
            })}
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-[#FAFBE0]">{user?.name}</p>
              <p className="text-xs text-[#FAFBE0]/70 capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              data-testid="logout-button"
              className="rounded-full text-[#FAFBE0] hover:bg-[#003300] hover:text-[#FFFF00]"
            >
              <LogOut size={18} />
              <span className="hidden sm:inline ml-2">{t("nav.logout")}</span>
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="lg:hidden border-t border-[#003300] bg-[#005500] p-4 animate-fade-in">
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-[#FFFF00] text-[#005500]"
                      : "hover:bg-[#003300] text-[#FAFBE0]"
                  }`}
                >
                  <Icon size={20} />
                  {t(item.label)}
                </Link>
              );
            })}
          </nav>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 md:p-8 max-w-7xl mx-auto w-full">{children}</main>

      {/* Footer */}
      <footer className="border-t border-border bg-[#005500] text-[#FAFBE0] mt-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-3">
              <CarlsburgLogo size={32} className="text-[#FFFF00]" />
              <div>
                <span className="font-serif text-lg font-bold text-[#FFFF00]">Carlsburg</span>
                <span className="text-sm text-[#FAFBE0]/80 ml-2">Cockpit</span>
              </div>
            </div>
            <div className="flex flex-col md:flex-row items-center gap-2 md:gap-4">
              {buildId && (hasRole("admin") || hasRole("schichtleiter")) && (
                <span className="text-xs text-[#FAFBE0]/50 font-mono" title="Build ID">
                  Build: {buildId}
                </span>
              )}
              <p className="text-sm text-[#FAFBE0]/70">
                © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant. Alle Rechte vorbehalten.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
