/**
 * PersonalakteTab.jsx - Admin Personalakte V1.1
 * Modul 30 V1.1: Digitale Personalakte (LIGHT)
 * 
 * Funktionen:
 * - Dokumente auflisten mit Acknowledgement-Status
 * - Dokumente hochladen mit Versionierung
 * - Pflichtdokumente markieren
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { toast } from "sonner";
import {
  Upload,
  Download,
  Trash2,
  FileText,
  Loader2,
  CheckCircle,
  AlertCircle,
  Eye,
  RefreshCw,
  File,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Document Category Config
const DOC_CATEGORY_CONFIG = {
  CONTRACT: { label: "Arbeitsvertrag", color: "bg-blue-100 text-blue-700", icon: FileText },
  POLICY: { label: "Belehrung", color: "bg-yellow-100 text-yellow-700", icon: FileText },
  CERTIFICATE: { label: "Bescheinigung", color: "bg-green-100 text-green-700", icon: FileText },
  OTHER: { label: "Sonstiges", color: "bg-gray-100 text-gray-700", icon: File },
};

export default function PersonalakteTab({ memberId, staffName, isAdmin }) {
  const fileInputRef = useRef(null);
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  // Upload form
  const [uploadForm, setUploadForm] = useState({
    title: "",
    category: "CONTRACT",
    requires_acknowledgement: false,
  });

  // Fetch documents
  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await axios.get(
        `${BACKEND_URL}/api/admin/staff/${memberId}/documents`,
        { headers }
      );
      setDocuments(res.data.data || []);
    } catch (err) {
      console.error("Error fetching documents:", err);
      if (err.response?.status !== 404) {
        toast.error("Fehler beim Laden der Dokumente");
      }
    } finally {
      setLoading(false);
    }
  }, [memberId, headers]);

  useEffect(() => {
    fetchDocuments();
  }, [memberId]);

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 10 * 1024 * 1024) {
      toast.error("Datei zu groß. Maximum: 10MB");
      return;
    }

    const allowedTypes = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowedTypes.includes(ext)) {
      toast.error(`Dateityp nicht erlaubt. Erlaubt: ${allowedTypes.join(", ")}`);
      return;
    }

    setSelectedFile(file);
    setUploadForm({
      ...uploadForm,
      title: file.name.replace(/\.[^/.]+$/, ""), // Remove extension for title
    });
    setShowUploadDialog(true);
  };

  // Handle upload
  const handleUpload = async () => {
    if (!selectedFile || !uploadForm.title.trim()) {
      toast.error("Bitte Titel und Datei angeben");
      return;
    }

    setUploading(true);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("title", uploadForm.title);
    formData.append("category", uploadForm.category);
    formData.append("requires_acknowledgement", uploadForm.requires_acknowledgement);

    try {
      await axios.post(
        `${BACKEND_URL}/api/admin/staff/${memberId}/documents`,
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
      setSelectedFile(null);
      setUploadForm({ title: "", category: "CONTRACT", requires_acknowledgement: false });
      if (fileInputRef.current) fileInputRef.current.value = "";
      fetchDocuments();
    } catch (err) {
      console.error("Upload error:", err);
      toast.error(err.response?.data?.detail || "Fehler beim Hochladen");
    } finally {
      setUploading(false);
    }
  };

  // Handle download
  const handleDownload = async (doc) => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/admin/staff/${memberId}/documents/${doc.id}/download`,
        {
          headers,
          responseType: "blob",
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", doc.file_name || "dokument");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download error:", err);
      toast.error("Fehler beim Download");
    }
  };

  // Handle delete
  const handleDelete = async (doc) => {
    if (!window.confirm(`Dokument "${doc.title}" wirklich löschen?`)) return;

    try {
      await axios.delete(
        `${BACKEND_URL}/api/admin/staff/${memberId}/documents/${doc.id}`,
        { headers }
      );
      toast.success("Dokument gelöscht");
      fetchDocuments();
    } catch (err) {
      console.error("Delete error:", err);
      toast.error(err.response?.data?.detail || "Fehler beim Löschen");
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return new Date(dateStr).toLocaleDateString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (!bytes) return "-";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[#005500]" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium text-lg">Personalakte</h3>
          <p className="text-sm text-gray-500">
            Digitale Dokumente für {staffName}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchDocuments}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Aktualisieren
          </Button>
          {isAdmin && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.doc,.docx"
                onChange={handleFileSelect}
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                className="bg-[#005500] hover:bg-[#004400]"
              >
                <Upload className="h-4 w-4 mr-2" />
                Dokument hochladen
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Documents Table */}
      <Card>
        <CardContent className="p-0">
          {documents.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <FileText className="h-12 w-12 mx-auto mb-3 text-gray-300" />
              <p>Keine Dokumente vorhanden</p>
              {isAdmin && (
                <Button
                  variant="outline"
                  className="mt-4"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Erstes Dokument hochladen
                </Button>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Titel</TableHead>
                  <TableHead>Kategorie</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Pflicht</TableHead>
                  <TableHead>Bestätigt</TableHead>
                  <TableHead>Datum</TableHead>
                  <TableHead className="text-right">Aktionen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {documents.map((doc) => {
                  const catConfig = DOC_CATEGORY_CONFIG[doc.category] || DOC_CATEGORY_CONFIG.OTHER;
                  const CatIcon = catConfig.icon;

                  return (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <CatIcon className="h-4 w-4 text-gray-400" />
                          <span className="font-medium">{doc.title}</span>
                        </div>
                        {doc.file_name && (
                          <span className="text-xs text-gray-400 block mt-0.5">
                            {doc.file_name} ({formatFileSize(doc.file_size)})
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge className={catConfig.color}>
                          {catConfig.label}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">V{doc.version || 1}</Badge>
                      </TableCell>
                      <TableCell>
                        {doc.requires_acknowledgement ? (
                          <Badge className="bg-red-100 text-red-700">Ja</Badge>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {doc.requires_acknowledgement ? (
                          doc.acknowledged ? (
                            <div className="flex items-center gap-1 text-green-600">
                              <CheckCircle className="h-4 w-4" />
                              <span className="text-xs">{formatDate(doc.acknowledged_at)}</span>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1 text-amber-600">
                              <AlertCircle className="h-4 w-4" />
                              <span className="text-xs">Offen</span>
                            </div>
                          )
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-gray-600">
                          {formatDate(doc.created_at)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDownload(doc)}
                            title="Herunterladen"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          {isAdmin && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(doc)}
                              className="text-red-500 hover:text-red-700 hover:bg-red-50"
                              title="Löschen"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Upload Dialog */}
      <Dialog open={showUploadDialog} onOpenChange={(open) => {
        if (!open) {
          setSelectedFile(null);
          setUploadForm({ title: "", category: "CONTRACT", requires_acknowledgement: false });
        }
        setShowUploadDialog(open);
      }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dokument hochladen</DialogTitle>
            <DialogDescription>
              {selectedFile && (
                <span className="flex items-center gap-2 mt-2">
                  <FileText className="h-4 w-4" />
                  {selectedFile.name} ({formatFileSize(selectedFile.size)})
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Titel *</Label>
              <Input
                value={uploadForm.title}
                onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
                placeholder="z.B. Arbeitsvertrag 2025"
              />
            </div>
            <div className="space-y-2">
              <Label>Kategorie</Label>
              <Select
                value={uploadForm.category}
                onValueChange={(v) => setUploadForm({ ...uploadForm, category: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="CONTRACT">Arbeitsvertrag</SelectItem>
                  <SelectItem value="POLICY">Belehrung</SelectItem>
                  <SelectItem value="CERTIFICATE">Bescheinigung</SelectItem>
                  <SelectItem value="OTHER">Sonstiges</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="requires_ack"
                checked={uploadForm.requires_acknowledgement}
                onCheckedChange={(checked) => 
                  setUploadForm({ ...uploadForm, requires_acknowledgement: checked })
                }
              />
              <label
                htmlFor="requires_ack"
                className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
              >
                Pflichtdokument (Mitarbeiter muss bestätigen)
              </label>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowUploadDialog(false)}
            >
              Abbrechen
            </Button>
            <Button
              onClick={handleUpload}
              disabled={uploading || !uploadForm.title.trim()}
              className="bg-[#005500] hover:bg-[#004400]"
            >
              {uploading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              <Upload className="h-4 w-4 mr-2" />
              Hochladen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
