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
  Utensils,
  Music,
  ChefHat,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";
import { useNavigate, useLocation } from "react-router-dom";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const STATUS_CONFIG = {
  draft: { label: "Entwurf", color: "bg-gray-100 text-gray-800" },
  published: { label: "Veröffentlicht", color: "bg-green-100 text-green-800" },
  sold_out: { label: "Ausgebucht", color: "bg-red-100 text-red-800" },
  cancelled: { label: "Abgesagt", color: "bg-orange-100 text-orange-800" },
};

const CATEGORY_CONFIG = {
  VERANSTALTUNG: { 
    label: "Veranstaltungen", 
    description: "Kulturprogramm mit Eintritt (Kabarett, Konzerte, Shows)",
    icon: Music,
    color: "text-purple-600",
    bgColor: "bg-purple-50"
  },
  AKTION: { 
    label: "Aktionen", 
    description: "Sattessen & Themenabende ohne Menüwahl",
    icon: Utensils,
    color: "text-amber-600",
    bgColor: "bg-amber-50"
  },
  AKTION_MENUE: { 
    label: "Menü-Aktionen", 
    description: "Spezielle Menüs mit Auswahlpflicht",
    icon: ChefHat,
    color: "text-emerald-600",
    bgColor: "bg-emerald-50"
  },
};

