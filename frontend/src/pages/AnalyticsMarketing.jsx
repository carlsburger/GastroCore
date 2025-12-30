import React from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Megaphone, Mail, Users, TrendingUp, Calendar } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

/**
 * Marketing Auswertung - Read-only Analytics
 * Navigation Model A: Auswertungen → Marketing
 */
export default function AnalyticsMarketing() {
  const navigate = useNavigate();
  
  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Marketing – Auswertung</h1>
        <p className="text-gray-500 mt-1">
          Analyse von Kampagnen, Reichweite und Opt-ins
        </p>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* Placeholder Cards - Werden mit echten KPIs befüllt */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-600" />
              Marketing Opt-ins
            </CardTitle>
            <CardDescription>Aktive Abonnenten</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-emerald-600">–</div>
            <p className="text-sm text-gray-500 mt-1">
              Mit Einwilligung
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <Mail className="h-5 w-5 text-blue-600" />
              Nachrichten
            </CardTitle>
            <CardDescription>Dieser Monat</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-blue-600">–</div>
            <p className="text-sm text-gray-500 mt-1">
              Versendete Kampagnen
            </p>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-amber-600" />
              Öffnungsrate
            </CardTitle>
            <CardDescription>Durchschnitt</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-amber-600">–%</div>
            <p className="text-sm text-gray-500 mt-1">
              E-Mail Engagement
            </p>
          </CardContent>
        </Card>
      </div>
      
      <div className="mt-8 p-6 bg-violet-50 rounded-lg border border-violet-200">
        <div className="flex items-start gap-3">
          <Megaphone className="h-5 w-5 text-violet-600 mt-0.5" />
          <div>
            <h3 className="font-medium text-violet-800">Marketing-Center</h3>
            <p className="text-sm text-violet-700 mt-1">
              Kampagnen erstellen und verwalten Sie im Marketing-Center.
              Hier sehen Sie die aggregierten Kennzahlen.
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-3"
              onClick={() => navigate("/marketing")}
            >
              Marketing-Center öffnen
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
