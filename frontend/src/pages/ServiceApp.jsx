/**
 * ServiceApp.jsx - Wrapper für Service-Terminal Bereich
 * Sprint: Service-Terminal getrennt & abgesichert
 * 
 * Separater Layout-Wrapper für Service-Mitarbeiter:
 * - Kein Admin-Menü
 * - iPad Querformat optimiert
 * - Nur Service-relevante Navigation
 */
import React, { useState, useEffect } from "react";
import { useNavigate, useLocation, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Calendar,
  LayoutGrid,
  Users,
  UserPlus,
  LogOut,
  User,
  Moon,
  Sun,
  Utensils,
  ChevronDown,
} from "lucide-react";
import { cn } from "../lib/utils";

const ServiceApp = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, canAccessTerminal } = useAuth();
  const [darkMode, setDarkMode] = useState(false);

  // Check access
  useEffect(() => {
    if (!canAccessTerminal()) {
      navigate("/service/login", { replace: true });
    }
  }, [canAccessTerminal, navigate]);

  const handleLogout = () => {
    logout();
    navigate("/service/login", { replace: true });
  };

  // Navigation items for service
  const navItems = [
    { path: "/service", label: "Heute", icon: Calendar },
    { path: "/service/tischplan", label: "Tischplan", icon: LayoutGrid },
    { path: "/service/warteliste", label: "Warteliste", icon: Users },
    { path: "/service/walkin", label: "Walk-in", icon: UserPlus },
  ];

  const isActive = (path) => {
    if (path === "/service") {
      return location.pathname === "/service" || location.pathname === "/service/";
    }
    return location.pathname.startsWith(path);
  };

  return (
    <div className={cn(
      "min-h-screen flex flex-col",
      darkMode ? "dark bg-gray-900" : "bg-gradient-to-br from-emerald-50 via-white to-sky-50"
    )}>
      {/* Top Navigation Bar - iPad optimized */}
      <header className={cn(
        "sticky top-0 z-50 border-b shadow-sm",
        darkMode ? "bg-gray-800 border-gray-700" : "bg-white/95 backdrop-blur border-emerald-100"
      )}>
        <div className="flex items-center justify-between px-4 h-16">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-10 h-10 rounded-xl flex items-center justify-center",
              darkMode ? "bg-emerald-600" : "bg-gradient-to-br from-emerald-600 to-emerald-700"
            )}>
              <Utensils className="h-5 w-5 text-white" />
            </div>
            <div className="hidden sm:block">
              <h1 className={cn(
                "font-bold text-lg",
                darkMode ? "text-white" : "text-emerald-800"
              )}>
                Service-Terminal
              </h1>
            </div>
          </div>

          {/* Navigation Tabs - Large Touch Targets */}
          <nav className="flex items-center gap-1 sm:gap-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.path);
              return (
                <Button
                  key={item.path}
                  variant={active ? "default" : "ghost"}
                  size="lg"
                  onClick={() => navigate(item.path)}
                  className={cn(
                    "h-12 px-3 sm:px-4 font-medium transition-all",
                    active
                      ? darkMode
                        ? "bg-emerald-600 text-white"
                        : "bg-emerald-600 text-white shadow-md"
                      : darkMode
                        ? "text-gray-300 hover:bg-gray-700"
                        : "text-emerald-700 hover:bg-emerald-50"
                  )}
                >
                  <Icon className="h-5 w-5 sm:mr-2" />
                  <span className="hidden sm:inline">{item.label}</span>
                </Button>
              );
            })}
          </nav>

          {/* User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className={cn(
                  "h-12 px-3 gap-2",
                  darkMode ? "text-gray-300" : "text-emerald-700"
                )}
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center",
                  darkMode ? "bg-gray-700" : "bg-emerald-100"
                )}>
                  <User className="h-4 w-4" />
                </div>
                <span className="hidden md:inline text-sm font-medium">
                  {user?.name || user?.email?.split("@")[0]}
                </span>
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem disabled className="font-medium">
                {user?.email}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setDarkMode(!darkMode)}>
                {darkMode ? (
                  <>
                    <Sun className="mr-2 h-4 w-4" />
                    Hell
                  </>
                ) : (
                  <>
                    <Moon className="mr-2 h-4 w-4" />
                    Dunkel
                  </>
                )}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-600">
                <LogOut className="mr-2 h-4 w-4" />
                Abmelden
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
};

export default ServiceApp;
