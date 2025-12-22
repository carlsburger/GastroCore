import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../hooks/use-toast";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
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
  Mail,
  Share2,
  Bell,
  Plus,
  Send,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  Edit,
  Trash2,
  RefreshCw,
  Settings,
  FileText,
  Calendar,
  Loader2,
} from "lucide-react";
import api from "../lib/api";

const STATUS_COLORS = {
  draft: "bg-gray-100 text-gray-800",
  review: "bg-yellow-100 text-yellow-800",
  approved: "bg-blue-100 text-blue-800",
  scheduled: "bg-purple-100 text-purple-800",
  sent: "bg-green-100 text-green-800",
  posted: "bg-green-100 text-green-800",
  failed: "bg-red-100 text-red-800",
  archived: "bg-gray-200 text-gray-600",
};

const STATUS_LABELS = {
  draft: "Entwurf",
  review: "Zur Prüfung",
  approved: "Freigegeben",
  scheduled: "Geplant",
  sent: "Gesendet",
  posted: "Veröffentlicht",
  failed: "Fehlgeschlagen",
  archived: "Archiviert",
};

const TYPE_ICONS = {
  newsletter: Mail,
  social: Share2,
  push: Bell,
};

const TYPE_LABELS = {
  newsletter: "Newsletter",
  social: "Social Post",
  push: "Push",
};

