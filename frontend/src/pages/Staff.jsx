import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
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
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  Users,
  Plus,
  RefreshCw,
  Loader2,
  Edit,
  Trash2,
  Search,
  Mail,
  Phone,
  Calendar,
  Clock,
  FileText,
  ChevronRight,
  UserCheck,
  UserX,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const EMPLOYMENT_TYPES = {
  mini: { label: "Minijob", color: "bg-blue-100 text-blue-700" },
  teilzeit: { label: "Teilzeit", color: "bg-purple-100 text-purple-700" },
  vollzeit: { label: "Vollzeit", color: "bg-green-100 text-green-700" },
};

const ROLES = {
  service: { label: "Service", color: "bg-emerald-100 text-emerald-700" },
  schichtleiter: { label: "Schichtleiter", color: "bg-amber-100 text-amber-700" },
  kueche: { label: "Küche", color: "bg-orange-100 text-orange-700" },
  bar: { label: "Bar", color: "bg-violet-100 text-violet-700" },
  aushilfe: { label: "Aushilfe", color: "bg-gray-100 text-gray-700" },
};

const STATUS_CONFIG = {
  aktiv: { label: "Aktiv", color: "bg-green-100 text-green-700", icon: UserCheck },
  inaktiv: { label: "Inaktiv", color: "bg-red-100 text-red-700", icon: UserX },
};

