// Bibliothèque juridique : liste filtrable des textes (pays, domaine), recherche plein texte
// dans les articles (FTS5), et page de détail avec l'analyse forces / lacunes / vigilance.

import { langueCourante, t } from "../i18n.js";
import { session, suivre, toast } from "../session.js";
import { corps, heros } from "../affiche.js";
import { api, h, icone } from "../ui.js";

export function ongletsBibliotheque(actif) {
  return h("nav", { class: "onglets-liens" },
    h("a", { href: "#/lois", class: actif === "lois" ? "actif" : "" }, t("lois.onglet.lois")),
    h("a", { href: "#/monde", class: actif === "monde" ? "actif" : "" }, `🌍 ${t("lois.onglet.monde")}`),
    h("a", { href: "#/droits", class: actif === "fiches" ? "actif" : "" }, t("lois.onglet.fiches")));
}

const filtres = { pays: null, domaine: null };
const ICONES_ANALYSE = { force: "bouclier", lacune: "alerte", vigilance: "eclair" };

export function boutonFavori(element) {
  const bouton = h("button", { class: "bouton bouton-secondaire bouton-favori", type: "button" },
    icone("etoile"), h("span", {}, t("lois.favori")));
  bouton.onclick = async () => {
    if (!session()) { toast(t("lois.favori.connexion")); return; }
    await suivre(element, "favori");
    bouton.classList.add("actif");
    bouton.lastChild.textContent = t("lois.favori.ok");
    toast(t("lois.favori.ok"));
  };
  return bouton;
}

function carteLoi(texte) {
  const lg = langueCourante();
  return h("a", { href: `#/lois/${texte.id}`, class: "carte carte-loi" },
    h("div", { class: "haut" },
      h("span", { class: "drapeau" }, texte.pays),
      h("span", { class: "discret" }, lg === "ar" ? texte.pays_nom_ar : texte.pays_nom)),
    h("h3", { dir: "auto" }, texte.titre),
    h("span", { class: "ref", dir: "auto" }, texte.reference),
    h("p", { class: "resume", dir: "auto" }, texte.resume),
    h("div", { class: "bas" },
      texte.domaines.includes("texte intégral") ? h("span", { class: "pastille integral" }, t("lois.integral")) : null,
      h("span", { class: "pastille" }, `${texte.nb_articles} ${t("lois.articles")}`),
      texte.nb_lacunes ? h("span", { class: "pastille danger" }, `${texte.nb_lacunes} ${t("lois.lacunes")}`) : null,
      ...texte.domaines.filter((d) => d !== "texte intégral").slice(0, 2).map((d) => h("span", { class: "pastille vert" }, d))));
}

function vueDetail(zone, texteId) {
  api(`/api/lois/${encodeURIComponent(texteId)}`).then((texte) => {
    suivre(`loi:${texte.id}`);
    const lg = langueCourante();
    zone.replaceChildren(h("div", { class: "lecture" },
      h("nav", { class: "sommaire" },
        h("h2", {}, t("droits.sommaire")),
        ...texte.articles.map((a, i) => h("a", { href: "#", dir: "auto", onclick: (e) => {
          e.preventDefault();
          document.getElementById(`art-${i}`)?.scrollIntoView({ behavior: "smooth" });
          // Texte intégral : les articles n'ont pas de titre, on montre le début du contenu.
        } }, a.titre ? `${a.numero} · ${a.titre}` : `Art. ${a.numero} · ${a.contenu.slice(0, 38)}…`)),
        h("a", { href: "#", onclick: (e) => { e.preventDefault(); document.getElementById("analyse-texte")?.scrollIntoView({ behavior: "smooth" }); } },
          `⚖ ${t("lois.analyse")}`)),
      h("article", { class: "carte article" },
        h("a", { href: "#/lois", class: "bouton bouton-fantome" }, icone("retour", "icone icone-direction"), t("lois.retour")),
        h("div", { style: "display:flex;gap:8px;align-items:center;margin:10px 0" },
          h("span", { class: "drapeau" }, texte.pays),
          h("span", { class: "discret" }, lg === "ar" ? texte.pays_nom_ar : texte.pays_nom),
          h("span", { class: "pastille" }, texte.type)),
        h("h1", { dir: "auto" }, texte.titre),
        h("p", { class: "discret", dir: "auto" }, `${t("lois.reference")} : ${texte.reference}`),
        h("p", { class: "discret", dir: "auto" }, `${t("lois.source")} : ${texte.source}`,
          texte.url ? h("span", {}, " · ", h("a", { href: texte.url, target: "_blank", rel: "noopener noreferrer" }, texte.url)) : null),
        h("p", { dir: "auto", style: "margin:16px 0" }, texte.resume),
        h("div", { class: "avertissement" }, icone("alerte"),
          h("span", {}, t(texte.domaines.includes("texte intégral") ? "lois.avert.integral" : "lois.avert"))),
        h("div", { style: "margin:8px 0 6px" }, boutonFavori(`loi:${texte.id}`)),
        ...texte.articles.map((a, i) => h("section", { class: "article-loi", id: `art-${i}` },
          h("span", { class: "num" }, `Art. ${a.numero}`),
          h("h3", { dir: "auto" }, a.titre),
          h("p", { dir: "auto" }, a.contenu))),
        h("section", { class: "article-loi", id: "analyse-texte" },
          h("h2", { style: "font-size:1.15rem;margin-bottom:14px" }, `⚖ ${t("lois.analyse")}`),
          h("div", { class: "analyse-loi" },
            ...texte.analyses.map((a) => h("div", { class: `point ${a.type}` }, icone(ICONES_ANALYSE[a.type]),
              h("div", {}, h("strong", {}, t(`lois.${a.type}`)), h("p", { dir: "auto" }, a.contenu)))))))));
  }).catch(() => zone.replaceChildren(h("p", { class: "discret" }, t("lois.aucun"))));
}

