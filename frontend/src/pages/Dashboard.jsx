import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { reservationsApi, areasApi } from "../lib/api";
import { t } from "../lib/i18n";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
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
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  Search,
  Plus,
  RefreshCw,
  Users,
  Clock,
  Phone,
  MapPin,
  Calendar,
  Loader2,
  CheckCircle,
  XCircle,
  UserCheck,
  LogOut,
  Footprints,
  FileText,
  Download,
  MessageCircle,
  AlertTriangle,
  Ban,
  Bell,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

// Status configuration - single source of truth
const STATUS_CONFIG = {
  neu: { 
    label: "Neu", 
    next: "bestaetigt", 
    nextLabel: "Bestätigen",
    icon: Clock,
    className: "status-neu"
  },
  bestaetigt: { 
    label: "Bestätigt", 
    next: "angekommen", 
    nextLabel: "Angekommen",
    icon: CheckCircle,
    className: "status-bestaetigt"
  },
  angekommen: { 
    label: "Angekommen", 
    next: "abgeschlossen", 
    nextLabel: "Abschließen",
    icon: UserCheck,
    className: "status-angekommen"
  },
  abgeschlossen: { 
    label: "Abgeschlossen", 
    next: null,
    icon: LogOut,
    className: "status-abgeschlossen"
  },
  no_show: { 
    label: "No-Show", 
    next: null,
    icon: XCircle,
    className: "status-no_show"
  },
  storniert: { 
    label: "Storniert", 
    next: null,
    icon: XCircle,
    className: "status-storniert"
  },
};

// Quick action button component for 1-click status changes
const QuickActionButton = ({ reservation, onStatusChange, disabled }) => {
  const config = STATUS_CONFIG[reservation.status];
  if (!config?.next) return null;
  
  return (
    <Button
      size="lg"
      className="rounded-full min-w-[140px] h-12 font-bold text-base"
      onClick={(e) => {
        e.stopPropagation();
        onStatusChange(reservation.id, config.next);
      }}
      disabled={disabled}
      data-testid={`quick-action-${reservation.id}`}
    >
      → {config.nextLabel}
    </Button>
  );
};

// No-Show button component
const NoShowButton = ({ reservation, onStatusChange, disabled }) => {
  const status = reservation.status;
  // Can only mark as no-show if not terminal
  if (["abgeschlossen", "no_show", "storniert"].includes(status)) return null;
  
  return (
    <Button
      size="lg"
      variant="destructive"
      className="rounded-full h-12 px-6 font-bold"
      onClick={(e) => {
        e.stopPropagation();
        onStatusChange(reservation.id, "no_show");
      }}
      disabled={disabled}
      data-testid={`no-show-${reservation.id}`}
    >
      No-Show
    </Button>
  );
};

