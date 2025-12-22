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
  Upload,
  RefreshCw,
  Loader2,
  FileSpreadsheet,
  Database,
  FolderSync,
  CheckCircle,
  AlertTriangle,
  Clock,
  Grid3X3,
  Users,
  CalendarDays,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const TableImport = () => {
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const [status, setStatus] = useState(null);
  const [importLogs, setImportLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(null);
  const [seeding, setSeeding] = useState(false);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [statusRes, logsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/data-status`),
        axios.get(`${BACKEND_URL}/api/admin/import/logs?limit=10`, { headers }),
      ]);
      setStatus(statusRes.data);
      setImportLogs(logsRes.data);
    } catch (err) {
      console.error("Error loading data:", err);
      toast.error("Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFileUpload = async (type, file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(type);
      const endpoint = type === "tables" 
        ? "/api/admin/import/tables" 
        : "/api/admin/import/table-combinations";
      
      const res = await axios.post(`${BACKEND_URL}${endpoint}`, formData, {
        headers: {
          ...headers,
          "Content-Type": "multipart/form-data",
        },
      });

      if (res.data.success) {
        toast.success(res.data.message);
      } else {
        toast.warning(res.data.message);
      }
      loadData();
    } catch (err) {
      console.error("Upload error:", err);
      toast.error(err.response?.data?.detail || "Upload fehlgeschlagen");
    } finally {
      setUploading(null);
    }
  };

  const handleSeedFromRepo = async () => {
    try {
      setSeeding(true);
      const res = await axios.post(`${BACKEND_URL}/api/admin/seed/from-repo`, {}, { headers });
      
      if (res.data.success) {
        toast.success(res.data.message);
      } else {
        toast.warning(res.data.message);
      }
      loadData();
    } catch (err) {
      console.error("Seed error:", err);
      toast.error(err.response?.data?.detail || "Seed fehlgeschlagen");
    } finally {
      setSeeding(false);
    }
  };

  const formatDate = (isoString) => {
    if (!isoString) return "-";
    return new Date(isoString).toLocaleString("de-DE", {
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
              Tisch-Import & Seed
            </h1>
            <p className="text-gray-600" style={{ fontFamily: "'Lato', sans-serif" }}>
              Stammdaten importieren und synchronisieren
            </p>
          </div>
          <Button variant="outline" onClick={loadData} disabled={loading} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Aktualisieren
          </Button>
        </div>

        {/* Data Status Card */}
        <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ color: "#002f02" }}>
              <Database className="h-5 w-5" />
              Daten-Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex items-center gap-2 text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Lade Status...
              </div>
            ) : status ? (
              <div className="space-y-4">
                {/* DB Warning */}
                {status.database_warning && (
                  <div className="flex items-center gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    <span className="text-sm text-yellow-700">{status.database_warning}</span>
                  </div>
                )}
                
                {/* Build Info */}
                <div className="flex gap-4 text-sm">
                  <Badge variant="outline">Build: {status.build_id}</Badge>
                  <Badge variant="outline">Version: {status.version}</Badge>
                  <Badge className={status.database_type === "external" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"}>
                    DB: {status.database_type}
                  </Badge>
                </div>

                {/* Counts Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-3 bg-white rounded-lg border">
                    <div className="flex items-center gap-2 text-gray-600 text-sm">
                      <Grid3X3 className="h-4 w-4" />
                      Tische
                    </div>
                    <div className="text-2xl font-bold" style={{ color: "#002f02" }}>
                      {status.counts?.tables || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded-lg border">
                    <div className="flex items-center gap-2 text-gray-600 text-sm">
                      <Grid3X3 className="h-4 w-4" />
                      Kombinationen
                    </div>
                    <div className="text-2xl font-bold" style={{ color: "#002f02" }}>
                      {status.counts?.table_combinations || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded-lg border">
                    <div className="flex items-center gap-2 text-gray-600 text-sm">
                      <Users className="h-4 w-4" />
                      Mitarbeiter
                    </div>
                    <div className="text-2xl font-bold" style={{ color: "#002f02" }}>
                      {status.counts?.staff_members || 0}
                    </div>
                  </div>
                  <div className="p-3 bg-white rounded-lg border">
                    <div className="flex items-center gap-2 text-gray-600 text-sm">
                      <CalendarDays className="h-4 w-4" />
                      Reservierungen
                    </div>
                    <div className="text-2xl font-bold" style={{ color: "#002f02" }}>
                      {status.counts?.reservations || 0}
                    </div>
                  </div>
                </div>

                {/* Last Import */}
                {status.last_import && (
                  <div className="text-sm text-gray-600">
                    <span className="font-medium">Letzter Import:</span>{" "}
                    {formatDate(status.last_import.timestamp)} - {status.last_import.collection}{" "}
                    ({status.last_import.created} neu, {status.last_import.updated} aktualisiert)
                  </div>
                )}
              </div>
            ) : null}
          </CardContent>
        </Card>

        {/* Import Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Tables Import */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <FileSpreadsheet className="h-5 w-5 text-green-600" />
                Tische importieren
              </CardTitle>
              <CardDescription>
                Excel-Datei mit Tisch-Stammdaten
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>Sheet: "tables"</li>
                  <li>Spalten: table_number, area, subarea, seats, ...</li>
                  <li>Upsert nach Tischnummer + Bereich</li>
                </ul>
              </div>
              <div>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => handleFileUpload("tables", e.target.files?.[0])}
                  className="hidden"
                  id="tables-upload"
                  disabled={uploading === "tables"}
                />
                <label htmlFor="tables-upload">
                  <Button
                    asChild
                    disabled={uploading === "tables"}
                    className="w-full gap-2 cursor-pointer"
                    style={{ backgroundColor: "#ffed00", color: "#002f02" }}
                  >
                    <span>
                      {uploading === "tables" ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      Tische hochladen
                    </span>
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Combinations Import */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                Kombinationen importieren
              </CardTitle>
              <CardDescription>
                Excel-Datei mit Tischkombinationen
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>Sheet: "combinations"</li>
                  <li>Spalten: combo_id, subarea, tables, ...</li>
                  <li>Upsert nach combo_id</li>
                </ul>
              </div>
              <div>
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={(e) => handleFileUpload("combinations", e.target.files?.[0])}
                  className="hidden"
                  id="combos-upload"
                  disabled={uploading === "combinations"}
                />
                <label htmlFor="combos-upload">
                  <Button
                    asChild
                    disabled={uploading === "combinations"}
                    className="w-full gap-2 cursor-pointer"
                    style={{ backgroundColor: "#ffed00", color: "#002f02" }}
                  >
                    <span>
                      {uploading === "combinations" ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Upload className="h-4 w-4" />
                      )}
                      Kombinationen hochladen
                    </span>
                  </Button>
                </label>
              </div>
            </CardContent>
          </Card>

          {/* Seed from Repo */}
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <FolderSync className="h-5 w-5 text-purple-600" />
                Seed aus Repo
              </CardTitle>
              <CardDescription>
                Stammdaten aus /seed/ Ordner laden
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="text-sm text-gray-600">
                <ul className="list-disc list-inside space-y-1">
                  <li>/seed/tables.xlsx</li>
                  <li>/seed/table_combinations.xlsx</li>
                  <li>Bei neuem Container ausführen</li>
                </ul>
              </div>
              <Button
                onClick={handleSeedFromRepo}
                disabled={seeding}
                className="w-full gap-2"
                style={{ backgroundColor: "#ffed00", color: "#002f02" }}
              >
                {seeding ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <FolderSync className="h-4 w-4" />
                )}
                Seed aus Repo laden
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Import Logs Table */}
        {importLogs.length > 0 && (
          <Card style={{ backgroundColor: "#f3f6de", borderColor: "#002f02" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2" style={{ color: "#002f02" }}>
                <Clock className="h-5 w-5" />
                Import-Protokoll
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Zeitpunkt</TableHead>
                    <TableHead>Collection</TableHead>
                    <TableHead>Datei</TableHead>
                    <TableHead>Benutzer</TableHead>
                    <TableHead className="text-right">Neu</TableHead>
                    <TableHead className="text-right">Aktualisiert</TableHead>
                    <TableHead className="text-right">Fehler</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {importLogs.map((log, idx) => (
                    <TableRow key={idx}>
                      <TableCell>{formatDate(log.timestamp)}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{log.collection}</Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{log.filename}</TableCell>
                      <TableCell>{log.user}</TableCell>
                      <TableCell className="text-right text-green-600">{log.created}</TableCell>
                      <TableCell className="text-right text-blue-600">{log.updated}</TableCell>
                      <TableCell className="text-right text-red-600">{log.errors || 0}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {/* Info Box */}
        <Card className="border-blue-200 bg-blue-50">
          <CardContent className="pt-4">
            <div className="flex items-start gap-3">
              <CheckCircle className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="text-sm">
                <p className="font-medium text-blue-800">Import-Regeln:</p>
                <ul className="text-blue-700 list-disc list-inside mt-1 space-y-1">
                  <li>Imports sind idempotent (mehrfach ausführbar ohne Duplikate)</li>
                  <li>Bestehende Einträge werden aktualisiert (Upsert)</li>
                  <li>Kombinationen nur innerhalb gleicher Subarea erlaubt</li>
                  <li>Tisch 3, 2, 11, 12, 19, 20, 21 sind nicht kombinierbar</li>
                </ul>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default TableImport;
