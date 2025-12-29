/**
 * EmployeePWA.jsx - Mitarbeiter-PWA V1
 * Modul 30: MITARBEITER & DIENSTPLAN
 * 
 * Funktionen:
 * - Home/Status mit Quick Actions
 * - Meine Schichten (read-only, nur PUBLISHED)
 * - Timeclock mit Pause strict
 * 
 * REGEL: Clock-out bei aktiver Pause = BLOCKIERT + Hinweis
 */

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import { format, parseISO, isToday, isTomorrow, isPast, addDays } from "date-fns";
import { de } from "date-fns/locale";

// UI Components
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "../components/ui/alert";

// Icons
import {
  Play,
  Square,
  Coffee,
  LogIn,
  LogOut,
  Clock,
  Calendar,
  User,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Timer,
  Pause,
  ChevronRight,
  MapPin,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

// Status Colors & Labels
const STATUS_CONFIG = {
  OFF: {
    color: "bg-gray-100 text-gray-800 border-gray-300",
    bgColor: "bg-gray-50",
    label: "Nicht eingestempelt",
    icon: LogOut,
  },
  WORKING: {
    color: "bg-green-100 text-green-800 border-green-300",
    bgColor: "bg-green-50",
    label: "Arbeitet",
    icon: Play,
  },
  BREAK: {
    color: "bg-yellow-100 text-yellow-800 border-yellow-300",
    bgColor: "bg-yellow-50",
    label: "In Pause",
    icon: Coffee,
  },
  CLOSED: {
    color: "bg-blue-100 text-blue-800 border-blue-300",
    bgColor: "bg-blue-50",
    label: "Feierabend",
    icon: CheckCircle,
  },
};

export default function EmployeePWA() {
  const { token, user } = useAuth();
  
  // State
  const [status, setStatus] = useState(null);
  const [todaySession, setTodaySession] = useState(null);
  const [myShifts, setMyShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("home");

  // API Headers - memoized to prevent unnecessary re-renders
  const getHeaders = useCallback(() => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  }), [token]);

  // ============== API CALLS ==============

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/timeclock/status`, { headers: getHeaders() });
      if (!res.ok) {
        if (res.status === 401) {
          // Don't show error for auth issues - user might need to re-login
          console.warn("Auth expired for status endpoint");
          return null;
        }
        throw new Error("Fehler beim Laden des Status");
      }
      const data = await res.json();
      setStatus(data);
      return data;
    } catch (err) {
      console.error("fetchStatus error:", err);
      // Don't set error for status - it's not critical
      return null;
      return null;
    }
  }, [token]);

  const fetchTodaySession = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/timeclock/today`, { headers: getHeaders() });
      if (!res.ok) {
        if (res.status === 401) return null;
        throw new Error("Fehler beim Laden der Tagesübersicht");
      }
      const data = await res.json();
      setTodaySession(data);
      return data;
    } catch (err) {
      console.error("fetchTodaySession error:", err);
      return null;
    }
  }, [getHeaders]);

  const fetchMyShifts = useCallback(async () => {
    try {
      // Get shifts for next 14 days
      const from = format(new Date(), "yyyy-MM-dd");
      const to = format(addDays(new Date(), 14), "yyyy-MM-dd");
      
      const res = await fetch(
        `${API_URL}/api/staff/shifts/v2/my?date_from=${from}&date_to=${to}`,
        { headers: getHeaders() }
      );
      
      if (!res.ok) {
        if (res.status === 401) return;
        throw new Error("Fehler beim Laden der Schichten");
      }
      
      const data = await res.json();
      setMyShifts(data.data || []);
    } catch (err) {
      console.error("fetchMyShifts error:", err);
    }
  }, [getHeaders]);

  // Initial Load
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchStatus(), fetchTodaySession(), fetchMyShifts()]);
      setLoading(false);
    };
    loadData();
  }, [fetchStatus, fetchTodaySession, fetchMyShifts]);

  // Auto-refresh status every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStatus();
      fetchTodaySession();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchTodaySession]);

  // ============== TIMECLOCK ACTIONS ==============

  const handleTimeclockAction = async (action) => {
    setActionLoading(true);
    setError(null);
    
    try {
      const endpoint = {
        "clock-in": "timeclock/clock-in",
        "clock-out": "timeclock/clock-out",
        "break-start": "timeclock/break-start",
        "break-end": "timeclock/break-end",
      }[action];
      
      if (!endpoint) throw new Error("Ungültige Aktion");
      
      const res = await fetch(`${API_URL}/api/${endpoint}`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({}),
      });
      
      let data;
      try {
        data = await res.json();
      } catch (e) {
        data = { detail: "Unbekannter Fehler" };
      }
      
      if (!res.ok) {
        // Handle specific errors
        const message = data.detail || "Aktion nicht möglich";
        setError(message);
        toast.error(message);
        return;
      }
      
      // Success
      const messages = {
        "clock-in": "Erfolgreich eingestempelt",
        "clock-out": "Erfolgreich ausgestempelt",
        "break-start": "Pause gestartet",
        "break-end": "Pause beendet",
      };
      
      toast.success(messages[action]);
      
      // Refresh status
      await fetchStatus();
      await fetchTodaySession();
      
    } catch (err) {
      setError(err.message);
      toast.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ============== HELPERS ==============

  const formatTime = (seconds) => {
    if (!seconds || seconds < 0) return "0h 0m";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const formatTimeString = (isoString) => {
    if (!isoString) return "--:--";
    try {
      return format(parseISO(isoString), "HH:mm", { locale: de });
    } catch {
      return "--:--";
    }
  };

  const getCurrentState = () => {
    if (!status?.has_session) return "OFF";
    return status.state || "OFF";
  };

  const getNextShift = () => {
    const now = new Date();
    const upcoming = myShifts
      .filter(s => {
        const shiftDate = s.date_local || s.shift_date;
        if (!shiftDate) return false;
        const shiftDateTime = parseISO(`${shiftDate}T${s.start_time || "00:00"}`);
        return shiftDateTime >= now;
      })
      .sort((a, b) => {
        const dateA = a.date_local || a.shift_date;
        const dateB = b.date_local || b.shift_date;
        return dateA.localeCompare(dateB);
      });
    
    return upcoming[0] || null;
  };

  const getTodayShift = () => {
    const today = format(new Date(), "yyyy-MM-dd");
    return myShifts.find(s => 
      (s.date_local === today) || (s.shift_date === today)
    );
  };

  // ============== RENDER ==============

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-[#FAFBE0] to-white">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-10 w-10 animate-spin text-[#005500]" />
          <span className="text-[#005500] font-medium">Lade Daten...</span>
        </div>
      </div>
    );
  }

  const currentState = getCurrentState();
  const stateConfig = STATUS_CONFIG[currentState] || STATUS_CONFIG.OFF;
  const StateIcon = stateConfig.icon;
  const todayShift = getTodayShift();
  const nextShift = getNextShift();

  return (
    <div className="min-h-screen bg-gradient-to-b from-[#FAFBE0] to-white pb-20">
      {/* Header */}
      <div className="bg-[#005500] text-white px-4 py-6 rounded-b-3xl shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-bold">Hallo, {user?.name || user?.email?.split("@")[0] || "Mitarbeiter"}!</h1>
            <p className="text-white/80 text-sm">
              {format(new Date(), "EEEE, d. MMMM yyyy", { locale: de })}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="text-white hover:bg-white/20"
            onClick={() => {
              fetchStatus();
              fetchTodaySession();
              fetchMyShifts();
            }}
          >
            <RefreshCw className="h-5 w-5" />
          </Button>
        </div>
        
        {/* Current Status Badge */}
        <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full ${stateConfig.color}`}>
          <StateIcon className="h-4 w-4" />
          <span className="font-medium">{stateConfig.label}</span>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="px-4 mt-4">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Fehler</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
        <TabsList className="grid w-full grid-cols-3 mx-4 max-w-[calc(100%-2rem)] bg-white shadow-sm">
          <TabsTrigger value="home" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white">
            <Clock className="h-4 w-4 mr-1" />
            Status
          </TabsTrigger>
          <TabsTrigger value="shifts" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white">
            <Calendar className="h-4 w-4 mr-1" />
            Schichten
          </TabsTrigger>
          <TabsTrigger value="time" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white">
            <Timer className="h-4 w-4 mr-1" />
            Zeiten
          </TabsTrigger>
        </TabsList>

        {/* HOME TAB */}
        <TabsContent value="home" className="px-4 mt-4 space-y-4">
          {/* Today's Shift Card */}
          {todayShift && (
            <Card className="border-[#005500]/20 bg-white">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">
                  Heutige Schicht
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-2xl font-bold text-[#005500]">
                      {todayShift.start_time} – {todayShift.end_time}
                    </div>
                    <div className="text-sm text-gray-600 flex items-center gap-2 mt-1">
                      <MapPin className="h-3 w-3" />
                      {todayShift.role || "Service"}
                      {todayShift.station && ` • ${todayShift.station}`}
                    </div>
                  </div>
                  <Badge variant="outline" className="bg-green-50 text-green-700 border-green-300">
                    Geplant
                  </Badge>
                </div>
                {todayShift.notes_staff && (
                  <div className="mt-3 p-2 bg-yellow-50 rounded text-sm text-yellow-800">
                    📝 {todayShift.notes_staff}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Quick Actions */}
          <Card className={`border-2 ${stateConfig.color} ${stateConfig.bgColor}`}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <StateIcon className="h-5 w-5" />
                {stateConfig.label}
              </CardTitle>
              {status?.clock_in_at && (
                <CardDescription>
                  Eingestempelt seit {formatTimeString(status.clock_in_at)}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Action Buttons based on state */}
              {currentState === "OFF" && (
                <Button
                  className="w-full h-14 text-lg bg-[#005500] hover:bg-[#004400]"
                  onClick={() => handleTimeclockAction("clock-in")}
                  disabled={actionLoading}
                >
                  {actionLoading ? (
                    <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                  ) : (
                    <LogIn className="h-5 w-5 mr-2" />
                  )}
                  Arbeitsstart
                </Button>
              )}

              {currentState === "WORKING" && (
                <>
                  <Button
                    className="w-full h-12 bg-yellow-500 hover:bg-yellow-600 text-white"
                    onClick={() => handleTimeclockAction("break-start")}
                    disabled={actionLoading}
                  >
                    {actionLoading ? (
                      <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                    ) : (
                      <Coffee className="h-5 w-5 mr-2" />
                    )}
                    Pause starten
                  </Button>
                  <Button
                    className="w-full h-12 bg-red-500 hover:bg-red-600 text-white"
                    onClick={() => handleTimeclockAction("clock-out")}
                    disabled={actionLoading}
                  >
                    {actionLoading ? (
                      <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                    ) : (
                      <LogOut className="h-5 w-5 mr-2" />
                    )}
                    Arbeitsende
                  </Button>
                </>
              )}

              {currentState === "BREAK" && (
                <>
                  {/* CRITICAL: Block clock-out during break */}
                  <Alert className="bg-yellow-100 border-yellow-400">
                    <Coffee className="h-4 w-4 text-yellow-700" />
                    <AlertTitle className="text-yellow-800">Pause aktiv</AlertTitle>
                    <AlertDescription className="text-yellow-700">
                      Bitte erst die Pause beenden, bevor du ausstempeln kannst.
                    </AlertDescription>
                  </Alert>
                  
                  <Button
                    className="w-full h-14 text-lg bg-green-600 hover:bg-green-700 text-white"
                    onClick={() => handleTimeclockAction("break-end")}
                    disabled={actionLoading}
                  >
                    {actionLoading ? (
                      <RefreshCw className="h-5 w-5 animate-spin mr-2" />
                    ) : (
                      <Play className="h-5 w-5 mr-2" />
                    )}
                    Pause beenden
                  </Button>
                  
                  {/* Disabled clock-out button with explanation */}
                  <Button
                    className="w-full h-12 bg-gray-300 text-gray-500 cursor-not-allowed"
                    disabled
                  >
                    <XCircle className="h-5 w-5 mr-2" />
                    Arbeitsende (Pause erst beenden!)
                  </Button>
                </>
              )}

              {currentState === "CLOSED" && (
                <div className="text-center py-4">
                  <CheckCircle className="h-12 w-12 text-green-600 mx-auto mb-2" />
                  <p className="text-lg font-medium text-green-700">
                    Feierabend! Schönen Tag noch.
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    Ausgestempelt um {formatTimeString(status?.clock_out_at)}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Next Shift (if not today) */}
          {!todayShift && nextShift && (
            <Card className="border-[#005500]/20 bg-white">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">
                  Nächste Schicht
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-lg font-bold text-[#005500]">
                      {format(parseISO(nextShift.date_local || nextShift.shift_date), "EEEE, d. MMM", { locale: de })}
                    </div>
                    <div className="text-xl font-medium">
                      {nextShift.start_time} – {nextShift.end_time}
                    </div>
                  </div>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* SHIFTS TAB */}
        <TabsContent value="shifts" className="px-4 mt-4">
          <Card className="border-[#005500]/20">
            <CardHeader>
              <CardTitle className="text-lg text-[#005500]">
                Meine Schichten
              </CardTitle>
              <CardDescription>
                Nächste 14 Tage
              </CardDescription>
            </CardHeader>
            <CardContent>
              {myShifts.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Calendar className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p>Keine geplanten Schichten</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {myShifts.map((shift) => {
                    const shiftDate = shift.date_local || shift.shift_date;
                    const date = parseISO(shiftDate);
                    const isShiftToday = isToday(date);
                    const isShiftTomorrow = isTomorrow(date);
                    const isShiftPast = isPast(date) && !isShiftToday;
                    
                    return (
                      <div
                        key={shift.id}
                        className={`p-4 rounded-lg border ${
                          isShiftToday
                            ? "bg-green-50 border-green-300"
                            : isShiftPast
                            ? "bg-gray-50 border-gray-200 opacity-60"
                            : "bg-white border-gray-200"
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className={`font-medium ${isShiftToday ? "text-green-700" : ""}`}>
                                {isShiftToday
                                  ? "Heute"
                                  : isShiftTomorrow
                                  ? "Morgen"
                                  : format(date, "EEE, d. MMM", { locale: de })}
                              </span>
                              {isShiftToday && (
                                <Badge className="bg-green-600 text-white text-xs">
                                  Heute
                                </Badge>
                              )}
                            </div>
                            <div className="text-xl font-bold mt-1">
                              {shift.start_time} – {shift.end_time}
                            </div>
                            <div className="text-sm text-gray-600 mt-1 flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {shift.role || "Service"}
                              {shift.station && (
                                <>
                                  <span className="mx-1">•</span>
                                  <MapPin className="h-3 w-3" />
                                  {shift.station}
                                </>
                              )}
                            </div>
                          </div>
                          <div className="text-right text-sm text-gray-500">
                            {shift.hours && `${shift.hours}h`}
                          </div>
                        </div>
                        {shift.notes_staff && (
                          <div className="mt-2 p-2 bg-yellow-50 rounded text-sm text-yellow-800">
                            📝 {shift.notes_staff}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* TIME TAB */}
        <TabsContent value="time" className="px-4 mt-4 space-y-4">
          {/* Today's Summary */}
          <Card className="border-[#005500]/20">
            <CardHeader>
              <CardTitle className="text-lg text-[#005500]">
                Heute
              </CardTitle>
              <CardDescription>
                {format(new Date(), "d. MMMM yyyy", { locale: de })}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {todaySession?.has_session ? (
                <div className="space-y-4">
                  {/* Time Stats */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-blue-50 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-blue-700">
                        {formatTime(todaySession.session?.total_work_seconds || status?.total_work_seconds || 0)}
                      </div>
                      <div className="text-xs text-blue-600">Brutto</div>
                    </div>
                    <div className="bg-yellow-50 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-yellow-700">
                        {formatTime(todaySession.session?.total_break_seconds || status?.total_break_seconds || 0)}
                      </div>
                      <div className="text-xs text-yellow-600">Pause</div>
                    </div>
                    <div className="bg-green-50 p-3 rounded-lg text-center">
                      <div className="text-2xl font-bold text-green-700">
                        {formatTime(todaySession.session?.net_work_seconds || status?.net_work_seconds || 0)}
                      </div>
                      <div className="text-xs text-green-600">Netto</div>
                    </div>
                  </div>

                  {/* Timeline */}
                  <div className="border-t pt-4">
                    <h4 className="font-medium text-gray-700 mb-3">Zeitverlauf</h4>
                    <div className="space-y-2">
                      {/* Clock In */}
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                          <LogIn className="h-5 w-5 text-green-600" />
                        </div>
                        <div>
                          <div className="font-medium">Eingestempelt</div>
                          <div className="text-sm text-gray-500">
                            {formatTimeString(todaySession.session?.clock_in_at)}
                          </div>
                        </div>
                      </div>

                      {/* Breaks */}
                      {todaySession.session?.breaks?.map((brk, idx) => (
                        <React.Fragment key={idx}>
                          <div className="flex items-center gap-3 ml-5 border-l-2 border-gray-200 pl-4">
                            <div className="w-8 h-8 rounded-full bg-yellow-100 flex items-center justify-center">
                              <Coffee className="h-4 w-4 text-yellow-600" />
                            </div>
                            <div>
                              <div className="text-sm font-medium">Pause {idx + 1}</div>
                              <div className="text-xs text-gray-500">
                                {formatTimeString(brk.start_at)}
                                {brk.end_at ? ` – ${formatTimeString(brk.end_at)}` : " (aktiv)"}
                                {brk.duration_seconds > 0 && ` (${Math.round(brk.duration_seconds / 60)}min)`}
                              </div>
                            </div>
                          </div>
                        </React.Fragment>
                      ))}

                      {/* Clock Out */}
                      {todaySession.session?.clock_out_at && (
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-full bg-red-100 flex items-center justify-center">
                            <LogOut className="h-5 w-5 text-red-600" />
                          </div>
                          <div>
                            <div className="font-medium">Ausgestempelt</div>
                            <div className="text-sm text-gray-500">
                              {formatTimeString(todaySession.session?.clock_out_at)}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Clock className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                  <p>Heute noch nicht eingestempelt</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Shift Link Info */}
          {status?.shift_linked && status?.shift_info && (
            <Card className="border-[#005500]/20 bg-blue-50">
              <CardContent className="py-4">
                <div className="flex items-center gap-3">
                  <CheckCircle className="h-5 w-5 text-blue-600" />
                  <div>
                    <div className="font-medium text-blue-800">Mit Schicht verknüpft</div>
                    <div className="text-sm text-blue-600">
                      {status.shift_info.start_time} – {status.shift_info.end_time}
                      {status.shift_info.role && ` • ${status.shift_info.role}`}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