export const Dashboard = () => {
  const { isSchichtleiter } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(null); // Track which reservation is loading
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [areaFilter, setAreaFilter] = useState("all");
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showWalkInDialog, setShowWalkInDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);
  const [formData, setFormData] = useState({
    guest_name: "",
    guest_phone: "",
    guest_email: "",
    party_size: 2,
    date: format(new Date(), "yyyy-MM-dd"),
    time: "19:00",
    area_id: "",
    notes: "",
  });
  const [walkInData, setWalkInData] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    area_id: "",
    table_number: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [guestCache, setGuestCache] = useState({}); // Cache for guest flags

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { date: selectedDate };
      if (statusFilter !== "all") params.status = statusFilter;
      if (areaFilter !== "all") params.area_id = areaFilter;
      if (search) params.search = search;

      const [resRes, areasRes] = await Promise.all([
        reservationsApi.getAll(params),
        areasApi.getAll(),
      ]);
      setReservations(resRes.data);
      setAreas(areasRes.data);
      
      // Fetch guest flags for reservations with phone numbers
      const phonesToCheck = [...new Set(resRes.data.filter(r => r.guest_phone).map(r => r.guest_phone))];
      const guestFlags = {};
      for (const phone of phonesToCheck.slice(0, 20)) { // Limit to avoid too many requests
        try {
          const guestRes = await axios.get(`${BACKEND_URL}/api/guests/check/${encodeURIComponent(phone)}`, { headers });
          guestFlags[phone] = guestRes.data;
        } catch (e) {
          // Ignore errors
        }
      }
      setGuestCache(guestFlags);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
    }
  }, [selectedDate, statusFilter, areaFilter, search]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Polling every 30 seconds
  useEffect(() => {
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Quick status change - optimized for 1-click
  const handleQuickStatusChange = async (reservationId, newStatus) => {
    setActionLoading(reservationId);
    try {
      await reservationsApi.updateStatus(reservationId, newStatus);
      toast.success(`Status: ${STATUS_CONFIG[newStatus]?.label || newStatus}`);
      fetchData();
      setShowDetailDialog(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Ändern des Status");
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const dataToSend = { ...formData };
      if (!dataToSend.area_id) delete dataToSend.area_id;
      if (!dataToSend.guest_email) delete dataToSend.guest_email;
      if (!dataToSend.notes) delete dataToSend.notes;
      
      await reservationsApi.create(dataToSend);
      toast.success("Reservierung erstellt");
      setShowCreateDialog(false);
      setFormData({
        guest_name: "",
        guest_phone: "",
        guest_email: "",
        party_size: 2,
        date: selectedDate,
        time: "19:00",
        area_id: "",
        notes: "",
      });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  };

  // Walk-In: Sofortige Erfassung
  const handleWalkIn = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await axios.post(`${BACKEND_URL}/api/walk-ins`, walkInData, { headers });
      toast.success("Walk-In erfasst und als 'Angekommen' markiert");
      setShowWalkInDialog(false);
      setWalkInData({
        guest_name: "",
        guest_phone: "",
        party_size: 2,
        area_id: "",
        table_number: "",
        notes: "",
      });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Walk-In");
    } finally {
      setSubmitting(false);
    }
  };

  // PDF Export
  const handleExportPDF = async () => {
    setExportLoading(true);
    try {
      const params = new URLSearchParams({ date: selectedDate });
      if (areaFilter !== "all") params.append("area_id", areaFilter);
      
      const response = await axios.get(`${BACKEND_URL}/api/export/table-plan?${params}`, {
        headers,
        responseType: "blob",
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `tischplan_${selectedDate}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success("PDF heruntergeladen");
    } catch (err) {
      toast.error("Fehler beim PDF-Export");
    } finally {
      setExportLoading(false);
    }
  };

  // WhatsApp Reminder - generates deep link and opens it
  const handleWhatsAppReminder = async (reservation) => {
    if (!reservation.guest_phone) {
      toast.error("Keine Telefonnummer hinterlegt");
      return;
    }
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/reservations/${reservation.id}/whatsapp-reminder`,
        {},
        { headers }
      );
      // Open WhatsApp link in new tab
      window.open(response.data.whatsapp_link, "_blank");
      toast.success("WhatsApp wird geöffnet...");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen des WhatsApp-Links");
    }
  };

  // Get guest flag info
  const getGuestFlag = (phone) => {
    if (!phone) return null;
    return guestCache[phone];
  };

  const getAreaName = (areaId) => {
    const area = areas.find((a) => a.id === areaId);
    return area?.name || "-";
  };

  // Calculate stats
  const stats = {
    total: reservations.length,
    neu: reservations.filter((r) => r.status === "neu").length,
    bestaetigt: reservations.filter((r) => r.status === "bestaetigt").length,
    angekommen: reservations.filter((r) => r.status === "angekommen").length,
    guests: reservations.reduce((sum, r) => sum + r.party_size, 0),
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Service-Terminal
            </h1>
            <p className="text-muted-foreground mt-1">
              {format(new Date(selectedDate), "EEEE, d. MMMM yyyy", { locale: de })}
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              variant="outline"
              size="lg"
              onClick={fetchData}
              data-testid="refresh-button"
              className="rounded-full h-12 w-12"
            >
              <RefreshCw size={20} className={loading ? "animate-spin" : ""} />
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={handleExportPDF}
              disabled={exportLoading}
              data-testid="export-pdf-button"
              className="rounded-full h-12 px-4"
              title="Tischplan als PDF"
            >
              {exportLoading ? <Loader2 size={20} className="animate-spin" /> : <Download size={20} />}
            </Button>
            {isSchichtleiter() && (
              <>
                <Button
                  variant="secondary"
                  size="lg"
                  onClick={() => setShowWalkInDialog(true)}
                  data-testid="walk-in-button"
                  className="rounded-full h-12 px-6 font-bold"
                >
                  <Footprints size={20} className="mr-2" />
                  Walk-In
                </Button>
                <Button
                  size="lg"
                  onClick={() => {
                    setFormData({ ...formData, date: selectedDate });
                    setShowCreateDialog(true);
                  }}
                  data-testid="new-reservation-button"
                  className="rounded-full h-12 px-6 font-bold"
                >
                  <Plus size={20} className="mr-2" />
                  Neue Reservierung
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Stats Cards - Larger touch targets */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[
            { label: "Gesamt", value: stats.total, icon: Calendar, color: "primary" },
            { label: "Neu", value: stats.neu, icon: Clock, color: "yellow" },
            { label: "Bestätigt", value: stats.bestaetigt, icon: CheckCircle, color: "blue" },
            { label: "Angekommen", value: stats.angekommen, icon: UserCheck, color: "green" },
            { label: "Gäste", value: stats.guests, icon: Users, color: "muted" },
          ].map((stat) => (
            <Card key={stat.label} className="bg-card hover:shadow-md transition-shadow cursor-default">
              <CardContent className="p-4 md:p-6">
                <div className="flex items-center gap-3">
                  <div className={`p-3 rounded-full bg-${stat.color}/10`}>
                    <stat.icon size={24} className="text-primary" />
                  </div>
                  <div>
                    <p className="text-3xl font-bold">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.label}</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Filters - Larger inputs */}
        <Card className="bg-card">
          <CardContent className="p-4">
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground" size={20} />
                  <Input
                    placeholder="Suche nach Name oder Telefon..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-12 h-12 text-base"
                    data-testid="search-input"
                  />
                </div>
              </div>
              <div className="flex gap-3 flex-wrap">
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-auto h-12"
                  data-testid="date-filter"
                />
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[160px] h-12" data-testid="status-filter">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Status</SelectItem>
                    {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                      <SelectItem key={key} value={key}>{config.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={areaFilter} onValueChange={setAreaFilter}>
                  <SelectTrigger className="w-[160px] h-12" data-testid="area-filter">
                    <SelectValue placeholder="Bereich" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Bereiche</SelectItem>
                    {areas.map((a) => (
                      <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reservations List - Optimized for touch */}
        <div className="space-y-3">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-10 w-10 animate-spin text-primary" />
            </div>
          ) : reservations.length === 0 ? (
            <Card className="bg-card">
              <CardContent className="py-16 text-center">
                <Calendar className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
                <p className="text-lg text-muted-foreground">Keine Reservierungen für diesen Tag</p>
              </CardContent>
            </Card>
          ) : (
            reservations.map((reservation) => {
              const statusConfig = STATUS_CONFIG[reservation.status];
              const isLoading = actionLoading === reservation.id;
              
              return (
                <Card
                  key={reservation.id}
                  className="bg-card hover:shadow-lg transition-all cursor-pointer group"
                  onClick={() => {
                    setSelectedReservation(reservation);
                    setShowDetailDialog(true);
                  }}
                  data-testid={`reservation-${reservation.id}`}
                >
                  <CardContent className="p-4 md:p-6">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                      {/* Main Info */}
                      <div className="flex items-center gap-4 flex-1">
                        {/* Time - Large & prominent */}
                        <div className="w-20 text-center flex-shrink-0">
                          <p className="text-2xl font-bold">{reservation.time}</p>
                          <p className="text-xs text-muted-foreground">Uhr</p>
                        </div>
                        
                        <div className="h-14 w-px bg-border hidden sm:block" />
                        
                        {/* Guest Info */}
                        <div className="flex-1 min-w-0">
                          <p className="font-semibold text-lg truncate">{reservation.guest_name}</p>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1 flex-wrap">
                            <span className="flex items-center gap-1">
                              <Users size={16} />
                              <span className="font-medium">{reservation.party_size}</span> Pers.
                            </span>
                            <span className="flex items-center gap-1">
                              <Phone size={16} />
                              {reservation.guest_phone}
                            </span>
                            {reservation.area_id && (
                              <span className="flex items-center gap-1">
                                <MapPin size={16} />
                                {getAreaName(reservation.area_id)}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Status & Actions */}
                      <div className="flex items-center gap-3 flex-wrap justify-end">
                        <Badge className={`${statusConfig?.className} border text-sm px-4 py-2`}>
                          {statusConfig?.label || reservation.status}
                        </Badge>
                        
                        {/* Quick Actions - 1 Click */}
                        {isSchichtleiter() && (
                          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                            <QuickActionButton
                              reservation={reservation}
                              onStatusChange={handleQuickStatusChange}
                              disabled={isLoading}
                            />
                            <NoShowButton
                              reservation={reservation}
                              onStatusChange={handleQuickStatusChange}
                              disabled={isLoading}
                            />
                          </div>
                        )}
                        
                        {isLoading && <Loader2 className="h-5 w-5 animate-spin" />}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">Neue Reservierung</DialogTitle>
            <DialogDescription>Erfassen Sie eine neue Reservierung</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="guest_name">Gastname *</Label>
                  <Input
                    id="guest_name"
                    value={formData.guest_name}
                    onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                    required
                    className="h-11"
                    data-testid="form-guest-name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="guest_phone">Telefon *</Label>
                  <Input
                    id="guest_phone"
                    value={formData.guest_phone}
                    onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })}
                    required
                    className="h-11"
                    data-testid="form-guest-phone"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="guest_email">E-Mail (optional)</Label>
                <Input
                  id="guest_email"
                  type="email"
                  value={formData.guest_email}
                  onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })}
                  className="h-11"
                  data-testid="form-guest-email"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date">Datum *</Label>
                  <Input
                    id="date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    className="h-11"
                    data-testid="form-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="time">Uhrzeit *</Label>
                  <Input
                    id="time"
                    type="time"
                    value={formData.time}
                    onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    required
                    className="h-11"
                    data-testid="form-time"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="party_size">Personen *</Label>
                  <Input
                    id="party_size"
                    type="number"
                    min="1"
                    max="20"
                    value={formData.party_size}
                    onChange={(e) => setFormData({ ...formData, party_size: parseInt(e.target.value) || 1 })}
                    required
                    className="h-11"
                    data-testid="form-party-size"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="area">Bereich</Label>
                <Select
                  value={formData.area_id}
                  onValueChange={(v) => setFormData({ ...formData, area_id: v })}
                >
                  <SelectTrigger className="h-11" data-testid="form-area">
                    <SelectValue placeholder="Bereich wählen..." />
                  </SelectTrigger>
                  <SelectContent>
                    {areas.map((a) => (
                      <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">Notizen</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="min-h-[80px]"
                  data-testid="form-notes"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)} className="rounded-full">
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full" data-testid="form-submit">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                Erstellen
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog - Optimized for quick actions */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-[500px]">
          {selectedReservation && (
            <>
              <DialogHeader>
                <DialogTitle className="font-serif text-2xl">{selectedReservation.guest_name}</DialogTitle>
                <DialogDescription>Reservierung #{selectedReservation.id.slice(0, 8)}</DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                {/* Status with Actions */}
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <Badge className={`${STATUS_CONFIG[selectedReservation.status]?.className} border mt-1`}>
                      {STATUS_CONFIG[selectedReservation.status]?.label}
                    </Badge>
                  </div>
                  {isSchichtleiter() && (
                    <div className="flex gap-2">
                      <QuickActionButton
                        reservation={selectedReservation}
                        onStatusChange={handleQuickStatusChange}
                        disabled={actionLoading === selectedReservation.id}
                      />
                      <NoShowButton
                        reservation={selectedReservation}
                        onStatusChange={handleQuickStatusChange}
                        disabled={actionLoading === selectedReservation.id}
                      />
                    </div>
                  )}
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Datum</p>
                    <p className="font-medium text-lg">{selectedReservation.date}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Uhrzeit</p>
                    <p className="font-medium text-lg">{selectedReservation.time} Uhr</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Personen</p>
                    <p className="font-medium text-lg">{selectedReservation.party_size}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Bereich</p>
                    <p className="font-medium text-lg">{getAreaName(selectedReservation.area_id) || "-"}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-muted-foreground">Telefon</p>
                  <a href={`tel:${selectedReservation.guest_phone}`} className="font-medium text-lg text-primary hover:underline">
                    {selectedReservation.guest_phone}
                  </a>
                </div>

                {selectedReservation.guest_email && (
                  <div>
                    <p className="text-sm text-muted-foreground">E-Mail</p>
                    <a href={`mailto:${selectedReservation.guest_email}`} className="font-medium text-primary hover:underline">
                      {selectedReservation.guest_email}
                    </a>
                  </div>
                )}

                {selectedReservation.notes && (
                  <div>
                    <p className="text-sm text-muted-foreground">Notizen</p>
                    <p className="font-medium bg-muted p-3 rounded-lg">{selectedReservation.notes}</p>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDetailDialog(false)} className="rounded-full">
                  Schließen
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Walk-In Dialog - Schnellerfassung */}
      <Dialog open={showWalkInDialog} onOpenChange={setShowWalkInDialog}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl flex items-center gap-2">
              <Footprints className="h-6 w-6" />
              Walk-In erfassen
            </DialogTitle>
            <DialogDescription>
              Gast ist bereits da - wird sofort als "Angekommen" markiert
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleWalkIn}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="walkin_name">Name *</Label>
                  <Input
                    id="walkin_name"
                    value={walkInData.guest_name}
                    onChange={(e) => setWalkInData({ ...walkInData, guest_name: e.target.value })}
                    required
                    className="h-11"
                    placeholder="Gastname"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="walkin_size">Personen *</Label>
                  <Input
                    id="walkin_size"
                    type="number"
                    min="1"
                    max="20"
                    value={walkInData.party_size}
                    onChange={(e) => setWalkInData({ ...walkInData, party_size: parseInt(e.target.value) || 1 })}
                    required
                    className="h-11"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="walkin_area">Bereich</Label>
                  <Select
                    value={walkInData.area_id}
                    onValueChange={(v) => setWalkInData({ ...walkInData, area_id: v })}
                  >
                    <SelectTrigger className="h-11">
                      <SelectValue placeholder="Wählen..." />
                    </SelectTrigger>
                    <SelectContent>
                      {areas.map((a) => (
                        <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="walkin_table">Tisch-Nr.</Label>
                  <Input
                    id="walkin_table"
                    value={walkInData.table_number}
                    onChange={(e) => setWalkInData({ ...walkInData, table_number: e.target.value })}
                    className="h-11"
                    placeholder="z.B. T5"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="walkin_phone">Telefon (optional)</Label>
                <Input
                  id="walkin_phone"
                  value={walkInData.guest_phone}
                  onChange={(e) => setWalkInData({ ...walkInData, guest_phone: e.target.value })}
                  className="h-11"
                  placeholder="Für Rückfragen"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="walkin_notes">Notizen</Label>
                <Textarea
                  id="walkin_notes"
                  value={walkInData.notes}
                  onChange={(e) => setWalkInData({ ...walkInData, notes: e.target.value })}
                  className="min-h-[60px]"
                  placeholder="z.B. Kinderstuhl, Allergie..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowWalkInDialog(false)} className="rounded-full">
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full bg-green-600 hover:bg-green-700">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <UserCheck className="h-4 w-4 mr-2" />}
                Walk-In erfassen
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Dashboard;
