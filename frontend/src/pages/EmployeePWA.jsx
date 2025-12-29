/**
 * EmployeePWA.jsx - Mitarbeiter-PWA V1.1
 * Modul 30: MITARBEITER & DIENSTPLAN + ABWESENHEIT & PERSONALAKTE
 * 
 * V1.0 Funktionen:
 * - Home/Status mit Quick Actions
 * - Meine Schichten (read-only, nur PUBLISHED)
 * - Timeclock mit Pause strict
 * 
 * V1.1 Erweiterungen:
 * - Abwesenheit: Antrag stellen, Liste, Stornieren
 * - Unterlagen: Dokumentenliste, Bestätigung, Badge
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";

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
  CalendarOff,
  FileText,
  Download,
  Eye,
  Plus,
  Trash2,
  Check,
  X,
  Palmtree,
  Thermometer,
  Star,
  HelpCircle,
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

// V1.1: Absence Type Config
const ABSENCE_TYPE_CONFIG = {
  VACATION: { label: "Urlaub", icon: Palmtree, color: "bg-green-100 text-green-700" },
  SICK: { label: "Krank", icon: Thermometer, color: "bg-red-100 text-red-700" },
  SPECIAL: { label: "Sonderfrei", icon: Star, color: "bg-purple-100 text-purple-700" },
  OTHER: { label: "Sonstiges", icon: HelpCircle, color: "bg-gray-100 text-gray-700" },
};

// V1.1: Absence Status Config
const ABSENCE_STATUS_CONFIG = {
  REQUESTED: { label: "Beantragt", color: "bg-yellow-100 text-yellow-700 border-yellow-300" },
  APPROVED: { label: "Genehmigt", color: "bg-green-100 text-green-700 border-green-300" },
  REJECTED: { label: "Abgelehnt", color: "bg-red-100 text-red-700 border-red-300" },
  CANCELLED: { label: "Storniert", color: "bg-gray-100 text-gray-500 border-gray-300" },
};

// V1.1: Document Category Config
const DOC_CATEGORY_CONFIG = {
  CONTRACT: { label: "Arbeitsvertrag", color: "bg-blue-100 text-blue-700" },
  POLICY: { label: "Belehrung", color: "bg-yellow-100 text-yellow-700" },
  CERTIFICATE: { label: "Bescheinigung", color: "bg-green-100 text-green-700" },
  OTHER: { label: "Sonstiges", color: "bg-gray-100 text-gray-700" },
};

export default function EmployeePWA() {
  const { token, user } = useAuth();
  
  // State - V1.0
  const [status, setStatus] = useState(null);
  const [todaySession, setTodaySession] = useState(null);
  const [myShifts, setMyShifts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("home");

  // State - V1.1 Absences
  const [absences, setAbsences] = useState([]);
  const [absencesLoading, setAbsencesLoading] = useState(false);
  const [showAbsenceForm, setShowAbsenceForm] = useState(false);
  const [newAbsence, setNewAbsence] = useState({
    type: "VACATION",
    start_date: "",
    end_date: "",
    notes_employee: "",
  });
  const [cancelAbsenceId, setCancelAbsenceId] = useState(null);

  // State - V1.1 Documents
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [unacknowledgedCount, setUnacknowledgedCount] = useState(0);
  const [acknowledgeDocId, setAcknowledgeDocId] = useState(null);

  // API Headers - memoized to prevent unnecessary re-renders
  const getHeaders = useCallback(() => ({
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  }), [token]);

  // ============== API CALLS - V1.0 ==============

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/timeclock/status`, { headers: getHeaders() });
      if (!res.ok) {
        if (res.status === 401) {
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

  // ============== API CALLS - V1.1 ABSENCES ==============

  const fetchAbsences = useCallback(async () => {
    try {
      setAbsencesLoading(true);
      const res = await fetch(`${API_URL}/api/staff/absences/me`, { headers: getHeaders() });
      if (!res.ok) {
        if (res.status === 401) return;
        throw new Error("Fehler beim Laden der Abwesenheiten");
      }
      const data = await res.json();
      setAbsences(data.data || []);
    } catch (err) {
      console.error("fetchAbsences error:", err);
      toast.error("Fehler beim Laden der Abwesenheiten");
    } finally {
      setAbsencesLoading(false);
    }
  }, [getHeaders]);

  const createAbsence = async () => {
    if (!newAbsence.start_date || !newAbsence.end_date) {
      toast.error("Bitte Start- und Enddatum angeben");
      return;
    }

    try {
      setActionLoading(true);
      const res = await fetch(`${API_URL}/api/staff/absences`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify(newAbsence),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Erstellen des Antrags");
      }

      toast.success("Abwesenheitsantrag eingereicht");
      setShowAbsenceForm(false);
      setNewAbsence({ type: "VACATION", start_date: "", end_date: "", notes_employee: "" });
      fetchAbsences();
    } catch (err) {
      console.error("createAbsence error:", err);
      toast.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const cancelAbsence = async (absenceId) => {
    try {
      setActionLoading(true);
      const res = await fetch(`${API_URL}/api/staff/absences/${absenceId}/cancel`, {
        method: "POST",
        headers: getHeaders(),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Stornieren");
      }

      toast.success("Abwesenheit storniert");
      setCancelAbsenceId(null);
      fetchAbsences();
    } catch (err) {
      console.error("cancelAbsence error:", err);
      toast.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ============== API CALLS - V1.1 DOCUMENTS ==============

  const fetchDocuments = useCallback(async () => {
    try {
      setDocumentsLoading(true);
      const res = await fetch(`${API_URL}/api/staff/documents/me`, { headers: getHeaders() });
      if (!res.ok) {
        if (res.status === 401) return;
        throw new Error("Fehler beim Laden der Dokumente");
      }
      const data = await res.json();
      setDocuments(data.data || []);
      setUnacknowledgedCount(data.unacknowledged_count || 0);
    } catch (err) {
      console.error("fetchDocuments error:", err);
      toast.error("Fehler beim Laden der Dokumente");
    } finally {
      setDocumentsLoading(false);
    }
  }, [getHeaders]);

  const fetchUnacknowledgedCount = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/staff/documents/me/unacknowledged-count`, { 
        headers: getHeaders() 
      });
      if (res.ok) {
        const data = await res.json();
        setUnacknowledgedCount(data.count || 0);
      }
    } catch (err) {
      console.error("fetchUnacknowledgedCount error:", err);
    }
  }, [getHeaders]);

  const acknowledgeDocument = async (documentId) => {
    try {
      setActionLoading(true);
      const res = await fetch(`${API_URL}/api/staff/documents/${documentId}/acknowledge`, {
        method: "POST",
        headers: getHeaders(),
        body: JSON.stringify({}),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Fehler beim Bestätigen");
      }

      toast.success("Dokument als gelesen bestätigt");
      setAcknowledgeDocId(null);
      fetchDocuments();
    } catch (err) {
      console.error("acknowledgeDocument error:", err);
      toast.error(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ============== INITIAL LOAD ==============

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([
        fetchStatus(), 
        fetchTodaySession(), 
        fetchMyShifts(),
        fetchUnacknowledgedCount() // V1.1: Badge count
      ]);
      setLoading(false);
    };
    loadData();
  }, [fetchStatus, fetchTodaySession, fetchMyShifts, fetchUnacknowledgedCount]);

  // Auto-refresh status every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchStatus();
      fetchTodaySession();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus, fetchTodaySession]);

  // V1.1: Load absences when tab changes
  useEffect(() => {
    if (activeTab === "absence" && absences.length === 0) {
      fetchAbsences();
    }
    if (activeTab === "documents" && documents.length === 0) {
      fetchDocuments();
    }
  }, [activeTab, absences.length, documents.length, fetchAbsences, fetchDocuments]);

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
      
      const data = await res.json();
      
      if (!res.ok) {
        if (res.status === 409) {
          toast.error(data.detail || "Aktion nicht möglich");
          setError(data.detail);
        } else {
          throw new Error(data.detail || "Fehler bei der Aktion");
        }
        return;
      }
      
      const messages = {
        "clock-in": "Erfolgreich eingestempelt",
        "clock-out": "Erfolgreich ausgestempelt",
        "break-start": "Pause gestartet",
        "break-end": "Pause beendet",
      };
      
      toast.success(messages[action]);
      await Promise.all([fetchStatus(), fetchTodaySession()]);
      
    } catch (err) {
      console.error("Timeclock action error:", err);
      toast.error(err.message);
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  // ============== HELPERS ==============

  const formatTime = (seconds) => {
    if (!seconds || seconds < 0) return "0:00";
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hrs}:${mins.toString().padStart(2, "0")}`;
  };

  const formatTimeString = (isoString) => {
    if (!isoString) return "--:--";
    try {
      return format(parseISO(isoString), "HH:mm", { locale: de });
    } catch {
      return "--:--";
    }
  };

  const formatDateRange = (start, end) => {
    try {
      const startDate = parseISO(start);
      const endDate = parseISO(end);
      return `${format(startDate, "dd.MM.yyyy", { locale: de })} – ${format(endDate, "dd.MM.yyyy", { locale: de })}`;
    } catch {
      return `${start} – ${end}`;
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
              fetchUnacknowledgedCount();
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

      {/* Tabs - V1.1: 5 Tabs now */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
        <TabsList className="grid w-full grid-cols-5 mx-4 max-w-[calc(100%-2rem)] bg-white shadow-sm">
          <TabsTrigger value="home" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white text-xs px-1">
            <Clock className="h-4 w-4" />
          </TabsTrigger>
          <TabsTrigger value="shifts" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white text-xs px-1">
            <Calendar className="h-4 w-4" />
          </TabsTrigger>
          <TabsTrigger value="time" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white text-xs px-1">
            <Timer className="h-4 w-4" />
          </TabsTrigger>
          <TabsTrigger value="absence" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white text-xs px-1">
            <CalendarOff className="h-4 w-4" />
          </TabsTrigger>
          <TabsTrigger value="documents" className="data-[state=active]:bg-[#005500] data-[state=active]:text-white text-xs px-1 relative">
            <FileText className="h-4 w-4" />
            {unacknowledgedCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-4 w-4 flex items-center justify-center">
                {unacknowledgedCount}
              </span>
            )}
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
                  Eingestempelt um {formatTimeString(status.clock_in_at)}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Current Time Stats */}
              {status?.has_session && (
                <div className="grid grid-cols-3 gap-2 text-center text-sm mb-4">
                  <div className="bg-white/50 rounded p-2">
                    <div className="font-bold">{formatTime(status.total_work_seconds)}</div>
                    <div className="text-xs text-gray-600">Brutto</div>
                  </div>
                  <div className="bg-white/50 rounded p-2">
                    <div className="font-bold">{formatTime(status.total_break_seconds)}</div>
                    <div className="text-xs text-gray-600">Pause</div>
                  </div>
                  <div className="bg-white/50 rounded p-2">
                    <div className="font-bold">{formatTime(status.net_work_seconds)}</div>
                    <div className="text-xs text-gray-600">Netto</div>
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-2">
                {currentState === "OFF" && (
                  <Button
                    onClick={() => handleTimeclockAction("clock-in")}
                    disabled={actionLoading}
                    className="col-span-2 bg-[#005500] hover:bg-[#004400] text-white"
                  >
                    <LogIn className="h-4 w-4 mr-2" />
                    Einstempeln
                  </Button>
                )}

                {currentState === "WORKING" && (
                  <>
                    <Button
                      onClick={() => handleTimeclockAction("break-start")}
                      disabled={actionLoading}
                      variant="outline"
                      className="border-yellow-500 text-yellow-700 hover:bg-yellow-50"
                    >
                      <Coffee className="h-4 w-4 mr-2" />
                      Pause
                    </Button>
                    <Button
                      onClick={() => handleTimeclockAction("clock-out")}
                      disabled={actionLoading}
                      variant="outline"
                      className="border-red-500 text-red-700 hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4 mr-2" />
                      Ausstempeln
                    </Button>
                  </>
                )}

                {currentState === "BREAK" && (
                  <>
                    <Button
                      onClick={() => handleTimeclockAction("break-end")}
                      disabled={actionLoading}
                      className="col-span-2 bg-[#005500] hover:bg-[#004400] text-white"
                    >
                      <Play className="h-4 w-4 mr-2" />
                      Pause beenden
                    </Button>
                    <Alert className="col-span-2 border-yellow-400 bg-yellow-50">
                      <AlertCircle className="h-4 w-4 text-yellow-600" />
                      <AlertDescription className="text-yellow-800 text-sm">
                        Ausstempeln während der Pause nicht möglich!
                        Bitte erst Pause beenden.
                      </AlertDescription>
                    </Alert>
                  </>
                )}

                {currentState === "CLOSED" && (
                  <div className="col-span-2 text-center py-4 text-gray-600">
                    <CheckCircle className="h-8 w-8 mx-auto mb-2 text-blue-500" />
                    <p>Arbeitstag beendet</p>
                    <p className="text-sm text-gray-500">
                      Arbeitszeit: {formatTime(status?.net_work_seconds || 0)}
                    </p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Next Shift Preview */}
          {nextShift && !isToday(parseISO(nextShift.date_local || nextShift.shift_date)) && (
            <Card className="border-[#005500]/20">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-gray-500">
                  Nächste Schicht
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">
                      {format(parseISO(nextShift.date_local || nextShift.shift_date), "EEEE, d. MMMM", { locale: de })}
                    </div>
                    <div className="text-[#005500] font-bold">
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
        <TabsContent value="shifts" className="px-4 mt-4 space-y-3">
          <h2 className="text-lg font-semibold text-[#005500]">Meine Schichten</h2>
          
          {myShifts.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-gray-500">
                <Calendar className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>Keine Schichten in den nächsten 14 Tagen</p>
              </CardContent>
            </Card>
          ) : (
            myShifts.map((shift) => {
              const shiftDate = shift.date_local || shift.shift_date;
              const isShiftToday = isToday(parseISO(shiftDate));
              const isShiftTomorrow = isTomorrow(parseISO(shiftDate));
              
              return (
                <Card 
                  key={shift.id} 
                  className={`border-l-4 ${isShiftToday ? "border-l-green-500 bg-green-50/50" : "border-l-[#005500]"}`}
                >
                  <CardContent className="py-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-gray-700">
                          {isShiftToday && <Badge className="mr-2 bg-green-500">Heute</Badge>}
                          {isShiftTomorrow && <Badge className="mr-2 bg-blue-500">Morgen</Badge>}
                          {format(parseISO(shiftDate), "EEE, d. MMM", { locale: de })}
                        </div>
                        <div className="text-lg font-bold text-[#005500]">
                          {shift.start_time} – {shift.end_time}
                        </div>
                        <div className="text-sm text-gray-600">
                          {shift.role || "Service"}
                          {shift.station && ` • ${shift.station}`}
                        </div>
                      </div>
                      {shift.notes_staff && (
                        <div className="text-sm bg-yellow-50 p-2 rounded text-yellow-800 max-w-[150px]">
                          📝 {shift.notes_staff}
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
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

        {/* V1.1: ABSENCE TAB */}
        <TabsContent value="absence" className="px-4 mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[#005500]">Abwesenheiten</h2>
            <Button 
              onClick={() => setShowAbsenceForm(true)}
              size="sm"
              className="bg-[#005500] hover:bg-[#004400]"
            >
              <Plus className="h-4 w-4 mr-1" />
              Antrag
            </Button>
          </div>

          {absencesLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-[#005500]" />
            </div>
          ) : absences.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-gray-500">
                <CalendarOff className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>Keine Abwesenheiten eingetragen</p>
                <Button 
                  onClick={() => setShowAbsenceForm(true)}
                  variant="outline"
                  className="mt-4"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Abwesenheit beantragen
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {absences.map((absence) => {
                const typeConfig = ABSENCE_TYPE_CONFIG[absence.type] || ABSENCE_TYPE_CONFIG.OTHER;
                const statusConfig = ABSENCE_STATUS_CONFIG[absence.status] || ABSENCE_STATUS_CONFIG.REQUESTED;
                const TypeIcon = typeConfig.icon;
                const canCancel = absence.status === "REQUESTED";

                return (
                  <Card key={absence.id} className="border-l-4 border-l-[#005500]">
                    <CardContent className="py-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-full ${typeConfig.color}`}>
                            <TypeIcon className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="font-medium">{typeConfig.label}</div>
                            <div className="text-sm text-gray-600">
                              {formatDateRange(absence.start_date, absence.end_date)}
                            </div>
                            {absence.days_count && (
                              <div className="text-xs text-gray-500">
                                {absence.days_count} {absence.days_count === 1 ? "Tag" : "Tage"}
                              </div>
                            )}
                            {absence.notes_employee && (
                              <div className="text-xs text-gray-500 mt-1 italic">
                                "{absence.notes_employee}"
                              </div>
                            )}
                            {absence.notes_admin && (
                              <div className="text-xs text-red-600 mt-1">
                                Admin: {absence.notes_admin}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Badge className={statusConfig.color}>
                            {statusConfig.label}
                          </Badge>
                          {canCancel && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-red-600 hover:text-red-700 hover:bg-red-50 h-7 px-2"
                              onClick={() => setCancelAbsenceId(absence.id)}
                            >
                              <X className="h-3 w-3 mr-1" />
                              Stornieren
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>

        {/* V1.1: DOCUMENTS TAB */}
        <TabsContent value="documents" className="px-4 mt-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-[#005500]">Unterlagen</h2>
            {unacknowledgedCount > 0 && (
              <Badge className="bg-red-500">
                {unacknowledgedCount} offen
              </Badge>
            )}
          </div>

          {documentsLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-6 w-6 animate-spin text-[#005500]" />
            </div>
          ) : documents.length === 0 ? (
            <Card className="border-dashed">
              <CardContent className="py-8 text-center text-gray-500">
                <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>Keine Dokumente vorhanden</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {documents.map((doc) => {
                const catConfig = DOC_CATEGORY_CONFIG[doc.category] || DOC_CATEGORY_CONFIG.OTHER;
                const needsAck = doc.requires_acknowledgement && !doc.acknowledged;

                return (
                  <Card 
                    key={doc.id} 
                    className={`border-l-4 ${needsAck ? "border-l-red-500 bg-red-50/30" : "border-l-[#005500]"}`}
                  >
                    <CardContent className="py-3">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <div className={`p-2 rounded-full ${catConfig.color}`}>
                            <FileText className="h-4 w-4" />
                          </div>
                          <div>
                            <div className="font-medium">{doc.title}</div>
                            <div className="text-sm text-gray-600">
                              {catConfig.label} • Version {doc.version}
                            </div>
                            {doc.requires_acknowledgement && (
                              <div className="mt-1">
                                {doc.acknowledged ? (
                                  <span className="text-xs text-green-600 flex items-center gap-1">
                                    <Check className="h-3 w-3" />
                                    Bestätigt am {formatTimeString(doc.acknowledged_at)}
                                  </span>
                                ) : (
                                  <span className="text-xs text-red-600 flex items-center gap-1">
                                    <AlertCircle className="h-3 w-3" />
                                    Bestätigung erforderlich
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col items-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 px-2"
                            onClick={() => window.open(`${API_URL}${doc.file_url}`, '_blank')}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Öffnen
                          </Button>
                          {needsAck && (
                            <Button
                              size="sm"
                              className="bg-[#005500] hover:bg-[#004400] h-8"
                              onClick={() => setAcknowledgeDocId(doc.id)}
                            >
                              <Check className="h-3 w-3 mr-1" />
                              Bestätigen
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* V1.1: Absence Form Dialog */}
      <Dialog open={showAbsenceForm} onOpenChange={setShowAbsenceForm}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Abwesenheit beantragen</DialogTitle>
            <DialogDescription>
              Reichen Sie einen Antrag für Urlaub, Krankheit oder Sonderfrei ein.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Art der Abwesenheit</Label>
              <Select 
                value={newAbsence.type} 
                onValueChange={(v) => setNewAbsence({...newAbsence, type: v})}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="VACATION">🏖️ Urlaub</SelectItem>
                  <SelectItem value="SICK">🤒 Krank</SelectItem>
                  <SelectItem value="SPECIAL">⭐ Sonderfrei</SelectItem>
                  <SelectItem value="OTHER">📋 Sonstiges</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Von</Label>
                <Input 
                  type="date" 
                  value={newAbsence.start_date}
                  onChange={(e) => setNewAbsence({...newAbsence, start_date: e.target.value})}
                />
              </div>
              <div className="space-y-2">
                <Label>Bis</Label>
                <Input 
                  type="date" 
                  value={newAbsence.end_date}
                  onChange={(e) => setNewAbsence({...newAbsence, end_date: e.target.value})}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notiz (optional)</Label>
              <Textarea 
                placeholder="z.B. Grund oder besondere Hinweise..."
                value={newAbsence.notes_employee}
                onChange={(e) => setNewAbsence({...newAbsence, notes_employee: e.target.value})}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAbsenceForm(false)}>
              Abbrechen
            </Button>
            <Button 
              onClick={createAbsence}
              disabled={actionLoading || !newAbsence.start_date || !newAbsence.end_date}
              className="bg-[#005500] hover:bg-[#004400]"
            >
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
              Antrag einreichen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* V1.1: Cancel Absence Confirmation Dialog */}
      <Dialog open={!!cancelAbsenceId} onOpenChange={() => setCancelAbsenceId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Abwesenheit stornieren?</DialogTitle>
            <DialogDescription>
              Möchten Sie diesen Antrag wirklich stornieren? Diese Aktion kann nicht rückgängig gemacht werden.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCancelAbsenceId(null)}>
              Nein, behalten
            </Button>
            <Button 
              variant="destructive"
              onClick={() => cancelAbsence(cancelAbsenceId)}
              disabled={actionLoading}
            >
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
              Ja, stornieren
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* V1.1: Acknowledge Document Confirmation Dialog */}
      <Dialog open={!!acknowledgeDocId} onOpenChange={() => setAcknowledgeDocId(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Dokument bestätigen</DialogTitle>
            <DialogDescription>
              Hiermit bestätigen Sie, dass Sie das Dokument gelesen und verstanden haben.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAcknowledgeDocId(null)}>
              Abbrechen
            </Button>
            <Button 
              onClick={() => acknowledgeDocument(acknowledgeDocId)}
              disabled={actionLoading}
              className="bg-[#005500] hover:bg-[#004400]"
            >
              {actionLoading ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : null}
              <Check className="h-4 w-4 mr-2" />
              Gelesen & Verstanden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
