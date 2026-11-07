// État de connexion et services partagés (notifications, suivi des consultations, révélations).
// Le jeton de session est dans un cookie HttpOnly : JavaScript ne peut pas le lire.

import { api, h } from "./ui.js";

let utilisatrice = null;
const abonnes = new Set();

export const session = () => utilisatrice;
export const surChangement = (fonction) => abonnes.add(fonction);
const notifier = () => abonnes.forEach((f) => f(utilisatrice));

export async function chargerSession() {
  utilisatrice = await api("/api/auth/moi").catch(() => null);
  notifier();
  return utilisatrice;
}

export async function seConnecter(identifiant, motDePasse, rester) {
  utilisatrice = await envoyer("/api/auth/connexion", { identifiant, mot_de_passe: motDePasse, rester });
  notifier();
  return utilisatrice;
}

export async function sInscrire(donnees) {
  utilisatrice = await envoyer("/api/auth/inscription", donnees);
  notifier();
  return utilisatrice;
}

export async function seDeconnecter() {
  await api("/api/auth/deconnexion", { method: "POST" }).catch(() => {});
  utilisatrice = null;
  notifier();
}

export function mettreAJour(profil) { utilisatrice = profil; notifier(); }

// Comme api(), mais renvoie le message d'erreur du serveur (« mot de passe incorrect »…).
export async function envoyer(chemin, corps, methode = "POST") {
  const reponse = await fetch(chemin, { method: methode, headers: { "Content-Type": "application/json" },
                                        body: corps ? JSON.stringify(corps) : undefined });
  const donnees = await reponse.json().catch(() => ({}));
  if (!reponse.ok) {
    const detail = Array.isArray(donnees.detail) ? "Vérifiez les champs du formulaire." : donnees.detail;
    throw new Error(detail || `Erreur ${reponse.status}`);
  }
  return donnees;
}

// Une consultation n'est enregistrée que si l'utilisatrice est connectée.
export function suivre(element, action = "vue") {
  if (!utilisatrice) return Promise.resolve(false);
  return api("/api/interactions", { method: "POST", body: { element, action } }).catch(() => false);
}

export function toast(message) {
  const zone = document.getElementById("toasts");
  const el = h("div", { class: "toast" }, message);
  zone.append(el);
  setTimeout(() => el.remove(), 3200);
}

// Révèle en douceur les éléments .revele quand ils entrent dans l'écran.
const observateur = "IntersectionObserver" in window
  ? new IntersectionObserver((entrees) => entrees.forEach((e) => {
      if (e.isIntersecting) { e.target.classList.add("visible"); observateur.unobserve(e.target); }
    }), { threshold: 0.12 })
  : null;

export function reveler(racine) {
  racine.querySelectorAll(".revele").forEach((el) => {
    if (observateur) observateur.observe(el); else el.classList.add("visible");
  });
}

// Compteur animé (0 → valeur).
export function compter(el, valeur, duree = 1200) {
  const debut = performance.now();
  const etape = (t) => {
    const p = Math.min(1, (t - debut) / duree);
    el.textContent = Math.round(valeur * (1 - (1 - p) ** 3));
    if (p < 1) requestAnimationFrame(etape);
  };
  requestAnimationFrame(etape);
}
