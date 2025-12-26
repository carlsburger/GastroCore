import React, { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "./ui/dialog";
import { Switch } from "./ui/switch";
import { Textarea } from "./ui/textarea";
import { toast } from "sonner";
import { Euro, Plus, Trash2, Loader2, CreditCard, Percent, AlertCircle, CheckCircle } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Payment Policy Mode Labels
const PAYMENT_MODE_LABELS = {
  none: "Keine Zahlung",
  deposit: "Anzahlung",
  full: "Volle Zahlung",
};

// Deposit Type Labels  
const DEPOSIT_TYPE_LABELS = {
  fixed_per_person: "Fester Betrag pro Person",
  percent_of_total: "Prozent vom Gesamtpreis",
};

export const EventPricingDialog = ({ event, open, onOpenChange, onSaved }) => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("pricing"); // "pricing" | "payment"
  
  // Pricing State
  const [pricingMode, setPricingMode] = useState("single");
  const [singlePrice, setSinglePrice] = useState(0);
  const [variants, setVariants] = useState([]);
  
  // Payment Policy State
  const [paymentMode, setPaymentMode] = useState("none");
  const [paymentRequired, setPaymentRequired] = useState(false);
  const [depositValue, setDepositValue] = useState(10);
  const [depositType, setDepositType] = useState("fixed_per_person");
  const [paymentWindow, setPaymentWindow] = useState(30);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // Initialize from event data
  useEffect(() => {
    if (event && open) {
      const pricing = event.event_pricing || {};
      const policy = event.payment_policy || {};
      
      // Pricing
      setPricingMode(pricing.pricing_mode || "single");
      setSinglePrice(pricing.single_price_per_person || event.ticket_price || event.price_per_person || 0);
      setVariants(pricing.variants || []);
      
      // Payment Policy
      const category = event.content_category;
      const defaultMode = category === "VERANSTALTUNG" ? "full" : 
                         category === "AKTION_MENUE" ? "deposit" : "none";
      setPaymentMode(policy.mode || defaultMode);
      setPaymentRequired(policy.required ?? (category !== "AKTION"));
      setDepositValue(policy.deposit_value || 10);
      setDepositType(policy.deposit_type || "fixed_per_person");
      setPaymentWindow(policy.payment_window_minutes || 30);
    }
  }, [event, open]);

  const addVariant = () => {
    setVariants([
      ...variants,
      { code: `var_${variants.length + 1}`, name: "", price_per_person: 0, description: "" }
    ]);
  };

  const updateVariant = (index, field, value) => {
    const updated = [...variants];
    updated[index] = { ...updated[index], [field]: value };
    setVariants(updated);
  };

  const removeVariant = (index) => {
    setVariants(variants.filter((_, i) => i !== index));
  };

  const savePricing = async () => {
    setLoading(true);
    try {
      // Validate
      if (pricingMode === "single" && (!singlePrice || singlePrice <= 0)) {
        toast.error("Bitte geben Sie einen Preis pro Person ein");
        setLoading(false);
        return;
      }
      if (pricingMode === "variants" && variants.length === 0) {
        toast.error("Bitte fügen Sie mindestens eine Variante hinzu");
        setLoading(false);
        return;
      }

      const pricingData = {
        pricing_mode: pricingMode,
        currency: "EUR",
        single_price_per_person: pricingMode === "single" ? parseFloat(singlePrice) : null,
        variants: pricingMode === "variants" ? variants.map(v => ({
          code: v.code,
          name: v.name,
          price_per_person: parseFloat(v.price_per_person),
          description: v.description || null
        })) : null
      };

      await axios.patch(`${BACKEND_URL}/api/events/${event.id}/pricing`, pricingData, { headers });
      toast.success("Preise gespeichert");
      
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setLoading(false);
    }
  };

  const savePaymentPolicy = async () => {
    setLoading(true);
    try {
      const policyData = {
        mode: paymentMode,
        basis: "per_person",
        required: paymentRequired,
        deposit_value: paymentMode === "deposit" ? parseFloat(depositValue) : null,
        deposit_type: paymentMode === "deposit" ? depositType : null,
        payment_window_minutes: paymentWindow,
        hold_reservation_until_paid: paymentRequired
      };

      await axios.patch(`${BACKEND_URL}/api/events/${event.id}/payment-policy`, policyData, { headers });
      toast.success("Zahlungsrichtlinie gespeichert");
      
      if (onSaved) onSaved();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setLoading(false);
    }
  };

  if (!event) return null;

  const category = event.content_category;
  const isKultur = category === "VERANSTALTUNG";
  const isMenueAktion = category === "AKTION_MENUE";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl flex items-center gap-2">
            <Euro className="h-6 w-6" />
            Preise & Zahlung: {event.title}
          </DialogTitle>
          <DialogDescription>
            {isKultur && <Badge className="bg-purple-100 text-purple-800">Kultur - Volle Zahlung erforderlich</Badge>}
            {isMenueAktion && <Badge className="bg-emerald-100 text-emerald-800">Menü-Aktion - Anzahlung erforderlich</Badge>}
            {!isKultur && !isMenueAktion && <Badge className="bg-amber-100 text-amber-800">Aktion - Zahlung optional</Badge>}
          </DialogDescription>
        </DialogHeader>

        {/* Tabs */}
        <div className="flex border-b mb-4">
          <button
            className={`px-4 py-2 font-medium ${activeTab === "pricing" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}
            onClick={() => setActiveTab("pricing")}
          >
            💰 Preise
          </button>
          <button
            className={`px-4 py-2 font-medium ${activeTab === "payment" ? "border-b-2 border-primary text-primary" : "text-muted-foreground"}`}
            onClick={() => setActiveTab("payment")}
          >
            💳 Zahlung
          </button>
        </div>

        {/* PRICING TAB */}
        {activeTab === "pricing" && (
          <div className="space-y-6">
            {/* Pricing Mode Selection */}
            <div className="space-y-2">
              <Label>Preismodus</Label>
              <Select value={pricingMode} onValueChange={setPricingMode}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="single">Einzelpreis pro Person</SelectItem>
                  <SelectItem value="variants">Varianten (z.B. Menü-Optionen)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Single Price */}
            {pricingMode === "single" && (
              <div className="space-y-2">
                <Label>Preis pro Person (€)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min="0"
                    step="0.10"
                    value={singlePrice}
                    onChange={(e) => setSinglePrice(e.target.value)}
                    className="w-32"
                  />
                  <span className="text-muted-foreground">EUR</span>
                </div>
              </div>
            )}

            {/* Variants */}
            {pricingMode === "variants" && (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Label>Preis-Varianten</Label>
                  <Button size="sm" variant="outline" onClick={addVariant}>
                    <Plus className="h-4 w-4 mr-1" /> Variante
                  </Button>
                </div>

                {variants.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground border-2 border-dashed rounded-lg">
                    <p>Noch keine Varianten</p>
                    <Button size="sm" className="mt-2" onClick={addVariant}>
                      <Plus className="h-4 w-4 mr-1" /> Erste Variante hinzufügen
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {variants.map((v, idx) => (
                      <Card key={idx} className="p-3">
                        <div className="grid grid-cols-12 gap-2 items-end">
                          <div className="col-span-3">
                            <Label className="text-xs">Code</Label>
                            <Input
                              value={v.code}
                              onChange={(e) => updateVariant(idx, "code", e.target.value)}
                              placeholder="menu_3g"
                            />
                          </div>
                          <div className="col-span-4">
                            <Label className="text-xs">Name</Label>
                            <Input
                              value={v.name}
                              onChange={(e) => updateVariant(idx, "name", e.target.value)}
                              placeholder="3-Gänge-Menü"
                            />
                          </div>
                          <div className="col-span-3">
                            <Label className="text-xs">Preis (€)</Label>
                            <Input
                              type="number"
                              min="0"
                              step="0.10"
                              value={v.price_per_person}
                              onChange={(e) => updateVariant(idx, "price_per_person", e.target.value)}
                            />
                          </div>
                          <div className="col-span-2 flex justify-end">
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red-600"
                              onClick={() => removeVariant(idx)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="mt-2">
                          <Label className="text-xs">Beschreibung (optional)</Label>
                          <Input
                            value={v.description || ""}
                            onChange={(e) => updateVariant(idx, "description", e.target.value)}
                            placeholder="z.B. Suppe + Hauptgang + Dessert"
                          />
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}

            <DialogFooter>
              <Button onClick={savePricing} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                Preise speichern
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* PAYMENT TAB */}
        {activeTab === "payment" && (
          <div className="space-y-6">
            {/* Info Box für Kategorie-Regeln */}
            {isKultur && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-purple-600 mt-0.5" />
                <div>
                  <p className="font-medium text-purple-900">Kulturveranstaltung</p>
                  <p className="text-sm text-purple-700">Volle Zahlung ist erforderlich. Der Eintrittspreis muss vollständig bezahlt werden.</p>
                </div>
              </div>
            )}
            {isMenueAktion && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-4 flex items-start gap-3">
                <AlertCircle className="h-5 w-5 text-emerald-600 mt-0.5" />
                <div>
                  <p className="font-medium text-emerald-900">Menü-Aktion</p>
                  <p className="text-sm text-emerald-700">Eine Anzahlung ist erforderlich, um die Reservierung zu bestätigen.</p>
                </div>
              </div>
            )}

            {/* Payment Mode */}
            <div className="space-y-2">
              <Label>Zahlungsmodus</Label>
              <Select 
                value={paymentMode} 
                onValueChange={setPaymentMode}
                disabled={isKultur}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {!isKultur && !isMenueAktion && <SelectItem value="none">Keine Zahlung erforderlich</SelectItem>}
                  {!isKultur && <SelectItem value="deposit">Anzahlung</SelectItem>}
                  <SelectItem value="full">Volle Zahlung</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Payment Required Toggle (nur für Aktionen) */}
            {!isKultur && !isMenueAktion && (
              <div className="flex items-center justify-between py-2">
                <div>
                  <Label>Zahlung erforderlich</Label>
                  <p className="text-sm text-muted-foreground">Reservierung erst nach Zahlung bestätigt</p>
                </div>
                <Switch
                  checked={paymentRequired}
                  onCheckedChange={setPaymentRequired}
                  disabled={paymentMode === "none"}
                />
              </div>
            )}

            {/* Deposit Settings */}
            {paymentMode === "deposit" && (
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <CreditCard className="h-5 w-5" /> Anzahlung
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Anzahlungstyp</Label>
                    <Select value={depositType} onValueChange={setDepositType}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="fixed_per_person">Fester Betrag pro Person</SelectItem>
                        <SelectItem value="percent_of_total">Prozent vom Gesamtpreis</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>
                      {depositType === "fixed_per_person" ? "Betrag pro Person (€)" : "Prozent"}
                    </Label>
                    <div className="flex items-center gap-2">
                      <Input
                        type="number"
                        min="0"
                        step={depositType === "percent_of_total" ? "1" : "0.50"}
                        value={depositValue}
                        onChange={(e) => setDepositValue(e.target.value)}
                        className="w-32"
                      />
                      <span className="text-muted-foreground">
                        {depositType === "fixed_per_person" ? "EUR" : "%"}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {depositType === "fixed_per_person" 
                        ? `Bei 4 Personen: ${(parseFloat(depositValue) || 0) * 4} € Anzahlung`
                        : `Bei 100 € Gesamtpreis: ${parseFloat(depositValue) || 0} € Anzahlung`
                      }
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Payment Window */}
            {paymentMode !== "none" && (
              <div className="space-y-2">
                <Label>Zahlungsfrist (Minuten)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min="5"
                    max="1440"
                    value={paymentWindow}
                    onChange={(e) => setPaymentWindow(parseInt(e.target.value) || 30)}
                    className="w-32"
                  />
                  <span className="text-muted-foreground">Minuten</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Reservierung verfällt nach {paymentWindow} Minuten ohne Zahlung
                </p>
              </div>
            )}

            <DialogFooter>
              <Button onClick={savePaymentPolicy} disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <CheckCircle className="h-4 w-4 mr-2" />}
                Zahlungsrichtlinie speichern
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

// Komponente für Preisanzeige in Event-Liste
export const EventPriceBadge = ({ event }) => {
  const pricing = event.event_pricing;
  const policy = event.payment_policy;
  
  if (!pricing && !event.ticket_price && !event.price_per_person) {
    return <Badge variant="outline" className="text-gray-500">Kein Preis</Badge>;
  }

  const getPriceDisplay = () => {
    if (pricing?.pricing_mode === "variants" && pricing.variants?.length > 0) {
      const min = Math.min(...pricing.variants.map(v => v.price_per_person));
      const max = Math.max(...pricing.variants.map(v => v.price_per_person));
      if (min === max) return `${min.toFixed(2)} €`;
      return `${min.toFixed(2)} - ${max.toFixed(2)} €`;
    }
    const price = pricing?.single_price_per_person || event.ticket_price || event.price_per_person || 0;
    return price > 0 ? `${price.toFixed(2)} €` : null;
  };

  const priceDisplay = getPriceDisplay();
  if (!priceDisplay) return null;

  return (
    <div className="flex items-center gap-2">
      <Badge className="bg-green-100 text-green-800">
        <Euro className="h-3 w-3 mr-1" />{priceDisplay}
      </Badge>
      {policy?.mode === "deposit" && (
        <Badge variant="outline" className="text-amber-600 border-amber-300">
          Anzahlung
        </Badge>
      )}
      {policy?.mode === "full" && (
        <Badge variant="outline" className="text-purple-600 border-purple-300">
          Vorauszahlung
        </Badge>
      )}
    </div>
  );
};

export default EventPricingDialog;
