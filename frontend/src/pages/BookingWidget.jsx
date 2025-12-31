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
import { Loader2, Calendar, Clock, Users, CheckCircle, AlertCircle, CalendarClock, User, Heart, Star, Info, ChevronLeft, ChevronRight } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Offizielles Carlsburg Logo
const CARLSBURG_LOGO_URL = "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png";

// ============================================
// BILDER-KONFIGURATION
// ============================================
// Sobald echte Carlsburg-Bilder hochgeladen werden, hier die Pfade anpassen:
// HERO_BACKGROUND = "/booking/K7A3951.jpg"
// GALLERY_IMAGES[0].src = "/booking/blick-terrasse-sommer-1.jpg"
// etc.
// ============================================

// Panorama Hintergrundbild (wird durch echtes Carlsburg-Bild ersetzt)
const HERO_BACKGROUND = "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&q=80";

// Galerie-Bilder (werden durch echte Carlsburg-Bilder ersetzt)
const GALLERY_IMAGES = [
  { src: "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=800&q=80", alt: "Restaurant Ambiente" },
  { src: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=800&q=80", alt: "Terrasse mit Aussicht" },
  { src: "https://images.unsplash.com/photo-1544025162-d76694265947?w=800&q=80", alt: "Kulinarische Köstlichkeiten" },
];

// Occasion options
const OCCASIONS = [
  { value: "", label: "Kein besonderer Anlass", displayLabel: "" },
  { value: "geburtstag", label: "Geburtstag", displayLabel: "Geburtstag" },
  { value: "hochzeit", label: "Hochzeit / Verlobung", displayLabel: "Hochzeit / Verlobung" },
  { value: "jubilaeum", label: "Jubiläum", displayLabel: "Jubiläum" },
  { value: "geschaeftlich", label: "Geschäftlich", displayLabel: "Geschäftlich" },
  { value: "date", label: "Date Night", displayLabel: "Date Night" },
  { value: "sonstiges", label: "Sonstiges", displayLabel: "Sonstiges" },
];

const getOccasionDisplayLabel = (value) => {
  if (!value || value === "none" || value === "") return null;
  const occasion = OCCASIONS.find(o => o.value === value);
  return occasion?.displayLabel || null;
};

export const BookingWidget = () => {
  const [searchParams] = useSearchParams();
  
  const initialDate = searchParams.get("date") || "";
  const initialTime = searchParams.get("time") || "";
  const initialPartySize = parseInt(searchParams.get("party_size") || "2");
  const lang = searchParams.get("lang") || "de";
  
  const [step, setStep] = useState(1);
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
  
  // Mobile gallery carousel
  const [galleryIndex, setGalleryIndex] = useState(0);
  
  // Translations
  const t = {
    title: "Tisch reservieren",
    date: "Datum",
    time: "Uhrzeit",
    guests: "Personen",
    name: "Name",
    phone: "Telefon",
    email: "E-Mail",
    occasion: "Anlass",
    notes: "Anmerkungen",
    next: "Weiter",
    back: "Zurück",
    book: "Jetzt reservieren",
    bookEvent: "Event buchen",
    fullyBooked: "Ausgebucht",
    success: "Reservierung erfolgreich!",
    successText: "Sie erhalten eine Bestätigung per E-Mail.",
    waitlistSuccess: "Auf Warteliste gesetzt",
    waitlistText: "Wir kontaktieren Sie, sobald ein Platz frei wird.",
    eventHint: "À-la-carte-Gerichte sind während der Sonderveranstaltung nur eingeschränkt verfügbar.",
    youAreBooking: "Sie buchen:",
  };

  // Load events for selected date
  const loadEventsForDate = async (selectedDate) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/events`);
      const allEvents = response.data || [];
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

  // Check availability
  const checkAvailability = async () => {
    if (!date) return;
    
    setChecking(true);
    setError("");
    setSelectedEvent(null);
    setIsEventBooking(false);
    
    await loadEventsForDate(date);
    
    const selectedDate = new Date(date);
    const dayOfWeek = selectedDate.getDay();
    const isMondayOrTuesday = dayOfWeek === 1 || dayOfWeek === 2;
    
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/availability`, {
        params: { date, party_size: partySize }
      });
      
      setAvailableSlots(response.data.slots || []);
      
      if (!response.data.available) {
        const slots = response.data.slots || [];
        const allClosed = slots.length === 0 || slots.every(s => s.disabled || !s.available);
        
        if (allClosed && isMondayOrTuesday) {
          setError("Sorry, Montag und Dienstag sind Ruhetag. Ab Mittwoch sind wir gern wieder für Sie da.");
        } else if (allClosed) {
          setError(response.data.message || t.fullyBooked);
        }
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail || "";
      if (isMondayOrTuesday) {
        setError("Sorry, Montag und Dienstag sind Ruhetag. Ab Mittwoch sind wir gern wieder für Sie da.");
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

  // Event handlers
  const handleEventSelect = (event) => {
    setSelectedEvent(event);
    setIsEventBooking(true);
    if (event.start_datetime) {
      const eventTime = event.start_datetime.split('T')[1]?.substring(0, 5);
      setTime(eventTime || "17:00");
    }
  };

  const handleSlotSelect = (slotTime) => {
    setTime(slotTime);
    setSelectedEvent(null);
    setIsEventBooking(false);
  };

  // Generate event slots
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
      slots.push(`${String(currentHour).padStart(2, '0')}:${String(currentMin).padStart(2, '0')}`);
      currentMin += 30;
      if (currentMin >= 60) {
        currentMin = 0;
        currentHour++;
      }
    }
    return slots;
  };

  // Filter regular slots (exclude event times)
  const getFilteredRegularSlots = () => {
    if (eventsForDate.length === 0) return availableSlots;
    
    const eventTimeRanges = eventsForDate.map(event => ({
      start: event.start_datetime?.split('T')[1]?.substring(0, 5) || "17:00"
    }));
    
    return availableSlots.filter(slot => {
      return !eventTimeRanges.some(range => slot.time >= range.start);
    });
  };

  // Extract event price
  const getEventPrice = (event) => {
    if (event.ticket_price) return `${event.ticket_price} €`;
    const desc = event.description || "";
    const priceMatch = desc.match(/(\d+[,\.]\d{2})\s*Euro/i);
    if (priceMatch) return `${priceMatch[1]} €`;
    return null;
  };

  // Submit handler
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    try {
      if (isEventBooking && selectedEvent) {
        await axios.post(`${BACKEND_URL}/api/public/events/${selectedEvent.id}/book`, {
          event_id: selectedEvent.id,
          guest_name: guestName,
          guest_phone: guestPhone,
          guest_email: guestEmail || null,
          party_size: partySize,
          notes: notes ? `Gewünschte Zeit: ${time} Uhr. ${notes}` : `Gewünschte Zeit: ${time} Uhr`,
        });
      } else {
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
        if (response.data.waitlist) setWaitlisted(true);
      }
      setSuccess(true);
      setStep(3);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map(d => d.msg).join(", ") || "Reservierung fehlgeschlagen");
      } else if (typeof detail === 'object') {
        setError(detail.msg || "Reservierung fehlgeschlagen");
      } else {
        setError(detail || "Reservierung fehlgeschlagen");
      }
    } finally {
      setLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];
  const maxDate = new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
  const regularSlots = getFilteredRegularSlots();
  const hasEvents = eventsForDate.length > 0;

  // Mobile gallery navigation
  const nextGalleryImage = () => setGalleryIndex((prev) => (prev + 1) % GALLERY_IMAGES.length);
  const prevGalleryImage = () => setGalleryIndex((prev) => (prev - 1 + GALLERY_IMAGES.length) % GALLERY_IMAGES.length);

  return (
    <div className="h-screen w-screen overflow-hidden relative">
      {/* Panorama Background - Full Screen */}
      <div 
        className="absolute inset-0 bg-cover bg-center bg-no-repeat"
        style={{ backgroundImage: `url(${HERO_BACKGROUND})` }}
      >
        <div className="absolute inset-0 bg-black/40" />
      </div>

      {/* Main Layout Container - 100vh, no scroll */}
      <div className="relative z-10 h-full w-full flex items-center justify-center p-3 lg:p-5">
        
        {/* Desktop: 2-Column Layout | Mobile: Single Column */}
        <div className="w-full max-w-[1100px] h-full max-h-[92vh] flex flex-col lg:flex-row gap-3 lg:gap-4">
          
          {/* LEFT: Booking Widget */}
          <div className="flex-1 lg:flex-[0_0_62%] min-h-0 flex flex-col">
            <Card className="flex-1 flex flex-col shadow-2xl border-0 bg-white/95 backdrop-blur-sm overflow-hidden rounded-xl">
              
              {/* Header - ENTSCHLACKT: Nur Logo, kein Claim-Text */}
              <CardHeader className="flex-shrink-0 text-center py-2 lg:py-3 border-b border-gray-100">
                {/* Logo ONLY - kein "Historisches Panoramarestaurant" Text */}
                <div className="flex justify-center mb-1">
                  <img 
                    src={CARLSBURG_LOGO_URL}
                    alt="Carlsburg"
                    className="h-9 lg:h-11 object-contain"
                    style={{ filter: 'brightness(0) saturate(100%) invert(15%) sepia(100%) saturate(1500%) hue-rotate(90deg) brightness(0.7)' }}
                  />
                </div>
                
                {/* Öffnungszeiten - Kompakt (Winter) */}
                <div className="mt-1.5 pt-1.5 border-t border-gray-100">
                  <p className="text-[9px] lg:text-[10px] font-semibold text-gray-700 mb-0.5">Öffnungszeiten</p>
                  <div className="text-[9px] lg:text-[10px] text-gray-600 leading-tight">
                    <span className="font-medium">Mo / Di:</span> <span className="text-red-600">Ruhetag</span>
                    <span className="mx-1.5">·</span>
                    <span className="font-medium">Mi / Do / So:</span> 12–18 Uhr
                    <span className="mx-1.5">·</span>
                    <span className="font-medium">Fr / Sa:</span> 12–20 Uhr
                  </div>
                </div>
                
                <CardTitle className="font-serif text-base lg:text-lg mt-1.5 text-gray-900">{t.title}</CardTitle>
                
                {/* Progress */}
                <div className="flex justify-center gap-1.5 mt-1.5">
                  {[1, 2, 3].map((s) => (
                    <div key={s} className={`w-7 lg:w-8 h-1 rounded-full transition-colors ${s <= step ? "bg-[#005500]" : "bg-gray-200"}`} />
                  ))}
                </div>
              </CardHeader>
              
              {/* Content - Scrollable if needed */}
              <CardContent className="flex-1 overflow-y-auto p-2.5 lg:p-3">
                
                {/* Error Alert */}
                {error && !hasEvents && (
                  <Alert variant="destructive" className="mb-2">
                    <AlertCircle className="h-3.5 w-3.5" />
                    <AlertDescription className="text-[11px] lg:text-xs">{error}</AlertDescription>
                  </Alert>
                )}
                
                {/* Step 1: Date & Time */}
                {step === 1 && (
                  <div className="space-y-2.5">
                    {/* Date & Party Size - Horizontal */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-0.5">
                        <Label className="text-[10px] lg:text-xs flex items-center gap-1 text-gray-700">
                          <Calendar size={12} className="text-[#005500]" />
                          {t.date}
                        </Label>
                        <Input
                          type="date"
                          value={date}
                          onChange={(e) => setDate(e.target.value)}
                          min={today}
                          max={maxDate}
                          className="h-8 lg:h-9 text-xs lg:text-sm border-gray-300"
                        />
                      </div>
                      <div className="space-y-0.5">
                        <Label className="text-[10px] lg:text-xs flex items-center gap-1 text-gray-700">
                          <Users size={12} className="text-[#005500]" />
                          {t.guests}
                        </Label>
                        <Select value={String(partySize)} onValueChange={(v) => setPartySize(parseInt(v))}>
                          <SelectTrigger className="h-8 lg:h-9 text-xs lg:text-sm border-gray-300">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) => (
                              <SelectItem key={n} value={String(n)}>{n}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    
                    {checking && (
                      <div className="flex justify-center py-3">
                        <Loader2 className="h-5 w-5 animate-spin text-[#005500]" />
                      </div>
                    )}
                    
                    {/* Event Card */}
                    {hasEvents && !checking && eventsForDate.map((event) => {
                      const eventSlots = getEventSlots(event);
                      const eventPrice = getEventPrice(event);
                      const startTime = event.start_datetime?.split('T')[1]?.substring(0, 5) || "17:00";
                      const endTime = event.end_datetime?.split('T')[1]?.substring(0, 5) || "18:30";
                      
                      return (
                        <div 
                          key={event.id}
                          className={`p-2.5 rounded-lg border-2 transition-all ${
                            selectedEvent?.id === event.id 
                              ? "border-[#005500] bg-[#005500]/5" 
                              : "border-amber-200 bg-amber-50"
                          }`}
                        >
                          <div className="flex items-start gap-2 mb-1.5">
                            <div className="w-7 h-7 rounded-md bg-amber-500 flex items-center justify-center flex-shrink-0">
                              <Star className="h-3.5 w-3.5 text-white" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-xs lg:text-sm text-gray-900 truncate">{event.title}</h3>
                              <p className="text-[10px] lg:text-xs text-gray-600">
                                Buchbar {startTime}–{endTime} Uhr
                              </p>
                              {eventPrice && (
                                <p className="text-[10px] lg:text-xs font-semibold text-[#005500]">{eventPrice} p. P.</p>
                              )}
                            </div>
                          </div>
                          
                          <div className="flex items-start gap-1 text-[9px] lg:text-[10px] text-amber-700 bg-amber-100 p-1.5 rounded mb-1.5">
                            <Info className="h-3 w-3 flex-shrink-0 mt-0.5" />
                            <span>{t.eventHint}</span>
                          </div>
                          
                          {/* Event Slots - 4 columns */}
                          <div className="grid grid-cols-4 gap-1">
                            {eventSlots.map((slotTime) => (
                              <Button
                                key={slotTime}
                                type="button"
                                variant={selectedEvent?.id === event.id && time === slotTime ? "default" : "outline"}
                                className={`h-7 text-[10px] lg:text-xs ${
                                  selectedEvent?.id === event.id && time === slotTime 
                                    ? "bg-[#005500] hover:bg-[#004400]" 
                                    : "border-amber-300 hover:bg-amber-100"
                                }`}
                                onClick={() => { handleEventSelect(event); setTime(slotTime); }}
                              >
                                {slotTime}
                              </Button>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                    
                    {/* Regular Slots - Grid */}
                    {regularSlots.length > 0 && !checking && (
                      <div className="space-y-1">
                        <Label className="text-[10px] lg:text-xs flex items-center gap-1 text-gray-700">
                          <Clock size={12} className="text-[#005500]" />
                          {hasEvents ? "Reguläre Zeiten" : t.time}
                        </Label>
                        <div className="grid grid-cols-4 lg:grid-cols-6 gap-1">
                          {regularSlots.map((slot) => (
                            <Button
                              key={slot.time}
                              type="button"
                              variant={!isEventBooking && time === slot.time ? "default" : "outline"}
                              className={`h-7 text-[10px] lg:text-xs ${!slot.available ? "opacity-50" : ""} ${
                                !isEventBooking && time === slot.time ? "bg-[#005500] hover:bg-[#004400]" : ""
                              }`}
                              onClick={() => slot.available && handleSlotSelect(slot.time)}
                              disabled={!slot.available}
                            >
                              {slot.time}
                            </Button>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <Button
                      className="w-full h-9 rounded-full font-semibold bg-[#005500] hover:bg-[#004400] text-white text-xs lg:text-sm"
                      onClick={() => setStep(2)}
                      disabled={!date || !time}
                    >
                      {isEventBooking ? t.bookEvent : t.next}
                    </Button>
                  </div>
                )}
                
                {/* Step 2: Guest Details */}
                {step === 2 && (
                  <form onSubmit={handleSubmit} className="space-y-2">
                    {/* Booking Summary */}
                    <div className="bg-gray-50 p-2 rounded-lg">
                      {isEventBooking && selectedEvent && (
                        <div className="mb-1.5 pb-1.5 border-b border-gray-200">
                          <div className="flex items-center gap-1 text-[#005500] text-[10px] font-semibold">
                            <Star className="h-3 w-3" />
                            <span>{t.youAreBooking}</span>
                          </div>
                          <p className="font-bold text-xs text-gray-900">{selectedEvent.title}</p>
                          {getEventPrice(selectedEvent) && (
                            <p className="text-[10px] text-[#005500]">{getEventPrice(selectedEvent)} p. P.</p>
                          )}
                          <div className="mt-1 text-[9px] text-amber-700 bg-amber-50 p-1 rounded flex items-start gap-1">
                            <Info className="h-2.5 w-2.5 flex-shrink-0 mt-0.5" />
                            <span>{t.eventHint}</span>
                          </div>
                        </div>
                      )}
                      <div className="flex items-center gap-2 text-[10px] lg:text-xs text-gray-600">
                        <span className="flex items-center gap-0.5">
                          <Calendar size={10} className="text-[#005500]" />
                          {date}
                        </span>
                        <span className="flex items-center gap-0.5">
                          <Clock size={10} className="text-[#005500]" />
                          {time}
                        </span>
                        <span className="flex items-center gap-0.5">
                          <Users size={10} className="text-[#005500]" />
                          {partySize}
                        </span>
                        <Button type="button" variant="ghost" size="sm" onClick={() => setStep(1)} className="text-[#005500] text-[10px] h-5 ml-auto px-1">
                          Ändern
                        </Button>
                      </div>
                    </div>
                    
                    {/* Form Fields - 2 columns */}
                    <div className="grid grid-cols-2 gap-2">
                      <div className="space-y-0.5">
                        <Label className="text-[10px] text-gray-700">{t.name} *</Label>
                        <Input value={guestName} onChange={(e) => setGuestName(e.target.value)} required className="h-8 text-xs border-gray-300" />
                      </div>
                      <div className="space-y-0.5">
                        <Label className="text-[10px] text-gray-700">{t.phone} *</Label>
                        <Input type="tel" value={guestPhone} onChange={(e) => setGuestPhone(e.target.value)} required className="h-8 text-xs border-gray-300" />
                      </div>
                      <div className="space-y-0.5">
                        <Label className="text-[10px] text-gray-700">{t.email} *</Label>
                        <Input type="email" value={guestEmail} onChange={(e) => setGuestEmail(e.target.value)} required className="h-8 text-xs border-gray-300" />
                      </div>
                      {!isEventBooking && (
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-gray-700">{t.occasion}</Label>
                          <Select value={occasion} onValueChange={setOccasion}>
                            <SelectTrigger className="h-8 text-xs border-gray-300">
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
                    </div>
                    
                    <div className="space-y-0.5">
                      <Label className="text-[10px] text-gray-700">{t.notes}</Label>
                      <Textarea
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Allergien, Kinderstühle, etc."
                        className="min-h-[50px] text-xs border-gray-300"
                      />
                    </div>
                    
                    {error && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-3 w-3" />
                        <AlertDescription className="text-[10px]">{error}</AlertDescription>
                      </Alert>
                    )}
                    
                    <div className="flex gap-2 pt-1">
                      <Button type="button" variant="outline" className="flex-1 h-9 rounded-full text-xs border-gray-300" onClick={() => setStep(1)}>
                        {t.back}
                      </Button>
                      <Button type="submit" className="flex-1 h-9 rounded-full font-semibold bg-[#005500] hover:bg-[#004400] text-xs" disabled={loading}>
                        {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : (isEventBooking ? t.bookEvent : t.book)}
                      </Button>
                    </div>
                  </form>
                )}
                
                {/* Step 3: Confirmation */}
                {step === 3 && success && (
                  <div className="text-center py-3">
                    <div className={`w-10 h-10 rounded-full mx-auto flex items-center justify-center mb-2 ${waitlisted ? "bg-yellow-100" : "bg-green-100"}`}>
                      {waitlisted ? <CalendarClock className="h-5 w-5 text-yellow-600" /> : <CheckCircle className="h-5 w-5 text-green-600" />}
                    </div>
                    
                    {!waitlisted && (
                      <p className="text-xs text-gray-700 mb-1.5 font-medium">
                        Vielen Dank für Ihre Reservierung – wir freuen uns auf Sie.
                      </p>
                    )}
                    
                    <h2 className="font-serif text-base mb-1 text-gray-900">
                      {waitlisted ? t.waitlistSuccess : t.success}
                    </h2>
                    <p className="text-[10px] text-gray-500 mb-2">{waitlisted ? t.waitlistText : t.successText}</p>
                    
                    {isEventBooking && selectedEvent && (
                      <div className="p-1.5 bg-amber-50 rounded border border-amber-200 mb-2">
                        <div className="flex items-center gap-1 justify-center text-amber-700 text-[10px]">
                          <Star className="h-3 w-3" />
                          <span className="font-semibold">{selectedEvent.title}</span>
                        </div>
                        <p className="text-[9px] text-amber-600">{t.eventHint}</p>
                      </div>
                    )}
                    
                    <div className="bg-gray-50 p-2 rounded-lg text-left">
                      <div className="grid grid-cols-2 gap-1 text-[10px]">
                        {guestName && (
                          <>
                            <span className="text-gray-500 flex items-center gap-0.5"><User size={10} />{t.name}:</span>
                            <span className="font-medium text-gray-900">{guestName}</span>
                          </>
                        )}
                        <span className="text-gray-500">{t.date}:</span>
                        <span className="font-medium text-gray-900">{date}</span>
                        <span className="text-gray-500">{t.time}:</span>
                        <span className="font-medium text-gray-900">{time} Uhr</span>
                        <span className="text-gray-500">{t.guests}:</span>
                        <span className="font-medium text-gray-900">{partySize}</span>
                        {!isEventBooking && getOccasionDisplayLabel(occasion) && (
                          <>
                            <span className="text-gray-500 flex items-center gap-0.5"><Heart size={10} />{t.occasion}:</span>
                            <span className="font-medium text-gray-900">{getOccasionDisplayLabel(occasion)}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
          
          {/* RIGHT: Gallery (Desktop) - FIXED: grid-rows mit 1fr für volle Höhe */}
          <div className="hidden lg:grid lg:flex-[0_0_36%] grid-rows-3 gap-3 h-full">
            {GALLERY_IMAGES.map((img, idx) => (
              <div key={idx} className="rounded-xl overflow-hidden shadow-lg h-full">
                <img src={img.src} alt={img.alt} className="w-full h-full object-cover" />
              </div>
            ))}
          </div>
          
          {/* Mobile Gallery Carousel */}
          <div className="lg:hidden flex-shrink-0 h-16 relative">
            <div className="flex h-full gap-1.5 overflow-hidden rounded-lg">
              {GALLERY_IMAGES.map((img, idx) => (
                <div 
                  key={idx} 
                  className={`flex-shrink-0 w-1/3 h-full rounded-lg overflow-hidden transition-opacity ${idx === galleryIndex ? 'ring-2 ring-white' : 'opacity-70'}`}
                >
                  <img src={img.src} alt={img.alt} className="w-full h-full object-cover" />
                </div>
              ))}
            </div>
            <button 
              onClick={prevGalleryImage}
              className="absolute left-0.5 top-1/2 -translate-y-1/2 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center text-white"
            >
              <ChevronLeft size={12} />
            </button>
            <button 
              onClick={nextGalleryImage}
              className="absolute right-0.5 top-1/2 -translate-y-1/2 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center text-white"
            >
              <ChevronRight size={12} />
            </button>
          </div>
        </div>
      </div>
      
      {/* Footer */}
      <div className="absolute bottom-1 left-0 right-0 text-center text-white/50 text-[9px] z-10">
        © {new Date().getFullYear()} Carlsburg
      </div>
    </div>
  );
};

export default BookingWidget;
