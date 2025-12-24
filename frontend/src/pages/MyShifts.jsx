import React, { useState, useEffect, useRef, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Clock, MapPin, ChevronLeft, ChevronRight, RefreshCw, AlertCircle, CalendarX, UserX } from "lucide-react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const DAY_NAMES = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"];

const ROLE_LABELS = {
  frueh: "Früh",
  spaet: "Spät",
  teildienst: "Teildienst",
  event: "Event"
};

// Maximale Ladezeit in Millisekunden
const LOADING_TIMEOUT_MS = 5000;

export default function MyShifts() {
  const { token, user } = useAuth();
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);
  const [error, setError] = useState(null);
  const [timedOut, setTimedOut] = useState(false);
  const timeoutRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Berechne Start/Ende der aktuellen Woche (ISO-Woche, Montag = Start)
  const getWeekRange = useCallback((offset = 0) => {
    const now = new Date();
    const dayOfWeek = now.getDay();
    const monday = new Date(now);
    monday.setDate(now.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1) + offset * 7);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    return {
      from: monday.toISOString().split('T')[0],
      to: sunday.toISOString().split('T')[0],
      weekStart: monday
    };
  }, []);

  // ISO-Kalenderwoche berechnen
  const getISOWeekNumber = useCallback((date) => {
    const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
    const dayNum = d.getUTCDay() || 7;
    d.setUTCDate(d.getUTCDate() + 4 - dayNum);
    const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
    return Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  }, []);

  const fetchMyShifts = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setError("no_token");
      return;
    }
    
    // Vorherigen Request abbrechen falls noch aktiv
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    
    // Vorheriges Timeout clearen
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setLoading(true);
    setError(null);
    setTimedOut(false);
    
    // Timeout nach 5 Sekunden
    timeoutRef.current = setTimeout(() => {
      setTimedOut(true);
      setLoading(false);
      setError("timeout");
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }, LOADING_TIMEOUT_MS);

    abortControllerRef.current = new AbortController();

    try {
      const range = getWeekRange(weekOffset);
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(
        `${BACKEND_URL}/api/staff/my-shifts?date_from=${range.from}&date_to=${range.to}`,
        { 
          headers,
          signal: abortControllerRef.current.signal
        }
      );
      
      // Timeout clearen bei Erfolg
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      setShifts(response.data || []);
      setError(null);
    } catch (err) {
      // Timeout clearen
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      // Abgebrochene Requests ignorieren
      if (axios.isCancel(err) || err.name === 'AbortError') {
        return;
      }
      
      // Fehlertyp bestimmen
      if (err.response?.status === 404) {
        setError("no_profile");
      } else if (err.response?.status === 401 || err.response?.status === 403) {
        setError("unauthorized");
      } else if (err.response?.data?.detail?.includes("nicht verknüpft") || 
                 err.response?.data?.detail?.includes("not linked")) {
        setError("no_profile");
      } else if (!navigator.onLine) {
        setError("offline");
      } else {
        setError("generic");
      }
    } finally {
      setLoading(false);
    }
  }, [token, weekOffset, getWeekRange]);

  useEffect(() => {
    fetchMyShifts();
    
    // Cleanup bei Unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchMyShifts]);

  const range = getWeekRange(weekOffset);
  const weekNumber = getISOWeekNumber(range.weekStart);

  // Gruppiere Schichten nach Datum
  const shiftsByDate = shifts.reduce((acc, shift) => {
    const dateKey = shift.shift_date || shift.date;
    if (!dateKey) return acc;
    if (!acc[dateKey]) {
      acc[dateKey] = [];
    }
    acc[dateKey].push(shift);
    return acc;
  }, {});

  // Berechne Gesamtstunden
  const totalHours = shifts.reduce((sum, s) => sum + (s.hours || 0), 0);

  // Retry-Handler
  const handleRetry = () => {
    fetchMyShifts();
  };

  // Error-State Komponenten
  const renderErrorState = () => {
    switch (error) {
      case "no_profile":
        return (
          <Card className="border-amber-300 bg-amber-50">
            <CardContent className="p-8 text-center">
              <UserX className="h-12 w-12 mx-auto mb-4 text-amber-500" />
              <p className="text-amber-800 font-medium text-lg">Kein Mitarbeiterprofil verknüpft</p>
              <p className="text-amber-600 text-sm mt-2 max-w-md mx-auto">
                Dein Benutzerkonto ist noch nicht mit einem Mitarbeiterprofil verbunden. 
                Bitte informiere deinen Admin oder die Schichtleitung.
              </p>
            </CardContent>
          </Card>
        );
      
      case "timeout":
        return (
          <Card className="border-orange-300 bg-orange-50">
            <CardContent className="p-8 text-center">
              <Clock className="h-12 w-12 mx-auto mb-4 text-orange-500" />
              <p className="text-orange-800 font-medium text-lg">Laden dauert zu lange</p>
              <p className="text-orange-600 text-sm mt-2">
                Die Verbindung zum Server ist langsam. Bitte versuche es erneut.
              </p>
              <Button 
                variant="outline" 
                className="mt-4 border-orange-400 text-orange-700 hover:bg-orange-100"
                onClick={handleRetry}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Erneut versuchen
              </Button>
            </CardContent>
          </Card>
        );
      
      case "offline":
        return (
          <Card className="border-gray-300 bg-gray-50">
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-500" />
              <p className="text-gray-800 font-medium text-lg">Keine Internetverbindung</p>
              <p className="text-gray-600 text-sm mt-2">
                Bitte prüfe deine Verbindung und versuche es erneut.
              </p>
              <Button 
                variant="outline" 
                className="mt-4"
                onClick={handleRetry}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Erneut versuchen
              </Button>
            </CardContent>
          </Card>
        );
      
      case "unauthorized":
        return (
          <Card className="border-red-300 bg-red-50">
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-800 font-medium text-lg">Zugriff verweigert</p>
              <p className="text-red-600 text-sm mt-2">
                Du hast keine Berechtigung, diese Seite zu sehen. Bitte melde dich erneut an.
              </p>
            </CardContent>
          </Card>
        );
      
      case "no_token":
        return (
          <Card className="border-gray-300 bg-gray-50">
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-gray-500" />
              <p className="text-gray-800 font-medium text-lg">Nicht angemeldet</p>
              <p className="text-gray-600 text-sm mt-2">
                Bitte melde dich an, um deine Schichten zu sehen.
              </p>
            </CardContent>
          </Card>
        );
      
      default: // "generic"
        return (
          <Card className="border-red-300 bg-red-50">
            <CardContent className="p-8 text-center">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-red-500" />
              <p className="text-red-800 font-medium text-lg">Schichten konnten nicht geladen werden</p>
              <p className="text-red-600 text-sm mt-2">
                Ein Fehler ist aufgetreten. Bitte versuche es später erneut.
              </p>
              <Button 
                variant="outline" 
                className="mt-4 border-red-400 text-red-700 hover:bg-red-100"
                onClick={handleRetry}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Erneut versuchen
              </Button>
            </CardContent>
          </Card>
        );
    }
  };

  // Empty State Komponente
  const renderEmptyState = () => (
    <Card className="border-dashed border-2 border-gray-200">
      <CardContent className="p-8 text-center">
        <CalendarX className="h-14 w-14 mx-auto mb-4 text-gray-300" />
        <p className="text-gray-700 font-medium text-lg">Keine Schichten geplant</p>
        <p className="text-gray-500 text-sm mt-2">
          Für diese Woche sind keine Schichten eingetragen.
        </p>
        {weekOffset === 0 && (
          <Button 
            variant="ghost" 
            className="mt-4 text-gray-500"
            onClick={() => setWeekOffset(1)}
          >
            Nächste Woche anzeigen
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Header mit Hilfetext */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Meine Schichten</h1>
        <p className="text-gray-600 mt-1">
          Hier siehst du deine geplanten Schichten und deine aktuellen Stunden.
        </p>
      </div>

      {/* Wochen-Navigation */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setWeekOffset(weekOffset - 1)}
              disabled={loading}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Vorwoche
            </Button>
            
            <div className="text-center">
              <div className="font-semibold text-lg">
                KW {weekNumber} / {range.weekStart.getFullYear()}
              </div>
              <div className="text-sm text-gray-500">
                {new Date(range.from).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })} – {new Date(range.to).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" })}
              </div>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setWeekOffset(weekOffset + 1)}
              disabled={loading}
            >
              Nächste Woche
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Zusammenfassung - nur anzeigen wenn keine Fehler */}
      {!error && (
        <div className="grid grid-cols-2 gap-4 mb-6">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold text-blue-600">
                {loading ? "–" : shifts.length}
              </div>
              <div className="text-sm text-gray-500">Schichten</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-3xl font-bold text-green-600">
                {loading ? "–" : `${totalHours.toFixed(1)}h`}
              </div>
              <div className="text-sm text-gray-500">Stunden</div>
            </CardContent>
          </Card>
        </div>
      )}
      
      {/* Aktionen (Urlaub, Wunschfrei) - nur anzeigen wenn kein Fehler */}
      {!error && !loading && (
        <Card className="mb-6 border-dashed border-2 border-gray-200">
          <CardContent className="p-4">
            <div className="flex flex-wrap gap-2 justify-center">
              <Button variant="outline" size="sm" disabled className="opacity-60">
                🏖️ Urlaub beantragen
              </Button>
              <Button variant="outline" size="sm" disabled className="opacity-60">
                ❌ Wunschfrei eintragen
              </Button>
              <Button variant="outline" size="sm" disabled className="opacity-60">
                🚫 Nicht verfügbar
              </Button>
            </div>
            <p className="text-xs text-gray-400 text-center mt-2">(Funktionen in Planung)</p>
          </CardContent>
        </Card>
      )}

      {/* Hauptinhalt: Loading / Error / Empty / Schichten */}
      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-gray-500">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
              <span>Lade Schichten...</span>
            </div>
          </CardContent>
        </Card>
      ) : error ? (
        renderErrorState()
      ) : shifts.length === 0 ? (
        renderEmptyState()
      ) : (
        <div className="space-y-4">
          {Object.entries(shiftsByDate)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([date, dayShifts]) => {
              const dateObj = new Date(date);
              const dayName = DAY_NAMES[dateObj.getDay()];
              const isToday = date === new Date().toISOString().split('T')[0];
              
              return (
                <Card key={date} className={isToday ? "ring-2 ring-blue-500" : ""}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Calendar className="h-5 w-5 text-gray-400" />
                      {dayName}, {dateObj.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })}
                      {isToday && (
                        <Badge className="bg-blue-500">Heute</Badge>
                      )}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {dayShifts.map((shift) => (
                        <div
                          key={shift.id}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="flex items-center gap-4">
                            <div
                              className="w-3 h-12 rounded-full"
                              style={{ backgroundColor: shift.work_area_color || "#3B82F6" }}
                            />
                            <div>
                              <div className="font-medium flex items-center gap-2">
                                <Clock className="h-4 w-4 text-gray-400" />
                                {shift.start_time} – {shift.end_time}
                                <span className="text-gray-400">({shift.hours}h)</span>
                              </div>
                              <div className="text-sm text-gray-500 flex items-center gap-2">
                                <MapPin className="h-4 w-4" />
                                {shift.work_area_name}
                                {shift.role && (
                                  <Badge variant="outline" className="ml-2">
                                    {ROLE_LABELS[shift.role] || shift.role}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
        </div>
      )}
    </div>
  );
}
