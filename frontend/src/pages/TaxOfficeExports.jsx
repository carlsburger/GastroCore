import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Checkbox } from "../components/ui/checkbox";
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
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  FileText,
  Download,
  Send,
  RefreshCw,
  Loader2,
  Settings,
  Plus,
  Calendar,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Mail,
  Building2,
  RotateCcw,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const STATUS_CONFIG = {
  pending: { label: "Wartend", color: "bg-gray-100 text-gray-700", icon: Clock },
  generating: { label: "Wird erstellt", color: "bg-blue-100 text-blue-700", icon: Loader2 },
  ready: { label: "Bereit", color: "bg-green-100 text-green-700", icon: CheckCircle },
  sent: { label: "Versendet", color: "bg-purple-100 text-purple-700", icon: Send },
  failed: { label: "Fehlgeschlagen", color: "bg-red-100 text-red-700", icon: XCircle },
};

const MONTHS = [
  "Januar", "Februar", "März", "April", "Mai", "Juni",
  "Juli", "August", "September", "Oktober", "November", "Dezember"
];

export const TaxOfficeExports = () => {
  const [jobs, setJobs] = useState([]);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showSendDialog, setShowSendDialog] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const currentDate = new Date();
  const [createData, setCreateData] = useState({
    export_type: "monthly_hours",
    year: currentDate.getFullYear(),
    month: currentDate.getMonth() + 1,
    include_pdf: true,
    include_csv: true,
  });

  const [settingsData, setSettingsData] = useState({
    recipient_emails: [],
    cc_emails: [],
    sender_name: "Carlsburg HR",
    subject_template: "{company} - Steuerbüro Export {period}",
    default_text_de: "Anbei finden Sie die Unterlagen für den Zeitraum {period}.",
    filename_prefix: "carlsburg",
  });

  const [sendData, setSendData] = useState({
    language: "de",
    custom_message: "",
  });

  const [newEmail, setNewEmail] = useState("");

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [jobsRes, settingsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/taxoffice/jobs`, { headers }),
        axios.get(`${BACKEND_URL}/api/taxoffice/settings`, { headers }),
      ]);
      setJobs(jobsRes.data);
      setSettings(settingsRes.data);
      setSettingsData(settingsRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateJob = async () => {
    setSubmitting(true);
    try {
      await axios.post(`${BACKEND_URL}/api/taxoffice/jobs`, createData, { headers });
      toast.success("Export-Job erstellt");
      setShowCreateDialog(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  };

  const handleSaveSettings = async () => {
    setSubmitting(true);
    try {
      await axios.patch(`${BACKEND_URL}/api/taxoffice/settings`, settingsData, { headers });
      toast.success("Einstellungen gespeichert");
      setShowSettingsDialog(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDownload = async (job, fileIndex) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/taxoffice/jobs/${job.id}/download/${fileIndex}`,
        { headers, responseType: "blob" }
      );
      const file = job.files[fileIndex];
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", file.name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success("Download gestartet");
    } catch (err) {
      toast.error("Fehler beim Download");
    }
  };

  const handleSend = async () => {
    if (!selectedJob) return;
    setSubmitting(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/taxoffice/jobs/${selectedJob.id}/send`,
        sendData,
        { headers }
      );
      toast.success("Export erfolgreich versendet");
      setShowSendDialog(false);
      setSelectedJob(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Versand fehlgeschlagen");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetry = async (job) => {
    try {
      await axios.post(`${BACKEND_URL}/api/taxoffice/jobs/${job.id}/retry`, {}, { headers });
      toast.success("Job wird erneut ausgeführt");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Wiederholen");
    }
  };

  const addEmail = (type) => {
    if (!newEmail || !newEmail.includes("@")) {
      toast.error("Ungültige E-Mail-Adresse");
      return;
    }
    const key = type === "recipient" ? "recipient_emails" : "cc_emails";
    if (!settingsData[key].includes(newEmail)) {
      setSettingsData({
        ...settingsData,
        [key]: [...settingsData[key], newEmail],
      });
    }
    setNewEmail("");
  };

  const removeEmail = (type, email) => {
    const key = type === "recipient" ? "recipient_emails" : "cc_emails";
    setSettingsData({
      ...settingsData,
      [key]: settingsData[key].filter((e) => e !== email),
    });
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("de-DE");
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl font-medium text-primary">Steuerbüro-Exporte</h1>
            <p className="text-muted-foreground">Monatliche Berichte und Versand</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchData} className="rounded-full">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" onClick={() => setShowSettingsDialog(true)} className="rounded-full">
              <Settings className="h-4 w-4 mr-2" />
              Einstellungen
            </Button>
            <Button onClick={() => setShowCreateDialog(true)} className="rounded-full">
              <Plus className="h-4 w-4 mr-2" />
              Neuer Export
            </Button>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-full">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{jobs.length}</p>
                  <p className="text-sm text-muted-foreground">Exporte gesamt</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-full">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {jobs.filter((j) => j.status === "ready").length}
                  </p>
                  <p className="text-sm text-muted-foreground">Bereit</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-full">
                  <Send className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {jobs.filter((j) => j.status === "sent").length}
                  </p>
                  <p className="text-sm text-muted-foreground">Versendet</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-full">
                  <Mail className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {settings?.recipient_emails?.length || 0}
                  </p>
                  <p className="text-sm text-muted-foreground">Empfänger</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Jobs List */}
        <Card>
          <CardHeader>
            <CardTitle>Export-Jobs</CardTitle>
            <CardDescription>Übersicht aller erstellten Exporte</CardDescription>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-12">
                <Loader2 className="h-10 w-10 animate-spin text-primary" />
              </div>
            ) : jobs.length === 0 ? (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Noch keine Exporte erstellt</p>
              </div>
            ) : (
              <div className="space-y-3">
                {jobs.map((job) => {
                  const statusConfig = STATUS_CONFIG[job.status] || STATUS_CONFIG.pending;
                  const StatusIcon = statusConfig.icon;

                  return (
                    <div
                      key={job.id}
                      className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <div className="flex items-center gap-4">
                        <div className="p-2 bg-muted rounded-lg">
                          <FileText className="h-5 w-5 text-muted-foreground" />
                        </div>
                        <div>
                          <p className="font-medium">
                            {job.export_type === "monthly_hours" && "Stundenübersicht"}
                            {job.export_type === "shift_list" && "Schichtliste"}
                            {job.export_type === "staff_registration" && `Mitarbeiter-Anmeldung: ${job.staff_name}`}
                          </p>
                          <p className="text-sm text-muted-foreground">
                            {MONTHS[job.month - 1]} {job.year} • Erstellt: {formatDate(job.created_at)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 flex-wrap">
                        <Badge className={statusConfig.color}>
                          <StatusIcon className={`h-3 w-3 mr-1 ${job.status === "generating" ? "animate-spin" : ""}`} />
                          {statusConfig.label}
                        </Badge>

                        {job.status === "ready" && (
                          <>
                            {job.files?.map((file, idx) => (
                              <Button
                                key={idx}
                                variant="outline"
                                size="sm"
                                onClick={() => handleDownload(job, idx)}
                                className="rounded-full"
                              >
                                <Download className="h-4 w-4 mr-1" />
                                {file.type.toUpperCase()}
                              </Button>
                            ))}
                            <Button
                              size="sm"
                              onClick={() => {
                                setSelectedJob(job);
                                setShowSendDialog(true);
                              }}
                              className="rounded-full"
                            >
                              <Send className="h-4 w-4 mr-1" />
                              Senden
                            </Button>
                          </>
                        )}

                        {job.status === "sent" && (
                          <span className="text-sm text-muted-foreground">
                            Gesendet: {formatDate(job.sent_at)}
                          </span>
                        )}

                        {job.status === "failed" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleRetry(job)}
                            className="rounded-full"
                          >
                            <RotateCcw className="h-4 w-4 mr-1" />
                            Wiederholen
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Create Job Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Neuen Export erstellen</DialogTitle>
            <DialogDescription>Wählen Sie Zeitraum und Export-Typ</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Export-Typ</Label>
              <Select
                value={createData.export_type}
                onValueChange={(v) => setCreateData({ ...createData, export_type: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="monthly_hours">Stundenübersicht (Monat)</SelectItem>
                  <SelectItem value="shift_list">Schichtliste</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Monat</Label>
                <Select
                  value={createData.month.toString()}
                  onValueChange={(v) => setCreateData({ ...createData, month: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {MONTHS.map((m, idx) => (
                      <SelectItem key={idx} value={(idx + 1).toString()}>
                        {m}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Jahr</Label>
                <Select
                  value={createData.year.toString()}
                  onValueChange={(v) => setCreateData({ ...createData, year: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[2024, 2025, 2026].map((y) => (
                      <SelectItem key={y} value={y.toString()}>
                        {y}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <Checkbox
                  id="include_pdf"
                  checked={createData.include_pdf}
                  onCheckedChange={(c) => setCreateData({ ...createData, include_pdf: c })}
                />
                <Label htmlFor="include_pdf">PDF erstellen</Label>
              </div>
              <div className="flex items-center gap-2">
                <Checkbox
                  id="include_csv"
                  checked={createData.include_csv}
                  onCheckedChange={(c) => setCreateData({ ...createData, include_csv: c })}
                />
                <Label htmlFor="include_csv">CSV erstellen</Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreateJob} disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Export erstellen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Settings Dialog */}
      <Dialog open={showSettingsDialog} onOpenChange={setShowSettingsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Steuerbüro-Einstellungen</DialogTitle>
            <DialogDescription>E-Mail-Empfänger und Export-Konfiguration</DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto">
            {/* Recipients */}
            <div className="space-y-2">
              <Label>Empfänger (Steuerbüro)</Label>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="email@steuerbuero.de"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addEmail("recipient")}
                />
                <Button variant="outline" onClick={() => addEmail("recipient")}>
                  Hinzufügen
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {settingsData.recipient_emails?.map((email) => (
                  <Badge key={email} variant="secondary" className="gap-1">
                    {email}
                    <button onClick={() => removeEmail("recipient", email)} className="ml-1 hover:text-red-500">
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            </div>

            {/* CC */}
            <div className="space-y-2">
              <Label>CC (optional)</Label>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="kopie@firma.de"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && addEmail("cc")}
                />
                <Button variant="outline" onClick={() => addEmail("cc")}>
                  Hinzufügen
                </Button>
              </div>
              <div className="flex flex-wrap gap-2 mt-2">
                {settingsData.cc_emails?.map((email) => (
                  <Badge key={email} variant="secondary" className="gap-1">
                    {email}
                    <button onClick={() => removeEmail("cc", email)} className="ml-1 hover:text-red-500">
                      ×
                    </button>
                  </Badge>
                ))}
              </div>
            </div>

            {/* Sender Name */}
            <div className="space-y-2">
              <Label>Absendername</Label>
              <Input
                value={settingsData.sender_name}
                onChange={(e) => setSettingsData({ ...settingsData, sender_name: e.target.value })}
              />
            </div>

            {/* Subject */}
            <div className="space-y-2">
              <Label>Betreff-Vorlage</Label>
              <Input
                value={settingsData.subject_template}
                onChange={(e) => setSettingsData({ ...settingsData, subject_template: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Platzhalter: {"{company}"}, {"{period}"}
              </p>
            </div>

            {/* Filename Prefix */}
            <div className="space-y-2">
              <Label>Dateiname-Präfix</Label>
              <Input
                value={settingsData.filename_prefix}
                onChange={(e) => setSettingsData({ ...settingsData, filename_prefix: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Beispiel: {settingsData.filename_prefix}_stunden_2024-12.csv
              </p>
            </div>

            {/* Default Text */}
            <div className="space-y-2">
              <Label>Standard-Text (Deutsch)</Label>
              <Textarea
                value={settingsData.default_text_de}
                onChange={(e) => setSettingsData({ ...settingsData, default_text_de: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSettingsDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSaveSettings} disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Send Dialog */}
      <Dialog open={showSendDialog} onOpenChange={setShowSendDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>An Steuerbüro senden</DialogTitle>
            <DialogDescription>
              Export wird an {settings?.recipient_emails?.join(", ") || "keine Empfänger"} gesendet
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Sprache</Label>
              <Select
                value={sendData.language}
                onValueChange={(v) => setSendData({ ...sendData, language: v })}
              >
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

            <div className="space-y-2">
              <Label>Zusätzliche Nachricht (optional)</Label>
              <Textarea
                value={sendData.custom_message}
                onChange={(e) => setSendData({ ...sendData, custom_message: e.target.value })}
                placeholder="Optionale zusätzliche Nachricht..."
                rows={3}
              />
            </div>

            {(!settings?.recipient_emails || settings.recipient_emails.length === 0) && (
              <div className="flex items-center gap-2 p-3 bg-yellow-50 rounded-lg text-yellow-700">
                <AlertCircle className="h-5 w-5" />
                <span>Bitte zuerst Empfänger in den Einstellungen konfigurieren</span>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSendDialog(false)}>
              Abbrechen
            </Button>
            <Button
              onClick={handleSend}
              disabled={submitting || !settings?.recipient_emails?.length}
            >
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              <Send className="h-4 w-4 mr-2" />
              Senden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default TaxOfficeExports;
