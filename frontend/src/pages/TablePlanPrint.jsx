import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { format } from 'date-fns';
import { de } from 'date-fns/locale';
import { 
  Cake, 
  AlertTriangle, 
  Leaf, 
  Timer, 
  Users,
  Clock,
  MapPin,
  Phone,
  Mail,
  FileText
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

// Status-Farben für Druck
const STATUS_COLORS = {
  frei: 'bg-green-100 border-green-400',
  reserviert: 'bg-yellow-100 border-yellow-400',
  belegt: 'bg-red-100 border-red-400',
  gesperrt: 'bg-gray-200 border-gray-400',
};

const STATUS_LABELS = {
  frei: 'Frei',
  reserviert: 'Reserviert',
  belegt: 'Belegt',
  gesperrt: 'Gesperrt',
};

export default function TablePlanPrint() {
  const [searchParams] = useSearchParams();
  const date = searchParams.get('date') || format(new Date(), 'yyyy-MM-dd');
  const slot = searchParams.get('slot') || 'all';
  
  const [tables, setTables] = useState([]);
  const [occupancy, setOccupancy] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const token = localStorage.getItem('token');
  const getHeaders = () => ({ Authorization: `Bearer ${token}` });

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const timeSlotParam = slot !== 'all' ? slot : undefined;
        
        const [tablesRes, occupancyRes, reservationsRes] = await Promise.all([
          axios.get(`${BACKEND_URL}/api/tables`, {
            headers: getHeaders(),
            params: { active_only: true }
          }),
          axios.get(`${BACKEND_URL}/api/tables/occupancy/${date}`, {
            headers: getHeaders(),
            params: { time_slot: timeSlotParam }
          }),
          axios.get(`${BACKEND_URL}/api/reservations`, {
            headers: getHeaders(),
            params: { date }
          })
        ]);

        setTables(tablesRes.data);
        setOccupancy(occupancyRes.data.occupancy || []);
        setReservations(reservationsRes.data.filter(r => 
          !r.archived && r.status !== 'storniert'
        ));
      } catch (err) {
        console.error('Fehler beim Laden:', err);
        setError('Daten konnten nicht geladen werden');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [date, slot, token]);

  // Auto-Print nach Laden
  useEffect(() => {
    if (!loading && !error) {
      setTimeout(() => {
        window.print();
      }, 500);
    }
  }, [loading, error]);

  const getTableOccupancy = (tableId) => {
    return occupancy.find(o => o.table_id === tableId) || { status: 'frei' };
  };

  const getSpecialIndicators = (reservation) => {
    if (!reservation) return [];
    const indicators = [];
    
    if (reservation.occasion?.toLowerCase().includes('geburtstag') || 
        reservation.notes?.toLowerCase().includes('geburtstag')) {
      indicators.push({ icon: Cake, label: 'Geburtstag', color: 'text-pink-600' });
    }
    if (reservation.allergies || reservation.notes?.toLowerCase().includes('allergi')) {
      indicators.push({ icon: AlertTriangle, label: 'Allergien', color: 'text-orange-600' });
    }
    if (reservation.menu_choice?.toLowerCase().includes('veget') || 
        reservation.notes?.toLowerCase().includes('vegan')) {
      indicators.push({ icon: Leaf, label: 'Vegetarisch', color: 'text-green-600' });
    }
    if (reservation.is_extended) {
      indicators.push({ icon: Timer, label: 'Verlängert', color: 'text-blue-600' });
    }
    
    return indicators;
  };

  // Gruppiere Tische nach Bereich
  const groupedTables = tables.reduce((acc, table) => {
    const area = table.area || 'sonstige';
    const subArea = table.sub_area || '';
    const key = subArea ? `${area}_${subArea}` : area;
    
    if (!acc[key]) {
      acc[key] = {
        area,
        subArea,
        label: subArea ? `${area} - ${subArea}` : area,
        tables: []
      };
    }
    acc[key].tables.push(table);
    return acc;
  }, {});

  // Statistiken
  const stats = {
    total: occupancy.length,
    frei: occupancy.filter(o => o.status === 'frei').length,
    reserviert: occupancy.filter(o => o.status === 'reserviert').length,
    belegt: occupancy.filter(o => o.status === 'belegt').length,
    gesperrt: occupancy.filter(o => o.status === 'gesperrt').length,
    guests: reservations.reduce((sum, r) => sum + (r.party_size || 0), 0)
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4">Lade Tischplan...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center text-red-600">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  const dateFormatted = format(new Date(date), 'EEEE, dd. MMMM yyyy', { locale: de });

  return (
    <div className="print-page p-4 max-w-[297mm] mx-auto">
      {/* Print Styles */}
      <style>{`
        @media print {
          @page {
            size: A4 landscape;
            margin: 10mm;
          }
          body {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
          }
          .no-print {
            display: none !important;
          }
          .print-page {
            max-width: 100% !important;
          }
        }
        .print-page {
          font-family: system-ui, -apple-system, sans-serif;
        }
      `}</style>

      {/* Header */}
      <div className="border-b-2 border-gray-800 pb-4 mb-4">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-2xl font-bold">Tischplan</h1>
            <p className="text-lg">{dateFormatted}</p>
            <p className="text-gray-600">
              Zeitfenster: {slot === 'all' ? 'Alle Zeiten' : slot}
            </p>
          </div>
          <div className="text-right text-sm text-gray-600">
            <p>Carlsburg Restaurant</p>
            <p>Druck: {format(new Date(), 'dd.MM.yyyy HH:mm')}</p>
          </div>
        </div>

        {/* Statistik-Leiste */}
        <div className="flex gap-6 mt-4 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-green-400 rounded"></div>
            <span>Frei: {stats.frei}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-yellow-400 rounded"></div>
            <span>Reserviert: {stats.reserviert}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-red-400 rounded"></div>
            <span>Belegt: {stats.belegt}</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-4 h-4 bg-gray-400 rounded"></div>
            <span>Gesperrt: {stats.gesperrt}</span>
          </div>
          <div className="ml-auto font-semibold">
            <Users className="inline h-4 w-4 mr-1" />
            {stats.guests} Gäste erwartet
          </div>
        </div>
      </div>

      {/* Tisch-Tabelle nach Bereichen */}
      {Object.entries(groupedTables).map(([key, group]) => (
        <div key={key} className="mb-6">
          <h2 className="text-lg font-semibold mb-2 capitalize flex items-center gap-2">
            <MapPin className="h-4 w-4" />
            {group.label}
          </h2>
          
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left w-16">Tisch</th>
                <th className="border p-2 text-left w-16">Plätze</th>
                <th className="border p-2 text-left w-24">Status</th>
                <th className="border p-2 text-left">Gast</th>
                <th className="border p-2 text-left w-16">Zeit</th>
                <th className="border p-2 text-left w-16">Pers.</th>
                <th className="border p-2 text-left">Hinweise</th>
              </tr>
            </thead>
            <tbody>
              {group.tables
                .sort((a, b) => {
                  const numA = parseFloat(a.table_number) || 0;
                  const numB = parseFloat(b.table_number) || 0;
                  return numA - numB;
                })
                .map(table => {
                  const occ = getTableOccupancy(table.id);
                  const reservation = occ.reservation;
                  const indicators = getSpecialIndicators(reservation);
                  
                  return (
                    <tr 
                      key={table.id} 
                      className={`${STATUS_COLORS[occ.status]} border`}
                    >
                      <td className="border p-2 font-bold">{table.table_number}</td>
                      <td className="border p-2">{table.seats_max}</td>
                      <td className="border p-2">{STATUS_LABELS[occ.status]}</td>
                      <td className="border p-2">
                        {reservation?.guest_name || '-'}
                        {reservation?.phone && (
                          <span className="text-xs text-gray-500 ml-2">
                            <Phone className="inline h-3 w-3" /> {reservation.phone}
                          </span>
                        )}
                      </td>
                      <td className="border p-2">{reservation?.time || '-'}</td>
                      <td className="border p-2">{reservation?.party_size || '-'}</td>
                      <td className="border p-2">
                        <div className="flex items-center gap-2">
                          {indicators.map((ind, i) => (
                            <span key={i} className={`${ind.color} text-xs`}>
                              <ind.icon className="inline h-3 w-3 mr-1" />
                              {ind.label}
                            </span>
                          ))}
                          {reservation?.notes && (
                            <span className="text-xs text-gray-600 truncate max-w-[150px]">
                              {reservation.notes}
                            </span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      ))}

      {/* Reservierungsliste (Extra) */}
      {reservations.length > 0 && (
        <div className="mt-8 pt-4 border-t-2 border-gray-800">
          <h2 className="text-lg font-semibold mb-2 flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Reservierungsliste ({reservations.length})
          </h2>
          
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Zeit</th>
                <th className="border p-2 text-left">Gast</th>
                <th className="border p-2 text-left">Pers.</th>
                <th className="border p-2 text-left">Tisch</th>
                <th className="border p-2 text-left">Kontakt</th>
                <th className="border p-2 text-left">Status</th>
                <th className="border p-2 text-left">Notizen</th>
              </tr>
            </thead>
            <tbody>
              {reservations
                .sort((a, b) => (a.time || '').localeCompare(b.time || ''))
                .map(res => (
                  <tr key={res.id} className="border">
                    <td className="border p-2 font-medium">{res.time}</td>
                    <td className="border p-2">{res.guest_name}</td>
                    <td className="border p-2">{res.party_size}</td>
                    <td className="border p-2">{res.table_numbers?.join(', ') || '-'}</td>
                    <td className="border p-2 text-xs">
                      {res.phone && <div><Phone className="inline h-3 w-3" /> {res.phone}</div>}
                      {res.email && <div><Mail className="inline h-3 w-3" /> {res.email}</div>}
                    </td>
                    <td className="border p-2">{res.status}</td>
                    <td className="border p-2 text-xs truncate max-w-[200px]">
                      {res.notes || res.occasion || '-'}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer */}
      <div className="mt-8 pt-4 border-t text-center text-xs text-gray-500 no-print">
        <button 
          onClick={() => window.print()}
          className="bg-gray-800 text-white px-4 py-2 rounded hover:bg-gray-700 mr-4"
        >
          🖨️ Drucken
        </button>
        <button 
          onClick={() => window.close()}
          className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400"
        >
          Schließen
        </button>
      </div>
    </div>
  );
}
