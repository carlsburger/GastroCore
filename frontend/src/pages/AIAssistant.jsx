import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../hooks/use-toast";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Bot,
  Calendar,
  Users,
  Megaphone,
  Settings,
  CheckCircle,
  XCircle,
  Clock,
  Sparkles,
  AlertTriangle,
  Lightbulb,
  ThumbsUp,
  ThumbsDown,
  Edit,
  Loader2,
  Info,
} from "lucide-react";
import api from "../lib/api";

const FEATURE_ICONS = {
  schedule: Calendar,
  reservation: Users,
  marketing: Megaphone,
};

const FEATURE_LABELS = {
  schedule: "Dienstplan",
  reservation: "Reservierung",
  marketing: "Marketing",
};

export default function AIAssistant() {
  const { token, hasRole } = useAuth();
  const { toast } = useToast();
  const isAdmin = hasRole("admin");

  const [status, setStatus] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("assistant");

  // Schedule config states
  const [scheduleConfig, setScheduleConfig] = useState(null);
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState(null);

  // Suggestion states
  const [generatingSuggestion, setGeneratingSuggestion] = useState(false);
  const [currentSuggestion, setCurrentSuggestion] = useState(null);
  const [suggestionDialogOpen, setSuggestionDialogOpen] = useState(false);

  // Form states
  const [scheduleWeek, setScheduleWeek] = useState("");
  const [reservationForm, setReservationForm] = useState({
    date: "",
    time: "18:00",
    party_size: 4,
    occasion: "",
    is_regular: false,
  });
  const [marketingForm, setMarketingForm] = useState({
    content_type: "newsletter",
    language: "de",
    target_audience: "newsletter_optin",
  });

  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [statusRes, logsRes, configRes] = await Promise.all([
        api.get("/api/ai/status", { headers }),
        api.get("/api/ai/logs?limit=50", { headers }),
        api.get("/api/ai/schedule/config", { headers }).catch(() => ({ data: null })),
      ]);
      setStatus(statusRes.data);
      setLogs(logsRes.data);
      if (configRes.data) {
        setScheduleConfig(configRes.data);
      }
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Daten konnten nicht geladen werden",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [token, toast]);

  useEffect(() => {
    fetchData();
    // Set default week to current week's Monday
    const today = new Date();
    const monday = new Date(today);
    monday.setDate(today.getDate() - today.getDay() + 1);
    setScheduleWeek(monday.toISOString().split("T")[0]);
    // Set default date to tomorrow
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    setReservationForm((prev) => ({
      ...prev,
      date: tomorrow.toISOString().split("T")[0],
    }));
  }, [fetchData]);

  const toggleFeature = async (feature, enabled) => {
    try {
      await api.patch(
        `/api/ai/settings?feature_${feature}=${enabled}`,
        {},
        { headers }
      );
      toast({
        title: "Erfolg",
        description: `${FEATURE_LABELS[feature]}-KI ${enabled ? "aktiviert" : "deaktiviert"}`,
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Einstellung konnte nicht geändert werden",
        variant: "destructive",
      });
    }
  };

  const toggleGlobal = async (enabled) => {
    try {
      await api.patch(`/api/ai/settings?enabled_global=${enabled}`, {}, { headers });
      toast({
        title: "Erfolg",
        description: `KI-Assistent ${enabled ? "aktiviert" : "deaktiviert"}`,
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Einstellung konnte nicht geändert werden",
        variant: "destructive",
      });
    }
  };

  const openConfigDialog = () => {
    setEditingConfig(JSON.parse(JSON.stringify(scheduleConfig || {})));
    setConfigDialogOpen(true);
  };

  const saveScheduleConfig = async () => {
    try {
      await api.patch("/api/ai/schedule/config", editingConfig, { headers });
      toast({ title: "Erfolg", description: "Konfiguration gespeichert" });
      setConfigDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Konfiguration konnte nicht gespeichert werden",
        variant: "destructive",
      });
    }
  };

  const resetScheduleConfig = async () => {
    if (!window.confirm("Wirklich auf Standardwerte zurücksetzen?")) return;
    try {
      await api.post("/api/ai/schedule/config/reset", {}, { headers });
      toast({ title: "Erfolg", description: "Konfiguration zurückgesetzt" });
      setConfigDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({ title: "Fehler", description: "Zurücksetzen fehlgeschlagen", variant: "destructive" });
    }
  };

  const updateConfigValue = (section, key, value) => {
    setEditingConfig((prev) => ({
      ...prev,
      [section]: {
        ...prev[section],
        [key]: parseInt(value) || value,
      },
    }));
  };

  const requestScheduleSuggestion = async () => {
    setGeneratingSuggestion(true);
    try {
      const res = await api.post(
        "/api/ai/schedule/suggest",
        { week_start: scheduleWeek },
        { headers }
      );
      setCurrentSuggestion({ type: "schedule", ...res.data });
      setSuggestionDialogOpen(true);
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "KI-Vorschlag fehlgeschlagen",
        variant: "destructive",
      });
    } finally {
      setGeneratingSuggestion(false);
    }
  };

  const requestReservationSuggestion = async () => {
    setGeneratingSuggestion(true);
    try {
      const res = await api.post("/api/ai/reservation/suggest", reservationForm, {
        headers,
      });
      setCurrentSuggestion({ type: "reservation", ...res.data });
      setSuggestionDialogOpen(true);
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "KI-Vorschlag fehlgeschlagen",
        variant: "destructive",
      });
    } finally {
      setGeneratingSuggestion(false);
    }
  };

  const requestMarketingSuggestion = async () => {
    setGeneratingSuggestion(true);
    try {
      const res = await api.post("/api/ai/marketing/suggest", marketingForm, {
        headers,
      });
      setCurrentSuggestion({ type: "marketing", ...res.data });
      setSuggestionDialogOpen(true);
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "KI-Vorschlag fehlgeschlagen",
        variant: "destructive",
      });
    } finally {
      setGeneratingSuggestion(false);
    }
  };

  const handleDecision = async (accepted) => {
    if (!currentSuggestion?.log_id) return;
    try {
      await api.post(
        `/api/ai/decision/${currentSuggestion.log_id}`,
        { accepted },
        { headers }
      );
      toast({
        title: accepted ? "Vorschlag akzeptiert" : "Vorschlag abgelehnt",
        description: accepted
          ? "Der Vorschlag wurde als hilfreich markiert."
          : "Der Vorschlag wurde abgelehnt.",
      });
      setSuggestionDialogOpen(false);
      setCurrentSuggestion(null);
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: "Entscheidung konnte nicht gespeichert werden",
        variant: "destructive",
      });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#002f02]" />
      </div>
    );
  }

  const ConfidenceBadge = ({ score }) => {
    const color =
      score >= 0.8
        ? "bg-green-100 text-green-800"
        : score >= 0.6
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-800";
    return (
      <Badge className={color}>
        Konfidenz: {Math.round(score * 100)}%
      </Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#002f02] flex items-center gap-3">
            <Bot className="w-8 h-8" />
            KI-Assistent
          </h1>
          <p className="text-muted-foreground">
            Intelligente Vorschläge für Dienstplan, Reservierungen und Marketing
          </p>
        </div>
        {status?.ai_configured ? (
          <Badge className="bg-green-100 text-green-800">
            <Sparkles className="w-3 h-3 mr-1" />
            KI aktiv
          </Badge>
        ) : (
          <Badge className="bg-red-100 text-red-800">
            <AlertTriangle className="w-3 h-3 mr-1" />
            KI nicht konfiguriert
          </Badge>
        )}
      </div>

      {/* Disclaimer */}
      <Card className="border-yellow-200 bg-yellow-50">
        <CardContent className="p-4 flex items-start gap-3">
          <Info className="w-5 h-5 text-yellow-600 mt-0.5" />
          <div className="text-sm text-yellow-800">
            <strong>Wichtiger Hinweis:</strong> Der KI-Assistent macht nur VORSCHLÄGE.
            Alle Änderungen erfordern Ihre explizite Bestätigung. Die KI kann keine
            Daten ändern oder Aktionen ausführen.
          </div>
        </CardContent>
      </Card>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="assistant">Assistent</TabsTrigger>
          <TabsTrigger value="logs">Protokoll ({logs.length})</TabsTrigger>
          {isAdmin && <TabsTrigger value="settings">Einstellungen</TabsTrigger>}
        </TabsList>

        <TabsContent value="assistant" className="space-y-6">
          {/* Statistics */}
          {status?.statistics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-[#002f02]">
                    {status.statistics.total_suggestions}
                  </p>
                  <p className="text-sm text-muted-foreground">Vorschläge gesamt</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-green-600">
                    {status.statistics.accepted}
                  </p>
                  <p className="text-sm text-muted-foreground">Akzeptiert</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-red-600">
                    {status.statistics.rejected}
                  </p>
                  <p className="text-sm text-muted-foreground">Abgelehnt</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-2xl font-bold text-blue-600">
                    {status.statistics.acceptance_rate}%
                  </p>
                  <p className="text-sm text-muted-foreground">Akzeptanzrate</p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Feature Cards */}
          <div className="grid md:grid-cols-3 gap-6">
            {/* Schedule AI */}
            <Card className={`border-[#002f02]/20 ${!status?.features?.schedule ? "opacity-60" : ""}`}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-[#002f02]" />
                    Dienstplan-KI
                  </div>
                  {isAdmin && scheduleConfig && (
                    <Button variant="ghost" size="sm" onClick={openConfigDialog}>
                      <Settings className="w-4 h-4" />
                    </Button>
                  )}
                </CardTitle>
                <CardDescription>
                  Vorschläge für Schichtverteilung
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Woche ab</Label>
                  <Input
                    type="date"
                    value={scheduleWeek}
                    onChange={(e) => setScheduleWeek(e.target.value)}
                  />
                </div>
                <Button
                  onClick={requestScheduleSuggestion}
                  disabled={!status?.features?.schedule || generatingSuggestion}
                  className="w-full bg-[#002f02] hover:bg-[#003300]"
                >
                  {generatingSuggestion ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Lightbulb className="w-4 h-4 mr-2" />
                  )}
                  Vorschlag generieren
                </Button>
                {scheduleConfig && (
                  <div className="text-xs text-muted-foreground border-t pt-2 mt-2">
                    <p>Konfiguration: Service {scheduleConfig.service?.normal_summer_weekend || "-"} (WE), Küche {scheduleConfig.kitchen?.normal || "-"}</p>
                  </div>
                )}
                {!status?.features?.schedule && (
                  <p className="text-xs text-muted-foreground text-center">
                    Feature deaktiviert
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Reservation AI */}
            <Card className={`border-[#002f02]/20 ${!status?.features?.reservation ? "opacity-60" : ""}`}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="w-5 h-5 text-[#002f02]" />
                  Reservierungs-KI
                </CardTitle>
                <CardDescription>
                  Bereichs- und Zeitvorschläge
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label>Datum</Label>
                    <Input
                      type="date"
                      value={reservationForm.date}
                      onChange={(e) =>
                        setReservationForm({ ...reservationForm, date: e.target.value })
                      }
                    />
                  </div>
                  <div>
                    <Label>Uhrzeit</Label>
                    <Input
                      type="time"
                      value={reservationForm.time}
                      onChange={(e) =>
                        setReservationForm({ ...reservationForm, time: e.target.value })
                      }
                    />
                  </div>
                </div>
                <div>
                  <Label>Personenzahl</Label>
                  <Input
                    type="number"
                    min="1"
                    max="50"
                    value={reservationForm.party_size}
                    onChange={(e) =>
                      setReservationForm({
                        ...reservationForm,
                        party_size: parseInt(e.target.value) || 1,
                      })
                    }
                  />
                </div>
                <Button
                  onClick={requestReservationSuggestion}
                  disabled={!status?.features?.reservation || generatingSuggestion}
                  className="w-full bg-[#002f02] hover:bg-[#003300]"
                >
                  {generatingSuggestion ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Lightbulb className="w-4 h-4 mr-2" />
                  )}
                  Vorschlag generieren
                </Button>
                {!status?.features?.reservation && (
                  <p className="text-xs text-muted-foreground text-center">
                    Feature deaktiviert
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Marketing AI */}
            <Card className={`border-[#002f02]/20 ${!status?.features?.marketing ? "opacity-60" : ""}`}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Megaphone className="w-5 h-5 text-[#002f02]" />
                  Marketing-KI
                </CardTitle>
                <CardDescription>
                  Text-Vorschläge für Newsletter & Social
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label>Typ</Label>
                  <Select
                    value={marketingForm.content_type}
                    onValueChange={(v) =>
                      setMarketingForm({ ...marketingForm, content_type: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="newsletter">Newsletter</SelectItem>
                      <SelectItem value="social">Social Post</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Sprache</Label>
                  <Select
                    value={marketingForm.language}
                    onValueChange={(v) =>
                      setMarketingForm({ ...marketingForm, language: v })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="de">Deutsch</SelectItem>
                      <SelectItem value="en">Englisch</SelectItem>
                      <SelectItem value="pl">Polnisch</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Button
                  onClick={requestMarketingSuggestion}
                  disabled={!status?.features?.marketing || generatingSuggestion}
                  className="w-full bg-[#002f02] hover:bg-[#003300]"
                >
                  {generatingSuggestion ? (
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  ) : (
                    <Lightbulb className="w-4 h-4 mr-2" />
                  )}
                  Vorschlag generieren
                </Button>
                {!status?.features?.marketing && (
                  <p className="text-xs text-muted-foreground text-center">
                    Feature deaktiviert
                  </p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="logs" className="space-y-4">
          {logs.length === 0 ? (
            <Card className="p-8 text-center text-muted-foreground">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Noch keine KI-Vorschläge generiert</p>
            </Card>
          ) : (
            logs.map((log) => {
              const FeatureIcon = FEATURE_ICONS[log.feature] || Bot;
              return (
                <Card key={log.id} className="border-[#002f02]/20">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <div className="p-2 bg-[#002f02]/10 rounded-lg">
                          <FeatureIcon className="w-5 h-5 text-[#002f02]" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {FEATURE_LABELS[log.feature]}
                            </span>
                            <ConfidenceBadge score={log.confidence_score} />
                            {log.accepted === true && (
                              <Badge className="bg-green-100 text-green-800">
                                <ThumbsUp className="w-3 h-3 mr-1" />
                                Akzeptiert
                              </Badge>
                            )}
                            {log.accepted === false && (
                              <Badge className="bg-red-100 text-red-800">
                                <ThumbsDown className="w-3 h-3 mr-1" />
                                Abgelehnt
                              </Badge>
                            )}
                            {log.accepted === null && (
                              <Badge className="bg-gray-100 text-gray-800">
                                <Clock className="w-3 h-3 mr-1" />
                                Ausstehend
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            {new Date(log.created_at).toLocaleString("de-DE")}
                          </p>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </TabsContent>

        {isAdmin && (
          <TabsContent value="settings" className="space-y-6">
            <Card className="border-[#002f02]/20">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="w-5 h-5" />
                  KI-Einstellungen
                </CardTitle>
                <CardDescription>
                  Aktivieren oder deaktivieren Sie KI-Features
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div>
                    <p className="font-medium">KI-Assistent Global</p>
                    <p className="text-sm text-muted-foreground">
                      Master-Schalter für alle KI-Features
                    </p>
                  </div>
                  <Switch
                    checked={status?.enabled_global || false}
                    onCheckedChange={toggleGlobal}
                  />
                </div>

                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Calendar className="w-5 h-5 text-[#002f02]" />
                      <div>
                        <p className="font-medium">Dienstplan-KI</p>
                        <p className="text-sm text-muted-foreground">
                          Vorschläge für Schichtverteilung
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={status?.features?.schedule || false}
                      onCheckedChange={(v) => toggleFeature("schedule", v)}
                      disabled={!status?.enabled_global}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Users className="w-5 h-5 text-[#002f02]" />
                      <div>
                        <p className="font-medium">Reservierungs-KI</p>
                        <p className="text-sm text-muted-foreground">
                          Bereichs- und Zeitvorschläge
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={status?.features?.reservation || false}
                      onCheckedChange={(v) => toggleFeature("reservation", v)}
                      disabled={!status?.enabled_global}
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Megaphone className="w-5 h-5 text-[#002f02]" />
                      <div>
                        <p className="font-medium">Marketing-KI</p>
                        <p className="text-sm text-muted-foreground">
                          Text-Vorschläge für Newsletter & Social
                        </p>
                      </div>
                    </div>
                    <Switch
                      checked={status?.features?.marketing || false}
                      onCheckedChange={(v) => toggleFeature("marketing", v)}
                      disabled={!status?.enabled_global}
                    />
                  </div>
                </div>

                <div className="p-4 bg-yellow-50 rounded-lg text-sm text-yellow-800">
                  <AlertTriangle className="w-4 h-4 inline mr-2" />
                  <strong>Hinweis:</strong> Die KI kann niemals automatisch Daten ändern.
                  Alle Vorschläge erfordern menschliche Bestätigung.
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>

      {/* Suggestion Dialog */}
      <Dialog open={suggestionDialogOpen} onOpenChange={setSuggestionDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#002f02]" />
              KI-Vorschlag: {currentSuggestion && FEATURE_LABELS[currentSuggestion.type]}
            </DialogTitle>
          </DialogHeader>
          {currentSuggestion && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <ConfidenceBadge score={currentSuggestion.confidence_score} />
                <Badge variant="outline">Nur Vorschlag</Badge>
              </div>

              <Card className="bg-[#002f02]/5 border-[#002f02]/20">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Vorschlag</CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="whitespace-pre-wrap text-sm bg-white p-3 rounded border">
                    {JSON.stringify(currentSuggestion.suggestion, null, 2)}
                  </pre>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Lightbulb className="w-4 h-4" />
                    Begründung
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm">{currentSuggestion.reasoning}</p>
                </CardContent>
              </Card>

              <div className="p-4 bg-yellow-50 rounded-lg text-sm text-yellow-800">
                <AlertTriangle className="w-4 h-4 inline mr-2" />
                {currentSuggestion.disclaimer}
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => handleDecision(false)}
              className="text-red-600"
            >
              <ThumbsDown className="w-4 h-4 mr-2" />
              Ablehnen
            </Button>
            <Button
              onClick={() => handleDecision(true)}
              className="bg-[#002f02] hover:bg-[#003300]"
            >
              <ThumbsUp className="w-4 h-4 mr-2" />
              Als hilfreich markieren
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Schedule Config Dialog */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5 text-[#002f02]" />
              Dienstplan-KI Konfiguration
            </DialogTitle>
          </DialogHeader>
          {editingConfig && (
            <div className="space-y-6">
              {/* Service Personalbedarf */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Personalbedarf - Service</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-xs">Sommer Werktag</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.normal_summer_weekday || 4}
                      onChange={(e) => updateConfigValue("service", "normal_summer_weekday", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Sommer Wochenende</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.normal_summer_weekend || 5}
                      onChange={(e) => updateConfigValue("service", "normal_summer_weekend", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Winter Werktag</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.normal_winter_weekday || 3}
                      onChange={(e) => updateConfigValue("service", "normal_winter_weekday", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Winter Wochenende</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.normal_winter_weekend || 4}
                      onChange={(e) => updateConfigValue("service", "normal_winter_weekend", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Kulinarische Aktion</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.culinary_event || 5}
                      onChange={(e) => updateConfigValue("service", "culinary_event", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Kultur Frühschicht</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.culture_early_shift || 3}
                      onChange={(e) => updateConfigValue("service", "culture_early_shift", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Kultur Abendschicht</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.culture_evening_shift || 5}
                      onChange={(e) => updateConfigValue("service", "culture_evening_shift", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Feiertag</Label>
                    <Input
                      type="number"
                      min="1"
                      max="20"
                      value={editingConfig.service?.holiday || 6}
                      onChange={(e) => updateConfigValue("service", "holiday", e.target.value)}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Kitchen Personalbedarf */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Personalbedarf - Küche</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-xs">Normal</Label>
                    <Input
                      type="number"
                      min="1"
                      max="15"
                      value={editingConfig.kitchen?.normal || 3}
                      onChange={(e) => updateConfigValue("kitchen", "normal", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Kulinarische Aktion</Label>
                    <Input
                      type="number"
                      min="1"
                      max="15"
                      value={editingConfig.kitchen?.culinary_event || 4}
                      onChange={(e) => updateConfigValue("kitchen", "culinary_event", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Kultur</Label>
                    <Input
                      type="number"
                      min="1"
                      max="15"
                      value={editingConfig.kitchen?.culture || 3}
                      onChange={(e) => updateConfigValue("kitchen", "culture", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Feiertag</Label>
                    <Input
                      type="number"
                      min="1"
                      max="15"
                      value={editingConfig.kitchen?.holiday || 4}
                      onChange={(e) => updateConfigValue("kitchen", "holiday", e.target.value)}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Work Rules */}
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Arbeitszeit-Regeln</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <Label className="text-xs">Max. Tage am Stück</Label>
                    <Input
                      type="number"
                      min="3"
                      max="7"
                      value={editingConfig.work_rules?.max_days_consecutive || 5}
                      onChange={(e) => updateConfigValue("work_rules", "max_days_consecutive", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Min. freie Tage/Woche</Label>
                    <Input
                      type="number"
                      min="1"
                      max="3"
                      value={editingConfig.work_rules?.min_free_days_per_week || 2}
                      onChange={(e) => updateConfigValue("work_rules", "min_free_days_per_week", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Max. Stunden/Tag</Label>
                    <Input
                      type="number"
                      min="6"
                      max="12"
                      value={editingConfig.work_rules?.max_hours_per_day || 10}
                      onChange={(e) => updateConfigValue("work_rules", "max_hours_per_day", e.target.value)}
                    />
                  </div>
                  <div>
                    <Label className="text-xs">Minijob-Verhältnis</Label>
                    <Input
                      type="number"
                      min="0.5"
                      max="2"
                      step="0.1"
                      value={editingConfig.work_rules?.minijob_ratio || 1.0}
                      onChange={(e) => updateConfigValue("work_rules", "minijob_ratio", parseFloat(e.target.value))}
                    />
                  </div>
                </CardContent>
              </Card>

              <div className="p-4 bg-yellow-50 rounded-lg text-sm text-yellow-800">
                <Info className="w-4 h-4 inline mr-2" />
                Diese Werte werden von der KI als Basis für Dienstplan-Vorschläge verwendet.
                Der Schichtleiter ist in den Zahlen NICHT enthalten.
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={resetScheduleConfig} className="text-red-600">
              Zurücksetzen
            </Button>
            <Button variant="outline" onClick={() => setConfigDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={saveScheduleConfig} className="bg-[#002f02] hover:bg-[#003300]">
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