export default function Marketing() {
  const { token, hasRole } = useAuth();
  const { toast } = useToast();
  const isAdmin = hasRole("admin");

  const [content, setContent] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [configStatus, setConfigStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("content");

  // Filters
  const [statusFilter, setStatusFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  // Dialogs
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [scheduleDialogOpen, setScheduleDialogOpen] = useState(false);
  const [testSendDialogOpen, setTestSendDialogOpen] = useState(false);
  const [logsDialogOpen, setLogsDialogOpen] = useState(false);

  const [selectedContent, setSelectedContent] = useState(null);
  const [contentLogs, setContentLogs] = useState([]);

  // Form state
  const [formData, setFormData] = useState({
    title: "",
    content_type: "newsletter",
    language: "de",
    short_text: "",
    html_body: "",
    image_url: "",
    link_url: "",
    channels: ["email"],
    audience: "newsletter_optin",
  });

  const [scheduleDate, setScheduleDate] = useState("");
  const [testEmail, setTestEmail] = useState("");

  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [contentRes, jobsRes, configRes] = await Promise.all([
        api.get("/api/marketing", { headers }),
        api.get("/api/marketing/jobs/list", { headers }),
        api.get("/api/marketing/config/status", { headers }),
      ]);
      setContent(contentRes.data);
      setJobs(jobsRes.data);
      setConfigStatus(configRes.data);
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
  }, [fetchData]);

  const filteredContent = content.filter((item) => {
    if (statusFilter !== "all" && item.status !== statusFilter) return false;
    if (typeFilter !== "all" && item.content_type !== typeFilter) return false;
    return true;
  });

  const resetForm = () => {
    setFormData({
      title: "",
      content_type: "newsletter",
      language: "de",
      short_text: "",
      html_body: "",
      image_url: "",
      link_url: "",
      channels: ["email"],
      audience: "newsletter_optin",
    });
  };

  const handleCreate = async () => {
    try {
      await api.post("/api/marketing", formData, { headers });
      toast({ title: "Erfolg", description: "Inhalt erstellt" });
      setCreateDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler beim Erstellen",
        variant: "destructive",
      });
    }
  };

  const handleUpdate = async () => {
    try {
      await api.patch(`/api/marketing/${selectedContent.id}`, formData, { headers });
      toast({ title: "Erfolg", description: "Inhalt aktualisiert" });
      setEditDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler beim Aktualisieren",
        variant: "destructive",
      });
    }
  };

  const handleSubmitReview = async (item) => {
    try {
      await api.post(`/api/marketing/${item.id}/submit-review`, {}, { headers });
      toast({ title: "Erfolg", description: "Zur Prüfung eingereicht" });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleApprove = async (item, approved) => {
    try {
      await api.post(`/api/marketing/${item.id}/approve`, { approved }, { headers });
      toast({
        title: "Erfolg",
        description: approved ? "Freigegeben" : "Abgelehnt",
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleSchedule = async () => {
    try {
      await api.post(
        `/api/marketing/${selectedContent.id}/schedule`,
        { scheduled_at: new Date(scheduleDate).toISOString() },
        { headers }
      );
      toast({ title: "Erfolg", description: "Geplant" });
      setScheduleDialogOpen(false);
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleSendNow = async (item) => {
    try {
      const endpoint =
        item.content_type === "newsletter" ? "send-now" : "post-now";
      const res = await api.post(`/api/marketing/${item.id}/${endpoint}`, {}, { headers });
      toast({
        title: "Erfolg",
        description: `Job gestartet: ${res.data.job_id}`,
      });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleTestSend = async () => {
    try {
      const res = await api.post(
        `/api/marketing/${selectedContent.id}/send-test`,
        { test_email: testEmail },
        { headers }
      );
      toast({
        title: res.data.smtp_configured ? "Test gesendet" : "Test geloggt",
        description: res.data.message,
      });
      setTestSendDialogOpen(false);
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleRetry = async (item) => {
    try {
      await api.post(`/api/marketing/${item.id}/retry`, {}, { headers });
      toast({ title: "Erfolg", description: "Wiederholen gestartet" });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const handleArchive = async (item) => {
    if (!window.confirm("Wirklich archivieren?")) return;
    try {
      await api.delete(`/api/marketing/${item.id}`, { headers });
      toast({ title: "Erfolg", description: "Archiviert" });
      fetchData();
    } catch (error) {
      toast({
        title: "Fehler",
        description: error.response?.data?.detail || "Fehler",
        variant: "destructive",
      });
    }
  };

  const openEdit = (item) => {
    setSelectedContent(item);
    setFormData({
      title: item.title,
      content_type: item.content_type,
      language: item.language,
      short_text: item.short_text || "",
      html_body: item.html_body || "",
      image_url: item.image_url || "",
      link_url: item.link_url || "",
      channels: item.channels || ["email"],
      audience: item.audience || "newsletter_optin",
    });
    setEditDialogOpen(true);
  };

  const openLogs = async (item) => {
    try {
      const res = await api.get(`/api/marketing/logs/${item.id}`, { headers });
      setContentLogs(res.data);
      setSelectedContent(item);
      setLogsDialogOpen(true);
    } catch (error) {
      toast({ title: "Fehler", description: "Logs konnten nicht geladen werden", variant: "destructive" });
    }
  };

  const runScheduler = async () => {
    try {
      await api.post("/api/marketing/scheduler/run", {}, { headers });
      toast({ title: "Erfolg", description: "Scheduler ausgeführt" });
      fetchData();
    } catch (error) {
      toast({ title: "Fehler", description: "Scheduler-Fehler", variant: "destructive" });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-[#002f02]" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#002f02]">Marketing</h1>
          <p className="text-muted-foreground">Newsletter & Social Media verwalten</p>
        </div>
        <div className="flex gap-2">
          {isAdmin && (
            <Button variant="outline" onClick={runScheduler}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Scheduler
            </Button>
          )}
          <Button onClick={() => { resetForm(); setCreateDialogOpen(true); }} className="bg-[#002f02] hover:bg-[#003300]">
            <Plus className="w-4 h-4 mr-2" />
            Neu erstellen
          </Button>
        </div>
      </div>

      {/* Config Status */}
      {configStatus && (
        <Card className="border-[#002f02]/20">
          <CardHeader className="py-3">
            <CardTitle className="text-sm flex items-center gap-2">
              <Settings className="w-4 h-4" />
              Konfigurationsstatus
            </CardTitle>
          </CardHeader>
          <CardContent className="py-2">
            <div className="flex flex-wrap gap-4 text-sm">
              <div className="flex items-center gap-2">
                <Mail className="w-4 h-4" />
                SMTP:
                <Badge variant={configStatus.smtp_configured ? "default" : "secondary"}>
                  {configStatus.smtp_configured ? "Konfiguriert" : "Nur Logging"}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Share2 className="w-4 h-4" />
                Facebook:
                <Badge variant={configStatus.facebook_configured ? "default" : "secondary"}>
                  {configStatus.facebook_configured ? "Konfiguriert" : "Nicht konfiguriert"}
                </Badge>
              </div>
              <div className="flex items-center gap-2">
                <Share2 className="w-4 h-4" />
                Instagram:
                <Badge variant={configStatus.instagram_configured ? "default" : "secondary"}>
                  {configStatus.instagram_configured ? "Konfiguriert" : "Nicht konfiguriert"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="content">Inhalte ({content.length})</TabsTrigger>
          <TabsTrigger value="jobs">Jobs ({jobs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="content" className="space-y-4">
          {/* Filters */}
          <div className="flex gap-4">
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Alle Status</SelectItem>
                <SelectItem value="draft">Entwurf</SelectItem>
                <SelectItem value="review">Zur Prüfung</SelectItem>
                <SelectItem value="approved">Freigegeben</SelectItem>
                <SelectItem value="scheduled">Geplant</SelectItem>
                <SelectItem value="sent">Gesendet</SelectItem>
                <SelectItem value="posted">Veröffentlicht</SelectItem>
                <SelectItem value="failed">Fehlgeschlagen</SelectItem>
              </SelectContent>
            </Select>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Typ" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Alle Typen</SelectItem>
                <SelectItem value="newsletter">Newsletter</SelectItem>
                <SelectItem value="social">Social</SelectItem>
                <SelectItem value="push">Push</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Content List */}
          <div className="space-y-3">
            {filteredContent.length === 0 ? (
              <Card className="p-8 text-center text-muted-foreground">
                <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Keine Inhalte gefunden</p>
              </Card>
            ) : (
              filteredContent.map((item) => {
                const TypeIcon = TYPE_ICONS[item.content_type] || FileText;
                return (
                  <Card key={item.id} className="border-[#002f02]/20">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-4">
                          <div className="p-2 bg-[#002f02]/10 rounded-lg">
                            <TypeIcon className="w-5 h-5 text-[#002f02]" />
                          </div>
                          <div>
                            <h3 className="font-medium">{item.title}</h3>
                            <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                              <Badge className={STATUS_COLORS[item.status]}>
                                {STATUS_LABELS[item.status]}
                              </Badge>
                              <span>{TYPE_LABELS[item.content_type]}</span>
                              <span>·</span>
                              <span>{item.language.toUpperCase()}</span>
                              {item.scheduled_at && (
                                <>
                                  <span>·</span>
                                  <Clock className="w-3 h-3" />
                                  <span>{new Date(item.scheduled_at).toLocaleString("de-DE")}</span>
                                </>
                              )}
                            </div>
                            {item.short_text && (
                              <p className="text-sm text-muted-foreground mt-2 line-clamp-2">
                                {item.short_text}
                              </p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          {/* Preview */}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => { setSelectedContent(item); setPreviewDialogOpen(true); }}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>

                          {/* Edit (only draft/review) */}
                          {["draft", "review"].includes(item.status) && (
                            <Button variant="ghost" size="sm" onClick={() => openEdit(item)}>
                              <Edit className="w-4 h-4" />
                            </Button>
                          )}

                          {/* Submit for review (draft) */}
                          {item.status === "draft" && (
                            <Button variant="outline" size="sm" onClick={() => handleSubmitReview(item)}>
                              Einreichen
                            </Button>
                          )}

                          {/* Approve/Reject (review) - Admin only */}
                          {item.status === "review" && isAdmin && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-green-600"
                                onClick={() => handleApprove(item, true)}
                              >
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Freigeben
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-red-600"
                                onClick={() => handleApprove(item, false)}
                              >
                                <XCircle className="w-4 h-4 mr-1" />
                                Ablehnen
                              </Button>
                            </>
                          )}

                          {/* Schedule/Send (approved) - Admin only */}
                          {item.status === "approved" && isAdmin && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => { setSelectedContent(item); setScheduleDialogOpen(true); }}
                              >
                                <Calendar className="w-4 h-4 mr-1" />
                                Planen
                              </Button>
                              <Button
                                size="sm"
                                className="bg-[#002f02] hover:bg-[#003300]"
                                onClick={() => handleSendNow(item)}
                              >
                                <Send className="w-4 h-4 mr-1" />
                                Jetzt {item.content_type === "newsletter" ? "senden" : "posten"}
                              </Button>
                            </>
                          )}

                          {/* Test send (newsletter) - Admin only */}
                          {item.content_type === "newsletter" && isAdmin && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => { setSelectedContent(item); setTestEmail(""); setTestSendDialogOpen(true); }}
                            >
                              Test
                            </Button>
                          )}

                          {/* Retry (failed) - Admin only */}
                          {item.status === "failed" && isAdmin && (
                            <Button variant="outline" size="sm" onClick={() => handleRetry(item)}>
                              <RefreshCw className="w-4 h-4 mr-1" />
                              Wiederholen
                            </Button>
                          )}

                          {/* Logs */}
                          <Button variant="ghost" size="sm" onClick={() => openLogs(item)}>
                            <FileText className="w-4 h-4" />
                          </Button>

                          {/* Archive - Admin only */}
                          {isAdmin && (
                            <Button variant="ghost" size="sm" className="text-red-600" onClick={() => handleArchive(item)}>
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}
          </div>
        </TabsContent>

        <TabsContent value="jobs" className="space-y-4">
          <div className="space-y-3">
            {jobs.length === 0 ? (
              <Card className="p-8 text-center text-muted-foreground">
                <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>Keine Jobs vorhanden</p>
              </Card>
            ) : (
              jobs.map((job) => (
                <Card key={job.id} className="border-[#002f02]/20">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge
                            className={
                              job.status === "done"
                                ? "bg-green-100 text-green-800"
                                : job.status === "failed"
                                ? "bg-red-100 text-red-800"
                                : job.status === "running"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-gray-100 text-gray-800"
                            }
                          >
                            {job.status}
                          </Badge>
                          <span className="font-medium">{job.job_type}</span>
                        </div>
                        <div className="text-sm text-muted-foreground mt-1">
                          <span>Erstellt: {new Date(job.created_at).toLocaleString("de-DE")}</span>
                          {job.finished_at && (
                            <span className="ml-4">
                              Beendet: {new Date(job.finished_at).toLocaleString("de-DE")}
                            </span>
                          )}
                        </div>
                        {job.stats && (
                          <div className="text-sm mt-1">
                            {job.stats.recipients_total && (
                              <span>
                                Empfänger: {job.stats.recipients_sent || 0}/{job.stats.recipients_total}
                              </span>
                            )}
                            {job.stats.failures_count > 0 && (
                              <span className="text-red-600 ml-2">
                                Fehler: {job.stats.failures_count}
                              </span>
                            )}
                          </div>
                        )}
                        {job.error && (
                          <p className="text-sm text-red-600 mt-1">{job.error}</p>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Neuen Inhalt erstellen</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Typ</Label>
                <Select
                  value={formData.content_type}
                  onValueChange={(v) => setFormData({ ...formData, content_type: v, channels: v === "newsletter" ? ["email"] : ["facebook", "instagram"] })}
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
                <Select value={formData.language} onValueChange={(v) => setFormData({ ...formData, language: v })}>
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
            </div>
            <div>
              <Label>Titel / Betreff</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="Titel eingeben..."
              />
            </div>
            <div>
              <Label>Kurztext (für Social/Preview)</Label>
              <Textarea
                value={formData.short_text}
                onChange={(e) => setFormData({ ...formData, short_text: e.target.value })}
                placeholder="Kurztext..."
                rows={3}
              />
            </div>
            {formData.content_type === "newsletter" && (
              <div>
                <Label>HTML-Inhalt</Label>
                <Textarea
                  value={formData.html_body}
                  onChange={(e) => setFormData({ ...formData, html_body: e.target.value })}
                  placeholder="<h1>Hallo!</h1><p>Ihr Newsletter...</p>"
                  rows={8}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Verwenden Sie {"{unsubscribe_url}"} für den Abmelde-Link
                </p>
              </div>
            )}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Bild-URL (optional)</Label>
                <Input
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              <div>
                <Label>Link-URL (optional)</Label>
                <Input
                  value={formData.link_url}
                  onChange={(e) => setFormData({ ...formData, link_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
            </div>
            <div>
              <Label>Zielgruppe</Label>
              <Select value={formData.audience} onValueChange={(v) => setFormData({ ...formData, audience: v })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="newsletter_optin">Newsletter Opt-in</SelectItem>
                  <SelectItem value="loyalty_customers">Loyalty-Kunden</SelectItem>
                  <SelectItem value="all_customers">Alle Kunden</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreate} className="bg-[#002f02] hover:bg-[#003300]">
              Erstellen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Inhalt bearbeiten</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Titel / Betreff</Label>
              <Input
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              />
            </div>
            <div>
              <Label>Kurztext</Label>
              <Textarea
                value={formData.short_text}
                onChange={(e) => setFormData({ ...formData, short_text: e.target.value })}
                rows={3}
              />
            </div>
            {formData.content_type === "newsletter" && (
              <div>
                <Label>HTML-Inhalt</Label>
                <Textarea
                  value={formData.html_body}
                  onChange={(e) => setFormData({ ...formData, html_body: e.target.value })}
                  rows={8}
                  className="font-mono text-sm"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleUpdate} className="bg-[#002f02] hover:bg-[#003300]">
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog open={previewDialogOpen} onOpenChange={setPreviewDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Vorschau: {selectedContent?.title}</DialogTitle>
          </DialogHeader>
          {selectedContent && (
            <div className="space-y-4">
              <div className="flex gap-2">
                <Badge className={STATUS_COLORS[selectedContent.status]}>
                  {STATUS_LABELS[selectedContent.status]}
                </Badge>
                <Badge variant="outline">{TYPE_LABELS[selectedContent.content_type]}</Badge>
                <Badge variant="outline">{selectedContent.language.toUpperCase()}</Badge>
              </div>
              {selectedContent.short_text && (
                <div>
                  <Label>Kurztext</Label>
                  <p className="p-3 bg-gray-50 rounded-lg">{selectedContent.short_text}</p>
                </div>
              )}
              {selectedContent.html_body && (
                <div>
                  <Label>Newsletter-Vorschau</Label>
                  <div
                    className="p-4 bg-white border rounded-lg"
                    dangerouslySetInnerHTML={{ __html: selectedContent.html_body }}
                  />
                </div>
              )}
              {selectedContent.image_url && (
                <div>
                  <Label>Bild</Label>
                  <img src={selectedContent.image_url} alt="" className="max-w-full rounded-lg" />
                </div>
              )}
              <div className="text-sm text-muted-foreground">
                <p>Erstellt von: {selectedContent.created_by?.name}</p>
                <p>Erstellt am: {new Date(selectedContent.created_at).toLocaleString("de-DE")}</p>
                {selectedContent.approved_by && (
                  <p>Freigegeben von: {selectedContent.approved_by.name}</p>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Schedule Dialog */}
      <Dialog open={scheduleDialogOpen} onOpenChange={setScheduleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Zeitpunkt planen</DialogTitle>
          </DialogHeader>
          <div>
            <Label>Versandzeitpunkt</Label>
            <Input
              type="datetime-local"
              value={scheduleDate}
              onChange={(e) => setScheduleDate(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setScheduleDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSchedule} className="bg-[#002f02] hover:bg-[#003300]">
              Planen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Test Send Dialog */}
      <Dialog open={testSendDialogOpen} onOpenChange={setTestSendDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Test-Newsletter senden</DialogTitle>
          </DialogHeader>
          <div>
            <Label>Test-E-Mail-Adresse</Label>
            <Input
              type="email"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              placeholder="test@example.com"
            />
            {!configStatus?.smtp_configured && (
              <p className="text-sm text-yellow-600 mt-2">
                <AlertCircle className="w-4 h-4 inline mr-1" />
                SMTP nicht konfiguriert - wird nur geloggt
              </p>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setTestSendDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleTestSend} className="bg-[#002f02] hover:bg-[#003300]">
              Test senden
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Logs Dialog */}
      <Dialog open={logsDialogOpen} onOpenChange={setLogsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Logs: {selectedContent?.title}</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {contentLogs.length === 0 ? (
              <p className="text-muted-foreground text-center py-4">Keine Logs vorhanden</p>
            ) : (
              contentLogs.map((log) => (
                <div key={log.id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                  <div className="flex items-center gap-2">
                    <Badge variant={log.status === "sent" || log.status === "posted" ? "default" : "secondary"}>
                      {log.status}
                    </Badge>
                    <span>{log.channel}</span>
                  </div>
                  <span className="text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString("de-DE")}
                  </span>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
