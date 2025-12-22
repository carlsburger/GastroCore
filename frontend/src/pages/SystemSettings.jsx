import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";
import {
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  Clock,
  Save,
  Loader2,
  ArrowLeft,
} from "lucide-react";
import axios from "axios";
import { Link } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const VALID_TIMEZONES = [
  { value: "Europe/Berlin", label: "Berlin (MEZ/MESZ)" },
  { value: "Europe/Vienna", label: "Wien (MEZ/MESZ)" },
  { value: "Europe/Zurich", label: "Zürich (MEZ/MESZ)" },
  { value: "Europe/Amsterdam", label: "Amsterdam (MEZ/MESZ)" },
  { value: "Europe/Paris", label: "Paris (MEZ/MESZ)" },
  { value: "Europe/London", label: "London (GMT/BST)" },
  { value: "UTC", label: "UTC" },
];

export default function SystemSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState({
    legal_name: "",
    address_street: "",
    address_zip: "",
    address_city: "",
    address_country: "Deutschland",
    phone: "",
    email: "",
    website: "",
    timezone: "Europe/Berlin",
  });
  const [errors, setErrors] = useState({});

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/system/settings`, { headers });
      setSettings(res.data);
    } catch (err) {
      toast.error("Fehler beim Laden der System-Einstellungen");
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!settings.legal_name || settings.legal_name.length < 2) {
      newErrors.legal_name = "Geschäftsbezeichnung muss mindestens 2 Zeichen haben";
    }
    
    if (settings.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(settings.email)) {
      newErrors.email = "Ungültige E-Mail-Adresse";
    }
    
    if (settings.phone) {
      const cleaned = settings.phone.replace(/[\s\-\/\(\)]/g, "");
      if (!/^\+?[0-9]{6,20}$/.test(cleaned)) {
        newErrors.phone = "Ungültiges Telefonnummer-Format";
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      toast.error("Bitte korrigieren Sie die markierten Felder");
      return;
    }
    
    setSaving(true);
    try {
      await axios.put(`${BACKEND_URL}/api/system/settings`, settings, { headers });
      toast.success("System-Einstellungen gespeichert");
    } catch (err) {
      const message = err.response?.data?.detail || "Fehler beim Speichern";
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (field, value) => {
    setSettings(prev => ({ ...prev, [field]: value }));
    // Clear error when user types
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

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
        <div className="flex items-center gap-4">
          <Link to="/settings">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          </Link>
          <div>
            <h1 className="text-2xl font-serif font-bold text-[#002f02]">
              System-Einstellungen
            </h1>
            <p className="text-[#002f02]/70">Geschäftsdaten und Stammdaten verwalten</p>
          </div>
        </div>

        {/* Company Profile Card */}
        <Card className="border-[#002f02]/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[#002f02]">
              <Building2 className="h-5 w-5" />
              Geschäftsprofil
            </CardTitle>
            <CardDescription>
              Diese Daten werden für Dokumente, E-Mails und offizielle Kommunikation verwendet.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Legal Name */}
            <div className="space-y-2">
              <Label htmlFor="legal_name" className="text-[#002f02] font-medium">
                Geschäftsbezeichnung *
              </Label>
              <Input
                id="legal_name"
                value={settings.legal_name}
                onChange={(e) => handleChange("legal_name", e.target.value)}
                placeholder="z.B. Carlsburg Restaurant GmbH"
                className={errors.legal_name ? "border-red-500" : "border-[#002f02]/30"}
              />
              {errors.legal_name && (
                <p className="text-sm text-red-500">{errors.legal_name}</p>
              )}
            </div>

            {/* Address */}
            <div className="space-y-4">
              <Label className="text-[#002f02] font-medium flex items-center gap-2">
                <MapPin className="h-4 w-4" />
                Adresse
              </Label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <Input
                    value={settings.address_street}
                    onChange={(e) => handleChange("address_street", e.target.value)}
                    placeholder="Straße und Hausnummer"
                    className="border-[#002f02]/30"
                  />
                </div>
                <Input
                  value={settings.address_zip}
                  onChange={(e) => handleChange("address_zip", e.target.value)}
                  placeholder="PLZ"
                  className="border-[#002f02]/30"
                />
                <Input
                  value={settings.address_city}
                  onChange={(e) => handleChange("address_city", e.target.value)}
                  placeholder="Stadt"
                  className="border-[#002f02]/30"
                />
                <Input
                  value={settings.address_country}
                  onChange={(e) => handleChange("address_country", e.target.value)}
                  placeholder="Land"
                  className="border-[#002f02]/30"
                />
              </div>
            </div>

            {/* Contact */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="phone" className="text-[#002f02] font-medium flex items-center gap-2">
                  <Phone className="h-4 w-4" />
                  Telefon
                </Label>
                <Input
                  id="phone"
                  value={settings.phone}
                  onChange={(e) => handleChange("phone", e.target.value)}
                  placeholder="+49 123 456789"
                  className={errors.phone ? "border-red-500" : "border-[#002f02]/30"}
                />
                {errors.phone && (
                  <p className="text-sm text-red-500">{errors.phone}</p>
                )}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="email" className="text-[#002f02] font-medium flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  E-Mail
                </Label>
                <Input
                  id="email"
                  type="email"
                  value={settings.email}
                  onChange={(e) => handleChange("email", e.target.value)}
                  placeholder="info@restaurant.de"
                  className={errors.email ? "border-red-500" : "border-[#002f02]/30"}
                />
                {errors.email && (
                  <p className="text-sm text-red-500">{errors.email}</p>
                )}
              </div>
            </div>

            {/* Website & Timezone */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="website" className="text-[#002f02] font-medium flex items-center gap-2">
                  <Globe className="h-4 w-4" />
                  Website
                </Label>
                <Input
                  id="website"
                  value={settings.website}
                  onChange={(e) => handleChange("website", e.target.value)}
                  placeholder="https://www.restaurant.de"
                  className="border-[#002f02]/30"
                />
              </div>
              
              <div className="space-y-2">
                <Label className="text-[#002f02] font-medium flex items-center gap-2">
                  <Clock className="h-4 w-4" />
                  Zeitzone
                </Label>
                <Select
                  value={settings.timezone}
                  onValueChange={(value) => handleChange("timezone", value)}
                >
                  <SelectTrigger className="border-[#002f02]/30">
                    <SelectValue placeholder="Zeitzone wählen" />
                  </SelectTrigger>
                  <SelectContent>
                    {VALID_TIMEZONES.map((tz) => (
                      <SelectItem key={tz.value} value={tz.value}>
                        {tz.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="bg-[#002f02] hover:bg-[#003d03] text-white"
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Speichern...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Speichern
              </>
            )}
          </Button>
        </div>
      </div>
    </Layout>
  );
}
