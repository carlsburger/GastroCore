import React, { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { ScrollArea } from "../components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Printer,
  RefreshCw,
  Calendar,
  Clock,
  Users,
  AlertTriangle,
  Cake,
  Leaf,
  Timer,
  MapPin,
  ChevronLeft,
  ChevronRight,
  FileText,
  Check,
  X,
  Link2,
  Unlink,
  UserPlus,
  Settings,
  Plus,
  Minus,
  Sparkles,
  Building,
  Trees,
  PartyPopper,
} from "lucide-react";
import { format, addDays, subDays } from "date-fns";
import { de } from "date-fns/locale";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Bereiche gemäß Spezifikation
const AREAS = {
  restaurant: { 
    label: "Restaurant", 
    icon: Building,
    subAreas: {
      saal: { label: "Saal", color: "bg-blue-100" },
      wintergarten: { label: "Wintergarten", color: "bg-cyan-100" }
    }
  },
  terrasse: { label: "Terrasse", icon: Trees, color: "bg-green-100" },
  event: { label: "Event", icon: PartyPopper, color: "bg-purple-100" }
};

// Zeitfenster-Optionen
const TIME_SLOTS = [
  { label: "11:00 - 14:00", value: "11:00-14:00", start: "11:00", end: "14:00" },
  { label: "14:00 - 17:00", value: "14:00-17:00", start: "14:00", end: "17:00" },
  { label: "17:00 - 20:00", value: "17:00-20:00", start: "17:00", end: "20:00" },
  { label: "20:00 - 23:00", value: "20:00-23:00", start: "20:00", end: "23:00" },
  { label: "Alle", value: "all", start: "00:00", end: "23:59" },
];

// Status-Farben für Tische
const STATUS_COLORS = {
  frei: "bg-green-100 border-green-500 hover:bg-green-200",
  reserviert: "bg-yellow-100 border-yellow-500 hover:bg-yellow-200",
  belegt: "bg-red-100 border-red-500 hover:bg-red-200",
  gesperrt: "bg-gray-300 border-gray-500 opacity-60",
};

const STATUS_LABELS = {
  frei: { text: "Frei", color: "bg-green-500" },
  reserviert: { text: "Reserviert", color: "bg-yellow-500" },
  belegt: { text: "Belegt", color: "bg-red-500" },
  gesperrt: { text: "Gesperrt", color: "bg-gray-500" },
};

