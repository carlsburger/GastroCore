import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  Clock,
  AlertCircle,
  CheckCircle,
  XCircle,
  Info,
  Settings,
  Users,
  CalendarDays,
  CalendarRange,
  Sparkles
} from 'lucide-react';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../components/ui/tooltip';
import Layout from '../components/Layout';

const API_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL || '';

// Hilfsfunktionen
const getWeekDates = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  const monday = new Date(d.setDate(diff));
  
  const dates = [];
  for (let i = 0; i < 7; i++) {
    const current = new Date(monday);
    current.setDate(monday.getDate() + i);
    dates.push(current.toISOString().split('T')[0]);
  }
  return dates;
};

const formatDate = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' });
};

const formatDateLong = (dateStr) => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('de-DE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
};

const getWeekNumber = (dateStr) => {
  const date = new Date(dateStr);
  const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
  const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
  return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
};

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];
const WEEKDAYS_LONG = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag'];

// LocalStorage Key für View-Mode
const VIEW_MODE_KEY = 'carlsburg_calendar_view';

export default function ReservationCalendar() {
  const navigate = useNavigate();
  
  // View Mode: "week" (default) oder "day"
  const [viewMode, setViewMode] = useState(() => {
    return localStorage.getItem(VIEW_MODE_KEY) || 'week';
  });
  
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [openingHours, setOpeningHours] = useState({});
  const [slotsData, setSlotsData] = useState({});
  const [reservationCounts, setReservationCounts] = useState({});
  const [reservationsData, setReservationsData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const weekDates = useMemo(() => getWeekDates(currentDate), [currentDate]);
  const weekNumber = useMemo(() => getWeekNumber(weekDates[0]), [weekDates]);

  // View Mode speichern
  useEffect(() => {
    localStorage.setItem(VIEW_MODE_KEY, viewMode);
  }, [viewMode]);

  const getToken = () => localStorage.getItem('token');

  // Daten laden
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);

    const token = getToken();
    if (!token) {
      setError('Nicht eingeloggt');
      setLoading(false);
      return;
    }

    const fromDate = viewMode === 'week' ? weekDates[0] : selectedDate;
    const toDate = viewMode === 'week' ? weekDates[6] : selectedDate;

    try {
      // Öffnungszeiten laden
      const hoursRes = await fetch(
        `${API_URL}/api/opening-hours/effective?from=${fromDate}&to=${toDate}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!hoursRes.ok) throw new Error('Öffnungszeiten konnten nicht geladen werden');
      const hoursData = await hoursRes.json();

      // Slots laden
      const slotsRes = await fetch(
        `${API_URL}/api/reservation-slots/effective-range?from=${fromDate}&to=${toDate}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!slotsRes.ok) throw new Error('Slots konnten nicht geladen werden');
      const slotsDataRes = await slotsRes.json();

      // Reservierungen laden (für Wochenansicht mit Details)
      const counts = {};
      const reservationsMap = {};
      if (viewMode === 'week') {
        for (const date of weekDates) {
          try {
            const resRes = await fetch(
              `${API_URL}/api/reservations?date=${date}`,
              { headers: { 'Authorization': `Bearer ${token}` } }
            );
            if (resRes.ok) {
              const resData = await resRes.json();
              const resList = Array.isArray(resData) ? resData : (resData.items || []);
              // Nur aktive Reservierungen
              const activeRes = resList
                .filter(r => !['storniert', 'no_show'].includes(r.status))
                .sort((a, b) => (a.time || '00:00').localeCompare(b.time || '00:00'));
              counts[date] = activeRes.length;
              // Speichere max 5 Reservierungen pro Tag für die Übersicht
              reservationsMap[date] = activeRes.slice(0, 5).map(r => ({
                time: r.time?.substring(0, 5) || '–',
                name: r.guest_name?.split(' ')[0] || 'Gast',
                party_size: r.party_size || 0,
              }));
            }
          } catch {
            counts[date] = 0;
            reservationsMap[date] = [];
          }
        }
      }

      // Daten in Maps umwandeln
      const hoursMap = {};
      (hoursData.days || []).forEach(day => {
        hoursMap[day.date] = day;
      });

      const slotsMap = {};
      (slotsDataRes.days || []).forEach(day => {
        slotsMap[day.date] = day;
      });

      setOpeningHours(hoursMap);
      setSlotsData(slotsMap);
      setReservationCounts(counts);
      setReservationsData(reservationsMap);
    } catch (err) {
      console.error('Fehler beim Laden:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [weekDates, selectedDate, viewMode]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Navigation
  const goToPrevWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - 7);
    setCurrentDate(newDate);
  };

  const goToNextWeek = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + 7);
    setCurrentDate(newDate);
  };

  const goToPrevDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() - 1);
    setSelectedDate(newDate.toISOString().split('T')[0]);
  };

  const goToNextDay = () => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + 1);
    setSelectedDate(newDate.toISOString().split('T')[0]);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
    setSelectedDate(new Date().toISOString().split('T')[0]);
  };

  const handleDayClick = (dateStr) => {
    setSelectedDate(dateStr);
    setViewMode('day');
  };

  // ========== WOCHENANSICHT KARTE (entschlackt) ==========
  const WeekDayCard = ({ dateStr, index }) => {
    const hours = openingHours[dateStr] || {};
    const slots = slotsData[dateStr] || {};
    const reservationCount = reservationCounts[dateStr] || 0;
    const dayReservations = reservationsData[dateStr] || [];
    
    const isOpen = hours.is_open !== false && slots.open !== false;
    const isClosed = !isOpen;
    const isToday = dateStr === new Date().toISOString().split('T')[0];
    
    const blocks = hours.blocks || [];
    const openTime = blocks.length > 0 ? blocks[0].start : null;
    const closeTime = blocks.length > 0 ? blocks[blocks.length - 1].end : null;

    return (
      <Card 
        className={`
          cursor-pointer transition-all duration-200 hover:shadow-lg
          ${isToday ? 'ring-2 ring-[#002f02] bg-[#002f02]/5' : ''}
          ${isClosed ? 'bg-gray-100' : 'hover:border-[#002f02]/50'}
        `}
        onClick={() => handleDayClick(dateStr)}
      >
        <CardContent className="p-3">
          {/* Wochentag + Datum */}
          <div className="text-center mb-2 pb-2 border-b border-gray-100">
            <div className={`text-xs font-medium ${isToday ? 'text-[#002f02]' : 'text-gray-500'}`}>
              {WEEKDAYS[index]}
            </div>
            <div className={`text-xl font-bold ${isToday ? 'text-[#002f02]' : 'text-gray-800'}`}>
              {new Date(dateStr).getDate()}.
            </div>
          </div>
          
          {isClosed ? (
            <div className="text-center py-3">
              <XCircle className="w-5 h-5 text-gray-400 mx-auto mb-1" />
              <span className="text-xs text-gray-500">geschlossen</span>
            </div>
          ) : (
            <div className="space-y-2">
              {/* Öffnungszeit - eine Zeile */}
              {openTime && closeTime && (
                <div className="text-center text-xs text-gray-600 font-medium">
                  {openTime}–{closeTime}
                </div>
              )}
              
              {/* Reservierungsliste */}
              <div className="space-y-0.5 min-h-[60px]">
                {dayReservations.length === 0 ? (
                  <div className="text-xs text-gray-400 text-center py-2">keine</div>
                ) : (
                  dayReservations.map((res, idx) => (
                    <div key={idx} className="text-xs truncate">
                      <span className="font-medium text-gray-600">{res.time}</span>
                      <span className="text-gray-400 mx-0.5">–</span>
                      <span className="text-gray-700">{res.name}</span>
                      <span className="text-gray-400 ml-0.5">({res.party_size})</span>
                    </div>
                  ))
                )}
                {reservationCount > 5 && (
                  <div className="text-xs text-gray-400 text-center">+{reservationCount - 5} mehr</div>
                )}
              </div>
              
              {/* Gesamt */}
              {reservationCount > 0 && (
                <div className="text-center pt-2 border-t border-gray-100">
                  <span className="text-xs font-semibold text-[#002f02]">{reservationCount} Res.</span>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  // ========== TAGESANSICHT (detailliert) ==========
  const DayDetailView = () => {
    const hours = openingHours[selectedDate] || {};
    const slots = slotsData[selectedDate] || {};
    
    const isOpen = hours.is_open !== false && slots.open !== false;
    const isClosed = !isOpen;
    
    const blocks = hours.blocks || [];
    const openTime = blocks.length > 0 ? blocks[0].start : null;
    const closeTime = blocks.length > 0 ? blocks[blocks.length - 1].end : null;
    
    const slotsList = slots.slots || [];
    const blockedWindows = slots.blocked || [];
    const notes = slots.notes || [];
    
    const isHoliday = hours.is_holiday;
    const holidayName = hours.holiday_name;
    const closureReason = hours.closure_reason;

    return (
      <div className="max-w-2xl mx-auto">
        <Card className="shadow-lg">
          <CardHeader className="border-b bg-gray-50">
            <CardTitle className="text-xl flex items-center gap-3">
              <CalendarDays className="w-6 h-6 text-[#002f02]" />
              {formatDateLong(selectedDate)}
            </CardTitle>
          </CardHeader>
          
          <CardContent className="p-6">
            {isClosed ? (
              <div className="text-center py-8">
                <XCircle className="w-16 h-16 text-gray-300 mx-auto mb-4" />
                <h3 className="text-xl font-semibold text-gray-600 mb-2">Geschlossen</h3>
                {closureReason && (
                  <p className="text-gray-500">{closureReason}</p>
                )}
                {isHoliday && holidayName && (
                  <Badge variant="outline" className="mt-3 border-amber-400 text-amber-700">
                    {holidayName}
                  </Badge>
                )}
              </div>
            ) : (
              <div className="space-y-6">
                {/* Öffnungszeiten - kompakt */}
                <div className="flex items-center gap-4 p-4 bg-green-50 rounded-lg border border-green-200">
                  <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                    <CheckCircle className="w-6 h-6 text-green-600" />
                  </div>
                  <div>
                    <div className="text-sm text-green-700 font-medium">Geöffnet</div>
                    <div className="text-2xl font-bold text-green-800">
                      {openTime} – {closeTime}
                    </div>
                  </div>
                </div>
                
                {/* Sperrfenster - nur wenn vorhanden */}
                {blockedWindows.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-700 flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-500" />
                      Sperrfenster
                    </h4>
                    <div className="grid gap-2">
                      {blockedWindows.map((bw, idx) => (
                        <div key={idx} className="flex items-center gap-3 p-3 bg-red-50 rounded-lg border border-red-200">
                          <Clock className="w-4 h-4 text-red-500" />
                          <span className="font-medium text-red-700">{bw.start} – {bw.end}</span>
                          {bw.reason && <span className="text-red-600 text-sm">({bw.reason})</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Hinweise - nur wenn vorhanden */}
                {notes.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="font-medium text-gray-700 flex items-center gap-2">
                      <Info className="w-4 h-4 text-amber-500" />
                      Hinweise
                    </h4>
                    <div className="space-y-2">
                      {notes.map((note, idx) => (
                        <div key={idx} className="flex items-start gap-2 p-3 bg-amber-50 rounded-lg border border-amber-200">
                          <Info className="w-4 h-4 text-amber-600 mt-0.5 flex-shrink-0" />
                          <span className="text-amber-800">{note}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    );
  };

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header mit View-Toggle */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <CalendarIcon className="w-6 h-6 text-[#002f02]" />
              Reservierungskalender
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              {viewMode === 'week' ? 'Wochenübersicht' : 'Tagesdetails'}
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            {/* View Toggle */}
            <div className="flex bg-gray-100 rounded-lg p-1">
              <Button 
                variant={viewMode === 'day' ? 'default' : 'ghost'} 
                size="sm"
                onClick={() => setViewMode('day')}
                className={viewMode === 'day' ? 'bg-[#002f02] text-white' : ''}
              >
                <CalendarDays className="w-4 h-4 mr-1" />
                Tag
              </Button>
              <Button 
                variant={viewMode === 'week' ? 'default' : 'ghost'} 
                size="sm"
                onClick={() => setViewMode('week')}
                className={viewMode === 'week' ? 'bg-[#002f02] text-white' : ''}
              >
                <CalendarRange className="w-4 h-4 mr-1" />
                Woche
              </Button>
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/settings/opening-hours')}
            >
              <Settings className="w-4 h-4 mr-1" />
              Einstellungen
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={viewMode === 'week' ? goToPrevWeek : goToPrevDay}>
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={goToToday}>
                  Heute
                </Button>
                <Button variant="outline" size="sm" onClick={viewMode === 'week' ? goToNextWeek : goToNextDay}>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="text-center">
                {viewMode === 'week' ? (
                  <>
                    <div className="text-lg font-semibold text-gray-900">
                      KW {weekNumber} / {new Date(weekDates[0]).getFullYear()}
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatDate(weekDates[0])} – {formatDate(weekDates[6])}
                    </div>
                  </>
                ) : (
                  <div className="text-lg font-semibold text-gray-900">
                    {formatDateLong(selectedDate)}
                  </div>
                )}
              </div>
              
              {/* Legende - nur in Wochenansicht */}
              {viewMode === 'week' && (
                <div className="flex items-center gap-4 text-xs">
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-green-600 rounded"></div>
                    <span>Offen</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-3 h-3 bg-gray-400 rounded"></div>
                    <span>Geschlossen</span>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#002f02]"></div>
          </div>
        )}

        {/* Content */}
        {!loading && !error && (
          viewMode === 'week' ? (
            // ========== WOCHENANSICHT ==========
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7 gap-4">
              {weekDates.map((dateStr, index) => (
                <WeekDayCard key={dateStr} dateStr={dateStr} index={index} />
              ))}
            </div>
          ) : (
            // ========== TAGESANSICHT ==========
            <DayDetailView />
          )
        )}

        {/* Statistik - nur in Wochenansicht */}
        {!loading && !error && viewMode === 'week' && (
          <Card>
            <CardContent className="p-4">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-green-600">
                    {weekDates.filter(d => slotsData[d]?.open !== false && openingHours[d]?.is_open !== false).length}
                  </div>
                  <div className="text-sm text-gray-500">Tage geöffnet</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-gray-600">
                    {weekDates.filter(d => slotsData[d]?.open === false || openingHours[d]?.is_open === false).length}
                  </div>
                  <div className="text-sm text-gray-500">Tage geschlossen</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-[#002f02]">
                    {Object.values(reservationCounts).reduce((a, b) => a + b, 0)}
                  </div>
                  <div className="text-sm text-gray-500">Reservierungen gesamt</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">
                    {Math.round(Object.values(reservationCounts).reduce((a, b) => a + b, 0) / 7)}
                  </div>
                  <div className="text-sm text-gray-500">Ø pro Tag</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
}
