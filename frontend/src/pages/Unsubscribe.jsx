import React, { useState, useEffect } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { CheckCircle, XCircle, Loader2, Mail } from "lucide-react";
import api from "../lib/api";

export default function Unsubscribe() {
  const { customerId } = useParams();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [pageData, setPageData] = useState(null);

  useEffect(() => {
    const checkToken = async () => {
      try {
        const res = await api.get(
          `/api/public/marketing/unsubscribe/confirm?customer_id=${customerId}&token=${token}`
        );
        setPageData(res.data);
        if (!res.data.valid) {
          setError(res.data.message);
        }
      } catch (err) {
        setError("Ungültiger Abmelde-Link");
      } finally {
        setLoading(false);
      }
    };

    if (customerId && token) {
      checkToken();
    } else {
      setError("Ungültiger Link");
      setLoading(false);
    }
  }, [customerId, token]);

  const handleUnsubscribe = async () => {
    setVerifying(true);
    try {
      await api.post(
        `/api/public/marketing/unsubscribe?customer_id=${customerId}&token=${token}`
      );
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || "Fehler bei der Abmeldung");
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFBE0] flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[#002f02]" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFBE0] flex items-center justify-center p-4">
      <Card className="max-w-md w-full border-[#002f02]/20">
        <CardHeader className="text-center">
          <div className="w-16 h-16 rounded-full bg-[#002f02] mx-auto flex items-center justify-center mb-4">
            <Mail className="w-8 h-8 text-[#FFFF00]" />
          </div>
          <CardTitle className="font-serif text-2xl text-[#002f02]">
            Newsletter Abmeldung
          </CardTitle>
        </CardHeader>
        <CardContent className="text-center">
          {error ? (
            <div className="space-y-4">
              <XCircle className="w-12 h-12 text-red-500 mx-auto" />
              <p className="text-red-600">{error}</p>
            </div>
          ) : success ? (
            <div className="space-y-4">
              <CheckCircle className="w-12 h-12 text-green-500 mx-auto" />
              <p className="text-green-600 font-medium">
                Sie wurden erfolgreich vom Newsletter abgemeldet.
              </p>
              <p className="text-sm text-muted-foreground">
                Sie werden keine weiteren Newsletter von uns erhalten.
              </p>
            </div>
          ) : pageData?.already_unsubscribed ? (
            <div className="space-y-4">
              <CheckCircle className="w-12 h-12 text-gray-400 mx-auto" />
              <p className="text-muted-foreground">
                Sie sind bereits vom Newsletter abgemeldet.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-muted-foreground">
                Möchten Sie sich wirklich vom Newsletter abmelden?
              </p>
              {pageData?.email_masked && (
                <p className="text-sm text-muted-foreground">
                  E-Mail: {pageData.email_masked}
                </p>
              )}
              <Button
                onClick={handleUnsubscribe}
                disabled={verifying}
                className="bg-[#002f02] hover:bg-[#003300]"
              >
                {verifying ? (
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                ) : null}
                Vom Newsletter abmelden
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
