import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Mail, Loader2, ArrowLeft, KeyRound } from "lucide-react";
import api from "../../lib/api";

export default function CustomerLogin() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [otpSent, setOtpSent] = useState(false);

  const requestOtp = async () => {
    setLoading(true);
    setError(null);
    try {
      await api.post("/api/customer/auth/request-otp", { email });
      setOtpSent(true);
      setStep(2);
    } catch (err) {
      setError(err.response?.data?.detail || "Fehler beim Senden des Codes");
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/api/customer/auth/verify-otp", { email, otp });
      // Store customer data
      localStorage.setItem("carlsburg_customer", JSON.stringify(res.data.customer));
      localStorage.setItem("carlsburg_customer_token", res.data.token);
      // Navigate to points page
      navigate("/app/punkte");
    } catch (err) {
      setError(err.response?.data?.detail || "Ungültiger Code");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 pb-8">
      <Link 
        to="/app"
        className="inline-flex items-center gap-1 text-[#00280b]/70 hover:text-[#00280b]"
        style={{ fontFamily: "'Lato', sans-serif" }}
      >
        <ArrowLeft className="w-4 h-4" />
        Zurück
      </Link>

      <div className="text-center py-4">
        <div 
          className="w-16 h-16 rounded-full mx-auto flex items-center justify-center mb-4"
          style={{ backgroundColor: "#00280b" }}
        >
          <KeyRound className="w-8 h-8 text-[#ffed00]" />
        </div>
        <h1 
          className="text-2xl font-bold text-[#00280b] mb-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Anmelden
        </h1>
        <p className="text-[#00280b]/70 text-sm" style={{ fontFamily: "'Lato', sans-serif" }}>
          {step === 1 
            ? "Geben Sie Ihre E-Mail-Adresse ein"
            : "Geben Sie den Code aus Ihrer E-Mail ein"
          }
        </p>
      </div>

      {step === 1 ? (
        <div className="space-y-4">
          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              <Mail className="w-4 h-4 inline mr-2" />
              E-Mail-Adresse
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ihre@email.de"
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={requestOtp}
            disabled={loading || !email}
            className="w-full p-4 rounded-full font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin inline" />
            ) : (
              "Code anfordern"
            )}
          </button>

          <p className="text-xs text-[#00280b]/60 text-center" style={{ fontFamily: "'Lato', sans-serif" }}>
            Wir senden Ihnen einen Einmal-Code per E-Mail.
            Kein Passwort erforderlich.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              <KeyRound className="w-4 h-4 inline mr-2" />
              Einmal-Code
            </label>
            <input
              type="text"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="123456"
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white text-center text-2xl tracking-widest"
              style={{ fontFamily: "'Lato', sans-serif" }}
              maxLength={6}
            />
          </div>

          <div 
            className="p-3 rounded-lg text-sm text-[#00280b]/70"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <p style={{ fontFamily: "'Lato', sans-serif" }}>
              Code gesendet an:<br />
              <strong>{email}</strong>
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={verifyOtp}
            disabled={loading || otp.length !== 6}
            className="w-full p-4 rounded-full font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin inline" />
            ) : (
              "Anmelden"
            )}
          </button>

          <button
            onClick={() => { setStep(1); setOtp(""); setError(null); }}
            className="w-full p-3 text-[#00280b]/70 text-sm"
            style={{ fontFamily: "'Lato', sans-serif" }}
          >
            Andere E-Mail verwenden
          </button>
        </div>
      )}
    </div>
  );
}
