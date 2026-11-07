// « Mes droits » : bibliothèque des fiches + recherche dans la base de connaissances
// (le même moteur que le chatbot, exposé directement).

import { t } from "../i18n.js";
import { suivre } from "../session.js";
import { api, h, icone } from "../ui.js";
import { preremplir } from "./chat.js";
import { boutonFavori, ongletsBibliotheque } from "./lois.js";

let cacheFiches = null;

async function chargerFiches() {
  cacheFiches ??= await api("/api/fiches");
  return cacheFiches;
}

function ancre(texte) {
  return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-").replace(/^-|-$/g, "");
}

function vueLecture(racine, fiche, aller) {
  suivre(`fiche:${fiche.id}`);
  const article = h("article", { class: "article carte" },
    h("a", { href: "#/droits", class: "bouton bouton-fantome" }, icone("retour", "icone icone-direction"), t("droits.retour")),
    h("h1", { dir: "auto" }, fiche.titre),
    h("div", { class: "avertissement" }, icone("alerte"), h("span", {}, t("droits.avert"))),
    h("div", { style: "margin-bottom:6px" }, boutonFavori(`fiche:${fiche.id}`)),
    ...fiche.sections.map((s) => h("section", { id: ancre(s.titre) },
      h("h2", { dir: "auto" }, s.titre),
      h("p", { dir: "auto" }, s.texte))),
    h("button", { class: "bouton bouton-primaire", onclick: () => {
      preremplir(fiche.sections[0]?.titre ? `${fiche.titre} : ${fiche.sections[0].titre}` : fiche.titre);
      aller("chat");
    } }, icone("chat"), t("droits.question")));

  const sommaire = h("nav", { class: "sommaire", "aria-label": t("droits.sommaire") },
    h("h2", {}, t("droits.sommaire")),
    ...fiche.sections.map((s) => h("a", { href: "#", dir: "auto", onclick: (e) => {
      e.preventDefault();
      document.getElementById(ancre(s.titre))?.scrollIntoView({ behavior: "smooth" });
    } }, s.titre)));

  racine.replaceChildren(h("div", { class: "lecture" }, sommaire, article));
}

export function pageDroits(racine, { params, aller }) {
  const zone = h("div");
  racine.append(zone);

  if (params[0]) {
    chargerFiches().then((fiches) => {
      const fiche = fiches.find((f) => f.id === params[0]);
      if (fiche) vueLecture(zone, fiche, aller);
      else aller("droits");
    });
    return;
  }

  const resultats = h("div", { class: "grille", "aria-live": "polite" });
  const grille = h("div", { class: "grille grille-3" });
  let minuterie = null;

  const champ = h("input", { type: "search", dir: "auto", placeholder: t("droits.recherche"),
                             "aria-label": t("droits.recherche") });
  champ.addEventListener("input", () => {
    clearTimeout(minuterie);
    const q = champ.value.trim();
    if (q.length < 3) { resultats.replaceChildren(); return; }
    minuterie = setTimeout(async () => {
      const trouves = await api(`/api/recherche?q=${encodeURIComponent(q)}&k=4`).catch(() => []);
      resultats.replaceChildren(
        h("h2", { class: "discret" }, trouves.length ? t("droits.resultats") : t("droits.aucun")),
        ...trouves.map((r) => h("a", { href: r.type === "loi" ? `#/lois/${r.element.slice(4)}` : `#/droits/${r.fiche}`, class: "carte resultat" },
          h("strong", { dir: "auto" }, r.titre),
          h("p", { dir: "auto" }, r.extrait.length > 260 ? `${r.extrait.slice(0, 260)}…` : r.extrait))));
    }, 250);
  });

  zone.append(
    h("header", { class: "titre-page" }, h("h1", {}, t("lois.titre")), h("p", {}, t("droits.sous"))),
    ongletsBibliotheque("fiches"),
    h("div", { class: "champ-recherche" }, icone("recherche"), champ),
    h("section", { class: "section" }, resultats),
    h("section", { class: "section" }, grille));

  chargerFiches().then((fiches) => {
    grille.replaceChildren(...fiches.map((f) => h("a", { href: `#/droits/${f.id}`, class: "carte carte-fiche" },
      h("span", { class: "icone-ronde" }, icone("droits")),
      h("h3", { dir: "auto" }, f.titre),
      h("p", { class: "discret", dir: "auto" }, f.sections.slice(0, 3).map((s) => s.titre).join(" · ")),
      h("div", { class: "pied-carte" }, h("span", {}, `${f.sections.length} ${t("droits.sections")}`),
        icone("fleche", "icone icone-direction")))));
  });
}
