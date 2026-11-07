// Coquille de l'application : navigation, langue, compte, sortie rapide, routage par ancre (#/page).
// Aucune donnée n'est écrite dans le navigateur (ni localStorage) ; seul un compte, s'il est
// utilisé, pose un cookie de session HttpOnly.

import { definirLangue, langueCourante, t } from "./i18n.js";
import { activerEffets, observerEffets } from "./effets.js";
import { animerDefilement } from "./defilement.js";
import { chargerSession, reveler, session, surChangement } from "./session.js";
import { h, icone } from "./ui.js";
import { pageAccueil } from "./pages/accueil.js";
import { pageChat } from "./pages/chat.js";
import { pageAnalyse } from "./pages/analyse.js";
import { pageLois } from "./pages/lois.js";
import { pageDroits } from "./pages/droits.js";
import { pageMonde } from "./pages/monde.js";
import { pageDossier } from "./pages/dossier.js";
import { pageAide } from "./pages/aide.js";
import { pageSecurite } from "./pages/securite.js";
import { pageCompte } from "./pages/compte.js";
import { pageEspace } from "./pages/espace.js";
import { pagePartenaires } from "./pages/partenaires.js";

const PAGES = [
  { route: "", cle: "nav.accueil", icone: "accueil", rendu: pageAccueil },
  { route: "chat", cle: "nav.chat", icone: "chat", rendu: pageChat },
  { route: "analyse", cle: "nav.analyse", court: "nav.court.analyse", icone: "balance", rendu: pageAnalyse },
  { route: "lois", cle: "nav.lois", court: "nav.court.lois", icone: "droits", rendu: pageLois, aussi: ["droits", "monde"] },
  { route: "aide", cle: "nav.aide", court: "nav.court.aide", icone: "aide", rendu: pageAide },
  { route: "securite", cle: "nav.securite", icone: "bouclier", rendu: pageSecurite },
  { route: "droits", rendu: pageDroits, cachee: true },
  { route: "monde", rendu: pageMonde, cachee: true },
  { route: "dossier", rendu: pageDossier, cachee: true },
  { route: "compte", rendu: pageCompte, cachee: true },
  { route: "espace", rendu: pageEspace, cachee: true },
  { route: "partenaires", rendu: pagePartenaires, cachee: true },
];

const contenu = document.getElementById("contenu");

// --- Sortie rapide ---------------------------------------------------------
function sortieRapide() {
  // keepalive : la déconnexion part même si la page est remplacée immédiatement.
  if (session()) fetch("/api/auth/deconnexion", { method: "POST", keepalive: true }).catch(() => {});
  document.body.replaceChildren();
  window.location.replace("https://www.google.com/search?q=m%C3%A9t%C3%A9o+tunis");
}
document.addEventListener("keydown", (e) => { if (e.key === "Escape") sortieRapide(); });

