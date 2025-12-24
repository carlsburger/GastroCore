import React, { useState, useEffect } from "react";
import { usersApi } from "../lib/api";
import { t } from "../lib/i18n";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Label } from "../components/ui/label";
import { toast } from "sonner";
import { Plus, User, Trash2, Loader2, Shield, Clock, Link2, Unlink, UserCheck, AlertTriangle } from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

const ROLE_BADGES = {
  admin: "bg-primary text-primary-foreground",
  schichtleiter: "bg-[#a2d2ff] text-[#00280b]",
  service: "bg-emerald-100 text-emerald-700",
  mitarbeiter: "bg-muted text-muted-foreground",
};

export const Users = () => {
  const [users, setUsers] = useState([]);
  const [staffMembers, setStaffMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showDialog, setShowDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showLinkDialog, setShowLinkDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedStaffId, setSelectedStaffId] = useState("");
  const [linkingUser, setLinkingUser] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    role: "mitarbeiter",
  });
  const [submitting, setSubmitting] = useState(false);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await usersApi.getAll();
      setUsers(res.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Benutzer");
    } finally {
      setLoading(false);
    }
  };

  const fetchStaffMembers = async () => {
    try {
      const res = await axios.get(`${BACKEND_URL}/api/staff/members`, { headers });
      setStaffMembers(res.data || []);
    } catch (err) {
      console.error("Fehler beim Laden der Mitarbeiter:", err);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchStaffMembers();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await usersApi.create(formData);
      toast.success("Benutzer erstellt");
      setShowDialog(false);
      setFormData({ name: "", email: "", password: "", role: "mitarbeiter" });
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Erstellen");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    try {
      await usersApi.delete(selectedUser.id);
      toast.success("Benutzer archiviert");
      setShowDeleteDialog(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Archivieren");
    }
  };

  // Staff-Link Dialog öffnen
  const openLinkDialog = (user) => {
    setSelectedUser(user);
    setSelectedStaffId(user.staff_member_id || "");
    setShowLinkDialog(true);
  };

  // Staff-Verknüpfung speichern
  const handleLinkStaff = async () => {
    if (!selectedUser) return;
    
    setLinkingUser(true);
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/users/${selectedUser.id}/link-staff`,
        null,
        { 
          headers,
          params: { staff_member_id: selectedStaffId || null }
        }
      );
      
      toast.success(res.data.message);
      if (res.data.warning) {
        toast.warning(res.data.warning);
      }
      
      setShowLinkDialog(false);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Verknüpfen");
    } finally {
      setLinkingUser(false);
    }
  };

  // Staff-Verknüpfung aufheben
  const handleUnlinkStaff = async () => {
    if (!selectedUser) return;
    
    setLinkingUser(true);
    try {
      const res = await axios.post(
        `${BACKEND_URL}/api/users/${selectedUser.id}/link-staff`,
        null,
        { headers }
      );
      
      toast.success("Verknüpfung aufgehoben");
      setShowLinkDialog(false);
      fetchUsers();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Fehler beim Aufheben");
    } finally {
      setLinkingUser(false);
    }
  };

  // Hilfsfunktion: Staff-Name aus ID
  const getStaffName = (staffId) => {
    const staff = staffMembers.find(s => s.id === staffId);
    return staff ? `${staff.first_name} ${staff.last_name}` : "Unbekannt";
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              {t("users.title")}
            </h1>
            <p className="text-muted-foreground mt-1">
              Verwalten Sie die Benutzerkonten
            </p>
          </div>
          <Button onClick={() => setShowDialog(true)} className="rounded-full" data-testid="new-user-button">
            <Plus size={16} className="mr-2" />
            {t("users.newUser")}
          </Button>
        </div>

        {/* Users List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : users.length === 0 ? (
          <Card className="bg-card">
            <CardContent className="py-12 text-center">
              <User className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{t("common.noData")}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4">
            {users.map((user) => (
              <Card key={user.id} className="bg-card group" data-testid={`user-${user.id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                        <User size={24} className="text-primary" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{user.name}</h3>
                          {user.must_change_password && (
                            <Badge variant="outline" className="text-xs">
                              <Clock size={12} className="mr-1" />
                              Passwort ändern
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                        {/* Staff-Verknüpfungs-Status */}
                        {user.role !== "admin" && (
                          <div className="flex items-center gap-1 mt-1">
                            {user.staff_member_id ? (
                              <span className="text-xs text-green-600 flex items-center gap-1">
                                <UserCheck size={12} />
                                Verknüpft: {getStaffName(user.staff_member_id)}
                              </span>
                            ) : (
                              <span className="text-xs text-amber-600 flex items-center gap-1">
                                <AlertTriangle size={12} />
                                Nicht verknüpft
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge className={ROLE_BADGES[user.role] || ROLE_BADGES.mitarbeiter}>
                        <Shield size={12} className="mr-1" />
                        {t(`users.roles.${user.role}`)}
                      </Badge>
                      {/* Link/Unlink Button - nur für Nicht-Admins */}
                      {user.role !== "admin" && (
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => openLinkDialog(user)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity"
                          title={user.staff_member_id ? "Verknüpfung bearbeiten" : "Mit Mitarbeiter verknüpfen"}
                        >
                          {user.staff_member_id ? <Link size={16} className="text-green-600" /> : <LinkOff size={16} className="text-amber-600" />}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => {
                          setSelectedUser(user);
                          setShowDeleteDialog(true);
                        }}
                        className="opacity-0 group-hover:opacity-100 transition-opacity"
                        data-testid={`delete-user-${user.id}`}
                      >
                        <Trash2 size={16} className="text-destructive" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Create Dialog */}
      <Dialog open={showDialog} onOpenChange={setShowDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl">{t("users.newUser")}</DialogTitle>
            <DialogDescription>
              Der Benutzer muss beim ersten Login sein Passwort ändern
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <div className="grid gap-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="name">{t("users.name")} *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  required
                  data-testid="user-form-name"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email">{t("users.email")} *</Label>
                <Input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  data-testid="user-form-email"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password">{t("auth.password")} *</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  minLength={8}
                  data-testid="user-form-password"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="role">{t("users.role")} *</Label>
                <Select
                  value={formData.role}
                  onValueChange={(v) => setFormData({ ...formData, role: v })}
                >
                  <SelectTrigger data-testid="user-form-role">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">{t("users.roles.admin")}</SelectItem>
                    <SelectItem value="schichtleiter">{t("users.roles.schichtleiter")}</SelectItem>
                    <SelectItem value="mitarbeiter">{t("users.roles.mitarbeiter")}</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDialog(false)} className="rounded-full">
                {t("common.cancel")}
              </Button>
              <Button type="submit" disabled={submitting} className="rounded-full" data-testid="user-form-submit">
                {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
                {t("common.create")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("users.confirmDelete")}</AlertDialogTitle>
            <AlertDialogDescription>
              Der Benutzer "{selectedUser?.name}" wird archiviert. Diese Aktion wird im Audit-Log protokolliert.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="rounded-full">{t("common.cancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="rounded-full bg-destructive" data-testid="confirm-delete-user">
              {t("common.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Staff-Link Dialog */}
      <Dialog open={showLinkDialog} onOpenChange={setShowLinkDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="font-serif text-2xl flex items-center gap-2">
              <Link size={20} />
              Mitarbeiterprofil verknüpfen
            </DialogTitle>
            <DialogDescription>
              Verknüpfe das Benutzerkonto "{selectedUser?.name}" mit einem Mitarbeiterprofil, 
              damit der Benutzer seine Schichten in "Meine Schichten" sehen kann.
            </DialogDescription>
          </DialogHeader>
          
          <div className="py-4 space-y-4">
            {/* Aktueller Status */}
            <div className="p-3 bg-muted rounded-lg">
              <Label className="text-xs text-muted-foreground">Aktueller Status</Label>
              <div className="mt-1 flex items-center gap-2">
                {selectedUser?.staff_member_id ? (
                  <>
                    <UserCheck size={16} className="text-green-600" />
                    <span className="font-medium text-green-700">
                      Verknüpft mit: {getStaffName(selectedUser.staff_member_id)}
                    </span>
                  </>
                ) : (
                  <>
                    <AlertTriangle size={16} className="text-amber-600" />
                    <span className="font-medium text-amber-700">Nicht verknüpft</span>
                  </>
                )}
              </div>
            </div>

            {/* Mitarbeiter-Auswahl */}
            <div className="space-y-2">
              <Label htmlFor="staff-select">Mitarbeiterprofil auswählen</Label>
              <Select
                value={selectedStaffId}
                onValueChange={setSelectedStaffId}
              >
                <SelectTrigger id="staff-select">
                  <SelectValue placeholder="Mitarbeiter auswählen..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">-- Keine Verknüpfung --</SelectItem>
                  {staffMembers
                    .filter(s => !s.archived)
                    .sort((a, b) => `${a.last_name}`.localeCompare(`${b.last_name}`))
                    .map((staff) => (
                      <SelectItem key={staff.id} value={staff.id}>
                        {staff.first_name} {staff.last_name} ({staff.position || staff.department || "Mitarbeiter"})
                      </SelectItem>
                    ))
                  }
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Wähle das Mitarbeiterprofil aus, das mit diesem Benutzerkonto verknüpft werden soll.
              </p>
            </div>
          </div>

          <DialogFooter className="flex gap-2">
            {selectedUser?.staff_member_id && (
              <Button 
                type="button" 
                variant="outline" 
                onClick={handleUnlinkStaff}
                disabled={linkingUser}
                className="rounded-full text-amber-600 border-amber-300 hover:bg-amber-50"
              >
                <LinkOff size={16} className="mr-2" />
                Verknüpfung aufheben
              </Button>
            )}
            <Button 
              type="button" 
              variant="outline" 
              onClick={() => setShowLinkDialog(false)} 
              className="rounded-full"
            >
              {t("common.cancel")}
            </Button>
            <Button 
              type="button" 
              onClick={handleLinkStaff}
              disabled={linkingUser || !selectedStaffId}
              className="rounded-full"
            >
              {linkingUser ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Link size={16} className="mr-2" />}
              Verknüpfen
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default Users;
