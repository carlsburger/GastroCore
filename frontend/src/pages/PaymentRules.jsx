import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  CreditCard,
  Plus,
  RefreshCw,
  Loader2,
  Edit,
  Trash2,
  Euro,
  Users,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  XCircle,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const TRIGGER_CONFIG = {
  event: { label: "Event", icon: Calendar, description: "Bei Event-Buchungen" },
  holiday: { label: "Feiertag", icon: Calendar, description: "An Feiertagen" },
  group_size: { label: "Gruppengröße", icon: Users, description: "Ab X Personen" },
  greylist: { label: "Greylist", icon: AlertTriangle, description: "Für Greylist-Gäste" },
};

const PAYMENT_TYPE_CONFIG = {
  deposit_per_person: { label: "Anzahlung pro Person", description: "X € pro Gast" },
  fixed_deposit: { label: "Fixe Anzahlung", description: "Fester Betrag" },
  full_payment: { label: "Komplettzahlung", description: "Voller Betrag" },
};

export const PaymentRules = () => {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    name: "",
    trigger: "group_size",
    trigger_value: 8,
    payment_type: "deposit_per_person",
    amount: 10,
    deadline_hours: 24,
    is_active: true,
    description: "",
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchRules();
  }, []);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${BACKEND_URL}/api/payments/rules`, { headers });
      setRules(response.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Regeln");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      trigger: "group_size",
      trigger_value: 8,
      payment_type: "deposit_per_person",
      amount: 10,
      deadline_hours: 24,
      is_active: true,
      description: "",
    });
    setEditingRule(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const data = { ...formData };
      // Don't send trigger_value for non-group triggers
      if (data.trigger !== "group_size") {
        data.trigger_value = null;
      }
      
      if (editingRule) {
        await axios.patch(`${BACKEND_URL}/api/payments/rules/${editingRule.id}`, data, { headers });
        toast.success("Regel aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/payments/rules`, data, { headers });
        toast.success("Regel erstellt");
      }
      setShowDialog(false);
      resetForm();
      fetchRules();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (rule) => {
    setEditingRule(rule);
    setFormData({
      name: rule.name || "",
      trigger: rule.trigger || "group_size",
      trigger_value: rule.trigger_value || 8,
      payment_type: rule.payment_type || "deposit_per_person",
      amount: rule.amount || 10,
      deadline_hours: rule.deadline_hours || 24,
      is_active: rule.is_active ?? true,
      description: rule.description || "",
    });
    setShowDialog(true);
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm("Regel wirklich löschen?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/payments/rules/${ruleId}`, { headers });
      toast.success("Regel gelöscht");
      fetchRules();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const handleSeedRules = async () => {
    try {
      const response = await axios.post(`${BACKEND_URL}/api/seed-payment-rules`, {}, { headers });
      toast.success(response.data.message);
      fetchRules();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Zahlungsregeln
            </h1>
            <p className="text-muted-foreground mt-1">
              Konfigurieren Sie, wann Zahlungen erforderlich sind
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchRules} className="rounded-full">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            {rules.length === 0 && (
              <Button variant="outline" onClick={handleSeedRules} className="rounded-full">
                Standard-Regeln laden
              </Button>
            )}
            <Button
              onClick={() => {
                resetForm();
                setShowDialog(true);
              }}
              className="rounded-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neue Regel
            </Button>
          </div>
        </div>

        {/* Info Card */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <CreditCard className="h-5 w-5 text-primary mt-0.5" />
              <div>
                <p className="font-medium">Zahlungspflicht automatisieren</p>
                <p className="text-sm text-muted-foreground">
                  Regeln bestimmen, wann Gäste eine Anzahlung oder Vorauszahlung leisten müssen.
                  Bei Events, großen Gruppen oder Greylist-Gästen kann automatisch eine Zahlung angefordert werden.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Rules List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
          </div>
        ) : rules.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <CreditCard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground mb-4">Keine Zahlungsregeln konfiguriert</p>
              <Button onClick={handleSeedRules}>
                Standard-Regeln erstellen
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {rules.map((rule) => {
              const triggerConfig = TRIGGER_CONFIG[rule.trigger] || TRIGGER_CONFIG.group_size;
              const TriggerIcon = triggerConfig.icon;
              const paymentTypeConfig = PAYMENT_TYPE_CONFIG[rule.payment_type] || PAYMENT_TYPE_CONFIG.deposit_per_person;
              
              return (
                <Card key={rule.id} className={`${!rule.is_active ? "opacity-50" : ""}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="p-3 rounded-full bg-primary/10">
                          <TriggerIcon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold">{rule.name}</p>
                            {!rule.is_active && (
                              <Badge variant="secondary">Inaktiv</Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {triggerConfig.label}
                            {rule.trigger === "group_size" && ` ab ${rule.trigger_value} Personen`}
                            {" • "}
                            {paymentTypeConfig.label}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-xl font-bold text-primary">
                            {rule.amount?.toFixed(2)} €
                            {rule.payment_type === "deposit_per_person" && <span className="text-sm font-normal text-muted-foreground"> /Pers.</span>}
                          </p>
                          {rule.deadline_hours > 0 && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1 justify-end">
                              <Clock className="h-3 w-3" />
                              {rule.deadline_hours}h vorher
                            </p>
                          )}
                        </div>
                        
                        <div className="flex gap-1">
                          <Button size="sm" variant="ghost" onClick={() => handleEdit(rule)}>
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleDelete(rule.id)}>
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                    {rule.description && (
                      <p className="text-sm text-muted-foreground mt-2 ml-16">
                        {rule.description}
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editingRule ? "Regel bearbeiten" : "Neue Zahlungsregel"}
            </DialogTitle>
            <DialogDescription>
              Definieren Sie, wann eine Zahlung erforderlich ist
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="z.B. Großgruppen-Anzahlung"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Auslöser</Label>
                  <Select
                    value={formData.trigger}
                    onValueChange={(v) => setFormData({ ...formData, trigger: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(TRIGGER_CONFIG).map(([key, config]) => (
                        <SelectItem key={key} value={key}>
                          {config.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                {formData.trigger === "group_size" && (
                  <div className="space-y-2">
                    <Label>Ab Personen</Label>
                    <Input
                      type="number"
                      min="2"
                      value={formData.trigger_value}
                      onChange={(e) => setFormData({ ...formData, trigger_value: parseInt(e.target.value) || 2 })}
                    />
                  </div>
                )}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Zahlungsart</Label>
                  <Select
                    value={formData.payment_type}
                    onValueChange={(v) => setFormData({ ...formData, payment_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(PAYMENT_TYPE_CONFIG).map(([key, config]) => (
                        <SelectItem key={key} value={key}>
                          {config.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                
                <div className="space-y-2">
                  <Label>Betrag (€)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) || 0 })}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Frist (Stunden vor Reservierung)</Label>
                <Input
                  type="number"
                  min="0"
                  value={formData.deadline_hours}
                  onChange={(e) => setFormData({ ...formData, deadline_hours: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  0 = sofort bei Buchung
                </p>
              </div>
              
              <div className="space-y-2">
                <Label>Beschreibung</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Optionale Beschreibung der Regel"
                  rows={2}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <Label>Regel aktiv</Label>
                  <p className="text-sm text-muted-foreground">
                    Regel wird bei Buchungen angewendet
                  </p>
                </div>
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(v) => setFormData({ ...formData, is_active: v })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting || !formData.name}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                {editingRule ? "Speichern" : "Erstellen"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default PaymentRules;
