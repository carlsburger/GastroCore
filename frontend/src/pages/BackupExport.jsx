import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
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
  Download,
  Save,
  RefreshCw,
  Loader2,
  FileSpreadsheet,
  FileJson,
  HardDrive,
  FolderArchive,
  Clock,
  CheckCircle,
  AlertTriangle,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const BackupExport = () => {
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(null);
  const [writing, setWriting] = useState(false);

  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(`${BACKEND_URL}/api/admin/backup/status`, { headers });
      setStatus(res.data);
    } catch (err) {
      console.error("Error loading backup status:", err);
      toast.error("Fehler beim Laden des Backup-Status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  const handleDownloadXlsx = async () => {
    try {
      setDownloading("xlsx");
      const res = await axios.get(`${BACKEND_URL}/api/admin/backup/export-xlsx`, {
        headers,
        responseType: "blob",
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      
      // Get filename from Content-Disposition header or use default
      const contentDisposition = res.headers["content-disposition"];
      let filename = `Carlsburg_Backup_${new Date().toISOString().split("T")[0]}.xlsx`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) filename = match[1].replace(/"/g, "");
      }
      
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success("XLSX-Export erfolgreich heruntergeladen");
    } catch (err) {
      console.error("Error downloading XLSX:", err);
      toast.error("Fehler beim Download der XLSX-Datei");
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadJson = async () => {
    try {
      setDownloading("json");
      const res = await axios.get(`${BACKEND_URL}/api/admin/backup/export-events-actions-json`, {
        headers,
        responseType: "blob",
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement("a");
      link.href = url;
      
      // Get filename from Content-Disposition header or use default
      const contentDisposition = res.headers["content-disposition"];
      let filename = `Carlsburg_EventsActions_${new Date().toISOString().split("T")[0]}.json`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) filename = match[1].replace(/"/g, "");
      }
      
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast.success("JSON-Export erfolgreich heruntergeladen");
    } catch (err) {
      console.error("Error downloading JSON:", err);
      toast.error("Fehler beim Download der JSON-Datei");
    } finally {
      setDownloading(null);
    }
  };

  const handleWriteBackup = async () => {
    try {
      setWriting(true);
      const res = await axios.post(`${BACKEND_URL}/api/admin/backup/write`, {}, { headers });
      
      if (res.data.ok) {
        toast.success(`Backup erfolgreich geschrieben: ${res.data.written.join(", ")}`);
        loadStatus(); // Refresh status
      } else {
        toast.error("Backup-Schreiben fehlgeschlagen");
      }
    } catch (err) {
      console.error("Error writing backup:", err);
      toast.error("Fehler beim Schreiben des Backups");
    } finally {
      setWriting(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (isoString) => {
    if (!isoString) return "-";
    const date = new Date(isoString);
    return date.toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <Layout>
      <div className="p-6 space-y-6" style={{ backgroundColor: "#fafbed", minHeight: "100vh" }}>
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ fontFamily: "'Playfair Display', serif", color: "#002f02" }}>
              Backup & Export
            </h1>
            <p className="text-gray-600" style={{ fontFamily: "'Lato', sans-serif" }}>
              Stammdaten sichern und exportieren
            </p>
          </div>
          <Button
            variant="outline"
            onClick={loadStatus}
            disabled={loading}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Aktualisieren
          </Button>
        </div>

        {/* Status Card */}
        <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ color: "#002f02" }}>
              <FolderArchive className="h-5 w-5" />
              Backup-Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Lade Status...
              </div>
            ) : status ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  {status.enabled ? (
                    <Badge className="bg-green-100 text-green-700">
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Aktiv
                    </Badge>
                  ) : (
                    <Badge className="bg-yellow-100 text-yellow-700">
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      Inaktiv
                    </Badge>
                  )}
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Backup-Ordner:</span> {status.backup_folder}
                </div>
                <div className="text-sm text-gray-600">
                  <span className="font-medium">Letztes Backup:</span>{" "}
                  {status.last_backup_at ? formatDate(status.last_backup_at) : "Noch kein Backup"}
                </div>
              </div>
            ) : (
              <div className="text-gray-500">Keine Daten verfügbar</div>
            )}
          </CardContent>
        </Card>

        {/* Export Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* XLSX Export */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <FileSpreadsheet className="h-5 w-5 text-green-600" />
                Stammdaten Export
              </CardTitle>
              <CardDescription>
                Mitarbeiter & Tische als Excel-Datei
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>Alle Mitarbeiter (ohne sensible Daten)</li>
                  <li>Alle Tische mit Bereichen</li>
                  <li>Meta-Informationen</li>
                </ul>
              </div>
              <Button
                onClick={handleDownloadXlsx}
                disabled={downloading === "xlsx"}
                className="w-full gap-2"
                style={{ backgroundColor: "#ffed00", color: "#002f02" }}
              >
                {downloading === "xlsx" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download XLSX
              </Button>
            </CardContent>
          </Card>

          {/* JSON Export */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <FileJson className="h-5 w-5 text-blue-600" />
                Events & Aktionen
              </CardTitle>
              <CardDescription>
                Veranstaltungen & Aktionen als JSON
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>Alle Veranstaltungen</li>
                  <li>Alle Aktionen (Sattessen etc.)</li>
                  <li>Menü-Aktionen</li>
                </ul>
              </div>
              <Button
                onClick={handleDownloadJson}
                disabled={downloading === "json"}
                className="w-full gap-2"
                style={{ backgroundColor: "#ffed00", color: "#002f02" }}
              >
                {downloading === "json" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
                Download JSON
              </Button>
            </CardContent>
          </Card>

          {/* Write to Disk */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <HardDrive className="h-5 w-5 text-purple-600" />
                Server-Backup
              </CardTitle>
              <CardDescription>
                Backup auf Server schreiben (Übergang)
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>XLSX + JSON auf Server</li>
                  <li>Ordner: /app/backups/</li>
                  <li>Für manuelle Sicherung</li>
                </ul>
              </div>
              <Button
                onClick={handleWriteBackup}
                disabled={writing}
                className="w-full gap-2"
                style={{ backgroundColor: "#ffed00", color: "#002f02" }}
              >
                {writing ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Backup jetzt schreiben
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Existing Backups Table */}
        {status?.files?.length > 0 && (
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <Clock className="h-5 w-5" />
                Vorhandene Backup-Dateien
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Dateiname</TableHead>
                    <TableHead>Größe</TableHead>
                    <TableHead>Geändert am</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {status.files.map((file, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">
                        {file.name.endsWith(".xlsx") ? (
                          <FileSpreadsheet className="h-4 w-4 inline mr-2 text-green-600" />
                        ) : file.name.endsWith(".json") ? (
                          <FileJson className="h-4 w-4 inline mr-2 text-blue-600" />
                        ) : null}
                        {file.name}
                      </TableCell>
                      <TableCell>{formatBytes(file.size)}</TableCell>
                      <TableCell>{formatDate(file.modified)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Info Box */}
        <Card className="border-yellow-400 bg-yellow-50">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-yellow-800">Hinweis zu sensiblen Daten:</p>
                <p className="text-yellow-700">
                  Steuer-ID, Sozialversicherungsnummer und IBAN werden im XLSX-Export maskiert 
                  (z.B. ****1234). Diese Daten bleiben nur in der Datenbank vollständig gespeichert.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default BackupExport;
