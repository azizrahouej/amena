// Atlas mondial : 190 pays d'après la Banque mondiale (Women, Business and the Law 2026).
// Carte en tuiles regroupées par région, colorées selon l'indicateur choisi ; fiche pays détaillée
// avec bases légales, comparaison régionale et mondiale.

import { langueCourante, t } from "../i18n.js";
import { api, h, icone } from "../ui.js";
import { ongletsBibliotheque } from "./lois.js";

let cache = null;
const etat = { indicateur: "score_cadre_legal", recherche: "" };

const INDICATEURS = [
  { id: "score_cadre_legal", cle: "monde.i.cadre", type: "score" },
  { id: "score_dispositifs", cle: "monde.i.dispositifs", type: "score" },
  { id: "score_application", cle: "monde.i.application", type: "score" },
  { id: "Saf_Law_DomViolLaw", cle: "monde.i.vd", type: "oui" },
  { id: "Saf_Law_DomViol_ProtOrd", cle: "monde.i.ordonnance", type: "oui" },
  { id: "Saf_Law_DomViol_SexualMR", cle: "monde.i.viol", type: "oui" },
  { id: "Saf_Law_SexHar_PubCpCr", cle: "monde.i.rue", type: "oui" },
  { id: "Saf_Law_SexHar_CybCpCr", cle: "monde.i.cyber", type: "oui" },
  { id: "Saf_Law_FemicideCr", cle: "monde.i.feminicide", type: "oui" },
  { id: "Saf_Law_ChildMarr_Age", cle: "monde.i.mariage", type: "oui" },
];

const charger = () => (cache ? Promise.resolve(cache) : api("/api/monde").then((d) => (cache = d)));

// Couleur d'un score de 0 à 100 : du rouge au vert, en passant par l'ambre.
function couleur(valeur) {
  if (valeur == null) return "var(--surface-2)";
  const teinte = Math.round((valeur / 100) * 135);
  return `hsl(${teinte} 62% 46%)`;
}

function valeurDe(pays, ind) {
  if (ind.type === "score") return pays[ind.id];
  const r = pays.reponses[ind.id];
  return r == null ? null : r ? 100 : 0;
}

function barreComparee(libelle, valeur, region, monde) {
  const piste = (v, classe) => h("div", { class: `piste-comparee ${classe}` },
    h("div", { style: `width:${v ?? 0}%;background:${classe === "pays" ? couleur(v) : ""}` }));
  return h("div", { class: "comparaison" },
    h("div", { class: "ligne-comparaison" }, h("strong", {}, libelle), h("b", {}, valeur == null ? t("monde.nonmesure") : `${Math.round(valeur)}/100`)),
    piste(valeur, "pays"),
    h("div", { class: "legende-comparaison" },
      h("span", {}, `${t("monde.region")} ${region ?? "—"}`), h("span", {}, `${t("monde.monde")} ${monde ?? "—"}`)));
}

function vueDetail(zone, code, aller) {
  api(`/api/monde/${encodeURIComponent(code)}`).then((p) => {
    const themes = {};
    for (const i of p.indicateurs) (themes[i.theme] ||= []).push(i);
    const cadre = p.indicateurs.filter((i) => i.pilier === "cadre_legal");
    const lacunes = cadre.filter((i) => i.reponse === false).length;
    zone.replaceChildren(
      h("a", { href: "#/monde", class: "bouton bouton-fantome" }, icone("retour", "icone icone-direction"), t("monde.retour")),
      h("header", { class: "entete-pays carte" },
        h("span", { class: "grand-code" }, p.iso3),
        h("div", { style: "flex:1;min-width:220px" },
          h("h1", {}, p.pays_fr),
          h("p", { class: "discret" }, `${p.region_fr} · ${p.revenu}`),
          h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;margin-top:10px" },
            h("span", { class: "pastille" }, `${t("monde.rang")} ${p.rang_cadre}/190`),
            h("span", { class: `pastille ${lacunes ? "danger" : "vert"}` }, `${lacunes} ${t("monde.lacunes")}`),
            p.code_bibliotheque ? h("a", { class: "pastille vert", href: "#/lois" }, t("monde.voirtextes")) : null)),
        h("button", { class: "bouton bouton-primaire", onclick: () => aller("analyse") }, icone("balance"), t("monde.analyser"))),
      h("div", { class: "grille grille-3 section" },
        barreComparee(t("monde.i.cadre"), p.score_cadre_legal, p.moyenne_region.cadre, p.moyenne_monde.cadre),
        barreComparee(t("monde.i.dispositifs"), p.score_dispositifs, p.moyenne_region.dispositifs, p.moyenne_monde.dispositifs),
        barreComparee(t("monde.i.application"), p.score_application, p.moyenne_region.application, p.moyenne_monde.application)),
      h("div", { class: "grille grille-2 section" },
        ...Object.entries(themes).map(([theme, items]) => h("section", { class: "carte" },
          h("h2", { style: "font-size:1.02rem;margin-bottom:12px" }, theme),
          h("ul", { class: "liste-indicateurs" }, ...items.map((i) => h("li", { class: i.reponse === true ? "oui" : i.reponse === false ? "non" : "na" },
            h("span", { class: "marque" }, i.reponse === true ? "✓" : i.reponse === false ? "✗" : "–"),
            h("div", {}, h("p", {}, i.question),
              i.base_legale ? h("small", { class: "discret", dir: "auto" }, i.base_legale) : null,
              i.reponse == null ? h("small", { class: "discret" }, t("monde.na")) : null))))))),
      h("p", { class: "discret source-donnees" }, `${t("monde.source")} : ${p.source}`));
  }).catch(() => zone.replaceChildren(h("p", { class: "discret" }, t("lois.aucun"))));
}

