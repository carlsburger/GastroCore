/**
 * ShiftsAdmin.jsx - Admin-Cockpit für Dienstplan V2
 * Modul 30: MITARBEITER & DIENSTPLAN
 * 
 * Verwendet ausschließlich /api/staff/shifts/v2 Endpoints
 * Keine Legacy-Logik, keine Schedule.jsx Abhängigkeiten
 */

import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { toast } from "sonner";
import {
  format,
  startOfWeek,
  endOfWeek,
  addDays,
  addWeeks,
  subWeeks,
  parseISO,
  isToday,
  isSameDay,
} from "date-fns";
import { de } from "date-fns/locale";

// UI Components
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Checkbox } from "../components/ui/checkbox";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";

// Icons
import {
  ChevronLeft,
  ChevronRight,
  Plus,
  Users,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Edit,
  Trash2,
  Send,
  UserPlus,
  UserMinus,
  RefreshCw,
  Coffee,
  LogIn,
  LogOut,
} from "lucide-react";

const API_URL = process.env.REACT_APP_BACKEND_URL || "";

// Status Badge Colors
const STATUS_COLORS = {
  DRAFT: "bg-gray-100 text-gray-800 border-gray-300",
  PUBLISHED: "bg-green-100 text-green-800 border-green-300",
  CANCELLED: "bg-red-100 text-red-800 border-red-300",
};

const STATUS_LABELS = {
  DRAFT: "Entwurf",
  PUBLISHED: "Veröffentlicht",
  CANCELLED: "Abgesagt",
};

// Role Labels - V2 kanonische Keys + Aliases
const ROLE_LABELS = {
  // Kanonische V2 Keys
  service: "Service",
  kitchen: "Küche",
  reinigung: "Reinigung",
  eismacher: "Eismacher",
  kuechenhilfe: "Küchenhilfe",
  // Rollen (nicht Departments)
  bar: "Bar",
  schichtleiter: "Schichtleiter",
  aushilfe: "Aushilfe",
  // Legacy Aliases
  cleaning: "Reinigung",
  ice_maker: "Eismacher",
  kitchen_help: "Küchenhilfe",
  kueche: "Küche",
};

