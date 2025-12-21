import React, { useState, useEffect } from "react";
import { useNavigate, Link } from "react-router-dom";
import { User, Mail, Bell, LogOut, ChevronLeft, Loader2, Check } from "lucide-react";
import api from "../../lib/api";

export default function CustomerProfile() {
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [newsletterOptin, setNewsletterOptin] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const storedCustomer = localStorage.getItem("carlsburg_customer");
    if (storedCustomer) {
      try {
        const parsed = JSON.parse(storedCustomer);
        setCustomer(parsed);
        setNewsletterOptin(parsed.newsletter_optin || false);
      } catch (e) {
        localStorage.removeItem("carlsburg_customer");
        navigate("/app/login");
      }
    } else {
      navigate("/app/login");
    }
    setLoading(false);
  }, [navigate]);

  const handleLogout = () => {
    localStorage.removeItem("carlsburg_customer");
    localStorage.removeItem("carlsburg_customer_token");
    navigate("/app");
  };

  const toggleNewsletter = async () => {
    const newValue = !newsletterOptin;
    setSaving(true);
    
    try {
      const token = localStorage.getItem("carlsburg_customer_token");
      await api.patch("/api/customer/profile", 
        { newsletter_optin: newValue },
        { headers: { Authorization: `Bearer ${token}` }}
      );
      setNewsletterOptin(newValue);
      
      // Update local storage
      const updatedCustomer = { ...customer, newsletter_optin: newValue };
      localStorage.setItem("carlsburg_customer", JSON.stringify(updatedCustomer));
      setCustomer(updatedCustomer);
      
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      console.error("Error updating newsletter:", err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-[#00280b]" />
      </div>
    );
  }

  if (!customer) {
    return null;
  }

  return (
    <div className="space-y-6 pb-8">
      <Link 
        to="/app"
        className="inline-flex items-center gap-1 text-[#00280b]/70 hover:text-[#00280b]"
        style={{ fontFamily: "'Lato', sans-serif" }}
      >
        <ChevronLeft className="w-4 h-4" />
        Zurück
      </Link>

      <h1 
        className="text-2xl font-bold text-[#00280b]"
        style={{ fontFamily: "'Playfair Display', serif" }}
      >
        Mein Profil
      </h1>

      {/* Profile Card */}
      <div 
        className="rounded-xl p-6"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <div className="flex items-center gap-4 mb-4">
          <div 
            className="w-16 h-16 rounded-full flex items-center justify-center"
            style={{ backgroundColor: "#00280b" }}
          >
            <User className="w-8 h-8 text-[#ffed00]" />
          </div>
          <div>
            <h2 
              className="text-xl font-bold text-[#00280b]"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {customer.name || "Gast"}
            </h2>
            <p className="text-sm text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
              Mitglied seit {customer.created_at 
                ? new Date(customer.created_at).toLocaleDateString("de-DE", { month: "long", year: "numeric" })
                : "2024"
              }
            </p>
          </div>
        </div>

        <div className="space-y-3 border-t border-[#00280b]/10 pt-4">
          <div className="flex items-center gap-3">
            <Mail className="w-5 h-5 text-[#00280b]/50" />
            <span className="text-[#00280b]" style={{ fontFamily: "'Lato', sans-serif" }}>
              {customer.email}
            </span>
          </div>
        </div>
      </div>

      {/* Newsletter Setting */}
      <div 
        className="rounded-xl p-4"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-[#00280b]" />
            <div>
              <p className="font-medium text-[#00280b]" style={{ fontFamily: "'Lato', sans-serif" }}>
                Newsletter
              </p>
              <p className="text-xs text-[#00280b]/60" style={{ fontFamily: "'Lato', sans-serif" }}>
                Events, Aktionen & Neuigkeiten
              </p>
            </div>
          </div>
          <button
            onClick={toggleNewsletter}
            disabled={saving}
            className={`w-14 h-8 rounded-full relative transition-colors ${
              newsletterOptin ? "bg-[#00280b]" : "bg-[#00280b]/20"
            }`}
          >
            <span 
              className={`absolute top-1 w-6 h-6 rounded-full bg-white shadow transition-transform ${
                newsletterOptin ? "left-7" : "left-1"
              }`}
            />
          </button>
        </div>
        {saved && (
          <p className="text-sm text-green-600 mt-2 flex items-center gap-1">
            <Check className="w-4 h-4" />
            Gespeichert
          </p>
        )}
      </div>

      {/* Data Privacy */}
      <div 
        className="rounded-xl p-4"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <p className="text-sm text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
          Ihre Daten werden gemäß unserer{" "}
          <a href="/datenschutz" className="underline text-[#00280b]">
            Datenschutzerklärung
          </a>{" "}
          verarbeitet.
        </p>
      </div>

      {/* Logout */}
      <button
        onClick={handleLogout}
        className="w-full p-4 rounded-xl flex items-center justify-center gap-2 font-medium border-2"
        style={{ borderColor: "#00280b", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
      >
        <LogOut className="w-5 h-5" />
        Abmelden
      </button>
    </div>
  );
}
