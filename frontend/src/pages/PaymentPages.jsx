import React, { useState, useEffect } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { Card, CardContent } from "../components/ui/card";
import { Button } from "../components/ui/button";
import {
  CheckCircle,
  XCircle,
  Loader2,
  Home,
  Calendar,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get("session_id");
  const [status, setStatus] = useState("checking");
  const [paymentInfo, setPaymentInfo] = useState(null);
  const [pollCount, setPollCount] = useState(0);

  useEffect(() => {
    if (sessionId) {
      pollPaymentStatus();
    } else {
      setStatus("error");
    }
  }, [sessionId]);

  const pollPaymentStatus = async () => {
    const maxAttempts = 10;
    const pollInterval = 2000;

    if (pollCount >= maxAttempts) {
      setStatus("timeout");
      return;
    }

    try {
      const response = await axios.get(`${BACKEND_URL}/api/payments/checkout/status/${sessionId}`);
      setPaymentInfo(response.data);

      if (response.data.payment_status === "paid") {
        setStatus("success");
        return;
      } else if (response.data.status === "expired" || response.data.payment_status === "failed") {
        setStatus("failed");
        return;
      }

      // Continue polling
      setPollCount((prev) => prev + 1);
      setTimeout(pollPaymentStatus, pollInterval);
    } catch (error) {
      console.error("Error checking payment status:", error);
      setStatus("error");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="max-w-md w-full">
        <CardContent className="pt-6">
          {status === "checking" && (
            <div className="text-center">
              <Loader2 className="h-16 w-16 animate-spin text-primary mx-auto mb-4" />
              <h2 className="font-serif text-2xl font-medium text-primary mb-2">
                Zahlung wird überprüft...
              </h2>
              <p className="text-muted-foreground">
                Bitte warten Sie einen Moment
              </p>
            </div>
          )}

          {status === "success" && (
            <div className="text-center">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-primary mb-2">
                Zahlung erfolgreich!
              </h2>
              <p className="text-muted-foreground mb-6">
                Vielen Dank für Ihre Zahlung. Ihre Buchung ist nun bestätigt.
              </p>
              
              {paymentInfo && (
                <div className="bg-muted rounded-lg p-4 mb-6 text-left">
                  <div className="flex justify-between mb-2">
                    <span className="text-muted-foreground">Betrag</span>
                    <span className="font-bold text-primary">
                      {paymentInfo.amount?.toFixed(2)} {paymentInfo.currency?.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Status</span>
                    <span className="text-green-600 font-medium">Bezahlt</span>
                  </div>
                </div>
              )}

              <div className="flex gap-2 justify-center">
                <Link to="/">
                  <Button variant="outline" className="rounded-full">
                    <Home className="h-4 w-4 mr-2" />
                    Startseite
                  </Button>
                </Link>
                <Link to="/book">
                  <Button className="rounded-full">
                    <Calendar className="h-4 w-4 mr-2" />
                    Weitere Buchung
                  </Button>
                </Link>
              </div>
            </div>
          )}

          {(status === "failed" || status === "error" || status === "timeout") && (
            <div className="text-center">
              <div className="w-20 h-20 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <XCircle className="h-10 w-10 text-red-600" />
              </div>
              <h2 className="font-serif text-2xl font-medium text-primary mb-2">
                Zahlung nicht erfolgreich
              </h2>
              <p className="text-muted-foreground mb-6">
                {status === "timeout" 
                  ? "Die Überprüfung dauert länger als erwartet. Bitte kontaktieren Sie uns."
                  : "Die Zahlung konnte nicht abgeschlossen werden. Bitte versuchen Sie es erneut."
                }
              </p>

              <Link to="/">
                <Button className="rounded-full">
                  <Home className="h-4 w-4 mr-2" />
                  Zur Startseite
                </Button>
              </Link>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export const PaymentCancel = () => {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="max-w-md w-full">
        <CardContent className="pt-6 text-center">
          <div className="w-20 h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <XCircle className="h-10 w-10 text-orange-600" />
          </div>
          <h2 className="font-serif text-2xl font-medium text-primary mb-2">
            Zahlung abgebrochen
          </h2>
          <p className="text-muted-foreground mb-6">
            Sie haben die Zahlung abgebrochen. Ihre Buchung ist noch nicht bestätigt.
          </p>

          <div className="flex gap-2 justify-center">
            <Link to="/">
              <Button variant="outline" className="rounded-full">
                <Home className="h-4 w-4 mr-2" />
                Startseite
              </Button>
            </Link>
            <Link to="/book">
              <Button className="rounded-full">
                <Calendar className="h-4 w-4 mr-2" />
                Erneut versuchen
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default PaymentSuccess;
