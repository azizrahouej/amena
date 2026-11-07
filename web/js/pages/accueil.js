// Accueil « affiche » : une page en panneaux pleine largeur, à la manière d'un site de festival.
//   ouverture     image plein cadre, infos pratiques, titre géant qui s'écarte au défilement ;
//   bande         mots-clés qui défilent en continu ;
//   parcours      les étapes en anneaux, avec deux onglets (consultation / après une violence) ;
//   affiche       les domaines traités, en grandes lignes, comme des têtes d'affiche ;
//   duel          la loi face à ses failles ;
//   espaces       les quatre espaces du cabinet, image en orbite ;
//   chiffres      la base juridique en nombres ;
//   formules      trois façons de commencer, sur des cartes ;
//   faq           questions fréquentes en accordéon ;
//   urgence       numéros d'urgence et sortie rapide.
// Les images : rendus 3D d'AMENA (img/3d) et photos fournies pour le projet (img/photos).

import { langueCourante, t } from "../i18n.js";
import { compter } from "../session.js";
import { api, h, icone } from "../ui.js";
import { preparerAnalyse } from "./analyse.js";
import { preremplir } from "./chat.js";

const IMG = "/static/img";
const PHOTOS = {
  cabinet: `${IMG}/3d/cabinet-3d.webp`, palais: `${IMG}/3d/palais-3d.webp`,
  marteau: `${IMG}/photos/marteau-portrait.webp`, livres: `${IMG}/photos/livres-marteau.webp`,
  themis: `${IMG}/photos/justice-livre.webp`, bibliotheque: `${IMG}/photos/justice-bibliotheque.webp`,
  // Photos réelles prises en Tunisie (Wikimedia Commons, crédits dans le pied de page).
  justice: `${IMG}/photos/palais-justice-tunis.webp`, kasbah: `${IMG}/photos/kasbah-tunis.webp`,
  avenue: `${IMG}/photos/avenue-bourguiba-tunis.webp`, terres: `${IMG}/photos/oliveraie-dahar.webp`,
};
const photo = (cle) => `--photo:url('${PHOTOS[cle]}')`;

// Un domaine ouvre soit l'analyse détaillée (famille, violences, numérique), soit le chat, qui
// cherche dans tous les codes (travail, contrats, procédure).
function versDomaine(cleExemple, mode, aller) {
  return (e) => {
    e.preventDefault();
    if (mode === "chat") { preremplir(t(cleExemple)); aller("chat"); return; }
    preparerAnalyse(t(cleExemple));
    aller("analyse");
  };
}

// Titre de section : la couleur se remplit au défilement (data-balayer).
const titre = (cle, niveau = "h2") => h(niveau, { class: "titre-section", "data-balayer": "" }, t(cle));

function entete(cleTitre, cleTexte, ...apres) {
  return h("header", { class: "entete-diapo" }, titre(cleTitre), h("div", {}, h("p", {}, t(cleTexte)), ...apres));
}

// --- Ouverture ---------------------------------------------------------------------------------
function ouverture() {
  return h("section", { class: "diapo diapo-nuit ouverture", "data-diapo": "" },
    h("div", { class: "ouverture-media", "aria-hidden": "true" },
      h("img", { src: PHOTOS.justice, alt: "", width: 1600, height: 1200, fetchpriority: "high", decoding: "async" }),
      h("span", { class: "voile" })),
    h("div", { class: "ouverture-infos" },
      h("dl", {},
        h("div", {}, h("dt", {}, t("ac.dispo.t")), h("dd", {}, t("ac.dispo.v"))),
        h("div", {}, h("dt", {}, t("ac.langues.t")), h("dd", {}, t("ac.langues.v")))),
      h("p", { class: "ouverture-accroche" }, t("ac.accroche")),
      h("div", { class: "boutons" },
        h("a", { href: "#/chat", class: "bouton bouton-blanc" }, t("cab.cta2"), icone("fleche", "icone icone-direction")),
        h("a", { href: "#/analyse", class: "bouton bouton-contour" }, t("cab.cta1")))),
    h("h1", { class: "titre-geant ouverture-titre", "data-ecarter": "" },
      h("span", {}, "AMENA"), h("span", { lang: "ar" }, "أمانة")));
}

