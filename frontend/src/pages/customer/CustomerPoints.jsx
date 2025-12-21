import React, { useState, useEffect, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Star, QrCode, History, Gift, Loader2, RefreshCw, LogIn } from "lucide-react";
import api from "../../lib/api";

export default function CustomerPoints() {
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [points, setPoints] = useState(null);
  const [history, setHistory] = useState([]);
  const [qrCode, setQrCode] = useState(null);
  const [qrExpiry, setQrExpiry] = useState(0);
  const [loading, setLoading] = useState(true);
  const [showQr, setShowQr] = useState(false);

  useEffect(() => {
    const storedCustomer = localStorage.getItem("carlsburg_customer");
    if (storedCustomer) {
      try {
        setCustomer(JSON.parse(storedCustomer));
      } catch (e) {
        localStorage.removeItem("carlsburg_customer");
      }
    }
    setLoading(false);
  }, []);

  const fetchPoints = useCallback(async () => {
    if (!customer) return;
    const token = localStorage.getItem("carlsburg_customer_token");
    if (!token) return;

    try {
      const res = await api.get("/api/customer/loyalty/balance", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setPoints(res.data);
    } catch (err) {
      console.error("Error fetching points:", err);
    }
  }, [customer]);

  const fetchHistory = useCallback(async () => {
    if (!customer) return;
    const token = localStorage.getItem("carlsburg_customer_token");
    if (!token) return;

    try {
      const res = await api.get("/api/customer/loyalty/history?limit=10", {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(res.data || []);
    } catch (err) {
      console.error("Error fetching history:", err);
    }
  }, [customer]);

  useEffect(() => {
    if (customer) {
      fetchPoints();
      fetchHistory();
    }
  }, [customer, fetchPoints, fetchHistory]);

  const generateQrCode = async () => {
    const token = localStorage.getItem("carlsburg_customer_token");
    if (!token) return;

    try {
      const res = await api.post("/api/customer/loyalty/generate-qr", {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setQrCode(res.data.qr_token);
      setQrExpiry(90); // 90 seconds
      setShowQr(true);
    } catch (err) {
      console.error("Error generating QR:", err);
    }
  };

  // QR Countdown
  useEffect(() => {
    if (qrExpiry > 0) {
      const timer = setTimeout(() => setQrExpiry(qrExpiry - 1), 1000);
      return () => clearTimeout(timer);
    } else if (qrExpiry === 0 && qrCode) {
      setQrCode(null);
      setShowQr(false);
    }
  }, [qrExpiry, qrCode]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-[#00280b]" />
      </div>
    );
  }

  // Not logged in
  if (!customer) {
    return (
      <div className="space-y-6 pb-8 text-center">
        <div 
          className="w-20 h-20 rounded-full mx-auto flex items-center justify-center"
          style={{ backgroundColor: "#ffed00" }}
        >
          <Star className="w-10 h-10 text-[#00280b]" />
        </div>
        
        <div>
          <h1 
            className="text-2xl font-bold text-[#00280b] mb-2"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Carlsburg Punkte
          </h1>
          <p className="text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
            Sammeln Sie Punkte bei jedem Besuch und lösen Sie diese gegen Prämien ein.
          </p>
        </div>

        <div 
          className="rounded-xl p-6"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <h3 
            className="font-semibold text-[#00280b] mb-3"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            So funktioniert's
          </h3>
          <ul className="text-sm text-[#00280b]/80 space-y-2 text-left" style={{ fontFamily: "'Lato', sans-serif" }}>
            <li>• 10 Punkte pro 100€ Umsatz</li>
            <li>• Punkte beim Bezahlen sammeln</li>
            <li>• QR-Code an der Kasse zeigen</li>
            <li>• Prämien im Restaurant einlösen</li>
          </ul>
        </div>

        <Link
          to="/app/login"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full font-semibold"
          style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
        >
          <LogIn className="w-5 h-5" />
          Jetzt anmelden
        </Link>

        <p className="text-xs text-[#00280b]/50" style={{ fontFamily: "'Lato', sans-serif" }}>
          Noch kein Konto? Bei der Anmeldung wird automatisch eines erstellt.
        </p>
      </div>
    );
  }

  // QR Code Modal
  if (showQr && qrCode) {
    return (
      <div className="space-y-6 pb-8 text-center">
        <h2 
          className="text-xl font-bold text-[#00280b]"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Ihr QR-Code
        </h2>
        
        <div 
          className="rounded-xl p-6 inline-block mx-auto"
          style={{ backgroundColor: "white" }}
        >
          {/* QR Code Display */}
          <div className="w-48 h-48 bg-[#00280b] rounded-lg flex items-center justify-center mb-4">
            <div className="text-center">
              <QrCode className="w-24 h-24 text-[#ffed00] mx-auto" />
              <p className="text-[#ffed00] text-xs mt-2 font-mono">{qrCode.slice(0, 8)}...</p>
            </div>
          </div>
          
          <div className="text-center">
            <p className="text-2xl font-bold text-[#00280b]">{qrExpiry}s</p>
            <p className="text-xs text-[#00280b]/60">Gültig</p>
          </div>
        </div>

        <p className="text-sm text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
          Zeigen Sie diesen Code an der Kasse, um Punkte zu sammeln.
        </p>

        <div className="flex gap-3 justify-center">
          <button
            onClick={generateQrCode}
            className="px-4 py-2 rounded-full text-sm font-medium border-2"
            style={{ borderColor: "#00280b", color: "#00280b" }}
          >
            <RefreshCw className="w-4 h-4 inline mr-1" />
            Neuer Code
          </button>
          <button
            onClick={() => { setShowQr(false); setQrCode(null); }}
            className="px-4 py-2 rounded-full text-sm font-medium"
            style={{ backgroundColor: "#f3f6de", color: "#00280b" }}
          >
            Schließen
          </button>
        </div>
      </div>
    );
  }

  // Logged in - Show points
  return (
    <div className="space-y-6 pb-8">
      <h1 
        className="text-2xl font-bold text-[#00280b]"
        style={{ fontFamily: "'Playfair Display', serif" }}
      >
        Meine Punkte
      </h1>

      {/* Points Card */}
      <div 
        className="rounded-2xl p-6 text-center shadow-lg"
        style={{ backgroundColor: "#00280b" }}
      >
        <Star className="w-12 h-12 text-[#ffed00] mx-auto mb-2" />
        <p className="text-[#fafbed]/70 text-sm mb-1" style={{ fontFamily: "'Lato', sans-serif" }}>
          Aktueller Stand
        </p>
        <p 
          className="text-5xl font-bold text-[#ffed00]"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          {points?.balance || 0}
        </p>
        <p className="text-[#fafbed]/70 text-sm" style={{ fontFamily: "'Lato', sans-serif" }}>
          Punkte
        </p>
      </div>

      {/* QR Button */}
      <button
        onClick={generateQrCode}
        className="w-full p-4 rounded-xl flex items-center justify-center gap-3 font-semibold shadow-sm"
        style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
      >
        <QrCode className="w-6 h-6" />
        QR-Code zum Punkte sammeln
      </button>

      {/* Rewards Link */}
      <Link
        to="/app/praemien"
        className="block rounded-xl p-4 border-2 border-[#00280b]/20 hover:border-[#00280b]"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Gift className="w-6 h-6 text-[#00280b]" />
            <div>
              <p className="font-semibold text-[#00280b]" style={{ fontFamily: "'Playfair Display', serif" }}>
                Prämien entdecken
              </p>
              <p className="text-xs text-[#00280b]/60" style={{ fontFamily: "'Lato', sans-serif" }}>
                Lösen Sie Ihre Punkte ein
              </p>
            </div>
          </div>
          <Gift className="w-5 h-5 text-[#00280b]/40" />
        </div>
      </Link>

      {/* History */}
      <div>
        <h2 
          className="text-lg font-bold text-[#00280b] mb-3 flex items-center gap-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          <History className="w-5 h-5" />
          Letzte Aktivitäten
        </h2>
        
        {history.length === 0 ? (
          <div 
            className="rounded-xl p-6 text-center"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <p className="text-[#00280b]/60 text-sm" style={{ fontFamily: "'Lato', sans-serif" }}>
              Noch keine Aktivitäten
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {history.map((item, index) => (
              <div
                key={index}
                className="rounded-xl p-3 flex items-center justify-between"
                style={{ backgroundColor: "#f3f6de" }}
              >
                <div>
                  <p className="font-medium text-[#00280b] text-sm" style={{ fontFamily: "'Lato', sans-serif" }}>
                    {item.description || item.type}
                  </p>
                  <p className="text-xs text-[#00280b]/60">
                    {new Date(item.created_at).toLocaleDateString("de-DE")}
                  </p>
                </div>
                <span className={`font-bold ${
                  item.points > 0 ? "text-green-600" : "text-red-600"
                }`}>
                  {item.points > 0 ? "+" : ""}{item.points}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
