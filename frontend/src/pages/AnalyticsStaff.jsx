import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { UsersRound, Clock, TrendingUp, Calendar } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

/**
 * Mitarbeiter Auswertung - Read-only Analytics
 * Navigation Model A: Auswertungen → Mitarbeiter
 */
export default function AnalyticsStaff() {
  const navigate = useNavigate();
  
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mitarbeiter – Auswertung</h1>
        <p className="text-gray-500 mt-1">
          Analyse von Stunden, Produktivität und Personalkosten
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Placeholder Cards - Werden mit echten KPIs befüllt */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Clock className="h-5 w-5 text-blue-600" />
              Arbeitsstunden
            </CardTitle>
            <CardDescription>Dieser Monat</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">– h</div>
            <p className="text-sm text-gray-500 mt-1">
              Summe aller Mitarbeiter
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-emerald-600" />
              Produktivität
            </CardTitle>
            <CardDescription>Umsatz pro Stunde</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">– €</div>
            <p className="text-sm text-gray-500 mt-1">
              Durchschnitt
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <UsersRound className="h-5 w-5 text-violet-600" />
              Aktive Mitarbeiter
            </CardTitle>
            <CardDescription>Im Dienst</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-violet-600">–</div>
            <p className="text-sm text-gray-500 mt-1">
              Diese Woche eingeplant
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="mt-8 p-6 bg-blue-50 rounded-lg border border-blue-200">
        <div className="flex items-start gap-3">
          <Calendar className="h-5 w-5 text-blue-600 mt-0.5" />
          <div>
            <h3 className="font-medium text-blue-800">Auswertung in Entwicklung</h3>
            <p className="text-sm text-blue-700 mt-1">
              Diese Seite wird mit detaillierten Personal-KPIs erweitert.
              Stundenabrechnungen finden Sie im Steuerbüro-Export.
            </p>
            <div className="flex gap-2 mt-3">
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => navigate("/taxoffice")}
              >
                Steuerbüro-Export
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => navigate("/shifts-admin")}
              >
                Dienstplan
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
