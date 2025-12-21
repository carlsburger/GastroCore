import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Gift, Star, Info, Loader2 } from "lucide-react";
import api from "../../lib/api";

export default function CustomerRewards() {
  const [rewards, setRewards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [customer, setCustomer] = useState(null);
  const [points, setPoints] = useState(0);

  useEffect(() => {
    const storedCustomer = localStorage.getItem("carlsburg_customer");
    if (storedCustomer) {
      try {
        setCustomer(JSON.parse(storedCustomer));
      } catch (e) {
        localStorage.removeItem("carlsburg_customer");
      }
    }
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get("/api/public/loyalty/rewards");
        setRewards(res.data || []);

        // If logged in, fetch balance
        if (customer) {
          const token = localStorage.getItem("carlsburg_customer_token");
          if (token) {
            const balanceRes = await api.get("/api/customer/loyalty/balance", {
              headers: { Authorization: `Bearer ${token}` }
            });
            setPoints(balanceRes.data?.balance || 0);
          }
        }
      } catch (error) {
        console.error("Error fetching rewards:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [customer]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-[#00280b]" />
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-8">
      <h1 
        className="text-2xl font-bold text-[#00280b]"
        style={{ fontFamily: "'Playfair Display', serif" }}
      >
        Prämien
      </h1>

      {/* Points Balance */}
      {customer && (
        <div 
          className="rounded-xl p-4 flex items-center justify-between"
          style={{ backgroundColor: "#ffed00" }}
        >
          <div className="flex items-center gap-3">
            <Star className="w-6 h-6 text-[#00280b]" />
            <div>
              <p className="text-xs text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>Ihre Punkte</p>
              <p className="text-xl font-bold text-[#00280b]" style={{ fontFamily: "'Playfair Display', serif" }}>
                {points}
              </p>
            </div>
          </div>
          <Link
            to="/app/punkte"
            className="text-sm text-[#00280b] underline"
            style={{ fontFamily: "'Lato', sans-serif" }}
          >
            Details
          </Link>
        </div>
      )}

      {/* Info Box */}
      <div 
        className="rounded-xl p-4 flex items-start gap-3"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <Info className="w-5 h-5 text-[#00280b] flex-shrink-0 mt-0.5" />
        <p className="text-sm text-[#00280b]/80" style={{ fontFamily: "'Lato', sans-serif" }}>
          Prämien können nur im Restaurant eingelöst werden. 
          Zeigen Sie Ihren QR-Code und nennen Sie die gewünschte Prämie.
        </p>
      </div>

      {/* Rewards List */}
      {rewards.length === 0 ? (
        <div 
          className="rounded-xl p-8 text-center"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <Gift className="w-12 h-12 text-[#00280b]/30 mx-auto mb-4" />
          <p className="text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
            Aktuell keine Prämien verfügbar.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {rewards.map((reward) => {
            const canRedeem = customer && points >= reward.points_cost;
            
            return (
              <div
                key={reward.id}
                className={`rounded-xl overflow-hidden shadow-sm ${
                  canRedeem ? "" : "opacity-60"
                }`}
                style={{ backgroundColor: "#f3f6de" }}
              >
                {reward.image_url && (
                  <div className="h-32 overflow-hidden">
                    <img
                      src={reward.image_url}
                      alt={reward.title}
                      className="w-full h-full object-cover"
                    />
                  </div>
                )}
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <h3 
                      className="font-bold text-[#00280b]"
                      style={{ fontFamily: "'Playfair Display', serif" }}
                    >
                      {reward.title}
                    </h3>
                    <span 
                      className="px-3 py-1 rounded-full text-sm font-bold flex items-center gap-1"
                      style={{ backgroundColor: "#ffed00", color: "#00280b" }}
                    >
                      <Star className="w-3 h-3" />
                      {reward.points_cost}
                    </span>
                  </div>
                  
                  {reward.description && (
                    <p 
                      className="text-sm text-[#00280b]/70 mb-3"
                      style={{ fontFamily: "'Lato', sans-serif" }}
                    >
                      {reward.description}
                    </p>
                  )}
                  
                  {customer ? (
                    canRedeem ? (
                      <p className="text-sm text-green-600 font-medium">
                        ✓ Einlösbar im Restaurant
                      </p>
                    ) : (
                      <p className="text-sm text-[#00280b]/50">
                        Noch {reward.points_cost - points} Punkte benötigt
                      </p>
                    )
                  ) : (
                    <Link
                      to="/app/login"
                      className="text-sm text-[#00280b] underline"
                    >
                      Anmelden um Punkte zu sehen
                    </Link>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CTA if not logged in */}
      {!customer && (
        <div className="text-center pt-4">
          <Link
            to="/app/login"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full font-semibold"
            style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            <Star className="w-5 h-5" />
            Jetzt anmelden & Punkte sammeln
          </Link>
        </div>
      )}
    </div>
  );
}
