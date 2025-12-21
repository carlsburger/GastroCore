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
  History,
  FileText,
  UserPlus,
  ClipboardList,
  Eye,
  Filter,
  X,
  Timer,
  Utensils,
} from "lucide-react";
import { format, isToday, isTomorrow, parseISO } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Status configuration
const STATUS_CONFIG = {
  neu: { 
    label: "Neu", 
    color: "bg-blue-100 text-blue-700 border-blue-200",
    icon: Clock,
    actions: ["bestaetigt", "storniert"]
  },
  bestaetigt: { 
    label: "Bestätigt", 
    color: "bg-emerald-100 text-emerald-700 border-emerald-200",
    icon: CheckCircle,
    actions: ["angekommen", "no_show", "storniert"]
  },
  angekommen: { 
    label: "Angekommen", 
    color: "bg-purple-100 text-purple-700 border-purple-200",
    icon: UserCheck,
    actions: ["abgeschlossen", "no_show"]
  },
  abgeschlossen: { 
    label: "Abgeschlossen", 
    color: "bg-gray-100 text-gray-600 border-gray-200",
    icon: LogOut,
    actions: []
  },
  no_show: { 
    label: "No-Show", 
    color: "bg-red-100 text-red-700 border-red-200",
    icon: XCircle,
    actions: []
  },
  storniert: { 
    label: "Storniert", 
    color: "bg-gray-100 text-gray-500 border-gray-200",
    icon: Ban,
    actions: []
  },
};

const PAYMENT_STATUS_CONFIG = {
  unpaid: { label: "Offen", color: "bg-yellow-100 text-yellow-700" },
  pending: { label: "Ausstehend", color: "bg-orange-100 text-orange-700" },
  paid: { label: "Bezahlt", color: "bg-green-100 text-green-700" },
  failed: { label: "Fehlgeschlagen", color: "bg-red-100 text-red-700" },
  refunded: { label: "Erstattet", color: "bg-gray-100 text-gray-600" },
};

// Polling interval in ms
const POLLING_INTERVAL = 20000; // 20 seconds