function bande() {
  const mots = t("ac.bande").split(" · ");
  const suite = () => h("span", {}, ...mots.flatMap((m) => [h("b", {}, m), h("i", { "aria-hidden": "true" }, "✦")]));
  return h("div", { class: "bande", "aria-label": mots.join(", ") },
    h("div", { class: "bande-piste", "aria-hidden": "true" }, suite(), suite()));
}

// --- Parcours en anneaux (le « programme » du festival) -------------------------------------------
const PARCOURS = {
  consultation: [["ac.c1", "themis"], ["ac.c2"], ["ac.c3", "bibliotheque"], ["ac.c4"], ["ac.c5", "marteau"],
                 ["ac.c6"], ["ac.c7", "livres"]],
  violence: [["ac.v1"], ["ac.v2", "themis"], ["ac.v3"], ["ac.v4", "marteau"], ["ac.v5"],
             ["ac.v6", "bibliotheque"], ["ac.v7", "cabinet"]],
};

function parcours() {
  const anneaux = h("ol", { class: "anneaux", "data-glisser": "-14" });
  const onglets = [];
  const choisir = (nom) => {
    onglets.forEach((o) => o.setAttribute("aria-selected", String(o.dataset.nom === nom)));
    anneaux.replaceChildren(...PARCOURS[nom].map(([cle, image], i) =>
      h("li", { class: `anneau-etape${image ? " avec-photo" : ""}`, style: image ? photo(image) : false },
        h("b", {}, String(i + 1).padStart(2, "0")), h("strong", {}, t(`${cle}.t`)), h("small", {}, t(`${cle}.s`)))));
  };
  for (const [nom, cle] of [["consultation", "ac.p.tab1"], ["violence", "ac.p.tab2"]]) {
    onglets.push(h("button", { type: "button", role: "tab", class: "onglet-jour", "data-nom": nom,
                               onclick: () => choisir(nom) }, t(cle)));
  }
  choisir("consultation");
  return h("section", { class: "diapo diapo-vin parcours", id: "parcours", "data-diapo": "" },
    entete("ac.p.titre", "ac.p.texte",
      h("div", { class: "onglets-jours", role: "tablist", "aria-label": t("ac.p.titre") }, ...onglets)),
    h("div", { class: "anneaux-cadre" }, anneaux),
    h("footer", { class: "pied-diapo" }, h("span", {}, t("ac.p.note")),
      h("a", { href: "#/chat", class: "lien-souligne" }, t("ac.p.lien"))));
}

// --- Affiche : les domaines traités --------------------------------------------------------------
function affiche(aller) {
  const domaines = [["cab.e1", "cab.ex1", "avenue", "chat"], ["cab.e2", "cab.ex2", "marteau", "chat"],
                    ["cab.e7", "cab.ex7", "terres", "chat"], ["cab.e3", "cab.ex3", "bibliotheque", "analyse"],
                    ["cab.e4", "cab.ex4", "livres", "analyse"], ["cab.e5", "cab.ex5", "cabinet", "analyse"],
                    ["cab.e6", "cab.ex6", "justice", "chat"]];
  return h("section", { class: "diapo diapo-nuit affiche", id: "domaines", "data-diapo": "" },
    entete("ac.d.titre", "ac.d.texte"),
    h("ol", { class: "affiche-liste" }, ...domaines.map(([cle, exemple, image, mode], i) => h("li", {},
      h("a", { href: `#/${mode}`, onclick: versDomaine(exemple, mode, aller) },
        h("span", { class: "medaillon", style: photo(image), "aria-hidden": "true" }),
        h("span", { class: "affiche-nom", "data-balayer": "" }, t(`${cle}.t`)),
        h("span", { class: "affiche-meta" }, h("small", {}, `${String(i + 1).padStart(2, "0")} · ${t("cab.e.lien")}`),
          h("span", {}, t(`${cle}.d`))))))));
}

