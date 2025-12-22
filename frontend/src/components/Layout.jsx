import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { t } from "../lib/i18n";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
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
  ChevronDown,
  ChevronRight,
  BarChart3,
  TrendingUp,
  BookOpen,
  TableProperties,
  ClipboardList,
  PartyPopper,
  Gift,
  UtensilsCrossed,
  Ticket,
  UsersRound,
  CalendarCheck,
  FileSpreadsheet,
  Newspaper,
  Send,
  Share2,
  Contact,
  CalendarRange,
  Sun,
  FileEdit,
  Shield,
  Cog,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";

// Carlsburg Logo - Vollständig mit Schriftzug
const CarlsburgLogo = ({ collapsed = false, className = "" }) => (
  <div className={`flex items-center gap-3 ${className}`}>
    {/* Logo Icon */}
    <svg
      width={collapsed ? 36 : 44}
      height={collapsed ? 36 : 44}
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
      className="flex-shrink-0"
    >
      {/* Gelber Hintergrund-Kreis */}
      <circle cx="50" cy="50" r="48" fill="#FFCC00" />
      {/* Gebäude */}
      <path
        d="M50 15 L72 35 L72 65 L28 65 L28 35 Z"
        fill="#005500"
      />
      {/* Dach */}
      <path
        d="M50 8 L78 35 L72 35 L50 15 L28 35 L22 35 Z"
        fill="#005500"
      />
      {/* Fenster oben */}
      <rect x="40" y="38" width="20" height="14" fill="#FFCC00" rx="1" />
      <line x1="50" y1="38" x2="50" y2="52" stroke="#005500" strokeWidth="2" />
      <line x1="40" y1="45" x2="60" y2="45" stroke="#005500" strokeWidth="2" />
      {/* Tür */}
      <rect x="43" y="52" width="14" height="13" fill="#FFCC00" rx="1" />
      {/* Geschwungene Basis */}
      <path
        d="M15 82 Q50 58 85 82"
        stroke="#005500"
        strokeWidth="5"
        fill="none"
      />
    </svg>
    {/* Schriftzug */}
    {!collapsed && (
      <div className="flex flex-col leading-none">
        <span className="font-serif text-xl font-bold text-[#FFCC00] tracking-wide">
          Carlsburg
        </span>
        <span className="text-[10px] text-[#FAFBE0]/70 tracking-widest uppercase">
          Cockpit
        </span>
      </div>
    )}
  </div>
);

// Navigation Struktur - Hierarchisch gruppiert
const navigationGroups = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/", label: "Übersicht", icon: LayoutDashboard },
      { path: "/analytics", label: "Kennzahlen", icon: BarChart3, disabled: true },
      { path: "/comparisons", label: "Vergleiche", icon: TrendingUp, disabled: true },
    ],
  },
  {
    id: "reservations",
    label: "Reservierungen",
    icon: BookOpen,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/reservations", label: "Reservierungsübersicht", icon: ClipboardList },
      { path: "/service-terminal", label: "Service-Terminal", icon: Utensils },
      { path: "/table-plan", label: "Tischplan", icon: MapPin },
      { path: "/table-admin", label: "Tisch-Stammdaten", icon: TableProperties, roles: ["admin"] },
      { path: "/reservation-config", label: "Konfiguration", icon: Settings, roles: ["admin"] },
      { path: "/waitlist", label: "Warteliste", icon: Clock },
      { path: "/guests", label: "Gäste", icon: UserX },
    ],
  },
  {
    id: "events",
    label: "Veranstaltungen",
    icon: PartyPopper,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/events-admin", label: "Veranstaltungen", icon: Calendar },
      { path: "/events-actions", label: "Aktionen", icon: Gift, disabled: true },
      { path: "/events-menus", label: "Menü-Aktionen", icon: UtensilsCrossed, disabled: true },
      { path: "/events-bookings", label: "Buchungen", icon: Ticket, disabled: true },
    ],
  },
  {
    id: "staff",
    label: "Mitarbeiter",
    icon: UsersRound,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/staff", label: "Mitarbeiter", icon: UserCog },
      { path: "/schedule", label: "Dienstplan", icon: CalendarClock },
      { path: "/shifts", label: "Schichten", icon: CalendarCheck, disabled: true },
      { path: "/taxoffice", label: "Exporte Steuerbüro", icon: FileSpreadsheet, roles: ["admin"] },
    ],
  },
  {
    id: "marketing",
    label: "Marketing",
    icon: Megaphone,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/marketing", label: "Übersicht", icon: Megaphone },
      { path: "/newsletters", label: "Newsletter", icon: Newspaper, disabled: true },
      { path: "/campaigns", label: "Kampagnen", icon: Send, disabled: true },
      { path: "/social", label: "Social Posts", icon: Share2, disabled: true },
      { path: "/customers", label: "Kunden", icon: Contact, disabled: true },
    ],
  },
  {
    id: "ai",
    label: "KI-Assistent",
    icon: Bot,
    roles: ["admin", "schichtleiter"],
    path: "/ai-assistant", // Direktlink ohne Children
  },
  {
    id: "settings",
    label: "Einstellungen",
    icon: Settings,
    roles: ["admin"],
    children: [
      { path: "/areas", label: "Bereiche", icon: MapPin },
      { path: "/settings", label: "System", icon: Cog },
      { path: "/users", label: "Benutzer", icon: Users },
      { path: "/audit", label: "Audit-Log", icon: FileText },
      { path: "/message-logs", label: "Nachrichten-Log", icon: Mail },
      { path: "/payments", label: "Zahlungen", icon: CreditCard },
    ],
  },
];

