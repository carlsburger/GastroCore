import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
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
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Switch } from "../components/ui/switch";
import { toast } from "sonner";
import {
  ArrowLeft,
  Plus,
  RefreshCw,
  Loader2,
  Edit,
  Trash2,
  GripVertical,
  Euro,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

export const EventProducts = () => {
  const { eventId } = useParams();
  const navigate = useNavigate();
  const [event, setEvent] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    price_delta: 0,
    required: true,
    selection_type: "single_choice",
    sort_order: 0,
    is_active: true,
  });

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchData();
  }, [eventId]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eventRes, productsRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/events/${eventId}`, { headers }),
        axios.get(`${BACKEND_URL}/api/events/${eventId}/products`, { headers }),
      ]);
      setEvent(eventRes.data);
      setProducts(productsRes.data);
    } catch (err) {
      toast.error("Fehler beim Laden");
      navigate("/events");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      description: "",
      price_delta: 0,
      required: true,
      selection_type: "single_choice",
      sort_order: products.length,
      is_active: true,
    });
    setEditingProduct(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const data = { ...formData, event_id: eventId };
      if (editingProduct) {
        await axios.patch(`${BACKEND_URL}/api/events/${eventId}/products/${editingProduct.id}`, data, { headers });
        toast.success("Option aktualisiert");
      } else {
        await axios.post(`${BACKEND_URL}/api/events/${eventId}/products`, data, { headers });
        toast.success("Option erstellt");
      }
      setShowDialog(false);
      resetForm();
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Speichern");
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (product) => {
    setEditingProduct(product);
    setFormData({
      name: product.name || "",
      description: product.description || "",
      price_delta: product.price_delta || 0,
      required: product.required ?? true,
      selection_type: product.selection_type || "single_choice",
      sort_order: product.sort_order || 0,
      is_active: product.is_active ?? true,
    });
    setShowDialog(true);
  };

  const handleDelete = async (productId) => {
    if (!window.confirm("Option wirklich löschen?")) return;
    try {
      await axios.delete(`${BACKEND_URL}/api/events/${eventId}/products/${productId}`, { headers });
      toast.success("Option gelöscht");
      fetchData();
    } catch (err) {
      toast.error("Fehler beim Löschen");
    }
  };

  if (loading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Loader2 className="h-10 w-10 animate-spin text-primary" />
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <Button variant="ghost" onClick={() => navigate("/events")} className="rounded-full">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="flex-1">
            <h1 className="font-serif text-3xl font-medium text-primary">
              Vorbestell-Optionen
            </h1>
            <p className="text-muted-foreground">
              {event?.title}
            </p>
          </div>
          <Button variant="outline" onClick={fetchData} className="rounded-full">
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Button
            onClick={() => {
              resetForm();
              setShowDialog(true);
            }}
            className="rounded-full"
          >
            <Plus className="h-4 w-4 mr-2" />
            Neue Option
          </Button>
        </div>

        {/* Info */}
        <Card>
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">
              Definieren Sie hier die Auswahloptionen für Gäste bei der Buchung. 
              Bei "Verpflichtend" müssen Gäste eine Auswahl treffen.
              Der Preisaufschlag wird zum Grundpreis addiert.
            </p>
          </CardContent>
        </Card>

        {/* Products List */}
        {products.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">Keine Optionen definiert</p>
              <Button
                onClick={() => {
                  resetForm();
                  setShowDialog(true);
                }}
                className="mt-4"
              >
                <Plus className="h-4 w-4 mr-2" />
                Erste Option erstellen
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {products.map((product, index) => (
              <Card key={product.id} className={`${!product.is_active ? "opacity-50" : ""}`}>
                <CardContent className="p-4">
                  <div className="flex items-center gap-4">
                    <GripVertical className="h-5 w-5 text-muted-foreground cursor-move" />
                    
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{product.name}</span>
                        {product.required && (
                          <Badge variant="secondary" className="text-xs">Pflicht</Badge>
                        )}
                        {!product.is_active && (
                          <Badge variant="outline" className="text-xs">Inaktiv</Badge>
                        )}
                      </div>
                      {product.description && (
                        <p className="text-sm text-muted-foreground mt-1">{product.description}</p>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-4">
                      {product.price_delta !== 0 && (
                        <span className={`font-medium ${product.price_delta > 0 ? "text-green-600" : "text-red-600"}`}>
                          {product.price_delta > 0 ? "+" : ""}{product.price_delta?.toFixed(2)} €
                        </span>
                      )}
                      
                      <Badge variant="outline">
                        {product.selection_type === "single_choice" ? "Einzelauswahl" : "Mehrfachauswahl"}
                      </Badge>
                      
                      <Button size="sm" variant="ghost" onClick={() => handleEdit(product)}>
                        <Edit className="h-4 w-4" />
                      </Button>
                      
                      <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleDelete(product.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>
              {editingProduct ? "Option bearbeiten" : "Neue Option"}
            </DialogTitle>
            <DialogDescription>
              z.B. Fisch, Fleisch, Vegetarisch für Gänseabend
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label>Name *</Label>
                <Input
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  placeholder="z.B. Gans (klassisch)"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Beschreibung</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  rows={2}
                  placeholder="Optionale Beschreibung"
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Preisaufschlag (€)</Label>
                  <Input
                    type="number"
                    step="0.01"
                    value={formData.price_delta}
                    onChange={(e) => setFormData({ ...formData, price_delta: parseFloat(e.target.value) || 0 })}
                  />
                  <p className="text-xs text-muted-foreground">
                    Negativ = Rabatt, 0 = kein Aufschlag
                  </p>
                </div>
                <div className="space-y-2">
                  <Label>Auswahltyp</Label>
                  <Select
                    value={formData.selection_type}
                    onValueChange={(v) => setFormData({ ...formData, selection_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="single_choice">Einzelauswahl</SelectItem>
                      <SelectItem value="multi_choice">Mehrfachauswahl</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <Label>Pflichtauswahl</Label>
                  <p className="text-sm text-muted-foreground">
                    Gast muss eine Auswahl treffen
                  </p>
                </div>
                <Switch
                  checked={formData.required}
                  onCheckedChange={(v) => setFormData({ ...formData, required: v })}
                />
              </div>
              
              <div className="flex items-center justify-between p-3 bg-muted rounded-lg">
                <div>
                  <Label>Aktiv</Label>
                  <p className="text-sm text-muted-foreground">
                    Option ist buchbar
                  </p>
                </div>
                <Switch
                  checked={formData.is_active}
                  onCheckedChange={(v) => setFormData({ ...formData, is_active: v })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)}>
                Abbrechen
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
                {editingProduct ? "Speichern" : "Erstellen"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default EventProducts;
