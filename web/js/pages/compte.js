// Connexion et inscription. Un compte est facultatif : tout le site fonctionne sans.

import { balance3d } from "../balance3d.js";
import { langueCourante, t } from "../i18n.js";
import { sInscrire, seConnecter, session, toast } from "../session.js";
import { api, h, icone } from "../ui.js";

let mode = "connexion";

function champ(id, libelle, attributs, aide) {
  return h("div", { class: "champ-groupe" },
    h("label", { for: id }, libelle),
    h("input", { id, class: "champ", ...attributs }),
    aide ? h("small", {}, aide) : null);
}

export function pageCompte(racine, { aller }) {
  if (session()) { aller("espace"); return; }

  const erreur = h("p", { class: "erreur-formulaire", hidden: true, role: "alert" });
  const formulaire = h("form", { class: "compte-formulaire", novalidate: true });

  function dessiner() {
    const inscription = mode === "inscription";
    const elements = [
      h("h1", {}, t(inscription ? "compte.titre.inscription" : "compte.titre.connexion")),
      erreur,
    ];
    if (inscription) {
      elements.push(
        champ("pseudo", t("compte.pseudo"), { name: "pseudo", autocomplete: "username", required: true, minlength: 3, maxlength: 30 }, t("compte.pseudo.aide")),
        champ("email", t("compte.email"), { name: "email", type: "email", autocomplete: "email" }, t("compte.email.aide")),
        champ("mdp", t("compte.mdp"), { name: "mot_de_passe", type: "password", autocomplete: "new-password", required: true, minlength: 8 }, t("compte.mdp.aide")));
      const pays = h("select", { id: "pays", name: "pays", class: "champ" });
      const interets = h("div", { class: "grille-interets" });
      api("/api/lois/pays").then((liste) => pays.replaceChildren(...liste.filter((p) => p.code !== "INT").map((p) =>
        h("option", { value: p.code }, langueCourante() === "ar" ? p.nom_ar : p.nom_fr))));
      api("/api/auth/interets").then((liste) => interets.replaceChildren(...liste.map((i) =>
        h("label", {}, h("input", { type: "checkbox", name: "interets", value: i }), i))));
      elements.push(
        h("div", { class: "champ-groupe" }, h("label", { for: "pays" }, t("compte.pays")), pays),
        h("div", { class: "champ-groupe" }, h("label", {}, t("compte.interets")), interets));
    } else {
      elements.push(
        champ("identifiant", t("compte.identifiant"), { name: "identifiant", autocomplete: "username", required: true }),
        champ("mdp", t("compte.mdp"), { name: "mot_de_passe", type: "password", autocomplete: "current-password", required: true }),
        h("label", { class: "case-ligne" }, h("input", { type: "checkbox", name: "rester" }), t("compte.rester")));
    }
    elements.push(
      h("div", { class: "note-confidentialite" }, icone("cadenas"), h("span", {}, t("compte.confidentialite"))),
      h("button", { class: "bouton bouton-primaire", type: "submit" }, t(inscription ? "compte.sinscrire" : "compte.seconnecter")),
      h("button", { class: "bouton bouton-fantome", type: "button", onclick: () => {
        mode = inscription ? "connexion" : "inscription";
        erreur.hidden = true;
        dessiner();
      } }, t(inscription ? "compte.basculer.connexion" : "compte.basculer.inscription")));
    formulaire.replaceChildren(...elements);
  }

  formulaire.onsubmit = async (e) => {
    e.preventDefault();
    const d = new FormData(formulaire);
    const bouton = formulaire.querySelector("button[type=submit]");
    bouton.disabled = true;
    try {
      const u = mode === "inscription"
        ? await sInscrire({ pseudo: d.get("pseudo"), email: d.get("email") || null, mot_de_passe: d.get("mot_de_passe"),
                            pays: d.get("pays") || "TN", interets: d.getAll("interets"), langue: langueCourante() })
        : await seConnecter(d.get("identifiant"), d.get("mot_de_passe"), d.get("rester") === "on");
      toast(`${t("compte.bienvenue")}, ${u.pseudo}`);
      aller("espace");
    } catch (err) {
      erreur.textContent = err.message;
      erreur.hidden = false;
      bouton.disabled = false;
    }
  };

  dessiner();
  racine.append(h("div", { class: "page-compte" },
    h("div", { class: "compte-visuel" }, balance3d(),
      h("h2", {}, t("compte.visuel.t")), h("p", {}, t("compte.visuel.d"))),
    formulaire));
}
