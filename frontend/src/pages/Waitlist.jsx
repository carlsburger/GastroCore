import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  Plus,
  Users,
  Phone,
  Clock,
  Loader2,
  AlertTriangle,
  CheckCircle,
  Mail,
  Trash2,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const WAITLIST_STATUS = {
  offen: { label: "Offen", className: "bg-yellow-100 text-yellow-800" },
  informiert: { label: "Informiert", className: "bg-blue-100 text-blue-800" },
  eingeloest: { label: "Eingelöst", className: "bg-green-100 text-green-800" },
  erledigt: { label: "Erledigt", className: "bg-gray-100 text-gray-600" },
};

export const Waitlist = () => {
  const { isSchichtleiter } = useAuth();
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [areas, setAreas] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split("T")[0]);
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showConvertDialog, setShowConvertDialog] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState(null);
  const [formData, setFormData] = useState({
    guest_name: "",
    guest_phone: "",
    guest_email: "",
    party_size: 2,
    date: "",
    preferred_time: "",
    priority: 3,
    notes: "",
  });
  const [convertTime, setConvertTime] = useState("");
  const [convertArea, setConvertArea] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = { date: selectedDate };
      if (statusFilter !== "all") params.status = statusFilter;

      const [entriesRes, areasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/waitlist`, { headers, params }),
        axios.get(`${BACKEND_URL}/api/areas`, { headers }),
      ]);
      setEntries(entriesRes.data);
      setAreas(areasRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedDate, statusFilter]);

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${BACKEND_URL}/api/waitlist`, formData, { headers });
      toast.success("Wartelisten-Eintrag erstellt");
      setShowCreateDialog(false);
      setFormData({
        guest_name: "",
        guest_phone: "",
        guest_email: "",
        party_size: 2,
        date: selectedDate,
        preferred_time: "",
        priority: 3,
        notes: "",
      });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  };

  const handleStatusChange = async (entryId, newStatus) => {
    try {
      await axios.patch(`${BACKEND_URL}/api/waitlist/${entryId}`, { status: newStatus }, { headers });
      toast.success(`Status: ${WAITLIST_STATUS[newStatus]?.label}`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    }
  };

  const handleConvert = async () => {
    if (!selectedEntry || !convertTime) return;
    setSubmitting(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/waitlist/${selectedEntry.id}/convert`,
        null,
        { headers, params: { time: convertTime, area_id: convertArea || undefined } }
      );
      toast.success("Reservierung erstellt!");
      setShowConvertDialog(false);
      setSelectedEntry(null);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler bei der Konvertierung");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (entryId) => {
    try {
      await axios.delete(`${BACKEND_URL}/api/waitlist/${entryId}`, { headers });
      toast.success("Eintrag archiviert");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Archivieren");
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">Warteliste</h1>
            <p className="text-muted-foreground mt-1">Gäste auf der Warteliste verwalten</p>
          </div>
          <Button
            onClick={() => {
              setFormData({ ...formData, date: selectedDate });
              setShowCreateDialog(true);
            }}
            className="rounded-full"
            data-testid="new-waitlist-button"
          >
            <Plus size={16} className="mr-2" />
            Neuer Eintrag
          </Button>
        </div>

        {/* Filters */}
        <Card className="bg-card">
          <CardContent className="p-4 flex flex-wrap gap-4">
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-auto h-11"
            />
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[150px] h-11">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Alle</SelectItem>
                {Object.entries(WAITLIST_STATUS).map(([key, val]) => (
                  <SelectItem key={key} value={key}>{val.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        {/* Entries List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : entries.length === 0 ? (
          <Card className="bg-card">
            <CardContent className="py-12 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Einträge auf der Warteliste</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {entries.map((entry) => (
              <Card key={entry.id} className="bg-card hover:shadow-md transition-all" data-testid={`waitlist-${entry.id}`}>
                <CardContent className="p-4">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                    <div className="flex items-center gap-4 flex-1">
                      {/* Priority indicator */}
                      <div className={`w-2 h-12 rounded-full ${
                        entry.priority >= 4 ? "bg-red-500" : entry.priority >= 3 ? "bg-yellow-500" : "bg-gray-300"
                      }`} />
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-lg">{entry.guest_name}</p>
                          <Badge className={WAITLIST_STATUS[entry.status]?.className}>
                            {WAITLIST_STATUS[entry.status]?.label}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                          <span className="flex items-center gap-1">
                            <Users size={14} />
                            {entry.party_size} Pers.
                          </span>
                          <span className="flex items-center gap-1">
                            <Phone size={14} />
                            {entry.guest_phone}
                          </span>
                          {entry.preferred_time && (
                            <span className="flex items-center gap-1">
                              <Clock size={14} />
                              {entry.preferred_time}
                            </span>
                          )}
                          {entry.guest_email && (
                            <span className="flex items-center gap-1">
                              <Mail size={14} />
                              {entry.guest_email}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-2 flex-wrap">
                      {entry.status === "offen" && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleStatusChange(entry.id, "informiert")}
                            className="rounded-full"
                          >
                            <Mail size={14} className="mr-1" />
                            Informieren
                          </Button>
                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedEntry(entry);
                              setConvertTime(entry.preferred_time || "19:00");
                              setShowConvertDialog(true);
                            }}
                            className="rounded-full"
                          >
                            <CheckCircle size={14} className="mr-1" />
                            Einlösen
                          </Button>
                        </>
                      )}
                      {entry.status === "informiert" && (
                        <Button
                          size="sm"
                          onClick={() => {
                            setSelectedEntry(entry);
                            setConvertTime(entry.preferred_time || "19:00");
                            setShowConvertDialog(true);
                          }}
                          className="rounded-full"
                        >
                          <CheckCircle size={14} className="mr-1" />
                          Einlösen
                        </Button>
                      )}
                      {!["eingeloest", "erledigt"].includes(entry.status) && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleStatusChange(entry.id, "erledigt")}
                        >
                          Erledigen
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleDelete(entry.id)}
                      >
                        <Trash2 size={14} className="text-destructive" />
                      </Button>
                    </div>
                  </div>
                  {entry.notes && (
                    <p className="text-sm text-muted-foreground mt-2 bg-muted p-2 rounded">{entry.notes}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">Neuer Wartelisten-Eintrag</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Name *</Label>
                  <Input
                    value={formData.guest_name}
                    onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Telefon *</Label>
                  <Input
                    value={formData.guest_phone}
                    onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>E-Mail</Label>
                <Input
                  type="email"
                  value={formData.guest_email}
                  onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label>Datum *</Label>
                  <Input
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Wunschzeit</Label>
                  <Input
                    type="time"
                    value={formData.preferred_time}
                    onChange={(e) => setFormData({ ...formData, preferred_time: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Personen *</Label>
                  <Input
                    type="number"
                    min="1"
                    max="20"
                    value={formData.party_size}
                    onChange={(e) => setFormData({ ...formData, party_size: parseInt(e.target.value) })}
                    required
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Priorität</Label>
                <Select value={String(formData.priority)} onValueChange={(v) => setFormData({ ...formData, priority: parseInt(v) })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">1 - Niedrig</SelectItem>
                    <SelectItem value="2">2</SelectItem>
                    <SelectItem value="3">3 - Normal</SelectItem>
                    <SelectItem value="4">4</SelectItem>
                    <SelectItem value="5">5 - Hoch</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Notizen</Label>
                <Textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)} className="rounded-full">
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full">
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                Erstellen
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Convert Dialog */}
      <Dialog open={showConvertDialog} onOpenChange={setShowConvertDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">Reservierung erstellen</DialogTitle>
            <DialogDescription>
              Erstellen Sie eine Reservierung für {selectedEntry?.guest_name}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Uhrzeit *</Label>
              <Input
                type="time"
                value={convertTime}
                onChange={(e) => setConvertTime(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Bereich</Label>
              <Select value={convertArea} onValueChange={setConvertArea}>
                <SelectTrigger>
                  <SelectValue placeholder="Optional" />
                </SelectTrigger>
                <SelectContent>
                  {areas.map((a) => (
                    <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setShowConvertDialog(false)} className="rounded-full">
              Abbrechen
            </Button>
            <Button onClick={handleConvert} disabled={submitting || !convertTime} className="rounded-full">
              {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Reservierung erstellen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Waitlist;
