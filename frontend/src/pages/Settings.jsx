import React, { useState, useEffect } from "react";
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
import { toast } from "sonner";
import {
  Settings as SettingsIcon,
  Bell,
  Clock,
  UserX,
  Mail,
  MessageCircle,
  Plus,
  Trash2,
  Loader2,
  Save,
  AlertTriangle,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const Settings = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({});
  const [reminderRules, setReminderRules] = useState([]);
  const [showRuleDialog, setShowRuleDialog] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [ruleForm, setRuleForm] = useState({
    name: "",
    hours_before: 24,
    channel: "email",
    is_active: true,
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [settingsRes, rulesRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/settings`, { headers }),
        axios.get(`${BACKEND_URL}/api/reminder-rules`, { headers }),
      ]);
      
      // Convert settings array to object
      const settingsObj = {};
      settingsRes.data.forEach(s => {
        settingsObj[s.key] = s.value;
      });
      setSettings(settingsObj);
      setReminderRules(rulesRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Einstellungen");
    } finally {
      setLoading(false);
    }
  };

  const saveSetting = async (key, value) => {
    try {
      await axios.post(`${BACKEND_URL}/api/settings`, { key, value: String(value) }, { headers });
      setSettings(prev => ({ ...prev, [key]: String(value) }));
      toast.success("Einstellung gespeichert");
    } catch (err) {
      toast.error("Fehler beim Speichern");
    }
  };

  const handleSaveRule = async () => {
    setSaving(true);
    try {
      if (editingRule) {
        await axios.patch(`${BACKEND_URL}/api/reminder-rules/${editingRule.id}`, ruleForm, { headers });
        toast.success("Regel aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/reminder-rules`, ruleForm, { headers });
        toast.success("Regel erstellt");
      }
      setShowRuleDialog(false);
      setEditingRule(null);
      setRuleForm({ name: "", hours_before: 24, channel: "email", is_active: true });
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm("Regel wirklich löschen?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/reminder-rules/${ruleId}`, { headers });
      toast.success("Regel gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const openEditRule = (rule) => {
    setEditingRule(rule);
    setRuleForm({
      name: rule.name,
      hours_before: rule.hours_before,
      channel: rule.channel,
      is_active: rule.is_active,
    });
    setShowRuleDialog(true);
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        <div>
          <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
            Einstellungen
          </h1>
          <p className="text-muted-foreground mt-1">
            Konfiguration für Reminders, No-Show-Regeln und mehr
          </p>
        </div>

        <Tabs defaultValue="reminders" className="space-y-6">
          <TabsList className="bg-card border">
            <TabsTrigger value="reminders" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Bell className="h-4 w-4 mr-2" />
              Erinnerungen
            </TabsTrigger>
            <TabsTrigger value="noshow" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <UserX className="h-4 w-4 mr-2" />
              No-Show Regeln
            </TabsTrigger>
            <TabsTrigger value="booking" className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground">
              <Clock className="h-4 w-4 mr-2" />
              Stornierung
            </TabsTrigger>
          </TabsList>

          {/* Reminder Rules Tab */}
          <TabsContent value="reminders" className="space-y-4">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle>Erinnerungs-Regeln</CardTitle>
                  <CardDescription>
                    Automatische Erinnerungen für bestätigte Reservierungen
                  </CardDescription>
                </div>
                <Button
                  onClick={() => {
                    setEditingRule(null);
                    setRuleForm({ name: "", hours_before: 24, channel: "email", is_active: true });
                    setShowRuleDialog(true);
                  }}
                  className="rounded-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Neue Regel
                </Button>
              </CardHeader>
              <CardContent>
                {reminderRules.length === 0 ? (
                  <p className="text-muted-foreground text-center py-8">
                    Keine Erinnerungs-Regeln konfiguriert
                  </p>
                ) : (
                  <div className="space-y-3">
                    {reminderRules.map((rule) => (
                      <div
                        key={rule.id}
                        className="flex items-center justify-between p-4 bg-muted rounded-lg"
                      >
                        <div className="flex items-center gap-4">
                          <div className={`p-2 rounded-full ${rule.channel === 'email' ? 'bg-blue-100' : rule.channel === 'whatsapp' ? 'bg-green-100' : 'bg-purple-100'}`}>
                            {rule.channel === 'email' ? (
                              <Mail className="h-5 w-5 text-blue-600" />
                            ) : rule.channel === 'whatsapp' ? (
                              <MessageCircle className="h-5 w-5 text-green-600" />
                            ) : (
                              <Bell className="h-5 w-5 text-purple-600" />
                            )}
                          </div>
                          <div>
                            <p className="font-medium">{rule.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {rule.hours_before}h vorher • {rule.channel === 'email' ? 'E-Mail' : rule.channel === 'whatsapp' ? 'WhatsApp' : 'Beide'}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <Badge variant={rule.is_active ? "default" : "secondary"}>
                            {rule.is_active ? "Aktiv" : "Inaktiv"}
                          </Badge>
                          <Button variant="ghost" size="sm" onClick={() => openEditRule(rule)}>
                            Bearbeiten
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => handleDeleteRule(rule.id)}>
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>WhatsApp-Hinweis</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-start gap-3 p-4 bg-green-50 rounded-lg border border-green-200">
                  <MessageCircle className="h-5 w-5 text-green-600 mt-0.5" />
                  <div>
                    <p className="font-medium text-green-800">WhatsApp Deep-Links</p>
                    <p className="text-sm text-green-700 mt-1">
                      WhatsApp-Erinnerungen werden als Deep-Links generiert. Das Service-Personal 
                      kann mit einem Klick WhatsApp öffnen und die vorausgefüllte Nachricht senden.
                      Keine WhatsApp Business API erforderlich.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* No-Show Rules Tab */}
          <TabsContent value="noshow" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>No-Show Schwellenwerte</CardTitle>
                <CardDescription>
                  Automatische Konsequenzen bei wiederholten No-Shows
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                      Greylist ab X No-Shows
                    </Label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        min="1"
                        max="10"
                        value={settings.no_show_greylist_threshold || "2"}
                        onChange={(e) => setSettings(prev => ({ ...prev, no_show_greylist_threshold: e.target.value }))}
                        className="w-24"
                      />
                      <Button 
                        variant="outline" 
                        onClick={() => saveSetting("no_show_greylist_threshold", settings.no_show_greylist_threshold)}
                      >
                        <Save className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Gäste erhalten einen Warnhinweis, Bestätigungspflicht kann aktiviert werden
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <UserX className="h-4 w-4 text-red-500" />
                      Blacklist ab X No-Shows
                    </Label>
                    <div className="flex gap-2">
                      <Input
                        type="number"
                        min="1"
                        max="20"
                        value={settings.no_show_blacklist_threshold || "4"}
                        onChange={(e) => setSettings(prev => ({ ...prev, no_show_blacklist_threshold: e.target.value }))}
                        className="w-24"
                      />
                      <Button 
                        variant="outline" 
                        onClick={() => saveSetting("no_show_blacklist_threshold", settings.no_show_blacklist_threshold)}
                      >
                        <Save className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Online-Reservierung blockiert, deutlicher Warnhinweis im Terminal
                    </p>
                  </div>
                </div>

                <div className="border-t pt-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Greylist-Gäste müssen bestätigen</Label>
                      <p className="text-sm text-muted-foreground">
                        Gäste auf der Greylist müssen ihre Reservierung per Link bestätigen
                      </p>
                    </div>
                    <Switch
                      checked={settings.greylist_requires_confirmation === "true"}
                      onCheckedChange={(checked) => saveSetting("greylist_requires_confirmation", checked)}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Konsequenzen-Übersicht</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className="bg-yellow-100 text-yellow-800">Greylist</Badge>
                    </div>
                    <ul className="text-sm text-yellow-800 space-y-1">
                      <li>• Gelber Marker im Service-Terminal</li>
                      <li>• Warnhinweis bei neuen Reservierungen</li>
                      <li>• Optional: Bestätigungspflicht</li>
                      <li>• Verstärkte Erinnerungen</li>
                    </ul>
                  </div>
                  <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge className="bg-red-100 text-red-800">Blacklist</Badge>
                    </div>
                    <ul className="text-sm text-red-800 space-y-1">
                      <li>• Roter Marker im Service-Terminal</li>
                      <li>• Online-Reservierung blockiert</li>
                      <li>• Deutliche Warnung für Personal</li>
                      <li>• Nur telefonisch möglich</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Booking/Cancellation Tab */}
          <TabsContent value="booking" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Stornierungsfrist</CardTitle>
                <CardDescription>
                  Bis wann können Gäste online stornieren?
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Stornierung möglich bis X Stunden vorher</Label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      min="1"
                      max="168"
                      value={settings.cancellation_deadline_hours || "24"}
                      onChange={(e) => setSettings(prev => ({ ...prev, cancellation_deadline_hours: e.target.value }))}
                      className="w-24"
                    />
                    <span className="flex items-center text-muted-foreground">Stunden</span>
                    <Button 
                      variant="outline" 
                      onClick={() => saveSetting("cancellation_deadline_hours", settings.cancellation_deadline_hours)}
                    >
                      <Save className="h-4 w-4" />
                    </Button>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Nach Ablauf der Frist wird der Stornierungslink deaktiviert
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Gast-Bestätigung</CardTitle>
                <CardDescription>
                  Gäste müssen ihre Reservierung aktiv bestätigen
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <Label>Bestätigung für alle Reservierungen</Label>
                    <p className="text-sm text-muted-foreground">
                      Jeder Gast muss seine Reservierung per E-Mail-Link bestätigen
                    </p>
                  </div>
                  <Switch
                    checked={settings.require_guest_confirmation === "true"}
                    onCheckedChange={(checked) => saveSetting("require_guest_confirmation", checked)}
                  />
                </div>
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm">
                    <strong>Hinweis:</strong> Unbestätigte Reservierungen werden im Service-Terminal 
                    mit einem Warnsymbol markiert.
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Restaurant-Name</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    value={settings.restaurant_name || ""}
                    onChange={(e) => setSettings(prev => ({ ...prev, restaurant_name: e.target.value }))}
                    placeholder="Restaurant-Name"
                    className="max-w-md"
                  />
                  <Button 
                    variant="outline" 
                    onClick={() => saveSetting("restaurant_name", settings.restaurant_name)}
                  >
                    <Save className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>

      {/* Rule Dialog */}
      <Dialog open={showRuleDialog} onOpenChange={setShowRuleDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editingRule ? "Regel bearbeiten" : "Neue Erinnerungs-Regel"}
            </DialogTitle>
            <DialogDescription>
              Konfigurieren Sie, wann und wie Erinnerungen gesendet werden
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={ruleForm.name}
                onChange={(e) => setRuleForm(prev => ({ ...prev, name: e.target.value }))}
                placeholder="z.B. 24h E-Mail Erinnerung"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Stunden vorher</Label>
                <Input
                  type="number"
                  min="1"
                  max="168"
                  value={ruleForm.hours_before}
                  onChange={(e) => setRuleForm(prev => ({ ...prev, hours_before: parseInt(e.target.value) || 24 }))}
                />
              </div>
              <div className="space-y-2">
                <Label>Kanal</Label>
                <Select
                  value={ruleForm.channel}
                  onValueChange={(v) => setRuleForm(prev => ({ ...prev, channel: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">E-Mail</SelectItem>
                    <SelectItem value="whatsapp">WhatsApp (Deep-Link)</SelectItem>
                    <SelectItem value="both">Beide</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <Label>Regel aktiv</Label>
              <Switch
                checked={ruleForm.is_active}
                onCheckedChange={(checked) => setRuleForm(prev => ({ ...prev, is_active: checked }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRuleDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSaveRule} disabled={saving || !ruleForm.name}>
              {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Settings;