// --- Duel : la loi face à ses failles ------------------------------------------------------------
function duel() {
  return h("section", { class: "diapo duel", "data-diapo": "" },
    h("div", { class: "duel-cote duel-loi", style: photo("marteau") },
      h("div", { class: "duel-haut" }, titre("ac.duel.titre"),
        h("p", {}, t("ac.duel.texte")), h("a", { href: "#/analyse", class: "lien-souligne" }, t("ac.duel.lien"))),
      h("div", { class: "duel-bas" }, h("small", {}, t("ac.duel.g.s")), h("strong", { "data-balayer": "" }, t("ac.duel.g")))),
    h("span", { class: "duel-vs", "aria-hidden": "true" }, "VS"),
    h("div", { class: "duel-cote duel-failles", style: photo("bibliotheque") },
      h("ol", { class: "duel-manches" }, ...[1, 2, 3].map((i) => h("li", {},
        h("small", {}, t(`ac.duel.m${i}.s`)), h("span", {}, t(`ac.duel.m${i}`))))),
      h("div", { class: "duel-bas" }, h("small", {}, t("ac.duel.d.s")), h("strong", { "data-balayer": "" }, t("ac.duel.d")))));
}

// --- Les quatre espaces ----------------------------------------------------------------------------
function espaces() {
  const zones = [["ac.z1", "chat", "themis"], ["ac.z2", "analyse", "marteau"],
                 ["ac.z3", "lois", "bibliotheque"], ["ac.z4", "dossier", "livres"]];
  const image = h("img", { src: PHOTOS.themis, alt: "", loading: "lazy", decoding: "async" });
  const legende = h("figcaption", {}, t("ac.z1.t"));
  const items = [];
  const montrer = (i) => {
    const [cle, , cleImage] = zones[i];
    image.src = PHOTOS[cleImage];
    legende.textContent = t(`${cle}.t`);
    items.forEach((li, j) => li.classList.toggle("actif", i === j));
  };
  zones.forEach(([cle, route], i) => {
    items.push(h("li", { onpointerenter: () => montrer(i), onfocusin: () => montrer(i) },
      h("a", { href: `#/${route}` },
        h("span", { class: "espace-tete" }, h("h3", {}, t(`${cle}.t`)), h("span", { class: "pastille-claire" }, t(`${cle}.tag`))),
        h("p", {}, t(`${cle}.d`)),
        h("span", { class: "lien-souligne" }, t("ac.z.ouvrir")))));
  });
  items[0].classList.add("actif");
  return h("section", { class: "diapo diapo-rouge espaces", "data-diapo": "" },
    entete("ac.z.titre", "ac.z.texte"),
    h("div", { class: "espaces-corps" },
      h("figure", { class: "orbite" }, h("div", { class: "orbite-disque" }, image), legende),
      h("ol", { class: "espaces-liste" }, ...items)));
}

// --- Chiffres ---------------------------------------------------------------------------------------
function chiffres() {
  const cles = [["textes", "cab.ch3"], ["pays_monde", "cab.ch1"], ["indicateurs_monde", "cab.ch2"]];
  const valeurs = Object.fromEntries(cles.map(([cle]) => [cle, h("b", {}, "0")]));
  api("/api/sante").then((s) => {
    for (const [cle] of cles) compter(valeurs[cle], s.bibliotheque[cle] || 0, 1600);
  }).catch(() => {});
  return h("section", { class: "diapo diapo-vin base-chiffres", "data-diapo": "" },
    entete("ac.n.titre", "ac.n.texte"),
    h("ul", { class: "grands-chiffres" },
      ...cles.map(([cle, libelle]) => h("li", { class: "revele" }, valeurs[cle], h("span", {}, t(libelle)))),
      h("li", { class: "revele" }, h("b", {}, "3"), h("span", {}, t("cab.ch4")))),
    h("figure", { class: "citation" }, h("blockquote", {}, t("cab.citation")), h("figcaption", {}, t("cab.auteur"))));
}

