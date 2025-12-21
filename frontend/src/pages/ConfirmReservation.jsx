import React, { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import axios from "axios";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Badge } from "../components/ui/badge";
import {
  Calendar,
  Clock,
  Users,
  MapPin,
  CheckCircle,
  Loader2,
  AlertCircle,
  PartyPopper,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const ConfirmReservation = () => {
  const { reservationId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [reservation, setReservation] = useState(null);
  const [error, setError] = useState("");
  const [confirmed, setConfirmed] = useState(false);

  useEffect(() => {
    fetchReservation();
  }, [reservationId, token]);

  const fetchReservation = async () => {
    try {
      const response = await axios.get(
        `${BACKEND_URL}/api/public/reservations/${reservationId}/confirm-info?token=${token}`
      );
      setReservation(response.data);
      if (response.data.guest_confirmed) {
        setConfirmed(true);
      }
    } catch (err) {
      setError(err.response?.data?.detail || "Reservierung nicht gefunden oder Link ungültig");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    setConfirming(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/public/reservations/${reservationId}/confirm?token=${token}`
      );
      setConfirmed(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Bestätigung fehlgeschlagen");
    } finally {
      setConfirming(false);
    }
  };

  // Format date nicely
  const formatDate = (dateStr) => {
    if (!dateStr) return "";
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString("de-DE", {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="w-16 h-16 rounded-full bg-red-100 mx-auto flex items-center justify-center mb-4">
                <AlertCircle className="h-8 w-8 text-red-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-primary mb-2">
                Fehler
              </h2>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (confirmed) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="w-20 h-20 rounded-full bg-green-100 mx-auto flex items-center justify-center mb-4">
                <PartyPopper className="h-10 w-10 text-green-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-primary mb-2">
                Reservierung bestätigt!
              </h2>
              <p className="text-muted-foreground mb-6">
                Vielen Dank für Ihre Bestätigung. Wir freuen uns auf Ihren Besuch!
              </p>
              
              <div className="bg-muted rounded-lg p-4 text-left space-y-3">
                <div className="flex items-center gap-3">
                  <Calendar className="h-5 w-5 text-primary" />
                  <span className="font-medium">{formatDate(reservation?.date)}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Clock className="h-5 w-5 text-primary" />
                  <span className="font-medium">{reservation?.time} Uhr</span>
                </div>
                <div className="flex items-center gap-3">
                  <Users className="h-5 w-5 text-primary" />
                  <span className="font-medium">{reservation?.party_size} Personen</span>
                </div>
                {reservation?.area_name && (
                  <div className="flex items-center gap-3">
                    <MapPin className="h-5 w-5 text-primary" />
                    <span className="font-medium">{reservation.area_name}</span>
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="max-w-md w-full">
        <CardHeader className="text-center">
          <div className="w-16 h-16 rounded-full bg-primary mx-auto flex items-center justify-center mb-4">
            <span className="text-primary-foreground font-serif text-2xl font-bold">G</span>
          </div>
          <CardTitle className="font-serif text-2xl">Reservierung bestätigen</CardTitle>
          <CardDescription>
            Bitte bestätigen Sie Ihre Reservierung
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="bg-muted rounded-lg p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Gast</span>
              <span className="font-medium">{reservation?.guest_name}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Datum</span>
              <span className="font-medium">{formatDate(reservation?.date)}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Uhrzeit</span>
              <span className="font-medium">{reservation?.time} Uhr</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Personen</span>
              <span className="font-medium">{reservation?.party_size}</span>
            </div>
            {reservation?.area_name && (
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">Bereich</span>
                <span className="font-medium">{reservation.area_name}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-muted-foreground">Status</span>
              <Badge>{reservation?.status === "neu" ? "Neu" : "Bestätigt"}</Badge>
            </div>
          </div>

          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Mit der Bestätigung verpflichten Sie sich, zur angegebenen Zeit zu erscheinen
              oder rechtzeitig abzusagen.
            </AlertDescription>
          </Alert>

          <Button
            className="w-full h-12 text-lg rounded-full"
            onClick={handleConfirm}
            disabled={confirming}
          >
            {confirming ? (
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
            ) : (
              <CheckCircle className="h-5 w-5 mr-2" />
            )}
            Reservierung bestätigen
          </Button>
        </CardContent>
      </Card>
    </div>
  );
};

export default ConfirmReservation;
