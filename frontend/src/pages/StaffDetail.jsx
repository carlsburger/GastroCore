import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Progress } from "../components/ui/progress";
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
  Alert,
  AlertDescription,
  AlertTitle,
} from "../components/ui/alert";
import { toast } from "sonner";
import {
  ArrowLeft,
  Mail,
  Phone,
  Calendar,
  Clock,
  FileText,
  Upload,
  Download,
  Trash2,
  Send,
  Loader2,
  User,
  Briefcase,
  File,
  MapPin,
  CreditCard,
  Shield,
  Heart,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Save,
  Building2,
  Smartphone,
} from "lucide-react";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const DOCUMENT_CATEGORIES = {
  arbeitsvertrag: { label: "Arbeitsvertrag", icon: FileText },
  belehrung: { label: "Belehrung", icon: FileText },
  zeugnis: { label: "Zeugnis", icon: FileText },
  sonstiges: { label: "Sonstiges", icon: File },
};

const VISIBILITY_OPTIONS = {
  hr_only: { label: "Nur HR/Admin", color: "bg-red-100 text-red-700" },
  manager: { label: "Manager sichtbar", color: "bg-yellow-100 text-yellow-700" },
  self: { label: "Mitarbeiter sichtbar", color: "bg-green-100 text-green-700" },
};

// Checklist labels for completeness
const CHECKLIST_LABELS = {
  email: "E-Mail-Adresse",
  mobile_phone: "Mobiltelefon",
  address: "Adresse (Straße, PLZ, Ort)",
  tax_id: "Steuer-ID",
  social_security_number: "Sozialversicherungsnummer",
  bank_iban: "Bank IBAN",
  health_insurance: "Krankenkasse",
  emergency_contact: "Notfallkontakt",
};

