// Animations liées au défilement, à la manière de GSAP ScrollTrigger, mais sans bibliothèque :
// le site ne charge aucun script externe. Chaque élément déclare son effet par un attribut :
//   data-ecarter         les deux moitiés du grand titre s'écartent quand on descend ;
//   data-balayer         le texte se remplit de blanc, de gauche à droite, en entrant à l'écran ;
//   data-glisser="-20"   l'élément glisse horizontalement (en % de sa largeur) pendant sa traversée ;
//   data-diapo         la diapositive grandit légèrement et arrondit ses angles en arrivant.
// Une seule boucle requestAnimationFrame, déclenchée par le défilement ; rien ne bouge si le
// système demande moins d'animations.

const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let suivis = [];
let prevu = false;

const borne = (x) => Math.min(1, Math.max(0, x));

function appliquer() {
  prevu = false;
  const vh = window.innerHeight;
  suivis = suivis.filter((el) => el.isConnected);
  for (const el of suivis) {
    const r = el.getBoundingClientRect();
    if (r.bottom < -vh || r.top > vh * 2) continue;
    // 0 quand le haut de l'élément touche le bas de l'écran, 1 quand son bas touche le haut.
    const traversee = borne((vh - r.top) / (vh + r.height));
    // 0 → 1 pendant l'entrée (du bas de l'écran jusqu'aux deux tiers).
    const entree = borne((vh - r.top) / (vh * 0.65));
    if (el.hasAttribute("data-ecarter")) {
      const p = borne(-r.top / Math.max(1, r.height * 0.9));
      el.style.setProperty("--ecart", (p * 28).toFixed(2));
    }
    if (el.hasAttribute("data-balayer")) el.style.setProperty("--p", `${(entree * 100).toFixed(1)}%`);
    if (el.hasAttribute("data-glisser")) {
      const amplitude = Number(el.dataset.glisser) || -20;
      el.style.transform = `translate3d(${((traversee - 0.5) * amplitude).toFixed(2)}%, 0, 0)`;
    }
    if (el.hasAttribute("data-diapo")) el.style.setProperty("--arrivee", entree.toFixed(3));
  }
}

function demander() {
  if (!prevu) { prevu = true; requestAnimationFrame(appliquer); }
}

window.addEventListener("scroll", demander, { passive: true });
window.addEventListener("resize", demander);

export function animerDefilement(racine) {
  const elements = racine.querySelectorAll("[data-ecarter], [data-balayer], [data-glisser], [data-diapo]");
  if (reduit) {
    elements.forEach((el) => { el.style.setProperty("--p", "100%"); el.style.setProperty("--arrivee", "1"); });
    return;
  }
  suivis = [...suivis.filter((el) => el.isConnected), ...elements];
  demander();
}
