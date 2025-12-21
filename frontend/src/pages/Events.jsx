import React, { useState, useEffect } from "react";
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
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";
import {
  Calendar,
  Plus,
  RefreshCw,
  Users,
  Clock,
  Euro,
  Loader2,
  Edit,
  Trash2,
  Eye,
  Send,
  XCircle,
  CheckCircle,
  Ticket,
  UtensilsCrossed,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";
import { useNavigate } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const STATUS_CONFIG = {
  draft: { label: "Entwurf", color: "bg-gray-100 text-gray-800" },
  published: { label: "Veröffentlicht", color: "bg-green-100 text-green-800" },
  sold_out: { label: "Ausgebucht", color: "bg-red-100 text-red-800" },
  cancelled: { label: "Abgesagt", color: "bg-orange-100 text-orange-800" },
};

const MODE_CONFIG = {
  ticket_only: { label: "Ticket (Kabarett)", icon: Ticket },
  reservation_with_preorder: { label: "Mit Vorbestellung", icon: UtensilsCrossed },
};

export const Events = () => {
  const navigate = useNavigate();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    title: "",
    description: "",
    image_url: "",
    start_datetime: "",
    end_datetime: "",
    capacity_total: 50,
    booking_mode: "ticket_only",
    pricing_mode: "fixed_ticket_price",
    ticket_price: 0,
    last_alacarte_reservation_minutes: 120,
    requires_payment: false,
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchEvents();
  }, [statusFilter]);

  const fetchEvents = async () => {
    setLoading(true);
    try {
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const response = await axios.get(`${BACKEND_URL}/api/events`, { headers, params });
      setEvents(response.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Events");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      title: "",
      description: "",
      image_url: "",
      start_datetime: "",
      end_datetime: "",
      capacity_total: 50,
      booking_mode: "ticket_only",
      pricing_mode: "fixed_ticket_price",
      ticket_price: 0,
      last_alacarte_reservation_minutes: 120,
      requires_payment: false,
    });
    setEditingEvent(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const data = { ...formData };
      if (editingEvent) {
        await axios.patch(`${BACKEND_URL}/api/events/${editingEvent.id}`, data, { headers });
        toast.success("Event aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/events`, data, { headers });
        toast.success("Event erstellt");
      }
      setShowCreateDialog(false);
      resetForm();
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (event) => {
    setEditingEvent(event);
    setFormData({
      title: event.title || "",
      description: event.description || "",
      image_url: event.image_url || "",
      start_datetime: event.start_datetime?.slice(0, 16) || "",
      end_datetime: event.end_datetime?.slice(0, 16) || "",
      capacity_total: event.capacity_total || 50,
      booking_mode: event.booking_mode || "ticket_only",
      pricing_mode: event.pricing_mode || "fixed_ticket_price",
      ticket_price: event.ticket_price || 0,
      last_alacarte_reservation_minutes: event.last_alacarte_reservation_minutes || 120,
      requires_payment: event.requires_payment || false,
    });
    setShowCreateDialog(true);
  };

  const handlePublish = async (eventId) => {
    try {
      await axios.post(`${BACKEND_URL}/api/events/${eventId}/publish`, {}, { headers });
      toast.success("Event veröffentlicht");
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Veröffentlichen");
    }
  };

  const handleCancel = async (eventId) => {
    if (!window.confirm("Event wirklich absagen? Alle Buchungen werden storniert.")) return;
    try {
      await axios.post(`${BACKEND_URL}/api/events/${eventId}/cancel`, {}, { headers });
      toast.success("Event abgesagt");
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Absagen");
    }
  };

  const handleDelete = async (eventId) => {
    if (!window.confirm("Event wirklich archivieren?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/events/${eventId}`, { headers });
      toast.success("Event archiviert");
      fetchEvents();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Archivieren");
    }
  };

  const formatDateTime = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return format(new Date(dateStr), "dd.MM.yyyy HH:mm", { locale: de });
    } catch {
      return dateStr;
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Veranstaltungen
            </h1>
            <p className="text-muted-foreground mt-1">
              Events und Sonderveranstaltungen verwalten
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchEvents} className="rounded-full">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button
              onClick={() => {
                resetForm();
                setShowCreateDialog(true);
              }}
              className="rounded-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neues Event
            </Button>
          </div>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex gap-4 items-center">
              <Label>Status:</Label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle</SelectItem>
                  <SelectItem value="draft">Entwürfe</SelectItem>
                  <SelectItem value="published">Veröffentlicht</SelectItem>
                  <SelectItem value="sold_out">Ausgebucht</SelectItem>
                  <SelectItem value="cancelled">Abgesagt</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Events List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
          </div>
        ) : events.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Events gefunden</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {events.map((event) => {
              const ModeIcon = MODE_CONFIG[event.booking_mode]?.icon || Ticket;
              const statusConfig = STATUS_CONFIG[event.status] || STATUS_CONFIG.draft;
              
              return (
                <Card key={event.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-start gap-4">
                      {/* Image */}
                      {event.image_url && (
                        <img
                          src={event.image_url}
                          alt={event.title}
                          className="w-24 h-24 object-cover rounded-lg hidden sm:block"
                        />
                      )}
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <h3 className="font-semibold text-lg">{event.title}</h3>
                            <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                              <span className="flex items-center gap-1">
                                <Calendar className="h-4 w-4" />
                                {formatDateTime(event.start_datetime)}
                              </span>
                              <span className="flex items-center gap-1">
                                <Users className="h-4 w-4" />
                                {event.booked_count || 0}/{event.capacity_total} Plätze
                              </span>
                              {event.ticket_price > 0 && (
                                <span className="flex items-center gap-1">
                                  <Euro className="h-4 w-4" />
                                  {event.ticket_price?.toFixed(2)} €
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <Badge className={statusConfig.color}>
                              {statusConfig.label}
                            </Badge>
                            <Badge variant="outline" className="flex items-center gap-1">
                              <ModeIcon className="h-3 w-3" />
                              {MODE_CONFIG[event.booking_mode]?.label}
                            </Badge>
                          </div>
                        </div>
                        
                        {/* Actions */}
                        <div className="flex items-center gap-2 mt-4 flex-wrap">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => navigate(`/events/${event.id}/bookings`)}
                            className="rounded-full"
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            Buchungen
                          </Button>
                          
                          {event.booking_mode === "reservation_with_preorder" && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => navigate(`/events/${event.id}/products`)}
                              className="rounded-full"
                            >
                              <UtensilsCrossed className="h-4 w-4 mr-1" />
                              Optionen
                            </Button>
                          )}
                          
                          {event.status === "draft" && (
                            <Button
                              size="sm"
                              onClick={() => handlePublish(event.id)}
                              className="rounded-full bg-green-600 hover:bg-green-700"
                            >
                              <Send className="h-4 w-4 mr-1" />
                              Veröffentlichen
                            </Button>
                          )}
                          
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleEdit(event)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          
                          {event.status === "published" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-orange-600"
                              onClick={() => handleCancel(event.id)}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          )}
                          
                          {event.status === "draft" && (
                            <Button
                              size="sm"
                              variant="ghost"
                              className="text-red-600"
                              onClick={() => handleDelete(event.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">
              {editingEvent ? "Event bearbeiten" : "Neues Event"}
            </DialogTitle>
            <DialogDescription>
              {editingEvent ? "Ändern Sie die Event-Details" : "Erstellen Sie eine neue Veranstaltung"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Titel *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                  placeholder="z.B. Kabarett-Abend"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Beschreibung</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={4}
                  placeholder="Beschreiben Sie das Event..."
                />
              </div>
              
              <div className="space-y-2">
                <Label>Bild-URL</Label>
                <Input
                  value={formData.image_url}
                  onChange={(e) => setFormData({ ...formData, image_url: e.target.value })}
                  placeholder="https://..."
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start *</Label>
                  <Input
                    type="datetime-local"
                    value={formData.start_datetime}
                    onChange={(e) => setFormData({ ...formData, start_datetime: e.target.value })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Ende</Label>
                  <Input
                    type="datetime-local"
                    value={formData.end_datetime}
                    onChange={(e) => setFormData({ ...formData, end_datetime: e.target.value })}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Kapazität *</Label>
                  <Input
                    type="number"
                    min="1"
                    value={formData.capacity_total}
                    onChange={(e) => setFormData({ ...formData, capacity_total: parseInt(e.target.value) || 1 })}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label>Buchungsmodus</Label>
                  <Select
                    value={formData.booking_mode}
                    onValueChange={(v) => setFormData({ ...formData, booking_mode: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ticket_only">Ticket (Kabarett)</SelectItem>
                      <SelectItem value="reservation_with_preorder">Mit Vorbestellung (Gänseabend)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Ticketpreis (€)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.ticket_price}
                    onChange={(e) => setFormData({ ...formData, ticket_price: parseFloat(e.target.value) || 0 })}
                  />
                </div>
                <div className="space-y-2">
                  <Label>Letzte Reservierung (Min. vorher)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.last_alacarte_reservation_minutes}
                    onChange={(e) => setFormData({ ...formData, last_alacarte_reservation_minutes: parseInt(e.target.value) || 0 })}
                  />
                </div>
              </div>
              
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <Label>Zahlung erforderlich</Label>
                  <p className="text-sm text-muted-foreground">
                    Gäste müssen bei Buchung bezahlen
                  </p>
                </div>
                <Switch
                  checked={formData.requires_payment}
                  onCheckedChange={(v) => setFormData({ ...formData, requires_payment: v })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                {editingEvent ? "Speichern" : "Erstellen"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Events;
