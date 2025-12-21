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

// Carlsburg Logo Component
const CarlsburgLogo = ({ size = 80, className = "" }) => (
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
          <div className="text-center">
            <CarlsburgLogo size={80} className="text-[#FFFF00] mx-auto mb-4" />
            <h1 className="font-serif text-4xl font-bold text-[#005500]">Carlsburg</h1>
            <p className="text-[#005500]/70 mt-1 text-lg">Cockpit</p>
            <p className="text-[#005500]/50 mt-2 text-sm">Historisches Panoramarestaurant</p>
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
            Testbenutzer: admin@gastrocore.de / Admin123!
          </p>
        </div>
      </div>

      {/* Right side - Carlsburg Branding */}
      <div className="hidden lg:block relative bg-[#005500]">
        <div className="absolute inset-0 flex flex-col items-center justify-center p-12">
          <CarlsburgLogo size={200} className="text-[#FFFF00] mb-8" />
          <h2 className="font-serif text-5xl font-bold text-[#FFFF00] mb-4 text-center">
            Carlsburg
          </h2>
          <p className="text-xl text-[#FAFBE0] text-center mb-8">
            Historisches Panoramarestaurant
          </p>
          <div className="text-[#FAFBE0]/70 text-center max-w-md">
            <p className="text-lg mb-4">
              Ihr Restaurant. Professionell verwaltet.
            </p>
            <p className="text-sm">
              Reservierungen, Personal und Service – alles in einer eleganten Oberfläche.
            </p>
          </div>
        </div>
        {/* Decorative curved line at bottom */}
        <svg 
          className="absolute bottom-0 left-0 right-0 w-full h-32"
          viewBox="0 0 100 20"
          preserveAspectRatio="none"
        >
          <path
            d="M0 20 Q50 0 100 20"
            stroke="#FFFF00"
            strokeWidth="0.5"
            fill="none"
          />
        </svg>
      </div>
    </div>
  );
};

export default Login;
