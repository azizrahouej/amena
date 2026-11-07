// Espace partenaires : tableau de bord pour les associations.
// Uniquement des compteurs agrégés et les métriques du modèle, jamais de texte.

import { langueCourante, t } from "../i18n.js";
import { api, h, icone } from "../ui.js";

const LIBELLES = {
  fr: { urgence: "Urgence", juridique: "Juridique", soutien: "Soutien", information: "Orientation",
        fr: "Français", ar: "Arabe", dz: "Derja", llm: "LLM", extractif: "Extractif" },
  ar: { urgence: "خطر", juridique: "قانوني", soutien: "دعم", information: "توجيه",
        fr: "الفرنسية", ar: "العربية", dz: "الدارجة", llm: "نموذج لغوي", extractif: "استخراجي" },
};
const lib = (cle) => LIBELLES[langueCourante()][cle] ?? cle;
const pourcent = (x) => `${Math.round(x * 100)} %`;

function kpi(valeur, cle, nomIcone, variante = "") {
  return h("div", { class: "carte kpi" },
    h("span", { class: `icone-ronde ${variante}`, style: "margin-bottom:8px" }, icone(nomIcone)),
    h("span", { class: "valeur" }, valeur),
    h("span", { class: "libelle" }, t(cle)));
}

function barres(donnees, ordre) {
  const total = Object.values(donnees).reduce((a, b) => a + b, 0);
  if (!total) return h("p", { class: "discret" }, t("part.vide"));
  const cles = ordre.filter((c) => c in donnees).concat(Object.keys(donnees).filter((c) => !ordre.includes(c)));
  return h("div", { class: "barres" }, ...cles.map((c) => h("div", { class: "barre" },
    h("span", {}, lib(c)),
    h("div", { class: "piste" }, h("div", { class: c === "urgence" ? "danger" : "", style: `width:${(donnees[c] / total) * 100}%` })),
    h("b", {}, donnees[c]))));
}

// 14 derniers jours, jours sans message compris : l'axe du temps reste lisible.
function histogramme(parJour) {
  const compte = Object.fromEntries(parJour.map((j) => [j.jour, j.messages]));
  const jours = Array.from({ length: 14 }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (13 - i));
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    return { iso, jour: d.getDate(), n: compte[iso] || 0 };
  });
  const max = Math.max(1, ...jours.map((j) => j.n));
  return h("div", { class: "histogramme" }, ...jours.map((j) =>
    h("div", { class: "colonne", title: `${j.iso} : ${j.n}` },
      h("span", { class: "valeur-colonne" }, j.n || ""),
      h("div", { class: `baton${j.n ? "" : " vide"}`, style: `height:${j.n ? Math.max(6, (j.n / max) * 100) : 3}%` }),
      h("span", { class: "date-colonne" }, j.jour))));
}

function tableauModele(evaluation) {
  if (!evaluation) return h("p", { class: "discret" }, "python scripts/evaluer.py");
  const lignes = Object.entries(evaluation.triage_test_manuel).filter(([, m]) => m.accuracy != null);
  const r = evaluation.recherche;
  return h("div", {},
    h("table", { class: "tableau" },
      h("thead", {}, h("tr", {}, h("th", {}, "Triage"), h("th", {}, "Accuracy"), h("th", {}, "F1 macro"), h("th", {}, "Rappel urgence"))),
      h("tbody", {}, ...lignes.map(([nom, m]) => h("tr", { class: nom.includes("AMENA") ? "vedette" : "" },
        h("td", {}, nom.replaceAll("_", " ")), h("td", { class: "nombre" }, pourcent(m.accuracy)),
        h("td", { class: "nombre" }, pourcent(m.f1_macro)), h("td", { class: "nombre" }, pourcent(m.rappel_urgence)))))),
    h("table", { class: "tableau", style: "margin-top:18px" },
      h("thead", {}, h("tr", {}, h("th", {}, "Recherche"), h("th", {}, "Hit@1"), h("th", {}, "Hit@4"), h("th", {}, "MRR"))),
      h("tbody", {}, ...[["Fiches", r], ["Lois", evaluation.recherche_lois]].filter(([, m]) => m).map(([nom, m]) =>
        h("tr", {}, h("td", {}, `${nom} (${m.n_questions} q.)`),
          h("td", { class: "nombre" }, pourcent(m["hit@1"])), h("td", { class: "nombre" }, pourcent(m["hit@4"])),
          h("td", { class: "nombre" }, m.mrr.toFixed(2)))))));
}

export function pagePartenaires(racine) {
  const zone = h("div");
  racine.append(h("header", { class: "titre-page" }, h("h1", {}, t("part.titre")), h("p", {}, t("part.sous"))), zone);

  api("/api/statistiques").then((s) => {
    const u = s.usage;
    const avisTotal = (u.avis.utile || 0) + (u.avis.pas_utile || 0);
    zone.append(
      h("div", { class: "grille grille-4" },
        kpi(u.messages, "part.messages", "chat"),
        kpi(u.triage.urgence || 0, "part.urgences", "alerte", "danger"),
        kpi(avisTotal ? pourcent((u.avis.utile || 0) / avisTotal) : "—", "part.utile", "pouce", "vert"),
        kpi(u.risque.total || 0, "part.evaluations", "bouclier")),
      h("div", { class: "grille grille-2 section" },
        h("div", { class: "carte" }, h("h2", { style: "font-size:1rem;margin-bottom:16px" }, t("part.triage")),
          barres(u.triage, ["urgence", "juridique", "soutien", "information"])),
        h("div", { class: "carte" }, h("h2", { style: "font-size:1rem;margin-bottom:16px" }, t("part.langues")),
          barres(u.langue, ["fr", "ar", "dz"]))),
      h("div", { class: "carte section" }, h("h2", { style: "font-size:1rem;margin-bottom:6px" }, t("part.jours")),
        histogramme(u.par_jour)),
      h("div", { class: "grille grille-2 section" },
        h("div", { class: "carte" }, h("h2", { style: "font-size:1rem;margin-bottom:12px" }, t("part.modele")),
          tableauModele(s.evaluation)),
        h("div", { class: "carte" }, h("h2", { style: "font-size:1rem;margin-bottom:12px" }, t("part.config")),
          h("ul", { class: "liste-simple" },
            h("li", {}, icone("droits"), `${s.fiches} fiches · ${s.systeme.chunks} chunks indexés`),
            h("li", {}, icone("chat"), `Génération : ${{ claude: `Claude (${s.systeme.modele})`, ollama: `IA locale Ollama (${s.systeme.modele})` }[s.systeme.moteur] || "extractive (sans modèle)"}`),
            h("li", {}, icone("recherche"), `Recherche sémantique : ${s.systeme.embeddings ? "activée" : "lexicale (TF-IDF)"}`),
            h("li", {}, icone("cadenas"), `Statistiques : ${u.activees ? "activées (compteurs anonymes)" : "désactivées"}`)))));
  }).catch((erreur) => {
    // 401 : pas connectée ; 403 : compte sans rôle partenaire.
    const reserve = /HTTP 40[13]/.test(erreur.message);
    zone.append(h("div", { class: "carte", style: "display:flex;gap:16px;align-items:center;flex-wrap:wrap" },
      h("span", { class: "icone-ronde" }, icone("cadenas")),
      h("p", { style: "flex:1" }, reserve ? t("part.reserve") : t("chat.erreur")),
      reserve ? h("a", { href: "#/compte", class: "bouton bouton-primaire" }, t("compte.connexion")) : null));
  });
}
