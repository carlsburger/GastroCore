import React, { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { ScrollArea } from "../components/ui/scroll-area";
import { Separator } from "../components/ui/separator";
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
  MessageCircle,
  AlertTriangle,
  Ban,
  CreditCard,
  Send,
  MoreVertical,
  ChevronRight,
  ChevronLeft,
  History,
  FileText,
  UserPlus,
  ClipboardList,
  Eye,
  Filter,
  X,
  Timer,
  Utensils,
  Bell,
  Printer,
  Cake,
  Leaf,
  Gift,
  StickyNote,
  ArrowRight,
  PlusCircle,
  MinusCircle,
} from "lucide-react";
import { format, isToday, isTomorrow, parseISO, addDays } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Optimierte Status-Farben (pastelliger, ruhiger)
const STATUS_CONFIG = {
  neu: { 
    label: "Neu", 
    color: "bg-sky-50 text-sky-700 border-sky-200",
    cardBg: "bg-sky-50/50",
    icon: Clock,
    actions: ["bestaetigt", "storniert"]
  },
  bestaetigt: { 
    label: "Bestätigt", 
    color: "bg-emerald-50 text-emerald-700 border-emerald-200",
    cardBg: "bg-emerald-50/30",
    icon: CheckCircle,
    actions: ["angekommen", "no_show", "storniert"]
  },
  angekommen: { 
    label: "Angekommen", 
    color: "bg-violet-50 text-violet-700 border-violet-200",
    cardBg: "bg-violet-50/30",
    icon: UserCheck,
    actions: ["abgeschlossen", "no_show"]
  },
  abgeschlossen: { 
    label: "Abgeschlossen", 
    color: "bg-stone-100 text-stone-600 border-stone-200",
    cardBg: "bg-stone-50/30",
    icon: LogOut,
    actions: []
  },
  no_show: { 
    label: "No-Show", 
    color: "bg-rose-50 text-rose-700 border-rose-200",
    cardBg: "bg-rose-50/30",
    icon: XCircle,
    actions: []
  },
  storniert: { 
    label: "Storniert", 
    color: "bg-stone-100 text-stone-500 border-stone-200",
    cardBg: "bg-stone-50/30",
    icon: Ban,
    actions: []
  },
};

const PAYMENT_STATUS_CONFIG = {
  unpaid: { label: "Offen", color: "bg-amber-50 text-amber-700" },
  pending: { label: "Ausstehend", color: "bg-orange-50 text-orange-700" },
  paid: { label: "Bezahlt", color: "bg-green-50 text-green-700" },
  failed: { label: "Fehlgeschlagen", color: "bg-red-50 text-red-700" },
  refunded: { label: "Erstattet", color: "bg-gray-100 text-gray-600" },
};

// Zeit-Slots für Schnellauswahl
const TIME_SLOTS = [
  { label: "Mittag", value: "mittag", range: "11:30-14:00" },
  { label: "Nachmittag", value: "nachmittag", range: "14:00-17:00" },
  { label: "Abend", value: "abend", range: "17:00-22:00" },
];

// Polling interval in ms
const POLLING_INTERVAL = 20000;

// LocalStorage Keys
const LS_AREA_KEY = "carlsburg_service_area";
const LS_SLOT_KEY = "carlsburg_service_slot";

