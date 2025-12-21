import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Badge } from "../components/ui/badge";
import { RadioGroup, RadioGroupItem } from "../components/ui/radio-group";
import { toast } from "sonner";
import {
  Calendar,
  Clock,
  Users,
  Euro,
  Loader2,
  ArrowLeft,
  ArrowRight,
  CheckCircle,
  Ticket,
  UtensilsCrossed,
  PartyPopper,
  Phone,
  Mail,
  User,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const PublicEventBooking = () => {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [step, setStep] = useState(1); // 1: Guest info, 2: Preorder selection, 3: Confirmation
  const [bookingResult, setBookingResult] = useState(null);

  const [formData, setFormData] = useState({
    guest_name: "",
    guest_phone: "",
    guest_email: "",
    party_size: 2,
    notes: "",
  });

  // Preorder selections: { productId: quantity } for each person
  const [selections, setSelections] = useState({});

  useEffect(() => {
    fetchEvent();
  }, [eventId]);

  const fetchEvent = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/events/${eventId}`);
      setEvent(response.data);
      
      // Initialize selections if preorder mode
      if (response.data.booking_mode === "reservation_with_preorder" && response.data.products) {
        const initialSelections = {};
        response.data.products.forEach(p => {
          initialSelections[p.id] = 0;
        });
        setSelections(initialSelections);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Event nicht gefunden");
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      return format(new Date(dateStr), "EEEE, d. MMMM yyyy", { locale: de });
    } catch {
      return dateStr;
    }
  };

  const formatTime = (dateStr) => {
    if (!dateStr) return "";
    try {
      return format(new Date(dateStr), "HH:mm", { locale: de });
    } catch {
      return dateStr;
    }
  };

  // Calculate total price
  const calculateTotal = () => {
    let total = (event?.ticket_price || 0) * formData.party_size;
    
    // Add price deltas from selections
    if (event?.products) {
      Object.entries(selections).forEach(([productId, qty]) => {
        const product = event.products.find(p => p.id === productId);
        if (product && qty > 0) {
          total += (product.price_delta || 0) * qty;
        }
      });
    }
    
    return total;
  };

  // Get total selections count
  const getTotalSelections = () => {
    return Object.values(selections).reduce((sum, qty) => sum + qty, 0);
  };

  // Handle single choice selection (for required products)
  const handleSingleChoice = (productId) => {
    // Reset all required products to 0
    const requiredProducts = event.products.filter(p => p.required && p.selection_type === "single_choice");
    const newSelections = { ...selections };
    requiredProducts.forEach(p => {
      newSelections[p.id] = 0;
    });
    // Set selected product to party_size
    newSelections[productId] = formData.party_size;
    setSelections(newSelections);
  };

  const handleSubmit = async () => {
    // Validate preorder if required
    if (event.booking_mode === "reservation_with_preorder") {
      const requiredProducts = event.products?.filter(p => p.required) || [];
      if (requiredProducts.length > 0) {
        const totalSelected = getTotalSelections();
        if (totalSelected !== formData.party_size) {
          toast.error(`Bitte wählen Sie für alle ${formData.party_size} Personen eine Option aus`);
          return;
        }
      }
    }

    setSubmitting(true);
    try {
      // Prepare items
      const items = [];
      Object.entries(selections).forEach(([productId, qty]) => {
        if (qty > 0) {
          items.push({
            event_product_id: productId,
            quantity: qty,
          });
        }
      });

      const bookingData = {
        event_id: eventId,
        guest_name: formData.guest_name,
        guest_phone: formData.guest_phone,
        guest_email: formData.guest_email || null,
        party_size: formData.party_size,
        notes: formData.notes || null,
        items: items.length > 0 ? items : null,
      };

      const response = await axios.post(`${BACKEND_URL}/api/public/events/${eventId}/book`, bookingData);
      setBookingResult(response.data);
      setStep(3);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler bei der Buchung");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <p className="text-red-600 mb-4">{error}</p>
            <Link to="/events-public">
              <Button variant="outline">Zurück zur Übersicht</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Step 3: Confirmation
  if (step === 3 && bookingResult) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="max-w-lg w-full">
          <CardContent className="pt-6">
            <div className="text-center mb-6">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <PartyPopper className="h-10 w-10 text-green-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-primary">
                Buchung erfolgreich!
              </h2>
              <p className="text-muted-foreground mt-2">
                Ihr Bestätigungscode: <span className="font-mono font-bold">{bookingResult.confirmation_code}</span>
              </p>
            </div>

            <div className="bg-muted rounded-lg p-4 space-y-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Event</span>
                <span className="font-medium">{bookingResult.event_title}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Datum</span>
                <span className="font-medium">{formatDate(bookingResult.event_date)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Personen</span>
                <span className="font-medium">{bookingResult.party_size}</span>
              </div>
              {bookingResult.total_price > 0 && (
                <div className="flex justify-between border-t pt-3">
                  <span className="font-medium">Gesamtpreis</span>
                  <span className="font-bold text-primary">{bookingResult.total_price?.toFixed(2)} €</span>
                </div>
              )}
            </div>

            {bookingResult.items && bookingResult.items.length > 0 && (
              <div className="mt-4 p-4 bg-amber-50 rounded-lg border border-amber-200">
                <p className="text-sm font-medium text-amber-800 mb-2">Ihre Auswahl:</p>
                <div className="space-y-1 text-sm">
                  {bookingResult.items.map((item, idx) => (
                    <div key={idx}>{item.quantity}x {item.product_name}</div>
                  ))}
                </div>
              </div>
            )}

            <p className="text-center text-sm text-muted-foreground mt-6">
              Eine Bestätigung wurde an Ihre E-Mail-Adresse gesendet.
            </p>

            <Button
              className="w-full mt-6 rounded-full"
              onClick={() => navigate("/events-public")}
            >
              Zurück zur Übersicht
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const hasPreorder = event.booking_mode === "reservation_with_preorder" && event.products && event.products.length > 0;
  const requiredProducts = hasPreorder ? event.products.filter(p => p.required && p.selection_type === "single_choice") : [];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-primary text-primary-foreground py-4">
        <div className="max-w-2xl mx-auto px-4 flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            className="text-primary-foreground hover:bg-primary-foreground/10"
            onClick={() => step > 1 ? setStep(step - 1) : navigate(`/events/${eventId}`)}
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            Zurück
          </Button>
          <div className="flex-1">
            <p className="text-sm opacity-80">Buchung für</p>
            <h1 className="font-medium">{event.title}</h1>
          </div>
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 py-8">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <div className={`flex items-center gap-2 ${step >= 1 ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 1 ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
              1
            </div>
            <span className="hidden sm:inline">Kontakt</span>
          </div>
          {hasPreorder && (
            <>
              <div className="w-8 h-px bg-border" />
              <div className={`flex items-center gap-2 ${step >= 2 ? "text-primary" : "text-muted-foreground"}`}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center ${step >= 2 ? "bg-primary text-primary-foreground" : "bg-muted"}`}>
                  2
                </div>
                <span className="hidden sm:inline">Auswahl</span>
              </div>
            </>
          )}
        </div>

        {/* Step 1: Guest Info */}
        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Ihre Kontaktdaten</CardTitle>
              <CardDescription>
                Bitte geben Sie Ihre Daten für die Buchung an
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name *</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={formData.guest_name}
                      onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                      required
                      className="pl-10"
                      placeholder="Ihr Name"
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>Personen *</Label>
                  <div className="relative">
                    <Users className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="number"
                      min="1"
                      max={event.available_capacity}
                      value={formData.party_size}
                      onChange={(e) => {
                        const val = parseInt(e.target.value) || 1;
                        setFormData({ ...formData, party_size: val });
                        // Reset selections when party size changes
                        if (hasPreorder) {
                          const newSelections = {};
                          event.products.forEach(p => { newSelections[p.id] = 0; });
                          setSelections(newSelections);
                        }
                      }}
                      required
                      className="pl-10"
                    />
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Telefon *</Label>
                  <div className="relative">
                    <Phone className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      value={formData.guest_phone}
                      onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })}
                      required
                      className="pl-10"
                      placeholder="+49..."
                    />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>E-Mail</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="email"
                      value={formData.guest_email}
                      onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })}
                      className="pl-10"
                      placeholder="ihre@email.de"
                    />
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <Label>Anmerkungen</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Besondere Wünsche, Allergien..."
                  rows={3}
                />
              </div>

              {/* Summary */}
              <div className="bg-muted rounded-lg p-4 mt-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-primary" />
                    <span>{formatDate(event.start_datetime)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Clock className="h-4 w-4 text-primary" />
                    <span>{formatTime(event.start_datetime)} Uhr</span>
                  </div>
                </div>
                {event.ticket_price > 0 && (
                  <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <span className="font-medium">Preis ({formData.party_size} Pers.)</span>
                    <span className="text-xl font-bold text-primary">
                      {(event.ticket_price * formData.party_size).toFixed(2)} €
                    </span>
                  </div>
                )}
              </div>

              <Button
                className="w-full h-12 text-lg rounded-full mt-4"
                onClick={() => {
                  if (!formData.guest_name || !formData.guest_phone) {
                    toast.error("Bitte füllen Sie alle Pflichtfelder aus");
                    return;
                  }
                  if (hasPreorder) {
                    setStep(2);
                  } else {
                    handleSubmit();
                  }
                }}
                disabled={submitting}
              >
                {submitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : hasPreorder ? (
                  <>
                    Weiter zur Auswahl
                    <ArrowRight className="h-5 w-5 ml-2" />
                  </>
                ) : (
                  <>
                    Jetzt buchen
                    <CheckCircle className="h-5 w-5 ml-2" />
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step 2: Preorder Selection */}
        {step === 2 && hasPreorder && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UtensilsCrossed className="h-5 w-5" />
                Ihre Auswahl
              </CardTitle>
              <CardDescription>
                Bitte wählen Sie für alle {formData.party_size} Personen eine Option
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Required Single Choice Products */}
              {requiredProducts.length > 0 && (
                <div className="space-y-4">
                  <p className="text-sm font-medium text-muted-foreground">
                    Wählen Sie eine der folgenden Optionen:
                  </p>
                  <RadioGroup
                    value={Object.entries(selections).find(([id, qty]) => qty > 0)?.[0] || ""}
                    onValueChange={handleSingleChoice}
                  >
                    {requiredProducts.map((product) => (
                      <div
                        key={product.id}
                        className={`flex items-center space-x-4 p-4 rounded-lg border cursor-pointer transition-colors ${
                          selections[product.id] > 0 ? "border-primary bg-primary/5" : "hover:bg-muted"
                        }`}
                        onClick={() => handleSingleChoice(product.id)}
                      >
                        <RadioGroupItem value={product.id} id={product.id} />
                        <div className="flex-1">
                          <label htmlFor={product.id} className="font-medium cursor-pointer">
                            {product.name}
                          </label>
                          {product.description && (
                            <p className="text-sm text-muted-foreground">{product.description}</p>
                          )}
                        </div>
                        {product.price_delta !== 0 && (
                          <span className={product.price_delta > 0 ? "text-green-600" : "text-red-600"}>
                            {product.price_delta > 0 ? "+" : ""}{product.price_delta?.toFixed(2)} €
                          </span>
                        )}
                      </div>
                    ))}
                  </RadioGroup>
                </div>
              )}

              {/* Selection Summary */}
              <div className="bg-muted rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Ausgewählt</span>
                  <span className={`font-medium ${getTotalSelections() === formData.party_size ? "text-green-600" : "text-orange-600"}`}>
                    {getTotalSelections()} / {formData.party_size} Personen
                  </span>
                </div>
                {getTotalSelections() !== formData.party_size && (
                  <p className="text-sm text-orange-600">
                    Bitte wählen Sie für alle Personen eine Option aus
                  </p>
                )}
                {event.ticket_price > 0 && (
                  <div className="flex items-center justify-between mt-3 pt-3 border-t">
                    <span className="font-medium">Gesamtpreis</span>
                    <span className="text-xl font-bold text-primary">
                      {calculateTotal().toFixed(2)} €
                    </span>
                  </div>
                )}
              </div>

              <Button
                className="w-full h-12 text-lg rounded-full"
                onClick={handleSubmit}
                disabled={submitting || getTotalSelections() !== formData.party_size}
              >
                {submitting ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    Jetzt buchen
                    <CheckCircle className="h-5 w-5 ml-2" />
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default PublicEventBooking;