export const StaffDetail = () => {
  const { memberId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [member, setMember] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showEmailDialog, setShowEmailDialog] = useState(false);

  // HR Fields editing state
  const [hrFields, setHrFields] = useState({
    email: "",
    mobile_phone: "",
    street: "",
    zip_code: "",
    city: "",
    date_of_birth: "",
    tax_id: "",
    social_security_number: "",
    health_insurance: "",
    bank_iban: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
  });

  const [uploadData, setUploadData] = useState({
    category: "sonstiges",
    visibility: "hr_only",
    description: "",
  });

  const [emailLanguage, setEmailLanguage] = useState("de");

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, [memberId]);

  useEffect(() => {
    if (member) {
      setHrFields({
        email: member.email || "",
        mobile_phone: member.mobile_phone || "",
        street: member.street || "",
        zip_code: member.zip_code || "",
        city: member.city || "",
        date_of_birth: member.date_of_birth || "",
        tax_id: member.tax_id || "",
        social_security_number: member.social_security_number || "",
        health_insurance: member.health_insurance || "",
        bank_iban: member.bank_iban || "",
        emergency_contact_name: member.emergency_contact_name || "",
        emergency_contact_phone: member.emergency_contact_phone || "",
      });
    }
  }, [member]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [memberRes, docsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/staff/members/${memberId}`, { headers }),
        axios.get(`${BACKEND_URL}/api/staff/members/${memberId}/documents`, { headers }),
      ]);
      setMember(memberRes.data);
      setDocuments(docsRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Daten");
      navigate("/staff");
    } finally {
      setLoading(false);
    }
  };

  const handleSaveHRFields = async () => {
    setSaving(true);
    try {
      const response = await axios.patch(
        `${BACKEND_URL}/api/staff/members/${memberId}/hr-fields`,
        hrFields,
        { headers }
      );
      setMember(response.data);
      toast.success("HR-Daten gespeichert");
      
      if (response.data.warnings?.length > 0) {
        response.data.warnings.forEach(w => {
          toast.warning(w.message);
        });
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      toast.error("Datei zu groß. Maximum: 10MB");
      return;
    }

    setShowUploadDialog(true);
  };

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;

    setUploading(true);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("category", uploadData.category);
    formData.append("visibility", uploadData.visibility);
    formData.append("description", uploadData.description);

    try {
      await axios.post(
        `${BACKEND_URL}/api/staff/members/${memberId}/documents`,
        formData,
        {
          headers: {
            ...headers,
            "Content-Type": "multipart/form-data",
          },
        }
      );
      toast.success("Dokument hochgeladen");
      setShowUploadDialog(false);
      setUploadData({ category: "sonstiges", visibility: "hr_only", description: "" });
      fileInputRef.current.value = "";
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Hochladen");
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (doc) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/staff/documents/${doc.id}/download`,
        {
          headers,
          responseType: "blob",
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", doc.original_filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      toast.error("Fehler beim Download");
    }
  };

  const handleDeleteDocument = async (doc) => {
    if (!window.confirm("Dokument wirklich löschen?")) return;

    try {
      await axios.delete(`${BACKEND_URL}/api/staff/documents/${doc.id}`, { headers });
      toast.success("Dokument gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  const handleSendWelcomeEmail = async () => {
    if (!member?.email) {
      toast.error("Keine E-Mail-Adresse hinterlegt");
      return;
    }

    setSendingEmail(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/staff/members/${memberId}/send-welcome`,
        { language: emailLanguage },
        { headers }
      );
      toast.success("Begrüßungs-E-Mail gesendet");
      setShowEmailDialog(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "E-Mail-Versand fehlgeschlagen");
    } finally {
      setSendingEmail(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleDateString("de-DE");
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-20">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  if (!member) {
    return (
      <Layout>
        <div className="text-center py-20">
          <p className="text-muted-foreground">Mitarbeiter nicht gefunden</p>
        </div>
      </Layout>
    );
  }

  const completeness = member.completeness;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/staff")} className="rounded-full">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Zurück
          </Button>
        </div>

        {/* Profile Header */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-6">
              {/* Avatar */}
              <div className="flex-shrink-0">
                <div className="w-24 h-24 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-3xl font-bold text-primary">
                    {member.first_name?.[0]}
                    {member.last_name?.[0]}
                  </span>
                </div>
              </div>

              {/* Info */}
              <div className="flex-1 space-y-4">
                <div>
                  <h1 className="font-serif text-3xl font-medium text-primary">
                    {member.full_name}
                  </h1>
                  <div className="flex flex-wrap gap-2 mt-2">
                    <Badge className="bg-emerald-100 text-emerald-700">{member.role}</Badge>
                    <Badge className="bg-purple-100 text-purple-700">
                      {member.employment_type} ({member.weekly_hours}h/Woche)
                    </Badge>
                    <Badge className={member.status === "aktiv" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}>
                      {member.status === "aktiv" ? "Aktiv" : "Inaktiv"}
                    </Badge>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  {member.email && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Mail className="h-4 w-4" />
                      <span>{member.email}</span>
                    </div>
                  )}
                  {(member.phone || member.mobile_phone) && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Phone className="h-4 w-4" />
                      <span>{member.mobile_phone || member.phone}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>Seit {formatDate(member.entry_date)}</span>
                  </div>
                </div>

                {/* Completeness Score (Admin only) */}
                {isAdmin && completeness && (
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Profilvollständigkeit</span>
                      <span className={`font-medium ${completeness.score === 100 ? 'text-green-600' : completeness.score >= 50 ? 'text-yellow-600' : 'text-red-600'}`}>
                        {completeness.score}%
                      </span>
                    </div>
                    <Progress value={completeness.score} className="h-2" />
                    {completeness.missing_for_active?.length > 0 && (
                      <p className="text-xs text-amber-600">
                        ⚠️ Pflichtfelder fehlen: {completeness.missing_for_active.join(", ")}
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-2">
                <Button
                  variant="outline"
                  onClick={() => setShowEmailDialog(true)}
                  disabled={!member.email}
                  className="rounded-full"
                >
                  <Send className="h-4 w-4 mr-2" />
                  Begrüßungs-E-Mail
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Tabs */}
        <Tabs defaultValue="contact" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="contact">
              <Phone className="h-4 w-4 mr-2" />
              Kontakt
            </TabsTrigger>
            {isAdmin && (
              <TabsTrigger value="hr">
                <Shield className="h-4 w-4 mr-2" />
                Personal/Steuer
              </TabsTrigger>
            )}
            <TabsTrigger value="emergency">
              <Heart className="h-4 w-4 mr-2" />
              Notfall
            </TabsTrigger>
            <TabsTrigger value="documents">
              <FileText className="h-4 w-4 mr-2" />
              Dokumente ({documents.length})
            </TabsTrigger>
          </TabsList>

          {/* Contact Tab */}
          <TabsContent value="contact" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Kontaktdaten
                </CardTitle>
                <CardDescription>Persönliche Kontaktinformationen des Mitarbeiters</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">E-Mail-Adresse</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="email"
                        type="email"
                        value={hrFields.email}
                        onChange={(e) => setHrFields({ ...hrFields, email: e.target.value })}
                        placeholder="mitarbeiter@example.de"
                        className="pl-10"
                        disabled={!isAdmin}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="mobile_phone">Mobiltelefon</Label>
                    <div className="relative">
                      <Smartphone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="mobile_phone"
                        type="tel"
                        value={hrFields.mobile_phone}
                        onChange={(e) => setHrFields({ ...hrFields, mobile_phone: e.target.value })}
                        placeholder="+49 170 1234567"
                        className="pl-10"
                        disabled={!isAdmin}
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="street">Straße und Hausnummer</Label>
                  <Input
                    id="street"
                    value={hrFields.street}
                    onChange={(e) => setHrFields({ ...hrFields, street: e.target.value })}
                    placeholder="Musterstraße 123"
                    disabled={!isAdmin}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="zip_code">PLZ</Label>
                    <Input
                      id="zip_code"
                      value={hrFields.zip_code}
                      onChange={(e) => setHrFields({ ...hrFields, zip_code: e.target.value })}
                      placeholder="80333"
                      maxLength={5}
                      disabled={!isAdmin}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="city">Ort</Label>
                    <Input
                      id="city"
                      value={hrFields.city}
                      onChange={(e) => setHrFields({ ...hrFields, city: e.target.value })}
                      placeholder="München"
                      disabled={!isAdmin}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="date_of_birth">Geburtsdatum</Label>
                  <Input
                    id="date_of_birth"
                    type="date"
                    value={hrFields.date_of_birth}
                    onChange={(e) => setHrFields({ ...hrFields, date_of_birth: e.target.value })}
                    disabled={!isAdmin}
                  />
                </div>

                {isAdmin && (
                  <div className="flex justify-end pt-4">
                    <Button onClick={handleSaveHRFields} disabled={saving} className="rounded-full">
                      {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      <Save className="h-4 w-4 mr-2" />
                      Kontaktdaten speichern
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* HR/Tax Tab (Admin only) */}
          {isAdmin && (
            <TabsContent value="hr" className="space-y-4">
              <Alert>
                <Shield className="h-4 w-4" />
                <AlertTitle>Sensible Daten</AlertTitle>
                <AlertDescription>
                  Diese Daten sind nur für Administratoren sichtbar und werden im Audit-Log protokolliert.
                </AlertDescription>
              </Alert>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Building2 className="h-5 w-5" />
                    Steuer- und Sozialversicherungsdaten
                  </CardTitle>
                  <CardDescription>Daten für Lohnabrechnung und Steuerbüro</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="tax_id">Steuer-ID</Label>
                      <Input
                        id="tax_id"
                        value={hrFields.tax_id}
                        onChange={(e) => setHrFields({ ...hrFields, tax_id: e.target.value })}
                        placeholder="12 345 678 901"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="social_security_number">Sozialversicherungsnummer</Label>
                      <Input
                        id="social_security_number"
                        value={hrFields.social_security_number}
                        onChange={(e) => setHrFields({ ...hrFields, social_security_number: e.target.value })}
                        placeholder="12 150485 K 123"
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="health_insurance">Krankenkasse</Label>
                      <Input
                        id="health_insurance"
                        value={hrFields.health_insurance}
                        onChange={(e) => setHrFields({ ...hrFields, health_insurance: e.target.value })}
                        placeholder="AOK Bayern"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="bank_iban">Bank IBAN</Label>
                      <div className="relative">
                        <CreditCard className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                        <Input
                          id="bank_iban"
                          value={hrFields.bank_iban}
                          onChange={(e) => setHrFields({ ...hrFields, bank_iban: e.target.value })}
                          placeholder="DE89 3704 0044 0532 0130 00"
                          className="pl-10"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="flex justify-end pt-4">
                    <Button onClick={handleSaveHRFields} disabled={saving} className="rounded-full">
                      {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      <Save className="h-4 w-4 mr-2" />
                      Steuer-/SV-Daten speichern
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* Completeness Checklist */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5" />
                    Onboarding-Checkliste
                  </CardTitle>
                  <CardDescription>Vollständigkeit des Mitarbeiterprofils</CardDescription>
                </CardHeader>
                <CardContent>
                  {completeness ? (
                    <div className="space-y-3">
                      {Object.entries(completeness.checklist).map(([key, value]) => (
                        <div key={key} className="flex items-center justify-between py-2 border-b last:border-0">
                          <span className="text-sm">{CHECKLIST_LABELS[key] || key}</span>
                          {value ? (
                            <CheckCircle2 className="h-5 w-5 text-green-500" />
                          ) : (
                            <XCircle className="h-5 w-5 text-red-400" />
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">Keine Daten verfügbar</p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          )}

          {/* Emergency Contact Tab */}
          <TabsContent value="emergency" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Heart className="h-5 w-5 text-red-500" />
                  Notfallkontakt
                </CardTitle>
                <CardDescription>Kontaktperson im Notfall</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_name">Name des Notfallkontakts</Label>
                    <div className="relative">
                      <User className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="emergency_contact_name"
                        value={hrFields.emergency_contact_name}
                        onChange={(e) => setHrFields({ ...hrFields, emergency_contact_name: e.target.value })}
                        placeholder="Maria Mustermann"
                        className="pl-10"
                        disabled={!isAdmin}
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="emergency_contact_phone">Telefon des Notfallkontakts</Label>
                    <div className="relative">
                      <Phone className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="emergency_contact_phone"
                        type="tel"
                        value={hrFields.emergency_contact_phone}
                        onChange={(e) => setHrFields({ ...hrFields, emergency_contact_phone: e.target.value })}
                        placeholder="+49 170 9876543"
                        className="pl-10"
                        disabled={!isAdmin}
                      />
                    </div>
                  </div>
                </div>

                {isAdmin && (
                  <div className="flex justify-end pt-4">
                    <Button onClick={handleSaveHRFields} disabled={saving} className="rounded-full">
                      {saving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                      <Save className="h-4 w-4 mr-2" />
                      Notfallkontakt speichern
                    </Button>
                  </div>
                )}

                {!isAdmin && (member.emergency_contact_name || member.emergency_contact_phone) && (
                  <div className="bg-muted p-4 rounded-lg">
                    <p className="font-medium">{member.emergency_contact_name || "-"}</p>
                    <p className="text-muted-foreground">{member.emergency_contact_phone || "-"}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Documents Tab */}
          <TabsContent value="documents" className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-medium">Dokumente</h3>
              {isAdmin && (
                <div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                    onChange={handleFileSelect}
                    className="hidden"
                  />
                  <Button onClick={() => fileInputRef.current?.click()} className="rounded-full">
                    <Upload className="h-4 w-4 mr-2" />
                    Dokument hochladen
                  </Button>
                </div>
              )}
            </div>

            {documents.length === 0 ? (
              <Card>
                <CardContent className="py-12 text-center">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">Keine Dokumente vorhanden</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-3">
                {documents.map((doc) => {
                  const catConfig = DOCUMENT_CATEGORIES[doc.category] || DOCUMENT_CATEGORIES.sonstiges;
                  const visConfig = VISIBILITY_OPTIONS[doc.visibility] || VISIBILITY_OPTIONS.hr_only;
                  const Icon = catConfig.icon;

                  return (
                    <Card key={doc.id}>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex items-center gap-3 flex-1 min-w-0">
                            <div className="p-2 bg-muted rounded-lg">
                              <Icon className="h-5 w-5 text-muted-foreground" />
                            </div>
                            <div className="min-w-0 flex-1">
                              <p className="font-medium truncate">{doc.original_filename}</p>
                              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                <span>{formatFileSize(doc.file_size)}</span>
                                <span>•</span>
                                <span>{formatDate(doc.created_at)}</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <Badge className={catConfig.label === "Arbeitsvertrag" ? "bg-blue-100 text-blue-700" : "bg-gray-100 text-gray-700"}>
                              {catConfig.label}
                            </Badge>
                            <Badge className={visConfig.color}>{visConfig.label}</Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDownload(doc)}
                              className="h-8 w-8 p-0"
                            >
                              <Download className="h-4 w-4" />
                            </Button>
                            {isAdmin && (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleDeleteDocument(doc)}
                                className="h-8 w-8 p-0 text-red-500"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      {/* Upload Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dokument hochladen</DialogTitle>
            <DialogDescription>
              Datei: {fileInputRef.current?.files?.[0]?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Kategorie</Label>
              <Select
                value={uploadData.category}
                onValueChange={(v) => setUploadData({ ...uploadData, category: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(DOCUMENT_CATEGORIES).map(([key, { label }]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Sichtbarkeit</Label>
              <Select
                value={uploadData.visibility}
                onValueChange={(v) => setUploadData({ ...uploadData, visibility: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(VISIBILITY_OPTIONS).map(([key, { label }]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Beschreibung (optional)</Label>
              <Input
                value={uploadData.description}
                onChange={(e) => setUploadData({ ...uploadData, description: e.target.value })}
                placeholder="Kurze Beschreibung..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowUploadDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleUpload} disabled={uploading}>
              {uploading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Hochladen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Email Dialog */}
      <Dialog open={showEmailDialog} onOpenChange={setShowEmailDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Begrüßungs-E-Mail senden</DialogTitle>
            <DialogDescription>
              E-Mail wird an {member?.email} gesendet
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Sprache</Label>
              <Select value={emailLanguage} onValueChange={setEmailLanguage}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="de">Deutsch</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="pl">Polski</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEmailDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSendWelcomeEmail} disabled={sendingEmail}>
              {sendingEmail && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Senden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default StaffDetail;
