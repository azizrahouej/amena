// « Ma sécurité » : questionnaire d'évaluation du danger + plan de sécurité à cocher.
// Les réponses ne quittent la page que pour être évaluées ; rien n'est enregistré.

import { PLAN, langueCourante, t } from "../i18n.js";
import { corps, heros } from "../affiche.js";
import { api, h, icone } from "../ui.js";

const etat = { onglet: "evaluation", index: -1, reponses: {}, resultat: null, coches: new Set() };
const NIVEAUX = ["faible", "modere", "eleve", "immediat"];

function vueEvaluation(zone, questions) {
  const rejouer = () => vueEvaluation(zone, questions);

  if (etat.resultat) {
    const r = etat.resultat;
    const rang = NIVEAUX.indexOf(r.niveau);
    zone.replaceChildren(h("div", { class: `carte resultat-niveau ${r.niveau} questionnaire` },
      h("span", { class: `pastille ${rang >= 2 ? "danger" : rang === 1 ? "orange" : "vert"}` }, icone("bouclier"), t(`niveau.${r.niveau}`)),
      h("div", { class: "jauge", "aria-hidden": "true" },
        ...NIVEAUX.map((_, i) => h("span", { class: i <= rang ? `plein ${r.niveau}` : "" }))),
      rang >= 2 ? h("div", { class: "contacts-message", style: "margin-bottom:16px" },
        ...["197", "193", "1899"].map((n) => h("a", { href: `tel:${n}` }, n))) : null,
      h("h2", { style: "font-size:1.1rem;margin-bottom:10px" }, t("securite.etapes")),
      h("ul", { class: "liste-simple" }, ...r.recommandations.map((x) => h("li", {}, icone("fleche", "icone icone-direction"), x))),
      r.facteurs.length ? h("details", { style: "margin-top:18px" },
        h("summary", { class: "discret", style: "cursor:pointer" }, `${t("securite.facteurs")} (${r.facteurs.length})`),
        h("ul", { style: "margin-top:8px" }, ...r.facteurs.map((f) => h("li", { class: "discret" }, f)))) : null,
      h("div", { style: "display:flex;gap:10px;flex-wrap:wrap;margin-top:22px" },
        h("button", { class: "bouton bouton-primaire", onclick: () => { etat.onglet = "plan"; dessiner(); } },
          icone("bouclier"), t("securite.versplan")),
        h("button", { class: "bouton bouton-secondaire", onclick: () => {
          etat.index = -1; etat.reponses = {}; etat.resultat = null; rejouer();
        } }, t("securite.recommencer")))));
    return;
  }

  if (etat.index < 0) {
    zone.replaceChildren(h("div", { class: "carte questionnaire" },
      h("span", { class: "icone-ronde danger", style: "margin-bottom:14px" }, icone("bouclier")),
      h("p", { style: "font-size:1.05rem" }, t("securite.intro")),
      h("button", { class: "bouton bouton-primaire", style: "margin-top:20px",
                    onclick: () => { etat.index = 0; rejouer(); } }, t("securite.commencer"), icone("fleche", "icone icone-direction"))));
    return;
  }

  const q = questions[etat.index];
  const repondre = async (valeur) => {
    etat.reponses[q.id] = valeur;
    // « Danger maintenant » : on n'attend pas la fin du questionnaire.
    if (etat.index === questions.length - 1 || (q.id === "danger_maintenant" && valeur)) {
      etat.resultat = await api("/api/risque", { method: "POST",
        body: { reponses: etat.reponses, langue: langueCourante() } });
    } else {
      etat.index += 1;
    }
    rejouer();
  };

  zone.replaceChildren(h("div", { class: "carte questionnaire" },
    h("div", { class: "discret" }, `${t("securite.question")} ${etat.index + 1} ${t("securite.sur")} ${questions.length}`),
    h("div", { class: "progression", role: "progressbar", "aria-valuemin": 0, "aria-valuemax": questions.length,
               "aria-valuenow": etat.index + 1 },
      h("div", { style: `width:${((etat.index + 1) / questions.length) * 100}%` })),
    h("p", { class: "question-texte", dir: "auto" }, q.texte),
    h("div", { class: "choix" },
      h("button", { onclick: () => repondre(true) }, t("securite.oui")),
      h("button", { onclick: () => repondre(false) }, t("securite.non")),
      h("button", { onclick: () => repondre(false) }, t("securite.nsp"))),
    etat.index > 0 ? h("button", { class: "bouton bouton-fantome", style: "margin-top:14px",
      onclick: () => { etat.index -= 1; rejouer(); } }, icone("retour", "icone icone-direction"), t("securite.precedent")) : null));
}

function vuePlan(zone) {
  const plan = PLAN[langueCourante()];
  zone.replaceChildren(
    h("div", { style: "display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px" },
      h("p", { class: "discret", style: "max-width:60ch" }, t("securite.plan.intro")),
      h("button", { class: "bouton bouton-secondaire", onclick: () => window.print() }, icone("imprimer"), t("securite.imprimer"))),
    h("div", { class: "grille grille-2" },
      ...plan.map((categorie, i) => {
        const compteur = h("span", { class: "pastille" });
        const majCompteur = () => {
          const faits = categorie.items.filter((_, j) => etat.coches.has(`${i}-${j}`)).length;
          compteur.textContent = `${faits}/${categorie.items.length} ${t("securite.pret")}`;
        };
        majCompteur();
        return h("div", { class: "carte plan-categorie" },
          h("h3", {}, h("span", {}, categorie.titre), compteur),
          ...categorie.items.map((item, j) => {
            const cle = `${i}-${j}`;
            const caseACocher = h("input", { type: "checkbox", checked: etat.coches.has(cle), onchange: (e) => {
              if (e.target.checked) etat.coches.add(cle); else etat.coches.delete(cle);
              majCompteur();
            } });
            return h("label", { class: "case" }, caseACocher, h("span", {}, item));
          }));
      })));
}

let racineCourante = null;
let questionsCache = {};

function dessiner() {
  const racine = racineCourante;
  const zone = h("div", { class: "securite-corps" });
  const onglet = (id, cle) => h("button", { class: "onglet-jour", type: "button", role: "tab",
    "aria-selected": etat.onglet === id ? "true" : "false",
    onclick: () => { etat.onglet = id; dessiner(); } }, t(cle));
  const lg = langueCourante();
  const questions = questionsCache[lg] ? Promise.resolve(questionsCache[lg])
    : api(`/api/risque/questions?langue=${lg}`).then((q) => (questionsCache[lg] = q));
  const plan = PLAN[lg];

  racine.replaceChildren(
    heros({
      surtitre: t("hp.securite.sur"), titre: t("securite.titre"), texte: t("securite.sous"), photo: "themis", teinte: "nuit",
      chiffres: [{ valeur: questions.then((q) => q.length), libelle: t("hp.questions") },
                 { valeur: NIVEAUX.length, libelle: t("hp.niveaux") },
                 { valeur: plan.reduce((n, c) => n + c.items.length, 0), libelle: t("hp.mesures") }],
      apres: h("div", { class: "onglets-jours", role: "tablist", "aria-label": t("securite.titre") },
        onglet("evaluation", "securite.onglet1"), onglet("plan", "securite.onglet2")),
    }),
    corps(zone));

  if (etat.onglet === "plan") { vuePlan(zone); return; }
  questions.then((q) => vueEvaluation(zone, q));
}

export function pageSecurite(racine) {
  racineCourante = racine;
  dessiner();
}
