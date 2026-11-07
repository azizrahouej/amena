// « Dossier pour mon avocat(e) » : un document clair à imprimer ou enregistrer en PDF.
// Tout est construit DANS le navigateur : rien n'est envoyé ni enregistré, et tout disparaît
// à la fermeture de l'onglet ou avec la sortie rapide. L'utilisatrice relit et complète avant
// d'imprimer.

import { langueCourante, t } from "../i18n.js";
import { api, h, icone } from "../ui.js";

const etat = {
  faits: "", pays: "TN", analyse: null, chronologie: [{ date: "", evenement: "" }],
  auteur: "", enfants: "", deja: new Set(), preuves: new Set(), questions: "",
};

// Appelée par le chat ou l'analyse : pré-remplit le dossier avec la situation et son analyse.
export function preparerDossier({ faits = "", analyse = null } = {}) {
  if (faits) etat.faits = etat.faits ? `${etat.faits}\n${faits}` : faits;
  if (analyse) etat.analyse = analyse;
}

const DEJA = ["dossier.d.certificat", "dossier.d.plainte", "dossier.d.ordonnance", "dossier.d.association", "dossier.d.depart"];
const QUESTIONS_TYPES = ["dossier.q1", "dossier.q2", "dossier.q3", "dossier.q4", "dossier.q5"];

function champ(libelle, element, aide = null) {
  return h("label", { class: "champ-groupe" }, h("span", { class: "libelle-dossier" }, libelle), element,
    aide ? h("small", {}, aide) : null);
}

function zoneTexte(cle, placeholder, lignes = 4) {
  const z = h("textarea", { class: "champ", rows: lignes, dir: "auto", placeholder });
  z.value = etat[cle];
  z.addEventListener("input", () => { etat[cle] = z.value; });
  return z;
}

// --- Le document imprimable ---------------------------------------------------------------
function documentDossier() {
  const a = etat.analyse;
  const aujourd_hui = new Date().toLocaleDateString(langueCourante() === "ar" ? "ar-TN" : "fr-FR",
    { day: "numeric", month: "long", year: "numeric" });
  // Numérotation automatique : les sections vides ne laissent pas de trou (1, 2, 3…).
  let numero = 0;
  const section = (titre, ...contenu) => h("section", { class: "doc-section" }, h("h2", {}, `${++numero}. ${titre}`), ...contenu);
  const liste = (elements, classe = "") => h("ul", { class: classe }, ...elements.map((x) => h("li", { dir: "auto" }, x)));

  const chrono = etat.chronologie.filter((l) => l.date || l.evenement);
  return h("article", { class: "document-dossier", id: "document-dossier" },
    h("header", { class: "doc-entete" },
      h("div", {}, h("p", { class: "doc-surtitre" }, t("dossier.doc.surtitre")), h("h1", {}, t("dossier.doc.titre")),
        h("p", { class: "doc-date" }, `${t("dossier.doc.date")} ${aujourd_hui}`)),
      h("span", { class: "doc-logo" }, icone("balance"))),
    h("p", { class: "doc-confidentiel" }, t("dossier.doc.confidentiel")),

    section(t("dossier.s.faits"), h("p", { class: "doc-faits", dir: "auto" }, etat.faits || t("dossier.vide"))),
    etat.auteur || etat.enfants ? section(t("dossier.s.personnes"),
      etat.auteur ? h("p", {}, h("strong", {}, `${t("dossier.auteur")} : `), etat.auteur) : null,
      etat.enfants ? h("p", {}, h("strong", {}, `${t("dossier.enfants")} : `), etat.enfants) : null) : null,
    chrono.length ? section(t("dossier.s.chronologie"),
      h("table", { class: "doc-table" }, h("thead", {}, h("tr", {}, h("th", {}, t("dossier.date")), h("th", {}, t("dossier.evenement")))),
        h("tbody", {}, ...chrono.map((l) => h("tr", {}, h("td", {}, l.date), h("td", { dir: "auto" }, l.evenement)))))) : null,

    a ? section(t("dossier.s.qualification"),
      ...a.qualifications.map((q) => h("div", { class: "doc-qualif" },
        h("h3", {}, q.libelle), h("p", {}, q.qualification),
        liste(q.fondements.map((f) => `${f.texte} — ${/^\d/.test(f.article) ? `art. ${f.article}` : f.titre} : ${f.contenu}`))))) : null,

    section(t("dossier.s.preuves"),
      etat.preuves.size ? liste([...etat.preuves].map((p) => `☑ ${p}`), "doc-coches") : h("p", {}, t("dossier.aucune.preuve")),
      a ? h("p", { class: "doc-note" }, h("strong", {}, `${t("dossier.preuves.manquantes")} : `),
        a.preuves.filter((p) => !etat.preuves.has(p)).join(" ; ") || "—") : null),

    section(t("dossier.s.deja"),
      etat.deja.size ? liste([...etat.deja].map((d) => `☑ ${t(d)}`), "doc-coches") : h("p", {}, t("dossier.rien.fait"))),

    a ? section(t("dossier.s.strategie"), h("ol", {}, ...a.demarches.map((d) => h("li", {}, d))),
      a.delais.length ? h("p", { class: "doc-note" }, h("strong", {}, `${t("analyse.delais")} : `), a.delais.join(" ; ")) : null) : null,
    a ? section(t("dossier.s.vigilance"), liste([...a.vigilance, ...a.limites_loi.map((l) => `${l.texte_titre} : ${l.contenu}`)])) : null,

    section(t("dossier.s.questions"), h("p", { class: "doc-faits", dir: "auto" }, etat.questions || "—")),

    h("footer", { class: "doc-pied" },
      h("p", {}, t("dossier.doc.pied1")),
      h("p", {}, t("dossier.doc.pied2"))));
}

