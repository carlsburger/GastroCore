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
import { Loader2, Calendar, Clock, Users, CheckCircle, AlertCircle, CalendarClock, User, Heart, Star, UtensilsCrossed, Info } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Offizielles Carlsburg Logo
const CARLSBURG_LOGO_URL = "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png";

// Panorama Hintergrundbilder für Premium-Optik
const HERO_BACKGROUND = "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&q=80";

// Galerie-Bilder
const GALLERY_IMAGES = [
  { src: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=600&q=80", alt: "Restaurant Ambiente" },
  { src: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=600&q=80", alt: "Terrasse mit Aussicht" },
  { src: "https://images.unsplash.com/photo-1544025162-d76694265947?w=600&q=80", alt: "Kulinarische Köstlichkeiten" },
];

// Occasion options with display labels
const OCCASIONS = [
  { value: "", label: "Kein besonderer Anlass", displayLabel: "" },
  { value: "geburtstag", label: "Geburtstag", displayLabel: "Geburtstag" },
  { value: "hochzeit", label: "Hochzeit / Verlobung", displayLabel: "Hochzeit / Verlobung" },
  { value: "jubilaeum", label: "Jubiläum", displayLabel: "Jubiläum" },
  { value: "geschaeftlich", label: "Geschäftlich", displayLabel: "Geschäftlich" },
  { value: "date", label: "Date Night", displayLabel: "Date Night" },
  { value: "sonstiges", label: "Sonstiges", displayLabel: "Sonstiges" },
];

// Helper to get display label for an occasion value
const getOccasionDisplayLabel = (value) => {
  if (!value || value === "none" || value === "") return null;
  const occasion = OCCASIONS.find(o => o.value === value);
  return occasion?.displayLabel || null;
};

// Öffnungszeiten strukturiert
const OPENING_HOURS = [
  { day: "Mo / Di", time: "Ruhetag" },
  { day: "Mi – Do", time: "12:00 – 18:00 Uhr" },
  { day: "Fr – Sa", time: "12:00 – 20:00 Uhr" },
  { day: "So", time: "12:00 – 18:00 Uhr" },
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
  
  // Event data
  const [eventsForDate, setEventsForDate] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isEventBooking, setIsEventBooking] = useState(false);
  
  // Restaurant branding
  const [logoLoaded, setLogoLoaded] = useState(false);
  const [isClosedDay, setIsClosedDay] = useState(false);
  
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
      bookEvent: "Event buchen",
      closed: "Geschlossen",
      available: "Verfügbar",
      fullyBooked: "Ausgebucht",
      success: "Reservierung erfolgreich!",
      successText: "Sie erhalten eine Bestätigung per E-Mail.",
      waitlistSuccess: "Auf Warteliste gesetzt",
      waitlistText: "Wir kontaktieren Sie, sobald ein Platz frei wird.",
      selectTime: "Bitte wählen Sie eine Uhrzeit",
      eventHint: "À-la-carte-Gerichte sind während der Sonderveranstaltung nur eingeschränkt verfügbar.",
      youAreBooking: "Sie buchen:",
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
      bookEvent: "Book Event",
      closed: "Closed",
      available: "Available",
      fullyBooked: "Fully Booked",
      success: "Reservation Successful!",
      successText: "You will receive a confirmation email.",
      waitlistSuccess: "Added to Waitlist",
      waitlistText: "We'll contact you when a spot opens up.",
      selectTime: "Please select a time",
      eventHint: "À la carte dishes are only available to a limited extent during the special event.",
      youAreBooking: "You are booking:",
    },
  }[lang] || {
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
    bookEvent: "Event buchen",
    closed: "Geschlossen",
    available: "Verfügbar",
    fullyBooked: "Ausgebucht",
    success: "Reservierung erfolgreich!",
    successText: "Sie erhalten eine Bestätigung per E-Mail.",
    waitlistSuccess: "Auf Warteliste gesetzt",
    waitlistText: "Wir kontaktieren Sie, sobald ein Platz frei wird.",
    selectTime: "Bitte wählen Sie eine Uhrzeit",
    eventHint: "À-la-carte-Gerichte sind während der Sonderveranstaltung nur eingeschränkt verfügbar.",
    youAreBooking: "Sie buchen:",
  };

  // Load events for selected date
  const loadEventsForDate = async (selectedDate) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/events`);
      const allEvents = response.data || [];
      
      // Filter events for the selected date
      const dateEvents = allEvents.filter(event => {
        if (!event.start_datetime) return false;
        const eventDate = event.start_datetime.split('T')[0];
        return eventDate === selectedDate;
      });
      
      setEventsForDate(dateEvents);
    } catch (err) {
      console.error("Error loading events:", err);
      setEventsForDate([]);
    }
  };

  // Check availability when date or party size changes
  const checkAvailability = async () => {
    if (!date) return;
    
    setChecking(true);
    setError("");
    setIsClosedDay(false);
    setSelectedEvent(null);
    setIsEventBooking(false);
    
    // Load events for this date
    await loadEventsForDate(date);
    
    // Calculate if selected date is Monday (1) or Tuesday (2) for Ruhetag message
    const selectedDate = new Date(date);
    const dayOfWeek = selectedDate.getDay(); // 0=Sunday, 1=Monday, 2=Tuesday
    const isMondayOrTuesday = dayOfWeek === 1 || dayOfWeek === 2;
    
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/availability`, {
        params: { date, party_size: partySize }
      });
      
      setAvailableSlots(response.data.slots || []);
      
      if (!response.data.available) {
        const slots = response.data.slots || [];
        const allClosed = slots.length === 0 || slots.every(s => s.disabled || !s.available);
        
        if (allClosed) {
          setIsClosedDay(true);
          if (isMondayOrTuesday) {
            setError("Sorry, Montag und Dienstag sind Ruhetag. Ab Mittwoch sind wir gern wieder für Sie da.");
          } else {
            setError(response.data.message || t.fullyBooked);
          }
        } else {
          setError(response.data.message || t.fullyBooked);
        }
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail || "";
      if (errorDetail.toLowerCase().includes("geschlossen") || errorDetail.toLowerCase().includes("closed")) {
        setIsClosedDay(true);
        if (isMondayOrTuesday) {
          setError("Sorry, Montag und Dienstag sind Ruhetag. Ab Mittwoch sind wir gern wieder für Sie da.");
        } else {
          setError(errorDetail || "Fehler bei der Verfügbarkeitsprüfung");
        }
      } else {
        setError(errorDetail || "Fehler bei der Verfügbarkeitsprüfung");
      }
    } finally {
      setChecking(false);
    }
  };

  useEffect(() => {
    if (date && partySize) {
      checkAvailability();
    }
  }, [date, partySize]);

  // Handle event selection
  const handleEventSelect = (event) => {
    setSelectedEvent(event);
    setIsEventBooking(true);
    // Set time to event start time
    if (event.start_datetime) {
      const eventTime = event.start_datetime.split('T')[1]?.substring(0, 5);
      setTime(eventTime || "17:00");
    }
  };

  // Handle regular slot selection
  const handleSlotSelect = (slotTime) => {
    setTime(slotTime);
    setSelectedEvent(null);
    setIsEventBooking(false);
  };

  // Generate event slots (17:00, 17:30, 18:00, 18:30 for event)
  const getEventSlots = (event) => {
    if (!event || !event.start_datetime || !event.end_datetime) return [];
    
    const startTime = event.start_datetime.split('T')[1]?.substring(0, 5) || "17:00";
    const endTime = event.end_datetime.split('T')[1]?.substring(0, 5) || "18:30";
    
    const slots = [];
    const [startHour, startMin] = startTime.split(':').map(Number);
    const [endHour, endMin] = endTime.split(':').map(Number);
    
    let currentHour = startHour;
    let currentMin = startMin;
    
    while (currentHour < endHour || (currentHour === endHour && currentMin <= endMin)) {
      const timeStr = `${String(currentHour).padStart(2, '0')}:${String(currentMin).padStart(2, '0')}`;
      slots.push(timeStr);
      
      currentMin += 30;
      if (currentMin >= 60) {
        currentMin = 0;
        currentHour++;
      }
    }
    
    return slots;
  };

  // Filter out event-blocked times from regular slots
  const getFilteredRegularSlots = () => {
    if (eventsForDate.length === 0) return availableSlots;
    
    // Get all event time ranges
    const eventTimeRanges = eventsForDate.map(event => {
      const startTime = event.start_datetime?.split('T')[1]?.substring(0, 5) || "17:00";
      const endTime = "23:59"; // Block until end of day for event period
      return { start: startTime, end: endTime };
    });
    
    // Filter slots that are NOT in event time ranges
    return availableSlots.filter(slot => {
      const slotTime = slot.time;
      const isInEventRange = eventTimeRanges.some(range => {
        return slotTime >= range.start;
      });
      return !isInEventRange;
    });
  };

  // Extract price from event description
  const getEventPrice = (event) => {
    if (event.ticket_price) return `${event.ticket_price} €`;
    
    // Try to extract from description
    const desc = event.description || "";
    const priceMatch = desc.match(/(\d+[,\.]\d{2})\s*Euro/i);
    if (priceMatch) return `${priceMatch[1]} €`;
    
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      if (isEventBooking && selectedEvent) {
        // Book event
        const response = await axios.post(`${BACKEND_URL}/api/public/events/${selectedEvent.id}/book`, {
          event_id: selectedEvent.id,
          guest_name: guestName,
          guest_phone: guestPhone,
          guest_email: guestEmail || null,
          party_size: partySize,
          notes: notes ? `Gewünschte Zeit: ${time} Uhr. ${notes}` : `Gewünschte Zeit: ${time} Uhr`,
        });
        
        if (response.data.waitlist) {
          setWaitlisted(true);
        }
      } else {
        // Regular booking
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

  // Get filtered regular slots
  const regularSlots = getFilteredRegularSlots();
  const hasEvents = eventsForDate.length > 0;

  return (
    <div className="min-h-screen relative">
      {/* Panorama Background */}
      <div 
        className="fixed inset-0 bg-cover bg-center bg-no-repeat"
        style={{ 
          backgroundImage: `url(${HERO_BACKGROUND})`,
        }}
      >
        {/* Dark Overlay */}
        <div className="absolute inset-0 bg-black/40" />
      </div>

      {/* Main Content */}
      <div className="relative z-10 min-h-screen flex flex-col items-center justify-start py-8 px-4">
        
        {/* Central Widget */}
        <Card className="w-full max-w-lg shadow-2xl border-0 bg-white/95 backdrop-blur-sm">
          <CardHeader className="text-center pb-4 border-b border-gray-100">
            {/* Logo */}
            <div className="flex justify-center mb-2">
              <img 
                src={CARLSBURG_LOGO_URL}
                alt="Carlsburg Historisches Panoramarestaurant"
                className="h-14 sm:h-16 object-contain"
                style={{ filter: 'brightness(0) saturate(100%) invert(15%) sepia(100%) saturate(1500%) hue-rotate(90deg) brightness(0.7)' }}
                onLoad={() => setLogoLoaded(true)}
                onError={() => setLogoLoaded(false)}
              />
            </div>
            
            {/* Claim */}
            <p className="text-xs text-gray-500 tracking-wide uppercase">
              Historisches Panoramarestaurant
            </p>
            
            {/* Öffnungszeiten strukturiert */}
            <div className="mt-4 pt-4 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-700 mb-2">Öffnungszeiten</p>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600 max-w-xs mx-auto">
                {OPENING_HOURS.map((oh, idx) => (
                  <React.Fragment key={idx}>
                    <span className="text-right font-medium">{oh.day}:</span>
                    <span className={oh.time === "Ruhetag" ? "text-red-600" : ""}>{oh.time}</span>
                  </React.Fragment>
                ))}
              </div>
            </div>
            
            <CardTitle className="font-serif text-2xl mt-4 text-gray-900">{t.title}</CardTitle>
            
            {/* Progress indicator */}
            <div className="flex justify-center gap-2 mt-4">
              {[1, 2, 3].map((s) => (
                <div
                  key={s}
                  className={`w-10 h-1.5 rounded-full transition-colors ${
                    s <= step ? "bg-[#005500]" : "bg-gray-200"
                  }`}
                />
              ))}
            </div>
          </CardHeader>
          
          <CardContent className="space-y-4 pt-6">
            {error && !hasEvents && (
              <Alert variant="destructive" className="animate-fade-in">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            {/* Step 1: Date & Time Selection */}
            {step === 1 && (
              <div className="space-y-5 animate-fade-in">
                <div className="space-y-2">
                  <Label htmlFor="date" className="flex items-center gap-2 text-gray-700">
                    <Calendar size={16} className="text-[#005500]" />
                    {t.date}
                  </Label>
                  <Input
                    id="date"
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                    min={today}
                    max={maxDate}
                    className="h-12 border-gray-300 focus:border-[#005500] focus:ring-[#005500]"
                    data-testid="widget-date"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="partySize" className="flex items-center gap-2 text-gray-700">
                    <Users size={16} className="text-[#005500]" />
                    {t.guests}
                  </Label>
                  <Select value={String(partySize)} onValueChange={(v) => setPartySize(parseInt(v))}>
                    <SelectTrigger className="h-12 border-gray-300" data-testid="widget-party-size">
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
                  <div className="flex justify-center py-6">
                    <Loader2 className="h-8 w-8 animate-spin text-[#005500]" />
                  </div>
                )}
                
                {/* Event Card - wenn Events vorhanden */}
                {hasEvents && !checking && (
                  <div className="space-y-3">
                    {eventsForDate.map((event) => {
                      const eventSlots = getEventSlots(event);
                      const eventPrice = getEventPrice(event);
                      const startTime = event.start_datetime?.split('T')[1]?.substring(0, 5) || "17:00";
                      const endTime = event.end_datetime?.split('T')[1]?.substring(0, 5) || "18:30";
                      
                      return (
                        <div 
                          key={event.id}
                          className={`p-4 rounded-xl border-2 transition-all ${
                            selectedEvent?.id === event.id 
                              ? "border-[#005500] bg-[#005500]/5" 
                              : "border-amber-200 bg-amber-50 hover:border-amber-300"
                          }`}
                        >
                          {/* Event Header */}
                          <div className="flex items-start gap-3 mb-3">
                            <div className="w-10 h-10 rounded-lg bg-amber-500 flex items-center justify-center flex-shrink-0">
                              <Star className="h-5 w-5 text-white" />
                            </div>
                            <div className="flex-1">
                              <h3 className="font-semibold text-gray-900">{event.title}</h3>
                              <p className="text-sm text-gray-600">
                                Buchbar {startTime}–{endTime} Uhr (letzte Reservierung {endTime} Uhr)
                              </p>
                              {eventPrice && (
                                <p className="text-sm font-semibold text-[#005500] mt-1">
                                  {eventPrice} p. P.
                                </p>
                              )}
                            </div>
                          </div>
                          
                          {/* Event Hint */}
                          <div className="flex items-start gap-2 text-xs text-amber-700 bg-amber-100 p-2 rounded-lg mb-3">
                            <Info className="h-4 w-4 flex-shrink-0 mt-0.5" />
                            <span>{t.eventHint}</span>
                          </div>
                          
                          {/* Event Slots */}
                          <div className="space-y-2">
                            <Label className="text-xs text-gray-600">Event-Zeiten wählen:</Label>
                            <div className="grid grid-cols-4 gap-2">
                              {eventSlots.map((slotTime) => (
                                <Button
                                  key={slotTime}
                                  type="button"
                                  variant={selectedEvent?.id === event.id && time === slotTime ? "default" : "outline"}
                                  className={`h-10 text-sm ${
                                    selectedEvent?.id === event.id && time === slotTime 
                                      ? "bg-[#005500] hover:bg-[#004400]" 
                                      : "border-amber-300 hover:bg-amber-100"
                                  }`}
                                  onClick={() => {
                                    handleEventSelect(event);
                                    setTime(slotTime);
                                  }}
                                  data-testid={`event-slot-${slotTime}`}
                                >
                                  {slotTime}
                                </Button>
                              ))}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                
                {/* Regular Slots */}
                {regularSlots.length > 0 && !checking && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2 text-gray-700">
                      <Clock size={16} className="text-[#005500]" />
                      {hasEvents ? "Reguläre Zeiten" : t.time}
                    </Label>
                    <div className="grid grid-cols-4 gap-2">
                      {regularSlots.map((slot) => (
                        <Button
                          key={slot.time}
                          type="button"
                          variant={!isEventBooking && time === slot.time ? "default" : "outline"}
                          className={`h-10 ${!slot.available ? "opacity-50 cursor-not-allowed" : ""} ${
                            !isEventBooking && time === slot.time 
                              ? "bg-[#005500] hover:bg-[#004400]" 
                              : ""
                          }`}
                          onClick={() => slot.available && handleSlotSelect(slot.time)}
                          disabled={!slot.available}
                          data-testid={`slot-${slot.time}`}
                        >
                          {slot.time}
                        </Button>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Closed day error (only if no events) */}
                {error && isClosedDay && !hasEvents && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                <Button
                  className="w-full h-12 rounded-full font-semibold bg-[#005500] hover:bg-[#004400] text-white"
                  onClick={() => setStep(2)}
                  disabled={!date || !time}
                  data-testid="widget-next"
                >
                  {isEventBooking ? t.bookEvent : t.next}
                </Button>
              </div>
            )}
            
            {/* Step 2: Guest Details */}
            {step === 2 && (
              <form onSubmit={handleSubmit} className="space-y-4 animate-fade-in">
                {/* Booking Summary */}
                <div className="bg-gray-50 p-4 rounded-xl">
                  {/* Event Booking Header */}
                  {isEventBooking && selectedEvent && (
                    <div className="mb-3 pb-3 border-b border-gray-200">
                      <div className="flex items-center gap-2 text-[#005500] font-semibold">
                        <Star className="h-4 w-4" />
                        <span>{t.youAreBooking}</span>
                      </div>
                      <p className="font-bold text-lg text-gray-900 mt-1">{selectedEvent.title}</p>
                      {getEventPrice(selectedEvent) && (
                        <p className="text-sm text-[#005500] font-medium">{getEventPrice(selectedEvent)} p. P.</p>
                      )}
                      <div className="mt-2 text-xs text-amber-700 bg-amber-50 p-2 rounded flex items-start gap-2">
                        <Info className="h-3 w-3 flex-shrink-0 mt-0.5" />
                        <span>{t.eventHint}</span>
                      </div>
                    </div>
                  )}
                  
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-4">
                      <span className="flex items-center gap-1 text-gray-600">
                        <Calendar size={14} className="text-[#005500]" />
                        {date}
                      </span>
                      <span className="flex items-center gap-1 text-gray-600">
                        <Clock size={14} className="text-[#005500]" />
                        {time} Uhr
                      </span>
                      <span className="flex items-center gap-1 text-gray-600">
                        <Users size={14} className="text-[#005500]" />
                        {partySize}
                      </span>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => setStep(1)} className="text-[#005500]">
                      Ändern
                    </Button>
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="guestName" className="text-gray-700">{t.name} *</Label>
                  <Input
                    id="guestName"
                    value={guestName}
                    onChange={(e) => setGuestName(e.target.value)}
                    required
                    className="h-11 border-gray-300 focus:border-[#005500] focus:ring-[#005500]"
                    data-testid="widget-name"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="guestPhone" className="text-gray-700">{t.phone} *</Label>
                  <Input
                    id="guestPhone"
                    type="tel"
                    value={guestPhone}
                    onChange={(e) => setGuestPhone(e.target.value)}
                    required
                    className="h-11 border-gray-300 focus:border-[#005500] focus:ring-[#005500]"
                    data-testid="widget-phone"
                  />
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="guestEmail" className="text-gray-700">{t.email} *</Label>
                  <Input
                    id="guestEmail"
                    type="email"
                    value={guestEmail}
                    onChange={(e) => setGuestEmail(e.target.value)}
                    required
                    className="h-11 border-gray-300 focus:border-[#005500] focus:ring-[#005500]"
                    data-testid="widget-email"
                  />
                </div>
                
                {!isEventBooking && (
                  <div className="space-y-2">
                    <Label htmlFor="occasion" className="text-gray-700">{t.occasion}</Label>
                    <Select value={occasion} onValueChange={setOccasion}>
                      <SelectTrigger className="h-11 border-gray-300" data-testid="widget-occasion">
                        <SelectValue placeholder="Optional" />
                      </SelectTrigger>
                      <SelectContent>
                        {OCCASIONS.map((o) => (
                          <SelectItem key={o.value} value={o.value || "none"}>{o.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="notes" className="text-gray-700">{t.notes}</Label>
                  <Textarea
                    id="notes"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Allergien, Kinderstühle, etc."
                    className="min-h-[80px] border-gray-300 focus:border-[#005500] focus:ring-[#005500]"
                    data-testid="widget-notes"
                  />
                </div>
                
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                <div className="flex gap-3 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1 h-12 rounded-full border-gray-300"
                    onClick={() => setStep(1)}
                  >
                    {t.back}
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1 h-12 rounded-full font-semibold bg-[#005500] hover:bg-[#004400]"
                    disabled={loading}
                    data-testid="widget-submit"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (isEventBooking ? t.bookEvent : t.book)}
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
                
                {/* Confirmation Headline */}
                {!waitlisted && (
                  <p className="text-base text-gray-700 mb-4 font-medium">
                    Vielen Dank für Ihre Reservierung – wir freuen uns auf Sie.
                  </p>
                )}
                
                <h2 className="font-serif text-2xl mb-2 text-gray-900">
                  {waitlisted ? t.waitlistSuccess : t.success}
                </h2>
                <p className="text-gray-500">
                  {waitlisted ? t.waitlistText : t.successText}
                </p>
                
                {/* Event Info in Confirmation */}
                {isEventBooking && selectedEvent && (
                  <div className="mt-4 p-3 bg-amber-50 rounded-lg border border-amber-200">
                    <div className="flex items-center gap-2 justify-center text-amber-700">
                      <Star className="h-4 w-4" />
                      <span className="font-semibold">{selectedEvent.title}</span>
                    </div>
                    <p className="text-xs text-amber-600 mt-1">{t.eventHint}</p>
                  </div>
                )}
                
                <div className="bg-gray-50 p-4 rounded-xl mt-6 text-left">
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {/* Name */}
                    {guestName && (
                      <>
                        <span className="text-gray-500 flex items-center gap-1">
                          <User size={14} className="text-[#005500]" />
                          {t.name}:
                        </span>
                        <span className="font-medium text-gray-900">{guestName}</span>
                      </>
                    )}
                    <span className="text-gray-500">{t.date}:</span>
                    <span className="font-medium text-gray-900">{date}</span>
                    <span className="text-gray-500">{t.time}:</span>
                    <span className="font-medium text-gray-900">{time} Uhr</span>
                    <span className="text-gray-500">{t.guests}:</span>
                    <span className="font-medium text-gray-900">{partySize}</span>
                    {/* Anlass (nur wenn ausgewählt und keine Event-Buchung) */}
                    {!isEventBooking && getOccasionDisplayLabel(occasion) && (
                      <>
                        <span className="text-gray-500 flex items-center gap-1">
                          <Heart size={14} className="text-[#005500]" />
                          {t.occasion}:
                        </span>
                        <span className="font-medium text-gray-900">{getOccasionDisplayLabel(occasion)}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        
        {/* Gallery Section */}
        <div className="w-full max-w-4xl mt-8 px-4">
          <div className="grid grid-cols-3 gap-3">
            {GALLERY_IMAGES.map((img, idx) => (
              <div 
                key={idx} 
                className="aspect-[4/3] rounded-xl overflow-hidden shadow-lg"
              >
                <img 
                  src={img.src} 
                  alt={img.alt}
                  className="w-full h-full object-cover hover:scale-105 transition-transform duration-500"
                />
              </div>
            ))}
          </div>
        </div>
        
        {/* Footer */}
        <footer className="mt-8 text-center text-white/70 text-xs">
          © {new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant
        </footer>
      </div>
    </div>
  );
};

export default BookingWidget;
