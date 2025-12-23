import React, { useState, useEffect, useMemo } from 'react';
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
  Settings
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

const API_URL = import.meta.env.REACT_APP_BACKEND_URL || process.env.REACT_APP_BACKEND_URL || '';

// Hilfsfunktionen
const getWeekDates = (date) => {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1); // Montag als Start
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

const getWeekNumber = (dateStr) => {
  const date = new Date(dateStr);
  const firstDayOfYear = new Date(date.getFullYear(), 0, 1);
  const pastDaysOfYear = (date - firstDayOfYear) / 86400000;
  return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
};

const WEEKDAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'];

export default function ReservationCalendar() {
  const navigate = useNavigate();
  const [currentDate, setCurrentDate] = useState(new Date());
  const [openingHours, setOpeningHours] = useState({});
  const [slotsData, setSlotsData] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const weekDates = useMemo(() => getWeekDates(currentDate), [currentDate]);
  const weekNumber = useMemo(() => getWeekNumber(weekDates[0]), [weekDates]);

  // Token aus localStorage
  const getToken = () => localStorage.getItem('token');

  // Daten laden
  const fetchData = async () => {
    setLoading(true);
    setError(null);

    const token = getToken();
    if (!token) {
      setError('Nicht eingeloggt');
      setLoading(false);
      return;
    }

    const fromDate = weekDates[0];
    const toDate = weekDates[6];

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
    } catch (err) {
      console.error('Fehler beim Laden:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [weekDates]);

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

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  // Tages-Kachel Komponente
  const DayCard = ({ dateStr, index }) => {
    const hours = openingHours[dateStr] || {};
    const slots = slotsData[dateStr] || {};
    
    const isOpen = hours.is_open !== false && slots.open !== false;
    const isClosed = !isOpen;
    const isToday = dateStr === new Date().toISOString().split('T')[0];
    
    // Öffnungszeiten extrahieren
    const blocks = hours.blocks || [];
    const openTime = blocks.length > 0 ? blocks[0].start : null;
    const closeTime = blocks.length > 0 ? blocks[blocks.length - 1].end : null;
    
    // Slots & Blocked
    const slotsList = slots.slots || [];
    const blockedWindows = slots.blocked || [];
    const notes = slots.notes || [];
    
    // Closure Reason
    const closureReason = hours.closure_reason || (isClosed ? 'Geschlossen' : null);
    
    // Feiertag
    const isHoliday = hours.is_holiday;
    const holidayName = hours.holiday_name;

    return (
      <Card className={`
        h-full transition-all duration-200
        ${isToday ? 'ring-2 ring-blue-500 bg-blue-50/50' : ''}
        ${isClosed ? 'bg-gray-100 opacity-80' : 'hover:shadow-md'}
      `}>
        <CardHeader className="pb-2 pt-3 px-3">
          {/* Datum & Wochentag */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-semibold ${isToday ? 'text-blue-600' : 'text-gray-600'}`}>
                {WEEKDAYS[index]}
              </span>
              <span className={`text-lg font-bold ${isToday ? 'text-blue-700' : ''}`}>
                {formatDate(dateStr)}
              </span>
            </div>
            
            {/* Status Badge */}
            {isClosed ? (
              <Badge variant="destructive" className="text-xs">
                <XCircle className="w-3 h-3 mr-1" />
                GESCHLOSSEN
              </Badge>
            ) : (
              <Badge variant="default" className="bg-green-600 text-xs">
                <CheckCircle className="w-3 h-3 mr-1" />
                OFFEN
              </Badge>
            )}
          </div>
          
          {/* Feiertag */}
          {isHoliday && (
            <div className="mt-1">
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300 text-xs">
                🎉 {holidayName}
              </Badge>
            </div>
          )}
          
          {/* Periode */}
          {hours.period_name && (
            <div className="text-xs text-gray-500 mt-1">
              Periode: {hours.period_name}
            </div>
          )}
        </CardHeader>
        
        <CardContent className="px-3 pb-3">
          {isClosed ? (
            <div className="text-center py-4">
              <div className="text-gray-500 text-sm">{closureReason}</div>
            </div>
          ) : (
            <>
              {/* Öffnungszeiten */}
              {openTime && closeTime && (
                <div className="flex items-center gap-1 text-sm text-gray-600 mb-2">
                  <Clock className="w-4 h-4" />
                  <span className="font-medium">{openTime} – {closeTime}</span>
                </div>
              )}
              
              {/* Blocked Windows */}
              {blockedWindows.length > 0 && (
                <div className="mb-2">
                  {blockedWindows.map((bw, idx) => (
                    <TooltipProvider key={idx}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <div className="bg-red-100 border border-red-300 rounded px-2 py-1 text-xs text-red-700 mb-1 flex items-center gap-1">
                            <AlertCircle className="w-3 h-3" />
                            <span className="font-medium">{bw.start}–{bw.end}</span>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{bw.reason || 'Sperrfenster'}</p>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ))}
                </div>
              )}
              
              {/* Slots */}
              <div className="flex flex-wrap gap-1">
                {slotsList.map((slot, idx) => (
                  <Badge 
                    key={idx} 
                    variant="outline" 
                    className="text-xs bg-white hover:bg-gray-50 cursor-default"
                  >
                    {slot}
                  </Badge>
                ))}
                {slotsList.length === 0 && (
                  <span className="text-xs text-gray-400">Keine Slots</span>
                )}
              </div>
              
              {/* Notes */}
              {notes.length > 0 && (
                <div className="mt-2 pt-2 border-t">
                  {notes.map((note, idx) => (
                    <div key={idx} className="flex items-start gap-1 text-xs text-amber-700 bg-amber-50 rounded p-1 mb-1">
                      <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                      <span>{note}</span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-6">
      {/* Header */}
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <CalendarIcon className="w-6 h-6 text-blue-600" />
              Öffnungszeiten & Slots Kalender
            </h1>
            <p className="text-gray-500 text-sm mt-1">
              Übersicht der Reservierungsmöglichkeiten pro Tag
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/admin/reservations/settings')}
            >
              <Settings className="w-4 h-4 mr-1" />
              Einstellungen
            </Button>
          </div>
        </div>

        {/* Navigation */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={goToPrevWeek}>
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={goToToday}>
                Heute
              </Button>
              <Button variant="outline" size="sm" onClick={goToNextWeek}>
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="text-center">
              <div className="text-lg font-semibold text-gray-900">
                KW {weekNumber} / {new Date(weekDates[0]).getFullYear()}
              </div>
              <div className="text-sm text-gray-500">
                {formatDate(weekDates[0])} – {formatDate(weekDates[6])}
              </div>
            </div>
            
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-green-600 rounded"></div>
                <span>Offen</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-500 rounded"></div>
                <span>Geschlossen</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-3 h-3 bg-red-200 border border-red-300 rounded"></div>
                <span>Sperrfenster</span>
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-600" />
            <span className="text-red-700">{error}</span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          </div>
        )}

        {/* Wochenansicht */}
        {!loading && !error && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-4">
            {weekDates.map((dateStr, index) => (
              <DayCard key={dateStr} dateStr={dateStr} index={index} />
            ))}
          </div>
        )}

        {/* Statistik */}
        {!loading && !error && (
          <div className="mt-6 bg-white rounded-lg shadow-sm p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div>
                <div className="text-2xl font-bold text-green-600">
                  {weekDates.filter(d => slotsData[d]?.open !== false).length}
                </div>
                <div className="text-sm text-gray-500">Tage offen</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-600">
                  {weekDates.filter(d => slotsData[d]?.open === false).length}
                </div>
                <div className="text-sm text-gray-500">Tage geschlossen</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-blue-600">
                  {weekDates.reduce((sum, d) => sum + (slotsData[d]?.slots?.length || 0), 0)}
                </div>
                <div className="text-sm text-gray-500">Slots gesamt</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-amber-600">
                  {weekDates.reduce((sum, d) => sum + (slotsData[d]?.blocked?.length || 0), 0)}
                </div>
                <div className="text-sm text-gray-500">Sperrfenster</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
