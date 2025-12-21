import React, { useState, useEffect, useCallback } from "react";
import { Calendar, Clock, Users, ChevronLeft, ChevronRight, Check, AlertCircle, Loader2 } from "lucide-react";
import api from "../../lib/api";

export default function CustomerReservation() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [availability, setAvailability] = useState(null);
  const [areas, setAreas] = useState([]);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [waitlisted, setWaitlisted] = useState(false);

  // Form state
  const [selectedDate, setSelectedDate] = useState("");
  const [selectedTime, setSelectedTime] = useState("");
  const [partySize, setPartySize] = useState(2);
  const [selectedArea, setSelectedArea] = useState("");
  const [guestData, setGuestData] = useState({
    name: "",
    email: "",
    phone: "",
    occasion: "",
    notes: "",
  });

  // Initialize with tomorrow's date
  useEffect(() => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    setSelectedDate(tomorrow.toISOString().split("T")[0]);
  }, []);

  // Fetch availability when date changes
  useEffect(() => {
    if (selectedDate) {
      fetchAvailability();
    }
  }, [selectedDate]);

  const fetchAvailability = async () => {
    try {
      const res = await api.get(`/api/public/availability?date=${selectedDate}`);
      setAvailability(res.data);
      setAreas(res.data?.areas || []);
    } catch (err) {
      console.error("Error fetching availability:", err);
    }
  };

  const timeSlots = availability?.slots || [
    "11:30", "12:00", "12:30", "13:00", "13:30", "14:00",
    "18:00", "18:30", "19:00", "19:30", "20:00", "20:30"
  ];

  const occasions = [
    { value: "", label: "Kein besonderer Anlass" },
    { value: "birthday", label: "Geburtstag" },
    { value: "anniversary", label: "Jahrestag" },
    { value: "business", label: "Geschäftlich" },
    { value: "celebration", label: "Feier" },
    { value: "other", label: "Sonstiges" },
  ];

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.post("/api/public/reservations", {
        date: selectedDate,
        time: selectedTime,
        party_size: partySize,
        area_id: selectedArea || undefined,
        guest_name: guestData.name,
        guest_email: guestData.email,
        guest_phone: guestData.phone,
        occasion: guestData.occasion || undefined,
        notes: guestData.notes || undefined,
      });
      
      if (res.data.status === "waitlist") {
        setWaitlisted(true);
      }
      setSuccess(true);
      setStep(4);
    } catch (err) {
      setError(err.response?.data?.detail || "Reservierung fehlgeschlagen. Bitte versuchen Sie es erneut.");
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    if (step === 1) return selectedDate && selectedTime && partySize;
    if (step === 2) return true; // Area is optional
    if (step === 3) return guestData.name && guestData.email && guestData.phone;
    return false;
  };

  return (
    <div className="space-y-6 pb-8">
      <h1 
        className="text-2xl font-bold text-[#00280b]"
        style={{ fontFamily: "'Playfair Display', serif" }}
      >
        Tisch reservieren
      </h1>

      {/* Progress */}
      {!success && (
        <div className="flex items-center justify-center gap-2">
          {[1, 2, 3].map((s) => (
            <div
              key={s}
              className={`w-10 h-1 rounded-full transition-colors ${
                s <= step ? "bg-[#00280b]" : "bg-[#00280b]/20"
              }`}
            />
          ))}
        </div>
      )}

      {/* Step 1: Date, Time, Party Size */}
      {step === 1 && (
        <div className="space-y-5">
          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              <Calendar className="w-4 h-4 inline mr-2" />
              Datum
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              min={new Date().toISOString().split("T")[0]}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              <Clock className="w-4 h-4 inline mr-2" />
              Uhrzeit
            </label>
            <div className="grid grid-cols-4 gap-2">
              {timeSlots.map((time) => (
                <button
                  key={time}
                  onClick={() => setSelectedTime(time)}
                  className={`p-2.5 rounded-lg text-sm font-medium transition-colors ${
                    selectedTime === time
                      ? "bg-[#00280b] text-[#ffed00]"
                      : "bg-white border border-[#00280b]/20 text-[#00280b] hover:border-[#00280b]"
                  }`}
                  style={{ fontFamily: "'Lato', sans-serif" }}
                >
                  {time}
                </button>
              ))}
            </div>
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              <Users className="w-4 h-4 inline mr-2" />
              Personenzahl
            </label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setPartySize(Math.max(1, partySize - 1))}
                className="w-12 h-12 rounded-full bg-white border-2 border-[#00280b]/20 text-[#00280b] text-xl font-bold"
              >
                -
              </button>
              <span 
                className="text-2xl font-bold text-[#00280b] w-12 text-center"
                style={{ fontFamily: "'Lato', sans-serif" }}
              >
                {partySize}
              </span>
              <button
                onClick={() => setPartySize(Math.min(20, partySize + 1))}
                className="w-12 h-12 rounded-full bg-white border-2 border-[#00280b]/20 text-[#00280b] text-xl font-bold"
              >
                +
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: Area Selection */}
      {step === 2 && (
        <div className="space-y-5">
          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-3" style={{ fontFamily: "'Lato', sans-serif" }}>
              Bereich (optional)
            </label>
            <div className="space-y-2">
              <button
                onClick={() => setSelectedArea("")}
                className={`w-full p-4 rounded-lg text-left transition-colors ${
                  !selectedArea
                    ? "bg-[#00280b] text-[#ffed00]"
                    : "bg-white border border-[#00280b]/20 text-[#00280b]"
                }`}
              >
                <span className="font-medium" style={{ fontFamily: "'Lato', sans-serif" }}>Keine Präferenz</span>
                <p className="text-xs opacity-70 mt-1">Wir wählen den besten verfügbaren Platz</p>
              </button>
              {areas.map((area) => (
                <button
                  key={area.id}
                  onClick={() => setSelectedArea(area.id)}
                  className={`w-full p-4 rounded-lg text-left transition-colors ${
                    selectedArea === area.id
                      ? "bg-[#00280b] text-[#ffed00]"
                      : "bg-white border border-[#00280b]/20 text-[#00280b]"
                  }`}
                >
                  <span className="font-medium" style={{ fontFamily: "'Lato', sans-serif" }}>{area.name}</span>
                  {area.description && (
                    <p className="text-xs opacity-70 mt-1">{area.description}</p>
                  )}
                </button>
              ))}
            </div>
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              Anlass (optional)
            </label>
            <select
              value={guestData.occasion}
              onChange={(e) => setGuestData({ ...guestData, occasion: e.target.value })}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            >
              {occasions.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Step 3: Guest Details */}
      {step === 3 && (
        <div className="space-y-4">
          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              Name *
            </label>
            <input
              type="text"
              value={guestData.name}
              onChange={(e) => setGuestData({ ...guestData, name: e.target.value })}
              placeholder="Max Mustermann"
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              E-Mail *
            </label>
            <input
              type="email"
              value={guestData.email}
              onChange={(e) => setGuestData({ ...guestData, email: e.target.value })}
              placeholder="max@beispiel.de"
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              Telefon *
            </label>
            <input
              type="tel"
              value={guestData.phone}
              onChange={(e) => setGuestData({ ...guestData, phone: e.target.value })}
              placeholder="+49 123 456789"
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          <div 
            className="rounded-xl p-4"
            style={{ backgroundColor: "#f3f6de" }}
          >
            <label className="block text-sm font-medium text-[#00280b] mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
              Besondere Wünsche (optional)
            </label>
            <textarea
              value={guestData.notes}
              onChange={(e) => setGuestData({ ...guestData, notes: e.target.value })}
              placeholder="z.B. Kinderstuhl benötigt, Allergien..."
              rows={3}
              className="w-full p-3 rounded-lg border-2 border-[#00280b]/20 focus:border-[#00280b] bg-white resize-none"
              style={{ fontFamily: "'Lato', sans-serif" }}
            />
          </div>

          {/* Summary */}
          <div 
            className="rounded-xl p-4 border-2"
            style={{ backgroundColor: "white", borderColor: "#00280b" }}
          >
            <h3 className="font-semibold text-[#00280b] mb-2" style={{ fontFamily: "'Playfair Display', serif" }}>
              Ihre Reservierung
            </h3>
            <div className="text-sm text-[#00280b]/80 space-y-1" style={{ fontFamily: "'Lato', sans-serif" }}>
              <p><strong>Datum:</strong> {new Date(selectedDate).toLocaleDateString("de-DE", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</p>
              <p><strong>Uhrzeit:</strong> {selectedTime} Uhr</p>
              <p><strong>Personen:</strong> {partySize}</p>
              {guestData.occasion && <p><strong>Anlass:</strong> {occasions.find(o => o.value === guestData.occasion)?.label}</p>}
            </div>
          </div>

          <p className="text-xs text-[#00280b]/60 text-center" style={{ fontFamily: "'Lato', sans-serif" }}>
            Mit der Reservierung akzeptieren Sie unsere <a href="/datenschutz" className="underline">Datenschutzbestimmungen</a>.
          </p>
        </div>
      )}

      {/* Step 4: Success */}
      {step === 4 && success && (
        <div className="text-center space-y-6 py-8">
          <div 
            className="w-20 h-20 rounded-full mx-auto flex items-center justify-center"
            style={{ backgroundColor: waitlisted ? "#ffed00" : "#00280b" }}
          >
            {waitlisted ? (
              <AlertCircle className="w-10 h-10 text-[#00280b]" />
            ) : (
              <Check className="w-10 h-10 text-[#ffed00]" />
            )}
          </div>
          <div>
            <h2 
              className="text-2xl font-bold text-[#00280b] mb-2"
              style={{ fontFamily: "'Playfair Display', serif" }}
            >
              {waitlisted ? "Auf der Warteliste" : "Reservierung eingegangen!"}
            </h2>
            <p className="text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
              {waitlisted 
                ? "Wir kontaktieren Sie, sobald ein Platz frei wird."
                : "Sie erhalten eine Bestätigung per E-Mail."
              }
            </p>
          </div>
          <button
            onClick={() => {
              setStep(1);
              setSuccess(false);
              setWaitlisted(false);
              setGuestData({ name: "", email: "", phone: "", occasion: "", notes: "" });
              setSelectedTime("");
              setSelectedArea("");
            }}
            className="px-6 py-3 rounded-full font-medium"
            style={{ backgroundColor: "#f3f6de", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            Neue Reservierung
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 inline mr-2" />
          {error}
        </div>
      )}

      {/* Navigation */}
      {!success && (
        <div className="flex gap-3 pt-4">
          {step > 1 && (
            <button
              onClick={() => setStep(step - 1)}
              className="flex-1 p-3 rounded-full font-medium border-2"
              style={{ borderColor: "#00280b", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
            >
              <ChevronLeft className="w-4 h-4 inline mr-1" />
              Zurück
            </button>
          )}
          <button
            onClick={() => {
              if (step < 3) setStep(step + 1);
              else handleSubmit();
            }}
            disabled={!canProceed() || loading}
            className="flex-1 p-3 rounded-full font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ backgroundColor: "#ffed00", color: "#00280b", fontFamily: "'Lato', sans-serif" }}
          >
            {loading ? (
              <Loader2 className="w-4 h-4 inline animate-spin" />
            ) : step < 3 ? (
              <>
                Weiter
                <ChevronRight className="w-4 h-4 inline ml-1" />
              </>
            ) : (
              "Jetzt reservieren"
            )}
          </button>
        </div>
      )}
    </div>
  );
}
