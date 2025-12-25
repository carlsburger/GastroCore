/**
 * GastroCore API Types
 * =====================
 * Zentrale Type-Definitionen für konsistente API-Kommunikation
 * 
 * Version: 1.0.0
 * Datum: 2025-12-25
 */

/**
 * API Error Codes (entspricht Backend ApiErrorCode Enum)
 * @readonly
 * @enum {string}
 */
export const ApiErrorCode = {
  STAFF_NOT_LINKED: 'STAFF_NOT_LINKED',
  NO_SHIFTS_ASSIGNED: 'NO_SHIFTS_ASSIGNED',
  INVALID_ROLE: 'INVALID_ROLE',
  NOT_AUTHENTICATED: 'NOT_AUTHENTICATED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  CONFLICT: 'CONFLICT',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
};

/**
 * Mapping von Error Codes zu deutschen Meldungen
 */
export const ErrorMessages = {
  [ApiErrorCode.STAFF_NOT_LINKED]: 'Kein Mitarbeiterprofil verknüpft. Bitte wende dich an die Schichtleitung.',
  [ApiErrorCode.NO_SHIFTS_ASSIGNED]: 'Keine Schichten für diesen Zeitraum vorhanden.',
  [ApiErrorCode.INVALID_ROLE]: 'Ungültige Benutzerrolle.',
  [ApiErrorCode.NOT_AUTHENTICATED]: 'Nicht angemeldet. Bitte erneut einloggen.',
  [ApiErrorCode.FORBIDDEN]: 'Keine Berechtigung für diese Aktion.',
  [ApiErrorCode.NOT_FOUND]: 'Die angeforderte Ressource wurde nicht gefunden.',
  [ApiErrorCode.VALIDATION_ERROR]: 'Ungültige Eingabe. Bitte überprüfe deine Daten.',
  [ApiErrorCode.CONFLICT]: 'Konflikt mit bestehenden Daten.',
  [ApiErrorCode.INTERNAL_ERROR]: 'Ein interner Fehler ist aufgetreten. Bitte versuche es später erneut.',
};

/**
 * Prüft ob eine API-Response das neue standardisierte Format hat
 * @param {object} response - API Response
 * @returns {boolean}
 */
export const isStandardResponse = (response) => {
  return response && typeof response === 'object' && 'success' in response;
};

/**
 * Extrahiert Daten aus einer API-Response (kompatibel mit altem und neuem Format)
 * @param {object} response - API Response
 * @returns {any} Die Daten oder die Response selbst
 */
export const extractData = (response) => {
  if (isStandardResponse(response)) {
    return response.data;
  }
  // Fallback für altes Format (Array oder Object direkt)
  return response;
};

/**
 * Prüft ob eine Response einen spezifischen Error Code hat
 * @param {object} response - API Response
 * @param {string} errorCode - ApiErrorCode
 * @returns {boolean}
 */
export const hasErrorCode = (response, errorCode) => {
  return isStandardResponse(response) && response.error === errorCode;
};

/**
 * Gibt die Fehlermeldung für eine Response zurück
 * @param {object} response - API Response
 * @returns {string|null}
 */
export const getErrorMessage = (response) => {
  if (!isStandardResponse(response)) return null;
  
  // Zuerst die Response-Message, dann Error-Code-Mapping
  if (response.message) return response.message;
  if (response.error && ErrorMessages[response.error]) {
    return ErrorMessages[response.error];
  }
  return null;
};

/**
 * HTTP Status Code Regeln (Dokumentation)
 * 
 * | Situation                              | Status |
 * |----------------------------------------|--------|
 * | Erfolgreiche Anfrage                   | 200 OK |
 * | Fachlich leer (keine Daten)            | 200 OK |
 * | Nicht authentifiziert                  | 401    |
 * | Kein Zugriff                           | 403    |
 * | Ressource existiert nicht              | 404    |
 * | Technischer Fehler                     | 500    |
 * 
 * ⚠️ WICHTIG:
 * Ein Zustand wie "Kein Mitarbeiterprofil verknüpft" 
 * ist kein Fehler, sondern ein gültiger Zustand → 200 OK
 */

export default {
  ApiErrorCode,
  ErrorMessages,
  isStandardResponse,
  extractData,
  hasErrorCode,
  getErrorMessage,
};
