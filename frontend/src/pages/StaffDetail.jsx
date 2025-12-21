import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
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
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
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
} from "lucide-react";
import axios from "axios";

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

export const StaffDetail = () => {
  const { memberId } = useParams();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);

  const [member, setMember] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [sendingEmail, setSendingEmail] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [showEmailDialog, setShowEmailDialog] = useState(false);

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

  const handleFileSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Check file size (10MB max)
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
                  {member.phone && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Phone className="h-4 w-4" />
                      <span>{member.phone}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar className="h-4 w-4" />
                    <span>Seit {formatDate(member.entry_date)}</span>
                  </div>
                </div>
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
        <Tabs defaultValue="documents" className="space-y-4">
          <TabsList>
            <TabsTrigger value="documents">
              <FileText className="h-4 w-4 mr-2" />
              Dokumente ({documents.length})
            </TabsTrigger>
            <TabsTrigger value="notes">
              <User className="h-4 w-4 mr-2" />
              Personalakte
            </TabsTrigger>
          </TabsList>

          {/* Documents Tab */}
          <TabsContent value="documents" className="space-y-4">
            <div className="flex justify-between items-center">
              <h3 className="font-medium">Dokumente</h3>
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
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteDocument(doc)}
                              className="h-8 w-8 p-0 text-red-500"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </TabsContent>

          {/* Notes Tab */}
          <TabsContent value="notes">
            <Card>
              <CardHeader>
                <CardTitle>HR-Notizen</CardTitle>
                <CardDescription>Interne Notizen zur Personalakte</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-muted rounded-lg p-4 whitespace-pre-wrap">
                  {member.notes || <span className="text-muted-foreground italic">Keine Notizen vorhanden</span>}
                </div>
              </CardContent>
            </Card>
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
