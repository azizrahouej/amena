// Moteur d'effets « 3D / 4D / 5D », sans bibliothèque :
//   3D  profondeur : cartes qui s'inclinent sous le pointeur avec un reflet, couches en parallaxe ;
//   4D  temps      : poussière d'or en perspective, révélations 3D au défilement, transitions de page ;
//   5D  interaction: lumière qui suit le curseur, boutons aimantés, barre de progression.
// Tout se désactive si l'utilisatrice demande moins d'animations, et sur écran tactile pour
// l'inclinaison (qui n'a pas de sens sans pointeur).

const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const pointeurFin = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

const INCLINABLES = ".carte-domaine, .carte-loi, .carte-reco, .tuile, .domaine, .kpi, .carte-appel, .etape-romaine, " +
                    ".comparaison, .carte-fiche, .illustration-3d, .carte-bienvenue, .t3d-direct, .t3d-contact";
const AIMANTES = ".bouton-primaire, .bouton-rond.principal";
const LUMINEUX = ".heros-cabinet, .t3d-cadre, .vitrine, .bandeau-nuit, .appel-final, .engagements .colonne-gauche, .chat-accueil";
const PARALLAXES = ".heros-cabinet, .tableau-3d";

// --- 3D : inclinaison avec reflet -------------------------------------------------
function inclinable(el) {
  if (el.dataset.incline) return;
  el.dataset.incline = "1";
  el.classList.add("incline");
  const reflet = document.createElement("span");
  reflet.className = "reflet";
  reflet.setAttribute("aria-hidden", "true");
  el.append(reflet);
  const force = el.matches(".domaine, .kpi") ? 5 : 8;
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect();
    const x = (e.clientX - r.left) / r.width;
    const y = (e.clientY - r.top) / r.height;
    el.style.setProperty("--ry", `${((x - 0.5) * 2 * force).toFixed(2)}deg`);
    el.style.setProperty("--rx", `${((0.5 - y) * 2 * force).toFixed(2)}deg`);
    el.style.setProperty("--mx", `${(x * 100).toFixed(1)}%`);
    el.style.setProperty("--my", `${(y * 100).toFixed(1)}%`);
    el.classList.add("survol-3d");
  });
  el.addEventListener("pointerleave", () => {
    el.style.setProperty("--rx", "0deg");
    el.style.setProperty("--ry", "0deg");
    el.classList.remove("survol-3d");
  });
}

// --- 5D : boutons aimantés ------------------------------------------------------------
function aimante(el) {
  if (el.dataset.aimant) return;
  el.dataset.aimant = "1";
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect();
    const dx = e.clientX - (r.left + r.width / 2);
    const dy = e.clientY - (r.top + r.height / 2);
    el.style.transform = `translate(${dx * 0.18}px, ${dy * 0.28}px)`;
  });
  el.addEventListener("pointerleave", () => { el.style.transform = ""; });
}

// --- 5D : lumière qui suit le pointeur sur les zones sombres ----------------------------------
function lumineux(el) {
  if (el.dataset.lumiere) return;
  el.dataset.lumiere = "1";
  el.classList.add("projecteur");
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect();
    el.style.setProperty("--sx", `${e.clientX - r.left}px`);
    el.style.setProperty("--sy", `${e.clientY - r.top}px`);
  });
}

// --- 3D : parallaxe des couches [data-profondeur] ----------------------------------------------
function parallaxe(conteneur) {
  const couches = [...conteneur.querySelectorAll("[data-profondeur]")];
  if (!couches.length || conteneur.dataset.parallaxe) return;
  conteneur.dataset.parallaxe = "1";
  let px = 0, py = 0;
  const appliquer = () => {
    const defilement = Math.min(window.scrollY, 900);
    for (const c of couches) {
      const p = Number(c.dataset.profondeur);
      // data-rotation : la couche pivote aussi, comme une maquette qu'on regarde de côté.
      const r = Number(c.dataset.rotation || 0);
      const pivot = r ? ` rotateX(${(-py * r).toFixed(2)}deg) rotateY(${(px * r * 1.6).toFixed(2)}deg)` : "";
      // data-defilement="0" : la couche ne glisse pas au défilement (elle ne doit rien recouvrir).
      const glisse = c.dataset.defilement === "0" ? 0 : defilement * p * 0.35;
      c.style.transform = `translate3d(${(px * p * 30).toFixed(1)}px, ${(py * p * 22 + glisse).toFixed(1)}px, 0)${pivot}`;
    }
  };
  conteneur.addEventListener("pointermove", (e) => {
    const r = conteneur.getBoundingClientRect();
    px = (e.clientX - r.left) / r.width - 0.5;
    py = (e.clientY - r.top) / r.height - 0.5;
    requestAnimationFrame(appliquer);
  });
  window.addEventListener("scroll", () => requestAnimationFrame(appliquer), { passive: true });
}

