import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { t } from "../lib/i18n";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Loader2, AlertCircle, Eye, EyeOff } from "lucide-react";

// Offizielles Carlsburg Logo (extern gehostet)
const CARLSBURG_LOGO_URL = "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png";

export const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const user = await login(email, password);
      if (user.must_change_password) {
        navigate("/change-password");
      } else {
        navigate("/");
      }
    } catch (err) {
      setError(err.message || t("auth.invalidCredentials"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      {/* Left side - Login Form */}
      <div className="flex items-center justify-center p-8 bg-[#FAFBE0]">
        <div className="w-full max-w-md space-y-8">
          {/* Logo und Titel */}
          <div className="text-center">
            <img 
              src={CARLSBURG_LOGO_URL} 
              alt="Carlsburg Logo" 
              className="h-24 mx-auto mb-4 object-contain"
              style={{ filter: 'brightness(0) saturate(100%) invert(15%) sepia(100%) saturate(1500%) hue-rotate(90deg) brightness(0.7)' }}
            />
            <p className="text-[#005500] mt-2 text-3xl font-bold tracking-wide">Cockpit</p>
          </div>

          <Card className="border-[#005500]/20 shadow-lg bg-white">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-serif text-[#005500]">{t("auth.login")}</CardTitle>
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
                    placeholder="name@carlsburg.de"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    data-testid="login-email"
                    className="h-11"
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
                      data-testid="login-password"
                      className="h-11 pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      data-testid="toggle-password"
                    >
                      {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full h-11 rounded-full font-bold bg-[#005500] hover:bg-[#003300] text-[#FAFBE0]"
                  disabled={loading}
                  data-testid="login-submit"
                >
                  {loading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      {t("common.loading")}
                    </>
                  ) : (
                    t("auth.loginButton")
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-sm text-[#005500]/50">
            © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant
          </p>
        </div>
      </div>

      {/* Right side - Carlsburg Branding */}
      <div className="hidden lg:flex relative bg-[#005500]">
        <div className="absolute inset-0 flex flex-col items-center justify-center p-12">
          {/* Großes offizielles Logo */}
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
        </div>
      </div>
    </div>
  );
};

export default Login;
