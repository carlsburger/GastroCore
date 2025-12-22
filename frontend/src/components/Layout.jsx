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

// Offizielles Carlsburg Logo URL
const CARLSBURG_LOGO_URL = "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png";

// Carlsburg Logo - Mit offiziellem Bild
const CarlsburgLogo = ({ collapsed = false, className = "" }) => (
  <div className={`flex items-center gap-3 ${className}`}>
    {/* Offizielles Logo */}
    <img 
      src={CARLSBURG_LOGO_URL}
      alt="Carlsburg"
      className={`object-contain flex-shrink-0 ${collapsed ? "h-9 w-9" : "h-11"}`}
    />
    {/* Schriftzug */}
    {!collapsed && (
      <div className="flex flex-col leading-none">
        <span className="text-[10px] text-[#fafbed]/70 tracking-widest uppercase">
          Cockpit
        </span>
      </div>
    )}
  </div>
);

// Navigation Struktur - Hierarchisch gruppiert (Standard eingeklappt)
const navigationGroups = [
  {
    id: "dashboard",
    label: "Dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "schichtleiter"],
    path: "/", // Direktlink
  },
  {
    id: "service",
    label: "Service-Terminal",
    icon: Utensils,
    roles: ["admin", "schichtleiter"],
    path: "/service-terminal", // Direktlink
  },
  {
    id: "reservations",
    label: "Reservierungen",
    icon: BookOpen,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/reservations", label: "Übersicht", icon: ClipboardList },
      { path: "/reservation-config", label: "Reservierungs-Einstellungen", icon: Settings, roles: ["admin"] },
      { path: "/table-plan", label: "Tischplan", icon: MapPin },
      { path: "/table-admin", label: "Tisch-Stammdaten", icon: TableProperties, roles: ["admin"] },
    ],
  },
  {
    id: "events",
    label: "Veranstaltungen & Aktionen",
    icon: PartyPopper,
    roles: ["admin", "schichtleiter"],
    children: [
      { path: "/events", label: "Veranstaltungen", icon: Calendar },
      { path: "/aktionen", label: "Aktionen", icon: Gift },
      { path: "/menue-aktionen", label: "Menü-Aktionen", icon: UtensilsCrossed },
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
      { path: "/my-shifts", label: "Meine Schichten", icon: CalendarCheck },
      { path: "/taxoffice", label: "Exporte Steuerbüro", icon: FileSpreadsheet, roles: ["admin"] },
    ],
  },
  {
    id: "marketing",
    label: "Marketing",
    icon: Megaphone,
    roles: ["admin", "schichtleiter"],
    path: "/marketing", // Direktlink
  },
  {
    id: "settings",
    label: "Einstellungen",
    icon: Settings,
    roles: ["admin"],
    children: [
      { path: "/admin/settings/system", label: "System", icon: Cog },
      { path: "/admin/settings/opening-hours", label: "Öffnungszeiten", icon: Clock },
      { path: "/settings", label: "E-Mail / Reminders", icon: Mail },
      { path: "/areas", label: "Bereiche", icon: MapPin },
      { path: "/users", label: "Benutzer", icon: Users },
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
          text-[#fafbed]/40 cursor-not-allowed
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
          ? "bg-[#ffed00] text-[#002f02] shadow-md" 
          : "text-[#fafbed] hover:bg-[#003d03]"
        }
        ${collapsed ? "justify-center" : ""}
      `}
      title={collapsed ? item.label : undefined}
      data-testid={`nav-item-${item.path.replace("/", "") || "home"}`}
    >
      <Icon size={18} className={isActive ? "text-[#002f02]" : ""} />
      {!collapsed && <span>{item.label}</span>}
    </Link>
  );
};

// Menügruppe (auf-/zuklappbar) - Standard eingeklappt
const NavGroup = ({ group, collapsed, location, onNavigate, hasRole }) => {
  const [isOpen, setIsOpen] = useState(false);
  const Icon = group.icon;
  
  // Prüfe ob ein Child aktiv ist
  const hasActiveChild = group.children?.some(child => 
    location.pathname === child.path || 
    (child.path !== "/" && location.pathname.startsWith(child.path))
  );

  // Auto-open NUR wenn ein Child aktiv ist
  useEffect(() => {
    if (hasActiveChild && !collapsed) {
      setIsOpen(true);
    } else if (!hasActiveChild) {
      setIsOpen(false);
    }
  }, [hasActiveChild, collapsed, location.pathname]);

  // Filter children by role
  const visibleChildren = group.children?.filter(child => 
    !child.roles || child.roles.some(role => hasRole(role))
  ) || [];

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
            ? "bg-[#ffed00] text-[#002f02] shadow-md" 
            : "text-[#fafbed] hover:bg-[#003d03]"
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
            ? "bg-[#003d03] text-[#ffed00]" 
            : "text-[#fafbed] hover:bg-[#003d03]"
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
        <div className="ml-3 pl-3 border-l-2 border-[#003d03] space-y-0.5 animate-fade-in">
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
    <div className="min-h-screen bg-[#fafbed] flex">
      {/* Desktop Sidebar */}
      <aside
        className={`
          hidden lg:flex flex-col
          ${sidebarCollapsed ? "w-20" : "w-64"}
          bg-[#002f02] text-[#fafbed]
          border-r border-[#003d03]
          transition-all duration-300
          fixed left-0 top-0 h-screen z-40
        `}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-4 border-b border-[#003d03]">
          <Link to="/" className="flex-1">
            <CarlsburgLogo collapsed={sidebarCollapsed} />
          </Link>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-1.5 rounded-lg hover:bg-[#003d03] text-[#fafbed]/70 hover:text-[#ffed00]"
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
          border-t border-[#003d03] p-3
          ${sidebarCollapsed ? "text-center" : ""}
        `}>
          {!sidebarCollapsed && (
            <div className="mb-3 px-2">
              <p className="text-sm font-medium text-[#ffed00] truncate">{user?.name}</p>
              <p className="text-xs text-[#fafbed]/60 capitalize">
                {t(`users.roles.${user?.role}`)}
              </p>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className={`
              w-full text-[#fafbed] hover:bg-[#003d03] hover:text-[#ffed00]
              ${sidebarCollapsed ? "px-2" : "justify-start"}
            `}
            data-testid="logout-button"
          >
            <LogOut size={18} />
            {!sidebarCollapsed && <span className="ml-2">Abmelden</span>}
          </Button>
          {buildId && !sidebarCollapsed && (
            <p className="text-[10px] text-[#fafbed]/30 text-center mt-2 font-mono">
              {buildId}
            </p>
          )}
        </div>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 h-16 bg-[#002f02] border-b border-[#003d03] flex items-center justify-between px-4">
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg hover:bg-[#003d03] text-[#fafbed]"
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
          className="text-[#fafbed] hover:bg-[#003d03]"
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
          <aside className="lg:hidden fixed left-0 top-16 bottom-0 w-72 bg-[#002f02] z-50 overflow-y-auto animate-slide-in-left">
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
            <div className="border-t border-[#003d03] p-4 mt-4">
              <p className="text-sm font-medium text-[#ffed00]">{user?.name}</p>
              <p className="text-xs text-[#fafbed]/60 capitalize">
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
        <main className="flex-1 p-4 md:p-6 lg:p-8 pt-20 lg:pt-6 bg-[#fafbed]">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-gray-200 bg-white mt-auto">
          <div className="max-w-7xl mx-auto px-4 md:px-8 py-4">
            <div className="flex flex-col md:flex-row justify-between items-center gap-2">
              <div className="flex items-center gap-2">
                <span className="font-serif text-sm font-bold text-[#002f02]">Carlsburg</span>
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
