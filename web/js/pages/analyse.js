// Analyse juridique : la situation décrite → une note structurée « comme une avocate ».
// La description n'est conservée nulle part (ni serveur, ni navigateur).

import { langueCourante, t } from "../i18n.js";
import { corps, heros } from "../affiche.js";
import { rendreMarkdown } from "../markdown.js";
import { api, h, icone } from "../ui.js";
import { preremplir } from "./chat.js";
import { preparerDossier } from "./dossier.js";

const etat = { situation: "", pays: "TN", resultat: null, lancerAuChargement: false };

// Depuis l'accueil : un domaine choisi pré-remplit la situation et lance l'analyse.
export function preparerAnalyse(texte) {
  etat.situation = texte;
  etat.resultat = null;
  etat.lancerAuChargement = true;
}

function bloc(nomIcone, titre, contenu, variante = "") {
  return h("section", { class: "carte revele visible" },
    h("h2", {}, h("span", { class: `icone-ronde ${variante}` }, icone(nomIcone)), titre), contenu);
}

function note(r, aller) {
  const enfants = [];
  if (r.urgence) {
    enfants.push(h("div", { class: "carte resultat-niveau eleve" },
      h("span", { class: "pastille danger" }, icone("alerte"), t("niveau.immediat")),
      h("div", { class: "contacts-message", style: "margin-top:12px" },
        ...["197", "193", "190", "1899"].map((n) => h("a", { href: `tel:${n}` }, n)))));
  }
  if (r.synthese) {
    enfants.push(h("section", { class: "carte synthese" }, h("h2", {}, icone("document"), t("analyse.synthese")),
      h("div", { class: "msg-corps", dir: "auto" }, rendreMarkdown(r.synthese))));
  }
  if (!r.qualifications.length) {
    enfants.push(h("div", { class: "avertissement" }, icone("alerte"),
      h("span", {}, r.pays === "TN" ? t("analyse.aucune") : t("analyse.horspays"))));
  } else {
    enfants.push(bloc("balance", t("analyse.qualification"), h("div", {},
      ...r.qualifications.map((q) => h("div", { class: "qualif" },
        h("h3", {}, q.libelle),
        h("p", { class: "discret" }, q.qualification),
        ...q.fondements.map((f) => h("a", { class: "fondement", href: `#/lois/${f.texte_id}`, dir: "auto" },
          // Article numéroté : « Art. 218 » ; sinon le titre de l'article (« Les formes de violence »).
          h("b", {}, /^\d/.test(f.article) ? `Art. ${f.article}` : f.titre || f.article), ` — ${f.texte}`, h("br"), h("span", { class: "discret" }, f.contenu))))))));
    enfants.push(h("div", { class: "grille grille-2" },
      bloc("liste", t("analyse.preuves"), h("ul", { class: "liste-coches" }, ...r.preuves.map((p) => h("li", {}, p))), "vert"),
      bloc("fleche", t("analyse.demarches"), h("ol", { class: "etapes-num" }, ...r.demarches.map((d) => h("li", {}, d))))));
    if (r.delais.length) {
      enfants.push(bloc("horloge", t("analyse.delais"), h("ul", { class: "liste-simple" },
        ...r.delais.map((d) => h("li", {}, icone("horloge"), d)))));
    }
    enfants.push(bloc("eclair", t("analyse.vigilance"), h("div", { class: "analyse-loi" },
      ...r.vigilance.map((v) => h("div", { class: "point vigilance" }, icone("eclair"), h("p", {}, v)))), "danger"));
  }
  if (r.limites_loi.length) {
    enfants.push(bloc("alerte", t("analyse.limites"), h("div", { class: "analyse-loi" },
      ...r.limites_loi.map((l) => h("div", { class: `point ${l.type}` }, icone(l.type === "lacune" ? "alerte" : "eclair"),
        h("div", {}, h("strong", {}, l.texte_titre), h("p", { dir: "auto" }, l.contenu))))), "danger"));
  }
  const ri = r.regard_international;
  if (ri) {
    enfants.push(bloc("globe", `${t("analyse.international")} — ${ri.pays}`, h("div", { class: "grille" },
      h("div", { class: "comparaison" },
        h("div", { class: "ligne-comparaison" }, h("strong", {}, t("analyse.score")), h("b", {}, `${Math.round(ri.score_cadre_legal)}/100`)),
        h("div", { class: "piste-comparee" }, h("div", { style: `width:${ri.score_cadre_legal}%;background:hsl(${Math.round(ri.score_cadre_legal * 1.35)} 62% 46%)` })),
        h("div", { class: "legende-comparaison" }, h("span", {}, `${t("monde.region")} ${ri.moyenne_region}`), h("span", {}, ri.source))),
      h("div", { class: "grille grille-2" },
        h("div", {}, h("h3", { style: "font-size:.95rem;margin-bottom:8px" }, t("analyse.acquis")),
          h("ul", { class: "liste-indicateurs" }, ...ri.acquis.slice(0, 6).map((a) => h("li", { class: "oui" }, h("span", { class: "marque" }, "✓"),
            h("div", {}, h("p", {}, a.question), h("small", { class: "discret", dir: "auto" }, a.base_legale)))))),
        h("div", {}, h("h3", { style: "font-size:.95rem;margin-bottom:8px" }, t("analyse.lacunesbm")),
          h("ul", { class: "liste-indicateurs" }, ...ri.lacunes.map((l) => h("li", { class: "non" }, h("span", { class: "marque" }, "✗"),
            h("div", {}, h("p", {}, l.question), h("small", { class: "discret" }, l.theme))))))),
      h("a", { href: `#/monde/${ri.iso3}`, class: "bouton bouton-secondaire", style: "justify-self:start" }, icone("globe"), t("monde.retour")))));
  }
  if (r.textes_complementaires.length) {
    enfants.push(bloc("globe", t("analyse.complementaires"), h("div", { class: "grille" },
      ...r.textes_complementaires.map((c) => h("a", { href: `#/lois/${c.texte_id}`, class: "fondement carte resultat" },
        h("strong", { dir: "auto" }, `${c.pays} · ${c.texte_titre} — Art. ${c.numero}`),
        h("p", { dir: "auto" }, `${c.titre} : ${c.contenu}`))))));
  }
  enfants.push(h("div", { class: "avertissement" }, icone("alerte"), h("span", {}, r.avertissement)));
  enfants.push(h("div", { style: "display:flex;gap:10px;flex-wrap:wrap" },
    h("button", { class: "bouton bouton-primaire", onclick: () => { preparerDossier({ faits: etat.situation, analyse: r }); aller("dossier"); } },
      icone("document"), t("chat2.dossier")),
    h("button", { class: "bouton bouton-secondaire", onclick: () => window.print() }, icone("imprimer"), t("analyse.imprimer")),
    h("button", { class: "bouton bouton-secondaire", onclick: () => { preremplir(etat.situation); aller("chat"); } },
      icone("chat"), t("analyse.chat"))));
  return h("div", { class: "note-juridique" }, ...enfants);
}

