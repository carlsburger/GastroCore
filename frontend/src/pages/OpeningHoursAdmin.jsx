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
  
  // Closure Dialog - erweitert für Datumsbereich
  const [showClosureDialog, setShowClosureDialog] = useState(false);
  const [editingClosure, setEditingClosure] = useState(null);
  const [closureForm, setClosureForm] = useState({
    // Neues einfaches Format mit Datumsbereich
    start_date: "",
    end_date: "",
    type: "closed_all_day", // closed_all_day oder closed_partial
    start_time: "",
    end_time: "",
    reason: "",
  });
  const [savingClosure, setSavingClosure] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [periodsRes, closuresRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/opening-hours/periods`, { headers }),
        axios.get(`${BACKEND_URL}/api/opening-hours/closures`, { headers }),
      ]);
      setPeriods(periodsRes.data);
      setClosures(closuresRes.data);
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

  // ============== CLOSURE FUNCTIONS (Einfaches Datumsbereich-Format) ==============
  
  const openClosureDialog = (closure = null) => {
    if (closure) {
      setEditingClosure(closure);
      setClosureForm({
        start_date: closure.start_date || closure.one_off_rule?.date || "",
        end_date: closure.end_date || closure.start_date || closure.one_off_rule?.date || "",
        type: closure.type === "closed_all_day" || closure.scope === "full_day" ? "closed_all_day" : "closed_partial",
        start_time: closure.start_time || "",
        end_time: closure.end_time || "",
        reason: closure.reason || "",
      });
    } else {
      setEditingClosure(null);
      // Default: Heute als Einzeltag, ganztags geschlossen
      const today = new Date().toISOString().split("T")[0];
      setClosureForm({
        start_date: today,
        end_date: today,
        type: "closed_all_day",
        start_time: "",
        end_time: "",
        reason: "",
      });
    }
    setShowClosureDialog(true);
  };

  const saveClosure = async () => {
    // Validierung
    if (!closureForm.reason) {
      toast.error("Bitte geben Sie einen Grund an");
      return;
    }
    if (!closureForm.start_date) {
      toast.error("Bitte geben Sie ein Startdatum an");
      return;
    }
    if (closureForm.type === "closed_partial" && (!closureForm.start_time || !closureForm.end_time)) {
      toast.error("Bei teilweiser Sperrung: Bitte Start- und Endzeit angeben");
      return;
    }
    
    setSavingClosure(true);
    try {
      const payload = {
        start_date: closureForm.start_date,
        end_date: closureForm.end_date || closureForm.start_date,
        type: closureForm.type,
        reason: closureForm.reason,
      };
      
      if (closureForm.type === "closed_partial") {
        payload.start_time = closureForm.start_time;
        payload.end_time = closureForm.end_time;
      }
      
      if (editingClosure?.id) {
        // Update: Löschen und neu anlegen (einfacher als PATCH für neues Format)
        await axios.delete(`${BACKEND_URL}/api/opening-hours/closures/${editingClosure.id}`, { headers });
        await axios.post(`${BACKEND_URL}/api/opening-hours/closures`, payload, { headers });
        toast.success("Sperrtag aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/opening-hours/closures`, payload, { headers });
        toast.success("Sperrtag erstellt");
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

  const deleteClosure = async (closureId) => {
    if (!window.confirm("Sperrtag wirklich löschen?")) return;
    
    try {
      await axios.delete(`${BACKEND_URL}/api/opening-hours/closures/${closureId}`, { headers });
      toast.success("Sperrtag gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const formatClosureDate = (closure) => {
    // Neues Format: start_date / end_date
    if (closure.start_date) {
      if (closure.end_date && closure.end_date !== closure.start_date) {
        return `${closure.start_date} bis ${closure.end_date}`;
      }
      return closure.start_date;
    }
    // Legacy: recurring
    if (closure.type === "recurring") {
      const month = MONTHS.find(m => m.value === closure.recurring_rule?.month)?.label || "";
      return `${closure.recurring_rule?.day}. ${month} (jährlich)`;
    }
    // Legacy: one_off
    return closure.one_off_rule?.date || "";
  };
  
  const formatClosureType = (closure) => {
    if (closure.type === "closed_all_day" || closure.scope === "full_day") {
      return "Ganztags geschlossen";
    }
    if (closure.type === "closed_partial" || closure.scope === "time_range") {
      return `Geschlossen ${closure.start_time || "?"} - ${closure.end_time || "?"}`;
    }
    return closure.type;
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

          {/* CLOSURES TAB */}
          <TabsContent value="closures" className="space-y-4">
            <div className="flex justify-between items-center">
              <p className="text-sm text-[#002f02]/70">
                Definieren Sie Sperrtage (einmalig oder jährlich wiederkehrend).
              </p>
              <Button onClick={() => openClosureDialog()} className="bg-[#002f02] hover:bg-[#003d03]">
                <Plus className="h-4 w-4 mr-2" />
                Neuer Sperrtag
              </Button>
            </div>

            {closures.length === 0 ? (
              <Card className="border-[#002f02]/20">
                <CardContent className="py-12 text-center">
                  <CalendarX className="h-12 w-12 mx-auto text-[#002f02]/30 mb-4" />
                  <p className="text-[#002f02]/70">Keine Sperrtage definiert.</p>
                  <p className="text-sm text-[#002f02]/50 mt-1">
                    Fügen Sie Feiertage oder Betriebsferien hinzu.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <Card className="border-[#002f02]/20">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Datum</TableHead>
                      <TableHead>Typ</TableHead>
                      <TableHead>Umfang</TableHead>
                      <TableHead>Grund</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Aktionen</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {closures.map((closure) => (
                      <TableRow key={closure.id}>
                        <TableCell className="font-medium">
                          {formatClosureDate(closure)}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={closure.type === "recurring" ? "border-amber-500 text-amber-700" : "border-blue-500 text-blue-700"}>
                            {closure.type === "recurring" ? "Jährlich" : "Einmalig"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {closure.scope === "full_day" ? (
                            "Ganzer Tag"
                          ) : (
                            `${closure.start_time} - ${closure.end_time}`
                          )}
                        </TableCell>
                        <TableCell>{closure.reason}</TableCell>
                        <TableCell>
                          {closure.active ? (
                            <Badge className="bg-green-100 text-green-800">Aktiv</Badge>
                          ) : (
                            <Badge variant="secondary">Inaktiv</Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm" onClick={() => openClosureDialog(closure)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => deleteClosure(closure.id)} className="text-red-600 hover:text-red-700">
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

        {/* CLOSURE DIALOG */}
        <Dialog open={showClosureDialog} onOpenChange={setShowClosureDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="text-[#002f02]">
                {editingClosure?.id ? "Sperrtag bearbeiten" : "Neuer Sperrtag"}
              </DialogTitle>
              <DialogDescription>
                Definieren Sie einen Tag oder Zeitraum, an dem das Restaurant geschlossen ist.
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4 py-4">
              {/* Type Selection */}
              {!editingClosure?.id && (
                <div>
                  <Label>Typ</Label>
                  <Select
                    value={closureForm.type}
                    onValueChange={(v) => setClosureForm(f => ({ ...f, type: v }))}
                  >
                    <SelectTrigger className="mt-1">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="one_off">Einmalig (bestimmtes Datum)</SelectItem>
                      <SelectItem value="recurring">Jährlich wiederkehrend</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Date Selection */}
              {closureForm.type === "one_off" ? (
                <div>
                  <Label>Datum *</Label>
                  <Input
                    type="date"
                    value={closureForm.one_off_rule.date}
                    onChange={(e) => setClosureForm(f => ({ ...f, one_off_rule: { date: e.target.value } }))}
                    className="mt-1"
                    disabled={!!editingClosure?.id}
                  />
                </div>
              ) : (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Tag *</Label>
                    <Input
                      type="number"
                      min="1"
                      max="31"
                      value={closureForm.recurring_rule.day}
                      onChange={(e) => setClosureForm(f => ({ ...f, recurring_rule: { ...f.recurring_rule, day: parseInt(e.target.value) } }))}
                      className="mt-1"
                      disabled={!!editingClosure?.id}
                    />
                  </div>
                  <div>
                    <Label>Monat *</Label>
                    <Select
                      value={String(closureForm.recurring_rule.month)}
                      onValueChange={(v) => setClosureForm(f => ({ ...f, recurring_rule: { ...f.recurring_rule, month: parseInt(v) } }))}
                      disabled={!!editingClosure?.id}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {MONTHS.map((m) => (
                          <SelectItem key={m.value} value={String(m.value)}>{m.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Scope */}
              <div>
                <Label>Umfang</Label>
                <Select
                  value={closureForm.scope}
                  onValueChange={(v) => setClosureForm(f => ({ ...f, scope: v }))}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="full_day">Ganzer Tag geschlossen</SelectItem>
                    <SelectItem value="time_range">Nur bestimmte Uhrzeiten</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Time Range */}
              {closureForm.scope === "time_range" && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Ab *</Label>
                    <Input
                      type="time"
                      value={closureForm.start_time}
                      onChange={(e) => setClosureForm(f => ({ ...f, start_time: e.target.value }))}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label>Bis *</Label>
                    <Input
                      type="time"
                      value={closureForm.end_time}
                      onChange={(e) => setClosureForm(f => ({ ...f, end_time: e.target.value }))}
                      className="mt-1"
                    />
                  </div>
                </div>
              )}

              {/* Reason */}
              <div>
                <Label>Grund *</Label>
                <Input
                  value={closureForm.reason}
                  onChange={(e) => setClosureForm(f => ({ ...f, reason: e.target.value }))}
                  placeholder="z.B. Heiligabend, Betriebsferien, Renovierung"
                  className="mt-1"
                />
              </div>

              {/* Active */}
              <div className="flex items-center gap-2">
                <Switch
                  checked={closureForm.active}
                  onCheckedChange={(v) => setClosureForm(f => ({ ...f, active: v }))}
                />
                <Label>Aktiv</Label>
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
