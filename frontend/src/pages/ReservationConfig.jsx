import React, { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import { Layout } from "../components/Layout";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
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
import {
  Clock,
  Calendar,
  Plus,
  Trash2,
  Save,
  Settings,
  Ban,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const DAY_NAMES = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"];

export const ReservationConfig = () => {
  const { token } = useAuth();

  // State
  const [activeTab, setActiveTab] = useState("duration");
  const [loading, setLoading] = useState(false);
  const [dataLoaded, setDataLoaded] = useState(false);
  
  // Duration Settings
  const [durationSettings, setDurationSettings] = useState({
    default_duration_minutes: 110,
    extension_options_minutes: [30, 60, 90, 120]
  });
  
  // Time Slot Configs (Durchgänge & Sperrzeiten)
  const [timeSlotConfigs, setTimeSlotConfigs] = useState([]);
  const [editingDay, setEditingDay] = useState(null);
  const [editingConfig, setEditingConfig] = useState(null);
  
  // Opening Periods (Zeiträume)
  const [openingPeriods, setOpeningPeriods] = useState([]);
  const [editingPeriod, setEditingPeriod] = useState(null);
  const [showPeriodDialog, setShowPeriodDialog] = useState(false);

  // Headers für API-Aufrufe
  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  // Fetch data when token is available
  useEffect(() => {
    const loadData = async () => {
      if (!token) return;
      
      try {
        // Fetch Duration Settings
        const durationRes = await axios.get(`${BACKEND_URL}/api/reservation-config/duration-settings`, { 
          headers: { Authorization: `Bearer ${token}` }
        });
        setDurationSettings(durationRes.data);
        
        // Fetch Time Slot Configs
        const slotsRes = await axios.get(`${BACKEND_URL}/api/reservation-config/time-slots`, { 
          headers: { Authorization: `Bearer ${token}` }
        });
        setTimeSlotConfigs(slotsRes.data);
        
        // Fetch Opening Periods
        const periodsRes = await axios.get(`${BACKEND_URL}/api/reservation-config/opening-periods`, { 
          headers: { Authorization: `Bearer ${token}` }
        });
        setOpeningPeriods(periodsRes.data);
        
        setDataLoaded(true);
      } catch (err) {
        console.error("Fehler beim Laden der Daten:", err);
      }
    };
    
    loadData();
  }, [token]);

  // Refresh functions for button
  const refreshData = async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [durationRes, slotsRes, periodsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/reservation-config/duration-settings`, { headers }),
        axios.get(`${BACKEND_URL}/api/reservation-config/time-slots`, { headers }),
        axios.get(`${BACKEND_URL}/api/reservation-config/opening-periods`, { headers })
      ]);
      setDurationSettings(durationRes.data);
      setTimeSlotConfigs(slotsRes.data);
      setOpeningPeriods(periodsRes.data);
      toast.success("Daten aktualisiert");
    } catch (err) {
      toast.error("Fehler beim Aktualisieren");
    } finally {
      setLoading(false);
    }
  };

  // Duration Settings Handlers
  const saveDurationSettings = async () => {
    setLoading(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/reservation-config/duration-settings?default_minutes=${durationSettings.default_duration_minutes}`,
        {},
        { headers }
      );
      toast.success("Aufenthaltsdauer gespeichert");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setLoading(false);
    }
  };

  // Time Slot Config Handlers
  const openEditDay = (day) => {
    const config = timeSlotConfigs.find(c => c.day_of_week === day) || {
      day_of_week: day,
      slots: [],
      blocked_ranges: [],
      slot_interval_minutes: 30,
      use_manual_slots: false
    };
    setEditingDay(day);
    setEditingConfig({ ...config });
  };

  const saveTimeSlotConfig = async () => {
    setLoading(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/reservation-config/time-slots`,
        editingConfig,
        { headers }
      );
      toast.success(`${DAY_NAMES[editingDay]} gespeichert`);
      fetchTimeSlotConfigs();
      setEditingDay(null);
      setEditingConfig(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setLoading(false);
    }
  };

  const addBlockedRange = () => {
    setEditingConfig({
      ...editingConfig,
      blocked_ranges: [...editingConfig.blocked_ranges, { start: "12:00", end: "14:00" }]
    });
  };

  const removeBlockedRange = (index) => {
    const newRanges = [...editingConfig.blocked_ranges];
    newRanges.splice(index, 1);
    setEditingConfig({ ...editingConfig, blocked_ranges: newRanges });
  };

  const updateBlockedRange = (index, field, value) => {
    const newRanges = [...editingConfig.blocked_ranges];
    newRanges[index] = { ...newRanges[index], [field]: value };
    setEditingConfig({ ...editingConfig, blocked_ranges: newRanges });
  };

  const addSlot = () => {
    const newSlots = [...editingConfig.slots, "12:00"].sort();
    setEditingConfig({ ...editingConfig, slots: newSlots });
  };

  const removeSlot = (index) => {
    const newSlots = [...editingConfig.slots];
    newSlots.splice(index, 1);
    setEditingConfig({ ...editingConfig, slots: newSlots });
  };

  const updateSlot = (index, value) => {
    const newSlots = [...editingConfig.slots];
    newSlots[index] = value;
    setEditingConfig({ ...editingConfig, slots: newSlots.sort() });
  };

  // Opening Period Handlers
  const openPeriodDialog = (period = null) => {
    if (period) {
      setEditingPeriod({ ...period });
    } else {
      setEditingPeriod({
        name: "",
        start_date: "",
        end_date: "",
        is_default: false,
        hours: DAY_NAMES.map((_, i) => ({
          day_of_week: i,
          open_time: "11:00",
          close_time: "22:00",
          is_closed: false
        }))
      });
    }
    setShowPeriodDialog(true);
  };

  const savePeriod = async () => {
    setLoading(true);
    try {
      if (editingPeriod.id) {
        await axios.patch(
          `${BACKEND_URL}/api/reservation-config/opening-periods/${editingPeriod.id}`,
          editingPeriod,
          { headers }
        );
        toast.success("Periode aktualisiert");
      } else {
        await axios.post(
          `${BACKEND_URL}/api/reservation-config/opening-periods`,
          editingPeriod,
          { headers }
        );
        toast.success("Periode erstellt");
      }
      fetchOpeningPeriods();
      setShowPeriodDialog(false);
      setEditingPeriod(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setLoading(false);
    }
  };

  const deletePeriod = async (periodId) => {
    if (!window.confirm("Periode wirklich löschen?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/reservation-config/opening-periods/${periodId}`, { headers });
      toast.success("Periode gelöscht");
      fetchOpeningPeriods();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Löschen");
    }
  };

  const updatePeriodHour = (dayIndex, field, value) => {
    const newHours = [...editingPeriod.hours];
    newHours[dayIndex] = { ...newHours[dayIndex], [field]: value };
    setEditingPeriod({ ...editingPeriod, hours: newHours });
  };

  return (
    <Layout>
    <div className="container mx-auto p-6 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Settings className="h-8 w-8" />
            Reservierungs-Konfiguration
          </h1>
          <p className="text-muted-foreground mt-1">
            Aufenthaltsdauer, Durchgänge, Sperrzeiten und Öffnungszeiten
          </p>
        </div>
        <Button onClick={refreshData} variant="outline" disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Aktualisieren
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="duration">
            <Clock className="h-4 w-4 mr-2" />
            Aufenthaltsdauer
          </TabsTrigger>
          <TabsTrigger value="timeslots">
            <Ban className="h-4 w-4 mr-2" />
            Durchgänge & Sperrzeiten
          </TabsTrigger>
          <TabsTrigger value="periods">
            <Calendar className="h-4 w-4 mr-2" />
            Öffnungszeiten-Perioden
          </TabsTrigger>
        </TabsList>

        {/* TAB: Aufenthaltsdauer */}
        <TabsContent value="duration">
          <Card>
            <CardHeader>
              <CardTitle>Standard-Aufenthaltsdauer</CardTitle>
              <CardDescription>
                Die voreingestellte Zeit, die für jede Reservierung angenommen wird.
                Mitarbeiter können diese verlängern.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <Label>Standard-Aufenthaltsdauer (Minuten)</Label>
                  <Input
                    type="number"
                    min={30}
                    max={300}
                    value={durationSettings.default_duration_minutes}
                    onChange={(e) => setDurationSettings({
                      ...durationSettings,
                      default_duration_minutes: parseInt(e.target.value) || 110
                    })}
                    className="mt-1"
                  />
                  <p className="text-sm text-muted-foreground mt-1">
                    = {Math.floor(durationSettings.default_duration_minutes / 60)}h {durationSettings.default_duration_minutes % 60}min
                  </p>
                </div>
                <div>
                  <Label>Verlängerungs-Optionen</Label>
                  <div className="flex gap-2 mt-2">
                    {durationSettings.extension_options_minutes?.map((min, i) => (
                      <Badge key={i} variant="secondary">+{min} min</Badge>
                    ))}
                  </div>
                </div>
              </div>
              <Button onClick={saveDurationSettings} disabled={loading}>
                <Save className="h-4 w-4 mr-2" />
                Speichern
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* TAB: Durchgänge & Sperrzeiten */}
        <TabsContent value="timeslots">
          <Card>
            <CardHeader>
              <CardTitle>Durchgänge & Sperrzeiten pro Wochentag</CardTitle>
              <CardDescription>
                Definieren Sie buchbare Zeitslots und Sperrzeiten zwischen Durchgängen.
                Beispiel: Sa/So mit Mittags- und Nachmittagsdurchgang.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!dataLoaded ? (
                <div className="text-center py-8 text-muted-foreground">
                  <RefreshCw className="h-8 w-8 mx-auto mb-4 animate-spin" />
                  <p>Lade Konfiguration...</p>
                </div>
              ) : timeSlotConfigs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <p>Keine Zeitslot-Konfiguration gefunden.</p>
                  <p className="text-sm">Die API gibt möglicherweise leere Daten zurück.</p>
                </div>
              ) : (
                <div className="grid gap-4">
                  {timeSlotConfigs.map((config, index) => (
                    <div
                      key={config.day_of_week}
                      className="flex items-center justify-between p-4 border rounded-lg hover:bg-muted/50 cursor-pointer"
                      onClick={() => openEditDay(config.day_of_week)}
                    >
                      <div className="flex items-center gap-4">
                        <span className="font-medium w-24">{config.day_name}</span>
                        {config.use_manual_slots ? (
                          <Badge variant="outline" className="text-xs">
                            {config.slots?.length || 0} Slots definiert
                          </Badge>
                        ) : (
                          <Badge variant="secondary" className="text-xs">
                            Auto ({config.slot_interval_minutes}min Intervall)
                          </Badge>
                        )}
                        {config.blocked_ranges?.length > 0 && (
                          <Badge variant="destructive" className="text-xs">
                            <Ban className="h-3 w-3 mr-1" />
                            {config.blocked_ranges.length} Sperrzeit(en)
                          </Badge>
                        )}
                      </div>
                      <Button variant="ghost" size="sm">Bearbeiten</Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Edit Day Dialog */}
          <Dialog open={editingDay !== null} onOpenChange={() => { setEditingDay(null); setEditingConfig(null); }}>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingDay !== null && DAY_NAMES[editingDay]} - Zeitslots & Sperrzeiten
                </DialogTitle>
              </DialogHeader>
              
              {editingConfig && (
                <div className="space-y-6">
                  {/* Slot-Modus */}
                  <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                    <div>
                      <Label>Manuelle Slots verwenden</Label>
                      <p className="text-sm text-muted-foreground">
                        Wenn aktiviert: Nur explizit definierte Zeiten sind buchbar
                      </p>
                    </div>
                    <Switch
                      checked={editingConfig.use_manual_slots}
                      onCheckedChange={(checked) => setEditingConfig({
                        ...editingConfig,
                        use_manual_slots: checked
                      })}
                    />
                  </div>

                  {/* Auto-Intervall */}
                  {!editingConfig.use_manual_slots && (
                    <div>
                      <Label>Slot-Intervall (Minuten)</Label>
                      <Select
                        value={String(editingConfig.slot_interval_minutes)}
                        onValueChange={(v) => setEditingConfig({
                          ...editingConfig,
                          slot_interval_minutes: parseInt(v)
                        })}
                      >
                        <SelectTrigger className="w-32 mt-1">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="15">15 min</SelectItem>
                          <SelectItem value="30">30 min</SelectItem>
                          <SelectItem value="60">60 min</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}

                  {/* Manuelle Slots */}
                  {editingConfig.use_manual_slots && (
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Label>Buchbare Zeiten</Label>
                        <Button size="sm" variant="outline" onClick={addSlot}>
                          <Plus className="h-4 w-4 mr-1" />
                          Zeit hinzufügen
                        </Button>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {editingConfig.slots?.map((slot, i) => (
                          <div key={i} className="flex items-center gap-1 bg-muted p-2 rounded">
                            <Input
                              type="time"
                              value={slot}
                              onChange={(e) => updateSlot(i, e.target.value)}
                              className="w-28 h-8"
                            />
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => removeSlot(i)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sperrzeiten */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Label>Sperrzeiten (Durchgangs-Pausen)</Label>
                      <Button size="sm" variant="outline" onClick={addBlockedRange}>
                        <Plus className="h-4 w-4 mr-1" />
                        Sperrzeit hinzufügen
                      </Button>
                    </div>
                    {editingConfig.blocked_ranges?.length === 0 && (
                      <p className="text-sm text-muted-foreground">
                        Keine Sperrzeiten definiert - alle Slots innerhalb der Öffnungszeiten sind buchbar.
                      </p>
                    )}
                    <div className="space-y-2">
                      {editingConfig.blocked_ranges?.map((range, i) => (
                        <div key={i} className="flex items-center gap-2 p-3 border rounded-lg bg-red-50">
                          <Ban className="h-5 w-5 text-red-500" />
                          <span className="text-sm">von</span>
                          <Input
                            type="time"
                            value={range.start}
                            onChange={(e) => updateBlockedRange(i, 'start', e.target.value)}
                            className="w-28"
                          />
                          <span className="text-sm">bis</span>
                          <Input
                            type="time"
                            value={range.end}
                            onChange={(e) => updateBlockedRange(i, 'end', e.target.value)}
                            className="w-28"
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => removeBlockedRange(i)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <DialogFooter>
                <Button variant="outline" onClick={() => { setEditingDay(null); setEditingConfig(null); }}>
                  Abbrechen
                </Button>
                <Button onClick={saveTimeSlotConfig} disabled={loading}>
                  <Save className="h-4 w-4 mr-2" />
                  Speichern
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>

        {/* TAB: Öffnungszeiten-Perioden */}
        <TabsContent value="periods">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Öffnungszeiten nach Zeitraum</span>
                <Button onClick={() => openPeriodDialog()}>
                  <Plus className="h-4 w-4 mr-2" />
                  Neue Periode
                </Button>
              </CardTitle>
              <CardDescription>
                Definieren Sie unterschiedliche Öffnungszeiten für verschiedene Zeiträume
                (z.B. Sommer, Winter, Feiertage).
              </CardDescription>
            </CardHeader>
            <CardContent>
              {openingPeriods.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Keine Perioden definiert.</p>
                  <p className="text-sm">Die Standard-Öffnungszeiten werden verwendet.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {openingPeriods.map((period) => (
                    <div
                      key={period.id}
                      className="p-4 border rounded-lg hover:bg-muted/50"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">{period.name}</h3>
                            {period.is_default && (
                              <Badge variant="secondary">Standard</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {period.start_date} bis {period.end_date}
                          </p>
                          <div className="flex flex-wrap gap-2 mt-3">
                            {period.hours?.map((h, i) => (
                              <Badge
                                key={i}
                                variant={h.is_closed ? "destructive" : "outline"}
                                className="text-xs"
                              >
                                {DAY_NAMES[h.day_of_week].substring(0, 2)}:{" "}
                                {h.is_closed ? "Geschl." : `${h.open_time}-${h.close_time}`}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openPeriodDialog(period)}
                          >
                            Bearbeiten
                          </Button>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => deletePeriod(period.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Period Dialog */}
          <Dialog open={showPeriodDialog} onOpenChange={setShowPeriodDialog}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>
                  {editingPeriod?.id ? "Periode bearbeiten" : "Neue Periode erstellen"}
                </DialogTitle>
              </DialogHeader>
              
              {editingPeriod && (
                <div className="space-y-6">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <Label>Name</Label>
                      <Input
                        value={editingPeriod.name}
                        onChange={(e) => setEditingPeriod({ ...editingPeriod, name: e.target.value })}
                        placeholder="z.B. Sommerzeit"
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>Startdatum</Label>
                      <Input
                        type="date"
                        value={editingPeriod.start_date}
                        onChange={(e) => setEditingPeriod({ ...editingPeriod, start_date: e.target.value })}
                        className="mt-1"
                      />
                    </div>
                    <div>
                      <Label>Enddatum</Label>
                      <Input
                        type="date"
                        value={editingPeriod.end_date}
                        onChange={(e) => setEditingPeriod({ ...editingPeriod, end_date: e.target.value })}
                        className="mt-1"
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Switch
                      checked={editingPeriod.is_default}
                      onCheckedChange={(checked) => setEditingPeriod({ ...editingPeriod, is_default: checked })}
                    />
                    <Label>Als Standard-Periode verwenden (Fallback)</Label>
                  </div>

                  <div>
                    <Label className="mb-3 block">Öffnungszeiten pro Wochentag</Label>
                    <div className="space-y-2">
                      {editingPeriod.hours?.map((hour, i) => (
                        <div key={i} className="flex items-center gap-3 p-3 bg-muted rounded-lg">
                          <span className="w-24 font-medium">{DAY_NAMES[i]}</span>
                          <Switch
                            checked={!hour.is_closed}
                            onCheckedChange={(checked) => updatePeriodHour(i, 'is_closed', !checked)}
                          />
                          <span className="text-sm w-16">{hour.is_closed ? "Geschl." : "Geöffnet"}</span>
                          {!hour.is_closed && (
                            <>
                              <Input
                                type="time"
                                value={hour.open_time}
                                onChange={(e) => updatePeriodHour(i, 'open_time', e.target.value)}
                                className="w-28"
                              />
                              <span>bis</span>
                              <Input
                                type="time"
                                value={hour.close_time}
                                onChange={(e) => updatePeriodHour(i, 'close_time', e.target.value)}
                                className="w-28"
                              />
                            </>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              <DialogFooter>
                <Button variant="outline" onClick={() => { setShowPeriodDialog(false); setEditingPeriod(null); }}>
                  Abbrechen
                </Button>
                <Button onClick={savePeriod} disabled={loading}>
                  <Save className="h-4 w-4 mr-2" />
                  Speichern
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </TabsContent>
      </Tabs>
    </div>
    </Layout>
  );
};

export default ReservationConfig;