// Einzelner Menüpunkt
const NavItem = ({ item, isActive, collapsed, onClick }) => {
  const Icon = item.icon;
  
  if (item.disabled) {
    return (
      <div
        className={`
          flex items-center gap-3 px-3 py-2 rounded-lg text-sm
          text-[#FAFBE0]/40 cursor-not-allowed
          ${collapsed ? "justify-center" : ""}
        `}
        title={collapsed ? item.label : `${item.label} (bald verfügbar)`}
      >
        <Icon size={18} />
        {!collapsed && <span>{item.label}</span>}
      </div>
    );
  }

  return (
    <Link
      to={item.path}
      onClick={onClick}
      className={`
        flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
        transition-all duration-200
        ${isActive 
          ? "bg-[#FFCC00] text-[#005500] shadow-md" 
          : "text-[#FAFBE0] hover:bg-[#004400]"
        }
        ${collapsed ? "justify-center" : ""}
      `}
      title={collapsed ? item.label : undefined}
      data-testid={`nav-item-${item.path.replace("/", "") || "home"}`}
    >
      <Icon size={18} className={isActive ? "text-[#005500]" : ""} />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
};

// Menügruppe (auf-/zuklappbar)
const NavGroup = ({ group, collapsed, location, onNavigate, hasRole }) => {
  const [isOpen, setIsOpen] = useState(false);
  const Icon = group.icon;
  
  // Prüfe ob User Rolle hat
  if (!group.roles.some(role => hasRole(role))) {
    return null;
  }

  // Direktlink ohne Children
  if (group.path && !group.children) {
    const isActive = location.pathname === group.path;
    return (
      <Link
        to={group.path}
        onClick={onNavigate}
        className={`
          flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
          transition-all duration-200
          ${isActive 
            ? "bg-[#FFCC00] text-[#005500] shadow-md" 
            : "text-[#FAFBE0] hover:bg-[#004400]"
          }
          ${collapsed ? "justify-center" : ""}
        `}
        title={collapsed ? group.label : undefined}
        data-testid={`nav-group-${group.id}`}
      >
        <Icon size={20} />
        {!collapsed && <span>{group.label}</span>}
      </Link>
    );
  }

  // Prüfe ob ein Child aktiv ist
  const hasActiveChild = group.children?.some(child => 
    location.pathname === child.path || 
    (child.path !== "/" && location.pathname.startsWith(child.path))
  );

  // Auto-open wenn ein Child aktiv ist
  useEffect(() => {
    if (hasActiveChild && !collapsed) {
      setIsOpen(true);
    }
  }, [hasActiveChild, collapsed]);

  // Filter children by role
  const visibleChildren = group.children?.filter(child => 
    !child.roles || child.roles.some(role => hasRole(role))
  ) || [];

  if (visibleChildren.length === 0) return null;

  return (
    <div className="space-y-1">
      {/* Group Header */}
      <button
        onClick={() => !collapsed && setIsOpen(!isOpen)}
        className={`
          w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
          transition-all duration-200
          ${hasActiveChild 
            ? "bg-[#004400] text-[#FFCC00]" 
            : "text-[#FAFBE0] hover:bg-[#004400]"
          }
          ${collapsed ? "justify-center" : "justify-between"}
        `}
        title={collapsed ? group.label : undefined}
        data-testid={`nav-group-${group.id}`}
      >
        <div className="flex items-center gap-3">
          <Icon size={20} />
          {!collapsed && <span>{group.label}</span>}
        </div>
        {!collapsed && (
          <span className="transition-transform duration-200">
            {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          </span>
        )}
      </button>

      {/* Children */}
      {!collapsed && isOpen && (
        <div className="ml-3 pl-3 border-l-2 border-[#004400] space-y-0.5 animate-fade-in">
          {visibleChildren.map((child) => (
            <NavItem
              key={child.path}
              item={child}
              isActive={location.pathname === child.path}
              collapsed={false}
              onClick={onNavigate}
            />
          ))}
        </div>
      )}

      {/* Collapsed Tooltip Menu */}
      {collapsed && (
        <div className="hidden group-hover:block absolute left-full top-0 ml-2 z-50">
          {/* Tooltip implementation could go here */}
        </div>
      )}
    </div>
  );
};

// Hauptlayout
export const Layout = ({ children }) => {
  const { user, logout, hasRole } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [buildId, setBuildId] = useState(null);

  // Fetch build info
  useEffect(() => {
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

  const closeMobileMenu = () => setMobileMenuOpen(false);

  return (
    <div className="min-h-screen bg-[#FAFBE0] flex">
      {/* Desktop Sidebar */}
      <aside
        className={`
          hidden lg:flex flex-col
          ${sidebarCollapsed ? "w-20" : "w-64"}
          bg-[#005500] text-[#FAFBE0]
          border-r border-[#004400]
          transition-all duration-300
          fixed left-0 top-0 h-screen z-40
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#004400]">
          <Link to="/" className="flex-1">
            <CarlsburgLogo collapsed={sidebarCollapsed} />
          </Link>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-[#004400] text-[#FAFBE0]/70 hover:text-[#FFCC00]"
            title={sidebarCollapsed ? "Menü erweitern" : "Menü einklappen"}
          >
            {sidebarCollapsed ? <PanelLeft size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        {/* Navigation */}
        <ScrollArea className="flex-1 py-4">
          <nav className="px-3 space-y-1">
            {navigationGroups.map((group) => (
              <NavGroup
                key={group.id}
                group={group}
                collapsed={sidebarCollapsed}
                location={location}
                onNavigate={() => {}}
                hasRole={hasRole}
              />
            ))}
          </nav>
        </ScrollArea>

        {/* User Footer */}
        <div className={`
          border-t border-[#004400] p-3
          ${sidebarCollapsed ? "text-center" : ""}
        `}>
          {!sidebarCollapsed && (
            <div className="mb-3 px-2">
              <p className="text-sm font-medium text-[#FFCC00] truncate">{user?.name}</p>
              <p className="text-xs text-[#FAFBE0]/60 capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className={`
              w-full text-[#FAFBE0] hover:bg-[#004400] hover:text-[#FFCC00]
              ${sidebarCollapsed ? "px-2" : "justify-start"}
            `}
            data-testid="logout-button"
          >
            <LogOut size={18} />
            {!sidebarCollapsed && <span className="ml-2">Abmelden</span>}
          </Button>
          {buildId && !sidebarCollapsed && (
            <p className="text-[10px] text-[#FAFBE0]/30 text-center mt-2 font-mono">
              {buildId}
            </p>
          )}
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 bg-[#005500] border-b border-[#004400] flex items-center justify-between px-4">
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg hover:bg-[#004400] text-[#FAFBE0]"
          data-testid="mobile-menu-toggle"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
        
        <Link to="/">
          <CarlsburgLogo collapsed={false} />
        </Link>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          className="text-[#FAFBE0] hover:bg-[#004400]"
        >
          <LogOut size={20} />
        </Button>
      </header>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <>
          <div
            className="lg:hidden fixed inset-0 bg-black/50 z-40"
            onClick={closeMobileMenu}
          />
          <aside className="lg:hidden fixed left-0 top-16 bottom-0 w-72 bg-[#005500] z-50 overflow-y-auto animate-slide-in-left">
            <nav className="p-4 space-y-1">
              {navigationGroups.map((group) => (
                <NavGroup
                  key={group.id}
                  group={group}
                  collapsed={false}
                  location={location}
                  onNavigate={closeMobileMenu}
                  hasRole={hasRole}
                />
              ))}
            </nav>
            
            {/* Mobile User Info */}
            <div className="border-t border-[#004400] p-4 mt-4">
              <p className="text-sm font-medium text-[#FFCC00]">{user?.name}</p>
              <p className="text-xs text-[#FAFBE0]/60 capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
          </aside>
        </>
      )}

      {/* Main Content Area */}
      <div className={`
        flex-1 flex flex-col min-h-screen
        ${sidebarCollapsed ? "lg:ml-20" : "lg:ml-64"}
        transition-all duration-300
      `}>
        {/* Top Bar (Desktop) */}
        <header className="hidden lg:flex h-16 items-center justify-between px-6 bg-white border-b border-gray-200 sticky top-0 z-30">
          <div>
            {/* Breadcrumb oder Seitentitel könnte hier hin */}
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user?.name}</p>
              <p className="text-xs text-gray-500 capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-4 md:p-6 lg:p-8 pt-20 lg:pt-6 bg-[#FAFBE0]">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 bg-white mt-auto">
          <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
            <div className="flex flex-col md:flex-row justify-between items-center gap-2">
              <div className="flex items-center gap-2">
                <span className="font-serif text-sm font-bold text-[#005500]">Carlsburg</span>
                <span className="text-xs text-gray-500">Cockpit</span>
              </div>
              <p className="text-xs text-gray-400">
                © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant
              </p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Layout;
