import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
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
import { toast } from "sonner";
import {
  ArrowLeft,
  RefreshCw,
  Users,
  Phone,
  Mail,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  Euro,
  UtensilsCrossed,
  AlertTriangle,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  pending: { label: "Ausstehend", color: "bg-yellow-100 text-yellow-800", icon: Clock },
  confirmed: { label: "Bestätigt", color: "bg-green-100 text-green-800", icon: CheckCircle },
  cancelled: { label: "Storniert", color: "bg-gray-100 text-gray-800", icon: XCircle },
  no_show: { label: "No-Show", color: "bg-red-100 text-red-800", icon: AlertTriangle },
};

export const EventBookings = () => {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, [eventId, statusFilter]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params = statusFilter !== "all" ? { status: statusFilter } : {};
      const [eventRes, bookingsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/events/${eventId}`, { headers }),
        axios.get(`${BACKEND_URL}/api/events/${eventId}/bookings`, { headers, params }),
      ]);
      setEvent(eventRes.data);
      setBookings(bookingsRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden");
      navigate("/events");
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (bookingId, newStatus) => {
    setActionLoading(bookingId);
    try {
      await axios.patch(
        `${BACKEND_URL}/api/events/${eventId}/bookings/${bookingId}`,
        { status: newStatus },
        { headers }
      );
      toast.success(`Status geändert: ${STATUS_CONFIG[newStatus]?.label}`);
      fetchData();
      setShowDetailDialog(false);
    } catch (err) {
      toast.error("Fehler beim Ändern des Status");
    } finally {
      setActionLoading(null);
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

  // Calculate stats
  const stats = {
    total: bookings.length,
    confirmed: bookings.filter(b => b.status === "confirmed").length,
    pending: bookings.filter(b => b.status === "pending").length,
    cancelled: bookings.filter(b => b.status === "cancelled").length,
    totalGuests: bookings.filter(b => b.status !== "cancelled").reduce((sum, b) => sum + (b.party_size || 0), 0),
  };

  // Calculate preorder summary for kitchen
  const preorderSummary = {};
  bookings.forEach(booking => {
    if (booking.status !== "cancelled" && booking.items) {
      booking.items.forEach(item => {
        const key = item.product_name || item.event_product_id;
        preorderSummary[key] = (preorderSummary[key] || 0) + item.quantity;
      });
    }
  });

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/events")} className="rounded-full">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="font-serif text-3xl font-medium text-primary">
              Buchungen
            </h1>
            <p className="text-muted-foreground">
              {event?.title} • {formatDateTime(event?.start_datetime)}
            </p>
          </div>
          <Button variant="outline" onClick={fetchData} className="rounded-full">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{stats.total}</p>
              <p className="text-sm text-muted-foreground">Buchungen</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-green-600">{stats.confirmed}</p>
              <p className="text-sm text-muted-foreground">Bestätigt</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-yellow-600">{stats.pending}</p>
              <p className="text-sm text-muted-foreground">Ausstehend</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{stats.totalGuests}</p>
              <p className="text-sm text-muted-foreground">Gäste</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{event?.available_capacity || 0}</p>
              <p className="text-sm text-muted-foreground">Frei</p>
            </CardContent>
          </Card>
        </div>

        {/* Preorder Summary for Kitchen */}
        {Object.keys(preorderSummary).length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <UtensilsCrossed className="h-5 w-5" />
                Vorbestellungen (Küche)
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-4">
                {Object.entries(preorderSummary).map(([name, qty]) => (
                  <div key={name} className="bg-muted px-4 py-2 rounded-lg">
                    <span className="font-bold text-2xl text-primary">{qty}x</span>
                    <span className="ml-2">{name}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Filter */}
        <Card>
          <CardContent className="p-4">
            <div className="flex gap-4 items-center">
              <span className="text-sm text-muted-foreground">Status:</span>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle</SelectItem>
                  <SelectItem value="confirmed">Bestätigt</SelectItem>
                  <SelectItem value="pending">Ausstehend</SelectItem>
                  <SelectItem value="cancelled">Storniert</SelectItem>
                  <SelectItem value="no_show">No-Show</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Bookings List */}
        {bookings.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Buchungen gefunden</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {bookings.map((booking) => {
              const statusConfig = STATUS_CONFIG[booking.status] || STATUS_CONFIG.pending;
              const StatusIcon = statusConfig.icon;
              const isLoading = actionLoading === booking.id;
              
              return (
                <Card
                  key={booking.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    setSelectedBooking(booking);
                    setShowDetailDialog(true);
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="text-center bg-primary/10 rounded-lg p-3 min-w-[60px]">
                          <p className="text-2xl font-bold text-primary">{booking.party_size}</p>
                          <p className="text-xs text-muted-foreground">Pers.</p>
                        </div>
                        
                        <div>
                          <p className="font-semibold">{booking.guest_name}</p>
                          <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <Phone className="h-3 w-3" />
                              {booking.guest_phone}
                            </span>
                            {booking.guest_email && (
                              <span className="flex items-center gap-1">
                                <Mail className="h-3 w-3" />
                                {booking.guest_email}
                              </span>
                            )}
                          </div>
                          {booking.items && booking.items.length > 0 && (
                            <div className="flex items-center gap-2 mt-1">
                              <UtensilsCrossed className="h-3 w-3 text-muted-foreground" />
                              <span className="text-sm text-muted-foreground">
                                {booking.items.map(i => `${i.quantity}x ${i.product_name}`).join(", ")}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-3">
                        {booking.total_price > 0 && (
                          <span className="font-medium">
                            {booking.total_price?.toFixed(2)} €
                          </span>
                        )}
                        <Badge className={statusConfig.color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {statusConfig.label}
                        </Badge>
                        <span className="text-xs text-muted-foreground font-mono">
                          {booking.confirmation_code}
                        </span>
                        {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Buchungsdetails</DialogTitle>
            <DialogDescription>
              Code: {selectedBooking?.confirmation_code}
            </DialogDescription>
          </DialogHeader>
          
          {selectedBooking && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Gast</p>
                  <p className="font-medium">{selectedBooking.guest_name}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Personen</p>
                  <p className="font-medium">{selectedBooking.party_size}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Telefon</p>
                  <p className="font-medium">{selectedBooking.guest_phone}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">E-Mail</p>
                  <p className="font-medium">{selectedBooking.guest_email || "-"}</p>
                </div>
                {selectedBooking.total_price > 0 && (
                  <>
                    <div>
                      <p className="text-sm text-muted-foreground">Gesamtpreis</p>
                      <p className="font-medium">{selectedBooking.total_price?.toFixed(2)} €</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Zahlung</p>
                      <p className="font-medium">{selectedBooking.payment_status === "paid" ? "Bezahlt" : "Offen"}</p>
                    </div>
                  </>
                )}
              </div>
              
              {selectedBooking.items && selectedBooking.items.length > 0 && (
                <div className="p-4 bg-amber-50 rounded-lg border border-amber-200">
                  <p className="text-sm font-medium text-amber-800 mb-2 flex items-center gap-2">
                    <UtensilsCrossed className="h-4 w-4" />
                    Vorbestellung
                  </p>
                  <div className="space-y-1">
                    {selectedBooking.items.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span>{item.quantity}x {item.product_name}</span>
                        {item.note && <span className="text-muted-foreground">({item.note})</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {selectedBooking.notes && (
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm text-muted-foreground">Notizen</p>
                  <p>{selectedBooking.notes}</p>
                </div>
              )}
              
              <DialogFooter className="flex-col sm:flex-row gap-2">
                {selectedBooking.status === "pending" && (
                  <Button
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => handleStatusChange(selectedBooking.id, "confirmed")}
                    disabled={actionLoading === selectedBooking.id}
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Bestätigen
                  </Button>
                )}
                {selectedBooking.status === "confirmed" && (
                  <Button
                    variant="destructive"
                    onClick={() => handleStatusChange(selectedBooking.id, "no_show")}
                    disabled={actionLoading === selectedBooking.id}
                  >
                    <AlertTriangle className="h-4 w-4 mr-2" />
                    No-Show
                  </Button>
                )}
                {["pending", "confirmed"].includes(selectedBooking.status) && (
                  <Button
                    variant="outline"
                    onClick={() => handleStatusChange(selectedBooking.id, "cancelled")}
                    disabled={actionLoading === selectedBooking.id}
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Stornieren
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default EventBookings;
