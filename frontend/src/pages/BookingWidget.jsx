import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import { Loader2, Calendar, Clock, Users, CheckCircle, AlertCircle, CalendarClock } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Occasion options
const OCCASIONS = [
  { value: "", label: "Kein besonderer Anlass" },
  { value: "geburtstag", label: "Geburtstag" },
  { value: "hochzeit", label: "Hochzeit / Verlobung" },
  { value: "jubilaeum", label: "Jubiläum" },
  { value: "geschaeftlich", label: "Geschäftlich" },
  { value: "date", label: "Date Night" },
  { value: "sonstiges", label: "Sonstiges" },
];

export const BookingWidget = () => {
  const [searchParams] = useSearchParams();
  
  // Initial values from URL params (for embed)
  const initialDate = searchParams.get("date") || "";
  const initialTime = searchParams.get("time") || "";
  const initialPartySize = parseInt(searchParams.get("party_size") || "2");
  const lang = searchParams.get("lang") || "de";
  
  const [step, setStep] = useState(1); // 1: Select date/time, 2: Enter details, 3: Confirmation
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [waitlisted, setWaitlisted] = useState(false);
  
  // Form data
  const [date, setDate] = useState(initialDate);
  const [time, setTime] = useState(initialTime);
  const [partySize, setPartySize] = useState(initialPartySize);
  const [availableSlots, setAvailableSlots] = useState([]);
  const [guestName, setGuestName] = useState("");
  const [guestPhone, setGuestPhone] = useState("");
  const [guestEmail, setGuestEmail] = useState("");
  const [occasion, setOccasion] = useState("");
  const [notes, setNotes] = useState("");
  
  // Restaurant branding
  const [restaurantName, setRestaurantName] = useState("");
  const [restaurantInitial, setRestaurantInitial] = useState("C");
  
  // Translations
  const t = {
    de: {
      title: "Tisch reservieren",
      step1: "Wählen Sie Datum & Zeit",
      step2: "Ihre Daten",
      step3: "Bestätigung",
      date: "Datum",
      time: "Uhrzeit",
      guests: "Personenzahl",
      name: "Name",
      phone: "Telefon",
      email: "E-Mail",
      occasion: "Anlass",
      notes: "Anmerkungen",
      checkAvailability: "Verfügbarkeit prüfen",
      next: "Weiter",
      back: "Zurück",
      book: "Jetzt reservieren",
      closed: "Geschlossen",
      available: "Verfügbar",
      fullyBooked: "Ausgebucht",
      success: "Reservierung erfolgreich!",
      successText: "Sie erhalten eine Bestätigung per E-Mail.",
      waitlistSuccess: "Auf Warteliste gesetzt",
      waitlistText: "Wir kontaktieren Sie, sobald ein Platz frei wird.",
      selectTime: "Bitte wählen Sie eine Uhrzeit",
    },
    en: {
      title: "Book a Table",
      step1: "Select Date & Time",
      step2: "Your Details",
      step3: "Confirmation",
      date: "Date",
      time: "Time",
      guests: "Party Size",
      name: "Name",
      phone: "Phone",
      email: "Email",
      occasion: "Occasion",
      notes: "Notes",
      checkAvailability: "Check Availability",
      next: "Next",
      back: "Back",
      book: "Book Now",
      closed: "Closed",
      available: "Available",
      fullyBooked: "Fully Booked",
      success: "Reservation Successful!",
      successText: "You will receive a confirmation email.",
      waitlistSuccess: "Added to Waitlist",
      waitlistText: "We'll contact you when a spot opens up.",
      selectTime: "Please select a time",
    },
    pl: {
      title: "Zarezerwuj stolik",
      step1: "Wybierz datę i godzinę",
      step2: "Twoje dane",
      step3: "Potwierdzenie",
      date: "Data",
      time: "Godzina",
      guests: "Liczba osób",
      name: "Imię i nazwisko",
      phone: "Telefon",
      email: "E-mail",
      occasion: "Okazja",
      notes: "Uwagi",
      checkAvailability: "Sprawdź dostępność",
      next: "Dalej",
      back: "Wstecz",
      book: "Zarezerwuj teraz",
      closed: "Zamknięte",
      available: "Dostępne",
      fullyBooked: "Brak miejsc",
      success: "Rezerwacja udana!",
      successText: "Otrzymasz potwierdzenie e-mailem.",
      waitlistSuccess: "Dodano do listy oczekujących",
      waitlistText: "Skontaktujemy się, gdy miejsce się zwolni.",
      selectTime: "Proszę wybrać godzinę",
    },
  }[lang] || t.de;

  // Check availability when date or party size changes
  const checkAvailability = async () => {
    if (!date) return;
    
    setChecking(true);
    setError("");
    
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/availability`, {
        params: { date, party_size: partySize }
      });
      
      setAvailableSlots(response.data.slots || []);
      
      if (!response.data.available) {
        setError(response.data.message || t.fullyBooked);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Fehler bei der Verfügbarkeitsprüfung");
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    if (date && partySize) {
      checkAvailability();
    }
  }, [date, partySize]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      const response = await axios.post(`${BACKEND_URL}/api/public/book`, {
        guest_name: guestName,
        guest_phone: guestPhone,
        guest_email: guestEmail,
        party_size: partySize,
        date,
        time,
        occasion: occasion || null,
        notes: notes || null,
        language: lang
      });
      
      if (response.data.waitlist) {
        setWaitlisted(true);
      }
      setSuccess(true);
      setStep(3);
    } catch (err) {
      setError(err.response?.data?.detail || "Reservierung fehlgeschlagen");
    } finally {
      setLoading(false);
    }
  };

  // Get min date (today)
  const today = new Date().toISOString().split('T')[0];
  // Get max date (90 days)
  const maxDate = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

  return (
    <div className="min-h-screen bg-background p-4 flex items-center justify-center">
      <Card className="w-full max-w-md shadow-xl border-border">
        <CardHeader className="text-center pb-2">
          <div className="w-12 h-12 rounded-full bg-primary mx-auto flex items-center justify-center mb-2">
            <span className="text-primary-foreground font-serif text-xl font-bold">C</span>
          </div>
          <CardTitle className="font-serif text-2xl">{t.title}</CardTitle>
          
          {/* Progress indicator */}
          <div className="flex justify-center gap-2 mt-4">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={`w-8 h-1 rounded-full transition-colors ${
                  s <= step ? "bg-primary" : "bg-muted"
                }`}
              />
            ))}
          </div>
        </CardHeader>
        
        <CardContent className="space-y-4">
          {error && (
            <Alert variant="destructive" className="animate-fade-in">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          
          {/* Step 1: Date & Time Selection */}
          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <div className="space-y-2">
                <Label htmlFor="date" className="flex items-center gap-2">
                  <Calendar size={16} />
                  {t.date}
                </Label>
                <Input
                  id="date"
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  min={today}
                  max={maxDate}
                  className="h-12"
                  data-testid="widget-date"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="partySize" className="flex items-center gap-2">
                  <Users size={16} />
                  {t.guests}
                </Label>
                <Select value={String(partySize)} onValueChange={(v) => setPartySize(parseInt(v))}>
                  <SelectTrigger className="h-12" data-testid="widget-party-size">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) => (
                      <SelectItem key={n} value={String(n)}>{n} {n === 1 ? "Person" : "Personen"}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {checking && (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-6 w-6 animate-spin text-primary" />
                </div>
              )}
              
              {/* Available time slots */}
              {availableSlots.length > 0 && (
                <div className="space-y-2">
                  <Label className="flex items-center gap-2">
                    <Clock size={16} />
                    {t.time}
                  </Label>
                  <div className="grid grid-cols-4 gap-2">
                    {availableSlots.map((slot) => (
                      <Button
                        key={slot.time}
                        type="button"
                        variant={time === slot.time ? "default" : "outline"}
                        className={`h-10 ${!slot.available ? "opacity-50 cursor-not-allowed" : ""}`}
                        onClick={() => slot.available && setTime(slot.time)}
                        disabled={!slot.available}
                        data-testid={`slot-${slot.time}`}
                      >
                        {slot.time}
                      </Button>
                    ))}
                  </div>
                </div>
              )}
              
              <Button
                className="w-full h-12 rounded-full font-bold"
                onClick={() => setStep(2)}
                disabled={!date || !time}
                data-testid="widget-next"
              >
                {t.next}
              </Button>
            </div>
          )}
          
          {/* Step 2: Guest Details */}
          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-4 animate-fade-in">
              <div className="bg-muted p-3 rounded-lg flex items-center justify-between text-sm">
                <div className="flex items-center gap-4">
                  <span className="flex items-center gap-1">
                    <Calendar size={14} />
                    {date}
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={14} />
                    {time}
                  </span>
                  <span className="flex items-center gap-1">
                    <Users size={14} />
                    {partySize}
                  </span>
                </div>
                <Button type="button" variant="ghost" size="sm" onClick={() => setStep(1)}>
                  Ändern
                </Button>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="guestName">{t.name} *</Label>
                <Input
                  id="guestName"
                  value={guestName}
                  onChange={(e) => setGuestName(e.target.value)}
                  required
                  className="h-11"
                  data-testid="widget-name"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="guestPhone">{t.phone} *</Label>
                <Input
                  id="guestPhone"
                  type="tel"
                  value={guestPhone}
                  onChange={(e) => setGuestPhone(e.target.value)}
                  required
                  className="h-11"
                  data-testid="widget-phone"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="guestEmail">{t.email} *</Label>
                <Input
                  id="guestEmail"
                  type="email"
                  value={guestEmail}
                  onChange={(e) => setGuestEmail(e.target.value)}
                  required
                  className="h-11"
                  data-testid="widget-email"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="occasion">{t.occasion}</Label>
                <Select value={occasion} onValueChange={setOccasion}>
                  <SelectTrigger className="h-11" data-testid="widget-occasion">
                    <SelectValue placeholder="Optional" />
                  </SelectTrigger>
                  <SelectContent>
                    {OCCASIONS.map((o) => (
                      <SelectItem key={o.value} value={o.value || "none"}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="notes">{t.notes}</Label>
                <Textarea
                  id="notes"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Allergien, Kinderstühle, etc."
                  className="min-h-[80px]"
                  data-testid="widget-notes"
                />
              </div>
              
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="flex-1 h-12 rounded-full"
                  onClick={() => setStep(1)}
                >
                  {t.back}
                </Button>
                <Button
                  type="submit"
                  className="flex-1 h-12 rounded-full font-bold"
                  disabled={loading}
                  data-testid="widget-submit"
                >
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t.book}
                </Button>
              </div>
            </form>
          )}
          
          {/* Step 3: Confirmation */}
          {step === 3 && success && (
            <div className="text-center py-6 animate-fade-in">
              <div className={`w-16 h-16 rounded-full mx-auto flex items-center justify-center mb-4 ${
                waitlisted ? "bg-yellow-100" : "bg-green-100"
              }`}>
                {waitlisted ? (
                  <CalendarClock className="h-8 w-8 text-yellow-600" />
                ) : (
                  <CheckCircle className="h-8 w-8 text-green-600" />
                )}
              </div>
              <h2 className="font-serif text-2xl mb-2">
                {waitlisted ? t.waitlistSuccess : t.success}
              </h2>
              <p className="text-muted-foreground">
                {waitlisted ? t.waitlistText : t.successText}
              </p>
              
              <div className="bg-muted p-4 rounded-lg mt-6 text-left">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <span className="text-muted-foreground">{t.date}:</span>
                  <span className="font-medium">{date}</span>
                  <span className="text-muted-foreground">{t.time}:</span>
                  <span className="font-medium">{time} Uhr</span>
                  <span className="text-muted-foreground">{t.guests}:</span>
                  <span className="font-medium">{partySize}</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default BookingWidget;
