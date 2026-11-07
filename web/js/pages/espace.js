// Espace personnel : recommandations hybrides, favoris, consultations récentes, préférences.

import { langueCourante, t } from "../i18n.js";
import { mettreAJour, seDeconnecter, session, toast } from "../session.js";
import { api, h, icone } from "../ui.js";

const lien = (e) => (e.type === "loi" ? `#/lois/${e.id.slice(4)}` : `#/droits/${e.id.slice(6)}`);
const typeLibelle = (e) => (e.type === "loi" ? t("espace.loi") : t("espace.fiche"));

function carteReco(r, i) {
  return h("a", { href: lien(r), class: `carte carte-reco revele visible` },
    h("div", { style: "display:flex;gap:6px;align-items:center" },
      h("span", { class: "drapeau" }, r.pays), h("span", { class: "pastille" }, typeLibelle(r))),
    h("h3", { dir: "auto" }, r.titre),
    h("span", { class: "raison" }, icone("etoile"), r.raison),
    h("div", { class: "barre-score", title: `score ${r.score}` }, h("div", { style: `width:${Math.max(8, r.score * 100)}%` })));
}

function listeElements(elements, vide, retirable) {
  if (!elements.length) return h("p", { class: "discret" }, vide);
  return h("ul", { class: "liste-simple" }, ...elements.map((e) => h("li", { style: "justify-content:space-between" },
    h("a", { href: lien(e), dir: "auto", style: "text-decoration:none;color:inherit;flex:1" },
      h("span", { class: "drapeau", style: "margin-inline-end:8px" }, e.pays), e.titre),
    retirable ? h("button", { class: "action-icone", title: "✕", "aria-label": "✕", onclick: async (ev) => {
      await api(`/api/favoris/${encodeURIComponent(e.id)}`, { method: "DELETE" });
      ev.currentTarget.closest("li").remove();
    } }, icone("sortie")) : null)));
}

export function pageEspace(racine, { aller }) {
  if (!session()) {
    // La session se charge peut-être encore : on réessaie une fois avant de rediriger.
    api("/api/auth/moi").then((u) => (u ? (mettreAJour(u), pageEspace(racine, { aller })) : aller("compte")));
    return;
  }
  const zone = h("div");
  racine.append(zone);

  api("/api/espace").then((d) => {
    const u = d.profil;
    const lg = langueCourante();
    const interets = h("div", { class: "grille-interets" });
    const pays = h("select", { class: "champ" });
    api("/api/auth/interets").then((liste) => interets.replaceChildren(...liste.map((i) =>
      h("label", {}, h("input", { type: "checkbox", value: i, checked: u.interets.includes(i) }), i))));
    api("/api/lois/pays").then((liste) => pays.replaceChildren(...liste.filter((p) => p.code !== "INT").map((p) =>
      h("option", { value: p.code, selected: p.code === u.pays }, lg === "ar" ? p.nom_ar : p.nom_fr))));

    zone.replaceChildren(
      h("div", { class: "entete-espace" },
        h("span", { class: "grand-avatar" }, u.pseudo.slice(0, 1).toUpperCase()),
        h("div", {}, h("h1", {}, `${t("compte.bienvenue")}, ${u.pseudo}`),
          h("p", { class: "discret" }, `${t("espace.membre")} ${u.cree_le.slice(0, 10)}`)),
        u.role !== "utilisatrice" ? h("a", { href: "#/partenaires", class: "bouton bouton-secondaire" }, icone("graphique"), t("nav.partenaires")) : null,
        h("button", { class: "bouton bouton-secondaire", onclick: async () => { await seDeconnecter(); aller(""); } },
          icone("sortie"), t("espace.deconnexion"))),

      h("section", {},
        h("h2", { style: "font-size:1.25rem" }, t("espace.reco")),
        h("p", { class: "discret", style: "margin:4px 0 16px" }, t("espace.reco.sous")),
        h("div", { class: "grille grille-3" }, ...d.recommandations.map(carteReco))),

      h("div", { class: "grille grille-2 section" },
        h("div", { class: "carte" }, h("h2", { style: "font-size:1.05rem;margin-bottom:14px" }, `★ ${t("espace.favoris")}`),
          listeElements(d.favoris, t("espace.vide.favoris"), true)),
        h("div", { class: "carte" }, h("h2", { style: "font-size:1.05rem;margin-bottom:14px" }, t("espace.recents")),
          listeElements(d.recents, t("espace.vide.recents"), false))),

      h("div", { class: "grille grille-2 section" },
        h("div", { class: "carte" },
          h("h2", { style: "font-size:1.05rem;margin-bottom:14px" }, t("espace.parametres")),
          h("div", { class: "champ-groupe" }, h("label", {}, t("compte.pays")), pays),
          h("div", { class: "champ-groupe", style: "margin-top:14px" }, h("label", {}, t("compte.interets")), interets),
          h("button", { class: "bouton bouton-primaire", style: "margin-top:16px", onclick: async () => {
            const choisis = [...interets.querySelectorAll("input:checked")].map((c) => c.value);
            mettreAJour(await api("/api/auth/moi", { method: "PATCH", body: { pays: pays.value, interets: choisis } }));
            toast(t("espace.enregistre"));
            pageEspace(racine.replaceChildren() || racine, { aller });
          } }, t("espace.enregistrer"))),
        h("div", { class: "carte zone-danger" },
          h("h2", { style: "font-size:1.05rem;margin-bottom:8px" }, t("espace.supprimer")),
          h("p", { class: "discret", style: "margin-bottom:16px" }, t("espace.supprimer.d")),
          h("button", { class: "bouton bouton-secondaire", style: "color:var(--danger);border-color:var(--danger)", onclick: async () => {
            if (!window.confirm(t("espace.supprimer.confirmer"))) return;
            await api("/api/auth/moi", { method: "DELETE" });
            mettreAJour(null);
            toast(t("espace.supprime"));
            aller("");
          } }, icone("corbeille"), t("espace.supprimer")))));
  }).catch(() => aller("compte"));
}
