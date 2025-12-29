/**
 * AbsencesAdmin.jsx - Admin Abwesenheiten-Verwaltung
 * Modul 30 V1.1: Abwesenheit & Personalakte
 * 
 * Funktionen:
 * - Alle Abwesenheiten auflisten
 * - Filter: Zeitraum, Status, Typ, Mitarbeiter
 * - Aktionen: Approve, Reject, Cancel
 * - Warnung bei Schicht-Kollision
 */

import React, { useState, useEffect, useCallback } from "react";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  Alert,
  AlertDescription,
} from "../components/ui/alert";
import { toast } from "sonner";
import {
  CalendarOff,
  RefreshCw,
  Loader2,
  Check,
  X,
  MoreVertical,
  Filter,
  Calendar,
  User,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Palmtree,
  Thermometer,
  Star,
  HelpCircle,
  Ban,
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { de } from "date-fns/locale";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Absence Type Config
const ABSENCE_TYPE_CONFIG = {
  VACATION: { label: "Urlaub", icon: Palmtree, color: "bg-green-100 text-green-700 border-green-200" },
  SICK: { label: "Krank", icon: Thermometer, color: "bg-red-100 text-red-700 border-red-200" },
  SPECIAL: { label: "Sonderfrei", icon: Star, color: "bg-purple-100 text-purple-700 border-purple-200" },
  OTHER: { label: "Sonstiges", icon: HelpCircle, color: "bg-gray-100 text-gray-700 border-gray-200" },
};

// Absence Status Config
const ABSENCE_STATUS_CONFIG = {
  REQUESTED: { label: "Beantragt", icon: Clock, color: "bg-yellow-100 text-yellow-700 border-yellow-300" },
  APPROVED: { label: "Genehmigt", icon: CheckCircle, color: "bg-green-100 text-green-700 border-green-300" },
  REJECTED: { label: "Abgelehnt", icon: XCircle, color: "bg-red-100 text-red-700 border-red-300" },
  CANCELLED: { label: "Storniert", icon: Ban, color: "bg-gray-100 text-gray-500 border-gray-300" },
};

export default function AbsencesAdmin() {
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [absences, setAbsences] = useState([]);
  const [staffMembers, setStaffMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  // Filters
  const [filterStatus, setFilterStatus] = useState("all");
  const [filterType, setFilterType] = useState("all");
  const [filterStaff, setFilterStaff] = useState("all");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");

  // Dialogs
  const [approveDialog, setApproveDialog] = useState(null);
  const [rejectDialog, setRejectDialog] = useState(null);
  const [cancelDialog, setCancelDialog] = useState(null);
  const [rejectReason, setRejectReason] = useState("");

  // Summary
  const [summary, setSummary] = useState({ total: 0, requested: 0, approved: 0, rejected: 0, cancelled: 0 });

  // Fetch absences
  const fetchAbsences = useCallback(async () => {
    try {
      setRefreshing(true);
      const params = new URLSearchParams();
      
      if (filterStatus !== "all") params.append("status", filterStatus);
      if (filterType !== "all") params.append("type", filterType);
      if (filterStaff !== "all") params.append("staff_member_id", filterStaff);
      if (filterDateFrom) params.append("date_from", filterDateFrom);
      if (filterDateTo) params.append("date_to", filterDateTo);

      const res = await axios.get(`${BACKEND_URL}/api/admin/absences?${params.toString()}`, { headers });
      setAbsences(res.data.data || []);
      setSummary(res.data.summary || { total: 0, requested: 0, approved: 0, rejected: 0, cancelled: 0 });
    } catch (err) {
      console.error("Error fetching absences:", err);
      toast.error("Fehler beim Laden der Abwesenheiten");
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, [filterStatus, filterType, filterStaff, filterDateFrom, filterDateTo, headers]);

  // Fetch staff members for filter dropdown
  const fetchStaffMembers = useCallback(async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/staff/members`, { headers });
      setStaffMembers(res.data || []);
    } catch (err) {
      console.error("Error fetching staff:", err);
    }
  }, [headers]);

  // Initial load
  useEffect(() => {
    fetchAbsences();
    fetchStaffMembers();
  }, []);

  // Reload when filters change
  useEffect(() => {
    fetchAbsences();
  }, [filterStatus, filterType, filterStaff, filterDateFrom, filterDateTo]);

  // Actions
  const handleApprove = async (absence) => {
    try {
      setActionLoading(true);
      await axios.post(
        `${BACKEND_URL}/api/admin/absences/${absence.id}/approve`,
        {},
        { headers }
      );
      toast.success("Abwesenheit genehmigt");
      setApproveDialog(null);
      fetchAbsences();
    } catch (err) {
      console.error("Error approving:", err);
      toast.error(err.response?.data?.detail || "Fehler beim Genehmigen");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async (absence) => {
    if (!rejectReason.trim()) {
      toast.error("Bitte geben Sie einen Ablehnungsgrund an");
      return;
    }

    try {
      setActionLoading(true);
      await axios.post(
        `${BACKEND_URL}/api/admin/absences/${absence.id}/reject`,
        { notes_admin: rejectReason },
        { headers }
      );
      toast.success("Abwesenheit abgelehnt");
      setRejectDialog(null);
      setRejectReason("");
      fetchAbsences();
    } catch (err) {
      console.error("Error rejecting:", err);
      toast.error(err.response?.data?.detail || "Fehler beim Ablehnen");
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancel = async (absence) => {
    try {
      setActionLoading(true);
      await axios.post(
        `${BACKEND_URL}/api/admin/absences/${absence.id}/cancel`,
        {},
        { headers }
      );
      toast.success("Abwesenheit storniert");
      setCancelDialog(null);
      fetchAbsences();
    } catch (err) {
      console.error("Error cancelling:", err);
      toast.error(err.response?.data?.detail || "Fehler beim Stornieren");
    } finally {
      setActionLoading(false);
    }
  };

  // Format helpers
  const formatDateRange = (start, end) => {
    try {
      const startDate = parseISO(start);
      const endDate = parseISO(end);
      return `${format(startDate, "dd.MM.yyyy", { locale: de })} – ${format(endDate, "dd.MM.yyyy", { locale: de })}`;
    } catch {
      return `${start} – ${end}`;
    }
  };

  const formatDate = (dateStr) => {
    try {
      return format(parseISO(dateStr), "dd.MM.yyyy", { locale: de });
    } catch {
      return dateStr;
    }
  };

  // Render
  if (loading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-[#005500]" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#005500] flex items-center gap-2">
              <CalendarOff className="h-6 w-6" />
              Abwesenheiten verwalten
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Urlaubsanträge, Krankmeldungen und Sonderfrei genehmigen oder ablehnen
            </p>
          </div>
          <Button
            variant="outline"
            onClick={fetchAbsences}
            disabled={refreshing}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
            Aktualisieren
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Card className="bg-gray-50">
            <CardContent className="py-4">
              <div className="text-2xl font-bold">{summary.total}</div>
              <div className="text-xs text-gray-500">Gesamt</div>
            </CardContent>
          </Card>
          <Card className="bg-yellow-50 border-yellow-200">
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-yellow-700">{summary.requested}</div>
              <div className="text-xs text-yellow-600">Beantragt</div>
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-green-700">{summary.approved}</div>
              <div className="text-xs text-green-600">Genehmigt</div>
            </CardContent>
          </Card>
          <Card className="bg-red-50 border-red-200">
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-red-700">{summary.rejected}</div>
              <div className="text-xs text-red-600">Abgelehnt</div>
            </CardContent>
          </Card>
          <Card className="bg-gray-50 border-gray-200">
            <CardContent className="py-4">
              <div className="text-2xl font-bold text-gray-500">{summary.cancelled}</div>
              <div className="text-xs text-gray-500">Storniert</div>
            </CardContent>
          </Card>
        </div>

        {/* Filters */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Filter className="h-4 w-4" />
              Filter
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <Label className="text-xs">Status</Label>
                <Select value={filterStatus} onValueChange={setFilterStatus}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Status</SelectItem>
                    <SelectItem value="REQUESTED">Beantragt</SelectItem>
                    <SelectItem value="APPROVED">Genehmigt</SelectItem>
                    <SelectItem value="REJECTED">Abgelehnt</SelectItem>
                    <SelectItem value="CANCELLED">Storniert</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Typ</Label>
                <Select value={filterType} onValueChange={setFilterType}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Typen</SelectItem>
                    <SelectItem value="VACATION">Urlaub</SelectItem>
                    <SelectItem value="SICK">Krank</SelectItem>
                    <SelectItem value="SPECIAL">Sonderfrei</SelectItem>
                    <SelectItem value="OTHER">Sonstiges</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Mitarbeiter</Label>
                <Select value={filterStaff} onValueChange={setFilterStaff}>
                  <SelectTrigger className="mt-1">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Alle Mitarbeiter</SelectItem>
                    {staffMembers.map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.full_name || `${staff.first_name} ${staff.last_name}`}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Von</Label>
                <Input
                  type="date"
                  value={filterDateFrom}
                  onChange={(e) => setFilterDateFrom(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label className="text-xs">Bis</Label>
                <Input
                  type="date"
                  value={filterDateTo}
                  onChange={(e) => setFilterDateTo(e.target.value)}
                  className="mt-1"
                />
              </div>
            </div>
            {(filterStatus !== "all" || filterType !== "all" || filterStaff !== "all" || filterDateFrom || filterDateTo) && (
              <Button
                variant="ghost"
                size="sm"
                className="mt-3 text-gray-500"
                onClick={() => {
                  setFilterStatus("all");
                  setFilterType("all");
                  setFilterStaff("all");
                  setFilterDateFrom("");
                  setFilterDateTo("");
                }}
              >
                <X className="h-3 w-3 mr-1" />
                Filter zurücksetzen
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Absences Table */}
        <Card>
          <CardContent className="p-0">
            {absences.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <CalendarOff className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                <p>Keine Abwesenheiten gefunden</p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Mitarbeiter</TableHead>
                    <TableHead>Typ</TableHead>
                    <TableHead>Zeitraum</TableHead>
                    <TableHead>Tage</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Notizen</TableHead>
                    <TableHead className="text-right">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {absences.map((absence) => {
                    const typeConfig = ABSENCE_TYPE_CONFIG[absence.type] || ABSENCE_TYPE_CONFIG.OTHER;
                    const statusConfig = ABSENCE_STATUS_CONFIG[absence.status] || ABSENCE_STATUS_CONFIG.REQUESTED;
                    const TypeIcon = typeConfig.icon;
                    const StatusIcon = statusConfig.icon;

                    return (
                      <TableRow key={absence.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <User className="h-4 w-4 text-gray-400" />
                            <span className="font-medium">{absence.staff_name || "Unbekannt"}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={typeConfig.color}>
                            <TypeIcon className="h-3 w-3 mr-1" />
                            {typeConfig.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm">
                            <Calendar className="h-3 w-3 text-gray-400" />
                            {formatDateRange(absence.start_date, absence.end_date)}
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm font-medium">{absence.days_count}</span>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusConfig.color}>
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {statusConfig.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-[200px] text-sm">
                            {absence.notes_employee && (
                              <div className="text-gray-600 truncate" title={absence.notes_employee}>
                                MA: {absence.notes_employee}
                              </div>
                            )}
                            {absence.notes_admin && (
                              <div className="text-red-600 truncate" title={absence.notes_admin}>
                                Admin: {absence.notes_admin}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-right">
                          {absence.status === "REQUESTED" && (
                            <div className="flex items-center justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-green-600 border-green-300 hover:bg-green-50"
                                onClick={() => setApproveDialog(absence)}
                              >
                                <Check className="h-3 w-3 mr-1" />
                                Genehmigen
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="text-red-600 border-red-300 hover:bg-red-50"
                                onClick={() => setRejectDialog(absence)}
                              >
                                <X className="h-3 w-3 mr-1" />
                                Ablehnen
                              </Button>
                            </div>
                          )}
                          {absence.status === "APPROVED" && (
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-gray-600"
                              onClick={() => setCancelDialog(absence)}
                            >
                              <Ban className="h-3 w-3 mr-1" />
                              Stornieren
                            </Button>
                          )}
                          {(absence.status === "REJECTED" || absence.status === "CANCELLED") && (
                            <span className="text-gray-400 text-sm">—</span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Approve Dialog */}
        <Dialog open={!!approveDialog} onOpenChange={() => setApproveDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Abwesenheit genehmigen?</DialogTitle>
              <DialogDescription>
                {approveDialog && (
                  <>
                    <strong>{approveDialog.staff_name}</strong> möchte {" "}
                    <strong>{ABSENCE_TYPE_CONFIG[approveDialog.type]?.label}</strong> {" "}
                    vom {formatDateRange(approveDialog.start_date, approveDialog.end_date)} {" "}
                    ({approveDialog.days_count} Tage).
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            {approveDialog?.has_shift_conflict && (
              <Alert className="border-yellow-300 bg-yellow-50">
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
                <AlertDescription className="text-yellow-800">
                  Warnung: Der Mitarbeiter hat Schichten im gewünschten Zeitraum!
                </AlertDescription>
              </Alert>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setApproveDialog(null)}>
                Abbrechen
              </Button>
              <Button
                onClick={() => handleApprove(approveDialog)}
                disabled={actionLoading}
                className="bg-green-600 hover:bg-green-700"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                <Check className="h-4 w-4 mr-2" />
                Genehmigen
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Reject Dialog */}
        <Dialog open={!!rejectDialog} onOpenChange={() => { setRejectDialog(null); setRejectReason(""); }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Abwesenheit ablehnen</DialogTitle>
              <DialogDescription>
                {rejectDialog && (
                  <>
                    Bitte geben Sie einen Grund für die Ablehnung an.
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              {rejectDialog && (
                <div className="bg-gray-50 p-3 rounded-lg text-sm">
                  <strong>{rejectDialog.staff_name}</strong>: {ABSENCE_TYPE_CONFIG[rejectDialog.type]?.label}<br />
                  {formatDateRange(rejectDialog.start_date, rejectDialog.end_date)} ({rejectDialog.days_count} Tage)
                </div>
              )}
              <div>
                <Label>Ablehnungsgrund (Pflicht)</Label>
                <Textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder="z.B. Zu viele Mitarbeiter bereits abwesend..."
                  rows={3}
                  className="mt-1"
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setRejectDialog(null); setRejectReason(""); }}>
                Abbrechen
              </Button>
              <Button
                onClick={() => handleReject(rejectDialog)}
                disabled={actionLoading || !rejectReason.trim()}
                variant="destructive"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                <X className="h-4 w-4 mr-2" />
                Ablehnen
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Cancel Dialog */}
        <Dialog open={!!cancelDialog} onOpenChange={() => setCancelDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Genehmigte Abwesenheit stornieren?</DialogTitle>
              <DialogDescription>
                {cancelDialog && (
                  <>
                    Dies wird die bereits genehmigte Abwesenheit von {" "}
                    <strong>{cancelDialog.staff_name}</strong> stornieren.
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCancelDialog(null)}>
                Abbrechen
              </Button>
              <Button
                onClick={() => handleCancel(cancelDialog)}
                disabled={actionLoading}
                variant="destructive"
              >
                {actionLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                <Ban className="h-4 w-4 mr-2" />
                Stornieren
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </Layout>
  );
}
