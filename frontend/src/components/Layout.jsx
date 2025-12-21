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
} from "lucide-react";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "nav.dashboard", roles: ["admin", "schichtleiter"] },
  { path: "/events-admin", icon: Calendar, label: "nav.events", roles: ["admin", "schichtleiter"] },
  { path: "/payments", icon: CreditCard, label: "nav.payments", roles: ["admin"] },
  { path: "/waitlist", icon: Clock, label: "nav.waitlist", roles: ["admin", "schichtleiter"] },
  { path: "/guests", icon: UserX, label: "nav.guests", roles: ["admin", "schichtleiter"] },
  { path: "/areas", icon: MapPin, label: "nav.areas", roles: ["admin"] },
  { path: "/users", icon: Users, label: "nav.users", roles: ["admin"] },
  { path: "/audit", icon: FileText, label: "nav.auditLog", roles: ["admin"] },
  { path: "/settings", icon: Settings, label: "nav.settings", roles: ["admin"] },
  { path: "/message-logs", icon: Mail, label: "nav.messageLogs", roles: ["admin"] },
];

export const Layout = ({ children }) => {
  const { user, logout, hasRole } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const filteredNavItems = navItems.filter((item) =>
    item.roles.some((role) => hasRole(role))
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-card/95 backdrop-blur supports-[backdrop-filter]:bg-card/80">
        <div className="flex h-16 items-center justify-between px-4 md:px-8">
          <div className="flex items-center gap-4">
            <button
              className="md:hidden p-2 hover:bg-muted rounded-lg"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              data-testid="mobile-menu-toggle"
            >
              {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-serif text-lg font-bold">G</span>
              </div>
              <span className="font-serif text-2xl font-medium text-primary hidden sm:block">
                GastroCore
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {filteredNavItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  data-testid={`nav-${item.path.replace("/", "") || "dashboard"}`}
                  className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted text-foreground"
                  }`}
                >
                  <Icon size={18} />
                  {t(item.label)}
                </Link>
              );
            })}
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-muted-foreground capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              data-testid="logout-button"
              className="rounded-full"
            >
              <LogOut size={18} />
              <span className="hidden sm:inline ml-2">{t("nav.logout")}</span>
            </Button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <nav className="md:hidden border-t border-border bg-card p-4 animate-fade-in">
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
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted text-foreground"
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
      <main className="p-4 md:p-8 max-w-7xl mx-auto">{children}</main>

      {/* Footer */}
      <footer className="border-t border-border bg-[#002f02] text-[#fafbed] mt-auto">
        <div className="max-w-7xl mx-auto px-4 md:px-8 py-6">
          <div className="flex flex-col md:flex-row justify-between items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-[#fafbed] flex items-center justify-center">
                <span className="text-[#002f02] font-serif text-sm font-bold">G</span>
              </div>
              <span className="font-serif text-lg">GastroCore</span>
            </div>
            <p className="text-sm opacity-80">
              © {new Date().getFullYear()} GastroCore. Alle Rechte vorbehalten.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