export const Staff = () => {
  const navigate = useNavigate();
  const [members, setMembers] = useState([]);
  const [workAreas, setWorkAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingMember, setEditingMember] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("aktiv");

  const [formData, setFormData] = useState({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    role: "service",
    employment_type: "teilzeit",
    weekly_hours: 20,
    entry_date: new Date().toISOString().split("T")[0],
    work_area_ids: [],
    notes: "",
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, [statusFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [membersRes, areasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/staff/members`, {
          headers,
          params: statusFilter !== "all" ? { status: statusFilter } : {},
        }),
        axios.get(`${BACKEND_URL}/api/staff/work-areas`, { headers }),
      ]);
      setMembers(membersRes.data);
      setWorkAreas(areasRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Mitarbeiter");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      first_name: "",
      last_name: "",
      email: "",
      phone: "",
      role: "service",
      employment_type: "teilzeit",
      weekly_hours: 20,
      entry_date: new Date().toISOString().split("T")[0],
      work_area_ids: [],
      notes: "",
    });
    setEditingMember(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      if (editingMember) {
        await axios.patch(
          `${BACKEND_URL}/api/staff/members/${editingMember.id}`,
          formData,
          { headers }
        );
        toast.success("Mitarbeiter aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/staff/members`, formData, { headers });
        toast.success("Mitarbeiter angelegt");
      }
      setShowDialog(false);
      resetForm();
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (member) => {
    setEditingMember(member);
    setFormData({
      first_name: member.first_name || "",
      last_name: member.last_name || "",
      email: member.email || "",
      phone: member.phone || "",
      role: member.role || "service",
      employment_type: member.employment_type || "teilzeit",
      weekly_hours: member.weekly_hours || 20,
      entry_date: member.entry_date || "",
      work_area_ids: member.work_area_ids || [],
      notes: member.notes || "",
      status: member.status || "aktiv",
    });
    setShowDialog(true);
  };

  const handleArchive = async (member) => {
    if (!window.confirm(`${member.full_name} wirklich archivieren?`)) return;

    try {
      await axios.delete(`${BACKEND_URL}/api/staff/members/${member.id}`, { headers });
      toast.success("Mitarbeiter archiviert");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Archivieren");
    }
  };

  const filteredMembers = members.filter((m) =>
    `${m.first_name} ${m.last_name}`.toLowerCase().includes(search.toLowerCase())
  );

  const getAreaNames = (areaIds) => {
    if (!areaIds || areaIds.length === 0) return "-";
    return areaIds
      .map((id) => workAreas.find((a) => a.id === id)?.name)
      .filter(Boolean)
      .join(", ");
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl font-medium text-primary">Mitarbeiter</h1>
            <p className="text-muted-foreground">Personalverwaltung und Stammdaten</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchData} className="rounded-full">
              <RefreshCw className="h-4 w-4 mr-2" />
              Aktualisieren
            </Button>
            <Button
              onClick={() => {
                resetForm();
                setShowDialog(true);
              }}
              className="rounded-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neuer Mitarbeiter
            </Button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-full">
                  <Users className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{members.length}</p>
                  <p className="text-sm text-muted-foreground">Gesamt</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-100 rounded-full">
                  <UserCheck className="h-5 w-5 text-green-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {members.filter((m) => m.employment_type === "vollzeit").length}
                  </p>
                  <p className="text-sm text-muted-foreground">Vollzeit</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-100 rounded-full">
                  <Clock className="h-5 w-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {members.filter((m) => m.employment_type === "teilzeit").length}
                  </p>
                  <p className="text-sm text-muted-foreground">Teilzeit</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-100 rounded-full">
                  <Users className="h-5 w-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-2xl font-bold">
                    {members.filter((m) => m.employment_type === "mini").length}
                  </p>
                  <p className="text-sm text-muted-foreground">Minijob</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Suche nach Name..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-10 rounded-full"
                />
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px] rounded-full">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Status</SelectItem>
                  <SelectItem value="aktiv">Aktiv</SelectItem>
                  <SelectItem value="inaktiv">Inaktiv</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Members List */}
        <div className="space-y-3">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            </div>
          ) : filteredMembers.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Keine Mitarbeiter gefunden</p>
              </CardContent>
            </Card>
          ) : (
            filteredMembers.map((member) => {
              const statusConfig = STATUS_CONFIG[member.status] || STATUS_CONFIG.aktiv;
              const roleConfig = ROLES[member.role] || ROLES.service;
              const empConfig = EMPLOYMENT_TYPES[member.employment_type] || EMPLOYMENT_TYPES.teilzeit;

              return (
                <Card
                  key={member.id}
                  className="hover:shadow-lg transition-all cursor-pointer"
                  onClick={() => navigate(`/staff/${member.id}`)}
                >
                  <CardContent className="p-4 md:p-6">
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                      {/* Info */}
                      <div className="flex items-center gap-4 flex-1">
                        <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                          <span className="text-lg font-bold text-primary">
                            {member.first_name?.[0]}
                            {member.last_name?.[0]}
                          </span>
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-lg">{member.full_name}</p>
                          <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground mt-1">
                            {member.email && (
                              <span className="flex items-center gap-1">
                                <Mail className="h-3 w-3" />
                                {member.email}
                              </span>
                            )}
                            {member.phone && (
                              <span className="flex items-center gap-1">
                                <Phone className="h-3 w-3" />
                                {member.phone}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Badges & Actions */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge className={roleConfig.color}>{roleConfig.label}</Badge>
                        <Badge className={empConfig.color}>
                          {empConfig.label} ({member.weekly_hours}h)
                        </Badge>
                        <Badge className={statusConfig.color}>{statusConfig.label}</Badge>
                        
                        <div className="flex gap-1 ml-2" onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(member)}
                            className="h-8 w-8 p-0"
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleArchive(member)}
                            className="h-8 w-8 p-0 text-red-500 hover:text-red-600"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                        <ChevronRight className="h-5 w-5 text-muted-foreground" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">
              {editingMember ? "Mitarbeiter bearbeiten" : "Neuer Mitarbeiter"}
            </DialogTitle>
            <DialogDescription>
              {editingMember ? "Aktualisieren Sie die Mitarbeiterdaten" : "Legen Sie einen neuen Mitarbeiter an"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              {/* Name */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Vorname *</Label>
                  <Input
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Nachname *</Label>
                  <Input
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    required
                  />
                </div>
              </div>

              {/* Contact */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>E-Mail</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Telefon</Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
              </div>

              {/* Role & Employment */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Rolle *</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(v) => setFormData({ ...formData, role: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(ROLES).map(([key, { label }]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Beschäftigungsart *</Label>
                  <Select
                    value={formData.employment_type}
                    onValueChange={(v) => setFormData({ ...formData, employment_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(EMPLOYMENT_TYPES).map(([key, { label }]) => (
                        <SelectItem key={key} value={key}>
                          {label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Hours & Date */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Sollstunden/Woche *</Label>
                  <Input
                    type="number"
                    min="0"
                    max="48"
                    step="0.5"
                    value={formData.weekly_hours}
                    onChange={(e) => setFormData({ ...formData, weekly_hours: parseFloat(e.target.value) })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Eintrittsdatum *</Label>
                  <Input
                    type="date"
                    value={formData.entry_date}
                    onChange={(e) => setFormData({ ...formData, entry_date: e.target.value })}
                    required
                  />
                </div>
              </div>

              {/* Status (only when editing) */}
              {editingMember && (
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(v) => setFormData({ ...formData, status: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="aktiv">Aktiv</SelectItem>
                      <SelectItem value="inaktiv">Inaktiv</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}

              {/* Notes */}
              <div className="space-y-2">
                <Label>Notizen (HR-intern)</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  placeholder="Interne Notizen..."
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                {editingMember ? "Speichern" : "Anlegen"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Staff;
