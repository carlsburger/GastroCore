import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { t } from "../lib/i18n";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Loader2, AlertCircle, Eye, EyeOff, Utensils, LayoutDashboard, ArrowLeft, Tablet, Monitor } from "lucide-react";

// Offizielles Carlsburg Logo (extern gehostet)
const CARLSBURG_LOGO_URL = "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png";

// LocalStorage Key für Login-Modus
const LOGIN_MODE_KEY = "carlsburg_login_mode";

export const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loginMode, setLoginMode] = useState(null); // null = Auswahl, "service" | "cockpit"
  const { login, isAuthenticated, user } = useAuth();
  const navigate = useNavigate();

  // WORKAROUND: Wenn die URL /book ist, navigiere direkt zum BookingWidget
  // (React Router funktioniert nicht korrekt im Preview-Kontext)
  useEffect(() => {
    const currentPath = window.location.pathname;
    console.log('[Login] Current path:', currentPath);
    if (currentPath === '/book') {
      console.log('[Login] Redirecting to /book via window.location');
      // Nicht navigate verwenden, da React Router nicht korrekt funktioniert
      // Stattdessen: Force reload der korrekten Seite
      return; // Nicht redirecten - die Route sollte korrekt matchen
    }
  }, []);

  // Redirect wenn bereits eingeloggt
  useEffect(() => {
    if (isAuthenticated && user) {
      redirectBasedOnRole(user.role);
    }
  }, [isAuthenticated, user]);

  // Redirect-Logik basierend auf Rolle
  const redirectBasedOnRole = (role) => {
    if (role === "service") {
      navigate("/service", { replace: true });
    } else if (role === "admin" || role === "schichtleiter") {
      // Bei Cockpit-Modus oder wenn Admin/Schichtleiter
      const savedMode = localStorage.getItem(LOGIN_MODE_KEY);
      if (savedMode === "service") {
        navigate("/service", { replace: true });
      } else {
        navigate("/", { replace: true });
      }
    } else if (role === "mitarbeiter") {
      // Mitarbeiter direkt zu MyShifts (nicht no-access!)
      navigate("/my-shifts", { replace: true });
    }
  };

  const handleModeSelect = (mode) => {
    setLoginMode(mode);
    localStorage.setItem(LOGIN_MODE_KEY, mode);
    setError("");
  };

  const handleBack = () => {
    setLoginMode(null);
    setError("");
    setEmail("");
    setPassword("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const user = await login(email, password);
      
      // Rolle prüfen basierend auf gewähltem Modus
      if (loginMode === "service") {
        // Service-Modus: Nur service, admin, schichtleiter erlaubt
        if (!["service", "admin", "schichtleiter"].includes(user.role)) {
          setError("Kein Zugriff auf das Service-Terminal mit dieser Rolle.");
          return;
        }
        navigate("/service", { replace: true });
      } else {
        // Cockpit-Modus: Nur admin, schichtleiter erlaubt
        if (!["admin", "schichtleiter"].includes(user.role)) {
          if (user.role === "service") {
            setError("Service-Mitarbeiter haben keinen Zugriff auf das Cockpit. Bitte wählen Sie 'Service-Terminal'.");
          } else if (user.role === "mitarbeiter") {
            setError("Mitarbeiter haben keinen Zugriff auf das Cockpit.");
          } else {
            setError("Kein Zugriff auf das Cockpit mit dieser Rolle.");
          }
          return;
        }
        
        if (user.must_change_password) {
          navigate("/change-password", { replace: true });
        } else {
          navigate("/", { replace: true });
        }
      }
    } catch (err) {
      setError(err.message || t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  // ============== MODUS-AUSWAHL ==============
  if (loginMode === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#FAFBE0] via-white to-emerald-50 p-4">
        <div className="w-full max-w-2xl space-y-8">
          {/* Logo und Titel */}
          <div className="text-center">
            <img 
              src={CARLSBURG_LOGO_URL} 
              alt="Carlsburg Logo" 
              className="h-28 mx-auto mb-4 object-contain"
              style={{ filter: 'brightness(0) saturate(100%) invert(15%) sepia(100%) saturate(1500%) hue-rotate(90deg) brightness(0.7)' }}
            />
            <p className="text-[#002f02]/60 mt-2 text-lg">Wählen Sie Ihren Zugang</p>
          </div>

          {/* Modus-Kacheln */}
          <div className="grid sm:grid-cols-2 gap-6">
            {/* Service-Terminal Kachel */}
            <button
              onClick={() => handleModeSelect("service")}
              className="group relative bg-white rounded-2xl p-8 shadow-lg border-2 border-emerald-100 hover:border-emerald-500 hover:shadow-xl transition-all duration-300 text-left"
            >
              <div className="absolute top-4 right-4">
                <Tablet className="h-6 w-6 text-emerald-500/50 group-hover:text-emerald-600" />
              </div>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform">
                <Utensils className="h-8 w-8 text-white" />
              </div>
              <h3 className="text-xl font-bold text-[#002f02] mb-2">Service-Terminal</h3>
              <p className="text-sm text-[#002f02]/60 mb-4">
                Für Kellner & Service-Personal
              </p>
              <div className="flex items-center text-emerald-600 text-sm font-medium">
                <span>iPad-optimiert</span>
                <ArrowLeft className="h-4 w-4 ml-2 rotate-180 group-hover:translate-x-1 transition-transform" />
              </div>
            </button>

            {/* Cockpit Kachel */}
            <button
              onClick={() => handleModeSelect("cockpit")}
              className="group relative bg-white rounded-2xl p-8 shadow-lg border-2 border-[#002f02]/10 hover:border-[#002f02]/50 hover:shadow-xl transition-all duration-300 text-left"
            >
              <div className="absolute top-4 right-4">
                <Monitor className="h-6 w-6 text-[#002f02]/30 group-hover:text-[#002f02]/60" />
              </div>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#002f02] to-[#004d00] flex items-center justify-center mb-4 shadow-lg group-hover:scale-110 transition-transform">
                <LayoutDashboard className="h-8 w-8 text-[#FAFBE0]" />
              </div>
              <h3 className="text-xl font-bold text-[#002f02] mb-2">Carlsburg Cockpit</h3>
              <p className="text-sm text-[#002f02]/60 mb-4">
                Für Admin & Schichtleiter
              </p>
              <div className="flex items-center text-[#002f02]/70 text-sm font-medium">
                <span>Vollzugriff</span>
                <ArrowLeft className="h-4 w-4 ml-2 rotate-180 group-hover:translate-x-1 transition-transform" />
              </div>
            </button>
          </div>

          <p className="text-center text-sm text-[#002f02]/40">
            © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant
          </p>
        </div>
      </div>
    );
  }

  // ============== LOGIN-FORMULAR ==============
  const isServiceMode = loginMode === "service";
  
  return (
    <div className={`min-h-screen grid lg:grid-cols-2 ${isServiceMode ? 'bg-emerald-50' : ''}`}>
      {/* Left side - Login Form */}
      <div className={`flex items-center justify-center p-8 ${isServiceMode ? 'bg-gradient-to-br from-emerald-50 to-white' : 'bg-[#FAFBE0]'}`}>
        <div className="w-full max-w-md space-y-8">
          {/* Zurück-Button */}
          <Button
            variant="ghost"
            onClick={handleBack}
            className="mb-4 text-[#002f02]/60 hover:text-[#002f02]"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Zurück zur Auswahl
          </Button>

          {/* Logo und Titel */}
          <div className="text-center">
            <div className={`w-20 h-20 rounded-2xl mx-auto mb-4 flex items-center justify-center shadow-lg ${
              isServiceMode 
                ? 'bg-gradient-to-br from-emerald-500 to-emerald-700' 
                : 'bg-gradient-to-br from-[#002f02] to-[#004d00]'
            }`}>
              {isServiceMode ? (
                <Utensils className="h-10 w-10 text-white" />
              ) : (
                <LayoutDashboard className="h-10 w-10 text-[#FAFBE0]" />
              )}
            </div>
            <h1 className="text-2xl font-bold text-[#002f02]">
              {isServiceMode ? "Service-Terminal" : "Carlsburg Cockpit"}
            </h1>
            <p className="text-[#002f02]/60 mt-1">
              {isServiceMode ? "Login für Service-Personal" : "Login für Administration"}
            </p>
          </div>

          <Card className={`border-0 shadow-lg ${isServiceMode ? 'bg-white' : 'bg-white'}`}>
            <CardHeader className="space-y-1 pb-4">
              <CardTitle className="text-xl font-serif text-[#002f02]">{t("auth.login")}</CardTitle>
              <CardDescription>
                Melden Sie sich mit Ihren Zugangsdaten an
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && (
                  <Alert variant="destructive" className="animate-fade-in">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="space-y-2">
                  <Label htmlFor="email">{t("auth.email")}</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder={isServiceMode ? "service@carlsburg.de" : "admin@carlsburg.de"}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    data-testid="login-email"
                    className={`h-12 text-lg ${isServiceMode ? 'border-emerald-200 focus:border-emerald-500' : ''}`}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">{t("auth.password")}</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      data-testid="login-password"
                      className={`h-12 text-lg pr-10 ${isServiceMode ? 'border-emerald-200 focus:border-emerald-500' : ''}`}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground p-1"
                      data-testid="toggle-password"
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className={`w-full h-14 text-lg font-bold rounded-xl shadow-lg ${
                    isServiceMode 
                      ? 'bg-emerald-600 hover:bg-emerald-700 text-white' 
                      : 'bg-[#002f02] hover:bg-[#003300] text-[#FAFBE0]'
                  }`}
                  disabled={loading}
                  data-testid="login-submit"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      Anmelden...
                    </>
                  ) : (
                    t("auth.loginButton")
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-sm text-[#002f02]/40">
            © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant
          </p>
        </div>
      </div>

      {/* Right side - Branding */}
      <div className={`hidden lg:flex relative ${isServiceMode ? 'bg-emerald-700' : 'bg-[#002f02]'}`}>
        <div className="absolute inset-0 flex flex-col items-center justify-center p-12">
          {isServiceMode ? (
            <>
              <div className="w-32 h-32 rounded-3xl bg-white/10 flex items-center justify-center mb-8">
                <Utensils className="h-16 w-16 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-white mb-4">Service-Terminal</h2>
              <p className="text-white/80 text-center max-w-md text-lg">
                Schneller Zugriff auf Reservierungen, Tischplan und Walk-ins – optimiert für iPad.
              </p>
            </>
          ) : (
            <>
              <img 
                src={CARLSBURG_LOGO_URL} 
                alt="Carlsburg Logo" 
                className="max-w-md w-full h-auto mb-8 object-contain"
              />
              <div className="text-[#FAFBE0]/90 text-center max-w-md mt-8">
                <p className="text-xl mb-4">
                  Ihr Restaurant. Professionell verwaltet.
                </p>
                <p className="text-sm text-[#FAFBE0]/70">
                  Reservierungen, Tischplan, Personal und Service – 
                  alles in einer eleganten Oberfläche.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