export const ServiceTerminal = ({ standalone = false, walkInMode = false }) => {
  const { user } = useAuth();
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [reservations, setReservations] = useState([]);
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Filters - mit localStorage Persistenz
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [selectedArea, setSelectedArea] = useState(() => localStorage.getItem(LS_AREA_KEY) || "all");
  const [selectedSlot, setSelectedSlot] = useState(() => localStorage.getItem(LS_SLOT_KEY) || "all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnlyPaymentRequired, setShowOnlyPaymentRequired] = useState(false);
  const [showOnlyFlagged, setShowOnlyFlagged] = useState(false);

  // Modals
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [showWalkInDialog, setShowWalkInDialog] = useState(false);
  const [showWaitlistDialog, setShowWaitlistDialog] = useState(false);
  const [showNewReservationsDrawer, setShowNewReservationsDrawer] = useState(false);
  const [showPhoneMode, setShowPhoneMode] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);
  
  // Forms
  const [phoneReservationData, setPhoneReservationData] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    time: format(new Date(), "HH:mm"),
    notes: "",
  });

  const [walkInData, setWalkInData] = useState({
    guest_name: "",
    party_size: 2,
    notes: "",
  });

  const [waitlistData, setWaitlistData] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    notes: "",
  });

  const pollingRef = useRef(null);

  // Persist area selection
  useEffect(() => {
    localStorage.setItem(LS_AREA_KEY, selectedArea);
  }, [selectedArea]);

  // Persist slot selection
  useEffect(() => {
    localStorage.setItem(LS_SLOT_KEY, selectedSlot);
  }, [selectedSlot]);

  // Computed: Neue/Unbestätigte Reservierungen
  const newReservations = reservations.filter(r => r.status === "neu" && r.date === selectedDate);
  const pendingCount = newReservations.length;

  // Fetch data
  const fetchData = useCallback(async (showLoader = true) => {
    if (showLoader) setLoading(true);
    else setRefreshing(true);

    try {
      const [resResponse, areasResponse] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/reservations`, {
          params: { date: selectedDate },
          headers,
        }),
        axios.get(`${BACKEND_URL}/api/areas`, { headers }),
      ]);

      setReservations(resResponse.data);
      setAreas(areasResponse.data);
      setLastUpdate(new Date());
    } catch (err) {
      toast.error("Fehler beim Laden der Daten");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedDate]);

  // Initial load and polling
  useEffect(() => {
    fetchData();
    pollingRef.current = setInterval(() => fetchData(false), POLLING_INTERVAL);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [selectedDate]);

  // ============== HANDLERS ==============

  const handleStatusChange = async (reservation, newStatus) => {
    try {
      await axios.patch(
        `${BACKEND_URL}/api/reservations/${reservation.id}/status`,
        null,
        { params: { new_status: newStatus }, headers }
      );
      toast.success(`Status: ${STATUS_CONFIG[newStatus]?.label}`);
      fetchData(false);
      if (showDetailSheet) setShowDetailSheet(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Statusänderung fehlgeschlagen");
    }
  };

  const handleCreateWalkIn = async () => {
    if (!walkInData.guest_name) {
      toast.error("Name ist erforderlich");
      return;
    }
    try {
      await axios.post(`${BACKEND_URL}/api/walk-ins`, {
        ...walkInData,
        area_id: selectedArea !== "all" ? selectedArea : undefined,
      }, { headers });
      toast.success("Walk-in angelegt");
      setShowWalkInDialog(false);
      setWalkInData({ guest_name: "", party_size: 2, notes: "" });
      fetchData(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Anlegen");
    }
  };

  const handlePhoneReservation = async () => {
    if (!phoneReservationData.guest_name || !phoneReservationData.guest_phone) {
      toast.error("Name und Telefon sind erforderlich");
      return;
    }
    try {
      await axios.post(`${BACKEND_URL}/api/reservations`, {
        guest_name: phoneReservationData.guest_name,
        guest_phone: phoneReservationData.guest_phone,
        party_size: phoneReservationData.party_size,
        date: selectedDate,
        time: phoneReservationData.time,
        notes: phoneReservationData.notes,
        source: "telefon",
      }, { headers });
      toast.success("Telefonische Reservierung angelegt");
      setShowPhoneMode(false);
      setPhoneReservationData({
        guest_name: "", guest_phone: "", party_size: 2,
        time: format(new Date(), "HH:mm"), notes: "",
      });
      fetchData(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Anlegen");
    }
  };

  const handleCreateWaitlist = async () => {
    if (!waitlistData.guest_name || !waitlistData.guest_phone) {
      toast.error("Name und Telefon sind erforderlich");
      return;
    }
    try {
      await axios.post(`${BACKEND_URL}/api/waitlist`, {
        ...waitlistData,
        date: selectedDate,
      }, { headers });
      toast.success("Warteliste-Eintrag angelegt");
      setShowWaitlistDialog(false);
      setWaitlistData({ guest_name: "", guest_phone: "", party_size: 2, notes: "" });
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Anlegen");
    }
  };

  const loadAuditLogs = async (reservationId) => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/audit-logs`, {
        params: { entity: "reservation", entity_id: reservationId, limit: 10 },
        headers,
      });
      setAuditLogs(response.data);
    } catch (err) {
      setAuditLogs([]);
    }
  };

  const openDetailSheet = (reservation) => {
    setSelectedReservation(reservation);
    setShowDetailSheet(true);
    loadAuditLogs(reservation.id);
  };

  // ============== DATE NAVIGATION ==============

  const goToToday = () => setSelectedDate(format(new Date(), "yyyy-MM-dd"));
  const goToTomorrow = () => setSelectedDate(format(addDays(new Date(), 1), "yyyy-MM-dd"));
  const navigateDate = (days) => {
    const current = parseISO(selectedDate);
    setSelectedDate(format(addDays(current, days), "yyyy-MM-dd"));
  };

  // ============== SLOT NAVIGATION ==============

  const slotIndex = TIME_SLOTS.findIndex(s => s.value === selectedSlot);
  const navigateSlot = (direction) => {
    if (selectedSlot === "all") {
      setSelectedSlot(direction > 0 ? TIME_SLOTS[0].value : TIME_SLOTS[TIME_SLOTS.length - 1].value);
    } else {
      const newIndex = slotIndex + direction;
      if (newIndex < 0) setSelectedSlot("all");
      else if (newIndex >= TIME_SLOTS.length) setSelectedSlot("all");
      else setSelectedSlot(TIME_SLOTS[newIndex].value);
    }
  };

  // ============== PRINT ==============

  const handlePrint = () => {
    window.print();
  };

  // ============== HELPERS ==============

  const getWhatsAppLink = (phone, message = "") => {
    const cleanPhone = phone?.replace(/[^0-9+]/g, "");
    if (!cleanPhone) return null;
    return `https://wa.me/${cleanPhone}${message ? `?text=${encodeURIComponent(message)}` : ""}`;
  };

  const getAreaName = (areaId) => areas.find(a => a.id === areaId)?.name || "-";

  const getDateLabel = (dateStr) => {
    const date = parseISO(dateStr);
    if (isToday(date)) return "Heute";
    if (isTomorrow(date)) return "Morgen";
    return format(date, "EEEE, dd. MMMM", { locale: de });
  };

  const isInSlot = (time, slot) => {
    if (slot === "all") return true;
    const [h, m] = time.split(":").map(Number);
    const minutes = h * 60 + m;
    if (slot === "mittag") return minutes >= 690 && minutes < 840; // 11:30-14:00
    if (slot === "nachmittag") return minutes >= 840 && minutes < 1020; // 14:00-17:00
    if (slot === "abend") return minutes >= 1020; // 17:00+
    return true;
  };

  // Prüfe auf Hinweise (Icons)
  const getReservationHints = (res) => {
    const hints = [];
    if (res.notes?.toLowerCase().includes("geburtstag")) hints.push({ icon: Cake, label: "Geburtstag", color: "text-pink-500" });
    if (res.notes?.toLowerCase().includes("allergi")) hints.push({ icon: Leaf, label: "Allergie", color: "text-red-500" });
    if (res.notes?.toLowerCase().includes("gesteck") || res.notes?.toLowerCase().includes("blumen")) hints.push({ icon: Gift, label: "Gesteck", color: "text-purple-500" });
    if (res.notes?.toLowerCase().includes("menü") || res.notes?.toLowerCase().includes("menu")) hints.push({ icon: Utensils, label: "Menü bestellt", color: "text-amber-600" });
    if (res.extended_duration) hints.push({ icon: Timer, label: "Verlängert", color: "text-blue-500" });
    if (res.notes && hints.length === 0) hints.push({ icon: StickyNote, label: "Notiz", color: "text-stone-500" });
    return hints;
  };

  // ============== FILTERS ==============

  const filteredReservations = reservations.filter((res) => {
    if (selectedArea !== "all" && res.area_id !== selectedArea) return false;
    if (selectedStatus !== "all" && res.status !== selectedStatus) return false;
    if (selectedSlot !== "all" && !isInSlot(res.time, selectedSlot)) return false;
    if (showOnlyPaymentRequired && !res.payment_required) return false;
    if (showOnlyFlagged && !res.guest_flag) return false;
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!res.guest_name?.toLowerCase().includes(query) && !res.guest_phone?.includes(query)) return false;
    }
    return true;
  });

  const sortedReservations = [...filteredReservations].sort((a, b) => (a.time || "00:00").localeCompare(b.time || "00:00"));

  // Stats
  const stats = {
    total: reservations.length,
    confirmed: reservations.filter(r => r.status === "bestaetigt").length,
    arrived: reservations.filter(r => r.status === "angekommen").length,
    completed: reservations.filter(r => r.status === "abgeschlossen").length,
    noShow: reservations.filter(r => r.status === "no_show").length,
    totalGuests: reservations.reduce((sum, r) => sum + (r.party_size || 0), 0),
    paymentPending: reservations.filter(r => r.payment_required && r.payment_status !== "paid").length,
  };

  // ============== RENDER ==============

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-12 w-12 animate-spin text-[#002f02]" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4 print:space-y-2">
        {/* ===== HEADER ===== */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 print:hidden">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="font-serif text-2xl lg:text-3xl font-bold text-[#002f02] flex items-center gap-3">
                <Utensils className="h-7 w-7" />
                Service-Terminal
              </h1>
              <p className="text-stone-500 text-sm mt-0.5">
                {getDateLabel(selectedDate)} • {format(lastUpdate, "HH:mm")} Uhr
              </p>
            </div>
            
            {/* Neue/Unbestätigte Banner */}
            {pendingCount > 0 && (
              <Button 
                variant="outline"
                onClick={() => setShowNewReservationsDrawer(true)}
                className="border-amber-400 bg-amber-50 text-amber-700 hover:bg-amber-100 animate-pulse"
              >
                <Bell className="h-4 w-4 mr-2" />
                <span className="font-bold">{pendingCount}</span>
                <span className="ml-1 hidden sm:inline">Neu</span>
              </Button>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" onClick={handlePrint} className="h-10 px-3" title="Drucken">
              <Printer className="h-4 w-4" />
            </Button>
            <Button variant="outline" onClick={() => setShowPhoneMode(true)} className="h-10 border-sky-400 text-sky-600 hover:bg-sky-50">
              <Phone className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Telefon</span>
            </Button>
            <Button variant="outline" onClick={() => fetchData(false)} disabled={refreshing} className="h-10">
              <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            </Button>
            <Button onClick={() => setShowWalkInDialog(true)} className="h-10 bg-[#002f02] hover:bg-[#003d03]">
              <Footprints className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Walk-in</span>
            </Button>
            <Button variant="outline" onClick={() => setShowWaitlistDialog(true)} className="h-10">
              <ClipboardList className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">Warteliste</span>
            </Button>
          </div>
        </div>

        {/* ===== DATE & SLOT NAVIGATION ===== */}
        <Card className="bg-white print:hidden">
          <CardContent className="p-3">
            <div className="flex flex-wrap items-center gap-3">
              {/* Date Navigation */}
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => navigateDate(-1)} className="h-9 w-9 p-0">
                  <ChevronLeft className="h-5 w-5" />
                </Button>
                <Button variant={isToday(parseISO(selectedDate)) ? "default" : "outline"} size="sm" onClick={goToToday}
                  className={isToday(parseISO(selectedDate)) ? "bg-[#002f02]" : ""}>
                  Heute
                </Button>
                <Button variant={isTomorrow(parseISO(selectedDate)) ? "default" : "outline"} size="sm" onClick={goToTomorrow}
                  className={isTomorrow(parseISO(selectedDate)) ? "bg-[#002f02]" : ""}>
                  Morgen
                </Button>
                <Input type="date" value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)} className="w-36 h-9" />
                <Button variant="ghost" size="sm" onClick={() => navigateDate(1)} className="h-9 w-9 p-0">
                  <ChevronRight className="h-5 w-5" />
                </Button>
              </div>

              <Separator orientation="vertical" className="h-8 hidden md:block" />

              {/* Slot Navigation */}
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={() => navigateSlot(-1)} className="h-9 w-9 p-0">
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Select value={selectedSlot} onValueChange={setSelectedSlot}>
                  <SelectTrigger className="w-32 h-9">
                    <Clock className="h-4 w-4 mr-1 text-stone-400" />
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Zeiten</SelectItem>
                    {TIME_SLOTS.map((slot) => (
                      <SelectItem key={slot.value} value={slot.value}>
                        {slot.label} <span className="text-xs text-stone-400 ml-1">({slot.range})</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button variant="ghost" size="sm" onClick={() => navigateSlot(1)} className="h-9 w-9 p-0">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>

              <Separator orientation="vertical" className="h-8 hidden lg:block" />

              {/* Area Tabs */}
              <div className="flex items-center gap-1">
                <Button variant={selectedArea === "all" ? "default" : "ghost"} size="sm" onClick={() => setSelectedArea("all")}
                  className={selectedArea === "all" ? "bg-[#002f02]" : ""}>
                  Alle
                </Button>
                {areas.map((area) => (
                  <Button key={area.id} variant={selectedArea === area.id ? "default" : "ghost"} size="sm"
                    onClick={() => setSelectedArea(area.id)}
                    className={selectedArea === area.id ? "bg-[#002f02]" : ""}>
                    {area.name}
                  </Button>
                ))}
              </div>

              {/* Search */}
              <div className="relative flex-1 min-w-[180px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-stone-400" />
                <Input placeholder="Suche..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9 h-9" />
                {searchQuery && (
                  <Button variant="ghost" size="sm" className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                    onClick={() => setSearchQuery("")}>
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ===== STATS BAR ===== */}
        <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-7 gap-2 print:hidden">
          <Card className="bg-white border-[#002f02]/20">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-[#002f02]">{stats.total}</p>
              <p className="text-[10px] lg:text-xs text-stone-500">Gesamt</p>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50/50 border-emerald-200">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-emerald-700">{stats.confirmed}</p>
              <p className="text-[10px] lg:text-xs text-emerald-600">Bestätigt</p>
            </CardContent>
          </Card>
          <Card className="bg-violet-50/50 border-violet-200">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-violet-700">{stats.arrived}</p>
              <p className="text-[10px] lg:text-xs text-violet-600">Angekommen</p>
            </CardContent>
          </Card>
          <Card className="bg-stone-50 border-stone-200 hidden sm:block">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-stone-600">{stats.completed}</p>
              <p className="text-[10px] lg:text-xs text-stone-500">Fertig</p>
            </CardContent>
          </Card>
          <Card className="bg-rose-50/50 border-rose-200 hidden lg:block">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-rose-700">{stats.noShow}</p>
              <p className="text-[10px] lg:text-xs text-rose-600">No-Show</p>
            </CardContent>
          </Card>
          <Card className="bg-sky-50/50 border-sky-200 hidden lg:block">
            <CardContent className="p-2 text-center">
              <p className="text-xl lg:text-2xl font-bold text-sky-700">{stats.totalGuests}</p>
              <p className="text-[10px] lg:text-xs text-sky-600">Gäste</p>
            </CardContent>
          </Card>
          {stats.paymentPending > 0 && (
            <Card className="bg-amber-50/50 border-amber-200 hidden lg:block">
              <CardContent className="p-2 text-center">
                <p className="text-xl lg:text-2xl font-bold text-amber-700">{stats.paymentPending}</p>
                <p className="text-[10px] lg:text-xs text-amber-600">Zahlung</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* ===== RESERVATION LIST ===== */}
        <div className="space-y-2">
          {sortedReservations.length === 0 ? (
            <Card className="bg-white">
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-stone-300 mb-4" />
                <p className="text-stone-500">Keine Reservierungen{selectedSlot !== "all" ? ` für ${TIME_SLOTS.find(s => s.value === selectedSlot)?.label}` : ""}</p>
              </CardContent>
            </Card>
          ) : (
            sortedReservations.map((res) => {
              const statusConfig = STATUS_CONFIG[res.status] || STATUS_CONFIG.neu;
              const StatusIcon = statusConfig.icon;
              const hasFlag = res.guest_flag === "greylist" || res.guest_flag === "blacklist";
              const isBlacklist = res.guest_flag === "blacklist";
              const paymentConfig = res.payment_status ? PAYMENT_STATUS_CONFIG[res.payment_status] : null;
              const hints = getReservationHints(res);

              return (
                <Card key={res.id} 
                  className={`bg-white hover:shadow-lg transition-all cursor-pointer border-l-4 ${
                    hasFlag ? (isBlacklist ? "border-l-rose-500" : "border-l-amber-400") : "border-l-[#002f02]"
                  }`}
                  onClick={() => openDetailSheet(res)}>
                  <CardContent className="p-3 lg:p-4">
                    <div className="flex items-center gap-3 lg:gap-4">
                      {/* Tisch & Personen - GROSS */}
                      <div className="flex items-center gap-2 min-w-[140px] lg:min-w-[160px]">
                        {res.table_number ? (
                          <div className="bg-[#002f02] text-white rounded-lg px-3 py-2 text-center min-w-[60px] lg:min-w-[70px]">
                            <p className="text-[9px] uppercase tracking-wider opacity-80">Tisch</p>
                            <p className="text-xl lg:text-2xl font-bold leading-tight">{res.table_number}</p>
                          </div>
                        ) : (
                          <div className="bg-stone-200 text-stone-500 rounded-lg px-3 py-2 text-center min-w-[60px] lg:min-w-[70px]">
                            <p className="text-[9px] uppercase tracking-wider">Tisch</p>
                            <p className="text-xl lg:text-2xl font-bold leading-tight">—</p>
                          </div>
                        )}
                        <div className="bg-sky-100 text-sky-800 rounded-lg px-3 py-2 text-center min-w-[50px] lg:min-w-[55px]">
                          <p className="text-[9px] uppercase tracking-wider opacity-80">Pers.</p>
                          <p className="text-xl lg:text-2xl font-bold leading-tight">{res.party_size}</p>
                        </div>
                      </div>

                      {/* Uhrzeit */}
                      <div className="text-center min-w-[55px] lg:min-w-[65px]">
                        <p className="text-xl lg:text-2xl font-bold text-[#002f02]">{res.time}</p>
                        <p className="text-[10px] text-stone-400">Uhr</p>
                      </div>

                      {/* Guest Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-semibold text-base lg:text-lg truncate text-stone-800">{res.guest_name}</p>
                          {hasFlag && (
                            <Badge className={`text-[10px] ${isBlacklist ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-700"}`}>
                              {isBlacklist ? <Ban className="h-3 w-3 mr-0.5" /> : <AlertTriangle className="h-3 w-3 mr-0.5" />}
                              {isBlacklist ? "Blacklist" : "Greylist"}
                            </Badge>
                          )}
                          {res.source === "walk_in" && (
                            <Badge variant="outline" className="text-[10px]"><Footprints className="h-3 w-3 mr-0.5" />Walk-in</Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-3 text-xs lg:text-sm text-stone-500 mt-0.5">
                          {res.guest_phone && <span className="flex items-center gap-1"><Phone className="h-3 w-3" />{res.guest_phone}</span>}
                          {res.area_id && <span className="flex items-center gap-1"><MapPin className="h-3 w-3" />{getAreaName(res.area_id)}</span>}
                        </div>
                      </div>

                      {/* Hints Icons */}
                      {hints.length > 0 && (
                        <div className="flex items-center gap-1 print:hidden">
                          <TooltipProvider>
                            {hints.map((hint, idx) => (
                              <Tooltip key={idx}>
                                <TooltipTrigger asChild>
                                  <div className={`p-1.5 rounded ${hint.color}`}>
                                    <hint.icon className="h-4 w-4" />
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent><p>{hint.label}</p></TooltipContent>
                              </Tooltip>
                            ))}
                          </TooltipProvider>
                        </div>
                      )}

                      {/* Status Badge */}
                      <div className="flex items-center gap-2 print:hidden">
                        {res.payment_required && paymentConfig && (
                          <Badge className={`text-[10px] ${paymentConfig.color}`}>
                            <CreditCard className="h-3 w-3 mr-0.5" />{paymentConfig.label}
                          </Badge>
                        )}
                        <Badge className={`text-xs ${statusConfig.color}`}>
                          <StatusIcon className="h-3 w-3 mr-1" />{statusConfig.label}
                        </Badge>
                      </div>

                      {/* Quick Actions */}
                      <div className="flex items-center gap-1 print:hidden" onClick={(e) => e.stopPropagation()}>
                        {/* Primary Quick Action - Large Touch Target */}
                        {statusConfig.actions.length > 0 && (
                          <Button size="sm" className="h-10 lg:h-11 px-3 lg:px-4 bg-[#002f02] hover:bg-[#003d03] rounded-lg font-medium"
                            onClick={() => handleStatusChange(res, statusConfig.actions[0])}>
                            {statusConfig.actions[0] === "bestaetigt" && <><CheckCircle className="h-4 w-4 mr-1" />Bestätigen</>}
                            {statusConfig.actions[0] === "angekommen" && <><UserCheck className="h-4 w-4 mr-1" />Einchecken</>}
                            {statusConfig.actions[0] === "abgeschlossen" && <><LogOut className="h-4 w-4 mr-1" />Fertig</>}
                          </Button>
                        )}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-10 w-10 p-0">
                              <MoreVertical className="h-5 w-5" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-48">
                            <DropdownMenuItem onClick={() => openDetailSheet(res)}>
                              <Eye className="h-4 w-4 mr-2" />Details
                            </DropdownMenuItem>
                            {res.guest_phone && getWhatsAppLink(res.guest_phone) && (
                              <DropdownMenuItem asChild>
                                <a href={getWhatsAppLink(res.guest_phone, `Hallo ${res.guest_name}, `)} target="_blank" rel="noopener noreferrer">
                                  <MessageCircle className="h-4 w-4 mr-2 text-green-600" />WhatsApp
                                </a>
                              </DropdownMenuItem>
                            )}
                            <DropdownMenuSeparator />
                            {statusConfig.actions.map((action) => (
                              <DropdownMenuItem key={action} onClick={() => handleStatusChange(res, action)}
                                className={action === "no_show" || action === "storniert" ? "text-rose-600" : ""}>
                                {STATUS_CONFIG[action]?.icon && React.createElement(STATUS_CONFIG[action].icon, { className: "h-4 w-4 mr-2" })}
                                {action === "bestaetigt" && "Bestätigen"}
                                {action === "angekommen" && "Einchecken"}
                                {action === "abgeschlossen" && "Abschließen"}
                                {action === "no_show" && "No-Show"}
                                {action === "storniert" && "Stornieren"}
                              </DropdownMenuItem>
                            ))}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })
          )}
        </div>
      </div>

      {/* ===== DETAIL SHEET ===== */}
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          {selectedReservation && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2 text-[#002f02]">
                  <Users className="h-5 w-5" />
                  Reservierung
                </SheetTitle>
                <SheetDescription>
                  {selectedReservation.time} Uhr • {selectedReservation.party_size} Personen
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-5">
                {/* Tisch prominent */}
                {selectedReservation.table_number && (
                  <div className="bg-[#002f02] text-white rounded-xl p-4 text-center">
                    <p className="text-xs opacity-80 uppercase tracking-wider">Tisch</p>
                    <p className="text-4xl font-bold">{selectedReservation.table_number}</p>
                  </div>
                )}

                {/* Guest Info */}
                <div className="bg-stone-50 rounded-xl p-4 space-y-2">
                  <p className="font-semibold text-lg text-stone-800">{selectedReservation.guest_name}</p>
                  {selectedReservation.guest_phone && (
                    <div className="flex items-center gap-2">
                      <a href={`tel:${selectedReservation.guest_phone}`} className="flex items-center gap-2 text-sm hover:underline">
                        <Phone className="h-4 w-4" />{selectedReservation.guest_phone}
                      </a>
                      {getWhatsAppLink(selectedReservation.guest_phone) && (
                        <a href={getWhatsAppLink(selectedReservation.guest_phone)} target="_blank" rel="noopener noreferrer" className="text-green-600">
                          <MessageCircle className="h-4 w-4" />
                        </a>
                      )}
                    </div>
                  )}
                  {selectedReservation.guest_flag && (
                    <Badge className={selectedReservation.guest_flag === "blacklist" ? "bg-rose-100 text-rose-700" : "bg-amber-100 text-amber-700"}>
                      {selectedReservation.guest_flag === "blacklist" ? "Blacklist" : "Greylist"}
                    </Badge>
                  )}
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Datum</p>
                    <p className="font-medium">{format(parseISO(selectedReservation.date), "dd.MM.yyyy")}</p>
                  </div>
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Uhrzeit</p>
                    <p className="font-medium">{selectedReservation.time} Uhr</p>
                  </div>
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Personen</p>
                    <p className="font-medium">{selectedReservation.party_size}</p>
                  </div>
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Bereich</p>
                    <p className="font-medium">{getAreaName(selectedReservation.area_id)}</p>
                  </div>
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Status</p>
                    <Badge className={STATUS_CONFIG[selectedReservation.status]?.color}>
                      {STATUS_CONFIG[selectedReservation.status]?.label}
                    </Badge>
                  </div>
                  <div className="bg-stone-50 rounded-lg p-3">
                    <p className="text-stone-500 text-xs">Quelle</p>
                    <p className="font-medium capitalize">{selectedReservation.source || "Online"}</p>
                  </div>
                </div>

                {/* Payment Info */}
                {selectedReservation.payment_required && (
                  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                    <div className="flex items-center justify-between">
                      <span className="font-medium">Zahlungsstatus</span>
                      <Badge className={PAYMENT_STATUS_CONFIG[selectedReservation.payment_status]?.color || "bg-stone-100"}>
                        {PAYMENT_STATUS_CONFIG[selectedReservation.payment_status]?.label || "Unbekannt"}
                      </Badge>
                    </div>
                    {selectedReservation.payment_status !== "paid" && (
                      <Button variant="outline" size="sm" className="mt-3 w-full">
                        <Send className="h-4 w-4 mr-2" />Zahlungslink senden
                      </Button>
                    )}
                  </div>
                )}

                {/* Notes */}
                {selectedReservation.notes && (
                  <div className="bg-amber-50 rounded-xl p-4">
                    <p className="text-xs text-amber-700 uppercase tracking-wider font-medium mb-1">Notizen</p>
                    <p className="text-sm whitespace-pre-wrap">{selectedReservation.notes}</p>
                  </div>
                )}

                {/* Audit Log */}
                <div className="space-y-2">
                  <p className="text-xs text-stone-500 uppercase tracking-wider font-medium flex items-center gap-1">
                    <History className="h-3 w-3" />Verlauf
                  </p>
                  <ScrollArea className="h-32">
                    {auditLogs.length === 0 ? (
                      <p className="text-xs text-stone-400">Keine Einträge</p>
                    ) : (
                      <div className="space-y-1">
                        {auditLogs.map((log, idx) => (
                          <div key={idx} className="text-xs border-l-2 border-[#002f02]/30 pl-2 py-0.5">
                            <p className="font-medium">{log.action}</p>
                            <p className="text-stone-400">{log.actor?.name} • {format(parseISO(log.timestamp), "dd.MM. HH:mm")}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </div>

                {/* Quick Actions */}
                <Separator />
                <div className="grid grid-cols-2 gap-2">
                  {STATUS_CONFIG[selectedReservation.status]?.actions.map((action) => (
                    <Button key={action}
                      variant={action === "no_show" || action === "storniert" ? "destructive" : "default"}
                      onClick={() => { handleStatusChange(selectedReservation, action); setShowDetailSheet(false); }}
                      className={`h-12 ${action !== "no_show" && action !== "storniert" ? "bg-[#002f02] hover:bg-[#003d03]" : ""}`}>
                      {action === "bestaetigt" && <><CheckCircle className="h-4 w-4 mr-2" />Bestätigen</>}
                      {action === "angekommen" && <><UserCheck className="h-4 w-4 mr-2" />Einchecken</>}
                      {action === "abgeschlossen" && <><LogOut className="h-4 w-4 mr-2" />Abschließen</>}
                      {action === "no_show" && <><XCircle className="h-4 w-4 mr-2" />No-Show</>}
                      {action === "storniert" && <><Ban className="h-4 w-4 mr-2" />Stornieren</>}
                    </Button>
                  ))}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* ===== NEW RESERVATIONS DRAWER ===== */}
      <Sheet open={showNewReservationsDrawer} onOpenChange={setShowNewReservationsDrawer}>
        <SheetContent side="right" className="w-full sm:max-w-md">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 text-amber-600">
              <Bell className="h-5 w-5" />
              Neue Reservierungen ({pendingCount})
            </SheetTitle>
            <SheetDescription>Reservierungen mit Status Neu</SheetDescription>
          </SheetHeader>
          <div className="mt-4 space-y-2">
            {newReservations.length === 0 ? (
              <p className="text-stone-500 text-center py-8">Keine neuen Reservierungen</p>
            ) : (
              newReservations.map((res) => (
                <Card key={res.id} className="cursor-pointer hover:shadow-md transition-shadow"
                  onClick={() => { setShowNewReservationsDrawer(false); openDetailSheet(res); }}>
                  <CardContent className="p-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-semibold">{res.guest_name}</p>
                        <p className="text-xs text-stone-500">{res.party_size} Pers. • {res.guest_phone}</p>
                      </div>
                      <div className="text-right">
                        <p className="font-bold text-[#002f02]">{res.time}</p>
                        <p className="text-xs text-stone-400">Uhr</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>

      {/* ===== WALK-IN DIALOG ===== */}
      <Dialog open={showWalkInDialog} onOpenChange={setShowWalkInDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Footprints className="h-5 w-5 text-[#002f02]" />Walk-in
            </DialogTitle>
            <DialogDescription>Gast ohne Reservierung</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Name *</Label>
              <Input value={walkInData.guest_name} onChange={(e) => setWalkInData({ ...walkInData, guest_name: e.target.value })}
                placeholder="Gastname" className="mt-1 h-12 text-lg" autoFocus />
            </div>
            <div>
              <Label>Personen</Label>
              <Select value={walkInData.party_size.toString()} onValueChange={(v) => setWalkInData({ ...walkInData, party_size: parseInt(v) })}>
                <SelectTrigger className="mt-1 h-12"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[1,2,3,4,5,6,7,8,9,10].map((n) => (
                    <SelectItem key={n} value={n.toString()}>{n} {n === 1 ? "Person" : "Personen"}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notiz</Label>
              <Textarea value={walkInData.notes} onChange={(e) => setWalkInData({ ...walkInData, notes: e.target.value })}
                placeholder="Optional..." rows={2} className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWalkInDialog(false)}>Abbrechen</Button>
            <Button onClick={handleCreateWalkIn} className="bg-[#002f02] hover:bg-[#003d03] h-11">Walk-in anlegen</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== WAITLIST DIALOG ===== */}
      <Dialog open={showWaitlistDialog} onOpenChange={setShowWaitlistDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-[#002f02]" />Warteliste
            </DialogTitle>
            <DialogDescription>Gast auf die Warteliste setzen</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label>Name *</Label>
              <Input value={waitlistData.guest_name} onChange={(e) => setWaitlistData({ ...waitlistData, guest_name: e.target.value })}
                placeholder="Gastname" className="mt-1 h-12" />
            </div>
            <div>
              <Label>Telefon *</Label>
              <Input value={waitlistData.guest_phone} onChange={(e) => setWaitlistData({ ...waitlistData, guest_phone: e.target.value })}
                placeholder="+49 170..." className="mt-1 h-12" />
            </div>
            <div>
              <Label>Personen</Label>
              <Select value={waitlistData.party_size.toString()} onValueChange={(v) => setWaitlistData({ ...waitlistData, party_size: parseInt(v) })}>
                <SelectTrigger className="mt-1 h-12"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[1,2,3,4,5,6,7,8,9,10].map((n) => (
                    <SelectItem key={n} value={n.toString()}>{n} Pers.</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Notiz</Label>
              <Textarea value={waitlistData.notes} onChange={(e) => setWaitlistData({ ...waitlistData, notes: e.target.value })}
                placeholder="Optional..." rows={2} className="mt-1" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWaitlistDialog(false)}>Abbrechen</Button>
            <Button onClick={handleCreateWaitlist} className="bg-[#002f02] hover:bg-[#003d03] h-11">Zur Warteliste</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ===== PHONE MODE DIALOG ===== */}
      <Dialog open={showPhoneMode} onOpenChange={setShowPhoneMode}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Phone className="h-5 w-5 text-sky-600" />Telefonische Reservierung
            </DialogTitle>
            <DialogDescription>Schnellerfassung während Telefonat</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>Name *</Label>
                <Input value={phoneReservationData.guest_name}
                  onChange={(e) => setPhoneReservationData({ ...phoneReservationData, guest_name: e.target.value })}
                  placeholder="Gast-Name" autoFocus className="mt-1 h-12 text-lg" />
              </div>
              <div className="col-span-2">
                <Label>Telefon *</Label>
                <Input value={phoneReservationData.guest_phone}
                  onChange={(e) => setPhoneReservationData({ ...phoneReservationData, guest_phone: e.target.value })}
                  placeholder="+49..." className="mt-1 h-12" />
              </div>
              <div>
                <Label>Uhrzeit</Label>
                <Input type="time" value={phoneReservationData.time}
                  onChange={(e) => setPhoneReservationData({ ...phoneReservationData, time: e.target.value })}
                  className="mt-1 h-12" />
              </div>
              <div>
                <Label>Personen</Label>
                <Select value={String(phoneReservationData.party_size)}
                  onValueChange={(v) => setPhoneReservationData({ ...phoneReservationData, party_size: parseInt(v) })}>
                  <SelectTrigger className="mt-1 h-12"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[1,2,3,4,5,6,7,8,9,10].map(n => (
                      <SelectItem key={n} value={String(n)}>{n} Pers.</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="col-span-2">
                <Label>Notiz</Label>
                <Textarea value={phoneReservationData.notes}
                  onChange={(e) => setPhoneReservationData({ ...phoneReservationData, notes: e.target.value })}
                  placeholder="Besondere Wünsche..." rows={2} className="mt-1" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPhoneMode(false)}>Abbrechen</Button>
            <Button onClick={handlePhoneReservation} className="bg-sky-600 hover:bg-sky-700 h-11">
              <Phone className="h-4 w-4 mr-2" />Reservierung anlegen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default ServiceTerminal;
