/**
 * ServiceLogin.jsx - Separater Login für Service-Terminal (iPad)
 * Sprint: Service-Terminal getrennt & abgesichert
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Loader2, Utensils, AlertCircle } from "lucide-react";
import { Alert, AlertDescription } from "../components/ui/alert";

const ServiceLogin = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, user, canAccessTerminal, isServiceOnly } = useAuth();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Redirect if already logged in
  useEffect(() => {
    if (isAuthenticated && user) {
      if (canAccessTerminal()) {
        navigate("/service", { replace: true });
      } else {
        setError("Sie haben keinen Zugriff auf das Service-Terminal.");
      }
    }
  }, [isAuthenticated, user, canAccessTerminal, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const userData = await login(email, password);
      
      // Check if user has terminal access
      if (!["admin", "schichtleiter", "service"].includes(userData.role)) {
        setError("Kein Service-Zugang. Bitte wenden Sie sich an Ihren Schichtleiter.");
        return;
      }
      
      // Redirect to service terminal
      navigate("/service", { replace: true });
    } catch (err) {
      setError(err.message || "Anmeldung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-emerald-50 via-white to-sky-50 p-4">
      {/* Background Pattern */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0" style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23000000' fill-opacity='0.4'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
        }} />
      </div>

      <Card className="w-full max-w-md shadow-2xl border-0 relative z-10">
        <CardHeader className="text-center pb-2">
          {/* Logo */}
          <div className="mx-auto w-20 h-20 rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-700 flex items-center justify-center mb-4 shadow-lg">
            <Utensils className="h-10 w-10 text-white" />
          </div>
          
          <CardTitle className="text-2xl font-bold text-emerald-800">
            Service-Terminal
          </CardTitle>
          <CardDescription className="text-emerald-600">
            Carlsburg Cockpit
          </CardDescription>
        </CardHeader>
        
        <CardContent className="pt-4">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-emerald-700">E-Mail</Label>
              <Input
                id="email"
                type="email"
                placeholder="service@carlsburg.de"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                className="h-12 text-lg border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500"
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="password" className="text-emerald-700">Passwort</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
                className="h-12 text-lg border-emerald-200 focus:border-emerald-500 focus:ring-emerald-500"
              />
            </div>

            <Button
              type="submit"
              disabled={loading}
              className="w-full h-14 text-lg font-semibold bg-emerald-600 hover:bg-emerald-700 text-white shadow-lg"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Anmelden...
                </>
              ) : (
                "Anmelden"
              )}
            </Button>
          </form>

          {/* Hint for iPad */}
          <div className="mt-6 pt-4 border-t border-emerald-100">
            <p className="text-xs text-center text-emerald-500">
              Optimiert für iPad Querformat
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default ServiceLogin;
