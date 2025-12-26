import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import { toast } from "sonner";
import {
  Calendar,
  Plus,
  RefreshCw,
  Loader2,
  ChevronLeft,
  ChevronRight,
  Clock,
  User,
  Download,
  Send,
  Edit,
  Trash2,
  Check,
  FileText,
  Copy,
  AlertTriangle,
  CalendarX,
  Filter,
  Wand2,
  AlertCircle,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const DAYS = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];
const FULL_DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];

const STATUS_CONFIG = {
  entwurf: { label: "Entwurf", color: "bg-yellow-100 text-yellow-700" },
  veroeffentlicht: { label: "Veröffentlicht", color: "bg-green-100 text-green-700" },
  archiviert: { label: "Archiviert", color: "bg-gray-100 text-gray-700" },
};

const SHIFT_ROLES = {
  service: { label: "Service", color: "#10b981" },
  schichtleiter: { label: "Schichtleiter", color: "#f59e0b" },
  kueche: { label: "Küche", color: "#f97316" },
  kuechenhilfe: { label: "Küchenhilfe", color: "#fb923c" },
  reinigung: { label: "Reinigung", color: "#94a3b8" },
  bar: { label: "Bar", color: "#8b5cf6" },
  aushilfe: { label: "Aushilfe", color: "#6b7280" },
};

// Department Filter Options - erweitert mit Reinigung
const DEPARTMENT_FILTER = {
  all: { label: "Alle", color: "bg-gray-100 text-gray-700", roles: [] },
  service: { label: "Service", color: "bg-green-100 text-green-700", roles: ["service", "schichtleiter", "bar", "aushilfe"] },
  kitchen: { label: "Küche", color: "bg-orange-100 text-orange-700", roles: ["kueche", "kuechenhilfe"] },
  reinigung: { label: "Reinigung", color: "bg-slate-100 text-slate-700", roles: ["reinigung"] },
};

// Eismacher NIE im Dienstplan anzeigen
const EXCLUDED_ROLES = ["eismacher"];

// Helper: Namen kürzen auf "V. Nachname" - mit Fallbacks
const formatShortName = (fullName) => {
  if (!fullName || fullName.trim() === "") return "N.N.";
  const parts = fullName.trim().split(" ").filter(p => p.length > 0);
  if (parts.length === 0) return "N.N.";
  if (parts.length === 1) return parts[0]; // Nur Vorname oder Nachname
  const firstName = parts[0];
  const lastName = parts.slice(1).join(" ");
  if (!firstName) return lastName;
  if (!lastName) return firstName;
  return `${firstName.charAt(0)}. ${lastName}`;
};

// ISO 8601 Week Number (Mo-So, korrekt für Jahreswechsel)
const getISOWeekData = (date = new Date()) => {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7; // Sonntag = 7
  d.setUTCDate(d.getUTCDate() + 4 - dayNum); // Donnerstag dieser Woche
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  const weekNum = Math.ceil((((d - yearStart) / 86400000) + 1) / 7);
  return {
    week: weekNum,
    year: d.getUTCFullYear() // Jahr der Kalenderwoche (kann bei Jahreswechsel abweichen!)
  };
};

// Mini-Test für Console (Ziel 1)
if (typeof window !== 'undefined' && window.console) {
  const today = new Date();
  const isoData = getISOWeekData(today);
  console.log(`[Dienstplan] Heute: ${today.toLocaleDateString('de-DE')} → KW ${isoData.week} / ${isoData.year}`);
}

