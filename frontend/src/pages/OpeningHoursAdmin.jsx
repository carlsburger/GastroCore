import React, { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { toast } from "sonner";
import {
  Clock,
  Calendar,
  Plus,
  Trash2,
  Loader2,
  Save,
  ArrowLeft,
  Copy,
  Edit,
  CalendarX,
  AlertTriangle,
  Sun,
  Snowflake,
  Check,
  X,
} from "lucide-react";
import axios from "axios";
import { Link } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const WEEKDAYS = [
  { key: "monday", label: "Montag", short: "Mo" },
  { key: "tuesday", label: "Dienstag", short: "Di" },
  { key: "wednesday", label: "Mittwoch", short: "Mi" },
  { key: "thursday", label: "Donnerstag", short: "Do" },
  { key: "friday", label: "Freitag", short: "Fr" },
  { key: "saturday", label: "Samstag", short: "Sa" },
  { key: "sunday", label: "Sonntag", short: "So" },
];

const MONTHS = [
  { value: 1, label: "Januar" },
  { value: 2, label: "Februar" },
  { value: 3, label: "März" },
  { value: 4, label: "April" },
  { value: 5, label: "Mai" },
  { value: 6, label: "Juni" },
  { value: 7, label: "Juli" },
  { value: 8, label: "August" },
  { value: 9, label: "September" },
  { value: 10, label: "Oktober" },
  { value: 11, label: "November" },
  { value: 12, label: "Dezember" },
];

export default function OpeningHoursAdmin() {
  const [loading, setLoading] = useState(true);
  const [periods, setPeriods] = useState([]);
  const [closures, setClosures] = useState([]);
  const [activeTab, setActiveTab] = useState("periods");
  
  // Period Dialog
  const [showPeriodDialog, setShowPeriodDialog] = useState(false);
  const [editingPeriod, setEditingPeriod] = useState(null);
  const [periodForm, setPeriodForm] = useState({
    name: "",
    start_date: "",
    end_date: "",
    priority: 0,
    active: true,
    rules_by_weekday: {},
  });
  const [savingPeriod, setSavingPeriod] = useState(false);
  
  // Closure Dialog - erweitert für Datumsbereich und OFFEN/GESCHLOSSEN
  const [showClosureDialog, setShowClosureDialog] = useState(false);
  const [editingClosure, setEditingClosure] = useState(null);
  const [closureForm, setClosureForm] = useState({
    // Neues Override-Format
    date_from: "",
    date_to: "",
    status: "closed", // "closed" oder "open"
    open_from: "",    // Bei status=open
    open_to: "",      // Bei status=open
    last_reservation_time: "", // Optional
    note: "",
    priority: 100,
  });
  const [savingClosure, setSavingClosure] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [periodsRes, overridesRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/opening-hours/periods`, { headers }),
        axios.get(`${BACKEND_URL}/api/opening-hours/overrides`, { headers }),
      ]);
      setPeriods(periodsRes.data);
      setClosures(overridesRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ============== PERIOD FUNCTIONS ==============
  
  const initializeWeekdayRules = () => {
    const rules = {};
    WEEKDAYS.forEach(day => {
      rules[day.key] = {
        is_closed: false,
        blocks: [{ start: "11:30", end: "22:00", reservable: true, label: "" }]
      };
    });
    return rules;
  };

  const openPeriodDialog = (period = null) => {
    if (period) {
      setEditingPeriod(period);
      setPeriodForm({
        name: period.name,
        start_date: period.start_date,
        end_date: period.end_date,
        priority: period.priority || 0,
        active: period.active !== false,
        rules_by_weekday: period.rules_by_weekday || initializeWeekdayRules(),
      });
    } else {
      setEditingPeriod(null);
      const today = new Date();
      const year = today.getFullYear();
      setPeriodForm({
        name: "",
        start_date: `${year}-01-01`,
        end_date: `${year}-12-31`,
        priority: 0,
        active: true,
        rules_by_weekday: initializeWeekdayRules(),
      });
    }
    setShowPeriodDialog(true);
  };

  const duplicatePeriod = (period) => {
    const newPeriod = {
      ...period,
      name: `${period.name} (Kopie)`,
      id: undefined,
    };
    openPeriodDialog(newPeriod);
    setEditingPeriod(null); // Treat as new
  };

  const savePeriod = async () => {
    if (!periodForm.name || !periodForm.start_date || !periodForm.end_date) {
      toast.error("Bitte füllen Sie alle Pflichtfelder aus");
      return;
    }
    
    setSavingPeriod(true);
    try {
      if (editingPeriod?.id) {
        await axios.patch(
          `${BACKEND_URL}/api/opening-hours/periods/${editingPeriod.id}`,
          periodForm,
          { headers }
        );
        toast.success("Periode aktualisiert");
      } else {
        await axios.post(
          `${BACKEND_URL}/api/opening-hours/periods`,
          periodForm,
          { headers }
        );
        toast.success("Periode erstellt");
      }
      setShowPeriodDialog(false);
      fetchData();
    } catch (err) {
      const message = err.response?.data?.detail || "Fehler beim Speichern";
      toast.error(message);
    } finally {
      setSavingPeriod(false);
    }
  };

  const deletePeriod = async (periodId) => {
    if (!window.confirm("Periode wirklich löschen?")) return;
    
    try {
      await axios.delete(`${BACKEND_URL}/api/opening-hours/periods/${periodId}`, { headers });
      toast.success("Periode gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const updateWeekdayRule = (dayKey, field, value) => {
    setPeriodForm(prev => ({
      ...prev,
      rules_by_weekday: {
        ...prev.rules_by_weekday,
        [dayKey]: {
          ...prev.rules_by_weekday[dayKey],
          [field]: value
        }
      }
    }));
  };

  const updateWeekdayBlock = (dayKey, blockIndex, field, value) => {
    setPeriodForm(prev => {
      const blocks = [...(prev.rules_by_weekday[dayKey]?.blocks || [])];
      blocks[blockIndex] = { ...blocks[blockIndex], [field]: value };
      return {
        ...prev,
        rules_by_weekday: {
          ...prev.rules_by_weekday,
          [dayKey]: {
            ...prev.rules_by_weekday[dayKey],
            blocks
          }
        }
      };
    });
  };

  const addWeekdayBlock = (dayKey) => {
    setPeriodForm(prev => {
      const blocks = [...(prev.rules_by_weekday[dayKey]?.blocks || [])];
      blocks.push({ start: "18:00", end: "22:00", reservable: true, label: "" });
      return {
        ...prev,
        rules_by_weekday: {
          ...prev.rules_by_weekday,
          [dayKey]: {
            ...prev.rules_by_weekday[dayKey],
            blocks
          }
        }
      };
    });
  };

  const removeWeekdayBlock = (dayKey, blockIndex) => {
    setPeriodForm(prev => {
      const blocks = [...(prev.rules_by_weekday[dayKey]?.blocks || [])];
      blocks.splice(blockIndex, 1);
      return {
        ...prev,
        rules_by_weekday: {
          ...prev.rules_by_weekday,
          [dayKey]: {
            ...prev.rules_by_weekday[dayKey],
            blocks
          }
        }
      };
    });
  };

  // ============== OVERRIDE FUNCTIONS (Neues Format mit status=open/closed) ==============
  
  const openClosureDialog = (override = null) => {
    if (override) {
      setEditingClosure(override);
      setClosureForm({
        date_from: override.date_from || override.start_date || "",
        date_to: override.date_to || override.end_date || override.date_from || "",
        status: override.status || (override.type === "closed_all_day" ? "closed" : "closed"),
        open_from: override.open_from || "",
        open_to: override.open_to || "",
        last_reservation_time: override.last_reservation_time || "",
        note: override.note || override.reason || "",
        priority: override.priority || 100,
      });
    } else {
      setEditingClosure(null);
      // Default: Heute als Einzeltag, geschlossen
      const today = new Date().toISOString().split("T")[0];
      setClosureForm({
        date_from: today,
        date_to: today,
        status: "closed",
        open_from: "",
        open_to: "",
        last_reservation_time: "",
        note: "",
        priority: 100,
      });
    }
    setShowClosureDialog(true);
  };

  const saveClosure = async () => {
    // Validierung
    if (!closureForm.note) {
      toast.error("Bitte geben Sie eine Notiz/Grund an");
      return;
    }
    if (!closureForm.date_from) {
      toast.error("Bitte geben Sie ein Startdatum an");
      return;
    }
    if (closureForm.status === "open" && (!closureForm.open_from || !closureForm.open_to)) {
      toast.error("Bei 'Offen' müssen Öffnungszeiten angegeben werden");
      return;
    }
    
    setSavingClosure(true);
    try {
      const payload = {
        date_from: closureForm.date_from,
        date_to: closureForm.date_to || closureForm.date_from,
        status: closureForm.status,
        note: closureForm.note,
        priority: closureForm.priority || 100,
      };
      
      if (closureForm.status === "open") {
        payload.open_from = closureForm.open_from;
        payload.open_to = closureForm.open_to;
        if (closureForm.last_reservation_time) {
          payload.last_reservation_time = closureForm.last_reservation_time;
        }
      }
      
      if (editingClosure?.id) {
        // Update via PUT
        await axios.put(`${BACKEND_URL}/api/opening-hours/overrides/${editingClosure.id}`, payload, { headers });
        toast.success("Override aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/opening-hours/overrides`, payload, { headers });
        toast.success("Override erstellt");
      }
      setShowClosureDialog(false);
      fetchData();
    } catch (err) {
      const message = err.response?.data?.detail || "Fehler beim Speichern";
      toast.error(message);
    } finally {
      setSavingClosure(false);
    }
  };

  const deleteClosure = async (overrideId) => {
    if (!window.confirm("Override wirklich löschen?")) return;
    
    try {
      await axios.delete(`${BACKEND_URL}/api/opening-hours/overrides/${overrideId}`, { headers });
      toast.success("Override gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const formatClosureDate = (override) => {
    const from = override.date_from || override.start_date || "";
    const to = override.date_to || override.end_date || "";
    if (to && to !== from) {
      return `${from} bis ${to}`;
    }
    return from;
  };
  
  const formatClosureStatus = (override) => {
    if (override.status === "open") {
      return `Offen ${override.open_from || "?"} - ${override.open_to || "?"}`;
    }
    return "Geschlossen";
  };

  // ============== RENDER ==============

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-[#002f02]" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/settings">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="h-5 w-5" />
              </Button>
            </Link>
            <div>
              <h1 className="text-2xl font-serif font-bold text-[#002f02]">
                Öffnungszeiten & Sperrtage
              </h1>
              <p className="text-[#002f02]/70">Master-Konfiguration für Reservierungen & Dienstplan</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-[#002f02]/10">
            <TabsTrigger 
              value="periods" 
              className="data-[state=active]:bg-[#002f02] data-[state=active]:text-white"
            >
              <Clock className="h-4 w-4 mr-2" />
              Öffnungszeiten-Perioden
            </TabsTrigger>
            <TabsTrigger 
              value="closures"
              className="data-[state=active]:bg-[#002f02] data-[state=active]:text-white"
            >
              <CalendarX className="h-4 w-4 mr-2" />
              Sperrtage
            </TabsTrigger>
          </TabsList>

          {/* PERIODS TAB */}
          <TabsContent value="periods" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-[#002f02]/70">
                Definieren Sie Zeiträume mit unterschiedlichen Öffnungszeiten (z.B. Sommer/Winter).
                Bei Überlappungen gewinnt die höhere Priorität.
              </p>
              <Button onClick={() => openPeriodDialog()} className="bg-[#002f02] hover:bg-[#003d03]">
                <Plus className="h-4 w-4 mr-2" />
                Neue Periode
              </Button>
            </div>

            {periods.length === 0 ? (
              <Card className="border-[#002f02]/20">
                <CardContent className="py-12 text-center">
                  <Clock className="h-12 w-12 mx-auto text-[#002f02]/30 mb-4" />
                  <p className="text-[#002f02]/70">Keine Öffnungszeiten-Perioden definiert.</p>
                  <p className="text-sm text-[#002f02]/50 mt-1">
                    Erstellen Sie eine Periode für Ihre Standard-Öffnungszeiten.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4">
                {periods.map((period) => (
                  <Card key={period.id} className={`border-[#002f02]/20 ${!period.active ? 'opacity-60' : ''}`}>
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          {period.name.toLowerCase().includes("sommer") ? (
                            <Sun className="h-5 w-5 text-amber-500" />
                          ) : period.name.toLowerCase().includes("winter") ? (
                            <Snowflake className="h-5 w-5 text-blue-500" />
                          ) : (
                            <Calendar className="h-5 w-5 text-[#002f02]" />
                          )}
                          <CardTitle className="text-lg text-[#002f02]">{period.name}</CardTitle>
                          <Badge variant={period.active ? "default" : "secondary"} className={period.active ? "bg-green-100 text-green-800" : ""}>
                            {period.active ? "Aktiv" : "Inaktiv"}
                          </Badge>
                          <Badge variant="outline" className="border-[#002f02]/30">
                            Priorität: {period.priority || 0}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm" onClick={() => duplicatePeriod(period)}>
                            <Copy className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => openPeriodDialog(period)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => deletePeriod(period.id)} className="text-red-600 hover:text-red-700">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                      <CardDescription>
                        {period.start_date} bis {period.end_date}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {WEEKDAYS.map((day) => {
                          const rules = period.rules_by_weekday?.[day.key];
                          const isClosed = rules?.is_closed;
                          const blocks = rules?.blocks || [];
                          
                          return (
                            <div 
                              key={day.key} 
                              className={`px-3 py-2 rounded-lg text-sm ${isClosed ? 'bg-red-100 text-red-800' : 'bg-[#002f02]/10 text-[#002f02]'}`}
                            >
                              <span className="font-medium">{day.short}:</span>{" "}
                              {isClosed ? (
                                "Geschlossen"
                              ) : blocks.length > 0 ? (
                                blocks.map((b, i) => `${b.start}-${b.end}`).join(", ")
                              ) : (
                                "Nicht konfiguriert"
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </TabsContent>

          {/* CLOSURES/OVERRIDES TAB */}
          <TabsContent value="closures" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-[#002f02]/70">
                Overrides haben <strong>höchste Priorität</strong> und überschreiben Perioden & Feiertage.
                Sie können Tage als GESCHLOSSEN oder mit SONDERÖFFNUNG definieren.
              </p>
              <Button onClick={() => openClosureDialog()} className="bg-[#002f02] hover:bg-[#003d03]">
                <Plus className="h-4 w-4 mr-2" />
                Neuer Override
              </Button>
            </div>

            {closures.length === 0 ? (
              <Card className="border-[#002f02]/20">
                <CardContent className="py-12 text-center">
                  <CalendarX className="h-12 w-12 mx-auto text-[#002f02]/30 mb-4" />
                  <p className="text-[#002f02]/70">Keine Overrides definiert.</p>
                  <p className="text-sm text-[#002f02]/50 mt-1">
                    Fügen Sie Sperrtage (Heiligabend, Silvester) oder Sonderöffnungen hinzu.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-[#002f02]/20">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Datum / Zeitraum</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Notiz</TableHead>
                      <TableHead>Priorität</TableHead>
                      <TableHead className="text-right">Aktionen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {closures.map((override) => (
                      <TableRow key={override.id}>
                        <TableCell className="font-medium">
                          {formatClosureDate(override)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={
                            override.status === "open" 
                              ? "border-green-500 text-green-700 bg-green-50" 
                              : "border-red-500 text-red-700 bg-red-50"
                          }>
                            {formatClosureStatus(override)}
                          </Badge>
                          {override.last_reservation_time && (
                            <span className="text-xs text-gray-500 ml-2">
                              Letzte Res.: {override.last_reservation_time}
                            </span>
                          )}
                        </TableCell>
                        <TableCell>{override.note || override.reason}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">{override.priority || 100}</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" onClick={() => openClosureDialog(override)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => deleteClosure(override.id)} className="text-red-600 hover:text-red-700">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Card>
            )}
          </TabsContent>
        </Tabs>

        {/* PERIOD DIALOG */}
        <Dialog open={showPeriodDialog} onOpenChange={setShowPeriodDialog}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-[#002f02]">
                {editingPeriod?.id ? "Periode bearbeiten" : "Neue Periode erstellen"}
              </DialogTitle>
              <DialogDescription>
                Definieren Sie Öffnungszeiten für einen Zeitraum.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6 py-4">
              {/* Basic Info */}
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <Label>Name *</Label>
                  <Input
                    value={periodForm.name}
                    onChange={(e) => setPeriodForm(p => ({ ...p, name: e.target.value }))}
                    placeholder="z.B. Sommer 2026, Winter 2026"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Startdatum *</Label>
                  <Input
                    type="date"
                    value={periodForm.start_date}
                    onChange={(e) => setPeriodForm(p => ({ ...p, start_date: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Enddatum *</Label>
                  <Input
                    type="date"
                    value={periodForm.end_date}
                    onChange={(e) => setPeriodForm(p => ({ ...p, end_date: e.target.value }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Priorität (bei Überlappung)</Label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={periodForm.priority}
                    onChange={(e) => setPeriodForm(p => ({ ...p, priority: parseInt(e.target.value) || 0 }))}
                    className="mt-1"
                  />
                  <p className="text-xs text-gray-500 mt-1">Höhere Werte gewinnen bei überlappenden Perioden</p>
                </div>
                <div className="flex items-center gap-2 pt-6">
                  <Switch
                    checked={periodForm.active}
                    onCheckedChange={(v) => setPeriodForm(p => ({ ...p, active: v }))}
                  />
                  <Label>Aktiv</Label>
                </div>
              </div>

              {/* Weekday Rules */}
              <div className="space-y-4">
                <Label className="text-lg font-semibold text-[#002f02]">Öffnungszeiten pro Wochentag</Label>
                {WEEKDAYS.map((day) => {
                  const rules = periodForm.rules_by_weekday[day.key] || { is_closed: false, blocks: [] };
                  
                  return (
                    <Card key={day.key} className="border-[#002f02]/20">
                      <CardContent className="py-3">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <span className="font-medium text-[#002f02] w-24">{day.label}</span>
                            <div className="flex items-center gap-2">
                              <Switch
                                checked={rules.is_closed}
                                onCheckedChange={(v) => updateWeekdayRule(day.key, "is_closed", v)}
                              />
                              <span className="text-sm text-gray-600">Geschlossen</span>
                            </div>
                          </div>
                          {!rules.is_closed && (
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => addWeekdayBlock(day.key)}
                            >
                              <Plus className="h-3 w-3 mr-1" />
                              Block
                            </Button>
                          )}
                        </div>
                        
                        {!rules.is_closed && rules.blocks?.map((block, idx) => (
                          <div key={idx} className="flex items-center gap-2 mt-2 ml-4">
                            <Input
                              type="time"
                              value={block.start}
                              onChange={(e) => updateWeekdayBlock(day.key, idx, "start", e.target.value)}
                              className="w-32"
                            />
                            <span>bis</span>
                            <Input
                              type="time"
                              value={block.end}
                              onChange={(e) => updateWeekdayBlock(day.key, idx, "end", e.target.value)}
                              className="w-32"
                            />
                            <div className="flex items-center gap-1">
                              <Switch
                                checked={block.reservable !== false}
                                onCheckedChange={(v) => updateWeekdayBlock(day.key, idx, "reservable", v)}
                              />
                              <span className="text-xs text-gray-500">Reservierbar</span>
                            </div>
                            <Input
                              value={block.label || ""}
                              onChange={(e) => updateWeekdayBlock(day.key, idx, "label", e.target.value)}
                              placeholder="Label (optional)"
                              className="w-40"
                            />
                            {rules.blocks.length > 1 && (
                              <Button 
                                variant="ghost" 
                                size="sm"
                                onClick={() => removeWeekdayBlock(day.key, idx)}
                                className="text-red-600"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        ))}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowPeriodDialog(false)}>
                Abbrechen
              </Button>
              <Button 
                onClick={savePeriod} 
                disabled={savingPeriod}
                className="bg-[#002f02] hover:bg-[#003d03]"
              >
                {savingPeriod ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Speichern...</>
                ) : (
                  <><Save className="mr-2 h-4 w-4" /> Speichern</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* OVERRIDE DIALOG */}
        <Dialog open={showClosureDialog} onOpenChange={setShowClosureDialog}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="text-[#002f02]">
                {editingClosure?.id ? "Override bearbeiten" : "Neuer Override"}
              </DialogTitle>
              <DialogDescription>
                Overrides haben <strong>höchste Priorität</strong> und überschreiben Perioden & Feiertage.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Datumsbereich */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Von Datum *</Label>
                  <Input
                    type="date"
                    value={closureForm.date_from}
                    onChange={(e) => setClosureForm(f => ({ 
                      ...f, 
                      date_from: e.target.value,
                      date_to: f.date_to || e.target.value
                    }))}
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label>Bis Datum</Label>
                  <Input
                    type="date"
                    value={closureForm.date_to}
                    onChange={(e) => setClosureForm(f => ({ ...f, date_to: e.target.value }))}
                    className="mt-1"
                    min={closureForm.date_from}
                  />
                  <p className="text-xs text-gray-500 mt-1">Leer = Einzeltag</p>
                </div>
              </div>

              {/* Status: Geschlossen / Offen */}
              <div>
                <Label>Status</Label>
                <Select
                  value={closureForm.status}
                  onValueChange={(v) => setClosureForm(f => ({ ...f, status: v }))}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="closed">🔴 Geschlossen</SelectItem>
                    <SelectItem value="open">🟢 Offen (Sonderöffnung)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Öffnungszeiten bei status=open */}
              {closureForm.status === "open" && (
                <div className="p-4 bg-green-50 rounded-lg border border-green-200 space-y-3">
                  <p className="text-sm font-medium text-green-800">Sonderöffnungszeiten</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Öffnung *</Label>
                      <Input
                        type="time"
                        value={closureForm.open_from}
                        onChange={(e) => setClosureForm(f => ({ ...f, open_from: e.target.value }))}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>Schließung *</Label>
                      <Input
                        type="time"
                        value={closureForm.open_to}
                        onChange={(e) => setClosureForm(f => ({ ...f, open_to: e.target.value }))}
                        className="mt-1"
                      />
                    </div>
                  </div>
                  <div>
                    <Label>Letzte Reservierung (optional)</Label>
                    <Input
                      type="time"
                      value={closureForm.last_reservation_time}
                      onChange={(e) => setClosureForm(f => ({ ...f, last_reservation_time: e.target.value }))}
                      className="mt-1"
                      placeholder="z.B. 14:30 für Silvester"
                    />
                    <p className="text-xs text-green-700 mt-1">
                      Beispiel Silvester: Offen 12:00-16:00, letzte Reservierung 14:30
                    </p>
                  </div>
                </div>
              )}

              {/* Notiz */}
              <div>
                <Label>Notiz / Grund *</Label>
                <Input
                  value={closureForm.note}
                  onChange={(e) => setClosureForm(f => ({ ...f, note: e.target.value }))}
                  placeholder="z.B. Heiligabend, Silvester, Betriebsferien"
                  className="mt-1"
                />
              </div>

              {/* Priorität */}
              <div>
                <Label>Priorität</Label>
                <Input
                  type="number"
                  min="0"
                  max="1000"
                  value={closureForm.priority}
                  onChange={(e) => setClosureForm(f => ({ ...f, priority: parseInt(e.target.value) || 100 }))}
                  className="mt-1 w-32"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Höhere Werte gewinnen bei überlappenden Overrides (Standard: 100)
                </p>
              </div>
              
              {/* Hinweis-Box */}
              <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 text-sm text-blue-800">
                <strong>💡 Tipp:</strong> Overrides überschreiben alles - auch Feiertage und Ruhetage.
                Nutzen Sie "Offen" für Silvester (12:00-16:00, letzte Res. 14:30).
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowClosureDialog(false)}>
                Abbrechen
              </Button>
              <Button 
                onClick={saveClosure} 
                disabled={savingClosure}
                className="bg-[#002f02] hover:bg-[#003d03]"
              >
                {savingClosure ? (
                  <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Speichern...</>
                ) : (
                  <><Save className="mr-2 h-4 w-4" /> Speichern</>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
