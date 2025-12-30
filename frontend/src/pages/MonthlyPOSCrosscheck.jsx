import React, { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { 
  RefreshCw, 
  CheckCircle2, 
  AlertTriangle, 
  Lock,
  FileCheck,
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  Euro
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL;

// Generate last 12 months for selection
const generateMonthOptions = () => {
  const options = [];
  const now = new Date();
  for (let i = 0; i < 12; i++) {
    const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const value = date.toISOString().slice(0, 7); // YYYY-MM
    const label = date.toLocaleDateString("de-DE", { month: "long", year: "numeric" });
    options.push({ value, label });
  }
  return options;
};

export default function MonthlyPOSCrosscheck() {
  const { token, user } = useAuth();
  const [selectedMonth, setSelectedMonth] = useState(() => {
    const now = new Date();
    return now.toISOString().slice(0, 7);
  });
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [monthStatus, setMonthStatus] = useState(null);

  const monthOptions = generateMonthOptions();

  const fetchMonthStatus = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/pos/monthly-status?month=${selectedMonth}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setMonthStatus(response.data);
    } catch (error) {
      console.error("Error fetching month status:", error);
      toast.error("Fehler beim Laden des Monatsstatus");
    } finally {
      setLoading(false);
    }
  }, [token, selectedMonth]);

  useEffect(() => {
    fetchMonthStatus();
  }, [fetchMonthStatus]);

  const handleConfirmMonth = async () => {
    if (!window.confirm(
      `Monat ${selectedMonth} wirklich bestätigen?\n\n` +
      `Dies sperrt die POS-Daten für diesen Monat.\n` +
      `Die Aktion kann nicht rückgängig gemacht werden.`
    )) {
      return;
    }

    setConfirming(true);
    try {
      const response = await axios.post(
        `${BACKEND_URL}/api/pos/monthly/${selectedMonth}/confirm`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      toast.success(`Monat ${selectedMonth} wurde bestätigt`);
      setMonthStatus(prev => ({
        ...prev,
        confirmed: true,
        locked: true,
        confirmed_by: response.data.confirmed_by,
        confirmed_at: response.data.confirmed_at
      }));
    } catch (error) {
      toast.error("Bestätigung fehlgeschlagen: " + (error.response?.data?.detail || error.message));
    } finally {
      setConfirming(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return "—";
    return new Intl.NumberFormat("de-DE", {
      style: "currency",
      currency: "EUR"
    }).format(value);
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return "—";
    const prefix = value > 0 ? "+" : "";
    return `${prefix}${value.toFixed(1)}%`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    return new Date(dateStr).toLocaleString("de-DE", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  const crosscheck = monthStatus?.crosscheck || {};

  const getCrosscheckStatus = () => {
    if (monthStatus?.confirmed) {
      return { 
        badge: <Badge className="bg-green-100 text-green-800"><Lock className="h-3 w-3 mr-1" />Bestätigt</Badge>,
        color: "green" 
      };
    }
    if (!crosscheck.has_monthly_pdf) {
      return { 
        badge: <Badge variant="secondary"><Minus className="h-3 w-3 mr-1" />Kein Monatsbericht</Badge>,
        color: "gray"
      };
    }
    if (crosscheck.warning) {
      return { 
        badge: <Badge variant="destructive"><AlertTriangle className="h-3 w-3 mr-1" />Abweichung</Badge>,
        color: "yellow"
      };
    }
    return { 
      badge: <Badge className="bg-green-100 text-green-800"><CheckCircle2 className="h-3 w-3 mr-1" />OK</Badge>,
      color: "green"
    };
  };

  const getDiffIcon = (value) => {
    if (value === null || value === undefined) return <Minus className="h-4 w-4 text-gray-400" />;
    if (value > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
    if (value < 0) return <TrendingDown className="h-4 w-4 text-red-500" />;
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  const status = getCrosscheckStatus();
  const isAdmin = user?.role === "admin";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-serif font-bold text-[#005500]">Monatsabschluss POS</h1>
          <p className="text-[#005500]/70">Crosscheck & Bestätigung der POS-Umsatzdaten</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={selectedMonth} onValueChange={setSelectedMonth}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Monat wählen" />
            </SelectTrigger>
            <SelectContent>
              {monthOptions.map(opt => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button 
            variant="outline" 
            size="icon" 
            onClick={fetchMonthStatus}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="h-8 w-8 animate-spin text-[#005500]" />
        </div>
      ) : (
        <>
          {/* Status Overview */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                {status.badge}
                {monthStatus?.confirmed && (
                  <div className="mt-2 text-xs text-muted-foreground">
                    <p>Bestätigt von: {monthStatus.confirmed_by}</p>
                    <p>Am: {formatDate(monthStatus.confirmed_at)}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <FileCheck className="h-4 w-4" />
                  Tagesberichte
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{crosscheck.daily_count || 0}</div>
                <p className="text-xs text-muted-foreground">
                  Tage mit POS-Daten
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium flex items-center gap-2">
                  <Euro className="h-4 w-4" />
                  Monatsbericht
                </CardTitle>
              </CardHeader>
              <CardContent>
                {crosscheck.has_monthly_pdf ? (
                  <Badge className="bg-green-100 text-green-800">Vorhanden</Badge>
                ) : (
                  <Badge variant="secondary">Nicht vorhanden</Badge>
                )}
                {crosscheck.monthly_pdf_file && (
                  <p className="text-xs text-muted-foreground mt-1 truncate" title={crosscheck.monthly_pdf_file}>
                    {crosscheck.monthly_pdf_file}
                  </p>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Crosscheck Details */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5" />
                Crosscheck: Tagesdaten vs. Monatsbericht
              </CardTitle>
              <CardDescription>
                Vergleich der summierten Tagesumsätze mit dem Monatsbericht (NETTO)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left py-3 px-4 font-medium">Kennzahl</th>
                      <th className="text-right py-3 px-4 font-medium">Tagesdaten Σ</th>
                      <th className="text-right py-3 px-4 font-medium">Monatsbericht</th>
                      <th className="text-right py-3 px-4 font-medium">Differenz</th>
                      <th className="text-right py-3 px-4 font-medium">%</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4 font-medium">Netto Gesamt</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.daily_sum_net_total)}</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.monthly_pdf_net_total)}</td>
                      <td className="text-right py-3 px-4 flex items-center justify-end gap-1">
                        {getDiffIcon(crosscheck.diff_abs_net_total)}
                        {formatCurrency(crosscheck.diff_abs_net_total)}
                      </td>
                      <td className={`text-right py-3 px-4 ${
                        crosscheck.diff_pct_net_total && Math.abs(crosscheck.diff_pct_net_total) > 1 
                          ? 'text-red-600 font-medium' 
                          : ''
                      }`}>
                        {formatPercent(crosscheck.diff_pct_net_total)}
                      </td>
                    </tr>
                    <tr className="border-b hover:bg-muted/50">
                      <td className="py-3 px-4">Speisen (Food)</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.daily_sum_food_net)}</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.monthly_pdf_food_net)}</td>
                      <td className="text-right py-3 px-4 flex items-center justify-end gap-1">
                        {getDiffIcon(crosscheck.diff_abs_food_net)}
                        {formatCurrency(crosscheck.diff_abs_food_net)}
                      </td>
                      <td className="text-right py-3 px-4">{formatPercent(crosscheck.diff_pct_food_net)}</td>
                    </tr>
                    <tr className="hover:bg-muted/50">
                      <td className="py-3 px-4">Getränke (Beverage)</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.daily_sum_beverage_net)}</td>
                      <td className="text-right py-3 px-4">{formatCurrency(crosscheck.monthly_pdf_beverage_net)}</td>
                      <td className="text-right py-3 px-4 flex items-center justify-end gap-1">
                        {getDiffIcon(crosscheck.diff_abs_beverage_net)}
                        {formatCurrency(crosscheck.diff_abs_beverage_net)}
                      </td>
                      <td className="text-right py-3 px-4">{formatPercent(crosscheck.diff_pct_beverage_net)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Warnings */}
              {crosscheck.warning && crosscheck.warning_reasons?.length > 0 && (
                <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-center gap-2 text-yellow-800 font-medium mb-2">
                    <AlertTriangle className="h-4 w-4" />
                    Abweichungen erkannt
                  </div>
                  <ul className="text-sm text-yellow-700 list-disc list-inside">
                    {crosscheck.warning_reasons.map((reason, idx) => (
                      <li key={idx}>{reason}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Info when no monthly PDF */}
              {!crosscheck.has_monthly_pdf && (
                <div className="mt-4 bg-gray-50 border border-gray-200 rounded-lg p-4">
                  <p className="text-sm text-gray-600">
                    <strong>Hinweis:</strong> Für diesen Monat liegt kein Monatsbericht (PDF) vor. 
                    Der Crosscheck basiert nur auf den vorhandenen Tagesdaten.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Confirm Action */}
          {isAdmin && !monthStatus?.confirmed && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Lock className="h-5 w-5" />
                  Monat bestätigen
                </CardTitle>
                <CardDescription>
                  Sperrt die POS-Daten für {selectedMonth} und verhindert nachträgliche Änderungen
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-4">
                  <Button
                    className="bg-[#005500] hover:bg-[#004400]"
                    onClick={handleConfirmMonth}
                    disabled={confirming || !crosscheck.has_daily_data}
                  >
                    {confirming ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4 mr-2" />
                    )}
                    Monat {selectedMonth} bestätigen
                  </Button>
                  
                  {crosscheck.warning && (
                    <span className="text-sm text-yellow-600">
                      ⚠️ Trotz Abweichungen bestätigen?
                    </span>
                  )}
                </div>

                {!crosscheck.has_daily_data && (
                  <p className="text-sm text-muted-foreground mt-2">
                    Keine Tagesdaten vorhanden. Bestätigung nicht möglich.
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* Already Confirmed */}
          {monthStatus?.confirmed && (
            <Card className="border-green-200 bg-green-50">
              <CardContent className="py-6">
                <div className="flex items-center gap-3">
                  <div className="h-10 w-10 rounded-full bg-green-100 flex items-center justify-center">
                    <Lock className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="font-medium text-green-800">Monat bestätigt & gesperrt</p>
                    <p className="text-sm text-green-600">
                      Bestätigt von {monthStatus.confirmed_by} am {formatDate(monthStatus.confirmed_at)}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
