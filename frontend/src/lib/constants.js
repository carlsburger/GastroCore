/**
 * ZENTRALE KONSTANTEN - GastroCore / Carlsburg Cockpit
 * 
 * WICHTIG: Diese Datei ist die EINZIGE Quelle für:
 * - Branding (Restaurant-Name)
 * - Wochentage (deutsch)
 * - Bereichs-Abkürzungen
 * 
 * KEINE Hardcodes in anderen Dateien!
 */

// ============================================================
// BRANDING
// ============================================================
export const BRANDING = {
  // Restaurant-Name (IMMER mit C, nicht K!)
  RESTAURANT_NAME: "Carlsburg",
  RESTAURANT_FULL: "Carlsburg Historisches Panoramarestaurant",
  COCKPIT_NAME: "Carlsburg Cockpit",
  
  // Logo URL
  LOGO_URL: "https://customer-assets.emergentagent.com/job_table-planner-4/artifacts/87kb0tcl_grafik.png",
  
  // Copyright
  COPYRIGHT: `© ${new Date().getFullYear()} Carlsburg Historisches Panoramarestaurant`,
};

// ============================================================
// WOCHENTAGE - DEUTSCH (VERBINDLICH)
// ============================================================
// Kurzform: Index 0 = Montag, 6 = Sonntag
export const DAYS_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"];

// Langform
export const DAYS_FULL = [
  "Montag",
  "Dienstag", 
  "Mittwoch",
  "Donnerstag",
  "Freitag",
  "Samstag",
  "Sonntag"
];

// Uppercase Version
export const DAYS_UPPER = ["MO", "DI", "MI", "DO", "FR", "SA", "SO"];

// Helper: JavaScript Date.getDay() gibt 0=Sonntag zurück
// Diese Funktion konvertiert zu unserem Format (0=Montag)
export const getDayIndex = (date) => {
  const jsDay = date.getDay(); // 0=So, 1=Mo, ..., 6=Sa
  return jsDay === 0 ? 6 : jsDay - 1; // 0=Mo, ..., 6=So
};

// Helper: Wochentag-Name für ein Datum
export const getDayName = (date, format = "short") => {
  const idx = getDayIndex(date);
  if (format === "full") return DAYS_FULL[idx];
  if (format === "upper") return DAYS_UPPER[idx];
  return DAYS_SHORT[idx];
};

// ============================================================
// BEREICHS-ABKÜRZUNGEN
// ============================================================
export const AREA_ABBR = {
  "Service": "SVC",
  "Küche": "KÜ",
  "Bar": "BAR",
  "Aushilfe": "AUS",
  "Event": "EVT",
  "Reinigung": "REI",
  // Fallback
  "default": "—"
};

export const getAreaAbbr = (areaName) => {
  return AREA_ABBR[areaName] || AREA_ABBR.default;
};

// ============================================================
// BESCHÄFTIGUNGS-ABKÜRZUNGEN
// ============================================================
export const EMPLOYMENT_ABBR = {
  "vollzeit": "VZ",
  "teilzeit": "TZ",
  "minijob": "MJ",
  "selbststaendig": "SE",
  "werkstudent": "WS",
  "default": "—"
};

export const getEmploymentAbbr = (type) => {
  return EMPLOYMENT_ABBR[type?.toLowerCase()] || EMPLOYMENT_ABBR.default;
};

// ============================================================
// NAMEN-FORMATIERUNG (ZENTRAL)
// ============================================================
/**
 * Formatiert einen Mitarbeiternamen nach der verbindlichen Reihenfolge:
 * 1. full_name (wenn vorhanden)
 * 2. first_name[0]. last_name (z.B. "A. Caban")
 * 3. display_name (Fallback)
 * 4. "N.N." (letzter Fallback)
 */
export const formatStaffName = (staff, format = "short") => {
  if (!staff) return "N.N.";
  
  const fullName = staff.full_name;
  const firstName = staff.first_name || "";
  const lastName = staff.last_name || "";
  const displayName = staff.display_name;
  
  // Priorität 1: full_name
  if (fullName && fullName.trim()) {
    if (format === "full") return fullName.trim();
    // Short format: "A. Caban"
    const parts = fullName.trim().split(" ");
    if (parts.length >= 2) {
      return `${parts[0][0]}. ${parts.slice(1).join(" ")}`;
    }
    return fullName.trim();
  }
  
  // Priorität 2: first_name + last_name
  if (firstName || lastName) {
    if (format === "full") return `${firstName} ${lastName}`.trim();
    // Short format
    if (firstName && lastName) {
      return `${firstName[0]}. ${lastName}`;
    }
    return (firstName || lastName).trim();
  }
  
  // Priorität 3: display_name
  if (displayName && displayName.trim()) {
    return displayName.trim();
  }
  
  // Fallback
  return "N.N.";
};

// ============================================================
// EVENT-KATEGORIEN
// ============================================================
export const EVENT_CATEGORIES = {
  AKTION: "aktion",
  MENU_AKTION: "menu_aktion",
  VERANSTALTUNG: "veranstaltung",
  EVENT: "event",
  KULTUR: "kultur"
};

// Mapping für API-Kategorisierung
export const categorizeEvent = (event) => {
  const category = (event.category || "").toLowerCase();
  const type = (event.type || "").toLowerCase();
  const eventType = (event.event_type || "").toLowerCase();
  
  // Aktionen
  if (category === "aktion" || type === "aktion") {
    return EVENT_CATEGORIES.AKTION;
  }
  
  // Menü-Aktionen
  if (category === "menüaktion" || category === "menu_aktion" || 
      type === "menüaktion" || type === "menu_aktion") {
    return EVENT_CATEGORIES.MENU_AKTION;
  }
  
  // Events/Veranstaltungen
  if (eventType === "kultur" || eventType === "event" || 
      category === "event" || type === "event") {
    return EVENT_CATEGORIES.VERANSTALTUNG;
  }
  
  // Default: Veranstaltung
  return EVENT_CATEGORIES.VERANSTALTUNG;
};

export default {
  BRANDING,
  DAYS_SHORT,
  DAYS_FULL,
  DAYS_UPPER,
  getDayIndex,
  getDayName,
  AREA_ABBR,
  getAreaAbbr,
  EMPLOYMENT_ABBR,
  getEmploymentAbbr,
  formatStaffName,
  EVENT_CATEGORIES,
  categorizeEvent
};
