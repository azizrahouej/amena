// Balance de la justice en 3D, construite uniquement avec des transformations CSS 3D :
// aucune bibliothèque externe (WebGL, three.js) n'est chargée, rien ne quitte le site.
// Elle tourne lentement sur elle-même et suit le pointeur ; le fléau oscille.

import { h } from "./ui.js";

const RAD = Math.PI / 180;

function disque(rayon, y, classe = "disque") {
  return h("div", { class: classe, style: `width:${rayon * 2}px;height:${rayon * 2}px;margin:${-rayon}px 0 0 ${-rayon}px;transform:translateY(${y}px) rotateX(90deg)` });
}

// Un cylindre plein = une pile de disques très proches (illusion d'épaisseur).
function pile(rayon, yHaut, epaisseur, classe) {
  return Array.from({ length: Math.ceil(epaisseur / 1.5) }, (_, i) => disque(rayon, yHaut + i * 1.5, classe));
}

function colonne(rayon, yHaut, hauteur, faces = 14) {
  const largeur = 2 * rayon * Math.tan(Math.PI / faces) + 0.6;
  return Array.from({ length: faces }, (_, i) => {
    const angle = (360 / faces) * i;
    const lumiere = 0.55 + 0.45 * Math.cos(angle * RAD);
    return h("div", { class: "face-colonne", style: `width:${largeur}px;height:${hauteur}px;margin-left:${-largeur / 2}px;top:${yHaut}px;transform:rotateY(${angle}deg) translateZ(${rayon}px);filter:brightness(${lumiere.toFixed(2)})` });
  });
}

function plateau() {
  const rayon = 46;
  const longueur = 110;
  const chaines = [0, 120, 240].map((angle) => {
    const inclinaison = Math.atan(rayon / longueur) / RAD;
    const l = Math.hypot(rayon, longueur);
    return h("div", { class: "chaine", style: `height:${l}px;transform:rotateY(${angle}deg) rotateX(${inclinaison}deg)` });
  });
  return h("div", { class: "suspension" },
    ...chaines,
    ...pile(rayon, longueur, 4, "disque bord"),
    disque(rayon - 8, longueur + 5, "disque creux"),
    disque(rayon - 18, longueur + 10, "disque creux"),
    disque(rayon - 30, longueur + 14, "disque creux"));
}

function fleau() {
  const faces = [
    "translateZ(6px)", "rotateY(180deg) translateZ(6px)",
    "rotateX(90deg) translateZ(6px)", "rotateX(-90deg) translateZ(6px)",
  ];
  return h("div", { class: "fleau" },
    ...faces.map((t) => h("div", { class: "face-fleau", style: `transform:${t}` })),
    h("div", { class: "bras gauche" }, plateau()),
    h("div", { class: "bras droit" }, plateau()),
    h("div", { class: "pivot-fleau" }));
}

export function balance3d() {
  const objet = h("div", { class: "balance" },
    ...pile(84, 150, 8, "disque socle"),
    ...pile(66, 141, 8, "disque socle"),
    ...pile(48, 132, 6, "disque socle"),
    ...colonne(9, -96, 230),
    h("div", { class: "orbe" }),
    fleau());

  const scene = h("div", { class: "scene3d", "aria-hidden": "true" },
    h("div", { class: "halo" }),
    h("div", { class: "anneau a1" }), h("div", { class: "anneau a2" }),
    h("div", { class: "pivot" }, objet),
    h("div", { class: "ombre-sol" }),
    ...Array.from({ length: 14 }, (_, i) => h("span", { class: "particule",
      style: `--x:${(i * 37) % 100}%;--d:${6 + (i % 5) * 1.7}s;--delai:${-(i * 0.9)}s;--t:${2 + (i % 3)}px` })));

  // Rotation : lente et automatique, ou guidée par le pointeur quand il survole la scène.
  let angle = -25, cibleX = -8, inclinaison = -8, pointeur = null;
  scene.addEventListener("pointermove", (e) => {
    const r = scene.getBoundingClientRect();
    pointeur = { x: (e.clientX - r.left) / r.width - 0.5, y: (e.clientY - r.top) / r.height - 0.5 };
  });
  scene.addEventListener("pointerleave", () => { pointeur = null; });

  const reduit = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  function image() {
    if (!scene.isConnected) return; // la page a changé : on arrête la boucle
    if (pointeur) {
      angle += (pointeur.x * 70 - angle) * 0.06;
      cibleX = pointeur.y * -25;
    } else if (!reduit) {
      angle += 0.18;
      cibleX = -8;
    }
    inclinaison += (cibleX - inclinaison) * 0.06;
    objet.style.transform = `rotateX(${inclinaison.toFixed(2)}deg) rotateY(${angle.toFixed(2)}deg)`;
    requestAnimationFrame(image);
  }
  requestAnimationFrame(image);
  return scene;
}
