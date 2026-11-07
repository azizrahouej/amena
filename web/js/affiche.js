// Composants « affiche » partagés par les pages intérieures (analyse, aide, bibliothèque, sécurité) :
// un grand panneau d'en-tête coloré, puis le contenu dans un panneau clair.

import { compter } from "./session.js";
import { h } from "./ui.js";

export const PHOTOS = {
  cabinet: "/static/img/3d/cabinet-3d.webp", palais: "/static/img/3d/palais-3d.webp",
  marteau: "/static/img/photos/marteau-portrait.webp", livres: "/static/img/photos/livres-marteau.webp",
  themis: "/static/img/photos/justice-livre.webp", bibliotheque: "/static/img/photos/justice-bibliotheque.webp",
};

// chiffres : [{ valeur: Number | Promise<Number> | String, libelle }]
export function heros({ surtitre, titre, texte, photo, teinte = "rouge", chiffres = [], actions = [], apres = null }) {
  const listeChiffres = chiffres.length ? h("ul", { class: "heros-chiffres" }, ...chiffres.map(({ valeur, libelle }) => {
    const b = h("b", {}, typeof valeur === "number" || valeur instanceof Promise ? "0" : valeur);
    if (typeof valeur === "number") compter(b, valeur, 1400);
    if (valeur instanceof Promise) valeur.then((v) => compter(b, v, 1400)).catch(() => { b.textContent = "—"; });
    return h("li", {}, b, h("span", {}, libelle));
  })) : null;
  return h("section", { class: `diapo diapo-${teinte} heros-page`, "data-diapo": "" },
    h("div", { class: "heros-texte" },
      surtitre ? h("span", { class: "surtitre-clair" }, surtitre) : null,
      h("h1", { class: "titre-section", "data-balayer": "" }, titre),
      texte ? h("p", { class: "heros-accroche" }, texte) : null,
      actions.length ? h("div", { class: "boutons" }, ...actions) : null,
      apres),
    photo ? h("figure", { class: "heros-medaillon", "aria-hidden": "true" },
      h("span", { class: "heros-disque", style: `--photo:url('${PHOTOS[photo] || photo}')` })) : null,
    listeChiffres);
}

export function corps(...enfants) {
  return h("section", { class: "diapo diapo-clair page-corps" }, ...enfants);
}