export default function ShiftsAdmin() {
  const { token } = useAuth();
  
  // State
  const [shifts, setShifts] = useState([]);
  const [staffMembers, setStaffMembers] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentWeekStart, setCurrentWeekStart] = useState(
    startOfWeek(new Date(), { weekStartsOn: 1 })
  );
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [viewMode, setViewMode] = useState("week"); // "week" | "day"
  
  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [confirmAction, setConfirmAction] = useState(null);
  
  // Selected Shift for Edit/Assign
  const [selectedShift, setSelectedShift] = useState(null);
  
  // Daily Overview
  const [dailyOverview, setDailyOverview] = useState(null);
  
  // Form State
  const [formData, setFormData] = useState({
    date_local: format(new Date(), "yyyy-MM-dd"),
    start_time: "09:00",
    end_time: "17:00",
    role: "service",
    station: "",
    required_staff_count: 1,
    notes_staff: "",
    notes_internal: "",
    template_id: "",
  });

  // API Headers
  const headers = {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  };

  // ============== API CALLS ==============
  
  const fetchShifts = useCallback(async () => {
    try {
      const weekEnd = endOfWeek(currentWeekStart, { weekStartsOn: 1 });
      const params = new URLSearchParams({
        date_from: format(currentWeekStart, "yyyy-MM-dd"),
        date_to: format(weekEnd, "yyyy-MM-dd"),
        include_cancelled: "true",
      });
      
      const res = await fetch(`${API_URL}/api/staff/shifts/v2?${params}`, { headers });
      if (!res.ok) throw new Error("Fehler beim Laden der Schichten");
      
      const data = await res.json();
      setShifts(data.shifts || []);
    } catch (error) {
      console.error("fetchShifts error:", error);
      toast.error("Schichten konnten nicht geladen werden");
    }
  }, [token, currentWeekStart]);

  const fetchStaffMembers = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/staff/members`, { headers });
      if (!res.ok) throw new Error("Fehler beim Laden der Mitarbeiter");
      
      const data = await res.json();
      setStaffMembers(data.data || data || []);
    } catch (error) {
      console.error("fetchStaffMembers error:", error);
    }
  }, [token]);

  const fetchTemplates = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shift-templates?active_only=true`, { headers });
      if (!res.ok) throw new Error("Fehler beim Laden der Vorlagen");
      
      const data = await res.json();
      setTemplates(data.data || data || []);
    } catch (error) {
      console.error("fetchTemplates error:", error);
    }
  }, [token]);

  const fetchDailyOverview = useCallback(async (date) => {
    try {
      const dayKey = format(date, "yyyy-MM-dd");
      const res = await fetch(`${API_URL}/api/timeclock/admin/daily-overview?day_key=${dayKey}`, { headers });
      if (!res.ok) throw new Error("Fehler beim Laden der Tagesübersicht");
      
      const data = await res.json();
      setDailyOverview(data);
    } catch (error) {
      console.error("fetchDailyOverview error:", error);
      setDailyOverview(null);
    }
  }, [token]);

  // Load Data
  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchShifts(), fetchStaffMembers(), fetchTemplates()]);
      setLoading(false);
    };
    loadData();
  }, [fetchShifts, fetchStaffMembers, fetchTemplates]);

  // Load Daily Overview when date changes
  useEffect(() => {
    if (isToday(selectedDate)) {
      fetchDailyOverview(selectedDate);
    }
  }, [selectedDate, fetchDailyOverview]);

  // ============== SHIFT CRUD ==============

  const createShift = async () => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2`, {
        method: "POST",
        headers,
        body: JSON.stringify(formData),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Erstellen");
      }
      
      toast.success("Schicht erstellt");
      setCreateDialogOpen(false);
      resetForm();
      fetchShifts();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const updateShift = async () => {
    if (!selectedShift) return;
    
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${selectedShift.id}`, {
        method: "PATCH",
        headers,
        body: JSON.stringify(formData),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Aktualisieren");
      }
      
      toast.success("Schicht aktualisiert");
      setEditDialogOpen(false);
      setSelectedShift(null);
      resetForm();
      fetchShifts();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const deleteShift = async (shiftId) => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${shiftId}`, {
        method: "DELETE",
        headers,
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Löschen");
      }
      
      toast.success("Schicht gelöscht");
      fetchShifts();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const publishShift = async (shiftId) => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${shiftId}/publish`, {
        method: "POST",
        headers,
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Veröffentlichen");
      }
      
      toast.success("Schicht veröffentlicht");
      fetchShifts();
    } catch (error) {
      toast.error(error.message);
    }
  };

  const cancelShift = async (shiftId) => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${shiftId}/cancel`, {
        method: "POST",
        headers,
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Absagen");
      }
      
      toast.success("Schicht abgesagt");
      fetchShifts();
    } catch (error) {
      toast.error(error.message);
    }
  };

  // ============== STAFF ASSIGNMENT ==============

  const assignStaff = async (shiftId, staffId) => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${shiftId}/assign`, {
        method: "POST",
        headers,
        body: JSON.stringify({ staff_member_id: staffId }),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Zuweisen");
      }
      
      toast.success("Mitarbeiter zugewiesen");
      fetchShifts();
      
      // Update selected shift
      if (selectedShift?.id === shiftId) {
        const updated = await res.json();
        setSelectedShift(prev => ({
          ...prev,
          assigned_staff_ids: updated.assigned_staff_ids,
        }));
      }
    } catch (error) {
      toast.error(error.message);
    }
  };

  const unassignStaff = async (shiftId, staffId) => {
    try {
      const res = await fetch(`${API_URL}/api/staff/shifts/v2/${shiftId}/unassign`, {
        method: "POST",
        headers,
        body: JSON.stringify({ staff_member_id: staffId }),
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Fehler beim Entfernen");
      }
      
      toast.success("Mitarbeiter entfernt");
      fetchShifts();
      
      // Update selected shift
      if (selectedShift?.id === shiftId) {
        const updated = await res.json();
        setSelectedShift(prev => ({
          ...prev,
          assigned_staff_ids: updated.assigned_staff_ids,
        }));
      }
    } catch (error) {
      toast.error(error.message);
    }
  };

  // ============== HELPERS ==============

  const resetForm = () => {
    setFormData({
      date_local: format(selectedDate, "yyyy-MM-dd"),
      start_time: "09:00",
      end_time: "17:00",
      role: "service",
      station: "",
      required_staff_count: 1,
      notes_staff: "",
      notes_internal: "",
      template_id: "",
    });
  };

  const openCreateDialog = (date = null) => {
    resetForm();
    if (date) {
      setFormData(prev => ({ ...prev, date_local: format(date, "yyyy-MM-dd") }));
    }
    setCreateDialogOpen(true);
  };

  const openEditDialog = (shift) => {
    setSelectedShift(shift);
    setFormData({
      date_local: shift.date_local || shift.shift_date,
      start_time: shift.start_time || "09:00",
      end_time: shift.end_time || "17:00",
      role: shift.role || "service",
      station: shift.station || "",
      required_staff_count: shift.required_staff_count || 1,
      notes_staff: shift.notes_staff || "",
      notes_internal: shift.notes_internal || "",
    });
    setEditDialogOpen(true);
  };

  const openAssignDialog = (shift) => {
    setSelectedShift(shift);
    setAssignDialogOpen(true);
  };

  const openConfirmDialog = (action, shiftId, message) => {
    setConfirmAction({ action, shiftId, message });
    setConfirmDialogOpen(true);
  };

  const handleConfirmAction = () => {
    if (!confirmAction) return;
    
    switch (confirmAction.action) {
      case "publish":
        publishShift(confirmAction.shiftId);
        break;
      case "cancel":
        cancelShift(confirmAction.shiftId);
        break;
      case "delete":
        deleteShift(confirmAction.shiftId);
        break;
      default:
        break;
    }
    
    setConfirmDialogOpen(false);
    setConfirmAction(null);
  };

  const applyTemplate = (templateId) => {
    const template = templates.find(t => t.id === templateId);
    if (template) {
      setFormData(prev => ({
        ...prev,
        start_time: template.start_time || template.start_time_local || prev.start_time,
        end_time: template.end_time_fixed || template.end_time_local || prev.end_time,
        role: template.role || template.department || prev.role,
        station: template.station || "",
        template_id: templateId,
      }));
    }
  };

  // Get shifts for a specific date
  const getShiftsForDate = (date) => {
    const dateStr = format(date, "yyyy-MM-dd");
    return shifts.filter(s => 
      (s.date_local === dateStr) || (s.shift_date === dateStr)
    );
  };

  // Get week days
  const getWeekDays = () => {
    const days = [];
    for (let i = 0; i < 7; i++) {
      days.push(addDays(currentWeekStart, i));
    }
    return days;
  };

  // Navigation
  const prevWeek = () => setCurrentWeekStart(subWeeks(currentWeekStart, 1));
  const nextWeek = () => setCurrentWeekStart(addWeeks(currentWeekStart, 1));
  const goToToday = () => {
    const today = new Date();
    setCurrentWeekStart(startOfWeek(today, { weekStartsOn: 1 }));
    setSelectedDate(today);
  };

  // ============== RENDER ==============

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#FAFBE0]">
        <div className="flex flex-col items-center gap-4">
          <RefreshCw className="h-8 w-8 animate-spin text-[#005500]" />
          <span className="text-[#005500]">Lade Dienstplan...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFBE0] p-4 md:p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-serif font-bold text-[#005500]">
              Dienstplan V2
            </h1>
            <p className="text-[#005500]/70">
              Admin-Cockpit – Schichten verwalten
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={goToToday}
              className="border-[#005500] text-[#005500]"
            >
              Heute
            </Button>
            <Button
              onClick={() => openCreateDialog()}
              className="bg-[#005500] hover:bg-[#004400] text-white"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neue Schicht
            </Button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="week" className="space-y-4">
        <TabsList className="bg-white border border-[#005500]/20">
          <TabsTrigger value="week" onClick={() => setViewMode("week")}>
            <Calendar className="h-4 w-4 mr-2" />
            Wochenansicht
          </TabsTrigger>
          <TabsTrigger value="today" onClick={() => setViewMode("day")}>
            <Clock className="h-4 w-4 mr-2" />
            Heute
          </TabsTrigger>
        </TabsList>

        {/* Week View */}
        <TabsContent value="week">
          <Card className="border-[#005500]/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <Button variant="ghost" size="icon" onClick={prevWeek}>
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <CardTitle className="text-lg font-medium text-[#005500]">
                  {format(currentWeekStart, "d. MMMM", { locale: de })} –{" "}
                  {format(endOfWeek(currentWeekStart, { weekStartsOn: 1 }), "d. MMMM yyyy", { locale: de })}
                </CardTitle>
                <Button variant="ghost" size="icon" onClick={nextWeek}>
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-7 gap-2">
                {getWeekDays().map((day) => {
                  const dayShifts = getShiftsForDate(day);
                  const isCurrentDay = isToday(day);
                  const isSelected = isSameDay(day, selectedDate);
                  
                  return (
                    <div
                      key={day.toISOString()}
                      className={`min-h-[200px] border rounded-lg p-2 cursor-pointer transition-colors ${
                        isCurrentDay
                          ? "bg-[#005500]/10 border-[#005500]"
                          : isSelected
                          ? "bg-[#FFFF00]/20 border-[#005500]/50"
                          : "bg-white border-gray-200 hover:border-[#005500]/30"
                      }`}
                      onClick={() => setSelectedDate(day)}
                    >
                      <div className="text-center mb-2">
                        <div className="text-xs text-gray-500">
                          {format(day, "EEE", { locale: de })}
                        </div>
                        <div className={`text-lg font-medium ${isCurrentDay ? "text-[#005500]" : ""}`}>
                          {format(day, "d")}
                        </div>
                      </div>
                      
                      <div className="space-y-1">
                        {dayShifts.slice(0, 4).map((shift) => (
                          <div
                            key={shift.id}
                            className={`text-xs p-1 rounded border ${STATUS_COLORS[shift.status || "DRAFT"]}`}
                            onClick={(e) => {
                              e.stopPropagation();
                              openEditDialog(shift);
                            }}
                          >
                            <div className="font-medium truncate">
                              {shift.start_time} - {shift.end_time}
                            </div>
                            <div className="truncate text-[10px]">
                              {ROLE_LABELS[shift.role] || shift.role}
                            </div>
                            <div className="flex items-center gap-1 text-[10px]">
                              <Users className="h-2.5 w-2.5" />
                              {shift.assigned_staff?.length || 0}/{shift.required_staff_count || 1}
                            </div>
                          </div>
                        ))}
                        {dayShifts.length > 4 && (
                          <div className="text-xs text-center text-gray-500">
                            +{dayShifts.length - 4} weitere
                          </div>
                        )}
                        {dayShifts.length === 0 && (
                          <div className="text-xs text-center text-gray-400 py-4">
                            Keine Schichten
                          </div>
                        )}
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        className="w-full mt-2 h-6 text-xs"
                        onClick={(e) => {
                          e.stopPropagation();
                          openCreateDialog(day);
                        }}
                      >
                        <Plus className="h-3 w-3 mr-1" />
                        Hinzufügen
                      </Button>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Day Detail Panel */}
          <Card className="mt-4 border-[#005500]/20">
            <CardHeader>
              <CardTitle className="text-lg text-[#005500]">
                {format(selectedDate, "EEEE, d. MMMM yyyy", { locale: de })}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {getShiftsForDate(selectedDate).length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    Keine Schichten für diesen Tag
                  </div>
                ) : (
                  getShiftsForDate(selectedDate).map((shift) => (
                    <ShiftCard
                      key={shift.id}
                      shift={shift}
                      onEdit={() => openEditDialog(shift)}
                      onAssign={() => openAssignDialog(shift)}
                      onPublish={() => openConfirmDialog("publish", shift.id, "Schicht veröffentlichen?")}
                      onCancel={() => openConfirmDialog("cancel", shift.id, "Schicht absagen?")}
                      onDelete={() => openConfirmDialog("delete", shift.id, "Schicht löschen?")}
                    />
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Today View - Operative Control */}
        <TabsContent value="today">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Today's Shifts */}
            <Card className="border-[#005500]/20">
              <CardHeader>
                <CardTitle className="text-lg text-[#005500] flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  Geplante Schichten Heute
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {getShiftsForDate(new Date()).length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      Keine Schichten heute
                    </div>
                  ) : (
                    getShiftsForDate(new Date())
                      .filter(s => s.status !== "CANCELLED")
                      .map((shift) => (
                        <ShiftCard
                          key={shift.id}
                          shift={shift}
                          compact
                          onEdit={() => openEditDialog(shift)}
                          onAssign={() => openAssignDialog(shift)}
                          onPublish={() => openConfirmDialog("publish", shift.id, "Schicht veröffentlichen?")}
                          onCancel={() => openConfirmDialog("cancel", shift.id, "Schicht absagen?")}
                        />
                      ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Daily Overview - Timeclock Status */}
            <Card className="border-[#005500]/20">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg text-[#005500] flex items-center gap-2">
                    <Clock className="h-5 w-5" />
                    Tagesübersicht
                  </CardTitle>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => fetchDailyOverview(new Date())}
                  >
                    <RefreshCw className="h-4 w-4" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {dailyOverview ? (
                  <div className="space-y-4">
                    {/* Summary */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      <div className="bg-green-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-green-700">
                          {dailyOverview.summary?.working_count || 0}
                        </div>
                        <div className="text-xs text-green-600 flex items-center justify-center gap-1">
                          <LogIn className="h-3 w-3" />
                          Arbeiten
                        </div>
                      </div>
                      <div className="bg-yellow-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-yellow-700">
                          {dailyOverview.summary?.on_break_count || 0}
                        </div>
                        <div className="text-xs text-yellow-600 flex items-center justify-center gap-1">
                          <Coffee className="h-3 w-3" />
                          Pause
                        </div>
                      </div>
                      <div className="bg-blue-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-blue-700">
                          {dailyOverview.summary?.completed_count || 0}
                        </div>
                        <div className="text-xs text-blue-600 flex items-center justify-center gap-1">
                          <LogOut className="h-3 w-3" />
                          Fertig
                        </div>
                      </div>
                      <div className="bg-red-50 p-3 rounded-lg text-center">
                        <div className="text-2xl font-bold text-red-700">
                          {dailyOverview.summary?.missing_count || 0}
                        </div>
                        <div className="text-xs text-red-600 flex items-center justify-center gap-1">
                          <AlertCircle className="h-3 w-3" />
                          Fehlt
                        </div>
                      </div>
                    </div>

                    {/* Working */}
                    {dailyOverview.working?.length > 0 && (
                      <div>
                        <h4 className="font-medium text-green-700 mb-2 flex items-center gap-2">
                          <CheckCircle className="h-4 w-4" />
                          Aktiv ({dailyOverview.working.length})
                        </h4>
                        <div className="space-y-1">
                          {dailyOverview.working.map((w) => (
                            <div key={w.staff_id} className="text-sm bg-green-50 p-2 rounded flex justify-between">
                              <span>{w.staff_name}</span>
                              <span className="text-gray-500">
                                seit {w.clock_in_at?.split("T")[1]?.slice(0, 5)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* On Break */}
                    {dailyOverview.on_break?.length > 0 && (
                      <div>
                        <h4 className="font-medium text-yellow-700 mb-2 flex items-center gap-2">
                          <Coffee className="h-4 w-4" />
                          In Pause ({dailyOverview.on_break.length})
                        </h4>
                        <div className="space-y-1">
                          {dailyOverview.on_break.map((w) => (
                            <div key={w.staff_id} className="text-sm bg-yellow-50 p-2 rounded">
                              {w.staff_name}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Missing */}
                    {dailyOverview.missing?.length > 0 && (
                      <div>
                        <h4 className="font-medium text-red-700 mb-2 flex items-center gap-2">
                          <AlertCircle className="h-4 w-4" />
                          Fehlt trotz Schicht ({dailyOverview.missing.length})
                        </h4>
                        <div className="space-y-1">
                          {dailyOverview.missing.map((m) => (
                            <div key={m.staff_id} className="text-sm bg-red-50 p-2 rounded flex justify-between">
                              <span>{m.staff_name}</span>
                              <span className="text-xs text-gray-500">
                                {m.shifts?.[0]?.start_time} - {m.shifts?.[0]?.end_time}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    Keine Daten verfügbar
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Shift Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Neue Schicht erstellen</DialogTitle>
          </DialogHeader>
          <ShiftForm
            formData={formData}
            setFormData={setFormData}
            templates={templates}
            onApplyTemplate={applyTemplate}
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={createShift} className="bg-[#005500] hover:bg-[#004400]">
              Erstellen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Shift Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Schicht bearbeiten</DialogTitle>
          </DialogHeader>
          <ShiftForm
            formData={formData}
            setFormData={setFormData}
            templates={templates}
            onApplyTemplate={applyTemplate}
            isEdit
          />
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={updateShift} className="bg-[#005500] hover:bg-[#004400]">
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Staff Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Mitarbeiter zuweisen</DialogTitle>
          </DialogHeader>
          {selectedShift && (
            <AssignStaffPanel
              shift={selectedShift}
              staffMembers={staffMembers}
              onAssign={(staffId) => assignStaff(selectedShift.id, staffId)}
              onUnassign={(staffId) => unassignStaff(selectedShift.id, staffId)}
            />
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>
              Schließen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Dialog */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Bestätigung</AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.message}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Abbrechen</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmAction}>
              Bestätigen
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ============== SUB-COMPONENTS ==============

function ShiftCard({ shift, compact, onEdit, onAssign, onPublish, onCancel, onDelete }) {
  const assignedCount = shift.assigned_staff?.length || shift.assigned_staff_ids?.length || 0;
  const requiredCount = shift.required_staff_count || 1;
  const isFull = assignedCount >= requiredCount;
  
  return (
    <div className={`bg-white border rounded-lg p-3 ${STATUS_COLORS[shift.status || "DRAFT"]}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium">
              {shift.start_time} – {shift.end_time}
            </span>
            <Badge variant="outline" className={STATUS_COLORS[shift.status || "DRAFT"]}>
              {STATUS_LABELS[shift.status || "DRAFT"]}
            </Badge>
          </div>
          
          <div className="text-sm text-gray-600 space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-medium">{ROLE_LABELS[shift.role] || shift.role}</span>
              {shift.station && <span className="text-gray-400">• {shift.station}</span>}
            </div>
            
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              <span className={isFull ? "text-green-600" : "text-orange-600"}>
                {assignedCount}/{requiredCount} besetzt
              </span>
            </div>
            
            {!compact && shift.assigned_staff?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {shift.assigned_staff.map((s) => (
                  <Badge key={s.id} variant="secondary" className="text-xs">
                    {s.name}
                  </Badge>
                ))}
              </div>
            )}
            
            {shift.notes_staff && (
              <div className="text-xs text-gray-500 mt-1 italic">
                {shift.notes_staff}
              </div>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onAssign}>
            <UserPlus className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onEdit}>
            <Edit className="h-4 w-4" />
          </Button>
          
          {shift.status === "DRAFT" && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-green-600 hover:text-green-700"
              onClick={onPublish}
            >
              <Send className="h-4 w-4" />
            </Button>
          )}
          
          {shift.status !== "CANCELLED" && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-600 hover:text-red-700"
              onClick={onCancel}
            >
              <XCircle className="h-4 w-4" />
            </Button>
          )}
          
          {onDelete && shift.status === "DRAFT" && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-red-600 hover:text-red-700"
              onClick={onDelete}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function ShiftForm({ formData, setFormData, templates, onApplyTemplate, isEdit }) {
  return (
    <div className="space-y-4">
      {!isEdit && templates.length > 0 && (
        <div>
          <Label>Aus Vorlage</Label>
          <Select onValueChange={onApplyTemplate}>
            <SelectTrigger>
              <SelectValue placeholder="Vorlage wählen (optional)" />
            </SelectTrigger>
            <SelectContent>
              {templates.map((t) => (
                <SelectItem key={t.id} value={t.id}>
                  {t.name} ({t.start_time || t.start_time_local})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Datum</Label>
          <Input
            type="date"
            value={formData.date_local}
            onChange={(e) => setFormData({ ...formData, date_local: e.target.value })}
          />
        </div>
        <div>
          <Label>Rolle</Label>
          <Select
            value={formData.role}
            onValueChange={(v) => setFormData({ ...formData, role: v })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(ROLE_LABELS).map(([key, label]) => (
                <SelectItem key={key} value={key}>{label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Startzeit</Label>
          <Input
            type="time"
            value={formData.start_time}
            onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
          />
        </div>
        <div>
          <Label>Endzeit</Label>
          <Input
            type="time"
            value={formData.end_time}
            onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
          />
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Station (optional)</Label>
          <Input
            value={formData.station}
            onChange={(e) => setFormData({ ...formData, station: e.target.value })}
            placeholder="z.B. Terrasse"
          />
        </div>
        <div>
          <Label>Soll-Besetzung</Label>
          <Input
            type="number"
            min="1"
            max="20"
            value={formData.required_staff_count}
            onChange={(e) => setFormData({ ...formData, required_staff_count: parseInt(e.target.value) || 1 })}
          />
        </div>
      </div>
      
      <div>
        <Label>Notizen für Mitarbeiter</Label>
        <Textarea
          value={formData.notes_staff}
          onChange={(e) => setFormData({ ...formData, notes_staff: e.target.value })}
          placeholder="Sichtbar für zugewiesene Mitarbeiter"
          rows={2}
        />
      </div>
      
      <div>
        <Label>Interne Notizen</Label>
        <Textarea
          value={formData.notes_internal}
          onChange={(e) => setFormData({ ...formData, notes_internal: e.target.value })}
          placeholder="Nur für Admins sichtbar"
          rows={2}
        />
      </div>
    </div>
  );
}

function AssignStaffPanel({ shift, staffMembers, onAssign, onUnassign }) {
  const assignedIds = shift.assigned_staff_ids || shift.assigned_staff?.map(s => s.id) || [];
  
  return (
    <div className="space-y-4">
      <div className="bg-gray-50 p-3 rounded-lg">
        <div className="text-sm">
          <strong>{shift.start_time} – {shift.end_time}</strong>
          <span className="text-gray-500 ml-2">
            {ROLE_LABELS[shift.role] || shift.role}
          </span>
        </div>
        <div className="text-sm text-gray-600 mt-1">
          Besetzung: {assignedIds.length} / {shift.required_staff_count || 1}
        </div>
      </div>
      
      <div>
        <Label className="mb-2 block">Zugewiesene Mitarbeiter</Label>
        {assignedIds.length === 0 ? (
          <div className="text-sm text-gray-500 py-2">Niemand zugewiesen</div>
        ) : (
          <div className="space-y-1">
            {staffMembers
              .filter((s) => assignedIds.includes(s.id))
              .map((staff) => (
                <div
                  key={staff.id}
                  className="flex items-center justify-between bg-green-50 p-2 rounded"
                >
                  <span className="text-sm">
                    {staff.full_name || `${staff.first_name} ${staff.last_name}`}
                  </span>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 text-red-600 hover:text-red-700"
                    onClick={() => onUnassign(staff.id)}
                  >
                    <UserMinus className="h-4 w-4" />
                  </Button>
                </div>
              ))}
          </div>
        )}
      </div>
      
      <div>
        <Label className="mb-2 block">Verfügbare Mitarbeiter</Label>
        <div className="space-y-1 max-h-[200px] overflow-y-auto">
          {staffMembers
            .filter((s) => !assignedIds.includes(s.id))
            .map((staff) => (
              <div
                key={staff.id}
                className="flex items-center justify-between bg-gray-50 p-2 rounded hover:bg-gray-100"
              >
                <div>
                  <span className="text-sm">
                    {staff.full_name || `${staff.first_name} ${staff.last_name}`}
                  </span>
                  {staff.role && (
                    <span className="text-xs text-gray-500 ml-2">
                      ({ROLE_LABELS[staff.role] || staff.role})
                    </span>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-green-600 hover:text-green-700"
                  onClick={() => onAssign(staff.id)}
                >
                  <UserPlus className="h-4 w-4" />
                </Button>
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
