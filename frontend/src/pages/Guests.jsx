import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import {
  Search,
  Users,
  Phone,
  Mail,
  Loader2,
  AlertTriangle,
  Ban,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const FLAG_CONFIG = {
  none: { label: "Normal", className: "bg-green-100 text-green-800", icon: CheckCircle },
  greylist: { label: "Greylist", className: "bg-yellow-100 text-yellow-800", icon: AlertCircle },
  blacklist: { label: "Blacklist", className: "bg-red-100 text-red-800", icon: Ban },
};

export const Guests = () => {
  const [guests, setGuests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [flagFilter, setFlagFilter] = useState("all");
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [selectedGuest, setSelectedGuest] = useState(null);
  const [editFlag, setEditFlag] = useState("");
  const [editNotes, setEditNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchGuests = async () => {
    setLoading(true);
    try {
      const params = {};
      if (flagFilter !== "all") params.flag = flagFilter;
      if (search) params.search = search;

      const res = await axios.get(`${BACKEND_URL}/api/guests`, { headers, params });
      setGuests(res.data);
    } catch (err) {
      toast.error("Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGuests();
  }, [flagFilter, search]);

  const handleEdit = (guest) => {
    setSelectedGuest(guest);
    setEditFlag(guest.flag || "none");
    setEditNotes(guest.notes || "");
    setShowEditDialog(true);
  };

  const handleSave = async () => {
    if (!selectedGuest) return;
    setSubmitting(true);
    try {
      await axios.patch(
        `${BACKEND_URL}/api/guests/${selectedGuest.id}`,
        { flag: editFlag, notes: editNotes },
        { headers }
      );
      toast.success("Gast aktualisiert");
      setShowEditDialog(false);
      fetchGuests();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">Gäste</h1>
            <p className="text-muted-foreground mt-1">No-Show Management & Gästelisten</p>
          </div>
        </div>

        {/* Filters */}
        <Card className="bg-card">
          <CardContent className="p-4 flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="Suche nach Name, Telefon, E-Mail..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 h-11"
              />
            </div>
            <div className="flex gap-2">
              {["all", "greylist", "blacklist"].map((flag) => (
                <Button
                  key={flag}
                  variant={flagFilter === flag ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFlagFilter(flag)}
                  className="rounded-full"
                >
                  {flag === "all" ? "Alle" : FLAG_CONFIG[flag]?.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-card">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold">{guests.length}</p>
              <p className="text-sm text-muted-foreground">Gesamt</p>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-yellow-600">
                {guests.filter((g) => g.flag === "greylist").length}
              </p>
              <p className="text-sm text-muted-foreground">Greylist</p>
            </CardContent>
          </Card>
          <Card className="bg-card">
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold text-red-600">
                {guests.filter((g) => g.flag === "blacklist").length}
              </p>
              <p className="text-sm text-muted-foreground">Blacklist</p>
            </CardContent>
          </Card>
        </div>

        {/* Guests List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : guests.length === 0 ? (
          <Card className="bg-card">
            <CardContent className="py-12 text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Gäste gefunden</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {guests.map((guest) => {
              const flagConfig = FLAG_CONFIG[guest.flag] || FLAG_CONFIG.none;
              const FlagIcon = flagConfig.icon;
              
              return (
                <Card
                  key={guest.id}
                  className="bg-card hover:shadow-md transition-all cursor-pointer"
                  onClick={() => handleEdit(guest)}
                  data-testid={`guest-${guest.id}`}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-full ${flagConfig.className}`}>
                          <FlagIcon size={20} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-semibold">{guest.name || "Unbekannt"}</p>
                            <Badge className={flagConfig.className}>{flagConfig.label}</Badge>
                          </div>
                          <div className="flex items-center gap-4 text-sm text-muted-foreground mt-1">
                            <span className="flex items-center gap-1">
                              <Phone size={14} />
                              {guest.phone}
                            </span>
                            {guest.email && (
                              <span className="flex items-center gap-1">
                                <Mail size={14} />
                                {guest.email}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-2xl font-bold">{guest.no_show_count || 0}</p>
                        <p className="text-xs text-muted-foreground">No-Shows</p>
                      </div>
                    </div>
                    {guest.notes && (
                      <p className="text-sm text-muted-foreground mt-2 bg-muted p-2 rounded">
                        {guest.notes}
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">Gast bearbeiten</DialogTitle>
            <DialogDescription>
              {selectedGuest?.phone} - {selectedGuest?.no_show_count || 0} No-Shows
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="space-y-2">
              <Label>Status</Label>
              <div className="flex gap-2">
                {Object.entries(FLAG_CONFIG).map(([key, config]) => (
                  <Button
                    key={key}
                    variant={editFlag === key ? "default" : "outline"}
                    className={`flex-1 rounded-full ${editFlag === key ? "" : config.className}`}
                    onClick={() => setEditFlag(key)}
                  >
                    {config.label}
                  </Button>
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>Notizen</Label>
              <Textarea
                value={editNotes}
                onChange={(e) => setEditNotes(e.target.value)}
                placeholder="Interne Notizen zum Gast..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)} className="rounded-full">
              Abbrechen
            </Button>
            <Button onClick={handleSave} disabled={submitting} className="rounded-full">
              {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
              Speichern
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Guests;