export function pageMonde(racine, { params, aller }) {
  const zone = h("div");
  racine.append(zone);
  if (params[0]) { vueDetail(zone, params[0], aller); return; }

  const carte = h("div", { class: "atlas" });
  const kpis = h("div", { class: "grille grille-4" });
  const puces = h("div", { class: "filtres" });
  const champ = h("input", { type: "search", class: "champ", placeholder: t("monde.recherche"), value: etat.recherche,
                             "aria-label": t("monde.recherche"), style: "max-width:320px" });

  function dessiner(pays) {
    const ind = INDICATEURS.find((i) => i.id === etat.indicateur);
    puces.replaceChildren(...INDICATEURS.map((i) => h("button", { type: "button",
      class: `puce-filtre${i.id === etat.indicateur ? " actif" : ""}`,
      onclick: () => { etat.indicateur = i.id; dessiner(pays); } }, t(i.cle))));

    const q = etat.recherche.trim().toLowerCase();
    const parRegion = {};
    for (const p of pays) (parRegion[p.region_fr] ||= []).push(p);
    carte.replaceChildren(...Object.entries(parRegion).sort().map(([region, liste]) => h("section", { class: "region-atlas" },
      h("h3", {}, region, h("small", {}, ` · ${liste.length}`)),
      h("div", { class: "tuiles-pays" }, ...liste.map((p) => {
        const v = valeurDe(p, ind);
        const masque = q && !p.pays_fr.toLowerCase().includes(q) && !p.pays_en.toLowerCase().includes(q) && !p.iso3.toLowerCase().includes(q);
        return h("a", { href: `#/monde/${p.iso3}`, class: `tuile-pays${masque ? " estompee" : ""}${p.iso3 === "TUN" ? " vedette-pays" : ""}`,
                        style: `--teinte:${couleur(v)}`, title: `${p.pays_fr} : ${v == null ? t("monde.nonmesure") : ind.type === "score" ? `${Math.round(v)}/100` : v ? t("securite.oui") : t("securite.non")}` },
          h("b", {}, p.iso3), h("span", {}, p.pays_fr));
      })))));

    const part = (code) => Math.round((pays.filter((p) => p.reponses[code] === true).length / pays.length) * 100);
    kpis.replaceChildren(
      ...[["Saf_Law_DomViolLaw", "monde.kpi.vd"], ["Saf_Law_DomViol_ProtOrd", "monde.kpi.ordonnance"],
          ["Saf_Law_SexHar_CybCpCr", "monde.kpi.cyber"], ["Saf_Law_FemicideCr", "monde.kpi.feminicide"]]
        .map(([code, cle]) => h("div", { class: "carte kpi" }, h("span", { class: "valeur" }, `${part(code)} %`), h("span", { class: "libelle" }, t(cle)))));
  }

  champ.addEventListener("input", () => { etat.recherche = champ.value; if (cache) dessiner(cache); });

  zone.append(
    h("header", { class: "titre-page" }, h("h1", {}, t("monde.titre")), h("p", {}, t("monde.sous"))),
    ongletsBibliotheque("monde"),
    kpis,
    h("div", { class: "ligne-formulaire", style: "margin-top:22px" }, champ,
      h("div", { class: "legende-atlas" }, h("span", {}, "0"), h("div", { class: "degrade-legende" }), h("span", {}, "100"))),
    puces,
    carte,
    h("p", { class: "discret source-donnees" }, `${t("monde.source")} : Banque mondiale, Women, Business and the Law 2026 (CC BY 4.0)`));
  charger().then(dessiner);
}
