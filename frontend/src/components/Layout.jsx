import React, { useState, useEffect } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { t } from "../lib/i18n";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { BRANDING } from "../lib/constants"; // Zentrale Branding-Konstanten
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
  HardDrive,
  Upload,
  CalendarOff,
  ExternalLink,
  Database,
  PieChart,
  Briefcase,
  Activity,
  Server,
  ShieldCheck,
} from "lucide-react";

// Offizielles Carlsburg Logo URL - aus zentraler Konstante
const CARLSBURG_LOGO_URL = BRANDING.LOGO_URL;

// Carlsburg Logo - Mit offiziellem Bild
const CarlsburgLogo = ({ collapsed = false, className = "" }) => (
  <div className={`flex items-center gap-3 ${className}`}>
    {/* Offizielles Logo */}
    <img 
      src={CARLSBURG_LOGO_URL}
      alt={BRANDING.RESTAURANT_NAME}
      className={`object-contain flex-shrink-0 ${collapsed ? "h-9 w-9" : "h-11"}`}
    />
    {/* Schriftzug */}
    {!collapsed && (
      <div className="flex flex-col leading-none">
        <span className="text-[10px] text-[#fafbed]/70 tracking-widest uppercase">
          CB | Cockpit
        </span>
      </div>
    )}
  </div>
);

// ============================================================
// NAVIGATION MODEL A - Clean Separation
// ============================================================
// 1. CB | Dashboard    → Entrepreneur KPI Overview (Landing)
// 2. Auswertungen      → Read-only Domain Analytics
// 3. Operativ          → Daily Work Screens
// 4. System            → Configuration & Admin
// ============================================================

