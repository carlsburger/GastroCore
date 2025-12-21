import React, { useState, useEffect } from "react";
import { areasApi } from "../lib/api";
import { t } from "../lib/i18n";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent } from "../components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
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
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { toast } from "sonner";
import { Plus, MapPin, Users, Pencil, Trash2, Loader2 } from "lucide-react";

export const Areas = () => {
  const [areas, setAreas] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedArea, setSelectedArea] = useState(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    capacity: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const fetchAreas = async () => {
    setLoading(true);
    try {
      const res = await areasApi.getAll();
      setAreas(res.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Bereiche");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAreas();
  }, []);

  const handleOpenDialog = (area = null) => {
    if (area) {
      setSelectedArea(area);
      setFormData({
        name: area.name,
        description: area.description || "",
        capacity: area.capacity?.toString() || "",
      });
    } else {
      setSelectedArea(null);
      setFormData({ name: "", description: "", capacity: "" });
    }
    setShowDialog(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    
    const data = {
      name: formData.name,
      description: formData.description || null,
      capacity: formData.capacity ? parseInt(formData.capacity) : null,
    };

    try {
      if (selectedArea) {
        await areasApi.update(selectedArea.id, data);
        toast.success("Bereich aktualisiert");
      } else {
        await areasApi.create(data);
        toast.success("Bereich erstellt");
      }
      setShowDialog(false);
      fetchAreas();
    } catch (err) {
      toast.error("Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await areasApi.delete(selectedArea.id);
      toast.success("Bereich archiviert");
      setShowDeleteDialog(false);
      setSelectedArea(null);
      fetchAreas();
    } catch (err) {
      toast.error("Fehler beim Archivieren");
    }
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              {t("areas.title")}
            </h1>
            <p className="text-muted-foreground mt-1">
              Verwalten Sie Ihre Restaurant-Bereiche
            </p>
          </div>
          <Button onClick={() => handleOpenDialog()} className="rounded-full" data-testid="new-area-button">
            <Plus size={16} className="mr-2" />
            {t("areas.newArea")}
          </Button>
        </div>

        {/* Areas Grid */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : areas.length === 0 ? (
          <Card className="bg-card">
            <CardContent className="py-12 text-center">
              <MapPin className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{t("common.noData")}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {areas.map((area) => (
              <Card key={area.id} className="bg-card group" data-testid={`area-${area.id}`}>
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-3 rounded-full bg-primary/10">
                        <MapPin size={24} className="text-primary" />
                      </div>
                      <div>
                        <h3 className="font-medium text-lg">{area.name}</h3>
                        {area.capacity && (
                          <p className="text-sm text-muted-foreground flex items-center gap-1">
                            <Users size={14} />
                            {area.capacity} Plätze
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleOpenDialog(area)}
                        data-testid={`edit-area-${area.id}`}
                      >
                        <Pencil size={16} />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedArea(area);
                          setShowDeleteDialog(true);
                        }}
                        data-testid={`delete-area-${area.id}`}
                      >
                        <Trash2 size={16} className="text-destructive" />
                      </Button>
                    </div>
                  </div>
                  {area.description && (
                    <p className="text-sm text-muted-foreground mt-3">{area.description}</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">
              {selectedArea ? "Bereich bearbeiten" : t("areas.newArea")}
            </DialogTitle>
            <DialogDescription>
              {selectedArea ? "Ändern Sie die Bereichsdaten" : "Erstellen Sie einen neuen Bereich"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t("areas.name")} *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="area-form-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="capacity">{t("areas.capacity")}</Label>
                <Input
                  id="capacity"
                  type="number"
                  min="1"
                  value={formData.capacity}
                  onChange={(e) => setFormData({ ...formData, capacity: e.target.value })}
                  data-testid="area-form-capacity"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">{t("areas.description")}</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  data-testid="area-form-description"
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)} className="rounded-full">
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full" data-testid="area-form-submit">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {t("common.save")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("areas.confirmDelete")}</AlertDialogTitle>
            <AlertDialogDescription>
              Der Bereich "{selectedArea?.name}" wird archiviert. Diese Aktion wird im Audit-Log protokolliert.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-full">{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="rounded-full bg-destructive" data-testid="confirm-delete">
              {t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Layout>
  );
};

export default Areas;
