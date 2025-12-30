import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { BookOpen, TrendingUp, Users, Calendar, Clock } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

/**
 * Reservierung Auswertung - Read-only Analytics
 * Navigation Model A: Auswertungen → Reservierung
 */
export default function AnalyticsReservations() {
  const navigate = useNavigate();
  
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Reservierung – Auswertung</h1>
        <p className="text-gray-500 mt-1">
          Analyse von Auslastung, Gästezahlen und Trends
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Placeholder Cards - Werden mit echten KPIs befüllt */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-600" />
              Gäste heute
            </CardTitle>
            <CardDescription>Reservierte Plätze</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">–</div>
            <p className="text-sm text-gray-500 mt-1">
              Daten aus Reservierungen
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              Auslastung
            </CardTitle>
            <CardDescription>Kapazitätsnutzung</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">–%</div>
            <p className="text-sm text-gray-500 mt-1">
              Basierend auf Tischkapazität
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Calendar className="h-5 w-5 text-amber-600" />
              Reservierungen
            </CardTitle>
            <CardDescription>Diesen Monat</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">–</div>
            <p className="text-sm text-gray-500 mt-1">
              Anzahl Buchungen
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="mt-8 p-6 bg-amber-50 rounded-lg border border-amber-200">
        <div className="flex items-start gap-3">
          <Clock className="h-5 w-5 text-amber-600 mt-0.5" />
          <div>
            <h3 className="font-medium text-amber-800">Auswertung in Entwicklung</h3>
            <p className="text-sm text-amber-700 mt-1">
              Diese Seite wird mit detaillierten Reservierungs-KPIs erweitert.
              Aktuell finden Sie die Übersicht im Dashboard.
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-3"
              onClick={() => navigate("/dashboard")}
            >
              Zum Dashboard
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