const navigationGroups = [
  // ─────────────────────────────────────────────────────────────
  // 1. CB | DASHBOARD - Entrepreneur KPI Overview (Landing Page)
  // ─────────────────────────────────────────────────────────────
  {
    id: "dashboard",
    label: "CB | Dashboard",
    icon: LayoutDashboard,
    roles: ["admin", "schichtleiter"],
    path: "/dashboard",
    isLanding: true, // Markierung als Startseite
  },

  // ─────────────────────────────────────────────────────────────
  // 2. AUSWERTUNGEN - Read-only Analytics
  // ─────────────────────────────────────────────────────────────
  {
    id: "analytics",
    label: "Auswertungen",
    icon: PieChart,
    roles: ["admin", "schichtleiter"],
    children: [
      { 
        path: "/analytics/reservations", 
        label: "Reservierung", 
        icon: BookOpen,
        description: "Auslastung, Gäste, Trends"
      },
      { 
        path: "/analytics/staff", 
        label: "Mitarbeiter", 
        icon: UsersRound,
        description: "Stunden, Produktivität, Kosten"
      },
      { 
        path: "/analytics/marketing", 
        label: "Marketing", 
        icon: Megaphone,
        description: "Kampagnen, Reichweite, Opt-ins"
      },
      { 
        path: "/pos-crosscheck", 
        label: "POS / Umsatz", 
        icon: TrendingUp,
        description: "Z-Berichte, Monatsabschluss"
      },
    ],
  },

  // ─────────────────────────────────────────────────────────────
  // 3. OPERATIV - Daily Work Screens
  // ─────────────────────────────────────────────────────────────
  {
    id: "operativ",
    label: "Operativ",
    icon: Briefcase,
    roles: ["admin", "schichtleiter"],
    children: [
      // Service-Terminal Gruppe
      { 
        path: "/service-terminal", 
        label: "Service-Terminal", 
        icon: Utensils,
        highlight: true,
        description: "Tagesgeschäft, Walk-Ins"
      },
      // Reservierungen Gruppe
      { 
        path: "/reservations", 
        label: "Reservierungen", 
        icon: ClipboardList,
      },
      { 
        path: "/reservation-calendar", 
        label: "Reserv.-Kalender", 
        icon: CalendarRange,
      },
      { 
        path: "/table-plan", 
        label: "Tischplan", 
        icon: MapPin,
      },
      { 
        path: "/guests", 
        label: "Gästekartei", 
        icon: Contact,
      },
      { divider: true, label: "Mitarbeiter" },
      // Mitarbeiter & Dienstplan
      { 
        path: "/staff", 
        label: "Team-Übersicht", 
        icon: UsersRound,
      },
      { 
        path: "/shifts-admin", 
        label: "Dienstplan", 
        icon: CalendarClock,
      },
      { 
        path: "/absences", 
        label: "Abwesenheiten", 
        icon: CalendarOff,
      },
      { divider: true, label: "Events" },
      // Events & Aktionen
      { 
        path: "/events", 
        label: "Veranstaltungen", 
        icon: PartyPopper,
      },
      { 
        path: "/aktionen", 
        label: "Aktionen", 
        icon: Gift,
      },
      { 
        path: "/menue-aktionen", 
        label: "Menü-Aktionen", 
        icon: UtensilsCrossed,
      },
    ],
  },

  // ─────────────────────────────────────────────────────────────
  // PERSÖNLICH - Für alle authentifizierten Benutzer
  // ─────────────────────────────────────────────────────────────
  {
    id: "my-shifts",
    label: "Meine Schichten",
    icon: CalendarCheck,
    path: "/my-shifts",
    roles: ["admin", "schichtleiter", "service", "mitarbeiter"],
  },
  {
    id: "employee-pwa",
    label: "Stempeln",
    icon: Clock,
    path: "/employee",
    roles: ["admin", "schichtleiter", "service", "mitarbeiter"],
  },

  // ─────────────────────────────────────────────────────────────
  // 4. SYSTEM - Configuration & Admin (Admin-only)
  // ─────────────────────────────────────────────────────────────
  {
    id: "system",
    label: "System",
    icon: Settings,
    roles: ["admin"],
    children: [
      // Öffnungszeiten & Perioden
      { 
        path: "/admin/settings/opening-hours", 
        label: "Öffnungszeiten", 
        icon: Clock,
        description: "Perioden, Saisonzeiten"
      },
      { 
        path: "/reservation-config", 
        label: "Reservierung-Config", 
        icon: BookOpen,
      },
      { divider: true, label: "Stammdaten" },
      // Stammdaten
      { 
        path: "/areas", 
        label: "Bereiche", 
        icon: MapPin,
      },
      { 
        path: "/table-admin", 
        label: "Tische", 
        icon: TableProperties,
      },
      { 
        path: "/shift-templates", 
        label: "Schichtmodelle", 
        icon: FileText,
      },
      { 
        path: "/staff-import", 
        label: "Mitarbeiter-Import", 
        icon: Upload,
      },
      { divider: true, label: "Administration" },
      // Rollen & Benutzer
      { 
        path: "/users", 
        label: "Benutzer & Rollen", 
        icon: ShieldCheck,
      },
      { 
        path: "/settings", 
        label: "E-Mail / SMTP", 
        icon: Mail,
      },
      { 
        path: "/marketing", 
        label: "Marketing-Center", 
        icon: Megaphone,
      },
      { divider: true, label: "Technik" },
      // POS & Import
      { 
        path: "/pos-import", 
        label: "POS Import", 
        icon: Mail,
        description: "IMAP Monitoring"
      },
      { 
        path: "/taxoffice", 
        label: "Steuerbüro-Export", 
        icon: FileSpreadsheet,
      },
      { divider: true, label: "Backup & Restore" },
      // Seeds & Backup
      { 
        path: "/seeds-backup", 
        label: "System-Seeds", 
        icon: Database,
        description: "Config Packs"
      },
      { 
        path: "/admin/settings/backup", 
        label: "Backup / Export", 
        icon: HardDrive,
      },
      { divider: true, label: "System" },
      // Systemstatus
      { 
        path: "/admin/settings/system", 
        label: "Systemstatus", 
        icon: Activity,
      },
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

  // Externe Links (öffnen in neuem Tab)
  if (item.external) {
    return (
      <a
        href={item.path}
        target="_blank"
        rel="noopener noreferrer"
        className={`
          flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
          transition-all duration-200
          text-[#fafbed] hover:bg-[#003d03]
          ${collapsed ? "justify-center" : ""}
        `}
        title={collapsed ? item.label : (item.tooltip || undefined)}
      >
        <Icon size={18} />
        {!collapsed && (
          <>
            <span>{item.label}</span>
            <ExternalLink size={12} className="ml-auto opacity-60" />
          </>
        )}
      </a>
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
  const groupRef = React.useRef(null);
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

  // Auto-Scroll zum geöffneten Menü
  useEffect(() => {
    if (isOpen && groupRef.current && !collapsed) {
      // Kurze Verzögerung für Animation
      const timer = setTimeout(() => {
        groupRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isOpen, collapsed]);

  // Filter children by role AND hidden flag
  const visibleChildren = group.children?.filter(child => 
    !child.hidden && (!child.roles || child.roles.some(role => hasRole(role)))
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
    <div className="space-y-1" ref={groupRef}>
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
        title={group.fullLabel || group.label}
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

        {/* User Footer - Kompakt */}
        <div className={`
          border-t border-[#003d03] py-2 px-3
          ${sidebarCollapsed ? "text-center" : ""}
        `}>
          {!sidebarCollapsed && (
            <div className="flex items-center justify-between mb-1.5">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-medium text-[#ffed00] truncate">{user?.name}</p>
                <p className="text-[10px] text-[#fafbed]/50 capitalize">
                  {t(`users.roles.${user?.role}`)}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleLogout}
                className="h-7 px-2 text-[#fafbed]/70 hover:bg-[#003d03] hover:text-[#ffed00]"
                data-testid="logout-button"
                title="Abmelden"
              >
                <LogOut size={14} />
              </Button>
            </div>
          )}
          {sidebarCollapsed && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              className="w-full px-2 text-[#fafbed] hover:bg-[#003d03] hover:text-[#ffed00]"
              data-testid="logout-button"
            >
              <LogOut size={16} />
            </Button>
          )}
          {buildId && !sidebarCollapsed && (
            <p className="text-[9px] text-[#fafbed]/20 text-center font-mono">
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
                <span className="font-serif text-sm font-bold text-[#002f02]">{BRANDING.RESTAURANT_NAME}</span>
                <span className="text-xs text-gray-500">Cockpit</span>
              </div>
              <p className="text-xs text-gray-400">
                {BRANDING.COPYRIGHT}
              </p>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Layout;
