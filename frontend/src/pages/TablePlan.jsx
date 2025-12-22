import React, { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
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
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { ScrollArea } from "../components/ui/scroll-area";
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
} from "lucide-react";
import { format, addDays, subDays } from "date-fns";
import { de } from "date-fns/locale";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Zeitfenster-Optionen
const TIME_SLOTS = [
  { label: "11:00 - 14:00", start: "11:00", end: "14:00" },
  { label: "14:00 - 17:00", start: "14:00", end: "17:00" },
  { label: "17:00 - 20:00", start: "17:00", end: "20:00" },
  { label: "20:00 - 23:00", start: "20:00", end: "23:00" },
  { label: "Alle", start: "00:00", end: "23:59" },
];

// Status-Farben für Tischkarten
const STATUS_COLORS = {
  neu: "bg-yellow-100 border-yellow-400",
  bestaetigt: "bg-blue-100 border-blue-400",
  angekommen: "bg-green-100 border-green-500",
  abgeschlossen: "bg-gray-100 border-gray-300",
  no_show: "bg-red-100 border-red-400",
  storniert: "bg-gray-50 border-gray-200 opacity-50",
};

export const TablePlan = () => {
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [selectedTimeSlot, setSelectedTimeSlot] = useState(TIME_SLOTS[0]);
  const [reservations, setReservations] = useState([]);
  const [tables, setTables] = useState([]);
  const [areas, setAreas] = useState([]);
  const [selectedArea, setSelectedArea] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selectedReservation, setSelectedReservation] = useState(null);

  // Fetch data
  useEffect(() => {
    fetchData();
  }, [selectedDate, selectedArea]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [resRes, areasRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/reservations`, {
          params: { date: selectedDate },
          headers,
        }),
        axios.get(`${BACKEND_URL}/api/areas`, { headers }),
      ]);
      
      setReservations(resRes.data.filter(r => 
        !r.archived && r.status !== "storniert"
      ));
      setAreas(areasRes.data.filter(a => !a.archived));
      
      // Generiere Tische basierend auf Reservierungen mit Tischnummer
      const uniqueTables = [...new Set(resRes.data
        .filter(r => r.table_number)
        .map(r => r.table_number)
      )].sort((a, b) => {
        const numA = parseInt(a) || 0;
        const numB = parseInt(b) || 0;
        return numA - numB;
      });
      setTables(uniqueTables);
      
    } catch (err) {
      console.error("Fehler beim Laden:", err);
      toast.error("Daten konnten nicht geladen werden");
    } finally {
      setLoading(false);
    }
  };

  // Filter Reservierungen nach Zeitfenster
  const filteredReservations = reservations.filter(res => {
    // Zeitfilter
    if (selectedTimeSlot.start !== "00:00") {
      const resTime = res.time;
      if (resTime < selectedTimeSlot.start || resTime >= selectedTimeSlot.end) {
        return false;
      }
    }
    // Bereichsfilter
    if (selectedArea !== "all" && res.area_id !== selectedArea) {
      return false;
    }
    return true;
  });

  // Gruppiere nach Tisch
  const reservationsByTable = filteredReservations.reduce((acc, res) => {
    const table = res.table_number || "Ohne Tisch";
    if (!acc[table]) acc[table] = [];
    acc[table].push(res);
    return acc;
  }, {});

  // Datum Navigation
  const goToPreviousDay = () => setSelectedDate(format(subDays(new Date(selectedDate), 1), "yyyy-MM-dd"));
  const goToNextDay = () => setSelectedDate(format(addDays(new Date(selectedDate), 1), "yyyy-MM-dd"));
  const goToToday = () => setSelectedDate(format(new Date(), "yyyy-MM-dd"));

  // PDF Export Handler
  const handlePrintPDF = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/export/table-plan`,
        {
          params: { 
            date: selectedDate,
            time_start: selectedTimeSlot.start,
            time_end: selectedTimeSlot.end,
            area_id: selectedArea !== "all" ? selectedArea : undefined,
          },
          headers,
          responseType: 'blob',
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `tischplan_${selectedDate}_${selectedTimeSlot.label.replace(/[:\s-]/g, '')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success("PDF heruntergeladen");
    } catch (err) {
      toast.error("PDF-Export fehlgeschlagen");
    }
  };

  // Hilfsfunktion: Hat besondere Hinweise?
  const getSpecialIndicators = (res) => {
    const indicators = [];
    
    // Geburtstag
    if (res.occasion?.toLowerCase().includes("geburtstag") || res.notes?.toLowerCase().includes("geburtstag")) {
      indicators.push({ icon: Cake, color: "text-pink-500", label: "Geburtstag" });
    }
    
    // Allergien
    if (res.allergies || res.notes?.toLowerCase().includes("allergi") || res.notes?.toLowerCase().includes("unverträgl")) {
      indicators.push({ icon: AlertTriangle, color: "text-orange-500", label: "Allergien" });
    }
    
    // Vegetarisch/Vegan
    if (res.menu_choice?.toLowerCase().includes("veget") || res.notes?.toLowerCase().includes("veget") || res.notes?.toLowerCase().includes("vegan")) {
      indicators.push({ icon: Leaf, color: "text-green-500", label: "Vegetarisch" });
    }
    
    // Verlängert
    if (res.is_extended) {
      indicators.push({ icon: Timer, color: "text-blue-500", label: "Verlängert" });
    }
    
    return indicators;
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
              Übersicht aller Reservierungen nach Tisch
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={fetchData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Aktualisieren
            </Button>
            <Button onClick={handlePrintPDF} className="bg-[#005500] hover:bg-[#003300]">
              <Printer className="h-4 w-4 mr-2" />
              PDF Drucken
            </Button>
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
                  value={selectedTimeSlot.label}
                  onValueChange={(v) => setSelectedTimeSlot(TIME_SLOTS.find(t => t.label === v) || TIME_SLOTS[0])}
                >
                  <SelectTrigger className="w-40">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TIME_SLOTS.map((slot) => (
                      <SelectItem key={slot.label} value={slot.label}>
                        {slot.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Bereich */}
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <Select value={selectedArea} onValueChange={setSelectedArea}>
                  <SelectTrigger className="w-40">
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
              </div>

              {/* Stats */}
              <div className="ml-auto flex items-center gap-4 text-sm">
                <Badge variant="outline" className="text-lg px-3 py-1">
                  <Users className="h-4 w-4 mr-2" />
                  {filteredReservations.reduce((sum, r) => sum + (r.party_size || 0), 0)} Gäste
                </Badge>
                <Badge variant="secondary" className="text-lg px-3 py-1">
                  {filteredReservations.length} Reservierungen
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

        {/* Tischplan Grid */}
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <RefreshCw className="h-12 w-12 animate-spin text-[#005500]" />
          </div>
        ) : filteredReservations.length === 0 ? (
          <Card className="p-12 text-center">
            <FileText className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
            <p className="text-xl text-muted-foreground">
              Keine Reservierungen für diesen Zeitraum
            </p>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {Object.entries(reservationsByTable).sort(([a], [b]) => {
              const numA = parseInt(a) || 999;
              const numB = parseInt(b) || 999;
              return numA - numB;
            }).map(([tableNumber, tableReservations]) => (
              <Card 
                key={tableNumber} 
                className={`${tableNumber === "Ohne Tisch" ? "border-dashed" : "border-solid"} border-2`}
              >
                <CardHeader className="pb-2 bg-muted/50">
                  <CardTitle className="flex items-center justify-between">
                    <span className="text-lg">
                      {tableNumber === "Ohne Tisch" ? "Ohne Tisch" : `Tisch ${tableNumber}`}
                    </span>
                    <Badge variant="secondary">
                      {tableReservations.reduce((sum, r) => sum + (r.party_size || 0), 0)} Pers.
                    </Badge>
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-3 space-y-3">
                  {tableReservations.sort((a, b) => a.time.localeCompare(b.time)).map((res) => {
                    const indicators = getSpecialIndicators(res);
                    return (
                      <div
                        key={res.id}
                        className={`p-3 rounded-lg border-2 cursor-pointer hover:shadow-md transition-shadow ${STATUS_COLORS[res.status] || 'bg-white'}`}
                        onClick={() => setSelectedReservation(res)}
                      >
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-semibold">{res.guest_name}</p>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground">
                              <Clock className="h-3 w-3" />
                              {res.time}
                              <Users className="h-3 w-3 ml-2" />
                              {res.party_size}
                            </div>
                          </div>
                          {indicators.length > 0 && (
                            <div className="flex gap-1">
                              {indicators.map((ind, i) => (
                                <ind.icon key={i} className={`h-4 w-4 ${ind.color}`} title={ind.label} />
                              ))}
                            </div>
                          )}
                        </div>
                        {(res.notes || res.allergies || res.menu_choice) && (
                          <div className="mt-2 pt-2 border-t border-dashed text-xs text-muted-foreground">
                            {res.allergies && (
                              <p className="text-orange-600 font-medium">⚠ {res.allergies}</p>
                            )}
                            {res.menu_choice && (
                              <p className="text-green-600">Menü: {res.menu_choice}</p>
                            )}
                            {res.notes && <p className="truncate">{res.notes}</p>}
                          </div>
                        )}
                        {res.is_extended && (
                          <Badge variant="outline" className="mt-2 text-xs">
                            <Timer className="h-3 w-3 mr-1" />
                            Verlängert
                          </Badge>
                        )}
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* Detail Dialog */}
        <Dialog open={!!selectedReservation} onOpenChange={() => setSelectedReservation(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reservierungsdetails</DialogTitle>
            </DialogHeader>
            {selectedReservation && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">Gast</Label>
                    <p className="font-semibold text-lg">{selectedReservation.guest_name}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Telefon</Label>
                    <p>{selectedReservation.guest_phone}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Uhrzeit</Label>
                    <p className="font-semibold">{selectedReservation.time}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">Personen</Label>
                    <p>{selectedReservation.party_size}</p>
                  </div>
                  {selectedReservation.table_number && (
                    <div>
                      <Label className="text-muted-foreground">Tisch</Label>
                      <p>Tisch {selectedReservation.table_number}</p>
                    </div>
                  )}
                  {selectedReservation.occasion && (
                    <div>
                      <Label className="text-muted-foreground">Anlass</Label>
                      <p>{selectedReservation.occasion}</p>
                    </div>
                  )}
                </div>
                {selectedReservation.allergies && (
                  <div className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                    <Label className="text-orange-600 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Allergien/Unverträglichkeiten
                    </Label>
                    <p className="mt-1">{selectedReservation.allergies}</p>
                  </div>
                )}
                {selectedReservation.menu_choice && (
                  <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                    <Label className="text-green-600 flex items-center gap-2">
                      <Leaf className="h-4 w-4" />
                      Menüwahl
                    </Label>
                    <p className="mt-1">{selectedReservation.menu_choice}</p>
                  </div>
                )}
                {selectedReservation.notes && (
                  <div>
                    <Label className="text-muted-foreground">Notizen</Label>
                    <p className="mt-1 p-3 bg-muted rounded-lg">{selectedReservation.notes}</p>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
};

export default TablePlan;