export const Events = ({ category: propCategory }) => {
  const navigate = useNavigate();
  const location = useLocation();
  
  // Determine category from prop or URL path
  const getCategory = () => {
    if (propCategory) return propCategory;
    if (location.pathname === "/aktionen") return "AKTION";
    if (location.pathname === "/menue-aktionen") return "AKTION_MENUE";
    return "VERANSTALTUNG";
  };
  
  const currentCategory = getCategory();
  const categoryConfig = CATEGORY_CONFIG[currentCategory];
  
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
    price_per_person: 0,
    last_alacarte_reservation_minutes: 120,
    requires_payment: false,
    requires_menu_choice: false,
    content_category: "VERANSTALTUNG",
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

  // Filter events by category
  const filteredEvents = events.filter(e => e.content_category === currentCategory);

  const resetForm = () => {
    const isVeranstaltung = currentCategory === "VERANSTALTUNG";
    const isMenueAktion = currentCategory === "AKTION_MENUE";
    
    setFormData({
      title: "",
      description: "",
      image_url: "",
      start_datetime: "",
      end_datetime: "",
      capacity_total: isVeranstaltung ? 60 : 0,
      booking_mode: isVeranstaltung ? "ticket_only" : "reservation",
      pricing_mode: isVeranstaltung ? "fixed_ticket_price" : "per_person",
      ticket_price: 0,
      price_per_person: 0,
      last_alacarte_reservation_minutes: 120,
      requires_payment: isVeranstaltung,
      requires_menu_choice: isMenueAktion,
      content_category: currentCategory,
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
      capacity_total: event.capacity_total || event.capacity || 50,
      booking_mode: event.booking_mode || "ticket_only",
      pricing_mode: event.pricing_mode || "fixed_ticket_price",
      ticket_price: event.ticket_price || 0,
      price_per_person: event.price_per_person || 0,
      last_alacarte_reservation_minutes: event.last_alacarte_reservation_minutes || 120,
      requires_payment: event.requires_payment || false,
      requires_menu_choice: event.requires_menu_choice || false,
      content_category: event.content_category || "VERANSTALTUNG",
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

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      return format(new Date(dateStr), "dd.MM.yyyy", { locale: de });
    } catch {
      return dateStr;
    }
  };

  const CategoryIcon = CATEGORY_CONFIG[categoryTab]?.icon || Calendar;

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Veranstaltungen & Aktionen
            </h1>
            <p className="text-muted-foreground mt-1">
              Events, Sattessen und Menü-Aktionen verwalten
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={fetchEvents} className="rounded-full">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button
              onClick={() => {
                resetForm(categoryTab);
                setShowCreateDialog(true);
              }}
              className="rounded-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neu
            </Button>
          </div>
        </div>

        {/* Category Tabs */}
        <Tabs value={categoryTab} onValueChange={setCategoryTab}>
          <TabsList className="grid w-full grid-cols-3 h-auto">
            {Object.entries(CATEGORY_CONFIG).map(([key, config]) => {
              const Icon = config.icon;
              return (
                <TabsTrigger 
                  key={key} 
                  value={key}
                  className="flex flex-col sm:flex-row items-center gap-1 sm:gap-2 py-3 data-[state=active]:bg-primary data-[state=active]:text-white"
                >
                  <Icon className="h-4 w-4" />
                  <span className="text-xs sm:text-sm">{config.label}</span>
                  <Badge variant="secondary" className="ml-1 text-xs">
                    {categoryCounts[key]}
                  </Badge>
                </TabsTrigger>
              );
            })}
          </TabsList>

          {/* Tab Content */}
          {Object.keys(CATEGORY_CONFIG).map((category) => (
            <TabsContent key={category} value={category} className="space-y-4">
              {/* Category Description */}
              <Card className={CATEGORY_CONFIG[category].bgColor}>
                <CardContent className="py-3">
                  <p className={`text-sm ${CATEGORY_CONFIG[category].color}`}>
                    {CATEGORY_CONFIG[category].description}
                  </p>
                </CardContent>
              </Card>

              {/* Status Filter */}
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
              ) : filteredEvents.length === 0 ? (
                <Card>
                  <CardContent className="py-12 text-center">
                    <CategoryIcon className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">Keine {CATEGORY_CONFIG[category].label} gefunden</p>
                    <Button 
                      className="mt-4" 
                      onClick={() => {
                        resetForm(category);
                        setShowCreateDialog(true);
                      }}
                    >
                      <Plus className="h-4 w-4 mr-2" />
                      {CATEGORY_CONFIG[category].label.slice(0, -2)} erstellen
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                <div className="grid gap-4">
                  {filteredEvents.map((event) => {
                    const statusConfig = STATUS_CONFIG[event.status] || STATUS_CONFIG.draft;
                    const price = event.ticket_price || event.price_per_person || 0;
                    const hasMenuOptions = event.menu_options && event.menu_options.length > 0;
                    
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
                                  <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1 flex-wrap">
                                    {event.date && (
                                      <span className="flex items-center gap-1">
                                        <Calendar className="h-4 w-4" />
                                        {formatDate(event.date)}
                                      </span>
                                    )}
                                    {event.all_dates && event.all_dates.length > 1 && (
                                      <Badge variant="outline" className="text-xs">
                                        {event.all_dates.length} Termine
                                      </Badge>
                                    )}
                                    {event.default_start_time && (
                                      <span className="flex items-center gap-1">
                                        <Clock className="h-4 w-4" />
                                        {event.default_start_time} Uhr
                                      </span>
                                    )}
                                    {(event.capacity_total || event.capacity) && (
                                      <span className="flex items-center gap-1">
                                        <Users className="h-4 w-4" />
                                        {event.booked_count || 0}/{event.capacity_total || event.capacity || "∞"} Plätze
                                      </span>
                                    )}
                                    {price > 0 && (
                                      <span className="flex items-center gap-1">
                                        <Euro className="h-4 w-4" />
                                        {price.toFixed(2)} €
                                      </span>
                                    )}
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-wrap">
                                  <Badge className={statusConfig.color}>
                                    {statusConfig.label}
                                  </Badge>
                                  {event.requires_menu_choice && (
                                    <Badge className="bg-emerald-100 text-emerald-800">
                                      <ChefHat className="h-3 w-3 mr-1" />
                                      Menüwahl
                                    </Badge>
                                  )}
                                  {event.requires_payment && (
                                    <Badge className="bg-blue-100 text-blue-800">
                                      <Ticket className="h-3 w-3 mr-1" />
                                      Eintritt
                                    </Badge>
                                  )}
                                </div>
                              </div>

                              {/* Menu Options Preview */}
                              {hasMenuOptions && (
                                <div className="mt-2 flex flex-wrap gap-1">
                                  {event.menu_options.slice(0, 3).map((opt, idx) => (
                                    <Badge key={idx} variant="outline" className="text-xs">
                                      {opt.title}
                                    </Badge>
                                  ))}
                                  {event.menu_options.length > 3 && (
                                    <Badge variant="outline" className="text-xs">
                                      +{event.menu_options.length - 3} weitere
                                    </Badge>
                                  )}
                                </div>
                              )}
                              
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
                                
                                {event.requires_menu_choice && (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => navigate(`/events/${event.id}/products`)}
                                    className="rounded-full"
                                  >
                                    <UtensilsCrossed className="h-4 w-4 mr-1" />
                                    Menü-Optionen
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
            </TabsContent>
          ))}
        </Tabs>
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">
              {editingEvent ? "Event bearbeiten" : `Neue ${CATEGORY_CONFIG[formData.content_category]?.label.slice(0, -2) || "Veranstaltung"}`}
            </DialogTitle>
            <DialogDescription>
              {editingEvent ? "Ändern Sie die Event-Details" : CATEGORY_CONFIG[formData.content_category]?.description}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              {/* Category Selection (only for new) */}
              {!editingEvent && (
                <div className="space-y-2">
                  <Label>Kategorie *</Label>
                  <Select 
                    value={formData.content_category} 
                    onValueChange={(v) => {
                      const isVeranstaltung = v === "VERANSTALTUNG";
                      const isMenueAktion = v === "AKTION_MENUE";
                      setFormData({ 
                        ...formData, 
                        content_category: v,
                        requires_payment: isVeranstaltung,
                        requires_menu_choice: isMenueAktion,
                        booking_mode: isVeranstaltung ? "ticket_only" : "reservation",
                      });
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(CATEGORY_CONFIG).map(([key, config]) => (
                        <SelectItem key={key} value={key}>
                          {config.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}

              <div className="space-y-2">
                <Label>Titel *</Label>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  required
                  placeholder="z.B. Kabarett-Abend, Spareribs Sattessen"
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
                  <Label>Kapazität</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.capacity_total}
                    onChange={(e) => setFormData({ ...formData, capacity_total: parseInt(e.target.value) || 0 })}
                    placeholder="0 = unbegrenzt"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Preis pro Person (€)</Label>
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    value={formData.content_category === "VERANSTALTUNG" ? formData.ticket_price : formData.price_per_person}
                    onChange={(e) => {
                      const price = parseFloat(e.target.value) || 0;
                      if (formData.content_category === "VERANSTALTUNG") {
                        setFormData({ ...formData, ticket_price: price });
                      } else {
                        setFormData({ ...formData, price_per_person: price });
                      }
                    }}
                  />
                </div>
              </div>

              {/* Options based on category */}
              <div className="space-y-4 pt-2 border-t">
                {formData.content_category === "VERANSTALTUNG" && (
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Eintritt erforderlich</Label>
                      <p className="text-xs text-muted-foreground">Zahlung vor Veranstaltung</p>
                    </div>
                    <Switch
                      checked={formData.requires_payment}
                      onCheckedChange={(v) => setFormData({ ...formData, requires_payment: v })}
                    />
                  </div>
                )}

                {formData.content_category === "AKTION_MENUE" && (
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Menüauswahl erforderlich</Label>
                      <p className="text-xs text-muted-foreground">Gast muss bei Buchung wählen</p>
                    </div>
                    <Switch
                      checked={formData.requires_menu_choice}
                      onCheckedChange={(v) => setFormData({ ...formData, requires_menu_choice: v })}
                    />
                  </div>
                )}

                <div className="space-y-2">
                  <Label>Letzte À-la-carte Reservierung vor Event (Min.)</Label>
                  <Input
                    type="number"
                    min="0"
                    value={formData.last_alacarte_reservation_minutes}
                    onChange={(e) => setFormData({ ...formData, last_alacarte_reservation_minutes: parseInt(e.target.value) || 0 })}
                  />
                  <p className="text-xs text-muted-foreground">
                    Wie viele Minuten vor Event-Start sind normale Reservierungen noch möglich?
                  </p>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)}>
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Speichern...
                  </>
                ) : editingEvent ? (
                  "Aktualisieren"
                ) : (
                  "Erstellen"
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Events;
