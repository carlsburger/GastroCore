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
  bar: { label: "Bar", color: "#8b5cf6" },
  aushilfe: { label: "Aushilfe", color: "#6b7280" },
};

// Helper to get current calendar week
const getCurrentWeek = () => {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 1);
  const diff = now - start + ((start.getTimezoneOffset() - now.getTimezoneOffset()) * 60 * 1000);
  const oneWeek = 1000 * 60 * 60 * 24 * 7;
  return Math.ceil((diff / oneWeek + start.getDay() + 1) / 7);
};

export const Schedule = () => {
  const [year, setYear] = useState(new Date().getFullYear());
  const [week, setWeek] = useState(getCurrentWeek());
  const [schedule, setSchedule] = useState(null);
  const [staffMembers, setStaffMembers] = useState([]);
  const [workAreas, setWorkAreas] = useState([]);
  const [hoursOverview, setHoursOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showShiftDialog, setShowShiftDialog] = useState(false);
  const [editingShift, setEditingShift] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);

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
        params: { year, status: "all" },
      });
      
      const existingSchedule = schedulesRes.data.find(
        (s) => s.year === year && s.week === week && !s.archived
      );

      if (existingSchedule) {
        // Load full schedule with shifts
        const scheduleRes = await axios.get(
          `${BACKEND_URL}/api/staff/schedules/${existingSchedule.id}`,
          { headers }
        );
        setSchedule(scheduleRes.data);
      } else {
        setSchedule(null);
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

  const handleCreateSchedule = async () => {
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/staff/schedules`,
        { year, week },
        { headers }
      );
      toast.success("Dienstplan erstellt");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
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
        `${BACKEND_URL}/api/staff/export/schedule/${schedule.id}/pdf`,
        { headers, responseType: "blob" }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `dienstplan_kw${week}_${year}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("PDF heruntergeladen");
    } catch (err) {
      toast.error("Fehler beim Export");
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
    const start = new Date(schedule.week_start);
    return Array.from({ length: 7 }, (_, i) => {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      return date.toISOString().split("T")[0];
    });
  };

  const getShiftsForDate = (date) => {
    if (!schedule?.shifts) return [];
    return schedule.shifts.filter((s) => s.shift_date === date);
  };

  const weekDates = getWeekDates();
  const statusConfig = STATUS_CONFIG[schedule?.status] || STATUS_CONFIG.entwurf;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl font-medium text-primary">Dienstplan</h1>
            <p className="text-muted-foreground">Wochenübersicht und Schichtplanung</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchData} className="rounded-full">
              <RefreshCw className="h-4 w-4" />
            </Button>
            {schedule && (
              <>
                <Button variant="outline" onClick={handleExportPDF} className="rounded-full">
                  <Download className="h-4 w-4 mr-2" />
                  PDF
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
                    {new Date(schedule.week_start).toLocaleDateString("de-DE")} - {new Date(schedule.week_end).toLocaleDateString("de-DE")}
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
            {/* Week Grid */}
            <div className="grid grid-cols-7 gap-2">
              {weekDates.map((date, idx) => {
                const shifts = getShiftsForDate(date);
                const dayDate = new Date(date);
                const isToday = new Date().toISOString().split("T")[0] === date;

                return (
                  <Card key={date} className={isToday ? "ring-2 ring-primary" : ""}>
                    <CardHeader className="pb-2 px-3 pt-3">
                      <div className="flex justify-between items-center">
                        <div>
                          <p className="font-bold text-lg">{DAYS[idx]}</p>
                          <p className="text-sm text-muted-foreground">
                            {dayDate.getDate()}.{dayDate.getMonth() + 1}.
                          </p>
                        </div>
                        {schedule.status !== "archiviert" && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => openShiftDialog(date)}
                            className="h-7 w-7 p-0"
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </CardHeader>
                    <CardContent className="px-3 pb-3 space-y-2">
                      {shifts.length === 0 ? (
                        <p className="text-xs text-muted-foreground text-center py-4">-</p>
                      ) : (
                        shifts.map((shift) => {
                          const area = workAreas.find((a) => a.id === shift.work_area_id);
                          return (
                            <div
                              key={shift.id}
                              className="p-2 rounded-lg text-xs cursor-pointer hover:opacity-80 transition-opacity"
                              style={{ backgroundColor: area?.color + "20", borderLeft: `3px solid ${area?.color}` }}
                              onClick={() => schedule.status !== "archiviert" && openShiftDialog(date, shift)}
                            >
                              <p className="font-medium truncate">{shift.staff_member?.full_name || "?"}</p>
                              <p className="text-muted-foreground">
                                {shift.start_time} - {shift.end_time}
                              </p>
                              <p className="text-muted-foreground truncate">{area?.name}</p>
                            </div>
                          );
                        })
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>

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
                          <th className="text-center py-2 px-3">Beschäftigung</th>
                          <th className="text-center py-2 px-3">Soll</th>
                          <th className="text-center py-2 px-3">Geplant</th>
                          <th className="text-center py-2 px-3">Differenz</th>
                          <th className="text-center py-2 px-3">Schichten</th>
                        </tr>
                      </thead>
                      <tbody>
                        {hoursOverview.overview.map((row) => (
                          <tr key={row.staff_member_id} className="border-b hover:bg-muted/50">
                            <td className="py-2 px-3 font-medium">{row.name}</td>
                            <td className="py-2 px-3 text-center">
                              <Badge variant="outline" className="text-xs">
                                {row.employment_type}
                              </Badge>
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
                        ))}
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
                      {s.full_name}
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
    </Layout>
  );
};

export default Schedule;