// --- Routage ---------------------------------------------------------------
function analyserRoute() {
  const [route = "", ...params] = location.hash.replace(/^#\/?/, "").split("/");
  return { page: PAGES.find((p) => p.route === route) || PAGES[0], params: params.map(decodeURIComponent), route };
}

export function aller(chemin) { location.hash = `#/${chemin}`; }

function lienNav(page, actif, classe, cle) {
  return h("a", { href: `#/${page.route}`, class: `${classe}${actif ? " actif" : ""}`,
                  "aria-current": actif ? "page" : false },
    icone(page.icone), h("span", {}, t(cle)));
}

// --- Menu plein écran (mobile et tablette) ----------------------------------------
const NUMEROS = [["197", "pied.n197"], ["193", "pied.n193"], ["190", "pied.n190"], ["1899", "pied.n1899"]];

function ouvrirMenu(ouvert) {
  const menu = document.getElementById("menu-plein");
  const bouton = document.getElementById("bouton-menu");
  menu.hidden = !ouvert;
  bouton.setAttribute("aria-expanded", String(ouvert));
  bouton.setAttribute("aria-label", t(ouvert ? "menu.fermer" : "menu.ouvrir"));
  document.body.classList.toggle("menu-ouvert", ouvert);
}

function dessinerMenu(visibles, estActif) {
  const cliquer = (id) => () => { ouvrirMenu(false); document.getElementById(id).click(); };
  document.getElementById("menu-plein").replaceChildren(
    h("ul", { class: "menu-liens" }, ...visibles.map((p, i) => h("li", {},
      h("a", { href: `#/${p.route}`, class: estActif(p) ? "actif" : "", "aria-current": estActif(p) ? "page" : false },
        h("small", {}, String(i + 1).padStart(2, "0")), t(p.cle))))),
    h("div", { class: "menu-bas" },
      h("div", { class: "menu-reglages" },
        h("button", { type: "button", class: "bouton bouton-contour", onclick: cliquer("bouton-langue") }, icone("langues"), t("langue.autre")),
        h("button", { type: "button", class: "bouton bouton-contour", onclick: cliquer("bouton-theme") },
          icone(document.documentElement.dataset.theme === "sombre" ? "soleil" : "lune"),
          t(document.documentElement.dataset.theme === "sombre" ? "theme.clair" : "theme.sombre")),
        h("a", { href: session() ? "#/espace" : "#/compte", class: "bouton bouton-contour" }, icone("utilisatrice"),
          session() ? session().pseudo : t("compte.connexion"))),
      h("ul", { class: "menu-numeros" }, ...NUMEROS.map(([n, cle]) => h("li", {},
        h("a", { href: `tel:${n}` }, h("b", {}, n), h("span", {}, t(cle))))))));
}

function dessinerCoquille(route) {
  const visibles = PAGES.filter((p) => !p.cachee);
  const estActif = (p) => p.route === route || (p.aussi || []).includes(route);
  // Dans la barre : les rubriques ; l'accueil passe par le logo et le chat par le bouton blanc.
  document.getElementById("navigation").replaceChildren(
    ...visibles.filter((p) => p.route !== "" && p.route !== "chat")
      .map((p) => lienNav(p, estActif(p), "lien-nav", p.court || p.cle)));
  dessinerMenu(visibles, estActif);
  const menu = document.getElementById("bouton-menu");
  menu.onclick = () => ouvrirMenu(menu.getAttribute("aria-expanded") !== "true");
  menu.setAttribute("aria-label", t("menu.ouvrir"));

  const billet = document.getElementById("bouton-billet");
  billet.replaceChildren(h("span", {}, t("cab.cta2")), icone("fleche", "icone icone-direction"));
  billet.classList.toggle("actif", route === "chat");


  // Thème clair par défaut ; le sombre est un choix explicite, oublié à la fermeture de l'onglet.
  const theme = document.getElementById("bouton-theme");
  const sombre = document.documentElement.dataset.theme === "sombre";
  theme.replaceChildren(icone(sombre ? "soleil" : "lune"));
  theme.title = t(sombre ? "theme.clair" : "theme.sombre");
  theme.setAttribute("aria-label", theme.title);
  theme.onclick = () => {
    if (sombre) delete document.documentElement.dataset.theme;
    else document.documentElement.dataset.theme = "sombre";
    dessinerCoquille(route);
  };

  const bouton = document.getElementById("bouton-langue");
  bouton.replaceChildren(h("span", { lang: langueCourante() === "fr" ? "ar" : "fr" }, t("langue.court")));
  bouton.title = t("langue.autre");
  bouton.setAttribute("aria-label", t("langue.autre"));
  bouton.onclick = () => { definirLangue(langueCourante() === "fr" ? "ar" : "fr"); rendre(); };

  dessinerCompte();
  dessinerPied(visibles);
}

function dessinerPied(visibles) {
  document.getElementById("pied").replaceChildren(
    h("div", { class: "pied-grille" },
      h("div", { class: "pied-intro" },
        h("p", {}, t("pied.avertissement")),
        h("p", {}, t("pied.confidentialite"))),
      h("div", {}, h("h4", {}, t("pied.navigation")),
        h("ul", {}, ...visibles.map((p) => h("li", {}, h("a", { href: `#/${p.route}` }, t(p.cle)))),
          h("li", {}, h("a", { href: "#/dossier" }, t("t3d.dossier.t"))),
          h("li", {}, h("a", { href: "#/monde" }, t("lois.onglet.monde"))),
          h("li", {}, h("a", { href: "#/partenaires" }, t("nav.partenaires"))))),
      h("div", {}, h("h4", {}, t("pied.urgences")),
        h("ul", {}, ...NUMEROS.map(([n, cle]) => h("li", {}, h("a", { href: `tel:${n}`, class: "numero-pied" },
          h("span", {}, t(cle)), h("b", {}, n)))))),
      h("div", {}, h("h4", {}, t("pied.sources")),
        h("ul", {},
          h("li", {}, t("pied.source1")),
          h("li", {}, t("pied.source2")),
          h("li", {}, t("pied.source3")),
          h("li", {}, t("pied.photos"))))),
    h("p", { class: "pied-geant", "aria-hidden": "true" }, h("span", {}, "AMENA"), h("span", { lang: "ar" }, "أمانة")),
    h("div", { class: "pied-bas" }, `© ${new Date().getFullYear()} AMENA · ${t("pied.bas")}`));
}

function dessinerCompte() {
  const lien = document.getElementById("bouton-compte");
  const u = session();
  if (u) {
    lien.href = "#/espace";
    lien.className = "bouton-compte";
    lien.replaceChildren(h("span", { class: "pastille-avatar" }, u.pseudo.slice(0, 1).toUpperCase()), h("span", {}, u.pseudo));
  } else {
    lien.href = "#/compte";
    lien.className = "bouton-compte deconnecte";
    lien.replaceChildren(icone("utilisatrice"), h("span", {}, t("compte.connexion")));
  }
}

let routePrecedente = null;

function rendre() {
  const { page, params, route } = analyserRoute();
  ouvrirMenu(false);
  dessinerCoquille(route);
  contenu.replaceChildren();
  page.rendu(contenu, { params, aller });
  reveler(contenu);
  activerEffets(contenu);
  animerDefilement(contenu);
  document.body.dataset.page = route || "accueil";
  const cle = `${route}/${params.join("/")}`;
  if (cle !== routePrecedente) {
    window.scrollTo({ top: 0 });
    routePrecedente = cle;
  }
}

definirLangue(navigator.language?.startsWith("ar") ? "ar" : "fr");
surChangement(dessinerCompte);
observerEffets(contenu);
window.addEventListener("hashchange", rendre);
export const rafraichir = rendre;
rendre();
chargerSession();