export function pageAnalyse(racine, { aller }) {
  const resultat = h("div");
  const zone = h("textarea", { dir: "auto", placeholder: t("analyse.placeholder"), "aria-label": t("analyse.titre") });
  zone.value = etat.situation;
  const choixPays = h("select", { "aria-label": t("analyse.pays") });
  const bouton = h("button", { class: "bouton bouton-primaire bouton-lueur", type: "submit" }, icone("balance"), t("analyse.lancer"));
  const erreur = h("p", { class: "erreur-formulaire", hidden: true });

  // Pays de la bibliothèque (analyse détaillée) puis les 190 pays de la Banque mondiale.
  Promise.all([api("/api/lois/pays"), api("/api/monde")]).then(([pays, monde]) => {
    const lg = langueCourante();
    const dejaListes = new Set(["TUN", "MAR", "DZA", "FRA", "ESP", "LBN"]);
    choixPays.replaceChildren(
      h("optgroup", { label: t("nav.lois") }, ...pays.filter((p) => p.code !== "INT").map((p) =>
        h("option", { value: p.code, selected: p.code === etat.pays }, lg === "ar" ? p.nom_ar : p.nom_fr))),
      h("optgroup", { label: t("analyse.autrespays") }, ...monde.filter((p) => !dejaListes.has(p.iso3)).map((p) =>
        h("option", { value: p.iso3, selected: p.iso3 === etat.pays }, p.pays_fr))));
  });

  async function lancer() {
    etat.situation = zone.value.trim();
    etat.pays = choixPays.value || "TN";
    if (etat.situation.length < 15) { erreur.textContent = t("analyse.court"); erreur.hidden = false; return; }
    erreur.hidden = true;
    bouton.disabled = true;
    resultat.replaceChildren(h("div", { class: "carte chargement-analyse" },
      h("p", { class: "discret" }, t("analyse.encours")),
      ...[90, 70, 80, 55].map((w) => h("div", { class: "squelette", style: `width:${w}%` }))));
    try {
      etat.resultat = await api("/api/analyse", { method: "POST", body: { situation: etat.situation, pays: etat.pays } });
      resultat.replaceChildren(note(etat.resultat, aller));
      resultat.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch {
      resultat.replaceChildren(h("p", { class: "erreur-formulaire" }, t("chat.erreur")));
    } finally {
      bouton.disabled = false;
    }
  }

  const exemples = h("div", { class: "exemples" }, h("span", { class: "discret" }, t("analyse.exemples")),
    ...["analyse.ex1", "analyse.ex2", "analyse.ex3", "analyse.ex4"].map((c) =>
      h("button", { type: "button", onclick: () => { zone.value = t(c); zone.focus(); } }, t(c))));

  const stats = api("/api/sante").then((s) => s.bibliotheque);
  racine.append(
    heros({
      surtitre: t("hp.analyse.sur"), titre: t("analyse.titre"), texte: t("analyse.sous"), photo: "marteau", teinte: "rouge",
      chiffres: [{ valeur: stats.then((b) => b.textes), libelle: t("hp.textes") },
                 { valeur: stats.then((b) => b.articles), libelle: t("hp.articles") },
                 { valeur: stats.then((b) => b.pays_monde), libelle: t("hp.pays") }],
      actions: [h("a", { href: "#formulaire-analyse", class: "bouton bouton-blanc", onclick: (e) => {
        e.preventDefault(); zone.focus(); zone.scrollIntoView({ behavior: "smooth", block: "center" }); } },
        t("analyse.lancer"), icone("fleche", "icone icone-direction"))],
    }),
    h("section", { class: "diapo diapo-nuit bande-etapes", "data-diapo": "" },
      h("ol", { class: "etapes-anneaux" }, ...[1, 2, 3, 4].map((i) => h("li", {},
        h("b", {}, `0${i}`), h("strong", {}, t(`hp.a${i}`)), h("small", {}, t(`hp.a${i}.s`)))))),
    corps(
      h("div", { class: "analyse-disposition", id: "formulaire-analyse" },
        h("div", {},
          h("form", { class: "carte zone-situation", onsubmit: (e) => { e.preventDefault(); lancer(); } },
            h("label", { class: "libelle-grand" }, t("hp.decrivez")),
            zone, exemples, erreur,
            h("div", { class: "ligne-formulaire" },
              h("label", { class: "case-ligne" }, t("analyse.pays"), choixPays),
              bouton)),
          resultat),
        h("aside", { class: "panneau" },
          h("div", { class: "carte carte-sombre" },
            h("h2", {}, t("analyse.comment.t")),
            h("ol", { class: "etapes-num" }, ...[1, 2, 3, 4].map((i) => h("li", {}, t(`analyse.comment.${i}`))))),
          h("div", { class: "note-confidentialite" }, icone("cadenas"), h("span", {}, t("analyse.confidentiel")))))));

  if (etat.resultat) resultat.replaceChildren(note(etat.resultat, aller));
  if (etat.lancerAuChargement) {
    etat.lancerAuChargement = false;
    lancer();
  }
}
