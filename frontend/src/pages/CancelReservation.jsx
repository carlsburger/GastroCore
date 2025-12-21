import React, { useState, useEffect } from "react";
import { useParams, useSearchParams, Link } from "react-router-dom";
import axios from "axios";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Loader2, CheckCircle, XCircle, Calendar, Clock, Users } from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

export const CancelReservation = () => {
  const { reservationId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  
  const [status, setStatus] = useState("loading"); // loading, confirm, success, error
  const [reservation, setReservation] = useState(null);
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => {
    // Try to fetch reservation info (public endpoint would be needed, or just show confirm)
    if (!token) {
      setStatus("error");
      setError("Ungültiger Stornierungslink");
      return;
    }
    setStatus("confirm");
  }, [token]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await axios.post(
        `${BACKEND_URL}/api/reservations/${reservationId}/cancel`,
        null,
        { params: { token } }
      );
      setStatus("success");
    } catch (err) {
      setStatus("error");
      setError(
        err.response?.data?.detail || 
        "Stornierung fehlgeschlagen. Bitte kontaktieren Sie uns direkt."
      );
    } finally {
      setCancelling(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-full bg-primary mx-auto flex items-center justify-center mb-4">
            <span className="text-primary-foreground font-serif text-3xl font-bold">C</span>
          </div>
          <h1 className="font-serif text-3xl font-medium text-primary">Carlsburg</h1>
          <p className="text-muted-foreground">Restaurant</p>
        </div>

        <Card className="bg-card shadow-lg">
          <CardContent className="p-6">
            {status === "loading" && (
              <div className="text-center py-8">
                <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
                <p className="mt-4 text-muted-foreground">Laden...</p>
              </div>
            )}

            {status === "confirm" && (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-destructive/10 mx-auto flex items-center justify-center mb-4">
                  <XCircle className="h-8 w-8 text-destructive" />
                </div>
                <h2 className="font-serif text-2xl mb-2">Reservierung stornieren?</h2>
                <p className="text-muted-foreground mb-6">
                  Möchten Sie Ihre Reservierung wirklich stornieren? Diese Aktion kann nicht rückgängig gemacht werden.
                </p>
                
                <div className="flex gap-3 justify-center">
                  <Link to="/">
                    <Button variant="outline" className="rounded-full">
                      Abbrechen
                    </Button>
                  </Link>
                  <Button
                    variant="destructive"
                    className="rounded-full"
                    onClick={handleCancel}
                    disabled={cancelling}
                    data-testid="confirm-cancel-button"
                  >
                    {cancelling ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Wird storniert...
                      </>
                    ) : (
                      "Ja, stornieren"
                    )}
                  </Button>
                </div>
              </div>
            )}

            {status === "success" && (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-green-100 mx-auto flex items-center justify-center mb-4">
                  <CheckCircle className="h-8 w-8 text-green-600" />
                </div>
                <h2 className="font-serif text-2xl mb-2">Stornierung bestätigt</h2>
                <p className="text-muted-foreground mb-6">
                  Ihre Reservierung wurde erfolgreich storniert. Sie erhalten eine Bestätigung per E-Mail.
                </p>
                <p className="text-sm text-muted-foreground">
                  Wir würden uns freuen, Sie ein anderes Mal begrüßen zu dürfen!
                </p>
              </div>
            )}

            {status === "error" && (
              <div className="text-center">
                <div className="w-16 h-16 rounded-full bg-destructive/10 mx-auto flex items-center justify-center mb-4">
                  <XCircle className="h-8 w-8 text-destructive" />
                </div>
                <h2 className="font-serif text-2xl mb-2">Fehler</h2>
                <Alert variant="destructive" className="mb-4">
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
                <p className="text-sm text-muted-foreground">
                  Bei Fragen erreichen Sie uns unter:<br />
                  <a href="mailto:reservierung@carlsburg.de" className="text-primary underline">
                    reservierung@carlsburg.de
                  </a>
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <p className="text-center text-sm text-muted-foreground mt-6">
          © {new Date().getFullYear()} Carlsburg Restaurant
        </p>
      </div>
    </div>
  );
};

export default CancelReservation;
