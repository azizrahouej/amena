// « Trouver de l'aide » : numéro vert en grand, urgences, quoi dire au téléphone, services
// publics et associations. Les données viennent de data/ressources.json (via /api/ressources).

import { corps, heros } from "../affiche.js";
import { langueCourante, t } from "../i18n.js";
import { api, h, icone } from "../ui.js";

let cache = null;

export function pageAide(racine) {
  const entete = h("div");
  const zone = h("div", { class: "aide-corps" });
  racine.append(entete, corps(zone));

  (cache ? Promise.resolve(cache) : api("/api/ressources").then((r) => (cache = r))).then((r) => {
    const lg = langueCourante();
    const ecoute = r.ecoute[0];

    entete.replaceWith(heros({
      surtitre: t("hp.aide.sur"), titre: t("aide.titre"), texte: t("aide.sous"), teinte: "rouge cercles",
      photo: "cabinet",
      apres: h("div", { class: "heros-numero" },
        h("small", {}, `${ecoute[lg]} · ${ecoute[`detail_${lg}`]}`),
        h("a", { class: "numero-geant", href: `tel:${ecoute.numero}` }, ecoute.numero)),
      actions: [h("a", { href: `tel:${ecoute.numero}`, class: "bouton bouton-blanc" }, icone("aide"), t("aide.appeler")),
                h("a", { href: "#/chat", class: "bouton bouton-contour" }, icone("chat"), t("cab.cta2"))],
    }));

    zone.append(
      h("section", { class: "bloc-page" },
        h("header", { class: "entete-bloc" }, h("h2", {}, t("aide.urgences")), h("p", {}, t("hp.aide.urgences"))),
        h("div", { class: "grille-numeros" },
          ...r.urgences.map((u) => h("a", { href: `tel:${u.numero}`, class: "carte-numero" },
            h("span", { class: "numero" }, u.numero),
            h("strong", {}, u[lg]),
            h("span", { class: "detail" }, u[`detail_${lg}`]),
            h("span", { class: "appeler" }, icone("aide"), t("aide.appeler")))))),

      h("section", { class: "bloc-page grille-deux" },
        h("div", { class: "carte carte-sombre" },
          h("h2", {}, t("aide.telephone.t")),
          h("ol", { class: "etapes-num" }, ...[1, 2, 3, 4].map((i) => h("li", {}, t(`aide.telephone.${i}`))))),
        h("div", { class: "carte" },
          h("h2", {}, t("aide.publics")),
          h("ul", { class: "liste-services" },
            ...r.publics.map((p) => h("li", {}, h("span", { class: "icone-ronde" }, icone("bouclier")),
              h("div", {}, h("strong", {}, p[lg]), h("p", { class: "discret" }, p[`detail_${lg}`]))))))),

      h("section", { class: "bloc-page" },
        h("header", { class: "entete-bloc" }, h("h2", {}, t("aide.associations")), h("p", {}, t("aide.verifier"))),
        h("div", { class: "grille-associations" },
          ...r.associations.map((a, i) => h("article", { class: "carte carte-association" },
            h("span", { class: "rang" }, String(i + 1).padStart(2, "0")),
            h("h3", {}, a[`nom_${lg}`]),
            h("p", { class: "discret" }, a[`services_${lg}`]))))));
  });
}
