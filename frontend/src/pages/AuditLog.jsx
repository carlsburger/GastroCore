import React, { useState, useEffect } from "react";
import { auditApi } from "../lib/api";
import { t } from "../lib/i18n";
import { Layout } from "../components/Layout";
import { Card, CardContent } from "../components/ui/card";
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
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { Button } from "../components/ui/button";
import { ScrollArea } from "../components/ui/scroll-area";
import { toast } from "sonner";
import { FileText, Loader2, Eye, User, Calendar, ArrowRight } from "lucide-react";
import { format } from "date-fns";
import { de } from "date-fns/locale";

const ACTION_BADGES = {
  create: "bg-green-100 text-green-800 border-green-200",
  update: "bg-blue-100 text-blue-800 border-blue-200",
  archive: "bg-red-100 text-red-800 border-red-200",
  status_change: "bg-yellow-100 text-yellow-800 border-yellow-200",
  password_change: "bg-purple-100 text-purple-800 border-purple-200",
};

const ENTITY_LABELS = {
  user: "Benutzer",
  area: "Bereich",
  reservation: "Reservierung",
  setting: "Einstellung",
};

export const AuditLog = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [entityFilter, setEntityFilter] = useState("all");
  const [showDetailDialog, setShowDetailDialog] = useState(false);
  const [selectedLog, setSelectedLog] = useState(null);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = {};
      if (entityFilter !== "all") params.entity = entityFilter;
      const res = await auditApi.getAll(params);
      setLogs(res.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Audit-Logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [entityFilter]);

  const formatTimestamp = (timestamp) => {
    try {
      return format(new Date(timestamp), "dd.MM.yyyy HH:mm:ss", { locale: de });
    } catch {
      return timestamp;
    }
  };

  const renderDiff = (before, after) => {
    if (!before && !after) return null;
    
    const allKeys = new Set([
      ...Object.keys(before || {}),
      ...Object.keys(after || {}),
    ]);

    const changes = [];
    allKeys.forEach((key) => {
      const beforeVal = before?.[key];
      const afterVal = after?.[key];
      if (JSON.stringify(beforeVal) !== JSON.stringify(afterVal)) {
        changes.push({ key, before: beforeVal, after: afterVal });
      }
    });

    if (changes.length === 0) return <p className="text-muted-foreground">Keine Änderungen</p>;

    return (
      <div className="space-y-2">
        {changes.map(({ key, before, after }) => (
          <div key={key} className="p-2 bg-muted rounded-lg">
            <p className="text-xs font-medium text-muted-foreground mb-1">{key}</p>
            <div className="flex items-center gap-2 text-sm">
              <span className="text-red-600 line-through">
                {before !== undefined ? JSON.stringify(before) : "—"}
              </span>
              <ArrowRight size={14} className="text-muted-foreground" />
              <span className="text-green-600">
                {after !== undefined ? JSON.stringify(after) : "—"}
              </span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              {t("audit.title")}
            </h1>
            <p className="text-muted-foreground mt-1">
              Alle Änderungen werden hier protokolliert
            </p>
          </div>
          <Select value={entityFilter} onValueChange={setEntityFilter}>
            <SelectTrigger className="w-[180px]" data-testid="entity-filter">
              <SelectValue placeholder="Entität filtern" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.all")}</SelectItem>
              <SelectItem value="user">Benutzer</SelectItem>
              <SelectItem value="area">Bereiche</SelectItem>
              <SelectItem value="reservation">Reservierungen</SelectItem>
              <SelectItem value="setting">Einstellungen</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Logs List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : logs.length === 0 ? (
          <Card className="bg-card">
            <CardContent className="py-12 text-center">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">{t("common.noData")}</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {logs.map((log) => (
              <Card
                key={log.id}
                className="bg-card hover:shadow-md transition-all cursor-pointer"
                onClick={() => {
                  setSelectedLog(log);
                  setShowDetailDialog(true);
                }}
                data-testid={`audit-log-${log.id}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="p-2 rounded-full bg-muted">
                        <FileText size={20} className="text-muted-foreground" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge className={`${ACTION_BADGES[log.action]} border`}>
                            {t(`audit.actions.${log.action}`)}
                          </Badge>
                          <Badge variant="outline">
                            {ENTITY_LABELS[log.entity] || log.entity}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <User size={14} />
                            {log.actor_email}
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar size={14} />
                            {formatTimestamp(log.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button variant="ghost" size="icon">
                      <Eye size={18} />
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Detail Dialog */}
      <Dialog open={showDetailDialog} onOpenChange={setShowDetailDialog}>
        <DialogContent className="max-w-2xl">
          {selectedLog && (
            <>
              <DialogHeader>
                <DialogTitle className="font-serif text-2xl flex items-center gap-2">
                  <Badge className={`${ACTION_BADGES[selectedLog.action]} border`}>
                    {t(`audit.actions.${selectedLog.action}`)}
                  </Badge>
                  {ENTITY_LABELS[selectedLog.entity] || selectedLog.entity}
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">{t("audit.actor")}</p>
                    <p className="font-medium">{selectedLog.actor_email}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("audit.timestamp")}</p>
                    <p className="font-medium">{formatTimestamp(selectedLog.timestamp)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t("audit.entity")}</p>
                    <p className="font-medium">{ENTITY_LABELS[selectedLog.entity] || selectedLog.entity}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Entity ID</p>
                    <p className="font-medium font-mono text-sm">{selectedLog.entity_id}</p>
                  </div>
                </div>

                <div>
                  <p className="text-sm text-muted-foreground mb-2">Änderungen</p>
                  <ScrollArea className="h-[300px] rounded-lg border p-4">
                    {renderDiff(selectedLog.before, selectedLog.after)}
                  </ScrollArea>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default AuditLog;