export function pageLois(racine, { params }) {
  const zone = h("div");
  if (params[0]) { racine.append(corps(zone)); vueDetail(zone, params[0]); return; }

  const grille = h("div", { class: "grille grille-3" });
  const barrePays = h("div", { class: "filtres" });
  const resultats = h("div", { class: "grille", "aria-live": "polite" });
  const champ = h("input", { type: "search", dir: "auto", placeholder: t("lois.recherche"), "aria-label": t("lois.recherche") });

  function charger() {
    const p = new URLSearchParams();
    if (filtres.pays) p.set("pays", filtres.pays);
    api(`/api/lois?${p}`).then((textes) => {
      grille.replaceChildren(...(textes.length ? textes.map(carteLoi) : [h("p", { class: "discret" }, t("lois.aucun"))]));
    });
  }

  api("/api/lois/pays").then((pays) => {
    const lg = langueCourante();
    const puce = (code, libelle, n) => h("button", { class: `puce-filtre${filtres.pays === code ? " actif" : ""}`, type: "button",
      onclick: () => { filtres.pays = code; dessinerPuces(); charger(); } }, libelle, n != null ? h("small", {}, n) : null);
    function dessinerPuces() {
      barrePays.replaceChildren(puce(null, t("lois.tous")),
        ...pays.map((p) => puce(p.code, lg === "ar" ? p.nom_ar : p.nom_fr, p.nb_textes)));
    }
    dessinerPuces();
  });

  let minuterie = null;
  champ.addEventListener("input", () => {
    clearTimeout(minuterie);
    const q = champ.value.trim();
    if (q.length < 3) { resultats.replaceChildren(); return; }
    minuterie = setTimeout(async () => {
      const trouves = await api(`/api/lois/recherche?q=${encodeURIComponent(q)}${filtres.pays ? `&pays=${filtres.pays}` : ""}`).catch(() => []);
      resultats.replaceChildren(
        h("h2", { class: "discret" }, trouves.length ? t("droits.resultats") : t("droits.aucun")),
        ...trouves.slice(0, 6).map((r) => h("a", { href: `#/lois/${r.texte_id}`, class: "carte resultat" },
          h("strong", { dir: "auto" }, `${r.pays} · ${r.texte_titre} — Art. ${r.numero}`),
          h("p", { dir: "auto" }, `${r.titre} : ${r.contenu}`))));
    }, 250);
  });

  const stats = api("/api/sante").then((s) => s.bibliotheque);
  racine.append(
    heros({
      surtitre: t("hp.lois.sur"), titre: t("lois.titre"), texte: t("lois.sous"), photo: "bibliotheque", teinte: "nuit",
      chiffres: [{ valeur: stats.then((b) => b.textes), libelle: t("hp.textes") },
                 { valeur: stats.then((b) => b.articles), libelle: t("hp.articles") },
                 { valeur: stats.then((b) => b.pays), libelle: t("hp.pays.biblio") }],
      apres: h("div", { class: "champ-recherche recherche-heros" }, icone("recherche"), champ),
    }),
    corps(zone));
  zone.append(
    ongletsBibliotheque("lois"),
    resultats,
    barrePays,
    grille);
  charger();
}
