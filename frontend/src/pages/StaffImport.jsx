import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import axios from "axios";
import { 
  Upload, 
  FileSpreadsheet, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle,
  Download,
  RefreshCw,
  Users,
  UserPlus,
  UserMinus,
  UserCheck,
  Play,
  Info,
  ChevronDown,
  ChevronUp
} from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Switch } from "../components/ui/switch";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "../components/ui/collapsible";

const BACKEND_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL || "";

export default function StaffImport() {
  const [file, setFile] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [executeResult, setExecuteResult] = useState(null);
  
  // Options
  const [strictFullImport, setStrictFullImport] = useState(true);
  const [enableNameFallback, setEnableNameFallback] = useState(false);
  
  // UI State
  const [showPlan, setShowPlan] = useState(false);
  const [showDuplicates, setShowDuplicates] = useState(false);
  const [showWarnings, setShowWarnings] = useState(false);
  
  const token = localStorage.getItem("token");
  
  const onDrop = useCallback((acceptedFiles) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.xlsx')) {
        toast.error("Nur XLSX-Dateien werden unterstützt");
        return;
      }
      setFile(selectedFile);
      setAnalysisResult(null);
      setExecuteResult(null);
    }
  }, []);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
    },
    maxFiles: 1
  });
  
  const handleAnalyze = async () => {
    if (!file) return;
    
    setAnalyzing(true);
    setAnalysisResult(null);
    setExecuteResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await axios.post(
        `${BACKEND_URL}/api/admin/staff/import/analyze?mode=A&strict_full_import=${strictFullImport}&enable_name_fallback=${enableNameFallback}`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        }
      );
      
      setAnalysisResult(response.data);
      toast.success("Analyse abgeschlossen");
      
    } catch (error) {
      console.error("Analyze error:", error);
      toast.error(error.response?.data?.detail || "Analyse fehlgeschlagen");
    } finally {
      setAnalyzing(false);
    }
  };
  
  const handleExecute = async () => {
    if (!file || !analysisResult) return;
    
    // Confirm before execution
    const totalChanges = analysisResult.counts.insert + analysisResult.counts.update + analysisResult.counts.deactivate;
    if (totalChanges === 0) {
      toast.info("Keine Änderungen zu importieren");
      return;
    }
    
    if (!window.confirm(`Import ausführen?\n\n• ${analysisResult.counts.insert} neue Mitarbeiter\n• ${analysisResult.counts.update} Aktualisierungen\n• ${analysisResult.counts.deactivate} Deaktivierungen\n\nDiese Aktion kann nicht rückgängig gemacht werden.`)) {
      return;
    }
    
    setExecuting(true);
    setExecuteResult(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      // Generate idempotency key
      const idempotencyKey = `import_${analysisResult.file_hash}_${Date.now()}`;
      
      const response = await axios.post(
        `${BACKEND_URL}/api/admin/staff/import/execute?mode=A&strict_full_import=${strictFullImport}&enable_name_fallback=${enableNameFallback}`,
        formData,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data',
            'Idempotency-Key': idempotencyKey
          }
        }
      );
      
      setExecuteResult(response.data);
      toast.success("Import erfolgreich abgeschlossen");
      
    } catch (error) {
      console.error("Execute error:", error);
      toast.error(error.response?.data?.detail || "Import fehlgeschlagen");
    } finally {
      setExecuting(false);
    }
  };
  
  const handleReset = () => {
    setFile(null);
    setAnalysisResult(null);
    setExecuteResult(null);
  };
  
  const downloadReport = () => {
    const data = executeResult || analysisResult;
    if (!data) return;
    
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `staff_import_${data.run_id || 'analysis'}_${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };
  
  const getActionIcon = (action) => {
    switch (action) {
      case 'insert': return <UserPlus className="h-4 w-4 text-green-500" />;
      case 'update': return <RefreshCw className="h-4 w-4 text-blue-500" />;
      case 'deactivate': return <UserMinus className="h-4 w-4 text-orange-500" />;
      case 'unchanged': return <UserCheck className="h-4 w-4 text-gray-400" />;
      case 'skip': return <XCircle className="h-4 w-4 text-red-500" />;
      default: return <Users className="h-4 w-4" />;
    }
  };
  
  const getActionBadge = (action) => {
    const colors = {
      insert: "bg-green-100 text-green-700",
      update: "bg-blue-100 text-blue-700",
      deactivate: "bg-orange-100 text-orange-700",
      unchanged: "bg-gray-100 text-gray-600",
      skip: "bg-red-100 text-red-700"
    };
    const labels = {
      insert: "Neu",
      update: "Update",
      deactivate: "Deaktivieren",
      unchanged: "Unverändert",
      skip: "Übersprungen"
    };
    return (
      <Badge className={colors[action] || "bg-gray-100"}>
        {labels[action] || action}
      </Badge>
    );
  };
  
  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Mitarbeiter Import</h1>
        <p className="text-gray-500 mt-1">
          Importieren Sie Mitarbeiterdaten aus einer Excel-Datei (XLSX)
        </p>
      </div>
      
      {/* Info Banner */}
      <Alert className="mb-6 border-blue-200 bg-blue-50">
        <Info className="h-4 w-4 text-blue-600" />
        <AlertTitle className="text-blue-800">Mode A – Strict Full Import</AlertTitle>
        <AlertDescription className="text-blue-700">
          <ul className="list-disc ml-4 mt-2 space-y-1 text-sm">
            <li>Neue Mitarbeiter werden angelegt</li>
            <li>Bestehende Mitarbeiter werden aktualisiert (Match über Email → Telefon → Personalnummer)</li>
            <li>Mitarbeiter die NICHT in der Datei sind, werden deaktiviert (active=false)</li>
            <li>Keine Löschungen – Daten bleiben erhalten</li>
          </ul>
        </AlertDescription>
      </Alert>
      
      <div className="grid gap-6">
        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileSpreadsheet className="h-5 w-5" />
              Datei hochladen
            </CardTitle>
            <CardDescription>
              Wählen Sie eine XLSX-Datei mit Mitarbeiterdaten aus
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
                ${isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'}
                ${file ? 'border-green-500 bg-green-50' : ''}`}
            >
              <input {...getInputProps()} />
              {file ? (
                <div className="flex flex-col items-center gap-2">
                  <CheckCircle2 className="h-12 w-12 text-green-500" />
                  <p className="font-medium text-green-700">{file.name}</p>
                  <p className="text-sm text-gray-500">
                    {(file.size / 1024).toFixed(1)} KB
                  </p>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={(e) => { e.stopPropagation(); handleReset(); }}
                  >
                    Andere Datei wählen
                  </Button>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Upload className="h-12 w-12 text-gray-400" />
                  <p className="font-medium">
                    {isDragActive ? 'Datei hier ablegen...' : 'Datei hierher ziehen oder klicken'}
                  </p>
                  <p className="text-sm text-gray-500">Nur XLSX-Dateien</p>
                </div>
              )}
            </div>
            
            {/* Import Options */}
            <div className="mt-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="strict-mode" className="font-medium">Strict Full Import (Mode A)</Label>
                  <p className="text-sm text-gray-500">
                    Deaktiviert Mitarbeiter die nicht in der Datei sind
                  </p>
                </div>
                <Switch 
                  id="strict-mode" 
                  checked={strictFullImport} 
                  onCheckedChange={setStrictFullImport}
                />
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="name-fallback" className="font-medium">Name+Geburtsdatum Fallback</Label>
                  <p className="text-sm text-gray-500">
                    Matching auch über Vor-/Nachname + Geburtsdatum
                  </p>
                </div>
                <Switch 
                  id="name-fallback" 
                  checked={enableNameFallback} 
                  onCheckedChange={setEnableNameFallback}
                />
              </div>
            </div>
            
            {/* Action Buttons */}
            <div className="mt-6 flex gap-3">
              <Button 
                onClick={handleAnalyze} 
                disabled={!file || analyzing || executing}
                className="flex-1"
              >
                {analyzing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Analysiere...
                  </>
                ) : (
                  <>
                    <FileSpreadsheet className="h-4 w-4 mr-2" />
                    Analysieren
                  </>
                )}
              </Button>
              
              <Button 
                onClick={handleExecute}
                disabled={!analysisResult || executing || executeResult}
                variant={analysisResult ? "default" : "outline"}
                className={analysisResult && !executeResult ? "flex-1 bg-green-600 hover:bg-green-700" : "flex-1"}
              >
                {executing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Importiere...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Import ausführen
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Results Card */}
        {(analysisResult || executeResult) && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  {executeResult ? (
                    <>
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                      Import abgeschlossen
                    </>
                  ) : (
                    <>
                      <Info className="h-5 w-5 text-blue-500" />
                      Analyse-Ergebnis (Dry-Run)
                    </>
                  )}
                </span>
                <Button variant="outline" size="sm" onClick={downloadReport}>
                  <Download className="h-4 w-4 mr-2" />
                  JSON Report
                </Button>
              </CardTitle>
              {executeResult && (
                <CardDescription>
                  Run ID: {executeResult.run_id}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              {/* Counts Summary */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                <div className="bg-green-50 rounded-lg p-4 text-center">
                  <UserPlus className="h-6 w-6 text-green-600 mx-auto mb-1" />
                  <div className="text-2xl font-bold text-green-700">
                    {(executeResult || analysisResult).counts.insert}
                  </div>
                  <div className="text-sm text-green-600">Neu</div>
                </div>
                
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <RefreshCw className="h-6 w-6 text-blue-600 mx-auto mb-1" />
                  <div className="text-2xl font-bold text-blue-700">
                    {(executeResult || analysisResult).counts.update}
                  </div>
                  <div className="text-sm text-blue-600">Updates</div>
                </div>
                
                <div className="bg-orange-50 rounded-lg p-4 text-center">
                  <UserMinus className="h-6 w-6 text-orange-600 mx-auto mb-1" />
                  <div className="text-2xl font-bold text-orange-700">
                    {(executeResult || analysisResult).counts.deactivate}
                  </div>
                  <div className="text-sm text-orange-600">Deaktiviert</div>
                </div>
                
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <UserCheck className="h-6 w-6 text-gray-500 mx-auto mb-1" />
                  <div className="text-2xl font-bold text-gray-600">
                    {(executeResult || analysisResult).counts.unchanged}
                  </div>
                  <div className="text-sm text-gray-500">Unverändert</div>
                </div>
                
                <div className="bg-red-50 rounded-lg p-4 text-center">
                  <XCircle className="h-6 w-6 text-red-500 mx-auto mb-1" />
                  <div className="text-2xl font-bold text-red-600">
                    {(executeResult || analysisResult).counts.skipped || 0}
                  </div>
                  <div className="text-sm text-red-500">Übersprungen</div>
                </div>
              </div>
              
              {/* Duplicates Section */}
              {analysisResult?.duplicates?.length > 0 && (
                <Collapsible open={showDuplicates} onOpenChange={setShowDuplicates}>
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full mb-2 justify-between">
                      <span className="flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-500" />
                        {analysisResult.duplicates.length} Duplikat-Kandidaten
                      </span>
                      {showDuplicates ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="bg-amber-50 rounded-lg p-4 mb-4">
                      <div className="space-y-2">
                        {analysisResult.duplicates.map((dup, idx) => (
                          <div key={idx} className="bg-white rounded p-3 border border-amber-200">
                            <div className="flex items-center gap-2">
                              <Badge variant="outline" className="text-amber-700">
                                Zeile {dup.row}
                              </Badge>
                              <span className="text-sm text-amber-800">{dup.reason}</span>
                            </div>
                            {dup.candidates?.length > 0 && (
                              <div className="text-xs text-gray-500 mt-1">
                                Kandidaten: {dup.candidates.join(', ')}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}
              
              {/* Warnings Section */}
              {analysisResult?.warnings?.length > 0 && (
                <Collapsible open={showWarnings} onOpenChange={setShowWarnings}>
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full mb-2 justify-between">
                      <span className="flex items-center gap-2">
                        <Info className="h-4 w-4 text-blue-500" />
                        {analysisResult.warnings.length} Hinweise
                      </span>
                      {showWarnings ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="bg-blue-50 rounded-lg p-4 mb-4">
                      <div className="space-y-2">
                        {analysisResult.warnings.slice(0, 20).map((warn, idx) => (
                          <div key={idx} className="text-sm flex items-center gap-2">
                            <Badge variant="outline" className="text-blue-700">
                              Zeile {warn.row}
                            </Badge>
                            <span className="text-blue-800">
                              {warn.field}: {warn.issue}
                            </span>
                          </div>
                        ))}
                        {analysisResult.warnings.length > 20 && (
                          <div className="text-sm text-gray-500">
                            ... und {analysisResult.warnings.length - 20} weitere
                          </div>
                        )}
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}
              
              {/* Plan Section */}
              {analysisResult?.plan?.length > 0 && (
                <Collapsible open={showPlan} onOpenChange={setShowPlan}>
                  <CollapsibleTrigger asChild>
                    <Button variant="outline" className="w-full justify-between">
                      <span className="flex items-center gap-2">
                        <Users className="h-4 w-4" />
                        Detaillierter Plan ({analysisResult.plan.length} Einträge)
                      </span>
                      {showPlan ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="mt-4 space-y-2 max-h-96 overflow-y-auto">
                      {analysisResult.plan.map((item, idx) => (
                        <div 
                          key={idx} 
                          className="bg-gray-50 rounded-lg p-3 border flex items-start gap-3"
                        >
                          {getActionIcon(item.action)}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              {item.row > 0 && (
                                <Badge variant="outline" className="text-xs">
                                  Zeile {item.row}
                                </Badge>
                              )}
                              {getActionBadge(item.action)}
                              {item.match_by !== 'none' && (
                                <Badge variant="secondary" className="text-xs">
                                  Match: {item.match_by}
                                </Badge>
                              )}
                            </div>
                            {item.excel_data && (
                              <div className="text-sm mt-1">
                                <span className="font-medium">
                                  {item.excel_data.first_name} {item.excel_data.last_name}
                                </span>
                                {item.excel_data.email && (
                                  <span className="text-gray-500 ml-2">{item.excel_data.email}</span>
                                )}
                              </div>
                            )}
                            {item.reason && (
                              <div className="text-sm text-gray-500 mt-1">{item.reason}</div>
                            )}
                            {item.changes && Object.keys(item.changes).length > 0 && (
                              <div className="text-xs text-gray-500 mt-1">
                                Änderungen: {Object.keys(item.changes).join(', ')}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}
              
              {/* Execute Result Errors */}
              {executeResult?.errors?.length > 0 && (
                <Alert className="mt-4 border-red-200 bg-red-50">
                  <XCircle className="h-4 w-4 text-red-600" />
                  <AlertTitle className="text-red-800">Fehler beim Import</AlertTitle>
                  <AlertDescription>
                    <ul className="list-disc ml-4 mt-2 text-sm text-red-700">
                      {executeResult.errors.map((err, idx) => (
                        <li key={idx}>{err}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>
        )}
        
        {/* Template Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Spaltenformat</CardTitle>
            <CardDescription>
              Erwartete Spalten in der Excel-Datei
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div>
                <h4 className="font-medium text-red-700 mb-2">Pflichtfelder</h4>
                <ul className="space-y-1 text-gray-600">
                  <li>• Vorname</li>
                  <li>• Nachname</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-amber-700 mb-2">Identifikatoren (min. 1)</h4>
                <ul className="space-y-1 text-gray-600">
                  <li>• Email</li>
                  <li>• Telefon</li>
                  <li>• Personalnummer</li>
                </ul>
              </div>
              <div>
                <h4 className="font-medium text-gray-700 mb-2">Optionale Felder</h4>
                <ul className="space-y-1 text-gray-600">
                  <li>• Rollen (kommasepariert)</li>
                  <li>• Anstellungsart</li>
                  <li>• Wochenstunden</li>
                  <li>• Eintrittsdatum</li>
                  <li>• Geburtsdatum</li>
                  <li>• Adresse (Straße, PLZ, Ort)</li>
                  <li>• Steuer_ID, SV_Nummer</li>
                  <li>• IBAN, Krankenkasse</li>
                  <li>• Notfallkontakt</li>
                </ul>
              </div>
            </div>
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <h4 className="font-medium text-gray-700 mb-2">Gültige Rollen</h4>
              <div className="flex flex-wrap gap-2">
                {['service', 'bar', 'kitchen', 'reinigung', 'eismacher', 'kuechenhilfe', 'aushilfe', 'schichtleiter'].map(role => (
                  <Badge key={role} variant="secondary">{role}</Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