export const Schedule = () => {
  // URL-Parameter für Deep-Links (?week=52&year=2025)
  const urlParams = new URLSearchParams(window.location.search);
  const urlWeek = urlParams.get('week');
  const urlYear = urlParams.get('year');
  
  // Initialisierung: URL-Params oder aktuelle ISO-Woche
  const initData = getISOWeekData();
  const [year, setYear] = useState(urlYear ? parseInt(urlYear) : initData.year);
  const [week, setWeek] = useState(urlWeek ? parseInt(urlWeek) : initData.week);
  const [schedule, setSchedule] = useState(null);
  const [staffMembers, setStaffMembers] = useState([]);
  const [workAreas, setWorkAreas] = useState([]);
  const [hoursOverview, setHoursOverview] = useState(null);
  const [closedDays, setClosedDays] = useState({}); // Map of date -> closure info
  const [loading, setLoading] = useState(true);
  const [showShiftDialog, setShowShiftDialog] = useState(false);
  const [editingShift, setEditingShift] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  // NEW: Department Filter (Sprint: Dienstplan Service live-tauglich)
  const [departmentFilter, setDepartmentFilter] = useState("all");
  
  // NEW: View Mode (Woche vs Monat)
  const [viewMode, setViewMode] = useState("week"); // "week" oder "month"
  
  // NEW: Event Warnings (Sprint: Dienstplan Service live-tauglich)
  const [eventWarnings, setEventWarnings] = useState([]);
  
  // NEW: Apply Templates Dialog
  const [showTemplatesDialog, setShowTemplatesDialog] = useState(false);
  const [templateSettings, setTemplateSettings] = useState({
    departments: ["service"],
    season: null, // null = auto-detect
  });
  const [applyingTemplates, setApplyingTemplates] = useState(false);

  const [shiftData, setShiftData] = useState({
    staff_member_id: "",
    work_area_id: "",
    start_time: "10:00",
    end_time: "18:00",
    role: "service",
    notes: "",
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, [year, week]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // Get staff and work areas first
      const [staffRes, areasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/staff/members`, { headers, params: { status: "aktiv" } }),
        axios.get(`${BACKEND_URL}/api/staff/work-areas`, { headers }),
      ]);
      setStaffMembers(staffRes.data);
      setWorkAreas(areasRes.data);

      // Try to get existing schedule
      const schedulesRes = await axios.get(`${BACKEND_URL}/api/staff/schedules`, {
        headers,
        params: { year },
      });
      
      const existingSchedule = schedulesRes.data.find(
        (s) => {
          const yearMatch = s.year === year || s.year === parseInt(year);
          const weekMatch = s.week === week || s.week === parseInt(week) || s.week_number === week;
          const notArchived = !s.archived;
          return yearMatch && weekMatch && notArchived;
        }
      );

      if (existingSchedule) {
        // Load full schedule with shifts
        const scheduleRes = await axios.get(
          `${BACKEND_URL}/api/staff/schedules/${existingSchedule.id}`,
          { headers }
        );
        setSchedule(scheduleRes.data);
        
        // Load effective hours for the week to show closures
        try {
          const effectiveRes = await axios.get(
            `${BACKEND_URL}/api/opening-hours/effective`,
            { 
              headers, 
              params: { 
                from: scheduleRes.data.start_date || scheduleRes.data.week_start, 
                to: scheduleRes.data.end_date || scheduleRes.data.week_end 
              } 
            }
          );
          // Create a map of closed days
          const closedMap = {};
          effectiveRes.data.days?.forEach((day) => {
            if (day.is_closed_full_day) {
              closedMap[day.date] = {
                reason: day.closure_reason || "Geschlossen",
                closures: day.closures || []
              };
            }
          });
          setClosedDays(closedMap);
        } catch (effErr) {
          console.log("Could not load effective hours:", effErr);
          setClosedDays({});
        }
        
        // NEW: Fetch Event Warnings
        try {
          const warningsRes = await axios.get(
            `${BACKEND_URL}/api/staff/schedules/${existingSchedule.id}/event-warnings`,
            { headers }
          );
          setEventWarnings(warningsRes.data.warnings || []);
        } catch (warnErr) {
          console.log("Could not load event warnings:", warnErr);
          setEventWarnings([]);
        }
      } else {
        setSchedule(null);
        setClosedDays({});
        setEventWarnings([]);
      }

      // Get hours overview
      const hoursRes = await axios.get(`${BACKEND_URL}/api/staff/hours-overview`, {
        headers,
        params: { year, week },
      });
      setHoursOverview(hoursRes.data);
    } catch (err) {
      console.error("Error fetching data:", err);
      toast.error("Fehler beim Laden des Dienstplans");
    } finally {
      setLoading(false);
    }
  };
  
  // NEW: Apply Templates to Schedule
  const handleApplyTemplates = async () => {
    if (!schedule) return;
    setApplyingTemplates(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/staff/schedules/${schedule.id}/apply-templates`,
        {
          schedule_id: schedule.id,
          departments: templateSettings.departments,
          season: templateSettings.season,
        },
        { headers }
      );
      toast.success(`${response.data.message} (Saison: ${response.data.season})`);
      setShowTemplatesDialog(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Anwenden der Vorlagen");
    } finally {
      setApplyingTemplates(false);
    }
  };
  
  // Filter shifts by department - erweitert
  const getFilteredShifts = (shifts) => {
    // Eismacher NIE anzeigen
    const filtered = shifts.filter(s => !EXCLUDED_ROLES.includes(s.role));
    
    if (departmentFilter === "all") return filtered;
    
    const filterConfig = DEPARTMENT_FILTER[departmentFilter];
    if (!filterConfig || !filterConfig.roles.length) return filtered;
    
    return filtered.filter(shift => {
      const role = shift.role || "";
      return filterConfig.roles.includes(role);
    });
  };
  
  // Get event warning for a specific date
  const getEventWarningForDate = (date) => {
    return eventWarnings.find(w => w.date === date);
  };
  
  // Helper: Check if date is weekend (Saturday or Sunday)
  const isWeekend = (dateStr) => {
    const date = new Date(dateStr);
    const day = date.getDay();
    return day === 0 || day === 6; // 0 = Sunday, 6 = Saturday
  };

  const handleCreateSchedule = async () => {
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/staff/schedules`,
        { year, week },
        { headers }
      );
      toast.success(`Dienstplan für KW ${week}/${year} erstellt`);
      
      // WICHTIG: Direkt den erstellten Schedule aus der Response verwenden
      // und nicht auf fetchData warten (Race Condition vermeiden)
      const newScheduleId = res.data.id;
      if (newScheduleId) {
        // Lade den vollständigen Schedule mit Shifts
        const scheduleRes = await axios.get(
          `${BACKEND_URL}/api/staff/schedules/${newScheduleId}`,
          { headers }
        );
        setSchedule(scheduleRes.data);
        setClosedDays({});
        setEventWarnings([]);
        
        // Lade auch Hours Overview
        try {
          const hoursRes = await axios.get(`${BACKEND_URL}/api/staff/hours-overview`, {
            headers,
            params: { year, week },
          });
          setHoursOverview(hoursRes.data);
        } catch (hoursErr) {
          console.log("Could not load hours overview:", hoursErr);
        }
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail || "Fehler beim Erstellen";
      // Falls Schedule bereits existiert, trotzdem Daten laden
      if (err.response?.data?.error_code === "VALIDATION_ERROR" && errorDetail.includes("existiert bereits")) {
        toast.info("Dienstplan existiert bereits - wird geladen");
        fetchData();
      } else {
        toast.error(errorDetail);
      }
    }
  };

  const handlePublish = async () => {
    if (!schedule) return;
    try {
      await axios.post(`${BACKEND_URL}/api/staff/schedules/${schedule.id}/publish`, {}, { headers });
      toast.success("Dienstplan veröffentlicht");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Veröffentlichen");
    }
  };

  const handleExportPDF = async () => {
    if (!schedule) return;
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/staff/schedules/${schedule.id}/export-pdf`,
        { headers, responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      // Dateiendung basierend auf Content-Type (HTML oder PDF)
      const contentType = response.headers?.["content-type"] || "";
      const ext = contentType.includes("pdf") ? "pdf" : "html";
      link.setAttribute("download", `dienstplan_kw${week}_${year}.${ext}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Kommunikation: HTML als Druckansicht
      if (ext === "html") {
        toast.success("Druckansicht (HTML) heruntergeladen – PDF folgt später");
      } else {
        toast.success("PDF heruntergeladen");
      }
    } catch (err) {
      toast.error("Fehler beim Export");
    }
  };

  // CSV Export (Sprint: Dienstplan Live-Ready)
  const handleExportCSV = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/staff/export/shifts/csv?year=${year}&week=${week}`,
        { headers, responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `schichten_kw${week}_${year}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("CSV heruntergeladen");
    } catch (err) {
      toast.error("Fehler beim CSV-Export");
    }
  };

  // Woche kopieren (Sprint: Dienstplan Live-Ready)
  const handleCopyWeek = async () => {
    if (!schedule) return;
    if (!window.confirm(`Dienstplan in die nächste Woche (KW ${week >= 52 ? 1 : week + 1}) kopieren?`)) {
      return;
    }
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/staff/schedules/${schedule.id}/copy`,
        {},
        { headers }
      );
      toast.success(`${response.data.message} (${response.data.shifts_copied} Schichten)`);
      // Zur neuen Woche wechseln
      if (week >= 52) {
        setYear(year + 1);
        setWeek(1);
      } else {
        setWeek(week + 1);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Kopieren");
    }
  };

  const openShiftDialog = (date, shift = null) => {
    setSelectedDate(date);
    if (shift) {
      setEditingShift(shift);
      setShiftData({
        staff_member_id: shift.staff_member_id || "",
        work_area_id: shift.work_area_id || "",
        start_time: shift.start_time || "10:00",
        end_time: shift.end_time || "18:00",
        role: shift.role || "service",
        notes: shift.notes || "",
      });
    } else {
      setEditingShift(null);
      setShiftData({
        staff_member_id: "",
        work_area_id: workAreas[0]?.id || "",
        start_time: "10:00",
        end_time: "18:00",
        role: "service",
        notes: "",
      });
    }
    setShowShiftDialog(true);
  };

  const handleSaveShift = async () => {
    if (!shiftData.staff_member_id || !shiftData.work_area_id) {
      toast.error("Bitte alle Pflichtfelder ausfüllen");
      return;
    }

    setSubmitting(true);
    try {
      if (editingShift) {
        await axios.patch(
          `${BACKEND_URL}/api/staff/shifts/${editingShift.id}`,
          shiftData,
          { headers }
        );
        toast.success("Schicht aktualisiert");
      } else {
        await axios.post(
          `${BACKEND_URL}/api/staff/shifts`,
          {
            ...shiftData,
            schedule_id: schedule.id,
            shift_date: selectedDate,
          },
          { headers }
        );
        toast.success("Schicht angelegt");
      }
      setShowShiftDialog(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteShift = async (shiftId) => {
    if (!window.confirm("Schicht wirklich löschen?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/staff/shifts/${shiftId}`, { headers });
      toast.success("Schicht gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const navigateWeek = (direction) => {
    let newWeek = week + direction;
    let newYear = year;
    
    if (newWeek < 1) {
      newWeek = 52;
      newYear--;
    } else if (newWeek > 52) {
      newWeek = 1;
      newYear++;
    }
    
    setWeek(newWeek);
    setYear(newYear);
  };

  const getWeekDates = () => {
    if (!schedule) return [];
    // Support both start_date and week_start field names
    const startStr = schedule.start_date || schedule.week_start;
    if (!startStr) return [];
    const start = new Date(startStr);
    return Array.from({ length: 7 }, (_, i) => {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      return date.toISOString().split("T")[0];
    });
  };

  const getShiftsForDate = (date) => {
    if (!schedule?.shifts) return [];
    // Support both 'date' and 'shift_date' field names for backwards compatibility
    const allShifts = schedule.shifts.filter((s) => (s.date || s.shift_date) === date);
    return getFilteredShifts(allShifts);
  };

  // KPI-Counter für Service/Küche/Gesamt
  const getShiftCounts = () => {
    if (!schedule?.shifts) return { service: 0, kitchen: 0, total: 0 };
    
    const allShifts = schedule.shifts.filter(s => !EXCLUDED_ROLES.includes(s.role));
    
    const serviceRoles = DEPARTMENT_FILTER.service.roles;
    const kitchenRoles = DEPARTMENT_FILTER.kitchen.roles;
    
    const serviceCount = allShifts.filter(s => serviceRoles.includes(s.role)).length;
    const kitchenCount = allShifts.filter(s => kitchenRoles.includes(s.role)).length;
    
    return {
      service: serviceCount,
      kitchen: kitchenCount,
      total: allShifts.length
    };
  };

  const shiftCounts = getShiftCounts();
  const weekDates = getWeekDates();
  const statusConfig = STATUS_CONFIG[schedule?.status] || STATUS_CONFIG.entwurf;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl font-medium text-primary">Dienstplan</h1>
            <p className="text-muted-foreground">KW {week} / {year} • {viewMode === "week" ? "Wochenübersicht" : "Monatsübersicht"}</p>
          </div>
          <div className="flex gap-2 flex-wrap">
            {/* View Mode Toggle (Woche/Monat) */}
            <div className="flex bg-gray-100 rounded-full p-1">
              <Button
                variant={viewMode === "week" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("week")}
                className={`rounded-full px-3 ${viewMode === "week" ? "bg-primary text-white" : ""}`}
              >
                Woche
              </Button>
              <Button
                variant={viewMode === "month" ? "default" : "ghost"}
                size="sm"
                onClick={() => setViewMode("month")}
                className={`rounded-full px-3 ${viewMode === "month" ? "bg-primary text-white" : ""}`}
              >
                Monat
              </Button>
            </div>
            
            {/* Department Filter Toggle */}
            <div className="flex bg-gray-100 rounded-full p-1">
              {Object.entries(DEPARTMENT_FILTER).map(([key, config]) => (
                <Button
                  key={key}
                  variant={departmentFilter === key ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setDepartmentFilter(key)}
                  className={`rounded-full px-3 ${departmentFilter === key ? "bg-primary text-white" : ""}`}
                >
                  {config.label}
                </Button>
              ))}
            </div>
            
            <Button variant="outline" onClick={fetchData} className="rounded-full">
              <RefreshCw className="h-4 w-4" />
            </Button>
            {schedule && (
              <>
                {/* Apply Templates Button */}
                {schedule.status === "entwurf" && (
                  <Button 
                    variant="outline" 
                    onClick={() => setShowTemplatesDialog(true)} 
                    className="rounded-full border-purple-400 text-purple-600 hover:bg-purple-50"
                  >
                    <Wand2 className="h-4 w-4 mr-2" />
                    Vorlagen
                  </Button>
                )}
                <Button variant="outline" onClick={handleExportCSV} className="rounded-full">
                  <FileText className="h-4 w-4 mr-2" />
                  CSV
                </Button>
                <Button variant="outline" onClick={handleExportPDF} className="rounded-full">
                  <Download className="h-4 w-4 mr-2" />
                  PDF
                </Button>
                <Button variant="outline" onClick={handleCopyWeek} className="rounded-full">
                  <Copy className="h-4 w-4 mr-2" />
                  Kopieren
                </Button>
                {schedule.status === "entwurf" && (
                  <Button onClick={handlePublish} className="rounded-full">
                    <Send className="h-4 w-4 mr-2" />
                    Veröffentlichen
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        {/* Week Navigation */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <Button variant="ghost" onClick={() => navigateWeek(-1)} className="rounded-full">
                <ChevronLeft className="h-5 w-5" />
              </Button>
              
              <div className="text-center">
                <h2 className="text-2xl font-bold">KW {week} / {year}</h2>
                {schedule && (
                  <p className="text-muted-foreground">
                    {new Date(schedule.start_date || schedule.week_start).toLocaleDateString("de-DE")} - {new Date(schedule.end_date || schedule.week_end).toLocaleDateString("de-DE")}
                  </p>
                )}
                {schedule && (
                  <Badge className={`${statusConfig.color} mt-2`}>{statusConfig.label}</Badge>
                )}
              </div>
              
              <Button variant="ghost" onClick={() => navigateWeek(1)} className="rounded-full">
                <ChevronRight className="h-5 w-5" />
              </Button>
            </div>
          </CardContent>
        </Card>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
          </div>
        ) : !schedule ? (
          <Card>
            <CardContent className="py-16 text-center">
              <Calendar className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg text-muted-foreground mb-4">
                Kein Dienstplan für KW {week}/{year} vorhanden
              </p>
              <Button onClick={handleCreateSchedule} className="rounded-full">
                <Plus className="h-4 w-4 mr-2" />
                Dienstplan erstellen
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Event Warnings Banner */}
            {eventWarnings.length > 0 && (
              <Card className="border-amber-400 bg-amber-50">
                <CardContent className="py-3 px-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-medium text-amber-800">Event-Hinweise für diese Woche</p>
                      <ul className="mt-1 space-y-1">
                        {eventWarnings.map((w, idx) => (
                          <li key={idx} className="text-sm text-amber-700">
                            {w.message}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Week Grid (nur bei viewMode === "week") */}
            {viewMode === "week" && (
            <div className="grid grid-cols-7 gap-2">
              {weekDates.map((date, idx) => {
                const shifts = getShiftsForDate(date);
                const dayDate = new Date(date);
                const isToday = new Date().toISOString().split("T")[0] === date;
                const closedInfo = closedDays[date];
                const isWknd = isWeekend(date);  // Sa/So hervorheben
                const isClosed = !!closedInfo;
                const eventWarning = getEventWarningForDate(date);

                return (
                  <Card key={date} className={`
                    ${isToday ? "ring-2 ring-primary" : ""} 
                    ${isClosed ? "bg-red-50" : ""} 
                    ${eventWarning ? "border-amber-400" : ""}
                    ${isWknd && !isClosed ? "bg-amber-50/50" : ""}
                  `}>
                    <CardHeader className="pb-1 px-2 pt-2">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className={`font-bold text-base ${isWknd ? "text-amber-700" : ""}`}>{DAYS[idx]}</p>
                          <p className="text-xs text-muted-foreground">
                            {dayDate.getDate()}.{dayDate.getMonth() + 1}.
                          </p>
                        </div>
                        {schedule.status !== "archiviert" && !isClosed && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openShiftDialog(date)}
                            className="h-6 w-6 p-0"
                          >
                            <Plus className="h-3 w-3" />
                          </Button>
                        )}
                      </div>
                      {/* Closure Banner */}
                      {isClosed && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="mt-1 flex items-center gap-1 px-1.5 py-0.5 bg-red-100 text-red-800 rounded text-[10px]">
                                <CalendarX className="h-3 w-3" />
                                <span className="font-medium truncate">{closedInfo.reason}</span>
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p>Restaurant geschlossen: {closedInfo.reason}</p>
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </CardHeader>
                    <CardContent className="px-2 pb-2 space-y-0.5">
                      {isClosed ? (
                        <p className="text-xs text-red-600 text-center py-2">Geschlossen</p>
                      ) : shifts.length === 0 ? (
                        <p className="text-xs text-muted-foreground text-center py-2">-</p>
                      ) : (
                        shifts.map((shift) => {
                          const area = workAreas.find((a) => a.id === shift.work_area_id);
                          
                          // Mitarbeiter-Name mit strenger Fallback-Reihenfolge:
                          // 1. full_name, 2. display_name, 3. first_name + last_name, 4. email
                          // KEIN Fallback auf Rollen/Work-Areas wie "Service"
                          let displayName = null;
                          const sm = shift.staff_member;
                          if (sm && typeof sm === 'object' && Object.keys(sm).length > 0) {
                            displayName = sm.full_name 
                              || sm.display_name 
                              || (sm.first_name && sm.last_name ? `${sm.first_name} ${sm.last_name}`.trim() : null)
                              || (sm.first_name || sm.last_name || null)
                              || sm.email;
                          }
                          
                          // Kein Mitarbeiter zugewiesen = "Nicht zugewiesen"
                          const staffName = displayName 
                            ? formatShortName(displayName) 
                            : "Nicht zugewiesen";
                          
                          // Ist die Schicht unbesetzt?
                          const isUnassigned = !displayName;
                          
                          // Zeit kompakt: "10:00–15:00"
                          const timeRange = `${shift.start_time?.slice(0,5) || "?"}–${shift.end_time?.slice(0,5) || "?"}`;
                          
                          return (
                            <div
                              key={shift.id}
                              className={`px-1.5 py-0.5 rounded text-[11px] cursor-pointer hover:opacity-80 transition-opacity flex items-center justify-between gap-1 ${isUnassigned ? 'border-dashed' : ''}`}
                              style={{ 
                                backgroundColor: area?.color + "12", 
                                borderLeft: `2px solid ${area?.color}`,
                                borderStyle: isUnassigned ? 'dashed' : 'solid'
                              }}
                              onClick={() => schedule.status !== "archiviert" && openShiftDialog(date, shift)}
                            >
                              <span className={`font-medium truncate ${isUnassigned ? 'text-muted-foreground italic' : ''}`}>
                                {staffName}
                              </span>
                              <span className="text-[10px] text-muted-foreground/70 whitespace-nowrap">
                                {timeRange}
                              </span>
                            </div>
                          );
                        })
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
            )}

            {/* Month View - A4 Landscape optimiert */}
            {viewMode === "month" && (
              <Card className="print:shadow-none">
                <CardHeader className="pb-2 print:pb-0">
                  <CardTitle className="text-lg print:text-base">
                    Monatsplan {year} - KW {week} (A4 Druck)
                  </CardTitle>
                </CardHeader>
                <CardContent className="overflow-x-auto">
                  <div className="min-w-[800px]">
                    <table className="w-full border-collapse text-xs">
                      <thead>
                        <tr>
                          <th className="border border-gray-300 p-1 bg-gray-100 text-left w-32 print:w-24">Mitarbeiter</th>
                          {weekDates.map((date, idx) => {
                            const isWknd = isWeekend(date);
                            const dayDate = new Date(date);
                            return (
                              <th 
                                key={date} 
                                className={`border border-gray-300 p-1 text-center ${isWknd ? "bg-amber-100 text-amber-800" : "bg-gray-100"}`}
                              >
                                <div className="font-bold">{DAYS[idx]}</div>
                                <div className="text-[10px] font-normal">{dayDate.getDate()}.{dayDate.getMonth() + 1}.</div>
                              </th>
                            );
                          })}
                          <th className="border border-gray-300 p-1 bg-gray-200 text-center w-16">Σ</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(() => {
                          // Defensiv: Prüfe ob Schedule und Shifts existieren
                          const allShifts = schedule?.shifts || [];
                          if (allShifts.length === 0) {
                            return (
                              <tr>
                                <td colSpan={weekDates.length + 2} className="text-center py-4 text-muted-foreground">
                                  Keine Schichten vorhanden
                                </td>
                              </tr>
                            );
                          }
                          
                          // Gruppiere Schichten nach Mitarbeiter
                          const staffShifts = {};
                          allShifts.forEach(shift => {
                            const staffId = shift.staff_member_id || `unassigned-${shift.id}`;
                            if (!staffShifts[staffId]) {
                              // Mitarbeiter-Name mit Fallback-Reihenfolge
                              let displayName = null;
                              const sm = shift.staff_member;
                              if (sm && typeof sm === 'object' && Object.keys(sm).length > 0) {
                                displayName = sm.full_name 
                                  || sm.display_name 
                                  || (sm.first_name && sm.last_name ? `${sm.first_name} ${sm.last_name}`.trim() : null)
                                  || (sm.first_name || sm.last_name || null)
                                  || sm.email;
                              }
                              staffShifts[staffId] = {
                                name: displayName || "Nicht zugewiesen",
                                isUnassigned: !displayName,
                                shifts: {}
                              };
                            }
                            // Support both 'date' and 'shift_date' field names
                            const shiftDate = shift.date || shift.shift_date;
                            if (!staffShifts[staffId].shifts[shiftDate]) {
                              staffShifts[staffId].shifts[shiftDate] = [];
                            }
                            staffShifts[staffId].shifts[shiftDate].push(shift);
                          });
                          
                          return Object.entries(staffShifts).map(([staffId, data]) => {
                            let totalHours = 0;
                            return (
                              <tr key={staffId} className="hover:bg-gray-50">
                                <td className={`border border-gray-300 p-1 font-medium text-xs ${data.isUnassigned ? 'italic text-muted-foreground' : ''}`}>
                                  {formatShortName(data.name)}
                                </td>
                                {weekDates.map((date) => {
                                  const dayShifts = data.shifts[date] || [];
                                  const isWknd = isWeekend(date);
                                  const isClosed = !!closedDays[date];
                                  
                                  // Summiere Stunden für diesen Tag
                                  dayShifts.forEach(s => {
                                    if (s.start_time && s.end_time) {
                                      const [sh, sm] = s.start_time.split(':').map(Number);
                                      const [eh, em] = s.end_time.split(':').map(Number);
                                      totalHours += (eh + em/60) - (sh + sm/60);
                                    }
                                  });
                                  
                                  return (
                                    <td 
                                      key={date} 
                                      className={`border border-gray-300 p-0.5 text-center text-[10px] ${
                                        isClosed ? "bg-red-50 text-red-400" : 
                                        isWknd ? "bg-amber-50" : ""
                                      }`}
                                    >
                                      {isClosed ? (
                                        <span className="text-[9px]">-</span>
                                      ) : dayShifts.length === 0 ? (
                                        <span className="text-gray-300">-</span>
                                      ) : (
                                        dayShifts.map((s, i) => (
                                          <div key={i} className="text-muted-foreground">
                                            {s.start_time?.slice(0,5)}–{s.end_time?.slice(0,5)}
                                          </div>
                                        ))
                                      )}
                                    </td>
                                  );
                                })}
                                <td className="border border-gray-300 p-1 text-center font-bold bg-gray-50">
                                  {totalHours.toFixed(1)}h
                                </td>
                              </tr>
                            );
                          });
                        })()}
                      </tbody>
                    </table>
                  </div>
                  
                  {/* Print Styles Info */}
                  <div className="mt-4 text-xs text-gray-500 print:hidden">
                    💡 Tipp: Für A4 Landscape-Druck nutzen Sie Strg+P und wählen Sie Querformat.
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Hours Overview */}
            {hoursOverview && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Stundenübersicht KW {week}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-2 px-3">Mitarbeiter</th>
                          <th className="text-center py-2 px-2 w-20">Bereich</th>
                          <th className="text-center py-2 px-2 w-16">Typ</th>
                          <th className="text-center py-2 px-3">Soll</th>
                          <th className="text-center py-2 px-3">Geplant</th>
                          <th className="text-center py-2 px-3">Differenz</th>
                          <th className="text-center py-2 px-3">Schichten</th>
                        </tr>
                      </thead>
                      <tbody>
                        {hoursOverview.overview.map((row) => {
                          // Mapping für Beschäftigungsart-Abkürzungen
                          const getEmploymentAbbr = (type) => {
                            if (!type) return "—";
                            const normalized = type.toLowerCase().trim();
                            if (normalized === "vollzeit" || normalized === "fulltime" || normalized === "full_time") return "VZ";
                            if (normalized === "teilzeit" || normalized === "parttime" || normalized === "part_time") return "TZ";
                            if (normalized === "minijob" || normalized === "aushilfe" || normalized === "mini_job") return "MJ";
                            if (normalized === "selbstständig" || normalized === "selbstaendig" || normalized === "self_employed" || normalized === "freelance") return "SE";
                            return "—";
                          };
                          
                          // Mapping für Bereich-Abkürzungen
                          const getAreaAbbr = (area) => {
                            if (!area || area === "—") return "—";
                            const normalized = area.toLowerCase().trim();
                            if (normalized === "service") return "SVC";
                            if (normalized === "küche" || normalized === "kueche") return "KÜ";
                            if (normalized === "reinigung") return "REI";
                            if (normalized === "event") return "EVT";
                            if (normalized === "bar") return "BAR";
                            return area.slice(0, 3).toUpperCase();
                          };
                          
                          const employmentAbbr = getEmploymentAbbr(row.employment_type);
                          const areaAbbr = getAreaAbbr(row.work_area);
                          
                          const employmentColors = {
                            "VZ": "bg-green-100 text-green-800 border-green-300",
                            "TZ": "bg-blue-100 text-blue-800 border-blue-300",
                            "MJ": "bg-amber-100 text-amber-800 border-amber-300",
                            "SE": "bg-purple-100 text-purple-800 border-purple-300",
                            "—": "bg-gray-100 text-gray-500 border-gray-300"
                          };
                          
                          const areaColors = {
                            "SVC": "bg-emerald-100 text-emerald-800",
                            "KÜ": "bg-orange-100 text-orange-800",
                            "REI": "bg-cyan-100 text-cyan-800",
                            "EVT": "bg-pink-100 text-pink-800",
                            "BAR": "bg-violet-100 text-violet-800",
                            "—": "bg-gray-100 text-gray-500"
                          };
                          
                          return (
                          <tr key={row.staff_member_id} className="border-b hover:bg-muted/50">
                            <td className="py-2 px-3 font-medium">{formatShortName(row.name)}</td>
                            <td className="py-1.5 px-2 text-center whitespace-nowrap">
                              <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${areaColors[areaAbbr] || areaColors["—"]}`}>
                                {areaAbbr}
                              </span>
                            </td>
                            <td className="py-1.5 px-2 text-center whitespace-nowrap">
                              <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium border ${employmentColors[employmentAbbr]}`}>
                                {employmentAbbr}
                              </span>
                            </td>
                            <td className="py-2 px-3 text-center">{row.weekly_hours_target}h</td>
                            <td className="py-2 px-3 text-center font-medium">{row.planned_hours}h</td>
                            <td className="py-2 px-3 text-center">
                              <span className={row.difference >= 0 ? "text-green-600" : "text-red-600"}>
                                {row.difference > 0 ? "+" : ""}{row.difference}h
                              </span>
                            </td>
                            <td className="py-2 px-3 text-center">{row.shift_count}</td>
                          </tr>
                          );
                        })}
                      </tbody>
                      <tfoot>
                        <tr className="bg-muted font-medium">
                          <td className="py-2 px-3">Gesamt</td>
                          <td></td>
                          <td className="py-2 px-3 text-center">{hoursOverview.total_target}h</td>
                          <td className="py-2 px-3 text-center">{hoursOverview.total_planned}h</td>
                          <td className="py-2 px-3 text-center">
                            <span className={hoursOverview.total_planned - hoursOverview.total_target >= 0 ? "text-green-600" : "text-red-600"}>
                              {hoursOverview.total_planned - hoursOverview.total_target > 0 ? "+" : ""}
                              {(hoursOverview.total_planned - hoursOverview.total_target).toFixed(1)}h
                            </span>
                          </td>
                          <td></td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </CardContent>
              </Card>
            )}
          </>
        )}
      </div>

      {/* Shift Dialog */}
      <Dialog open={showShiftDialog} onOpenChange={setShowShiftDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingShift ? "Schicht bearbeiten" : "Neue Schicht"}
            </DialogTitle>
            <DialogDescription>
              {selectedDate && `${FULL_DAYS[new Date(selectedDate).getDay() === 0 ? 6 : new Date(selectedDate).getDay() - 1]}, ${new Date(selectedDate).toLocaleDateString("de-DE")}`}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Mitarbeiter *</Label>
              <Select
                value={shiftData.staff_member_id}
                onValueChange={(v) => setShiftData({ ...shiftData, staff_member_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Mitarbeiter wählen" />
                </SelectTrigger>
                <SelectContent>
                  {staffMembers.map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {`${s.first_name || ''} ${s.last_name || ''}`.trim() || 'Unbekannt'}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Bereich *</Label>
              <Select
                value={shiftData.work_area_id}
                onValueChange={(v) => setShiftData({ ...shiftData, work_area_id: v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Bereich wählen" />
                </SelectTrigger>
                <SelectContent>
                  {workAreas.map((a) => (
                    <SelectItem key={a.id} value={a.id}>
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full" style={{ backgroundColor: a.color }} />
                        {a.name}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Von *</Label>
                <Input
                  type="time"
                  value={shiftData.start_time}
                  onChange={(e) => setShiftData({ ...shiftData, start_time: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Bis *</Label>
                <Input
                  type="time"
                  value={shiftData.end_time}
                  onChange={(e) => setShiftData({ ...shiftData, end_time: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Rolle</Label>
              <Select
                value={shiftData.role}
                onValueChange={(v) => setShiftData({ ...shiftData, role: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(SHIFT_ROLES).map(([key, { label }]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Notizen</Label>
              <Textarea
                value={shiftData.notes}
                onChange={(e) => setShiftData({ ...shiftData, notes: e.target.value })}
                placeholder="Optionale Notizen..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter className="flex justify-between">
            <div>
              {editingShift && (
                <Button
                  variant="destructive"
                  onClick={() => {
                    handleDeleteShift(editingShift.id);
                    setShowShiftDialog(false);
                  }}
                >
                  <Trash2 className="h-4 w-4 mr-2" />
                  Löschen
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setShowShiftDialog(false)}>
                Abbrechen
              </Button>
              <Button onClick={handleSaveShift} disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {editingShift ? "Speichern" : "Anlegen"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      
      {/* Apply Templates Dialog */}
      <Dialog open={showTemplatesDialog} onOpenChange={setShowTemplatesDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Wand2 className="h-5 w-5 text-purple-600" />
              Schicht-Vorlagen anwenden
            </DialogTitle>
            <DialogDescription>
              Erstellt Schichten basierend auf konfigurierten Vorlagen für diese Woche.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Bereiche</Label>
              <div className="flex gap-2">
                <Button
                  variant={templateSettings.departments.includes("service") ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    const deps = templateSettings.departments.includes("service")
                      ? templateSettings.departments.filter(d => d !== "service")
                      : [...templateSettings.departments, "service"];
                    setTemplateSettings({ ...templateSettings, departments: deps });
                  }}
                  className="flex-1"
                >
                  Service
                </Button>
                <Button
                  variant={templateSettings.departments.includes("kitchen") ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    const deps = templateSettings.departments.includes("kitchen")
                      ? templateSettings.departments.filter(d => d !== "kitchen")
                      : [...templateSettings.departments, "kitchen"];
                    setTemplateSettings({ ...templateSettings, departments: deps });
                  }}
                  className="flex-1"
                >
                  Küche
                </Button>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Saison</Label>
              <Select
                value={templateSettings.season || "auto"}
                onValueChange={(v) => setTemplateSettings({ ...templateSettings, season: v === "auto" ? null : v })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Saison wählen" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">Auto (aus Öffnungszeiten)</SelectItem>
                  <SelectItem value="summer">Sommer</SelectItem>
                  <SelectItem value="winter">Winter</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="bg-gray-50 rounded-lg p-3 text-sm text-gray-600">
              <p className="font-medium mb-1">Hinweis:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Schichten werden als Entwurf erstellt</li>
                <li>Mitarbeiter müssen danach zugewiesen werden</li>
                <li>Endzeiten "close+30" nutzen die Öffnungszeiten</li>
              </ul>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowTemplatesDialog(false)}>
              Abbrechen
            </Button>
            <Button 
              onClick={handleApplyTemplates} 
              disabled={applyingTemplates || templateSettings.departments.length === 0}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {applyingTemplates && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Anwenden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Schedule;
