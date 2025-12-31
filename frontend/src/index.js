import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

// DEBUG: Log sehr früh um zu prüfen ob das Bundle geladen wird
console.log('[index.js] React App wird gestartet');
console.log('[index.js] Aktueller Pfad:', window.location.pathname);
console.log('[index.js] Komplette URL:', window.location.href);

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