// --- La page : formulaire à gauche, aperçu du document à droite ---------------------------------
export function pageDossier(racine) {
  const apercu = h("div", { class: "apercu-dossier" });
  const rafraichir = () => apercu.replaceChildren(documentDossier());

  const listePreuves = h("div", { class: "grille-interets" });
  const dessinerPreuves = () => {
    const proposees = etat.analyse?.preuves || [t("dossier.p1"), t("dossier.p2"), t("dossier.p3"), t("dossier.p4")];
    listePreuves.replaceChildren(...proposees.map((p) => {
      const c = h("input", { type: "checkbox", checked: etat.preuves.has(p), onchange: (e) => {
        if (e.target.checked) etat.preuves.add(p); else etat.preuves.delete(p);
        rafraichir();
      } });
      return h("label", {}, c, p);
    }));
  };

  const chronologie = h("div", { class: "chronologie" });
  const dessinerChronologie = () => {
    chronologie.replaceChildren(...etat.chronologie.map((ligne, i) => h("div", { class: "ligne-chrono" },
      h("input", { class: "champ", type: "date", value: ligne.date, "aria-label": t("dossier.date"),
                   oninput: (e) => { ligne.date = e.target.value; rafraichir(); } }),
      h("input", { class: "champ", dir: "auto", value: ligne.evenement, placeholder: t("dossier.evenement.ph"),
                   "aria-label": t("dossier.evenement"), oninput: (e) => { ligne.evenement = e.target.value; rafraichir(); } }),
      h("button", { class: "action-icone", type: "button", "aria-label": "✕", onclick: () => {
        etat.chronologie.splice(i, 1);
        if (!etat.chronologie.length) etat.chronologie.push({ date: "", evenement: "" });
        dessinerChronologie(); rafraichir();
      } }, icone("sortie")))),
      h("button", { class: "bouton bouton-fantome", type: "button", onclick: () => {
        etat.chronologie.push({ date: "", evenement: "" }); dessinerChronologie();
      } }, `+ ${t("dossier.ajouter")}`));
  };

  const faits = zoneTexte("faits", t("dossier.faits.ph"), 6);
  const questions = zoneTexte("questions", t("dossier.questions.ph"), 4);
  if (!etat.questions) {
    etat.questions = QUESTIONS_TYPES.map((q) => `- ${t(q)}`).join("\n");
    questions.value = etat.questions;
  }
  const auteur = h("input", { class: "champ", dir: "auto", value: etat.auteur, placeholder: t("dossier.auteur.ph"),
                              oninput: (e) => { etat.auteur = e.target.value; rafraichir(); } });
  const enfants = h("input", { class: "champ", dir: "auto", value: etat.enfants, placeholder: t("dossier.enfants.ph"),
                               oninput: (e) => { etat.enfants = e.target.value; rafraichir(); } });
  [faits, questions].forEach((z) => z.addEventListener("input", rafraichir));

  const deja = h("div", { class: "grille-interets" }, ...DEJA.map((cle) => h("label", {},
    h("input", { type: "checkbox", checked: etat.deja.has(cle), onchange: (e) => {
      if (e.target.checked) etat.deja.add(cle); else etat.deja.delete(cle);
      rafraichir();
    } }), t(cle))));

  const boutonAnalyse = h("button", { class: "bouton bouton-secondaire", type: "button", onclick: async () => {
    if (etat.faits.trim().length < 15) return;
    boutonAnalyse.disabled = true;
    try {
      const r = await api("/api/analyse", { method: "POST", body: { situation: etat.faits, pays: etat.pays } });
      etat.analyse = r;
      dessinerPreuves();
      rafraichir();
    } finally { boutonAnalyse.disabled = false; }
  } }, icone("balance"), t("dossier.analyser"));

  dessinerPreuves();
  dessinerChronologie();
  rafraichir();

  racine.append(
    h("header", { class: "titre-page" },
      h("img", { src: "/static/img/livre-marteau.svg", alt: "", class: "illustration-entete", "aria-hidden": "true" }),
      h("h1", {}, t("dossier.titre")), h("p", {}, t("dossier.sous"))),
    h("div", { class: "disposition-dossier" },
      h("form", { class: "carte formulaire-dossier", onsubmit: (e) => e.preventDefault() },
        h("div", { class: "note-confidentialite" }, icone("cadenas"), h("span", {}, t("dossier.prive"))),
        champ(t("dossier.s.faits"), faits, t("dossier.faits.aide")),
        boutonAnalyse,
        champ(t("dossier.auteur"), auteur),
        champ(t("dossier.enfants"), enfants),
        h("div", { class: "champ-groupe" }, h("span", { class: "libelle-dossier" }, t("dossier.s.chronologie")), chronologie),
        h("div", { class: "champ-groupe" }, h("span", { class: "libelle-dossier" }, t("dossier.s.preuves")), listePreuves),
        h("div", { class: "champ-groupe" }, h("span", { class: "libelle-dossier" }, t("dossier.s.deja")), deja),
        champ(t("dossier.s.questions"), questions),
        h("button", { class: "bouton bouton-primaire", type: "button", onclick: () => window.print() },
          icone("imprimer"), t("dossier.telecharger")),
        h("p", { class: "discret" }, t("dossier.astuce.pdf"))),
      h("div", { class: "colonne-apercu" }, h("p", { class: "chat-rubrique" }, t("dossier.apercu")), apercu)));
}
