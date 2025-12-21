import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
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
  CreditCard,
  RefreshCw,
  Loader2,
  Euro,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  RotateCcw,
  Send,
  Eye,
  Search,
} from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const STATUS_CONFIG = {
  unpaid: { label: "Unbezahlt", color: "bg-gray-100 text-gray-800", icon: Clock },
  payment_pending: { label: "Ausstehend", color: "bg-yellow-100 text-yellow-800", icon: Clock },
  paid: { label: "Bezahlt", color: "bg-green-100 text-green-800", icon: CheckCircle },
  partially_paid: { label: "Teilzahlung", color: "bg-blue-100 text-blue-800", icon: AlertTriangle },
  refunded: { label: "Erstattet", color: "bg-purple-100 text-purple-800", icon: RotateCcw },
  failed: { label: "Fehlgeschlagen", color: "bg-red-100 text-red-800", icon: XCircle },
};

export const PaymentTransactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [showRefundDialog, setShowRefundDialog] = useState(false);
  const [showManualDialog, setShowManualDialog] = useState(false);
  const [refundReason, setRefundReason] = useState("");
  const [manualReason, setManualReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchTransactions();
  }, [statusFilter]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = { limit: 200 };
      if (statusFilter !== "all") params.status = statusFilter;
      
      const response = await axios.get(`${BACKEND_URL}/api/payments/transactions`, { headers, params });
      setTransactions(response.data);
    } catch (err) {
      toast.error("Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  };

  const handleResendLink = async (transactionId) => {
    setActionLoading(true);
    try {
      const response = await axios.post(`${BACKEND_URL}/api/payments/resend/${transactionId}`, {}, { headers });
      toast.success("Zahlungslink kopiert");
      navigator.clipboard.writeText(response.data.checkout_url);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    } finally {
      setActionLoading(false);
    }
  };

  const handleManualPayment = async () => {
    if (!manualReason || manualReason.length < 5) {
      toast.error("Bitte geben Sie eine Begründung an (mind. 5 Zeichen)");
      return;
    }
    setActionLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/payments/manual/${selectedTransaction.id}`, { reason: manualReason }, { headers });
      toast.success("Zahlung als erhalten markiert");
      setShowManualDialog(false);
      setManualReason("");
      fetchTransactions();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    } finally {
      setActionLoading(false);
    }
  };

  const handleRefund = async () => {
    if (!refundReason || refundReason.length < 5) {
      toast.error("Bitte geben Sie eine Begründung an (mind. 5 Zeichen)");
      return;
    }
    setActionLoading(true);
    try {
      await axios.post(`${BACKEND_URL}/api/payments/refund/${selectedTransaction.id}`, { reason: refundReason }, { headers });
      toast.success("Erstattung durchgeführt");
      setShowRefundDialog(false);
      setRefundReason("");
      fetchTransactions();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    } finally {
      setActionLoading(false);
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

  const filteredTransactions = transactions.filter((t) => {
    if (!search) return true;
    return (
      t.entity_id?.toLowerCase().includes(search.toLowerCase()) ||
      t.id?.toLowerCase().includes(search.toLowerCase())
    );
  });

  // Calculate stats
  const stats = {
    total: transactions.length,
    paid: transactions.filter(t => t.payment_status === "paid").length,
    pending: transactions.filter(t => t.payment_status === "payment_pending").length,
    totalAmount: transactions.filter(t => t.payment_status === "paid").reduce((sum, t) => sum + (t.amount || 0), 0),
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Zahlungen
            </h1>
            <p className="text-muted-foreground mt-1">
              Übersicht aller Zahlungstransaktionen
            </p>
          </div>
          <Button variant="outline" onClick={fetchTransactions} className="rounded-full">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-primary">{stats.total}</p>
              <p className="text-sm text-muted-foreground">Gesamt</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-green-600">{stats.paid}</p>
              <p className="text-sm text-muted-foreground">Bezahlt</p>
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
              <p className="text-3xl font-bold text-primary">{stats.totalAmount.toFixed(2)} €</p>
              <p className="text-sm text-muted-foreground">Einnahmen</p>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardContent className="p-4">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <Input
                    placeholder="Suche nach ID..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Status</SelectItem>
                  {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                    <SelectItem key={key} value={key}>{config.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Transactions List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
          </div>
        ) : filteredTransactions.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <CreditCard className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Transaktionen gefunden</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredTransactions.map((transaction) => {
              const statusConfig = STATUS_CONFIG[transaction.payment_status] || STATUS_CONFIG.unpaid;
              const StatusIcon = statusConfig.icon;
              
              return (
                <Card
                  key={transaction.id}
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => {
                    setSelectedTransaction(transaction);
                    setShowDetailDialog(true);
                  }}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-full ${statusConfig.color}`}>
                          <StatusIcon className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">
                              {transaction.entity_type === "reservation" ? "Reservierung" : "Event-Buchung"}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              {transaction.payment_type?.replace("_", " ")}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {formatDateTime(transaction.created_at)}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-xl font-bold text-primary">
                            {transaction.amount?.toFixed(2)} €
                          </p>
                        </div>
                        <Badge className={statusConfig.color}>
                          {statusConfig.label}
                        </Badge>
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
            <DialogTitle>Transaktionsdetails</DialogTitle>
            <DialogDescription>
              ID: {selectedTransaction?.id?.slice(0, 8)}...
            </DialogDescription>
          </DialogHeader>
          
          {selectedTransaction && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 p-4 bg-muted rounded-lg">
                <div>
                  <p className="text-sm text-muted-foreground">Typ</p>
                  <p className="font-medium">
                    {selectedTransaction.entity_type === "reservation" ? "Reservierung" : "Event-Buchung"}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Betrag</p>
                  <p className="font-medium text-primary">
                    {selectedTransaction.amount?.toFixed(2)} {selectedTransaction.currency}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <Badge className={STATUS_CONFIG[selectedTransaction.payment_status]?.color}>
                    {STATUS_CONFIG[selectedTransaction.payment_status]?.label}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Zahlungsart</p>
                  <p className="font-medium">{selectedTransaction.payment_type?.replace("_", " ")}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Erstellt</p>
                  <p className="font-medium">{formatDateTime(selectedTransaction.created_at)}</p>
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Session ID</p>
                  <p className="font-medium font-mono text-xs">{selectedTransaction.session_id?.slice(0, 20)}...</p>
                </div>
              </div>
              
              {selectedTransaction.manual_payment && (
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <p className="text-sm font-medium text-yellow-800">Manuelle Zahlung</p>
                  <p className="text-sm text-yellow-700">{selectedTransaction.manual_reason}</p>
                  <p className="text-xs text-yellow-600 mt-1">von {selectedTransaction.manual_by}</p>
                </div>
              )}
              
              {selectedTransaction.refund_reason && (
                <div className="p-3 bg-purple-50 rounded-lg border border-purple-200">
                  <p className="text-sm font-medium text-purple-800">Erstattung</p>
                  <p className="text-sm text-purple-700">{selectedTransaction.refund_reason}</p>
                  <p className="text-xs text-purple-600 mt-1">von {selectedTransaction.refunded_by}</p>
                </div>
              )}
              
              <DialogFooter className="flex-col sm:flex-row gap-2">
                {selectedTransaction.payment_status === "payment_pending" && (
                  <>
                    <Button
                      variant="outline"
                      onClick={() => handleResendLink(selectedTransaction.id)}
                      disabled={actionLoading}
                    >
                      <Send className="h-4 w-4 mr-2" />
                      Link kopieren
                    </Button>
                    <Button
                      className="bg-green-600 hover:bg-green-700"
                      onClick={() => {
                        setShowDetailDialog(false);
                        setShowManualDialog(true);
                      }}
                    >
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Manuell bezahlt
                    </Button>
                  </>
                )}
                {selectedTransaction.payment_status === "paid" && !selectedTransaction.refund_reason && (
                  <Button
                    variant="destructive"
                    onClick={() => {
                      setShowDetailDialog(false);
                      setShowRefundDialog(true);
                    }}
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Erstatten
                  </Button>
                )}
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Manual Payment Dialog */}
      <Dialog open={showManualDialog} onOpenChange={setShowManualDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Manuelle Zahlung erfassen</DialogTitle>
            <DialogDescription>
              Markieren Sie diese Zahlung als manuell erhalten (z.B. Bar, Überweisung)
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Begründung *</Label>
            <Textarea
              value={manualReason}
              onChange={(e) => setManualReason(e.target.value)}
              placeholder="z.B. Barzahlung vor Ort erhalten"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowManualDialog(false)}>
              Abbrechen
            </Button>
            <Button onClick={handleManualPayment} disabled={actionLoading}>
              {actionLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Bestätigen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Refund Dialog */}
      <Dialog open={showRefundDialog} onOpenChange={setShowRefundDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Erstattung durchführen</DialogTitle>
            <DialogDescription>
              Der Betrag von {selectedTransaction?.amount?.toFixed(2)} € wird erstattet
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Label>Begründung *</Label>
            <Textarea
              value={refundReason}
              onChange={(e) => setRefundReason(e.target.value)}
              placeholder="z.B. Stornierung durch Gast"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowRefundDialog(false)}>
              Abbrechen
            </Button>
            <Button variant="destructive" onClick={handleRefund} disabled={actionLoading}>
              {actionLoading && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Erstatten
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default PaymentTransactions;
