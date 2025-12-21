import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { Calendar, Clock, Users, Euro, MapPin, ChevronLeft, Loader2, Check } from "lucide-react";
import api from "../../lib/api";

export default function CustomerEventDetail() {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    guests: 2,
    name: "",
    email: "",
    phone: "",
    notes: "",
  });

  useEffect(() => {
    const fetchEvent = async () => {
      try {
        const res = await api.get(`/api/public/events/${eventId}`);
        setEvent(res.data);
      } catch (error) {
        console.error("Error fetching event:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchEvent();
  }, [eventId]);

  const handleBook = async () => {
    setBooking(true);
    setError(null);
    try {
      await api.post("/api/public/events/book", {
        event_id: eventId,
        guest_count: formData.guests,
        guest_name: formData.name,
        guest_email: formData.email,
        guest_phone: formData.phone,
        notes: formData.notes || undefined,
      });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Buchung fehlgeschlagen");
    } finally {
      setBooking(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-[#00280b]" />
      </div>
    );
  }

  if (!event) {
    return (
      <div className="text-center py-12">
        <p className="text-[#00280b]/70">Event nicht gefunden</p>
        <Link to="/app/events" className="text-[#00280b] underline mt-2 inline-block">
          Zurück zur Übersicht
        </Link>
      </div>
    );
  }

  if (success) {
    return (
      <div className="text-center space-y-6 py-12">
        <div 
          className="w-20 h-20 rounded-full mx-auto flex items-center justify-center"
          style={{ backgroundColor: "#00280b" }}
        >
          <Check className="w-10 h-10 text-[#ffed00]" />
        </div>
        <div>
          <h2 
            className="text-2xl font-bold text-[#00280b] mb-2"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Buchung erfolgreich!
          </h2>
          <p className="text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
            Sie erhalten eine Bestätigung per E-Mail.
          </p>
        </div>
        <Link
          to="/app/events"
          className="inline-block px-6 py-3 rounded-full font-medium"
          style={{ backgroundColor: "#f3f6de", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
        >
          Weitere Events
        </Link>
      </div>
    );
  }

  const totalPrice = event.price_per_person ? event.price_per_person * formData.guests : null;

  return (
    <div className="space-y-6 pb-8">
      {/* Back Button */}
      <Link 
        to="/app/events"
        className="inline-flex items-center gap-1 text-[#00280b]/70 hover:text-[#00280b]"
        style={{ fontFamily: "'Lato', sans-serif" }}
      >
        <ChevronLeft className="w-4 h-4" />
        Zurück
      </Link>

      {/* Image */}
      {event.image_url && (
        <div className="rounded-xl overflow-hidden shadow-lg -mx-4">
          <img
            src={event.image_url}
            alt={event.title}
            className="w-full h-48 object-cover"
          />
        </div>
      )}

      {/* Title & Info */}
      <div>
        <h1 
          className="text-2xl font-bold text-[#00280b] mb-3"
          style={{ fontFamily: "'Playfair Display', serif" }}
        >
          {event.title}
        </h1>
        
        <div className="flex flex-wrap gap-3 text-sm text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
          <span className="flex items-center gap-1 bg-[#f3f6de] px-3 py-1.5 rounded-full">
            <Calendar className="w-4 h-4" />
            {new Date(event.date).toLocaleDateString("de-DE", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </span>
          {event.time && (
            <span className="flex items-center gap-1 bg-[#f3f6de] px-3 py-1.5 rounded-full">
              <Clock className="w-4 h-4" />
              {event.time} Uhr
            </span>
          )}
          {event.price_per_person && (
            <span className="flex items-center gap-1 bg-[#ffed00] px-3 py-1.5 rounded-full text-[#00280b] font-medium">
              <Euro className="w-4 h-4" />
              {event.price_per_person}€ p.P.
            </span>
          )}
        </div>
      </div>

      {/* Description */}
      {event.description && (
        <div 
          className="rounded-xl p-4"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <p 
            className="text-[#00280b]/80 leading-relaxed whitespace-pre-line"
            style={{ fontFamily: "'Lato', sans-serif" }}
          >
            {event.description}
          </p>
        </div>
      )}

      {/* Availability */}
      {event.capacity_remaining !== undefined && (
        <div className={`text-center p-3 rounded-lg ${
          event.capacity_remaining === 0 
            ? "bg-red-100 text-red-700" 
            : event.capacity_remaining <= 10 
              ? "bg-orange-100 text-orange-700"
              : "bg-green-100 text-green-700"
        }`}>
          <Users className="w-4 h-4 inline mr-2" />
          {event.capacity_remaining === 0 
            ? "Ausgebucht" 
            : `Noch ${event.capacity_remaining} Plätze verfügbar`
          }
        </div>
      )}

      {/* Booking Form */}
      {event.capacity_remaining !== 0 && (
        <div className="space-y-4 pt-4 border-t-2 border-[#00280b]/10">
          <h2 
            className="text-lg font-bold text-[#00280b]"
            style={{ fontFamily: "'Playfair Display', serif" }}
          >
            Jetzt buchen
          </h2>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2">
              Anzahl Personen
            </label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setFormData({ ...formData, guests: Math.max(1, formData.guests - 1) })}
                className="w-10 h-10 rounded-full bg-white border-2 border-[#00280b]/20 text-[#00280b] text-xl font-bold"
              >
                -
              </button>
              <span className="text-xl font-bold text-[#00280b] w-8 text-center">
                {formData.guests}
              </span>
              <button
                onClick={() => setFormData({ ...formData, guests: Math.min(event.capacity_remaining || 20, formData.guests + 1) })}
                className="w-10 h-10 rounded-full bg-white border-2 border-[#00280b]/20 text-[#00280b] text-xl font-bold"
              >
                +
              </button>
              {totalPrice && (
                <span className="ml-auto font-bold text-[#00280b]">
                  = {totalPrice}€
                </span>
              )}
            </div>
          </div>

          <div className="rounded-xl p-4" style={{ backgroundColor: "#f3f6de" }}>
            <label className="block text-sm font-medium text-[#00280b] mb-2">Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
            />
          </div>

          <div className="rounded-xl p-4" style={{ backgroundColor: "#f3f6de" }}>
            <label className="block text-sm font-medium text-[#00280b] mb-2">E-Mail *</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
            />
          </div>

          <div className="rounded-xl p-4" style={{ backgroundColor: "#f3f6de" }}>
            <label className="block text-sm font-medium text-[#00280b] mb-2">Telefon *</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
            />
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
              {error}
            </div>
          )}

          <button
            onClick={handleBook}
            disabled={booking || !formData.name || !formData.email || !formData.phone}
            className="w-full p-4 rounded-full font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            {booking ? (
              <Loader2 className="w-5 h-5 animate-spin inline" />
            ) : (
              `Jetzt buchen${totalPrice ? ` • ${totalPrice}€` : ""}`
            )}
          </button>
        </div>
      )}
    </div>
  );
}
