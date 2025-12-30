import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { 
  RefreshCw, 
  Play, 
  Square, 
  AlertTriangle, 
  CheckCircle2, 
  Clock, 
  FileText,
  Mail,
  AlertCircle,
  Activity,
  Calendar
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

export default function POSImportMonitoring() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/pos/ingest/status-extended`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStatus(response.data);
    } catch (error) {
      console.error("Error fetching POS status:", error);
      toast.error("Fehler beim Laden des POS-Status");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchStatus();
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleTriggerIngest = async () => {
    setActionLoading("trigger");
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/pos/ingest/trigger`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Import abgeschlossen: ${response.data.processed} verarbeitet, ${response.data.duplicates} Duplikate`);
      fetchStatus();
    } catch (error) {
      toast.error("Import fehlgeschlagen: " + (error.response?.data?.detail || error.message));
    } finally {
      setActionLoading(null);
    }
  };

  const handleStartScheduler = async () => {
    setActionLoading("start");
    try {
      await axios.post(
        `${BACKEND_URL}/api/pos/scheduler/start`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Scheduler gestartet (10-Minuten-Intervall)");
      fetchStatus();
    } catch (error) {
      toast.error("Scheduler-Start fehlgeschlagen");
    } finally {
      setActionLoading(null);
    }
  };

  const handleStopScheduler = async () => {
    setActionLoading("stop");
    try {
      await axios.post(
        `${BACKEND_URL}/api/pos/scheduler/stop`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success("Scheduler gestoppt");
      fetchStatus();
    } catch (error) {
      toast.error("Scheduler-Stop fehlgeschlagen");
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    return date.toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-[#005500]" />
        </div>
      </div>
    );
  }

  const extended = status?.extended || {};

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#005500]">POS Import Monitoring</h1>
          <p className="text-[#005500]/70">Überwachung der gastronovi Z-Bericht Imports</p>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={fetchStatus}
          className="border-[#005500] text-[#005500]"
        >
          <RefreshCw className="h-4 w-4 mr-2" />
          Aktualisieren
        </Button>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Scheduler Status */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Scheduler Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {status?.scheduler_running ? (
                <Badge className="bg-green-100 text-green-800">
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                  Läuft
                </Badge>
              ) : (
                <Badge variant="secondary">
                  <Square className="h-3 w-3 mr-1" />
                  Gestoppt
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              Intervall: 10 Minuten
            </p>
          </CardContent>
        </Card>

        {/* IMAP Configuration */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Mail className="h-4 w-4" />
              IMAP Konfiguration
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {status?.imap_configured ? (
                <Badge className="bg-green-100 text-green-800">Konfiguriert</Badge>
              ) : (
                <Badge variant="destructive">Nicht konfiguriert</Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-2 truncate" title={status?.imap_user}>
              {status?.imap_user || "—"}
            </p>
          </CardContent>
        </Card>

        {/* Documents Today */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <FileText className="h-4 w-4" />
              PDFs verarbeitet
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{extended.docs_today || 0}</div>
            <p className="text-xs text-muted-foreground">
              Heute / {extended.docs_week || 0} diese Woche
            </p>
          </CardContent>
        </Card>

        {/* Failed Documents */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              Fehler
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${extended.failed_today > 0 ? 'text-red-600' : ''}`}>
              {extended.failed_today || 0}
            </div>
            <p className="text-xs text-muted-foreground">
              Heute / {extended.failed_week || 0} diese Woche
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Import Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Import Status
            </CardTitle>
            <CardDescription>Letzte Import-Aktivität</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Letzter Import-Lauf</p>
                <p className="font-medium">{formatDate(status?.latest_ingest?.timestamp)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Letzter Erfolg</p>
                <p className="font-medium">{formatDate(extended.last_successful_ingest)}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Letzte IMAP UID</p>
                <p className="font-medium">{status?.last_processed_uid || "—"}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Dokumente gesamt</p>
                <p className="font-medium">{status?.documents_total || 0}</p>
              </div>
            </div>

            {/* Current Month Crosscheck Warning */}
            {extended.current_month_crosscheck?.warning && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <div className="flex items-center gap-2 text-yellow-800">
                  <AlertCircle className="h-4 w-4" />
                  <span className="font-medium">Crosscheck-Warnung</span>
                </div>
                <p className="text-sm text-yellow-700 mt-1">
                  Abweichung im aktuellen Monat ({extended.current_month_crosscheck.month}) erkannt
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              Aktionen
            </CardTitle>
            <CardDescription>Import-Steuerung (Admin)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              className="w-full bg-[#005500] hover:bg-[#004400]"
              onClick={handleTriggerIngest}
              disabled={actionLoading !== null}
            >
              {actionLoading === "trigger" ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4 mr-2" />
              )}
              Import jetzt prüfen
            </Button>

            <div className="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                className="border-[#005500] text-[#005500]"
                onClick={handleStartScheduler}
                disabled={actionLoading !== null || status?.scheduler_running}
              >
                {actionLoading === "start" ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-2" />
                )}
                Scheduler starten
              </Button>
              <Button
                variant="outline"
                className="border-red-500 text-red-500 hover:bg-red-50"
                onClick={handleStopScheduler}
                disabled={actionLoading !== null || !status?.scheduler_running}
              >
                {actionLoading === "stop" ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Square className="h-4 w-4 mr-2" />
                )}
                Scheduler stoppen
              </Button>
            </div>

            <p className="text-xs text-muted-foreground">
              Der Scheduler prüft automatisch alle 10 Minuten auf neue Mails.
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Failed Documents */}
      {extended.failed_documents?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-600">
              <AlertTriangle className="h-5 w-5" />
              Fehlgeschlagene Imports ({extended.failed_documents.length})
            </CardTitle>
            <CardDescription>PDFs die nicht verarbeitet werden konnten</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Empfangen</TableHead>
                  <TableHead>Betreff</TableHead>
                  <TableHead>Datei</TableHead>
                  <TableHead>Fehler</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {extended.failed_documents.map((doc, idx) => (
                  <TableRow key={doc.id || idx}>
                    <TableCell className="text-sm">
                      {formatDate(doc.received_at)}
                    </TableCell>
                    <TableCell className="text-sm max-w-[200px] truncate">
                      {doc.subject || "—"}
                    </TableCell>
                    <TableCell className="text-sm max-w-[150px] truncate">
                      {doc.file_name || "—"}
                    </TableCell>
                    <TableCell className="text-sm text-red-600 max-w-[250px] truncate">
                      {doc.parse_error || "Unbekannter Fehler"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Recent Documents */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Letzte Dokumente
          </CardTitle>
          <CardDescription>Die letzten 20 verarbeiteten POS-Berichte</CardDescription>
        </CardHeader>
        <CardContent>
          <RecentDocuments token={token} />
        </CardContent>
      </Card>
    </div>
  );
}

// Separate component for recent documents
function RecentDocuments({ token }) {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const response = await axios.get(
          `${BACKEND_URL}/api/pos/documents?limit=20`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        setDocs(response.data.documents || []);
      } catch (error) {
        console.error("Error fetching documents:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchDocs();
  }, [token]);

  if (loading) {
    return <div className="text-center py-4 text-muted-foreground">Lädt...</div>;
  }

  if (docs.length === 0) {
    return <div className="text-center py-4 text-muted-foreground">Keine Dokumente vorhanden</div>;
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    const date = new Date(dateStr);
    return date.toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case "parsed":
        return <Badge className="bg-green-100 text-green-800">Verarbeitet</Badge>;
      case "failed":
        return <Badge variant="destructive">Fehler</Badge>;
      case "stored":
        return <Badge variant="secondary">Gespeichert</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const getTypeBadge = (type) => {
    switch (type) {
      case "daily":
        return <Badge variant="outline" className="border-blue-500 text-blue-600">Tagesbericht</Badge>;
      case "monthly":
        return <Badge variant="outline" className="border-purple-500 text-purple-600">Monatsbericht</Badge>;
      default:
        return <Badge variant="outline">{type}</Badge>;
    }
  };

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Empfangen</TableHead>
          <TableHead>Typ</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Datei</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {docs.map((doc, idx) => (
          <TableRow key={doc.id || idx}>
            <TableCell className="text-sm">{formatDate(doc.received_at)}</TableCell>
            <TableCell>{getTypeBadge(doc.doc_type)}</TableCell>
            <TableCell>{getStatusBadge(doc.parse_status)}</TableCell>
            <TableCell className="text-sm max-w-[200px] truncate" title={doc.file_name}>
              {doc.file_name || "—"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
