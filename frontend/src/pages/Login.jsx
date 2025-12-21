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
      <div className="flex items-center justify-center p-8 bg-background">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center">
            <div className="w-16 h-16 rounded-full bg-primary mx-auto flex items-center justify-center mb-4">
              <span className="text-primary-foreground font-serif text-3xl font-bold">G</span>
            </div>
            <h1 className="font-serif text-4xl font-medium text-primary">GastroCore</h1>
            <p className="text-muted-foreground mt-2">Gastro-Management System</p>
          </div>

          <Card className="border-border shadow-lg">
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-serif">{t("auth.login")}</CardTitle>
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
                    placeholder="name@example.de"
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
                  className="w-full h-11 rounded-full font-bold"
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

          <p className="text-center text-sm text-muted-foreground">
            Testbenutzer: admin@gastrocore.de / Admin123!
          </p>
        </div>
      </div>

      {/* Right side - Image */}
      <div
        className="hidden lg:block relative bg-cover bg-center"
        style={{
          backgroundImage:
            'url("https://images.unsplash.com/photo-1596226391997-5e7ea4805d03?crop=entropy&cs=srgb&fm=jpg&q=85")',
        }}
      >
        <div className="absolute inset-0 bg-[#00280b]/60" />
        <div className="absolute inset-0 flex items-end p-12">
          <div className="text-[#fafbed] max-w-lg">
            <h2 className="font-serif text-4xl mb-4">
              Ihr Restaurant. Professionell verwaltet.
            </h2>
            <p className="text-lg opacity-90">
              Reservierungen, Personal und Service – alles in einer eleganten Oberfläche.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