// --- 4D : poussière d'or en perspective (canvas 2D, projection 3D maison) ---------------------
export function poussiereOr(hote, nombre = window.innerWidth < 720 ? 70 : 160) {
  const canvas = document.createElement("canvas");
  canvas.className = "poussiere-or";
  canvas.setAttribute("aria-hidden", "true");
  hote.prepend(canvas);
  if (reduit) return canvas;

  const ctx = canvas.getContext("2d");
  const particules = Array.from({ length: nombre }, () => ({
    x: (Math.random() - 0.5) * 2, y: (Math.random() - 0.5) * 2, z: Math.random(),
    v: 0.0008 + Math.random() * 0.0018, t: Math.random() * Math.PI * 2,
  }));
  let largeur = 0, hauteur = 0, rotation = 0, cible = 0;
  const redimensionner = () => {
    const r = hote.getBoundingClientRect();
    largeur = canvas.width = Math.round(r.width * devicePixelRatio);
    hauteur = canvas.height = Math.round(r.height * devicePixelRatio);
  };
  redimensionner();
  new ResizeObserver(redimensionner).observe(hote);
  hote.addEventListener("pointermove", (e) => {
    const r = hote.getBoundingClientRect();
    cible = ((e.clientX - r.left) / r.width - 0.5) * 0.6;
  });

  function image() {
    if (!canvas.isConnected) return;
    rotation += (cible - rotation) * 0.03;
    ctx.clearRect(0, 0, largeur, hauteur);
    const cos = Math.cos(rotation), sin = Math.sin(rotation);
    for (const p of particules) {
      p.z -= p.v;                       // les particules avancent vers nous
      p.t += 0.01;
      if (p.z <= 0.02) { p.z = 1; p.x = (Math.random() - 0.5) * 2; p.y = (Math.random() - 0.5) * 2; }
      const x = p.x * cos - p.z * sin * 0.4;
      const echelle = 1 / (p.z * 1.6 + 0.25);          // projection en perspective
      const sx = largeur / 2 + x * largeur * 0.42 * echelle;
      const sy = hauteur / 2 + (p.y + Math.sin(p.t) * 0.02) * hauteur * 0.42 * echelle;
      const taille = Math.max(0.4, (1 - p.z) * 2.6 * devicePixelRatio);
      const alpha = Math.min(1, (1 - p.z) * 1.4) * 0.75;
      ctx.beginPath();
      ctx.fillStyle = `rgba(244, 214, 140, ${alpha.toFixed(3)})`;
      ctx.shadowColor = "rgba(244, 214, 140, .8)";
      ctx.shadowBlur = taille * 4;
      ctx.arc(sx, sy, taille, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(image);
  }
  requestAnimationFrame(image);
  return canvas;
}

// --- 4D : barre de progression du défilement ----------------------------------------------------
let barre = null;
function progression() {
  if (barre) return;
  barre = document.createElement("div");
  barre.className = "progression-page";
  barre.setAttribute("aria-hidden", "true");
  document.body.append(barre);
  const maj = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    barre.style.transform = `scaleX(${max > 0 ? Math.min(1, window.scrollY / max) : 0})`;
  };
  window.addEventListener("scroll", () => requestAnimationFrame(maj), { passive: true });
  window.addEventListener("hashchange", () => setTimeout(maj, 50));
}

// Appelée après chaque rendu de page : branche les effets sur les nouveaux éléments.
export function activerEffets(racine) {
  progression();
  if (reduit) return;
  racine.querySelectorAll(LUMINEUX).forEach(lumineux);
  racine.querySelectorAll(PARALLAXES).forEach(parallaxe);
  if (!pointeurFin) return;
  racine.querySelectorAll(INCLINABLES).forEach(inclinable);
  racine.querySelectorAll(AIMANTES).forEach(aimante);
}

// Les pages construisent parfois leur contenu après un appel réseau : on observe le DOM.
export function observerEffets(racine) {
  let attente = null;
  new MutationObserver(() => {
    clearTimeout(attente);
    attente = setTimeout(() => activerEffets(racine), 60);
  }).observe(racine, { childList: true, subtree: true });
}