// --- Formules (les « billets ») ------------------------------------------------------------------------
function formules() {
  const cartes = [["ac.f1", "chat", "rouge"], ["ac.f2", "analyse", "vin"], ["ac.f3", "dossier", "nuit"]];
  return h("section", { class: "diapo diapo-clair formules", "data-diapo": "" },
    entete("ac.f.titre", "ac.f.texte"),
    h("div", { class: "grille-formules" }, ...cartes.map(([cle, route, teinte], i) =>
      h("article", { class: `formule formule-${teinte} revele d${i}` },
        h("span", { class: "pastille-claire" }, t(`${cle}.tag`)),
        h("h3", { "data-balayer": "" }, t(`${cle}.t`)),
        h("ul", {}, ...[1, 2, 3].map((j) => h("li", {}, t(`${cle}.l${j}`)))),
        h("div", { class: "formule-bas" },
          h("p", { class: "prix" }, t("ac.f.prix"), h("small", {}, t("ac.f.gratuit"))),
          h("a", { href: `#/${route}`, class: "bouton bouton-blanc bouton-petit" }, t(`${cle}.b`)))))),
    h("p", { class: "note-formules" }, t("ac.f.note")));
}

// --- FAQ -------------------------------------------------------------------------------------------------
function faq() {
  return h("section", { class: "diapo diapo-vin faq", id: "faq", "data-diapo": "" },
    h("div", { class: "faq-intro" }, titre("ac.q.titre"), h("p", {}, t("ac.q.texte")),
      h("a", { href: "#/aide", class: "lien-souligne" }, t("nav.aide"))),
    h("div", { class: "faq-liste" }, ...[1, 2, 3, 4, 5, 6].map((i) =>
      h("details", {}, h("summary", {}, t(`ac.q${i}.q`)), h("p", {}, t(`ac.q${i}.r`))))));
}

// --- Urgence ---------------------------------------------------------------------------------------------
function urgence() {
  const numeros = [["197", "pied.n197"], ["193", "pied.n193"], ["190", "pied.n190"]];
  return h("section", { class: "diapo diapo-rouge urgence", "data-diapo": "" },
    h("img", { class: "urgence-palais", src: PHOTOS.palais, alt: "", loading: "lazy", decoding: "async", "aria-hidden": "true" }),
    h("div", { class: "urgence-contenu" },
      titre("ac.u.titre"),
      h("p", {}, t("ac.u.texte")),
      h("a", { class: "numero-geant", href: "tel:1899" }, "1899"),
      h("ul", { class: "urgence-colonnes" },
        ...numeros.map(([n, cle]) => h("li", {}, h("small", {}, t(cle)), h("a", { href: `tel:${n}` }, n))))));
}

// --- Le droit, chez nous : photos réelles de Tunisie ------------------------------------------------
function tunisie() {
  const lieux = [["justice", "ac.tn1"], ["kasbah", "ac.tn2"], ["avenue", "ac.tn3"], ["terres", "ac.tn4"]];
  return h("section", { class: "diapo diapo-clair tunisie", id: "tunisie", "data-diapo": "" },
    entete("ac.tn.titre", "ac.tn.texte"),
    h("div", { class: "tunisie-grille" }, ...lieux.map(([cle, texte], i) =>
      h("figure", { class: `tunisie-photo${i === 0 ? " tunisie-grande" : ""}` },
        h("img", { src: PHOTOS[cle], alt: t(`${texte}.alt`), loading: "lazy", decoding: "async" }),
        h("figcaption", {}, h("strong", {}, t(`${texte}.t`)), h("span", {}, t(`${texte}.d`)))))));
}

export function pageAccueil(racine, { aller }) {
  document.documentElement.style.setProperty("--sens", langueCourante() === "ar" ? "-1" : "1");
  racine.append(ouverture(), bande(), parcours(), affiche(aller), tunisie(), duel(), espaces(), chiffres(), formules(), faq(), urgence());
}
