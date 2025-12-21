import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { Calendar, Users, Euro, ChevronRight, Loader2 } from "lucide-react";
import api from "../../lib/api";

export default function CustomerEvents() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchEvents = async () => {
      try {
        const res = await api.get("/api/public/events?status=published");
        setEvents(res.data || []);
      } catch (error) {
        console.error("Error fetching events:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchEvents();
  }, []);

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
        Veranstaltungen
      </h1>

      {events.length === 0 ? (
        <div 
          className="rounded-xl p-8 text-center"
          style={{ backgroundColor: "#f3f6de" }}
        >
          <Calendar className="w-12 h-12 text-[#00280b]/30 mx-auto mb-4" />
          <p className="text-[#00280b]/70" style={{ fontFamily: "'Lato', sans-serif" }}>
            Aktuell keine Veranstaltungen geplant.
          </p>
          <p className="text-sm text-[#00280b]/50 mt-2" style={{ fontFamily: "'Lato', sans-serif" }}>
            Schauen Sie bald wieder vorbei!
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {events.map((event) => (
            <Link
              key={event.id}
              to={`/app/events/${event.id}`}
              className="block rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow"
              style={{ backgroundColor: "#f3f6de" }}
            >
              {event.image_url && (
                <div className="h-40 overflow-hidden">
                  <img
                    src={event.image_url}
                    alt={event.title}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h3 
                      className="font-bold text-[#00280b] text-lg mb-1"
                      style={{ fontFamily: "'Playfair Display', serif" }}
                    >
                      {event.title}
                    </h3>
                    
                    <div className="flex flex-wrap gap-3 text-sm text-[#00280b]/70 mb-2" style={{ fontFamily: "'Lato', sans-serif" }}>
                      <span className="flex items-center gap-1">
                        <Calendar className="w-4 h-4" />
                        {new Date(event.date).toLocaleDateString("de-DE", {
                          weekday: "short",
                          day: "numeric",
                          month: "short",
                        })}
                        {event.time && `, ${event.time}`}
                      </span>
                      {event.price_per_person && (
                        <span className="flex items-center gap-1">
                          <Euro className="w-4 h-4" />
                          {event.price_per_person}€ p.P.
                        </span>
                      )}
                    </div>
                    
                    {event.description && (
                      <p 
                        className="text-sm text-[#00280b]/60 line-clamp-2"
                        style={{ fontFamily: "'Lato', sans-serif" }}
                      >
                        {event.description}
                      </p>
                    )}
                    
                    {event.capacity_remaining !== undefined && event.capacity_remaining <= 10 && (
                      <p className="text-xs text-orange-600 mt-2 font-medium">
                        <Users className="w-3 h-3 inline mr-1" />
                        Nur noch {event.capacity_remaining} Plätze!
                      </p>
                    )}
                  </div>
                  <ChevronRight className="w-5 h-5 text-[#00280b]/40 flex-shrink-0 ml-2" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
