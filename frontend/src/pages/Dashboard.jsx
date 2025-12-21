import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { reservationsApi, areasApi } from "../lib/api";
import { t } from "../lib/i18n";
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
import { toast } from "sonner";
import {
  Search,
  Plus,
  RefreshCw,
  Users,
  Clock,
  Phone,
  MapPin,
  ChevronRight,
  Calendar,
  Loader2,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";

const STATUS_OPTIONS = [
  { value: "neu", label: "Neu", next: "bestaetigt" },
  { value: "bestaetigt", label: "Bestätigt", next: "angekommen" },
  { value: "angekommen", label: "Angekommen", next: "abgeschlossen" },
  { value: "abgeschlossen", label: "Abgeschlossen", next: null },
  { value: "no_show", label: "No-Show", next: null },
  { value: "storniert", label: "Storniert", next: null },
];

const getStatusBadgeClass = (status) => {
  const classes = {
    neu: "status-neu",
    bestaetigt: "status-bestaetigt",
    angekommen: "status-angekommen",
    abgeschlossen: "status-abgeschlossen",
    no_show: "status-no_show",
  };
  return classes[status] || "";
};

export const Dashboard = () => {
  const { isSchichtleiter } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [areaFilter, setAreaFilter] = useState("all");
  const [selectedDate, setSelectedDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState(null);
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
  const [submitting, setSubmitting] = useState(false);

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
    } catch (err) {
      toast.error("Fehler beim Laden der Daten");
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

  const handleStatusChange = async (reservation, newStatus) => {
    try {
      await reservationsApi.updateStatus(reservation.id, newStatus);
      toast.success(`Status geändert zu "${t(`status.${newStatus}`)}"`);
      fetchData();
      setShowDetailDialog(false);
    } catch (err) {
      toast.error("Fehler beim Ändern des Status");
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await reservationsApi.create(formData);
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
      toast.error("Fehler beim Erstellen der Reservierung");
    } finally {
      setSubmitting(false);
    }
  };

  const getAreaName = (areaId) => {
    const area = areas.find((a) => a.id === areaId);
    return area?.name || "-";
  };

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
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={fetchData}
              data-testid="refresh-button"
              className="rounded-full"
            >
              <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
            </Button>
            {isSchichtleiter() && (
              <Button
                onClick={() => setShowCreateDialog(true)}
                data-testid="new-reservation-button"
                className="rounded-full"
              >
                <Plus size={16} className="mr-2" />
                {t("reservations.newReservation")}
              </Button>
            )}
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-primary/10">
                  <Calendar size={20} className="text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.total}</p>
                  <p className="text-xs text-muted-foreground">Gesamt</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-[#ffed00]/20">
                  <Clock size={20} className="text-[#00280b]" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.neu}</p>
                  <p className="text-xs text-muted-foreground">Neu</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-[#a2d2ff]/30">
                  <Clock size={20} className="text-[#00280b]" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.bestaetigt}</p>
                  <p className="text-xs text-muted-foreground">Bestätigt</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-primary/10">
                  <Users size={20} className="text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.angekommen}</p>
                  <p className="text-xs text-muted-foreground">Angekommen</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-full bg-muted">
                  <Users size={20} className="text-muted-foreground" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stats.guests}</p>
                  <p className="text-xs text-muted-foreground">Gäste</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card className="bg-card">
          <CardContent className="p-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                  <Input
                    placeholder={t("reservations.search")}
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10"
                    data-testid="search-input"
                  />
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                <Input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="w-auto"
                  data-testid="date-filter"
                />
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[140px]" data-testid="status-filter">
                    <SelectValue placeholder="Status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t("common.all")}</SelectItem>
                    {STATUS_OPTIONS.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        {s.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={areaFilter} onValueChange={setAreaFilter}>
                  <SelectTrigger className="w-[140px]" data-testid="area-filter">
                    <SelectValue placeholder="Bereich" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">{t("common.all")}</SelectItem>
                    {areas.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Reservations List */}
        <div className="space-y-3">
          {loading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
          ) : reservations.length === 0 ? (
            <Card className="bg-card">
              <CardContent className="py-12 text-center">
                <Calendar className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">{t("reservations.noReservations")}</p>
              </CardContent>
            </Card>
          ) : (
            reservations.map((reservation) => (
              <Card
                key={reservation.id}
                className="bg-card hover:shadow-md transition-all cursor-pointer group"
                onClick={() => {
                  setSelectedReservation(reservation);
                  setShowDetailDialog(true);
                }}
                data-testid={`reservation-${reservation.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 flex-1">
                      <div className="w-16 text-center">
                        <p className="text-lg font-bold">{reservation.time}</p>
                        <p className="text-xs text-muted-foreground">Uhr</p>
                      </div>
                      <div className="h-12 w-px bg-border" />
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{reservation.guest_name}</p>
                        <div className="flex items-center gap-3 text-sm text-muted-foreground mt-1">
                          <span className="flex items-center gap-1">
                            <Users size={14} />
                            {reservation.party_size} {t("common.persons")}
                          </span>
                          <span className="flex items-center gap-1">
                            <Phone size={14} />
                            {reservation.guest_phone}
                          </span>
                          {reservation.area_id && (
                            <span className="flex items-center gap-1">
                              <MapPin size={14} />
                              {getAreaName(reservation.area_id)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={`${getStatusBadgeClass(reservation.status)} border`}>
                        {t(`status.${reservation.status}`)}
                      </Badge>
                      <ChevronRight
                        size={20}
                        className="text-muted-foreground group-hover:text-foreground transition-colors"
                      />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">
              {t("reservations.newReservation")}
            </DialogTitle>
            <DialogDescription>
              Erstellen Sie eine neue Reservierung
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate}>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="guest_name">{t("reservations.guestName")} *</Label>
                  <Input
                    id="guest_name"
                    value={formData.guest_name}
                    onChange={(e) => setFormData({ ...formData, guest_name: e.target.value })}
                    required
                    data-testid="form-guest-name"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="guest_phone">{t("reservations.phone")} *</Label>
                  <Input
                    id="guest_phone"
                    value={formData.guest_phone}
                    onChange={(e) => setFormData({ ...formData, guest_phone: e.target.value })}
                    required
                    data-testid="form-guest-phone"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="guest_email">{t("reservations.email")}</Label>
                <Input
                  id="guest_email"
                  type="email"
                  value={formData.guest_email}
                  onChange={(e) => setFormData({ ...formData, guest_email: e.target.value })}
                  data-testid="form-guest-email"
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="date">{t("reservations.date")} *</Label>
                  <Input
                    id="date"
                    type="date"
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    required
                    data-testid="form-date"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="time">{t("reservations.time")} *</Label>
                  <Input
                    id="time"
                    type="time"
                    value={formData.time}
                    onChange={(e) => setFormData({ ...formData, time: e.target.value })}
                    required
                    data-testid="form-time"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="party_size">{t("reservations.partySize")} *</Label>
                  <Input
                    id="party_size"
                    type="number"
                    min="1"
                    value={formData.party_size}
                    onChange={(e) =>
                      setFormData({ ...formData, party_size: parseInt(e.target.value) || 1 })
                    }
                    required
                    data-testid="form-party-size"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="area">{t("reservations.area")}</Label>
                <Select
                  value={formData.area_id}
                  onValueChange={(v) => setFormData({ ...formData, area_id: v })}
                >
                  <SelectTrigger data-testid="form-area">
                    <SelectValue placeholder="Bereich wählen..." />
                  </SelectTrigger>
                  <SelectContent>
                    {areas.map((a) => (
                      <SelectItem key={a.id} value={a.id}>
                        {a.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="notes">{t("reservations.notes")}</Label>
                <Textarea
                  id="notes"
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  data-testid="form-notes"
                />
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
                className="rounded-full"
              >
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full" data-testid="form-submit">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {t("common.create")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-[500px]">
          {selectedReservation && (
            <>
              <DialogHeader>
                <DialogTitle className="font-serif text-2xl">
                  {selectedReservation.guest_name}
                </DialogTitle>
                <DialogDescription>
                  Reservierung #{selectedReservation.id.slice(0, 8)}
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <Badge className={`${getStatusBadgeClass(selectedReservation.status)} border mt-1`}>
                      {t(`status.${selectedReservation.status}`)}
                    </Badge>
                  </div>
                  {isSchichtleiter() && (
                    <div className="flex gap-2">
                      {STATUS_OPTIONS.find((s) => s.value === selectedReservation.status)?.next && (
                        <Button
                          size="sm"
                          onClick={() =>
                            handleStatusChange(
                              selectedReservation,
                              STATUS_OPTIONS.find((s) => s.value === selectedReservation.status)?.next
                            )
                          }
                          className="rounded-full"
                          data-testid="next-status-button"
                        >
                          → {t(`status.${STATUS_OPTIONS.find((s) => s.value === selectedReservation.status)?.next}`)}
                        </Button>
                      )}
                      {selectedReservation.status !== "no_show" &&
                        selectedReservation.status !== "abgeschlossen" && (
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleStatusChange(selectedReservation, "no_show")}
                            className="rounded-full"
                            data-testid="no-show-button"
                          >
                            No-Show
                          </Button>
                        )}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.date")}</p>
                    <p className="font-medium">{selectedReservation.date}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.time")}</p>
                    <p className="font-medium">{selectedReservation.time} Uhr</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.partySize")}</p>
                    <p className="font-medium">{selectedReservation.party_size} {t("common.persons")}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.area")}</p>
                    <p className="font-medium">{getAreaName(selectedReservation.area_id) || "-"}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-muted-foreground">{t("reservations.phone")}</p>
                  <p className="font-medium">{selectedReservation.guest_phone}</p>
                </div>

                {selectedReservation.guest_email && (
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.email")}</p>
                    <p className="font-medium">{selectedReservation.guest_email}</p>
                  </div>
                )}

                {selectedReservation.notes && (
                  <div>
                    <p className="text-sm text-muted-foreground">{t("reservations.notes")}</p>
                    <p className="font-medium">{selectedReservation.notes}</p>
                  </div>
                )}
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => setShowDetailDialog(false)}
                  className="rounded-full"
                >
                  {t("common.cancel")}
                </Button>
              </DialogFooter>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Dashboard;
