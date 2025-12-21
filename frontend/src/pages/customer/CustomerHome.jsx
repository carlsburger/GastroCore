import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Calendar, Clock, MapPin, Phone, ChevronRight, Star, Utensils } from "lucide-react";
import api from "../../lib/api";

export default function CustomerHome() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await api.get("/api/public/events?status=published&limit=3");
        setEvents(res.data || []);
      } catch (error) {
        console.error("Error fetching events:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

  return (
    <div className="space-y-8 pb-8">
      {/* Hero Section */}
      <div 
        className="rounded-2xl p-6 text-center shadow-lg"
        style={{ backgroundColor: "#00280b" }}
      >
        <h1 
          className="text-2xl md:text-3xl font-bold text-[#ffed00] mb-2"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          Willkommen im Carlsburg
        </h1>
        <p 
          className="text-[#fafbed]/90 text-sm mb-6"
          style={{ fontFamily: "'Lato', sans-serif" }}
        >
          Historisches Panoramarestaurant seit 1890
        </p>
        <Link
          to="/app/reservieren"
          className="inline-flex items-center gap-2 px-6 py-3 rounded-full font-semibold text-[#00280b] transition-transform hover:scale-105"
          style={{ backgroundColor: "#ffed00", fontFamily: "'Lato', sans-serif" }}
        >
          <Calendar className="w-5 h-5" />
          Tisch reservieren
        </Link>
      </div>

      {/* Quick Info */}
      <div className="grid grid-cols-2 gap-4">
        <div 
          className="rounded-xl p-4 shadow-sm"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <Clock className="w-6 h-6 text-[#00280b] mb-2" />
          <h3 
            className="font-semibold text-[#00280b] text-sm mb-1"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Öffnungszeiten
          </h3>
          <p className="text-xs text-[#00280b]/80" style={{ fontFamily: "'Lato', sans-serif" }}>
            <span className="font-semibold">Sommer:</span> Täglich<br />
            <span className="font-semibold">Winter:</span> Mi-So<br />
            11:30 - 22:00 Uhr
          </p>
        </div>
        <div 
          className="rounded-xl p-4 shadow-sm"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <MapPin className="w-6 h-6 text-[#00280b] mb-2" />
          <h3 
            className="font-semibold text-[#00280b] text-sm mb-1"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Anfahrt
          </h3>
          <p className="text-xs text-[#00280b]/80" style={{ fontFamily: "'Lato', sans-serif" }}>
            Carlsburg 1<br />
            37308 Heilbad Heiligenstadt
          </p>
        </div>
      </div>

      {/* Loyalty Teaser */}
      <Link 
        to="/app/punkte"
        className="block rounded-xl p-4 shadow-sm border-2 border-[#ffed00]"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full" style={{ backgroundColor: "#ffed00" }}>
              <Star className="w-6 h-6 text-[#00280b]" />
            </div>
            <div>
              <h3 
                className="font-semibold text-[#00280b]"
                style={{ fontFamily: "'Playfair Display', serif" }}
              >
                Carlsburg Punkte
              </h3>
              <p className="text-xs text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
                Sammeln Sie Punkte bei jedem Besuch
              </p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-[#00280b]/50" />
        </div>
      </Link>

      {/* Events */}
      {events.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 
              className="text-xl font-bold text-[#00280b]"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Aktuelle Events
            </h2>
            <Link 
              to="/app/events" 
              className="text-sm text-[#00280b] hover:underline"
              style={{ fontFamily: "'Lato', sans-serif" }}
            >
              Alle anzeigen
            </Link>
          </div>
          <div className="space-y-3">
            {events.map((event) => (
              <Link
                key={event.id}
                to={`/app/events/${event.id}`}
                className="block rounded-xl overflow-hidden shadow-sm"
                style={{ backgroundColor: "#f3f6de" }}
              >
                <div className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 
                        className="font-semibold text-[#00280b] mb-1"
                        style={{ fontFamily: "'Playfair Display', serif" }}
                      >
                        {event.title}
                      </h3>
                      <p className="text-xs text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
                        {new Date(event.date).toLocaleDateString("de-DE", {
                          weekday: "long",
                          day: "numeric",
                          month: "long",
                        })}
                        {event.time && ` • ${event.time} Uhr`}
                      </p>
                    </div>
                    <ChevronRight className="w-5 h-5 text-[#00280b]/50 mt-1" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* About */}
      <div 
        className="rounded-xl p-5 shadow-sm"
        style={{ backgroundColor: "#f3f6de" }}
      >
        <div className="flex items-start gap-4">
          <Utensils className="w-8 h-8 text-[#00280b] flex-shrink-0" />
          <div>
            <h3 
              className="font-semibold text-[#00280b] mb-2"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              Über das Carlsburg
            </h3>
            <p 
              className="text-sm text-[#00280b]/80 leading-relaxed"
              style={{ fontFamily: "'Lato', sans-serif" }}
            >
              Genießen Sie regionale Spezialitäten in historischem Ambiente mit 
              atemberaubendem Panoramablick. Seit über 130 Jahren ein Ort der 
              Gastfreundschaft und kulinarischen Tradition.
            </p>
          </div>
        </div>
      </div>

      {/* Contact */}
      <div className="text-center">
        <a
          href="tel:+4936064560"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-medium border-2"
          style={{ 
            borderColor: "#00280b", 
            color: "#00280b",
            fontFamily: "'Lato', sans-serif"
          }}
        >
          <Phone className="w-4 h-4" />
          +49 3606 4560
        </a>
      </div>
    </div>
  );
}