export const TablePlan = () => {
  const token = localStorage.getItem("token");
  const getHeaders = () => ({ Authorization: `Bearer ${token}` });

  // State
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [selectedTimeSlot, setSelectedTimeSlot] = useState(TIME_SLOTS[2]); // 17:00-20:00 als Default
  const [selectedArea, setSelectedArea] = useState("all");
  const [selectedSubArea, setSelectedSubArea] = useState("all");
  const [tables, setTables] = useState([]);
  const [occupancy, setOccupancy] = useState([]);
  const [combinations, setCombinations] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Dialog States
  const [selectedTable, setSelectedTable] = useState(null);
  const [showTableDetail, setShowTableDetail] = useState(false);
  const [showWalkInDialog, setShowWalkInDialog] = useState(false);
  const [showCombinationDialog, setShowCombinationDialog] = useState(false);
  const [showTableAdminDialog, setShowTableAdminDialog] = useState(false);
  const [showSuggestionsDialog, setShowSuggestionsDialog] = useState(false);
  
  // Kombinations-State
  const [combinationTables, setCombinationTables] = useState([]);
  const [combinationMode, setCombinationMode] = useState(false);
  
  // Walk-in Form
  const [walkInForm, setWalkInForm] = useState({
    guest_name: "",
    guest_phone: "",
    party_size: 2,
    notes: ""
  });
  
  // Suggestions
  const [suggestions, setSuggestions] = useState([]);
  const [suggestionPartySize, setSuggestionPartySize] = useState(4);

  // Fetch data
  const fetchData = useCallback(async () => {
    const headers = getHeaders();
    setLoading(true);
    try {
      const timeSlotParam = selectedTimeSlot.value !== "all" ? selectedTimeSlot.value : undefined;
      const areaParam = selectedArea !== "all" ? selectedArea : undefined;
      
      const [tablesRes, occupancyRes, combinationsRes, reservationsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/tables`, { 
          headers,
          params: { active_only: true }
        }),
        axios.get(`${BACKEND_URL}/api/tables/occupancy/${selectedDate}`, {
          headers,
          params: { 
            time_slot: timeSlotParam,
            area: areaParam
          }
        }),
        axios.get(`${BACKEND_URL}/api/table-combinations/for-date/${selectedDate}`, {
          headers,
          params: { time_slot: timeSlotParam }
        }),
        axios.get(`${BACKEND_URL}/api/reservations`, {
          headers,
          params: { date: selectedDate }
        })
      ]);
      
      setTables(tablesRes.data);
      setOccupancy(occupancyRes.data.occupancy || []);
      setCombinations(combinationsRes.data);
      setReservations(reservationsRes.data.filter(r => !r.archived && r.status !== "storniert"));
      
    } catch (err) {
      console.error("Fehler beim Laden:", err);
      // Falls Tables API noch keine Daten hat, Fallback auf alte Logik
      if (err.response?.status === 404) {
        toast.info("Tisch-Stammdaten noch nicht angelegt. Bitte Tische konfigurieren.");
      } else {
        toast.error("Daten konnten nicht geladen werden");
      }
    } finally {
      setLoading(false);
    }
  }, [selectedDate, selectedTimeSlot, selectedArea, token]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Filter Tische nach Bereich
  const filteredTables = tables.filter(table => {
    if (selectedArea !== "all" && table.area !== selectedArea) return false;
    if (selectedArea === "restaurant" && selectedSubArea !== "all" && table.sub_area !== selectedSubArea) return false;
    return true;
  });

  // Gruppiere Tische nach Bereich/Subbereich
  const groupedTables = filteredTables.reduce((acc, table) => {
    let key = table.area;
    if (table.area === "restaurant" && table.sub_area) {
      key = `${table.area}_${table.sub_area}`;
    }
    if (!acc[key]) acc[key] = [];
    acc[key].push(table);
    return acc;
  }, {});

  // Hole Belegungsstatus für einen Tisch
  const getTableOccupancy = (tableId) => {
    return occupancy.find(o => o.table_id === tableId) || { status: "frei" };
  };

  // Prüfe ob Tisch in aktiver Kombination
  const getTableCombination = (tableId) => {
    return combinations.find(c => c.table_ids?.includes(tableId));
  };

  // Datum Navigation
  const goToPreviousDay = () => setSelectedDate(format(subDays(new Date(selectedDate), 1), "yyyy-MM-dd"));
  const goToNextDay = () => setSelectedDate(format(addDays(new Date(selectedDate), 1), "yyyy-MM-dd"));
  const goToToday = () => setSelectedDate(format(new Date(), "yyyy-MM-dd"));

  // Table Click Handler
  const handleTableClick = (table) => {
    if (combinationMode) {
      toggleCombinationTable(table);
    } else {
      setSelectedTable(table);
      setShowTableDetail(true);
    }
  };

  // Kombination Toggle
  const toggleCombinationTable = (table) => {
    // Prüfe ob Tisch kombinierbar
    if (!table.combinable || table.table_number === "3") {
      toast.error(`Tisch ${table.table_number} ist nicht kombinierbar`);
      return;
    }
    
    const isSelected = combinationTables.some(t => t.id === table.id);
    if (isSelected) {
      setCombinationTables(combinationTables.filter(t => t.id !== table.id));
    } else {
      // Prüfe Bereich/Subbereich
      if (combinationTables.length > 0) {
        const first = combinationTables[0];
        if (first.area !== table.area) {
          toast.error("Tische müssen im gleichen Bereich sein");
          return;
        }
        if (first.area === "restaurant" && first.sub_area !== table.sub_area) {
          toast.error("Saal und Wintergarten dürfen NICHT kombiniert werden");
          return;
        }
      }
      setCombinationTables([...combinationTables, table]);
    }
  };

  // Kombination erstellen
  const handleCreateCombination = async () => {
    if (combinationTables.length < 2) {
      toast.error("Mindestens 2 Tische auswählen");
      return;
    }
    
    try {
      await axios.post(`${BACKEND_URL}/api/table-combinations`, {
        date: selectedDate,
        time_slot: selectedTimeSlot.value,
        table_ids: combinationTables.map(t => t.id),
        name: `Kombination ${combinationTables.map(t => t.table_number).join(" + ")}`
      }, { headers });
      
      toast.success("Tischkombination erstellt");
      setCombinationMode(false);
      setCombinationTables([]);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen der Kombination");
    }
  };

  // Kombination auflösen
  const handleDissolveCombination = async (combinationId) => {
    try {
      await axios.delete(`${BACKEND_URL}/api/table-combinations/${combinationId}`, { headers });
      toast.success("Kombination aufgelöst");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Auflösen");
    }
  };

  // Walk-in erstellen
  const handleCreateWalkIn = async () => {
    if (!walkInForm.guest_name) {
      toast.error("Name erforderlich");
      return;
    }
    
    try {
      const walkInData = {
        ...walkInForm,
        table_number: selectedTable?.table_number,
        area_id: null
      };
      
      await axios.post(`${BACKEND_URL}/api/walk-ins`, walkInData, { headers });
      
      // Wenn Tisch ausgewählt, auch zuweisen
      if (selectedTable) {
        const resRes = await axios.get(`${BACKEND_URL}/api/reservations`, {
          headers,
          params: { date: format(new Date(), "yyyy-MM-dd") }
        });
        const newWalkIn = resRes.data.find(r => 
          r.guest_name === walkInForm.guest_name && 
          r.source === "walk-in" &&
          r.status === "angekommen"
        );
        
        if (newWalkIn) {
          await axios.post(`${BACKEND_URL}/api/tables/assign/${newWalkIn.id}`, null, {
            headers,
            params: { table_id: selectedTable.id }
          });
        }
      }
      
      toast.success("Walk-in erstellt");
      setShowWalkInDialog(false);
      setWalkInForm({ guest_name: "", guest_phone: "", party_size: 2, notes: "" });
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    }
  };

  // Status ändern
  const handleStatusChange = async (reservationId, newStatus) => {
    try {
      await axios.patch(
        `${BACKEND_URL}/api/reservations/${reservationId}/status`,
        null,
        { headers, params: { new_status: newStatus } }
      );
      toast.success(`Status geändert: ${newStatus}`);
      setShowTableDetail(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Statusänderung fehlgeschlagen");
    }
  };

  // Verlängerung
  const handleExtendReservation = async (reservationId) => {
    try {
      await axios.post(
        `${BACKEND_URL}/api/reservation-config/reservations/${reservationId}/extend`,
        { additional_minutes: 30, reason: "Service-Verlängerung" },
        { headers }
      );
      toast.success("Um 30 Minuten verlängert");
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Verlängerung fehlgeschlagen");
    }
  };

  // KI-Vorschläge laden
  const handleLoadSuggestions = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/tables/suggest`, {
        headers,
        params: {
          date: selectedDate,
          time: selectedTimeSlot.start,
          party_size: suggestionPartySize,
          area: selectedArea !== "all" ? selectedArea : undefined
        }
      });
      setSuggestions(res.data.suggestions || []);
      setShowSuggestionsDialog(true);
    } catch (err) {
      toast.error("Vorschläge konnten nicht geladen werden");
    }
  };

  // PDF Export
  const handlePrintPDF = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/export/table-plan`,
        {
          params: { 
            date: selectedDate,
            area_id: selectedArea !== "all" ? selectedArea : undefined,
          },
          headers,
          responseType: 'blob',
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tischplan_${selectedDate}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success("PDF heruntergeladen");
    } catch (err) {
      toast.error("PDF-Export fehlgeschlagen");
    }
  };

  // Hilfsfunktion: Besondere Hinweise
  const getSpecialIndicators = (reservation) => {
    if (!reservation) return [];
    const indicators = [];
    
    if (reservation.occasion?.toLowerCase().includes("geburtstag") || 
        reservation.notes?.toLowerCase().includes("geburtstag")) {
      indicators.push({ icon: Cake, color: "text-pink-500", label: "Geburtstag" });
    }
    if (reservation.allergies || reservation.notes?.toLowerCase().includes("allergi")) {
      indicators.push({ icon: AlertTriangle, color: "text-orange-500", label: "Allergien" });
    }
    if (reservation.menu_choice?.toLowerCase().includes("veget") || 
        reservation.notes?.toLowerCase().includes("vegan")) {
      indicators.push({ icon: Leaf, color: "text-green-500", label: "Vegetarisch" });
    }
    if (reservation.is_extended) {
      indicators.push({ icon: Timer, color: "text-blue-500", label: "Verlängert" });
    }
    
    return indicators;
  };

  // Statistiken berechnen
  const stats = {
    frei: occupancy.filter(o => o.status === "frei").length,
    reserviert: occupancy.filter(o => o.status === "reserviert").length,
    belegt: occupancy.filter(o => o.status === "belegt").length,
    gesperrt: occupancy.filter(o => o.status === "gesperrt").length,
    total: occupancy.length,
    guests: reservations.filter(r => 
      r.status !== "storniert" && r.status !== "no_show"
    ).reduce((sum, r) => sum + (r.party_size || 0), 0)
  };

  const getDateLabel = () => {
    const date = new Date(selectedDate);
    const today = new Date();
    today.setHours(0,0,0,0);
    date.setHours(0,0,0,0);
    
    if (date.getTime() === today.getTime()) return "Heute";
    if (date.getTime() === today.getTime() + 86400000) return "Morgen";
    return format(date, "EEEE, dd.MM.", { locale: de });
  };

  // Render Tisch-Kachel
  const renderTableCard = (table) => {
    const occ = getTableOccupancy(table.id);
    const comb = getTableCombination(table.id);
    const reservation = occ.reservation;
    const indicators = getSpecialIndicators(reservation);
    const isInCombinationMode = combinationTables.some(t => t.id === table.id);
    
    return (
      <div
        key={table.id}
        data-testid={`table-card-${table.table_number}`}
        onClick={() => handleTableClick(table)}
        className={`
          relative p-3 rounded-xl border-2 cursor-pointer transition-all
          ${STATUS_COLORS[occ.status]}
          ${isInCombinationMode ? 'ring-4 ring-purple-500 ring-offset-2' : ''}
          ${comb ? 'border-dashed border-purple-400' : ''}
          ${!table.combinable ? 'opacity-80' : ''}
        `}
      >
        {/* Tischnummer - Groß */}
        <div className="flex items-center justify-between mb-2">
          <div className="text-2xl font-bold text-gray-800">
            {table.table_number}
          </div>
          <Badge variant="secondary" className="text-xs">
            {table.seats_max} Pl.
          </Badge>
        </div>
        
        {/* Status Badge */}
        <Badge className={`${STATUS_LABELS[occ.status].color} text-white text-xs mb-2`}>
          {STATUS_LABELS[occ.status].text}
        </Badge>
        
        {/* Reservierungsinfo */}
        {reservation && (
          <div className="mt-2 space-y-1">
            <p className="font-semibold text-sm truncate">{reservation.guest_name}</p>
            <p className="text-xs text-gray-600">{reservation.time} | {reservation.party_size} Pers.</p>
            
            {/* Icons */}
            {indicators.length > 0 && (
              <div className="flex gap-1 mt-1">
                {indicators.map((ind, i) => (
                  <ind.icon key={i} className={`h-4 w-4 ${ind.color}`} title={ind.label} />
                ))}
              </div>
            )}
          </div>
        )}
        
        {/* Event-Sperrung */}
        {occ.status === "gesperrt" && reservation?.blocked_by === "event" && (
          <div className="mt-2 text-xs text-gray-600">
            <PartyPopper className="h-3 w-3 inline mr-1" />
            {reservation.event_name || "Event"}
          </div>
        )}
        
        {/* Kombinations-Indikator */}
        {comb && (
          <div className="absolute top-1 right-1">
            <Link2 className="h-4 w-4 text-purple-500" title={`Kombination: ${comb.table_numbers?.join(" + ")}`} />
          </div>
        )}
        
        {/* Nicht kombinierbar */}
        {!table.combinable && (
          <div className="absolute bottom-1 right-1 text-xs text-gray-400">
            ∅
          </div>
        )}
      </div>
    );
  };

  return (
    <Layout>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold text-[#005500] flex items-center gap-3">
              <MapPin className="h-8 w-8" />
              Tischplan
            </h1>
            <p className="text-muted-foreground mt-1">
              Grafische Übersicht & Belegung
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {combinationMode ? (
              <>
                <Badge variant="outline" className="text-purple-600 border-purple-400">
                  <Link2 className="h-4 w-4 mr-1" />
                  {combinationTables.length} Tische gewählt
                </Badge>
                <Button 
                  onClick={handleCreateCombination}
                  disabled={combinationTables.length < 2}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  <Check className="h-4 w-4 mr-2" />
                  Kombination erstellen
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setCombinationMode(false);
                    setCombinationTables([]);
                  }}
                >
                  <X className="h-4 w-4 mr-2" />
                  Abbrechen
                </Button>
              </>
            ) : (
              <>
                <Button 
                  variant="outline" 
                  onClick={() => setCombinationMode(true)}
                >
                  <Link2 className="h-4 w-4 mr-2" />
                  Kombination
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setShowWalkInDialog(true)}
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  Walk-in
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleLoadSuggestions}
                >
                  <Sparkles className="h-4 w-4 mr-2" />
                  KI-Vorschlag
                </Button>
                <Button variant="outline" onClick={fetchData} disabled={loading}>
                  <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                </Button>
                <Button onClick={handlePrintPDF} className="bg-[#005500] hover:bg-[#003300]">
                  <Printer className="h-4 w-4 mr-2" />
                  PDF
                </Button>
              </>
            )}
          </div>
        </div>

        {/* Filter-Leiste */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              {/* Datum Navigation */}
              <div className="flex items-center gap-2">
                <Button variant="outline" size="icon" onClick={goToPreviousDay}>
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <Input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-40"
                    data-testid="date-picker"
                  />
                </div>
                <Button variant="outline" size="icon" onClick={goToNextDay}>
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={goToToday}>
                  Heute
                </Button>
              </div>

              {/* Zeitfenster */}
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <Select
                  value={selectedTimeSlot.value}
                  onValueChange={(v) => setSelectedTimeSlot(TIME_SLOTS.find(t => t.value === v) || TIME_SLOTS[0])}
                >
                  <SelectTrigger className="w-40" data-testid="time-slot-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIME_SLOTS.map((slot) => (
                      <SelectItem key={slot.value} value={slot.value}>
                        {slot.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Bereich */}
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <Select value={selectedArea} onValueChange={(v) => {
                  setSelectedArea(v);
                  setSelectedSubArea("all");
                }}>
                  <SelectTrigger className="w-40" data-testid="area-select">
                    <SelectValue placeholder="Bereich" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Bereiche</SelectItem>
                    <SelectItem value="restaurant">Restaurant</SelectItem>
                    <SelectItem value="terrasse">Terrasse</SelectItem>
                    <SelectItem value="event">Event</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Subbereich für Restaurant */}
              {selectedArea === "restaurant" && (
                <Select value={selectedSubArea} onValueChange={setSelectedSubArea}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="Subbereich" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle</SelectItem>
                    <SelectItem value="saal">Saal</SelectItem>
                    <SelectItem value="wintergarten">Wintergarten</SelectItem>
                  </SelectContent>
                </Select>
              )}

              {/* Stats */}
              <div className="ml-auto flex items-center gap-3 text-sm">
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-green-500"></div>
                  <span>{stats.frei}</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                  <span>{stats.reserviert}</span>
                </div>
                <div className="flex items-center gap-1">
                  <div className="w-3 h-3 rounded-full bg-red-500"></div>
                  <span>{stats.belegt}</span>
                </div>
                <Badge variant="outline" className="text-lg px-3 py-1">
                  <Users className="h-4 w-4 mr-2" />
                  {stats.guests} Gäste
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Datum-Label */}
        <div className="text-center">
          <h2 className="text-xl font-semibold text-muted-foreground">
            {getDateLabel()} • {selectedTimeSlot.label}
          </h2>
        </div>

        {/* Aktive Kombinationen */}
        {combinations.length > 0 && (
          <Card className="border-purple-200 bg-purple-50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-2 text-purple-700">
                <Link2 className="h-4 w-4" />
                Aktive Tischkombinationen
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="flex flex-wrap gap-2">
                {combinations.map((comb) => (
                  <Badge 
                    key={comb.id} 
                    variant="outline" 
                    className="border-purple-400 text-purple-700 cursor-pointer hover:bg-purple-100"
                    onClick={() => handleDissolveCombination(comb.id)}
                  >
                    {comb.table_numbers?.join(" + ")} ({comb.total_seats} Pl.)
                    <X className="h-3 w-3 ml-1" />
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Tischplan Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-12 w-12 animate-spin text-[#005500]" />
          </div>
        ) : tables.length === 0 ? (
          <Card className="p-12 text-center">
            <Settings className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <p className="text-xl text-muted-foreground mb-4">
              Keine Tische konfiguriert
            </p>
            <p className="text-sm text-muted-foreground mb-4">
              Bitte legen Sie zuerst Tisch-Stammdaten an.
            </p>
            <Button onClick={() => setShowTableAdminDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Tische anlegen
            </Button>
          </Card>
        ) : (
          <Tabs defaultValue="all" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="all">Alle</TabsTrigger>
              {Object.entries(groupedTables).map(([key]) => {
                const [area, subArea] = key.split("_");
                const areaInfo = AREAS[area];
                const label = subArea 
                  ? areaInfo.subAreas?.[subArea]?.label 
                  : areaInfo?.label;
                const Icon = areaInfo?.icon || MapPin;
                return (
                  <TabsTrigger key={key} value={key} className="flex items-center gap-1">
                    <Icon className="h-4 w-4" />
                    {label}
                  </TabsTrigger>
                );
              })}
            </TabsList>

            <TabsContent value="all">
              {Object.entries(groupedTables).map(([key, groupTables]) => {
                const [area, subArea] = key.split("_");
                const areaInfo = AREAS[area];
                const label = subArea 
                  ? `${areaInfo?.label} - ${areaInfo?.subAreas?.[subArea]?.label}`
                  : areaInfo?.label;
                const bgColor = subArea 
                  ? areaInfo?.subAreas?.[subArea]?.color 
                  : areaInfo?.color || "bg-gray-100";
                
                return (
                  <div key={key} className="mb-6">
                    <h3 className={`text-lg font-semibold mb-3 px-3 py-2 rounded-lg ${bgColor}`}>
                      {label} ({groupTables.length} Tische)
                    </h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                      {groupTables
                        .sort((a, b) => {
                          const numA = parseInt(a.table_number) || 999;
                          const numB = parseInt(b.table_number) || 999;
                          return numA - numB;
                        })
                        .map(table => renderTableCard(table))}
                    </div>
                  </div>
                );
              })}
            </TabsContent>

            {Object.entries(groupedTables).map(([key, groupTables]) => (
              <TabsContent key={key} value={key}>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 xl:grid-cols-8 gap-3">
                  {groupTables
                    .sort((a, b) => {
                      const numA = parseInt(a.table_number) || 999;
                      const numB = parseInt(b.table_number) || 999;
                      return numA - numB;
                    })
                    .map(table => renderTableCard(table))}
                </div>
              </TabsContent>
            ))}
          </Tabs>
        )}

        {/* Tisch-Detail Dialog */}
        <Dialog open={showTableDetail} onOpenChange={setShowTableDetail}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                Tisch {selectedTable?.table_number}
                <Badge variant="secondary">{selectedTable?.seats_max} Plätze</Badge>
              </DialogTitle>
            </DialogHeader>
            
            {selectedTable && (() => {
              const occ = getTableOccupancy(selectedTable.id);
              const reservation = occ.reservation;
              
              return (
                <div className="space-y-4">
                  {/* Status */}
                  <div className="flex items-center gap-2">
                    <Label>Status:</Label>
                    <Badge className={`${STATUS_LABELS[occ.status].color} text-white`}>
                      {STATUS_LABELS[occ.status].text}
                    </Badge>
                  </div>
                  
                  {/* Bereich */}
                  <div className="flex items-center gap-2">
                    <Label>Bereich:</Label>
                    <span>{AREAS[selectedTable.area]?.label}</span>
                    {selectedTable.sub_area && (
                      <span className="text-muted-foreground">
                        ({AREAS.restaurant.subAreas[selectedTable.sub_area]?.label})
                      </span>
                    )}
                  </div>
                  
                  {/* Reservierung */}
                  {reservation && (
                    <Card className="p-3 bg-muted">
                      <div className="space-y-2">
                        <p className="font-semibold text-lg">{reservation.guest_name}</p>
                        <div className="grid grid-cols-2 gap-2 text-sm">
                          <div>
                            <Label className="text-muted-foreground">Uhrzeit</Label>
                            <p>{reservation.time}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Personen</Label>
                            <p>{reservation.party_size}</p>
                          </div>
                        </div>
                        {reservation.notes && (
                          <div>
                            <Label className="text-muted-foreground">Notizen</Label>
                            <p className="text-sm">{reservation.notes}</p>
                          </div>
                        )}
                        {reservation.allergies && (
                          <div className="p-2 bg-orange-100 rounded text-sm">
                            <AlertTriangle className="h-4 w-4 inline mr-1 text-orange-500" />
                            {reservation.allergies}
                          </div>
                        )}
                      </div>
                    </Card>
                  )}
                  
                  {/* Aktionen */}
                  <div className="flex flex-wrap gap-2">
                    {occ.status === "frei" && (
                      <Button 
                        onClick={() => {
                          setShowTableDetail(false);
                          setShowWalkInDialog(true);
                        }}
                        className="bg-green-600 hover:bg-green-700"
                      >
                        <UserPlus className="h-4 w-4 mr-2" />
                        Walk-in setzen
                      </Button>
                    )}
                    
                    {reservation && reservation.status === "bestaetigt" && (
                      <Button 
                        onClick={() => handleStatusChange(reservation.id, "angekommen")}
                        className="bg-blue-600 hover:bg-blue-700"
                      >
                        <Check className="h-4 w-4 mr-2" />
                        Einchecken
                      </Button>
                    )}
                    
                    {reservation && reservation.status === "angekommen" && (
                      <>
                        <Button 
                          onClick={() => handleExtendReservation(reservation.id)}
                          variant="outline"
                        >
                          <Timer className="h-4 w-4 mr-2" />
                          +30 Min
                        </Button>
                        <Button 
                          onClick={() => handleStatusChange(reservation.id, "abgeschlossen")}
                          className="bg-gray-600 hover:bg-gray-700"
                        >
                          <Check className="h-4 w-4 mr-2" />
                          Abschließen
                        </Button>
                      </>
                    )}
                    
                    {selectedTable.combinable && selectedTable.table_number !== "3" && (
                      <Button 
                        variant="outline"
                        onClick={() => {
                          setShowTableDetail(false);
                          setCombinationMode(true);
                          setCombinationTables([selectedTable]);
                        }}
                      >
                        <Link2 className="h-4 w-4 mr-2" />
                        Kombinieren
                      </Button>
                    )}
                  </div>
                </div>
              );
            })()}
          </DialogContent>
        </Dialog>

        {/* Walk-in Dialog */}
        <Dialog open={showWalkInDialog} onOpenChange={setShowWalkInDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>
                Walk-in erstellen
                {selectedTable && ` - Tisch ${selectedTable.table_number}`}
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <div>
                <Label>Name *</Label>
                <Input
                  value={walkInForm.guest_name}
                  onChange={(e) => setWalkInForm({...walkInForm, guest_name: e.target.value})}
                  placeholder="Gastname"
                  data-testid="walk-in-name"
                />
              </div>
              <div>
                <Label>Telefon</Label>
                <Input
                  value={walkInForm.guest_phone}
                  onChange={(e) => setWalkInForm({...walkInForm, guest_phone: e.target.value})}
                  placeholder="Optional"
                />
              </div>
              <div>
                <Label>Personen</Label>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={() => setWalkInForm({...walkInForm, party_size: Math.max(1, walkInForm.party_size - 1)})}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <span className="text-2xl font-bold w-12 text-center">{walkInForm.party_size}</span>
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={() => setWalkInForm({...walkInForm, party_size: walkInForm.party_size + 1})}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div>
                <Label>Notizen</Label>
                <Textarea
                  value={walkInForm.notes}
                  onChange={(e) => setWalkInForm({...walkInForm, notes: e.target.value})}
                  placeholder="Optional"
                />
              </div>
            </div>
            
            <DialogFooter>
              <Button variant="outline" onClick={() => setShowWalkInDialog(false)}>
                Abbrechen
              </Button>
              <Button onClick={handleCreateWalkIn} className="bg-[#005500] hover:bg-[#003300]">
                Walk-in erstellen
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* KI-Vorschläge Dialog */}
        <Dialog open={showSuggestionsDialog} onOpenChange={setShowSuggestionsDialog}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-yellow-500" />
                KI-Tischvorschläge
              </DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Label>Personenzahl:</Label>
                <div className="flex items-center gap-2">
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={() => setSuggestionPartySize(Math.max(1, suggestionPartySize - 1))}
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                  <span className="text-xl font-bold w-8 text-center">{suggestionPartySize}</span>
                  <Button 
                    variant="outline" 
                    size="icon"
                    onClick={() => setSuggestionPartySize(suggestionPartySize + 1)}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                <Button variant="outline" size="sm" onClick={handleLoadSuggestions}>
                  Neu laden
                </Button>
              </div>
              
              <ScrollArea className="h-64">
                {suggestions.length === 0 ? (
                  <p className="text-center text-muted-foreground py-8">
                    Keine passenden Tische gefunden
                  </p>
                ) : (
                  <div className="space-y-2">
                    {suggestions.map((sug, idx) => (
                      <Card 
                        key={idx} 
                        className="p-3 cursor-pointer hover:bg-muted"
                        onClick={() => {
                          if (sug.type === "single") {
                            const table = tables.find(t => t.id === sug.table_id);
                            if (table) {
                              setSelectedTable(table);
                              setShowSuggestionsDialog(false);
                              setShowTableDetail(true);
                            }
                          } else {
                            // Kombination vorschlagen
                            const combTables = tables.filter(t => sug.table_ids.includes(t.id));
                            setCombinationTables(combTables);
                            setCombinationMode(true);
                            setShowSuggestionsDialog(false);
                          }
                        }}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-semibold">{sug.message}</p>
                            <p className="text-xs text-muted-foreground">
                              {AREAS[sug.area]?.label}
                              {sug.sub_area && ` - ${AREAS.restaurant.subAreas[sug.sub_area]?.label}`}
                            </p>
                          </div>
                          <Badge variant="outline">
                            Score: {sug.score}
                          </Badge>
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </ScrollArea>
              
              <p className="text-xs text-muted-foreground text-center">
                KI-Vorschläge dienen nur als Empfehlung. Manuelle Auswahl erforderlich.
              </p>
            </div>
          </DialogContent>
        </Dialog>

        {/* Tisch-Admin Dialog (Vereinfacht) */}
        <Dialog open={showTableAdminDialog} onOpenChange={setShowTableAdminDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Tisch-Stammdaten verwalten</DialogTitle>
            </DialogHeader>
            
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Die Tisch-Verwaltung erfolgt über die Admin-Einstellungen oder API.
              </p>
              
              <div className="grid grid-cols-2 gap-4">
                <Card className="p-4">
                  <h4 className="font-semibold mb-2">Restaurant</h4>
                  <p className="text-sm text-muted-foreground">Saal + Wintergarten</p>
                  <p className="text-xs mt-2">
                    Tische aus Saal und Wintergarten dürfen NICHT kombiniert werden.
                  </p>
                </Card>
                <Card className="p-4">
                  <h4 className="font-semibold mb-2">Terrasse</h4>
                  <p className="text-sm text-muted-foreground">Außenbereich</p>
                  <p className="text-xs mt-2">
                    Keine Kombinationen mit Restaurant.
                  </p>
                </Card>
                <Card className="p-4">
                  <h4 className="font-semibold mb-2">Event</h4>
                  <p className="text-sm text-muted-foreground">Sonderbereich</p>
                  <p className="text-xs mt-2">
                    Blockiert reguläre Reservierungen.
                  </p>
                </Card>
                <Card className="p-4 border-dashed">
                  <h4 className="font-semibold mb-2">Tisch 3 (Sonderfall)</h4>
                  <p className="text-sm text-muted-foreground">Oval / Exot</p>
                  <p className="text-xs mt-2 text-orange-600">
                    Darf NIE kombiniert werden.
                  </p>
                </Card>
              </div>
              
              <p className="text-sm">
                Zum Anlegen von Tischen nutzen Sie bitte:
                <code className="ml-2 px-2 py-1 bg-muted rounded">POST /api/tables</code>
              </p>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default TablePlan;
