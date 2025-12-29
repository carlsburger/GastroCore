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
  CreditCard,
  Send,
  Sparkles,
  Theater,
  TrendingUp,
} from "lucide-react";
import { format, addDays, parseISO } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

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

// Payment Status configuration
const PAYMENT_STATUS_CONFIG = {
  unpaid: { label: "Zahlung offen", className: "bg-amber-100 text-amber-700 border-amber-300" },
  payment_pending: { label: "Ausstehend", className: "bg-yellow-100 text-yellow-700 border-yellow-300" },
  paid: { label: "Bezahlt", className: "bg-green-100 text-green-700 border-green-300" },
  partially_paid: { label: "Teilweise", className: "bg-orange-100 text-orange-700 border-orange-300" },
  refunded: { label: "Erstattet", className: "bg-purple-100 text-purple-700 border-purple-300" },
  failed: { label: "Fehlgeschlagen", className: "bg-red-100 text-red-700 border-red-300" },
};

// Payment Badge component
const PaymentBadge = ({ paymentStatus, amount, paymentRequired }) => {
  // Show badge if:
  // 1. There's a payment status other than null
  // 2. Payment is required and status is unpaid (to show "Zahlung offen")
  if (!paymentStatus && !paymentRequired) return null;
  
  // If no payment status but payment is required, show as unpaid
  const effectiveStatus = paymentStatus || (paymentRequired ? "unpaid" : null);
  if (!effectiveStatus) return null;
  
  // Don't show badge for unpaid if no amount is set (no payment required)
  if (effectiveStatus === "unpaid" && (!amount || amount <= 0)) return null;
  
  const config = PAYMENT_STATUS_CONFIG[effectiveStatus];
  if (!config) return null;
  
  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <Badge className={`${config.className} border text-xs px-2 py-1`}>
            <CreditCard className="h-3 w-3 mr-1" />
            {config.label}
          </Badge>
        </TooltipTrigger>
        <TooltipContent>
          <p>Zahlung: {config.label}</p>
          {amount > 0 && <p>Betrag: {amount.toFixed(2)} €</p>}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
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
  const [showPhoneDialog, setShowPhoneDialog] = useState(false);  // Telefon-Schnellanlage
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [exportLoading, setExportLoading] = useState(false);
  
  // Occasions & Special Requests (Go-Live Sprint)
  const [occasions, setOccasions] = useState([]);
  const [specialRequests, setSpecialRequests] = useState([]);
  
  const [formData, setFormData] = useState({
    guest_name: "",
    guest_phone: "",
    guest_email: "",
    party_size: 2,
    date: format(new Date(), "yyyy-MM-dd"),
    time: "19:00",
    area_id: "",
    notes: "",
    occasion: "none",
    special_requests: [],
  });
  
  // Telefon-Schnellanlage Data (Go-Live Sprint)
  const [phoneData, setPhoneData] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    date: format(addDays(new Date(), 1), "yyyy-MM-dd"),  // Default: morgen
    time: "19:00",
    area_id: "",
    occasion: "none",
    special_requests: [],
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
  
  // Events Dashboard State (3 Kategorien: VA, AK, MA)
  const [eventsSummary, setEventsSummary] = useState({
    kulturveranstaltungen: { events: [], total: 0, label: "Kulturveranstaltungen", prefix: "VA" },
    aktionen: { events: [], total: 0, label: "Aktionen", prefix: "AK" },
    menuaktionen: { events: [], total: 0, label: "Menüaktionen", prefix: "MA" },
    default_capacity: 95
  });
  const [eventsLoading, setEventsLoading] = useState(false);
  
  // Dashboard v1.1: 7-Tage Übersicht + WordPress Sync Status
  const [weekSummary, setWeekSummary] = useState({ days: [] });
  const [weekSummaryLoading, setWeekSummaryLoading] = useState(false);
  const [wpSyncStatus, setWpSyncStatus] = useState(null);
  const [wpSyncLoading, setWpSyncLoading] = useState(false);
  
  // Auslastungs-Schwellen (Gäste pro Tag)
  const LOAD_THRESHOLDS = {
    GREEN: 120,   // < 120 Gäste = grün
    YELLOW: 140,  // 120-139 = gelb
    // >= 140 = rot
  };

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };
  
  // Helper: Ampelfarbe für Gästeanzahl
  const getLoadColor = (guests) => {
    if (guests < LOAD_THRESHOLDS.GREEN) return "bg-green-100 text-green-700 border-green-300";
    if (guests < LOAD_THRESHOLDS.YELLOW) return "bg-amber-100 text-amber-700 border-amber-300";
    return "bg-red-100 text-red-700 border-red-300";
  };
  
  const getLoadStatus = (guests) => {
    if (guests < LOAD_THRESHOLDS.GREEN) return { icon: "🟢", label: "Normal" };
    if (guests < LOAD_THRESHOLDS.YELLOW) return { icon: "🟡", label: "Hoch" };
    return { icon: "🔴", label: "Kritisch" };
  };

  // Fetch Events Summary (alle 3 Kategorien: VA, AK, MA)
  const fetchEventsSummary = useCallback(async () => {
    setEventsLoading(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/events/dashboard/events-summary`, { headers });
      setEventsSummary(res.data);
    } catch (err) {
      console.error("Fehler beim Laden der Events:", err);
      // Fallback: leere Kategorien
      setEventsSummary({
        kulturveranstaltungen: { events: [], total: 0, label: "Kulturveranstaltungen", prefix: "VA" },
        aktionen: { events: [], total: 0, label: "Aktionen", prefix: "AK" },
        menuaktionen: { events: [], total: 0, label: "Menüaktionen", prefix: "MA" },
        default_capacity: 95
      });
    } finally {
      setEventsLoading(false);
    }
  }, []);
  
  // Fetch 7-Tage Übersicht
  const fetchWeekSummary = useCallback(async () => {
    setWeekSummaryLoading(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/reservations/summary?days=7`, { headers });
      setWeekSummary(res.data);
    } catch (err) {
      console.error("Fehler beim Laden der Wochenübersicht:", err);
      setWeekSummary({ days: [] });
    } finally {
      setWeekSummaryLoading(false);
    }
  }, []);
  
  // Fetch WordPress Sync Status
  const fetchWpSyncStatus = useCallback(async () => {
    setWpSyncLoading(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/events/sync/wordpress/status`, { headers });
      setWpSyncStatus(res.data);
    } catch (err) {
      console.error("Fehler beim Laden des WordPress Sync Status:", err);
      setWpSyncStatus(null);
    } finally {
      setWpSyncLoading(false);
    }
  }, []);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = { date: selectedDate };
      if (statusFilter !== "all") params.status = statusFilter;
      if (areaFilter !== "all") params.area_id = areaFilter;
      if (search) params.search = search;

      const [resRes, areasRes, occasionsRes, specialReqRes] = await Promise.all([
        reservationsApi.getAll(params),
        areasApi.getAll(),
        axios.get(`${BACKEND_URL}/api/reservation-config/occasions`, { headers }).catch(() => ({ data: [] })),
        axios.get(`${BACKEND_URL}/api/reservation-config/special-requests`, { headers }).catch(() => ({ data: [] })),
      ]);
      setReservations(resRes.data);
      setAreas(areasRes.data);
      setOccasions(occasionsRes.data || []);
      setSpecialRequests(specialReqRes.data || []);
      
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
    fetchEventsSummary();
    fetchWeekSummary();
    fetchWpSyncStatus();
  }, [fetchData, fetchEventsSummary, fetchWeekSummary, fetchWpSyncStatus]);

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

  // Telefon-Schnellanlage (Go-Live Sprint)
  const handlePhoneReservation = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const payload = {
        guest_name: phoneData.guest_name,
        guest_phone: phoneData.guest_phone,
        party_size: phoneData.party_size,
        date: phoneData.date,
        time: phoneData.time,
        area_id: phoneData.area_id || undefined,
        occasion: phoneData.occasion || undefined,
        special_requests: phoneData.special_requests?.length > 0 ? phoneData.special_requests : undefined,
        notes: phoneData.notes || undefined,
        source: "telefon",
      };
      
      await reservationsApi.create(payload);
      toast.success(`Reservierung für ${format(parseISO(phoneData.date), "dd.MM.yyyy")} um ${phoneData.time} erstellt`);
      setShowPhoneDialog(false);
      setPhoneData({
        guest_name: "",
        guest_phone: "",
        party_size: 2,
        date: format(addDays(new Date(), 1), "yyyy-MM-dd"),
        time: "19:00",
        area_id: "",
        occasion: "none",
        special_requests: [],
        notes: "",
      });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen der Reservierung");
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
              Carlsburg Cockpit
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
                  variant="outline"
                  size="lg"
                  onClick={() => setShowPhoneDialog(true)}
                  className="rounded-full h-12 px-6 font-bold border-2 border-amber-500 text-amber-700 hover:bg-amber-50"
                >
                  <Phone size={20} className="mr-2" />
                  📞 Telefon
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

        {/* ==================== DASHBOARD v1.1 KACHELN (nur Admin/Schichtleiter) ==================== */}
        {isSchichtleiter && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            
            {/* 7-Tage Übersicht mit Auslastungsampel */}
            <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-cyan-50">
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Calendar className="h-5 w-5 text-blue-600" />
                  <h3 className="font-semibold text-blue-900">Nächste 7 Tage</h3>
                </div>
                
                {weekSummaryLoading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                  </div>
                ) : (
                  <div className="space-y-2">
                    {weekSummary.days.map((day, idx) => {
                      const loadStatus = getLoadStatus(day.guests);
                      const isToday = idx === 0;
                      return (
                        <div 
                          key={day.date} 
                          className={`flex items-center justify-between p-2 rounded-lg ${
                            isToday ? "bg-blue-100 border border-blue-300" : "bg-white/50"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-lg">{loadStatus.icon}</span>
                            <span className={`font-medium ${isToday ? "text-blue-900" : "text-gray-700"}`}>
                              {day.weekday} {day.date.slice(5).replace("-", ".")}
                            </span>
                            {isToday && <Badge className="bg-blue-600 text-xs">Heute</Badge>}
                          </div>
                          <div className="flex items-center gap-3 text-sm">
                            <span className="text-gray-600">{day.reservations} Res.</span>
                            <Badge className={getLoadColor(day.guests)}>
                              {day.guests} Gäste
                            </Badge>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
                
                <div className="mt-3 pt-3 border-t border-blue-200 flex justify-between text-xs text-blue-700">
                  <span>🟢 &lt;120</span>
                  <span>🟡 120-139</span>
                  <span>🔴 ≥140 Gäste</span>
                </div>
              </CardContent>
            </Card>

            {/* WordPress Sync Status */}
            <Card className={`border-gray-200 ${
              wpSyncStatus?.last_result === 'error' 
                ? 'bg-gradient-to-r from-red-50 to-orange-50 border-red-300' 
                : 'bg-gradient-to-r from-gray-50 to-slate-50'
            }`}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <RefreshCw className={`h-5 w-5 ${
                    wpSyncStatus?.last_result === 'error' ? 'text-red-600' : 'text-gray-600'
                  }`} />
                  <h3 className={`font-semibold ${
                    wpSyncStatus?.last_result === 'error' ? 'text-red-900' : 'text-gray-900'
                  }`}>WordPress Event Sync</h3>
                  {wpSyncStatus?.last_result === 'error' && (
                    <Badge className="bg-red-600 text-white ml-auto">Fehler!</Badge>
                  )}
                </div>
                
                {wpSyncLoading ? (
                  <div className="flex justify-center py-4">
                    <Loader2 className="h-5 w-5 animate-spin text-gray-600" />
                  </div>
                ) : wpSyncStatus ? (
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Letzter Lauf:</span>
                      <span className="font-medium">
                        {wpSyncStatus.last_run_at 
                          ? new Date(wpSyncStatus.last_run_at).toLocaleString("de-DE", {
                              day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"
                            })
                          : "Nie"
                        }
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <Badge className={
                        wpSyncStatus.last_result === 'success' 
                          ? 'bg-green-100 text-green-700' 
                          : wpSyncStatus.last_result === 'partial'
                            ? 'bg-amber-100 text-amber-700'
                            : 'bg-red-100 text-red-700'
                      }>
                        {wpSyncStatus.last_result === 'success' ? '✓ Erfolgreich' : 
                         wpSyncStatus.last_result === 'partial' ? '⚠ Teilweise' : '✗ Fehler'}
                      </Badge>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">WordPress Events:</span>
                      <span className="font-medium">{wpSyncStatus.current_wordpress_events || 0}</span>
                    </div>
                    {wpSyncStatus.counts && (
                      <div className="pt-2 border-t border-gray-200 grid grid-cols-4 gap-1 text-xs text-center">
                        <div>
                          <div className="font-bold text-green-600">{wpSyncStatus.counts.created}</div>
                          <div className="text-gray-500">Neu</div>
                        </div>
                        <div>
                          <div className="font-bold text-blue-600">{wpSyncStatus.counts.updated}</div>
                          <div className="text-gray-500">Geändert</div>
                        </div>
                        <div>
                          <div className="font-bold text-gray-600">{wpSyncStatus.counts.unchanged}</div>
                          <div className="text-gray-500">Gleich</div>
                        </div>
                        <div>
                          <div className="font-bold text-orange-600">{wpSyncStatus.counts.archived}</div>
                          <div className="text-gray-500">Archiv</div>
                        </div>
                      </div>
                    )}
                    {wpSyncStatus.last_error && (
                      <div className="mt-2 p-2 bg-red-100 rounded text-red-700 text-xs">
                        {wpSyncStatus.last_error}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-gray-500 text-sm">Kein Sync-Status verfügbar</p>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* ==================== EVENTS WIDGET (3 Reihen: VA, AK, MA) ==================== */}
        {isSchichtleiter && (
          <div className="space-y-4">
            {/* Kulturveranstaltungen (VA) */}
            {eventsSummary.kulturveranstaltungen?.events?.length > 0 && (
              <Card className="bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Theater className="h-5 w-5 text-purple-600" />
                    <h3 className="font-semibold text-purple-900">
                      Kulturveranstaltungen (nächste 90 Tage)
                    </h3>
                    <Badge variant="outline" className="ml-auto text-purple-600 border-purple-300">
                      {eventsSummary.kulturveranstaltungen.events.length} Events
                    </Badge>
                  </div>
                  
                  {eventsLoading ? (
                    <div className="flex justify-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin text-purple-600" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                      {eventsSummary.kulturveranstaltungen.events.slice(0, 4).map((event) => (
                        <div 
                          key={event.id}
                          className="bg-white rounded-lg p-3 border border-purple-100 hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => window.location.href = `/events?id=${event.id}`}
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm text-gray-900 truncate">
                                <span className="text-purple-600 font-bold">VA</span>
                                {" "}
                                {event.short_name || event.title}
                              </p>
                              <p className="text-xs text-gray-500">
                                {event.date 
                                  ? format(new Date(event.date), "dd.MM.yyyy", { locale: de })
                                  : "Datum offen"
                                }
                                {event.start_time && ` • ${event.start_time}`}
                              </p>
                            </div>
                            <Badge 
                              variant="outline" 
                              className={`text-xs shrink-0 ${
                                event.status === 'critical' 
                                  ? 'bg-red-100 text-red-700 border-red-300' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-100 text-amber-700 border-amber-300'
                                    : 'bg-green-100 text-green-700 border-green-300'
                              }`}
                            >
                              {Math.round(event.utilization)}%
                            </Badge>
                          </div>
                          
                          <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                event.status === 'critical' 
                                  ? 'bg-red-500' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-500'
                                    : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(event.utilization, 100)}%` }}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between text-xs text-gray-600">
                            <span className="flex items-center gap-1">
                              <Users className="h-3 w-3" />
                              {event.sold}/{event.capacity}
                            </span>
                            {event.is_default_capacity && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <span className="text-purple-500 text-[10px]">Standard</span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Standard-Kapazität ({eventsSummary.default_capacity || 95} Plätze)</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {eventsSummary.kulturveranstaltungen.events.length > 4 && (
                    <div className="mt-3 text-center">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-purple-600 hover:text-purple-800"
                        onClick={() => window.location.href = '/events?category=kulturveranstaltungen'}
                      >
                        Alle {eventsSummary.kulturveranstaltungen.events.length} Kulturveranstaltungen anzeigen →
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Aktionen (AK) */}
            {eventsSummary.aktionen?.events?.length > 0 && (
              <Card className="bg-gradient-to-r from-amber-50 to-orange-50 border-amber-200">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <TrendingUp className="h-5 w-5 text-amber-600" />
                    <h3 className="font-semibold text-amber-900">
                      Aktionen (nächste 90 Tage)
                    </h3>
                    <Badge variant="outline" className="ml-auto text-amber-600 border-amber-300">
                      {eventsSummary.aktionen.events.length} Events
                    </Badge>
                  </div>
                  
                  {eventsLoading ? (
                    <div className="flex justify-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin text-amber-600" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                      {eventsSummary.aktionen.events.slice(0, 4).map((event) => (
                        <div 
                          key={event.id}
                          className="bg-white rounded-lg p-3 border border-amber-100 hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => window.location.href = `/events?id=${event.id}`}
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm text-gray-900 truncate">
                                <span className="text-amber-600 font-bold">AK</span>
                                {" "}
                                {event.short_name || event.title}
                              </p>
                              <p className="text-xs text-gray-500">
                                {event.date 
                                  ? format(new Date(event.date), "dd.MM.yyyy", { locale: de })
                                  : "Datum offen"
                                }
                                {event.start_time && ` • ${event.start_time}`}
                              </p>
                            </div>
                            <Badge 
                              variant="outline" 
                              className={`text-xs shrink-0 ${
                                event.status === 'critical' 
                                  ? 'bg-red-100 text-red-700 border-red-300' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-100 text-amber-700 border-amber-300'
                                    : 'bg-green-100 text-green-700 border-green-300'
                              }`}
                            >
                              {Math.round(event.utilization)}%
                            </Badge>
                          </div>
                          
                          <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                event.status === 'critical' 
                                  ? 'bg-red-500' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-500'
                                    : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(event.utilization, 100)}%` }}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between text-xs text-gray-600">
                            <span className="flex items-center gap-1">
                              <Users className="h-3 w-3" />
                              {event.sold}/{event.capacity}
                            </span>
                            {event.is_default_capacity && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <span className="text-amber-500 text-[10px]">Standard</span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Standard-Kapazität ({eventsSummary.default_capacity || 95} Plätze)</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {eventsSummary.aktionen.events.length > 4 && (
                    <div className="mt-3 text-center">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-amber-600 hover:text-amber-800"
                        onClick={() => window.location.href = '/events?category=aktionen'}
                      >
                        Alle {eventsSummary.aktionen.events.length} Aktionen anzeigen →
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Menüaktionen (MA) */}
            {eventsSummary.menuaktionen?.events?.length > 0 && (
              <Card className="bg-gradient-to-r from-emerald-50 to-teal-50 border-emerald-200">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-4">
                    <Sparkles className="h-5 w-5 text-emerald-600" />
                    <h3 className="font-semibold text-emerald-900">
                      Menüaktionen (nächste 90 Tage)
                    </h3>
                    <Badge variant="outline" className="ml-auto text-emerald-600 border-emerald-300">
                      {eventsSummary.menuaktionen.events.length} Events
                    </Badge>
                  </div>
                  
                  {eventsLoading ? (
                    <div className="flex justify-center py-4">
                      <Loader2 className="h-6 w-6 animate-spin text-emerald-600" />
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                      {eventsSummary.menuaktionen.events.slice(0, 4).map((event) => (
                        <div 
                          key={event.id}
                          className="bg-white rounded-lg p-3 border border-emerald-100 hover:shadow-md transition-shadow cursor-pointer"
                          onClick={() => window.location.href = `/events?id=${event.id}`}
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="flex-1 min-w-0">
                              <p className="font-medium text-sm text-gray-900 truncate">
                                <span className="text-emerald-600 font-bold">MA</span>
                                {" "}
                                {event.short_name || event.title}
                              </p>
                              <p className="text-xs text-gray-500">
                                {event.date 
                                  ? format(new Date(event.date), "dd.MM.yyyy", { locale: de })
                                  : "Datum offen"
                                }
                                {event.start_time && ` • ${event.start_time}`}
                              </p>
                            </div>
                            <Badge 
                              variant="outline" 
                              className={`text-xs shrink-0 ${
                                event.status === 'critical' 
                                  ? 'bg-red-100 text-red-700 border-red-300' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-100 text-amber-700 border-amber-300'
                                    : 'bg-green-100 text-green-700 border-green-300'
                              }`}
                            >
                              {Math.round(event.utilization)}%
                            </Badge>
                          </div>
                          
                          <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                            <div 
                              className={`h-2 rounded-full transition-all ${
                                event.status === 'critical' 
                                  ? 'bg-red-500' 
                                  : event.status === 'warning'
                                    ? 'bg-amber-500'
                                    : 'bg-green-500'
                              }`}
                              style={{ width: `${Math.min(event.utilization, 100)}%` }}
                            />
                          </div>
                          
                          <div className="flex items-center justify-between text-xs text-gray-600">
                            <span className="flex items-center gap-1">
                              <Users className="h-3 w-3" />
                              {event.sold}/{event.capacity}
                            </span>
                            {event.is_default_capacity && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <span className="text-emerald-500 text-[10px]">Standard</span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Standard-Kapazität ({eventsSummary.default_capacity || 95} Plätze)</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                  
                  {eventsSummary.menuaktionen.events.length > 4 && (
                    <div className="mt-3 text-center">
                      <Button 
                        variant="ghost" 
                        size="sm" 
                        className="text-emerald-600 hover:text-emerald-800"
                        onClick={() => window.location.href = '/events?category=menuaktionen'}
                      >
                        Alle {eventsSummary.menuaktionen.events.length} Menüaktionen anzeigen →
                      </Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        )}

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
                          <div className="flex items-center gap-2">
                            <p className="font-semibold text-lg truncate">{reservation.guest_name}</p>
                            {/* Greylist/Blacklist Markers */}
                            {(() => {
                              const guestInfo = getGuestFlag(reservation.guest_phone);
                              if (guestInfo?.flag === "blacklist") {
                                return (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger>
                                        <Badge className="bg-red-500 text-white text-xs">
                                          <Ban className="h-3 w-3 mr-1" />
                                          Blacklist
                                        </Badge>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        <p>{guestInfo.no_show_count} No-Shows - Online blockiert</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                );
                              } else if (guestInfo?.flag === "greylist") {
                                return (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger>
                                        <Badge className="bg-yellow-500 text-white text-xs">
                                          <AlertTriangle className="h-3 w-3 mr-1" />
                                          Greylist
                                        </Badge>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        <p>{guestInfo.no_show_count} No-Shows - Achtung</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                );
                              }
                              return null;
                            })()}
                            {/* Unconfirmed Warning */}
                            {reservation.status === "bestaetigt" && !reservation.guest_confirmed && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <Bell className="h-4 w-4 text-orange-500" />
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Gast hat noch nicht bestätigt</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                            {/* Payment Pending Warning */}
                            {reservation.payment_status === "payment_pending" && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger>
                                    <CreditCard className="h-4 w-4 text-yellow-500" />
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Zahlung ausstehend: {reservation.payment_amount?.toFixed(2) || 0} €</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
                            {/* Occasion Badge (Go-Live Sprint) */}
                            {reservation.occasion && (
                              <Badge variant="outline" className="text-xs border-purple-300 text-purple-700 bg-purple-50">
                                {occasions.find(o => o.key === reservation.occasion)?.icon || '✨'} 
                                {occasions.find(o => o.key === reservation.occasion)?.label || reservation.occasion}
                              </Badge>
                            )}
                          </div>
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
                            {/* Special Requests Icons (Go-Live Sprint) */}
                            {reservation.special_requests?.length > 0 && (
                              <span className="flex items-center gap-1">
                                {reservation.special_requests.slice(0, 4).map((reqKey, idx) => {
                                  const req = specialRequests.find(r => r.key === reqKey);
                                  return (
                                    <TooltipProvider key={idx}>
                                      <Tooltip>
                                        <TooltipTrigger>
                                          <span className="text-base">{req?.icon || '📌'}</span>
                                        </TooltipTrigger>
                                        <TooltipContent>
                                          <p>{req?.label || reqKey}</p>
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  );
                                })}
                                {reservation.special_requests.length > 4 && (
                                  <span className="text-xs text-muted-foreground">+{reservation.special_requests.length - 4}</span>
                                )}
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
                        
                        {/* Payment Status Badge */}
                        <PaymentBadge 
                          paymentStatus={reservation.payment_status} 
                          amount={reservation.payment_amount || 0}
                          paymentRequired={reservation.payment_transaction_id ? true : false}
                        />
                        
                        {/* Quick Actions - 1 Click */}
                        {isSchichtleiter() && (
                          <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                            {/* WhatsApp Button */}
                            {reservation.guest_phone && reservation.status === "bestaetigt" && (
                              <TooltipProvider>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      size="sm"
                                      variant="outline"
                                      className="rounded-full h-10 w-10 p-0 bg-green-50 border-green-300 hover:bg-green-100"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleWhatsAppReminder(reservation);
                                      }}
                                    >
                                      <MessageCircle className="h-4 w-4 text-green-600" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>WhatsApp Erinnerung senden</p>
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                            )}
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
              
              {/* Anlass (Go-Live Sprint) */}
              <div className="space-y-2">
                <Label htmlFor="occasion">Anlass</Label>
                <Select
                  value={formData.occasion || ""}
                  onValueChange={(v) => setFormData({ ...formData, occasion: v })}
                >
                  <SelectTrigger className="h-11">
                    <SelectValue placeholder="Optional: Anlass wählen..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Kein Anlass</SelectItem>
                    {occasions.map((occ) => (
                      <SelectItem key={occ.id} value={occ.key || occ.label}>
                        {occ.icon} {occ.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Sonderwünsche (Go-Live Sprint) */}
              <div className="space-y-2">
                <Label>Sonderwünsche</Label>
                <div className="grid grid-cols-2 gap-2 p-3 bg-muted/30 rounded-lg max-h-[140px] overflow-y-auto">
                  {specialRequests.map((req) => (
                    <label key={req.id} className="flex items-center gap-2 text-sm cursor-pointer hover:bg-muted/50 p-1 rounded">
                      <input
                        type="checkbox"
                        checked={formData.special_requests?.includes(req.key || req.label) || false}
                        onChange={(e) => {
                          const key = req.key || req.label;
                          const current = formData.special_requests || [];
                          if (e.target.checked) {
                            setFormData({ ...formData, special_requests: [...current, key] });
                          } else {
                            setFormData({ ...formData, special_requests: current.filter(k => k !== key) });
                          }
                        }}
                        className="rounded"
                      />
                      <span>{req.icon} {req.label}</span>
                    </label>
                  ))}
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="notes">Notizen</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  className="min-h-[80px]"
                  data-testid="form-notes"
                  placeholder="Weitere Hinweise..."
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

      {/* Telefon-Schnellanlage Dialog (Go-Live Sprint) */}
      <Dialog open={showPhoneDialog} onOpenChange={setShowPhoneDialog}>
        <DialogContent className="sm:max-w-[550px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl flex items-center gap-2">
              <Phone className="h-6 w-6 text-amber-600" />
              📞 Telefon-Reservierung
            </DialogTitle>
            <DialogDescription>
              Schnellanlage für telefonische Reservierungen
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handlePhoneReservation}>
            <div className="grid gap-4 py-4">
              {/* Datum & Uhrzeit - Prominent */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone_date" className="text-base font-semibold">📅 Datum *</Label>
                  <Input
                    id="phone_date"
                    type="date"
                    value={phoneData.date}
                    onChange={(e) => setPhoneData({ ...phoneData, date: e.target.value })}
                    required
                    className="h-12 text-lg font-medium"
                    min={format(new Date(), "yyyy-MM-dd")}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone_time" className="text-base font-semibold">⏰ Uhrzeit *</Label>
                  <Input
                    id="phone_time"
                    type="time"
                    value={phoneData.time}
                    onChange={(e) => setPhoneData({ ...phoneData, time: e.target.value })}
                    required
                    className="h-12 text-lg font-medium"
                  />
                </div>
              </div>
              
              {/* Personen & Name */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone_size" className="text-base font-semibold">👥 Personen *</Label>
                  <Input
                    id="phone_size"
                    type="number"
                    min="1"
                    max="20"
                    value={phoneData.party_size}
                    onChange={(e) => setPhoneData({ ...phoneData, party_size: parseInt(e.target.value) || 1 })}
                    required
                    className="h-12 text-lg font-medium"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone_name" className="text-base font-semibold">Name *</Label>
                  <Input
                    id="phone_name"
                    value={phoneData.guest_name}
                    onChange={(e) => setPhoneData({ ...phoneData, guest_name: e.target.value })}
                    required
                    className="h-12"
                    placeholder="Name des Gastes"
                  />
                </div>
              </div>
              
              {/* Telefon & Bereich */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="phone_tel" className="text-base font-semibold">📞 Telefon *</Label>
                  <Input
                    id="phone_tel"
                    value={phoneData.guest_phone}
                    onChange={(e) => setPhoneData({ ...phoneData, guest_phone: e.target.value })}
                    required
                    className="h-12"
                    placeholder="Rückrufnummer"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phone_area">Bereich</Label>
                  <Select
                    value={phoneData.area_id}
                    onValueChange={(v) => setPhoneData({ ...phoneData, area_id: v })}
                  >
                    <SelectTrigger className="h-12">
                      <SelectValue placeholder="Optional..." />
                    </SelectTrigger>
                    <SelectContent>
                      {areas.map((a) => (
                        <SelectItem key={a.id} value={a.id}>{a.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              {/* Anlass */}
              <div className="space-y-2">
                <Label>Anlass</Label>
                <Select
                  value={phoneData.occasion || ""}
                  onValueChange={(v) => setPhoneData({ ...phoneData, occasion: v })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Optional: Anlass wählen..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Kein Anlass</SelectItem>
                    {occasions.map((occ) => (
                      <SelectItem key={occ.id} value={occ.key || occ.label}>
                        {occ.icon} {occ.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              
              {/* Sonderwünsche - kompakt */}
              {specialRequests.length > 0 && (
                <div className="space-y-2">
                  <Label>Sonderwünsche (schnell)</Label>
                  <div className="flex flex-wrap gap-2 p-2 bg-muted/30 rounded-lg">
                    {specialRequests.slice(0, 8).map((req) => (
                      <label 
                        key={req.id} 
                        className={`flex items-center gap-1 text-sm cursor-pointer px-2 py-1 rounded-full border transition-colors ${
                          phoneData.special_requests?.includes(req.key || req.label) 
                            ? 'bg-primary text-primary-foreground border-primary' 
                            : 'bg-background hover:bg-muted border-muted-foreground/20'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={phoneData.special_requests?.includes(req.key || req.label) || false}
                          onChange={(e) => {
                            const key = req.key || req.label;
                            const current = phoneData.special_requests || [];
                            if (e.target.checked) {
                              setPhoneData({ ...phoneData, special_requests: [...current, key] });
                            } else {
                              setPhoneData({ ...phoneData, special_requests: current.filter(k => k !== key) });
                            }
                          }}
                          className="sr-only"
                        />
                        <span>{req.icon}</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Notizen */}
              <div className="space-y-2">
                <Label htmlFor="phone_notes">Notizen</Label>
                <Textarea
                  id="phone_notes"
                  value={phoneData.notes}
                  onChange={(e) => setPhoneData({ ...phoneData, notes: e.target.value })}
                  className="min-h-[60px]"
                  placeholder="Weitere Hinweise..."
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowPhoneDialog(false)} className="rounded-full">
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full bg-amber-600 hover:bg-amber-700">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Phone className="h-4 w-4 mr-2" />}
                Reservierung anlegen
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Dashboard;
