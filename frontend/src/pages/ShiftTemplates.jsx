import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { 
  Plus, 
  Pencil, 
  Trash2, 
  Play, 
  Clock, 
  Users as UsersIcon,
  AlertCircle,
  CheckCircle,
  RefreshCw
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Konstanten
const WORK_AREAS = [
  { value: "service", label: "Service", color: "#3B82F6" },
  { value: "kitchen", label: "Küche", color: "#EF4444" },
  { value: "reinigung", label: "Reinigung", color: "#6B7280" },
];

const SEASONS = [
  { value: "all", label: "Ganzjährig" },
  { value: "summer", label: "Sommer (Apr-Okt)" },
  { value: "winter", label: "Winter (Nov-Mär)" },
];

const DAY_TYPES = [
  { value: "all", label: "Alle Tage" },
  { value: "weekday", label: "Wochentage (Mo-Fr)" },
  { value: "weekend", label: "Wochenende (Sa-So)" },
];

const ROLES = [
  { value: "frueh", label: "Früh" },
  { value: "spaet", label: "Spät" },
  { value: "teildienst", label: "Teildienst" },
  { value: "event", label: "Event" },
];

export default function ShiftTemplates() {
  const { token } = useAuth();
  const { toast } = useToast();
  
  const [templates, setTemplates] = useState([]);
  const [workAreas, setWorkAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [applyingTemplates, setApplyingTemplates] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingTemplate, setEditingTemplate] = useState(null);
  
  // Form State
  const [formData, setFormData] = useState({
    name: "",
    department: "service",
    season: "all",
    day_type: "all",
    start_time: "10:00",
    end_time_type: "fixed",
    end_time_fixed: "18:00",
    close_plus_minutes: 30,
    headcount_default: 1,
    active: true,
  });

  const getHeaders = useCallback(() => ({
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }), [token]);

  // Daten laden
  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    
    try {
      const [templatesRes, areasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/staff/shift-templates`, { headers: getHeaders() }),
        axios.get(`${BACKEND_URL}/api/staff/work-areas`, { headers: getHeaders() }),
      ]);
      
      setTemplates(templatesRes.data || []);
      setWorkAreas(areasRes.data || []);
    } catch (err) {
      console.error("Fehler beim Laden:", err);
      toast({
        variant: "destructive",
        title: "Fehler",
        description: "Schichtmodelle konnten nicht geladen werden.",
      });
    } finally {
      setLoading(false);
    }
  }, [token, getHeaders, toast]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Template erstellen/bearbeiten
  const handleSubmit = async () => {
    if (!formData.name || !formData.work_area_id) {
      toast({
        variant: "destructive",
        title: "Fehler",
        description: "Name und Bereich sind Pflichtfelder.",
      });
      return;
    }

    try {
      const payload = {
        ...formData,
        end_time: formData.use_close_offset ? null : formData.end_time,
        close_offset_minutes: formData.use_close_offset ? formData.close_offset_minutes : null,
      };

      if (editingTemplate) {
        await axios.put(
          `${BACKEND_URL}/api/staff/shift-templates/${editingTemplate.id}`,
          payload,
          { headers: getHeaders() }
        );
        toast({ title: "Schichtmodell aktualisiert" });
      } else {
        await axios.post(
          `${BACKEND_URL}/api/staff/shift-templates`,
          payload,
          { headers: getHeaders() }
        );
        toast({ title: "Schichtmodell erstellt" });
      }

      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (err) {
      console.error("Fehler:", err);
      toast({
        variant: "destructive",
        title: "Fehler",
        description: err.response?.data?.detail || "Speichern fehlgeschlagen.",
      });
    }
  };

  // Template löschen
  const handleDelete = async (id) => {
    if (!window.confirm("Schichtmodell wirklich löschen?")) return;

    try {
      await axios.delete(`${BACKEND_URL}/api/staff/shift-templates/${id}`, {
        headers: getHeaders(),
      });
      toast({ title: "Schichtmodell gelöscht" });
      fetchData();
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Fehler",
        description: "Löschen fehlgeschlagen.",
      });
    }
  };

  // Templates auf aktuelle Woche anwenden
  const handleApplyTemplates = async () => {
    if (!window.confirm("Schichtmodelle auf aktuelle Woche anwenden? Bestehende Schichten werden nicht überschrieben.")) {
      return;
    }

    setApplyingTemplates(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/staff/shift-templates/apply`,
        {},
        { headers: getHeaders() }
      );
      
      const result = response.data;
      toast({
        title: "Vorlagen angewendet",
        description: `${result.shifts_created || 0} Schichten erstellt, ${result.shifts_skipped || 0} übersprungen.`,
      });
    } catch (err) {
      console.error("Fehler:", err);
      toast({
        variant: "destructive",
        title: "Fehler",
        description: err.response?.data?.detail || "Anwenden fehlgeschlagen.",
      });
    } finally {
      setApplyingTemplates(false);
    }
  };

  // Form zurücksetzen
  const resetForm = () => {
    setFormData({
      name: "",
      work_area_id: "",
      season: "all",
      day_type: "all",
      role: "frueh",
      start_time: "10:00",
      end_time: "18:00",
      use_close_offset: false,
      close_offset_minutes: 30,
      headcount: 1,
    });
    setEditingTemplate(null);
  };

  // Template bearbeiten
  const handleEdit = (template) => {
    setEditingTemplate(template);
    setFormData({
      name: template.name || "",
      work_area_id: template.work_area_id || "",
      season: template.season || "all",
      day_type: template.day_type || "all",
      role: template.role || "frueh",
      start_time: template.start_time || "10:00",
      end_time: template.end_time || "18:00",
      use_close_offset: !!template.close_offset_minutes,
      close_offset_minutes: template.close_offset_minutes || 30,
      headcount: template.headcount || 1,
    });
    setDialogOpen(true);
  };

  // Hilfsfunktion: Work Area Name finden
  const getWorkAreaName = (id) => {
    const area = workAreas.find((a) => a.id === id);
    return area?.name || "Unbekannt";
  };

  const getWorkAreaColor = (id) => {
    const area = workAreas.find((a) => a.id === id);
    return area?.color || "#6B7280";
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-6xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Schichtmodelle / Vorlagen</h1>
          <p className="text-gray-600 mt-1">
            Definiere Standard-Schichten, die automatisch auf den Dienstplan angewendet werden können.
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={handleApplyTemplates}
            disabled={applyingTemplates || templates.length === 0}
          >
            {applyingTemplates ? (
              <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Play className="h-4 w-4 mr-2" />
            )}
            Auf aktuelle Woche anwenden
          </Button>
          <Button onClick={() => { resetForm(); setDialogOpen(true); }}>
            <Plus className="h-4 w-4 mr-2" />
            Neues Modell
          </Button>
        </div>
      </div>

      {/* Info-Box */}
      {templates.length === 0 && (
        <Card className="mb-6 border-dashed border-2 border-amber-300 bg-amber-50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="h-12 w-12 mx-auto mb-4 text-amber-500" />
            <p className="text-amber-800 font-medium">Keine Schichtmodelle vorhanden</p>
            <p className="text-amber-600 text-sm mt-2">
              Erstelle Standard-Schichtmodelle, um den Dienstplan schneller zu füllen.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Templates Liste */}
      {templates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Aktive Schichtmodelle ({templates.length})</CardTitle>
            <CardDescription>
              Diese Vorlagen können auf den aktuellen Wochenplan angewendet werden.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Bereich</TableHead>
                  <TableHead>Zeiten</TableHead>
                  <TableHead>Saison / Tage</TableHead>
                  <TableHead>Headcount</TableHead>
                  <TableHead className="text-right">Aktionen</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {templates.map((template) => (
                  <TableRow key={template.id}>
                    <TableCell className="font-medium">
                      {template.name}
                      <Badge variant="outline" className="ml-2">
                        {ROLES.find((r) => r.value === template.role)?.label || template.role}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge
                        style={{
                          backgroundColor: getWorkAreaColor(template.work_area_id),
                          color: "white",
                        }}
                      >
                        {getWorkAreaName(template.work_area_id)}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <Clock className="h-4 w-4 text-gray-400" />
                        {template.start_time} – {template.end_time || `Close+${template.close_offset_minutes}min`}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-600">
                        {SEASONS.find((s) => s.value === template.season)?.label || "Alle"}
                        {" / "}
                        {DAY_TYPES.find((d) => d.value === template.day_type)?.label || "Alle"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        <UsersIcon className="h-4 w-4 text-gray-400" />
                        {template.headcount}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleEdit(template)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(template.id)}
                      >
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Dialog für Erstellen/Bearbeiten */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editingTemplate ? "Schichtmodell bearbeiten" : "Neues Schichtmodell"}
            </DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Name */}
            <div className="space-y-2">
              <Label>Name *</Label>
              <Input
                placeholder="z.B. Frühdienst Service"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            {/* Bereich */}
            <div className="space-y-2">
              <Label>Bereich *</Label>
              <Select
                value={formData.work_area_id}
                onValueChange={(value) => setFormData({ ...formData, work_area_id: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Bereich wählen" />
                </SelectTrigger>
                <SelectContent>
                  {workAreas.map((area) => (
                    <SelectItem key={area.id} value={area.id}>
                      {area.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Rolle */}
            <div className="space-y-2">
              <Label>Schichttyp</Label>
              <Select
                value={formData.role}
                onValueChange={(value) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Zeiten */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Startzeit</Label>
                <Input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Endzeit</Label>
                <Input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                  disabled={formData.use_close_offset}
                />
              </div>
            </div>

            {/* Saison + Tage */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Saison</Label>
                <Select
                  value={formData.season}
                  onValueChange={(value) => setFormData({ ...formData, season: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SEASONS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Tage</Label>
                <Select
                  value={formData.day_type}
                  onValueChange={(value) => setFormData({ ...formData, day_type: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {DAY_TYPES.map((d) => (
                      <SelectItem key={d.value} value={d.value}>
                        {d.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Headcount */}
            <div className="space-y-2">
              <Label>Headcount (Anzahl Mitarbeiter)</Label>
              <Input
                type="number"
                min={1}
                max={20}
                value={formData.headcount}
                onChange={(e) => setFormData({ ...formData, headcount: parseInt(e.target.value) || 1 })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleSubmit}>
              {editingTemplate ? "Speichern" : "Erstellen"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
