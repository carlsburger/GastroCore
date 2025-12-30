import React, { useState, useEffect, useCallback, useRef } from "react";
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
import { Checkbox } from "../components/ui/checkbox";
import { Label } from "../components/ui/label";
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
  Upload, 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle,
  FileArchive,
  Database,
  Clock,
  User,
  Shield,
  Settings,
  Calendar
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

// Seed collection labels
const COLLECTION_LABELS = {
  opening_hours_master: "Öffnungszeiten Master",
  opening_hours_periods: "Öffnungszeiten Perioden",
  shift_templates: "Schicht-Vorlagen",
  reservation_slot_rules: "Reservierungsregeln",
  reservation_options: "Reservierungsoptionen",
  reservation_slot_exceptions: "Reservierungsausnahmen",
  system_settings: "Systemeinstellungen"
};

export default function SeedsBackupRestore() {
  const { token, user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  
  // Import options
  const [dryRun, setDryRun] = useState(true);
  const [archiveMissing, setArchiveMissing] = useState(false);
  const [forceOverwrite, setForceOverwrite] = useState(false);
  
  const fileInputRef = useRef(null);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/admin/seeds/status`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setStatus(response.data);
    } catch (error) {
      console.error("Error fetching status:", error);
      toast.error("Fehler beim Laden des Status");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleExport = async () => {
    setExporting(true);
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/admin/seeds/export`,
        { 
          headers: { Authorization: `Bearer ${token}` },
          responseType: 'blob'
        }
      );
      
      // Get filename from response header
      const contentDisposition = response.headers['content-disposition'];
      let filename = 'carlsburg_system_seeds.zip';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename=(.+)/);
        if (match) filename = match[1];
      }
      
      // Download file
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("Backup erfolgreich erstellt");
      fetchStatus();
    } catch (error) {
      toast.error("Export fehlgeschlagen: " + (error.response?.data?.detail || error.message));
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    if (!file.name.endsWith('.zip')) {
      toast.error("Bitte eine ZIP-Datei auswählen");
      return;
    }
    
    setImporting(true);
    setImportResult(null);
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/admin/seeds/import?dry_run=${dryRun}&archive_missing=${archiveMissing}&force_overwrite=${forceOverwrite}`,
        formData,
        { 
          headers: { 
            Authorization: `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      setImportResult(response.data);
      
      if (response.data.status === "dry_run") {
        toast.info("Vorschau erstellt - keine Änderungen vorgenommen");
      } else if (response.data.status === "success") {
        toast.success(`Import erfolgreich: ${response.data.created} erstellt, ${response.data.updated} aktualisiert`);
        fetchStatus();
      } else {
        toast.warning("Import mit Fehlern abgeschlossen");
      }
    } catch (error) {
      toast.error("Import fehlgeschlagen: " + (error.response?.data?.detail || error.message));
    } finally {
      setImporting(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const getStatusBadge = (statusValue) => {
    switch (statusValue) {
      case "READY":
        return <Badge className="bg-green-100 text-green-800"><CheckCircle2 className="h-3 w-3 mr-1" />Bereit</Badge>;
      case "WARNINGS":
        return <Badge className="bg-yellow-100 text-yellow-800"><AlertTriangle className="h-3 w-3 mr-1" />Warnungen</Badge>;
      case "STOP":
        return <Badge variant="destructive"><XCircle className="h-3 w-3 mr-1" />Fehler</Badge>;
      default:
        return <Badge variant="secondary">{statusValue}</Badge>;
    }
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

  const isAdmin = user?.role === "admin";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#005500]">Backup & Restore</h1>
          <p className="text-[#005500]/70">System-Seeds sichern und wiederherstellen</p>
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
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Verification Status */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Shield className="h-4 w-4" />
              System-Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {getStatusBadge(status?.verification?.status)}
            {status?.verification?.warnings?.length > 0 && (
              <p className="text-xs text-yellow-600 mt-2">
                {status.verification.warnings.length} Warnung(en)
              </p>
            )}
            {status?.verification?.errors?.length > 0 && (
              <p className="text-xs text-red-600 mt-2">
                {status.verification.errors.length} Fehler
              </p>
            )}
          </CardContent>
        </Card>

        {/* Last Backup */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Letztes Backup
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="font-medium">{formatDate(status?.last_backup?.timestamp)}</p>
            {status?.last_backup?.user && (
              <p className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
                <User className="h-3 w-3" />
                {status.last_backup.user}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Total Documents */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="h-4 w-4" />
              Dokumente gesamt
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status?.total_documents || 0}</div>
            <p className="text-xs text-muted-foreground">
              in {Object.keys(status?.counts || {}).length} Collections
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Backup Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Download className="h-5 w-5" />
              Backup erstellen
            </CardTitle>
            <CardDescription>
              Exportiert alle System-Seeds als ZIP-Datei
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                <strong>Enthält:</strong> Öffnungszeiten, Schicht-Vorlagen, Reservierungsregeln, Systemeinstellungen
              </p>
              <p className="text-xs text-blue-600 mt-1">
                <strong>Nicht enthalten:</strong> Schichten, Reservierungen, Gäste, Logs, POS-Daten
              </p>
            </div>

            <Button
              className="w-full bg-[#005500] hover:bg-[#004400]"
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? (
                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <FileArchive className="h-4 w-4 mr-2" />
              )}
              Backup jetzt erstellen
            </Button>
          </CardContent>
        </Card>

        {/* Restore Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Restore durchführen
            </CardTitle>
            <CardDescription>
              Importiert System-Seeds aus einer ZIP-Datei
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Import Options */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="dryRun" 
                  checked={dryRun} 
                  onCheckedChange={setDryRun}
                />
                <Label htmlFor="dryRun" className="text-sm">
                  Nur Vorschau (Dry-Run)
                  <span className="text-muted-foreground ml-1">– empfohlen</span>
                </Label>
              </div>
              
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="archiveMissing" 
                  checked={archiveMissing} 
                  onCheckedChange={setArchiveMissing}
                  disabled={dryRun}
                />
                <Label htmlFor="archiveMissing" className="text-sm">
                  Fehlende Einträge archivieren
                </Label>
              </div>
              
              {isAdmin && (
                <div className="flex items-center space-x-2">
                  <Checkbox 
                    id="forceOverwrite" 
                    checked={forceOverwrite} 
                    onCheckedChange={setForceOverwrite}
                    disabled={dryRun}
                  />
                  <Label htmlFor="forceOverwrite" className="text-sm text-amber-600">
                    Überschreiben erzwingen (Admin)
                  </Label>
                </div>
              )}
            </div>

            {/* File Upload */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                onChange={handleImport}
                className="hidden"
                id="seedsFile"
              />
              <Button
                variant="outline"
                className="w-full border-[#005500] text-[#005500]"
                onClick={() => fileInputRef.current?.click()}
                disabled={importing}
              >
                {importing ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4 mr-2" />
                )}
                {dryRun ? "ZIP auswählen (Vorschau)" : "ZIP importieren"}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Import Result */}
      {importResult && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {importResult.status === "success" && <CheckCircle2 className="h-5 w-5 text-green-600" />}
              {importResult.status === "dry_run" && <Settings className="h-5 w-5 text-blue-600" />}
              {importResult.status === "error" && <XCircle className="h-5 w-5 text-red-600" />}
              Import-Ergebnis
              {importResult.status === "dry_run" && (
                <Badge variant="secondary" className="ml-2">Vorschau</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-4 gap-4 text-center">
              <div className="bg-green-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-green-700">{importResult.created}</div>
                <div className="text-xs text-green-600">Neu</div>
              </div>
              <div className="bg-blue-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-700">{importResult.updated}</div>
                <div className="text-xs text-blue-600">Aktualisiert</div>
              </div>
              <div className="bg-gray-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-gray-700">{importResult.archived}</div>
                <div className="text-xs text-gray-600">Archiviert</div>
              </div>
              <div className="bg-yellow-50 rounded-lg p-3">
                <div className="text-2xl font-bold text-yellow-700">{importResult.warnings?.length || 0}</div>
                <div className="text-xs text-yellow-600">Warnungen</div>
              </div>
            </div>

            {/* Details */}
            {importResult.details && Object.keys(importResult.details).length > 0 && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Collection</TableHead>
                    <TableHead className="text-right">Gesamt</TableHead>
                    <TableHead className="text-right">Neu</TableHead>
                    <TableHead className="text-right">Aktualisiert</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(importResult.details).map(([key, value]) => (
                    <TableRow key={key}>
                      <TableCell>{COLLECTION_LABELS[key] || key}</TableCell>
                      <TableCell className="text-right">{value.total || 0}</TableCell>
                      <TableCell className="text-right text-green-600">{value.created || 0}</TableCell>
                      <TableCell className="text-right text-blue-600">{value.updated || 0}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            {/* Warnings */}
            {importResult.warnings?.length > 0 && (
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                <p className="font-medium text-yellow-800 mb-2">Warnungen:</p>
                <ul className="text-sm text-yellow-700 list-disc list-inside">
                  {importResult.warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              </div>
            )}

            {/* Errors */}
            {importResult.errors?.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                <p className="font-medium text-red-800 mb-2">Fehler:</p>
                <ul className="text-sm text-red-700 list-disc list-inside">
                  {importResult.errors.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              </div>
            )}

            {/* Action hint for dry_run */}
            {importResult.status === "dry_run" && (
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-center">
                <p className="text-blue-800">
                  Dies war nur eine Vorschau. Deaktivieren Sie "Nur Vorschau" und laden Sie die Datei erneut hoch, um die Änderungen anzuwenden.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Collection Counts */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Aktuelle Seed-Daten
          </CardTitle>
          <CardDescription>Anzahl der Dokumente pro Collection</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Collection</TableHead>
                <TableHead className="text-right">Anzahl</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {status?.counts && Object.entries(status.counts).map(([key, count]) => (
                <TableRow key={key}>
                  <TableCell className="font-medium">{COLLECTION_LABELS[key] || key}</TableCell>
                  <TableCell className="text-right">{count}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Verification Warnings/Errors */}
      {(status?.verification?.warnings?.length > 0 || status?.verification?.errors?.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              Verifikation
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {status?.verification?.errors?.map((e, i) => (
              <div key={i} className="flex items-start gap-2 text-red-600">
                <XCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{e}</span>
              </div>
            ))}
            {status?.verification?.warnings?.map((w, i) => (
              <div key={i} className="flex items-start gap-2 text-yellow-600">
                <AlertTriangle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <span className="text-sm">{w}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
