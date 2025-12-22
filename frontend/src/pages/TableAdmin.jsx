import React, { useState, useEffect } from "react";
import axios from "axios";
import { toast } from "sonner";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
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
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  Settings,
  Building,
  Trees,
  PartyPopper,
  Link2,
  MapPin,
  Users,
  Check,
  X,
  AlertTriangle,
} from "lucide-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Bereiche
const AREAS = [
  { value: "restaurant", label: "Restaurant", icon: Building },
  { value: "terrasse", label: "Terrasse", icon: Trees },
  { value: "event", label: "Event", icon: PartyPopper },
];

const SUB_AREAS = [
  { value: "saal", label: "Saal" },
  { value: "wintergarten", label: "Wintergarten" },
];

export const TableAdmin = () => {
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  // State
  const [tables, setTables] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedTable, setSelectedTable] = useState(null);
  const [filterArea, setFilterArea] = useState("all");

  // Form State
  const [form, setForm] = useState({
    table_number: "",
    area: "restaurant",
    sub_area: "saal",
    seats_max: 4,
    seats_default: 4,
    combinable: true,
    combinable_with: "",
    fixed: false,
    active: true,
    notes: "",
  });

  // Fetch tables
  const fetchTables = async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${BACKEND_URL}/api/tables`, {
        headers,
        params: { active_only: false }
      });
      setTables(res.data);
    } catch (err) {
      console.error("Fehler beim Laden:", err);
      toast.error("Tische konnten nicht geladen werden");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  // Filter tables
  const filteredTables = tables.filter(t => {
    if (filterArea === "all") return true;
    return t.area === filterArea;
  });

  // Reset form
  const resetForm = () => {
    setForm({
      table_number: "",
      area: "restaurant",
      sub_area: "saal",
      seats_max: 4,
      seats_default: 4,
      combinable: true,
      combinable_with: "",
      fixed: false,
      active: true,
      notes: "",
    });
    setSelectedTable(null);
  };

  // Open edit dialog
  const openEditDialog = (table) => {
    setSelectedTable(table);
    setForm({
      table_number: table.table_number,
      area: table.area,
      sub_area: table.sub_area || "saal",
      seats_max: table.seats_max,
      seats_default: table.seats_default,
      combinable: table.combinable,
      combinable_with: table.combinable_with?.join(", ") || "",
      fixed: table.fixed,
      active: table.active,
      notes: table.notes || "",
    });
    setShowDialog(true);
  };

  // Save table
  const handleSave = async () => {
    if (!form.table_number) {
      toast.error("Tischnummer erforderlich");
      return;
    }

    try {
      const data = {
        table_number: form.table_number,
        area: form.area,
        sub_area: form.area === "restaurant" ? form.sub_area : null,
        seats_max: parseInt(form.seats_max),
        seats_default: parseInt(form.seats_default) || Math.min(4, parseInt(form.seats_max)),
        combinable: form.table_number === "3" ? false : form.combinable,
        combinable_with: form.combinable_with 
          ? form.combinable_with.split(",").map(s => s.trim()).filter(s => s)
          : [],
        fixed: form.fixed,
        active: form.active,
        notes: form.notes || null,
      };

      if (selectedTable) {
        await axios.patch(`${BACKEND_URL}/api/tables/${selectedTable.id}`, data, { headers });
        toast.success("Tisch aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/tables`, data, { headers });
        toast.success("Tisch erstellt");
      }

      setShowDialog(false);
      resetForm();
      fetchTables();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    }
  };

  // Delete table
  const handleDelete = async () => {
    if (!selectedTable) return;

    try {
      await axios.delete(`${BACKEND_URL}/api/tables/${selectedTable.id}`, { headers });
      toast.success("Tisch archiviert");
      setShowDeleteDialog(false);
      setSelectedTable(null);
      fetchTables();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Löschen");
    }
  };

  // Statistiken
  const stats = {
    total: tables.length,
    active: tables.filter(t => t.active).length,
    restaurant: tables.filter(t => t.area === "restaurant").length,
    terrasse: tables.filter(t => t.area === "terrasse").length,
    event: tables.filter(t => t.area === "event").length,
    totalSeats: tables.filter(t => t.active).reduce((sum, t) => sum + (t.seats_max || 0), 0),
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="font-serif text-3xl font-bold text-[#002f02] flex items-center gap-3">
              <Settings className="h-8 w-8" />
              Tisch-Stammdaten
            </h1>
            <p className="text-muted-foreground mt-1">
              Verwaltung aller Tische, Bereiche und Kombinationen
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={fetchTables} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Aktualisieren
            </Button>
            <Button 
              onClick={() => {
                resetForm();
                setShowDialog(true);
              }}
              className="bg-[#002f02] hover:bg-[#003300]"
            >
              <Plus className="h-4 w-4 mr-2" />
              Neuer Tisch
            </Button>
          </div>
        </div>

        {/* Statistiken */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{stats.total}</div>
              <p className="text-xs text-muted-foreground">Gesamt</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-green-600">{stats.active}</div>
              <p className="text-xs text-muted-foreground">Aktiv</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-blue-600">{stats.restaurant}</div>
              <p className="text-xs text-muted-foreground">Restaurant</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-green-600">{stats.terrasse}</div>
              <p className="text-xs text-muted-foreground">Terrasse</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold text-purple-600">{stats.event}</div>
              <p className="text-xs text-muted-foreground">Event</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4">
              <div className="text-2xl font-bold">{stats.totalSeats}</div>
              <p className="text-xs text-muted-foreground">Plätze</p>
            </CardContent>
          </Card>
        </div>

        {/* Hinweise */}
        <Card className="border-orange-200 bg-orange-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2 text-orange-700">
              <AlertTriangle className="h-4 w-4" />
              Wichtige Regeln
            </CardTitle>
          </CardHeader>
          <CardContent className="pt-0 text-sm text-orange-800">
            <ul className="list-disc list-inside space-y-1">
              <li><strong>Saal ≠ Wintergarten:</strong> Tische aus verschiedenen Subbereichen dürfen NICHT kombiniert werden</li>
              <li><strong>Tisch 3:</strong> Sonderfall (oval/Exot) - ist NIE kombinierbar</li>
              <li><strong>Bereichs-Trennung:</strong> Restaurant, Terrasse und Event sind getrennte Bereiche</li>
            </ul>
          </CardContent>
        </Card>

        {/* Filter */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-4">
              <Label>Bereich filtern:</Label>
              <Select value={filterArea} onValueChange={setFilterArea}>
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Bereiche</SelectItem>
                  {AREAS.map((area) => (
                    <SelectItem key={area.value} value={area.value}>
                      {area.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Badge variant="outline" className="ml-auto">
                {filteredTables.length} Tische
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Tisch-Tabelle */}
        <Card>
          <CardContent className="p-0">
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-20">Nr.</TableHead>
                    <TableHead>Bereich</TableHead>
                    <TableHead>Subbereich</TableHead>
                    <TableHead className="text-center">Plätze</TableHead>
                    <TableHead className="text-center">Kombinierbar</TableHead>
                    <TableHead>Kombinierbar mit</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead className="text-right">Aktionen</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8">
                        <RefreshCw className="h-6 w-6 animate-spin mx-auto text-muted-foreground" />
                      </TableCell>
                    </TableRow>
                  ) : filteredTables.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                        Keine Tische gefunden
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredTables
                      .sort((a, b) => {
                        // Sortiere nach Bereich, dann Nummer
                        if (a.area !== b.area) return a.area.localeCompare(b.area);
                        if (a.sub_area !== b.sub_area) return (a.sub_area || "").localeCompare(b.sub_area || "");
                        const numA = parseInt(a.table_number) || 999;
                        const numB = parseInt(b.table_number) || 999;
                        return numA - numB;
                      })
                      .map((table) => (
                        <TableRow 
                          key={table.id}
                          className={!table.active ? "opacity-50" : ""}
                          data-testid={`table-row-${table.table_number}`}
                        >
                          <TableCell className="font-bold text-lg">
                            {table.table_number}
                            {table.table_number === "3" && (
                              <Badge variant="outline" className="ml-2 text-xs">Oval</Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            <Badge variant="secondary">
                              {AREAS.find(a => a.value === table.area)?.label || table.area}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            {table.area === "restaurant" && table.sub_area && (
                              <Badge variant="outline">
                                {SUB_AREAS.find(s => s.value === table.sub_area)?.label || table.sub_area}
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <div className="flex items-center justify-center gap-1">
                              <Users className="h-4 w-4 text-muted-foreground" />
                              <span className="font-medium">{table.seats_max}</span>
                              {table.seats_default !== table.seats_max && (
                                <span className="text-xs text-muted-foreground">
                                  (Std: {table.seats_default})
                                </span>
                              )}
                            </div>
                          </TableCell>
                          <TableCell className="text-center">
                            {table.combinable ? (
                              <Check className="h-5 w-5 text-green-500 mx-auto" />
                            ) : (
                              <X className="h-5 w-5 text-red-500 mx-auto" />
                            )}
                          </TableCell>
                          <TableCell>
                            {table.combinable_with?.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {table.combinable_with.map((tn, i) => (
                                  <Badge key={i} variant="outline" className="text-xs">
                                    {tn}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="text-center">
                            <Badge variant={table.active ? "default" : "secondary"}>
                              {table.active ? "Aktiv" : "Inaktiv"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex justify-end gap-2">
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => openEditDialog(table)}
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                variant="outline"
                                size="icon"
                                onClick={() => {
                                  setSelectedTable(table);
                                  setShowDeleteDialog(true);
                                }}
                              >
                                <Trash2 className="h-4 w-4 text-red-500" />
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                  )}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Tisch-Dialog */}
        <Dialog open={showDialog} onOpenChange={setShowDialog}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>
                {selectedTable ? `Tisch ${selectedTable.table_number} bearbeiten` : "Neuer Tisch"}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4">
              <div>
                <Label>Tischnummer *</Label>
                <Input
                  value={form.table_number}
                  onChange={(e) => setForm({ ...form, table_number: e.target.value })}
                  placeholder="z.B. 22"
                  data-testid="table-number-input"
                />
                {form.table_number === "3" && (
                  <p className="text-xs text-orange-600 mt-1">
                    ⚠ Tisch 3 (Sonderfall) wird automatisch als nicht kombinierbar markiert
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Bereich *</Label>
                  <Select
                    value={form.area}
                    onValueChange={(v) => setForm({ ...form, area: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {AREAS.map((area) => (
                        <SelectItem key={area.value} value={area.value}>
                          {area.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {form.area === "restaurant" && (
                  <div>
                    <Label>Subbereich *</Label>
                    <Select
                      value={form.sub_area}
                      onValueChange={(v) => setForm({ ...form, sub_area: v })}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SUB_AREAS.map((sub) => (
                          <SelectItem key={sub.value} value={sub.value}>
                            {sub.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Max. Plätze *</Label>
                  <Input
                    type="number"
                    min={1}
                    max={30}
                    value={form.seats_max}
                    onChange={(e) => setForm({ ...form, seats_max: e.target.value })}
                  />
                </div>
                <div>
                  <Label>Standard-Plätze</Label>
                  <Input
                    type="number"
                    min={1}
                    max={form.seats_max}
                    value={form.seats_default}
                    onChange={(e) => setForm({ ...form, seats_default: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Switch
                    checked={form.combinable && form.table_number !== "3"}
                    onCheckedChange={(v) => setForm({ ...form, combinable: v })}
                    disabled={form.table_number === "3"}
                  />
                  <Label>Kombinierbar</Label>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={form.active}
                    onCheckedChange={(v) => setForm({ ...form, active: v })}
                  />
                  <Label>Aktiv</Label>
                </div>
              </div>

              {form.combinable && form.table_number !== "3" && (
                <div>
                  <Label>Kombinierbar mit (Tischnummern, kommagetrennt)</Label>
                  <Input
                    value={form.combinable_with}
                    onChange={(e) => setForm({ ...form, combinable_with: e.target.value })}
                    placeholder="z.B. 7, 23, 24"
                  />
                </div>
              )}

              <div className="flex items-center gap-2">
                <Switch
                  checked={form.fixed}
                  onCheckedChange={(v) => setForm({ ...form, fixed: v })}
                />
                <Label>Fixiert (nicht verschiebbar im grafischen Plan)</Label>
              </div>

              <div>
                <Label>Notizen</Label>
                <Textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  placeholder="Optionale Anmerkungen"
                />
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setShowDialog(false)}>
                Abbrechen
              </Button>
              <Button onClick={handleSave} className="bg-[#002f02] hover:bg-[#003300]">
                {selectedTable ? "Speichern" : "Erstellen"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Lösch-Dialog */}
        <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Tisch archivieren?</AlertDialogTitle>
              <AlertDialogDescription>
                Tisch {selectedTable?.table_number} wird archiviert und ist nicht mehr im Tischplan sichtbar.
                Diese Aktion kann rückgängig gemacht werden.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Abbrechen</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleDelete}
                className="bg-red-600 hover:bg-red-700"
              >
                Archivieren
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>
    </Layout>
  );
};

export default TableAdmin;
