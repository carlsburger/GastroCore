import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Calendar,
  Clock,
  Users,
  Euro,
  Loader2,
  ArrowRight,
  Ticket,
  UtensilsCrossed,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const PublicEventsList = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEvents();
  }, []);

  const fetchEvents = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/public/events`);
      setEvents(response.data);
    } catch (err) {
      console.error("Error fetching events:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      return format(new Date(dateStr), "EEE, d. MMM yyyy", { locale: de });
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

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="bg-primary text-primary-foreground py-8">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <div className="w-16 h-16 rounded-full bg-primary-foreground/20 mx-auto flex items-center justify-center mb-4">
            <span className="text-primary-foreground font-serif text-3xl font-bold">G</span>
          </div>
          <h1 className="font-serif text-3xl md:text-4xl font-medium">
            Veranstaltungen
          </h1>
          <p className="mt-2 opacity-80">
            Entdecken Sie unsere Events und buchen Sie Ihren Platz
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {events.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                Aktuell sind keine Veranstaltungen verfügbar
              </p>
              <Link to="/book">
                <Button variant="outline" className="mt-4">
                  Reguläre Reservierung
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-6">
            {events.map((event) => {
              const isSoldOut = event.available_capacity <= 0;
              
              return (
                <Link key={event.id} to={`/events/${event.id}`}>
                  <Card className="overflow-hidden hover:shadow-lg transition-shadow cursor-pointer">
                    <div className="flex flex-col md:flex-row">
                      {/* Image */}
                      {event.image_url && (
                        <div className="md:w-1/3 h-48 md:h-auto">
                          <img
                            src={event.image_url}
                            alt={event.title}
                            className="w-full h-full object-cover"
                          />
                        </div>
                      )}
                      
                      {/* Content */}
                      <CardContent className={`flex-1 p-6 ${!event.image_url ? "md:col-span-2" : ""}`}>
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h2 className="font-serif text-xl md:text-2xl font-medium text-primary">
                              {event.title}
                            </h2>
                            <div className="flex items-center gap-2 mt-2">
                              <Badge variant="outline" className="flex items-center gap-1">
                                {event.booking_mode === "ticket_only" ? (
                                  <>
                                    <Ticket className="h-3 w-3" />
                                    Ticket
                                  </>
                                ) : (
                                  <>
                                    <UtensilsCrossed className="h-3 w-3" />
                                    Mit Vorbestellung
                                  </>
                                )}
                              </Badge>
                              {isSoldOut && (
                                <Badge className="bg-red-100 text-red-800">
                                  Ausgebucht
                                </Badge>
                              )}
                            </div>
                          </div>
                          {event.ticket_price > 0 && (
                            <div className="text-right">
                              <p className="text-2xl font-bold text-primary">
                                {event.ticket_price?.toFixed(2)} €
                              </p>
                              <p className="text-xs text-muted-foreground">pro Person</p>
                            </div>
                          )}
                        </div>

                        {event.description && (
                          <p className="text-muted-foreground mt-3 line-clamp-2">
                            {event.description}
                          </p>
                        )}

                        <div className="flex items-center gap-6 mt-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            {formatDate(event.start_datetime)}
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            {formatTime(event.start_datetime)} Uhr
                          </span>
                          <span className="flex items-center gap-1">
                            <Users className="h-4 w-4" />
                            {isSoldOut ? "Ausgebucht" : `${event.available_capacity} Plätze frei`}
                          </span>
                        </div>

                        <Button
                          className="mt-4 rounded-full"
                          variant={isSoldOut ? "outline" : "default"}
                          disabled={isSoldOut}
                        >
                          {isSoldOut ? "Ausgebucht" : (
                            <>
                              Details & Buchen
                              <ArrowRight className="h-4 w-4 ml-2" />
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </div>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}

        {/* Link to regular booking */}
        <div className="text-center mt-8 pt-8 border-t">
          <p className="text-muted-foreground mb-4">
            Oder reservieren Sie regulär à la carte:
          </p>
          <Link to="/book">
            <Button variant="outline" className="rounded-full">
              Tischreservierung
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default PublicEventsList;
