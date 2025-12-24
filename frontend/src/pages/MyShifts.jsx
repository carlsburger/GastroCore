import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, Clock, MapPin, ChevronLeft, ChevronRight } from "lucide-react";
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

export default function MyShifts() {
  const { token, user } = useAuth();
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);

  // Berechne Start/Ende der aktuellen Woche
  const getWeekRange = (offset = 0) => {
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
  };

  const fetchMyShifts = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const range = getWeekRange(weekOffset);
      const headers = { Authorization: `Bearer ${token}` };
      const response = await axios.get(
        `${BACKEND_URL}/api/staff/my-shifts?date_from=${range.from}&date_to=${range.to}`,
        { headers }
      );
      setShifts(response.data);
    } catch (error) {
      console.error("Fehler beim Laden der Schichten:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMyShifts();
  }, [token, weekOffset]);

  const range = getWeekRange(weekOffset);
  const weekNumber = Math.ceil(
    ((range.weekStart - new Date(range.weekStart.getFullYear(), 0, 1)) / 86400000 + 
     new Date(range.weekStart.getFullYear(), 0, 1).getDay() + 1) / 7
  );

  // Gruppiere Schichten nach Datum
  const shiftsByDate = shifts.reduce((acc, shift) => {
    if (!acc[shift.shift_date]) {
      acc[shift.shift_date] = [];
    }
    acc[shift.shift_date].push(shift);
    return acc;
  }, {});

  // Berechne Gesamtstunden
  const totalHours = shifts.reduce((sum, s) => sum + (s.hours || 0), 0);

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Meine Schichten</h1>
        <p className="text-gray-600">Übersicht deiner geplanten Arbeitszeiten</p>
      </div>

      {/* Wochen-Navigation */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setWeekOffset(weekOffset - 1)}
            >
              <ChevronLeft className="h-4 w-4 mr-1" />
              Vorwoche
            </Button>
            
            <div className="text-center">
              <div className="font-semibold text-lg">
                KW {weekNumber} / {range.weekStart.getFullYear()}
              </div>
              <div className="text-sm text-gray-500">
                {new Date(range.from).toLocaleDateString("de-DE")} - {new Date(range.to).toLocaleDateString("de-DE")}
              </div>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setWeekOffset(weekOffset + 1)}
            >
              Nächste Woche
              <ChevronRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Zusammenfassung */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-blue-600">{shifts.length}</div>
            <div className="text-sm text-gray-500">Schichten</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-3xl font-bold text-green-600">{totalHours.toFixed(1)}h</div>
            <div className="text-sm text-gray-500">Stunden</div>
          </CardContent>
        </Card>
      </div>
      
      {/* Platzhalter: Urlaub / Wunschfrei / Nicht verfügbar (UI vorbereitet, Logik später) */}
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

      {/* Schichten-Liste */}
      {loading ? (
        <Card>
          <CardContent className="p-8 text-center text-gray-500">
            Lade Schichten...
          </CardContent>
        </Card>
      ) : shifts.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center text-gray-500">
            <Calendar className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Keine Schichten in dieser Woche geplant</p>
          </CardContent>
        </Card>
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
                      {dayName}, {dateObj.toLocaleDateString("de-DE")}
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
                                {shift.start_time} - {shift.end_time}
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
