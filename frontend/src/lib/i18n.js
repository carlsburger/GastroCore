// i18n - German translations (prepared for multi-language support)
const translations = {
  de: {
    // Navigation
    nav: {
      dashboard: "Dashboard",
      reservations: "Reservierungen",
      areas: "Bereiche",
      users: "Benutzer",
      auditLog: "Audit-Log",
      settings: "Einstellungen",
      logout: "Abmelden",
      waitlist: "Warteliste",
      guests: "Gäste",
      messageLogs: "Nachrichten",
    },
    // Auth
    auth: {
      login: "Anmelden",
      email: "E-Mail",
      password: "Passwort",
      loginButton: "Anmelden",
      changePassword: "Passwort ändern",
      currentPassword: "Aktuelles Passwort",
      newPassword: "Neues Passwort",
      confirmPassword: "Passwort bestätigen",
      passwordChanged: "Passwort erfolgreich geändert",
      mustChangePassword: "Bitte ändern Sie Ihr Passwort beim ersten Login",
      invalidCredentials: "Ungültige Anmeldedaten",
    },
    // Reservations
    reservations: {
      title: "Reservierungen",
      today: "Heute",
      newReservation: "Neue Reservierung",
      guestName: "Gastname",
      phone: "Telefon",
      email: "E-Mail",
      partySize: "Personenzahl",
      date: "Datum",
      time: "Uhrzeit",
      area: "Bereich",
      status: "Status",
      notes: "Notizen",
      search: "Suche nach Name oder Telefon...",
      noReservations: "Keine Reservierungen gefunden",
      confirmDelete: "Reservierung wirklich archivieren?",
    },
    // Status
    status: {
      neu: "Neu",
      bestaetigt: "Bestätigt",
      angekommen: "Angekommen",
      abgeschlossen: "Abgeschlossen",
      no_show: "No-Show",
      storniert: "Storniert",
    },
    // Areas
    areas: {
      title: "Bereiche",
      newArea: "Neuer Bereich",
      name: "Name",
      description: "Beschreibung",
      capacity: "Kapazität",
      confirmDelete: "Bereich wirklich archivieren?",
    },
    // Users
    users: {
      title: "Benutzer",
      newUser: "Neuer Benutzer",
      name: "Name",
      email: "E-Mail",
      role: "Rolle",
      roles: {
        admin: "Administrator",
        schichtleiter: "Schichtleiter",
        mitarbeiter: "Mitarbeiter",
      },
      confirmDelete: "Benutzer wirklich archivieren?",
    },
    // Audit Log
    audit: {
      title: "Audit-Log",
      actor: "Akteur",
      entity: "Entität",
      action: "Aktion",
      timestamp: "Zeitpunkt",
      before: "Vorher",
      after: "Nachher",
      actions: {
        create: "Erstellt",
        update: "Aktualisiert",
        archive: "Archiviert",
        status_change: "Status geändert",
        password_change: "Passwort geändert",
      },
    },
    // Common
    common: {
      save: "Speichern",
      cancel: "Abbrechen",
      delete: "Löschen",
      edit: "Bearbeiten",
      create: "Erstellen",
      loading: "Laden...",
      error: "Fehler",
      success: "Erfolgreich",
      noData: "Keine Daten vorhanden",
      all: "Alle",
      filter: "Filtern",
      refresh: "Aktualisieren",
      persons: "Personen",
    },
  },
};

// Current language (can be extended for language switching)
let currentLang = "de";

export const t = (key) => {
  const keys = key.split(".");
  let value = translations[currentLang];
  
  for (const k of keys) {
    if (value && typeof value === "object" && k in value) {
      value = value[k];
    } else {
      console.warn(`Translation not found: ${key}`);
      return key;
    }
  }
  
  return value;
};

export const setLanguage = (lang) => {
  if (translations[lang]) {
    currentLang = lang;
  }
};

export const getCurrentLanguage = () => currentLang;

export default translations;