export const ServiceTerminal = () => {
  const { user } = useAuth();
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [reservations, setReservations] = useState([]);
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Filters
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [selectedArea, setSelectedArea] = useState("all");
  const [selectedStatus, setSelectedStatus] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showOnlyPaymentRequired, setShowOnlyPaymentRequired] = useState(false);
  const [showOnlyFlagged, setShowOnlyFlagged] = useState(false);

  // Modals
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [showDetailSheet, setShowDetailSheet] = useState(false);
  const [showWalkInDialog, setShowWalkInDialog] = useState(false);
  const [showWaitlistDialog, setShowWaitlistDialog] = useState(false);
  const [auditLogs, setAuditLogs] = useState([]);

  // Walk-in form
  const [walkInData, setWalkInData] = useState({
    guest_name: "",
    party_size: 2,
    notes: "",
  });

  // Waitlist form
  const [waitlistData, setWaitlistData] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    notes: "",
  });

  const pollingRef = useRef(null);

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
  }, [selectedDate, headers]);

  // Initial load and polling
  useEffect(() => {
    fetchData();

    // Start polling
    pollingRef.current = setInterval(() => {
      fetchData(false);
    }, POLLING_INTERVAL);

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [selectedDate]);

  // Change status
  const handleStatusChange = async (reservation, newStatus) => {
    try {
      await axios.patch(
        `${BACKEND_URL}/api/reservations/${reservation.id}/status`,
        null,
        { params: { new_status: newStatus }, headers }
      );
      toast.success(`Status geändert: ${STATUS_CONFIG[newStatus]?.label}`);
      fetchData(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Statusänderung fehlgeschlagen");
    }
  };

  // Create walk-in
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

  // Create waitlist entry
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

  // Load audit logs for reservation
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

  // Open detail sheet
  const openDetailSheet = (reservation) => {
    setSelectedReservation(reservation);
    setShowDetailSheet(true);
    loadAuditLogs(reservation.id);
  };

  // Generate WhatsApp link
  const getWhatsAppLink = (phone, message = "") => {
    const cleanPhone = phone?.replace(/[^0-9+]/g, "");
    if (!cleanPhone) return null;
    const encodedMessage = encodeURIComponent(message);
    return `https://wa.me/${cleanPhone}${message ? `?text=${encodedMessage}` : ""}`;
  };

  // Filter reservations
  const filteredReservations = reservations.filter((res) => {
    // Area filter
    if (selectedArea !== "all" && res.area_id !== selectedArea) return false;
    
    // Status filter
    if (selectedStatus !== "all" && res.status !== selectedStatus) return false;
    
    // Payment required filter
    if (showOnlyPaymentRequired && !res.payment_required) return false;
    
    // Flagged guests filter
    if (showOnlyFlagged && !res.guest_flag) return false;
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const matchesName = res.guest_name?.toLowerCase().includes(query);
      const matchesPhone = res.guest_phone?.includes(query);
      if (!matchesName && !matchesPhone) return false;
    }
    
    return true;
  });

  // Sort by time
  const sortedReservations = [...filteredReservations].sort((a, b) => {
    const timeA = a.time || "00:00";
    const timeB = b.time || "00:00";
    return timeA.localeCompare(timeB);
  });

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

  // Get area name
  const getAreaName = (areaId) => {
    const area = areas.find(a => a.id === areaId);
    return area?.name || "-";
  };

  // Date label helper
  const getDateLabel = (dateStr) => {
    const date = parseISO(dateStr);
    if (isToday(date)) return "Heute";
    if (isTomorrow(date)) return "Morgen";
    return format(date, "EEEE, dd. MMMM", { locale: de });
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-12 w-12 animate-spin text-[#005500]" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold text-[#005500] flex items-center gap-3">
              <Utensils className="h-8 w-8" />
              Service-Terminal
            </h1>
            <p className="text-muted-foreground mt-1">
              {getDateLabel(selectedDate)} • Letzte Aktualisierung: {format(lastUpdate, "HH:mm:ss")}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => fetchData(false)}
              disabled={refreshing}
              className="rounded-full"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
              Aktualisieren
            </Button>
            <Button
              onClick={() => setShowWalkInDialog(true)}
              className="rounded-full bg-[#005500] hover:bg-[#003300]"
            >
              <Footprints className="h-4 w-4 mr-2" />
              Walk-in
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowWaitlistDialog(true)}
              className="rounded-full"
            >
              <ClipboardList className="h-4 w-4 mr-2" />
              Warteliste
            </Button>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <Card className="bg-white border-[#005500]/20">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-[#005500]">{stats.total}</p>
              <p className="text-xs text-muted-foreground">Reservierungen</p>
            </CardContent>
          </Card>
          <Card className="bg-emerald-50 border-emerald-200">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-emerald-700">{stats.confirmed}</p>
              <p className="text-xs text-emerald-600">Bestätigt</p>
            </CardContent>
          </Card>
          <Card className="bg-purple-50 border-purple-200">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-purple-700">{stats.arrived}</p>
              <p className="text-xs text-purple-600">Angekommen</p>
            </CardContent>
          </Card>
          <Card className="bg-gray-50 border-gray-200">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-gray-700">{stats.completed}</p>
              <p className="text-xs text-gray-600">Abgeschlossen</p>
            </CardContent>
          </Card>
          <Card className="bg-red-50 border-red-200">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-red-700">{stats.noShow}</p>
              <p className="text-xs text-red-600">No-Show</p>
            </CardContent>
          </Card>
          <Card className="bg-blue-50 border-blue-200">
            <CardContent className="p-3 text-center">
              <p className="text-2xl font-bold text-blue-700">{stats.totalGuests}</p>
              <p className="text-xs text-blue-600">Gäste gesamt</p>
            </CardContent>
          </Card>
          {stats.paymentPending > 0 && (
            <Card className="bg-amber-50 border-amber-200">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-amber-700">{stats.paymentPending}</p>
                <p className="text-xs text-amber-600">Zahlung offen</p>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Filters */}
        <Card className="bg-white">
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              {/* Date */}
              <div className="flex items-center gap-2">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-40"
                />
              </div>

              {/* Area Filter */}
              <Select value={selectedArea} onValueChange={setSelectedArea}>
                <SelectTrigger className="w-40">
                  <MapPin className="h-4 w-4 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Bereich" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Bereiche</SelectItem>
                  {areas.map((area) => (
                    <SelectItem key={area.id} value={area.id}>
                      {area.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Status Filter */}
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger className="w-40">
                  <Filter className="h-4 w-4 mr-2 text-muted-foreground" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Status</SelectItem>
                  {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                    <SelectItem key={key} value={key}>
                      {config.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Search */}
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Name oder Telefon suchen..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
                {searchQuery && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 p-0"
                    onClick={() => setSearchQuery("")}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>

              {/* Quick Filters */}
              <div className="flex items-center gap-2">
                <Button
                  variant={showOnlyPaymentRequired ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowOnlyPaymentRequired(!showOnlyPaymentRequired)}
                  className={showOnlyPaymentRequired ? "bg-amber-500 hover:bg-amber-600" : ""}
                >
                  <CreditCard className="h-4 w-4 mr-1" />
                  Zahlung offen
                </Button>
                <Button
                  variant={showOnlyFlagged ? "default" : "outline"}
                  size="sm"
                  onClick={() => setShowOnlyFlagged(!showOnlyFlagged)}
                  className={showOnlyFlagged ? "bg-red-500 hover:bg-red-600" : ""}
                >
                  <AlertTriangle className="h-4 w-4 mr-1" />
                  Markiert
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reservation List */}
        <div className="space-y-2">
          {sortedReservations.length === 0 ? (
            <Card className="bg-white">
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">Keine Reservierungen für diesen Tag</p>
              </CardContent>
            </Card>
          ) : (
            sortedReservations.map((res) => {
              const statusConfig = STATUS_CONFIG[res.status] || STATUS_CONFIG.neu;
              const StatusIcon = statusConfig.icon;
              const hasFlag = res.guest_flag === "greylist" || res.guest_flag === "blacklist";
              const isBlacklist = res.guest_flag === "blacklist";
              const paymentConfig = res.payment_status ? PAYMENT_STATUS_CONFIG[res.payment_status] : null;

              return (
                <Card 
                  key={res.id} 
                  className={`bg-white hover:shadow-md transition-shadow cursor-pointer ${
                    hasFlag ? (isBlacklist ? "border-l-4 border-l-red-500" : "border-l-4 border-l-amber-500") : ""
                  }`}
                  onClick={() => openDetailSheet(res)}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between gap-4">
                      {/* Time & Party Size */}
                      <div className="flex items-center gap-4 min-w-[140px]">
                        <div className="text-center">
                          <p className="text-2xl font-bold text-[#005500]">{res.time}</p>
                          <div className="flex items-center justify-center gap-1 text-muted-foreground">
                            <Users className="h-4 w-4" />
                            <span className="font-medium">{res.party_size}</span>
                          </div>
                        </div>
                      </div>

                      {/* Guest Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className="font-semibold text-lg truncate">{res.guest_name}</p>
                          {hasFlag && (
                            <Badge className={isBlacklist ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}>
                              {isBlacklist ? <Ban className="h-3 w-3 mr-1" /> : <AlertTriangle className="h-3 w-3 mr-1" />}
                              {isBlacklist ? "Blacklist" : "Greylist"}
                            </Badge>
                          )}
                          {res.source === "walk_in" && (
                            <Badge variant="outline" className="text-xs">
                              <Footprints className="h-3 w-3 mr-1" />
                              Walk-in
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                          {res.guest_phone && (
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {res.guest_phone}
                            </span>
                          )}
                          {res.area_id && (
                            <span className="flex items-center gap-1">
                              <MapPin className="h-3 w-3" />
                              {getAreaName(res.area_id)}
                            </span>
                          )}
                          {res.notes && (
                            <span className="flex items-center gap-1 text-amber-600">
                              <FileText className="h-3 w-3" />
                              Notiz
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Status & Payment Badges */}
                      <div className="flex items-center gap-2">
                        {res.payment_required && paymentConfig && (
                          <Badge className={paymentConfig.color}>
                            <CreditCard className="h-3 w-3 mr-1" />
                            {paymentConfig.label}
                          </Badge>
                        )}
                        <Badge className={statusConfig.color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {statusConfig.label}
                        </Badge>
                      </div>

                      {/* Quick Actions */}
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        {/* Primary Action Button */}
                        {statusConfig.actions.length > 0 && (
                          <Button
                            size="sm"
                            className="bg-[#005500] hover:bg-[#003300] rounded-full"
                            onClick={() => handleStatusChange(res, statusConfig.actions[0])}
                          >
                            {statusConfig.actions[0] === "bestaetigt" && "Bestätigen"}
                            {statusConfig.actions[0] === "angekommen" && "Angekommen"}
                            {statusConfig.actions[0] === "abgeschlossen" && "Abschließen"}
                          </Button>
                        )}

                        {/* More Actions Dropdown */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => openDetailSheet(res)}>
                              <Eye className="h-4 w-4 mr-2" />
                              Details anzeigen
                            </DropdownMenuItem>
                            
                            {res.guest_phone && getWhatsAppLink(res.guest_phone) && (
                              <DropdownMenuItem asChild>
                                <a href={getWhatsAppLink(res.guest_phone, `Hallo ${res.guest_name}, `)} target="_blank" rel="noopener noreferrer">
                                  <MessageCircle className="h-4 w-4 mr-2 text-green-600" />
                                  WhatsApp öffnen
                                </a>
                              </DropdownMenuItem>
                            )}

                            {res.payment_required && res.payment_status !== "paid" && (
                              <DropdownMenuItem>
                                <Send className="h-4 w-4 mr-2 text-amber-600" />
                                Zahlungslink senden
                              </DropdownMenuItem>
                            )}

                            <DropdownMenuSeparator />

                            {statusConfig.actions.map((action) => (
                              <DropdownMenuItem 
                                key={action}
                                onClick={() => handleStatusChange(res, action)}
                                className={action === "no_show" || action === "storniert" ? "text-red-600" : ""}
                              >
                                {STATUS_CONFIG[action]?.icon && (
                                  <span className="mr-2">
                                    {React.createElement(STATUS_CONFIG[action].icon, { className: "h-4 w-4" })}
                                  </span>
                                )}
                                {action === "bestaetigt" && "Bestätigen"}
                                {action === "angekommen" && "Als angekommen markieren"}
                                {action === "abgeschlossen" && "Abschließen"}
                                {action === "no_show" && "No-Show markieren"}
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

      {/* Detail Sheet */}
      <Sheet open={showDetailSheet} onOpenChange={setShowDetailSheet}>
        <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
          {selectedReservation && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2 text-[#005500]">
                  <Users className="h-5 w-5" />
                  Reservierungsdetails
                </SheetTitle>
                <SheetDescription>
                  {selectedReservation.time} Uhr • {selectedReservation.party_size} Personen
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                {/* Guest Info */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Gast</h3>
                  <div className="bg-muted/50 rounded-lg p-4 space-y-2">
                    <p className="font-semibold text-lg">{selectedReservation.guest_name}</p>
                    {selectedReservation.guest_phone && (
                      <p className="flex items-center gap-2 text-sm">
                        <Phone className="h-4 w-4" />
                        <a href={`tel:${selectedReservation.guest_phone}`} className="hover:underline">
                          {selectedReservation.guest_phone}
                        </a>
                        {getWhatsAppLink(selectedReservation.guest_phone) && (
                          <a 
                            href={getWhatsAppLink(selectedReservation.guest_phone)} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-green-600 hover:text-green-700"
                          >
                            <MessageCircle className="h-4 w-4" />
                          </a>
                        )}
                      </p>
                    )}
                    {selectedReservation.guest_email && (
                      <p className="flex items-center gap-2 text-sm">
                        <span>@</span>
                        <a href={`mailto:${selectedReservation.guest_email}`} className="hover:underline">
                          {selectedReservation.guest_email}
                        </a>
                      </p>
                    )}
                    {selectedReservation.guest_flag && (
                      <Badge className={selectedReservation.guest_flag === "blacklist" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-700"}>
                        {selectedReservation.guest_flag === "blacklist" ? "Blacklist" : "Greylist"}
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Reservation Details */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Details</h3>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Datum</p>
                      <p className="font-medium">{format(parseISO(selectedReservation.date), "dd.MM.yyyy")}</p>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Uhrzeit</p>
                      <p className="font-medium">{selectedReservation.time} Uhr</p>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Personen</p>
                      <p className="font-medium">{selectedReservation.party_size}</p>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Bereich</p>
                      <p className="font-medium">{getAreaName(selectedReservation.area_id)}</p>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Status</p>
                      <Badge className={STATUS_CONFIG[selectedReservation.status]?.color}>
                        {STATUS_CONFIG[selectedReservation.status]?.label}
                      </Badge>
                    </div>
                    <div className="bg-muted/50 rounded-lg p-3">
                      <p className="text-muted-foreground text-xs">Quelle</p>
                      <p className="font-medium capitalize">{selectedReservation.source || "Online"}</p>
                    </div>
                  </div>
                </div>

                {/* Payment Info */}
                {selectedReservation.payment_required && (
                  <div className="space-y-3">
                    <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Zahlung</h3>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                      <div className="flex items-center justify-between">
                        <span>Zahlungsstatus</span>
                        <Badge className={PAYMENT_STATUS_CONFIG[selectedReservation.payment_status]?.color || "bg-gray-100"}>
                          {PAYMENT_STATUS_CONFIG[selectedReservation.payment_status]?.label || "Unbekannt"}
                        </Badge>
                      </div>
                      {selectedReservation.payment_status !== "paid" && (
                        <Button variant="outline" size="sm" className="mt-3 w-full">
                          <Send className="h-4 w-4 mr-2" />
                          Zahlungslink erneut senden
                        </Button>
                      )}
                    </div>
                  </div>
                )}

                {/* Notes */}
                {selectedReservation.notes && (
                  <div className="space-y-3">
                    <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide">Notizen</h3>
                    <div className="bg-muted/50 rounded-lg p-4">
                      <p className="text-sm whitespace-pre-wrap">{selectedReservation.notes}</p>
                    </div>
                  </div>
                )}

                {/* Audit Log */}
                <div className="space-y-3">
                  <h3 className="font-semibold text-sm text-muted-foreground uppercase tracking-wide flex items-center gap-2">
                    <History className="h-4 w-4" />
                    Verlauf
                  </h3>
                  <ScrollArea className="h-48">
                    {auditLogs.length === 0 ? (
                      <p className="text-sm text-muted-foreground">Keine Einträge</p>
                    ) : (
                      <div className="space-y-2">
                        {auditLogs.map((log, idx) => (
                          <div key={idx} className="text-sm border-l-2 border-[#005500]/30 pl-3 py-1">
                            <p className="font-medium">{log.action}</p>
                            <p className="text-muted-foreground text-xs">
                              {log.actor?.name} • {format(parseISO(log.timestamp), "dd.MM. HH:mm")}
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </div>

                {/* Actions */}
                <Separator />
                <div className="flex flex-wrap gap-2">
                  {STATUS_CONFIG[selectedReservation.status]?.actions.map((action) => (
                    <Button
                      key={action}
                      variant={action === "no_show" || action === "storniert" ? "destructive" : "default"}
                      onClick={() => {
                        handleStatusChange(selectedReservation, action);
                        setShowDetailSheet(false);
                      }}
                      className={action !== "no_show" && action !== "storniert" ? "bg-[#005500] hover:bg-[#003300]" : ""}
                    >
                      {action === "bestaetigt" && "Bestätigen"}
                      {action === "angekommen" && "Als angekommen markieren"}
                      {action === "abgeschlossen" && "Abschließen"}
                      {action === "no_show" && "No-Show"}
                      {action === "storniert" && "Stornieren"}
                    </Button>
                  ))}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Walk-in Dialog */}
      <Dialog open={showWalkInDialog} onOpenChange={setShowWalkInDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Footprints className="h-5 w-5 text-[#005500]" />
              Walk-in anlegen
            </DialogTitle>
            <DialogDescription>
              Gast ohne vorherige Reservierung
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="walkin-name">Name *</Label>
              <Input
                id="walkin-name"
                value={walkInData.guest_name}
                onChange={(e) => setWalkInData({ ...walkInData, guest_name: e.target.value })}
                placeholder="Gastname"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="walkin-size">Personenzahl</Label>
              <Select
                value={walkInData.party_size.toString()}
                onValueChange={(v) => setWalkInData({ ...walkInData, party_size: parseInt(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <SelectItem key={n} value={n.toString()}>
                      {n} {n === 1 ? "Person" : "Personen"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="walkin-notes">Notizen</Label>
              <Textarea
                id="walkin-notes"
                value={walkInData.notes}
                onChange={(e) => setWalkInData({ ...walkInData, notes: e.target.value })}
                placeholder="Optional..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWalkInDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreateWalkIn} className="bg-[#005500] hover:bg-[#003300]">
              Walk-in anlegen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Waitlist Dialog */}
      <Dialog open={showWaitlistDialog} onOpenChange={setShowWaitlistDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ClipboardList className="h-5 w-5 text-[#005500]" />
              Warteliste-Eintrag
            </DialogTitle>
            <DialogDescription>
              Gast auf die Warteliste setzen
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="waitlist-name">Name *</Label>
              <Input
                id="waitlist-name"
                value={waitlistData.guest_name}
                onChange={(e) => setWaitlistData({ ...waitlistData, guest_name: e.target.value })}
                placeholder="Gastname"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="waitlist-phone">Telefon *</Label>
              <Input
                id="waitlist-phone"
                value={waitlistData.guest_phone}
                onChange={(e) => setWaitlistData({ ...waitlistData, guest_phone: e.target.value })}
                placeholder="+49 170 ..."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="waitlist-size">Personenzahl</Label>
              <Select
                value={waitlistData.party_size.toString()}
                onValueChange={(v) => setWaitlistData({ ...waitlistData, party_size: parseInt(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((n) => (
                    <SelectItem key={n} value={n.toString()}>
                      {n} {n === 1 ? "Person" : "Personen"}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="waitlist-notes">Notizen</Label>
              <Textarea
                id="waitlist-notes"
                value={waitlistData.notes}
                onChange={(e) => setWaitlistData({ ...waitlistData, notes: e.target.value })}
                placeholder="Optional..."
                rows={2}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowWaitlistDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleCreateWaitlist} className="bg-[#005500] hover:bg-[#003300]">
              Zur Warteliste
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default ServiceTerminal;
