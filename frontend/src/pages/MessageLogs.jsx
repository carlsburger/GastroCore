import React, { useState, useEffect } from "react";
import { Layout } from "../components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import {
  Mail,
  MessageCircle,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  RefreshCw,
  Search,
} from "lucide-react";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const CHANNEL_CONFIG = {
  email: { label: "E-Mail", icon: Mail, color: "bg-blue-100 text-blue-800" },
  whatsapp: { label: "WhatsApp", icon: MessageCircle, color: "bg-green-100 text-green-800" },
};

const STATUS_CONFIG = {
  sent: { label: "Gesendet", icon: CheckCircle, color: "bg-green-100 text-green-800" },
  failed: { label: "Fehlgeschlagen", icon: XCircle, color: "bg-red-100 text-red-800" },
  pending: { label: "Ausstehend", icon: Clock, color: "bg-yellow-100 text-yellow-800" },
  link_generated: { label: "Link erstellt", icon: CheckCircle, color: "bg-blue-100 text-blue-800" },
};

export const MessageLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [channelFilter, setChannelFilter] = useState("all");
  const [search, setSearch] = useState("");

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  useEffect(() => {
    fetchLogs();
  }, [channelFilter]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = { limit: 200 };
      if (channelFilter !== "all") params.channel = channelFilter;
      
      const response = await axios.get(`${BACKEND_URL}/api/message-logs`, { headers, params });
      setLogs(response.data);
    } catch (err) {
      toast.error("Fehler beim Laden der Logs");
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleString("de-DE", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return timestamp;
    }
  };

  const filteredLogs = logs.filter((log) => {
    if (!search) return true;
    return (
      log.recipient?.toLowerCase().includes(search.toLowerCase()) ||
      log.reservation_id?.toLowerCase().includes(search.toLowerCase()) ||
      log.message_type?.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <Layout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="font-serif text-3xl md:text-4xl font-medium text-primary">
              Nachrichten-Log
            </h1>
            <p className="text-muted-foreground mt-1">
              Alle gesendeten E-Mails und WhatsApp-Nachrichten
            </p>
          </div>
          <Button variant="outline" onClick={fetchLogs} className="rounded-full">
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Aktualisieren
          </Button>
        </div>

        <Card>
          <CardContent className="p-4">
            <div className="flex gap-4 flex-wrap">
              <div className="flex-1 min-w-[200px]">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground h-4 w-4" />
                  <Input
                    placeholder="Suche nach Empfänger, ID..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
              </div>
              <Select value={channelFilter} onValueChange={setChannelFilter}>
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Kanal" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Alle Kanäle</SelectItem>
                  <SelectItem value="email">E-Mail</SelectItem>
                  <SelectItem value="whatsapp">WhatsApp</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
          </div>
        ) : filteredLogs.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <Mail className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-muted-foreground">Keine Nachrichten gefunden</p>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {filteredLogs.map((log) => {
              const channelConfig = CHANNEL_CONFIG[log.channel] || CHANNEL_CONFIG.email;
              const statusConfig = STATUS_CONFIG[log.status] || STATUS_CONFIG.pending;
              const ChannelIcon = channelConfig.icon;
              const StatusIcon = statusConfig.icon;

              return (
                <Card key={log.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className={`p-2 rounded-full ${channelConfig.color}`}>
                          <ChannelIcon className="h-5 w-5" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{log.recipient}</span>
                            <Badge variant="outline" className="text-xs">
                              {log.message_type}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            Reservierung: {log.reservation_id?.slice(0, 8)}...
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <Badge className={statusConfig.color}>
                          <StatusIcon className="h-3 w-3 mr-1" />
                          {statusConfig.label}
                        </Badge>
                        <span className="text-sm text-muted-foreground">
                          {formatTimestamp(log.timestamp)}
                        </span>
                      </div>
                    </div>
                    {log.error_message && (
                      <div className="mt-2 p-2 bg-red-50 rounded text-sm text-red-700">
                        {log.error_message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default MessageLogs;
