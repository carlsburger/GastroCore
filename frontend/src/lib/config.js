// Zentrale API-Konfiguration für alle Seiten
// Verwendet relative URLs für externe Zugriffe (Kubernetes Ingress)

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || "";

// Für API-Aufrufe: Wenn keine BACKEND_URL gesetzt ist, verwende relative URL
export const getApiUrl = (path) => {
  if (BACKEND_URL) {
    return `${BACKEND_URL}${path}`;
  }
  // Relative URL - funktioniert mit Kubernetes Ingress
  return path;
};

// Basis-URL für direkte Verwendung
export const API_BASE_URL = BACKEND_URL || "";

export default { getApiUrl, API_BASE_URL };
