// Petits utilitaires d'interface. Tout le contenu dynamique passe par textContent :
// aucune donnée venant du serveur ou de l'utilisatrice n'est injectée comme HTML.

export function h(tag, attrs = {}, ...enfants) {
  const el = document.createElement(tag);
  for (const [cle, valeur] of Object.entries(attrs || {})) {
    if (valeur === false || valeur == null) continue;
    if (cle === "class") el.className = valeur;
    else if (cle.startsWith("on")) el.addEventListener(cle.slice(2), valeur);
    else if (cle === "html") el.innerHTML = valeur; // réservé aux icônes SVG statiques
    else el.setAttribute(cle, valeur === true ? "" : valeur);
  }
  for (const enfant of enfants.flat()) {
    if (enfant == null || enfant === false) continue;
    el.append(enfant instanceof Node ? enfant : document.createTextNode(String(enfant)));
  }
  return el;
}

export async function api(chemin, options = {}) {
  const reponse = await fetch(chemin, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`);
  return reponse.json();
}

const trait = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"';
const svg = (contenu) => `<svg viewBox="0 0 24 24" width="20" height="20" ${trait} aria-hidden="true">${contenu}</svg>`;

export const ICONES = {
  accueil: svg('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>'),
  chat: svg('<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.4A8 8 0 1 1 21 12Z"/>'),
  droits: svg('<path d="M12 3v18"/><path d="M5 7h14"/><path d="m5 7-3 7a3.5 3.5 0 0 0 6 0Z"/><path d="m19 7-3 7a3.5 3.5 0 0 0 6 0Z"/><path d="M8 21h8"/>'),
  aide: svg('<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2Z"/>'),
  bouclier: svg('<path d="M12 22s8-3.5 8-10V5l-8-3-8 3v7c0 6.5 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>'),
  graphique: svg('<path d="M3 3v18h18"/><path d="M7 15v3"/><path d="M12 10v8"/><path d="M17 6v12"/>'),
  envoyer: svg('<path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4Z"/>'),
  micro: svg('<rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 17v5"/>'),
  hautparleur: svg('<path d="M11 5 6 9H2v6h4l5 4Z"/><path d="M15.5 8.5a5 5 0 0 1 0 7"/><path d="M19 5a10 10 0 0 1 0 14"/>'),
  pouce: svg('<path d="M7 10v12"/><path d="M15 5.9 14 10h5.8a2 2 0 0 1 2 2.3l-1.4 8a2 2 0 0 1-2 1.7H7V10l4-8a3 3 0 0 1 3 3.9Z"/>'),
  poucebas: svg('<path d="M17 14V2"/><path d="M9 18.1 10 14H4.2a2 2 0 0 1-2-2.3l1.4-8A2 2 0 0 1 5.6 2H17v12l-4 8a3 3 0 0 1-3-3.9Z"/>'),
  recherche: svg('<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>'),
  fleche: svg('<path d="M5 12h14"/><path d="m13 6 6 6-6 6"/>'),
  retour: svg('<path d="M19 12H5"/><path d="m11 18-6-6 6-6"/>'),
  cadenas: svg('<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
  langues: svg('<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>'),
  coeur: svg('<path d="M19 14c1.5-1.5 3-3.2 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.8 0-3 .5-4.5 2-1.5-1.5-2.7-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4 3 5.5l7 7Z"/>'),
  horloge: svg('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
  imprimer: svg('<path d="M6 9V2h12v7"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>'),
  corbeille: svg('<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>'),
  alerte: svg('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'),
  sortie: svg('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  balance: svg('<path d="M12 3v18"/><path d="M7 21h10"/><path d="M4 7h16"/><path d="m4 7-2.5 6a3 3 0 0 0 5 0Z"/><path d="m20 7-2.5 6a3 3 0 0 0 5 0Z"/><circle cx="12" cy="4.5" r="1.5"/>'),
  utilisatrice: svg('<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>'),
  etoile: svg('<path d="m12 2 3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1Z"/>'),
  globe: svg('<circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3a14 14 0 0 1 0 18a14 14 0 0 1 0-18"/>'),
  document: svg('<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6"/><path d="M8 13h8"/><path d="M8 17h5"/>'),
  eclair: svg('<path d="M13 2 4 14h7l-1 8 9-12h-7Z"/>'),
  foyer: svg('<path d="M3 10.5 12 3l9 7.5V21H3Z"/><path d="M12 17.5s-3.5-2.1-3.5-4.4A1.9 1.9 0 0 1 12 12a1.9 1.9 0 0 1 3.5 1.1c0 2.3-3.5 4.4-3.5 4.4Z"/>'),
  telephone: svg('<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M11 18h2"/>'),
  famille: svg('<circle cx="8" cy="7" r="3"/><circle cx="17" cy="9" r="2.4"/><path d="M2.5 20a5.5 5.5 0 0 1 11 0"/><path d="M13.5 20a3.8 3.8 0 0 1 7.5 0"/>'),
  piece: svg('<circle cx="12" cy="12" r="9"/><path d="M14.5 9.5a2.5 2 0 0 0-2.5-1.5c-1.5 0-2.5.8-2.5 2s1.2 1.6 2.5 2 2.5.8 2.5 2-1 2-2.5 2a2.6 2 0 0 1-2.5-1.5"/><path d="M12 6v2"/><path d="M12 16v2"/>'),
  mallette: svg('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M3 13h18"/>'),
  marteau: svg('<path d="m14 13-8.5 8.5a2.1 2.1 0 0 1-3-3L11 10"/><path d="m16 16 6-6"/><path d="m8 8 6-6"/><path d="m9 7 8 8"/><path d="m21 11-8-8"/>'),
  lune: svg('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8Z"/>'),
  soleil: svg('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
  copier: svg('<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/>'),
  rejouer: svg('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/>'),
  carre: svg('<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor"/>'),
  liste: svg('<path d="M9 6h12"/><path d="M9 12h12"/><path d="M9 18h12"/><path d="m3 6 1 1 2-2"/><path d="m3 12 1 1 2-2"/><path d="m3 18 1 1 2-2"/>'),
};

export const icone = (nom, classe = "icone") => h("span", { class: classe, html: ICONES[nom] });

// Illustration originale (web/img/*.svg), servie par le site lui-même.
export const illustration = (nom, classe = "") =>
  h("div", { class: `illustration-3d ${classe}`, "aria-hidden": "true" },
    h("img", { src: `/static/img/${nom}.svg`, alt: "", loading: "lazy", decoding: "async" }));

// Transforme une réponse texte (lignes, puces « • ») en paragraphes et listes.
export function texteRiche(texte) {
  const bloc = h("div", { class: "texte-riche" });
  let liste = null;
  for (const ligne of texte.split("\n")) {
    const propre = ligne.trim();
    if (!propre) { liste = null; continue; }
    if (/^[•\-*]\s+/.test(propre)) {
      if (!liste) { liste = h("ul"); bloc.append(liste); }
      liste.append(h("li", { dir: "auto" }, propre.replace(/^[•\-*]\s+/, "")));
    } else {
      liste = null;
      bloc.append(h("p", { dir: "auto" }, propre));
    }
  }
  return bloc;
}
