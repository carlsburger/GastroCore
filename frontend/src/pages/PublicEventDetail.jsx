import React, { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { toast } from "sonner";
import {
  Calendar,
  Clock,
  Users,
  Euro,
  MapPin,
  Loader2,
  ArrowRight,
  Ticket,
  UtensilsCrossed,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const PublicEventDetail = () => {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEvent();
  }, [eventId]);

  const fetchEvent = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/events/${eventId}`);
      setEvent(response.data);
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

  const isSoldOut = event.available_capacity <= 0;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-primary text-primary-foreground py-4">
        <div className="max-w-4xl mx-auto px-4">
          <Link to="/events-public" className="text-sm opacity-80 hover:opacity-100">
            ← Alle Veranstaltungen
          </Link>
        </div>
      </div>

      {/* Hero Image */}
      {event.image_url && (
        <div className="w-full h-64 md:h-96 overflow-hidden">
          <img
            src={event.image_url}
            alt={event.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="grid md:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="md:col-span-2 space-y-6">
            <div>
              <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
                {event.title}
              </h1>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="outline" className="flex items-center gap-1">
                  {event.booking_mode === "ticket_only" ? (
                    <>
                      <Ticket className="h-3 w-3" />
                      Ticket-Event
                    </>
                  ) : (
                    <>
                      <UtensilsCrossed className="h-3 w-3" />
                      Mit Vorbestellung
                    </>
                  )}
                </Badge>
              </div>
            </div>

            {event.description && (
              <div className="prose prose-green max-w-none">
                <div className="whitespace-pre-line text-muted-foreground">
                  {event.description}
                </div>
              </div>
            )}

            {/* Products Preview for preorder events */}
            {event.booking_mode === "reservation_with_preorder" && event.products && event.products.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center gap-2">
                    <UtensilsCrossed className="h-5 w-5" />
                    Auswahloptionen
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {event.products.map((product) => (
                      <div key={product.id} className="flex justify-between items-center py-2 border-b last:border-0">
                        <div>
                          <p className="font-medium">{product.name}</p>
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
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Sidebar - Booking Card */}
          <div>
            <Card className="sticky top-4">
              <CardContent className="p-6 space-y-4">
                {/* Date & Time */}
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Calendar className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-medium">{formatDate(event.start_datetime)}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="h-5 w-5 text-primary" />
                    <div>
                      <p className="font-medium">
                        {formatTime(event.start_datetime)} Uhr
                        {event.end_datetime && ` - ${formatTime(event.end_datetime)} Uhr`}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="border-t pt-4 space-y-3">
                  {/* Price */}
                  {event.ticket_price > 0 && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Preis pro Person</span>
                      <span className="text-2xl font-bold text-primary">
                        {event.ticket_price?.toFixed(2)} €
                      </span>
                    </div>
                  )}

                  {/* Availability */}
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Verfügbare Plätze</span>
                    <span className={`font-bold ${isSoldOut ? "text-red-600" : "text-green-600"}`}>
                      {isSoldOut ? "Ausgebucht" : `${event.available_capacity} Plätze`}
                    </span>
                  </div>
                </div>

                {/* Book Button */}
                <Button
                  className="w-full h-12 text-lg rounded-full"
                  disabled={isSoldOut}
                  onClick={() => navigate(`/events/${eventId}/book`)}
                >
                  {isSoldOut ? (
                    "Ausgebucht"
                  ) : (
                    <>
                      Jetzt buchen
                      <ArrowRight className="h-5 w-5 ml-2" />
                    </>
                  )}
                </Button>

                {isSoldOut && (
                  <p className="text-center text-sm text-muted-foreground">
                    Leider sind alle Plätze vergeben
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PublicEventDetail;
