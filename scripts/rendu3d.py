"""Moteur de rendu 3D d'AMENA : lancer de rayons sur champs de distance signée (SDF raymarching).

Toutes les images 3D du site sont calculées ici, en local, avec numpy et Pillow : aucune image
n'est téléchargée, aucun service tiers n'est appelé, et le site reste sans ressource externe.

Scènes :
  - palais  : palais de justice en vue isométrique, posé sur un socle (fond transparent) ;
  - cabinet : nature morte « cabinet d'avocat » : marteau sur son socle, balance dorée, livres.

Techniques : marche de sphère (sphere tracing), normales par différences tétraédriques, ombres
douces, occlusion ambiante, lumières ponctuelles, réflexions (or, bois verni), textures
procédurales (bois, dallage, cuir), flou de profondeur, halo lumineux (bloom), tonemapping ACES.

Usage :
  python scripts/rendu3d.py palais  [--largeur 1500] [--ss 2]
  python scripts/rendu3d.py cabinet [--largeur 1600] [--ss 2]
  python scripts/rendu3d.py tout --apercu        # rendu rapide basse définition
"""
from __future__ import annotations

import argparse
import math
import time
from pathlib import Path

import numpy as np
from PIL import Image

F = np.float32
RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "web" / "img" / "3d"


# ================================================================================================
# Outils
# ================================================================================================
def vec(x, y, z):
    return np.array([x, y, z], dtype=F)


def unitaire(v):
    return (v / np.linalg.norm(v)).astype(F)


def lisse(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def smin(a, b, k):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def fract(x):
    return x - np.floor(x)


def hachage(a, b, c=0.0):
    v = np.sin(np.asarray(a, np.float64) * 127.1 + np.asarray(b, np.float64) * 311.7
               + np.asarray(c, np.float64) * 74.7) * 43758.5453
    return (v - np.floor(v)).astype(F)


def bruit(x, y, z=None):
    """Bruit de valeur 3D lissé, dans [0, 1]."""
    if z is None:
        z = np.zeros_like(x)
    ix, iy, iz = np.floor(x), np.floor(y), np.floor(z)
    fx, fy, fz = x - ix, y - iy, z - iz
    ux, uy, uz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def h(a, b, c):
        return hachage(ix + a, iy + b, iz + c)

    x00 = h(0, 0, 0) + (h(1, 0, 0) - h(0, 0, 0)) * ux
    x10 = h(0, 1, 0) + (h(1, 1, 0) - h(0, 1, 0)) * ux
    x01 = h(0, 0, 1) + (h(1, 0, 1) - h(0, 0, 1)) * ux
    x11 = h(0, 1, 1) + (h(1, 1, 1) - h(0, 1, 1)) * ux
    y0 = x00 + (x10 - x00) * uy
    y1 = x01 + (x11 - x01) * uy
    return y0 + (y1 - y0) * uz


def fbm(x, y, z=None, octaves=4):
    total, amp, norme = 0.0, 0.5, 0.0
    for _ in range(octaves):
        total = total + amp * bruit(x, y, z)
        norme += amp
        x, y = x * 2.03 + 1.7, y * 2.01 + 3.1
        z = None if z is None else z * 2.02 + 5.3
        amp *= 0.5
    return total / norme


# ================================================================================================
# Primitives (coordonnées séparées x, y, z : tableaux 1D)
# ================================================================================================
def boite(x, y, z, cx, cy, cz, bx, by, bz, r=0.0):
    qx = np.abs(x - cx) - (bx - r)
    qy = np.abs(y - cy) - (by - r)
    qz = np.abs(z - cz) - (bz - r)
    ext = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return ext + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r


def cyl_y(x, y, z, cx, cy, cz, r, h, arrondi=0.0):
    dr = np.sqrt((x - cx) ** 2 + (z - cz) ** 2) - (r - arrondi)
    dy = np.abs(y - cy) - (h - arrondi)
    return np.minimum(np.maximum(dr, dy), 0) + np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dy, 0) ** 2) - arrondi


def sphere(x, y, z, cx, cy, cz, r):
    return np.sqrt((x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2) - r


def capsule(x, y, z, a, b, r):
    ba = b - a
    inv = 1.0 / float(ba @ ba)
    pax, pay, paz = x - a[0], y - a[1], z - a[2]
    h = np.clip((pax * ba[0] + pay * ba[1] + paz * ba[2]) * inv, 0.0, 1.0)
    return np.sqrt((pax - h * ba[0]) ** 2 + (pay - h * ba[1]) ** 2 + (paz - h * ba[2]) ** 2) - r


def cylindre(x, y, z, a, b, r, arrondi=0.0):
    """Cylindre fermé d'axe [a, b] et de rayon r, aux bords arrondis."""
    axe = b - a
    longueur = float(np.linalg.norm(axe))
    u = axe / longueur
    c = (a + b) * 0.5
    px, py, pz = x - c[0], y - c[1], z - c[2]
    t = px * u[0] + py * u[1] + pz * u[2]
    rx, ry, rz = px - t * u[0], py - t * u[1], pz - t * u[2]
    dr = np.sqrt(rx * rx + ry * ry + rz * rz) - (r - arrondi)
    dl = np.abs(t) - (longueur * 0.5 - arrondi)
    return np.minimum(np.maximum(dr, dl), 0) + np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dl, 0) ** 2) - arrondi


def union(*ds):
    d = ds[0]
    for e in ds[1:]:
        d = np.minimum(d, e)
    return d


# ================================================================================================
# Moteur
# ================================================================================================
def marcher(ox, oy, oz, dx, dy, dz, sdf, tmax, iters=220, eps=2e-3, rel=0.0, facteur=0.9):
    n = ox.size
    t = np.zeros(n, F)
    touche = np.zeros(n, bool)
    act = np.arange(n)
    for _ in range(iters):
        if act.size == 0:
            break
        ta = t[act]
        d = sdf(ox[act] + dx[act] * ta, oy[act] + dy[act] * ta, oz[act] + dz[act] * ta)
        hit = d < eps + rel * ta
        touche[act[hit]] = True
        nt = ta + d * facteur
        t[act] = np.where(hit, ta, nt)
        act = act[~hit & (nt < tmax)]
    if act.size:  # rayons rasants non convergés : on garde ceux qui frôlent une surface
        ta = t[act]
        d = sdf(ox[act] + dx[act] * ta, oy[act] + dy[act] * ta, oz[act] + dz[act] * ta)
        touche[act[d < 10 * (eps + rel * ta)]] = True
    return t, touche


def normales(x, y, z, sdf, e):
    nx = ny = nz = 0.0
    for a, b, c in ((1, -1, -1), (-1, -1, 1), (-1, 1, -1), (1, 1, 1)):
        d = sdf(x + a * e, y + b * e, z + c * e)
        nx, ny, nz = nx + a * d, ny + b * d, nz + c * d
    lg = np.maximum(np.sqrt(nx * nx + ny * ny + nz * nz), 1e-9)
    return nx / lg, ny / lg, nz / lg


def ombre(x, y, z, L, sdf, tmin, tmax, k, pas_min, pas_max, iters=56):
    n = x.size
    res = np.ones(n, F)
    t = np.full(n, tmin, F)
    act = np.arange(n)
    for _ in range(iters):
        if act.size == 0:
            break
        ta = t[act]
        h = sdf(x[act] + L[0] * ta, y[act] + L[1] * ta, z[act] + L[2] * ta)
        res[act] = np.minimum(res[act], k * h / ta)
        nt = ta + np.clip(h, pas_min, pas_max)
        t[act] = nt
        act = act[(res[act] > 0.004) & (nt < tmax)]
    res = np.clip(res, 0.0, 1.0)
    return res * res * (3 - 2 * res)


def occlusion(x, y, z, nx, ny, nz, sdf, rayon, n=5):
    occ = 0.0
    total = 0.0
    poids = 1.0
    for i in range(1, n + 1):
        h = rayon * i / n
        d = sdf(x + nx * h, y + ny * h, z + nz * h)
        occ = occ + np.clip(h - d, 0, None) * poids
        total += h * poids
        poids *= 0.72
    return np.clip(1.0 - 1.25 * occ / total, 0.0, 1.0)


def _boite_1d(a, r, ax):
    if r < 1:
        return a
    a = np.moveaxis(a, ax, 0)
    p = np.concatenate([np.repeat(a[:1], r + 1, 0), a, np.repeat(a[-1:], r, 0)], 0)
    c = np.cumsum(p, 0, dtype=np.float32)
    out = (c[2 * r + 1:] - c[: -2 * r - 1]) / (2 * r + 1)
    return np.moveaxis(out, 0, ax)


def flou(img, r):
    """Flou quasi gaussien (trois passes de flou boîte séparable)."""
    r = int(round(r))
    for _ in range(3):
        img = _boite_1d(_boite_1d(img, r, 0), r, 1)
    return img


def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0)


def rendre(scene, W, H, morceau=180_000):
    ox, oy, oz, dx, dy, dz = scene.rayons(W, H)
    n = W * H
    rgb = np.zeros((n, 3), F)
    touche = np.zeros(n, bool)
    prof = np.full(n, np.inf, F)
    debut = time.time()
    for s in range(0, n, morceau):
        sl = slice(s, min(n, s + morceau))
        t, hit = marcher(ox[sl], oy[sl], oz[sl], dx[sl], dy[sl], dz[sl], scene.sdf, scene.tmax,
                         eps=scene.eps, rel=scene.rel)
        idx = np.nonzero(hit)[0]
        if idx.size:
            g = s + idx
            tt = t[idx]
            x, y, z = ox[g] + dx[g] * tt, oy[g] + dy[g] * tt, oz[g] + dz[g] * tt
            rgb[g] = scene.ombrer(x, y, z, dx[g], dy[g], dz[g])
            prof[g] = tt
        touche[sl] = hit
        print(f"  {min(n, s + morceau) * 100 // n:3d} %  ({time.time() - debut:5.1f} s)", flush=True)
    return rgb.reshape(H, W, 3), touche.reshape(H, W), prof.reshape(H, W)


def enregistrer(rgb, alpha, taille, chemin):
    img = (np.clip(rgb, 0, 1) ** (1 / 2.2) * 255 + 0.5).astype(np.uint8)
    if alpha is not None:
        a = (np.clip(alpha, 0, 1) * 255 + 0.5).astype(np.uint8)
        im = Image.fromarray(np.dstack([img, a]), "RGBA").convert("RGBa").resize(taille, Image.LANCZOS).convert("RGBA")
    else:
        im = Image.fromarray(img, "RGB").resize(taille, Image.LANCZOS)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    im.save(chemin, "WEBP", quality=90, method=6)
    return chemin


# ================================================================================================
# Scène 1 : palais de justice isométrique
# ================================================================================================
(SOCLE, PIERRE, MUR, MARBRE, VITRE, BRONZE, GAZON, FEUILLAGE, TRONC, LAMPE, METAL,
 DRAPEAU, TOIT, SPOT) = range(14)

BASE_PALAIS = np.array([
    [0.050, 0.045, 0.040],  # socle
    [0.50, 0.47, 0.42],     # pierre claire
    [0.085, 0.080, 0.075],  # murs sombres
    [0.70, 0.68, 0.63],     # marbre
    [0.02, 0.02, 0.02],     # vitres
    [0.22, 0.15, 0.08],     # bronze
    [0.035, 0.050, 0.025],  # gazon
    [0.10, 0.13, 0.07],     # olivier
    [0.07, 0.05, 0.035],    # tronc
    [0.05, 0.05, 0.05],     # lampe
    [0.03, 0.03, 0.03],     # métal
    [0.55, 0.02, 0.03],     # drapeau
    [0.075, 0.07, 0.065],   # toit
    [0.05, 0.05, 0.05],     # spots
], F)
BRILLANCE_PALAIS = np.array([0.15, 0.2, 0.25, 0.35, 0.8, 0.9, 0.02, 0.05, 0.02, 0.5, 0.6, 0.1, 0.15, 0.4], F)

ARBRES = [(-6.7, 5.9), (6.7, -5.9), (-6.5, -6.5)]


class Palais:
    nom = "palais-3d"
    transparent = True
    tmax = 75.0
    eps = 1.5e-3
    rel = 0.0

    def __init__(self):
        self.fwd = unitaire(vec(-0.80, -0.74, -1.0))
        self.cible = vec(0.0, 1.25, 0.4)
        self.demi_l = 12.2
        self.ratio = 0.84
        self.L = unitaire(vec(-0.45, 0.85, 0.55))
        self.C_CLE = vec(1.0, 0.86, 0.70) * 1.3
        self.Lf = unitaire(vec(0.9, 0.3, -0.2))
        self.C_FILL = vec(0.35, 0.45, 0.65) * 0.28
        self.points = [(vec(0.0, 2.1, 2.5), vec(1.0, 0.62, 0.30), 5.0)]
        for sx in (-2.35, 2.35):
            for sz in (5.1, 6.3, 7.5):
                self.points.append((vec(sx, 1.27, sz), vec(1.0, 0.80, 0.55), 1.1))

    # --- caméra orthographique (isométrique) ---
    def axes(self):
        right = unitaire(np.cross(self.fwd, vec(0, 1, 0)))
        up = np.cross(right, self.fwd).astype(F)
        return right, up

    def rayons(self, W, H):
        right, up = self.axes()
        u = ((np.arange(W, dtype=F) + 0.5) / W * 2 - 1) * self.demi_l
        v = (1 - (np.arange(H, dtype=F) + 0.5) / H * 2) * self.demi_l * H / W
        U, V = np.meshgrid(u, v)
        U, V = U.ravel(), V.ravel()
        o = self.cible - self.fwd * 30
        n = U.size
        return (o[0] + U * right[0] + V * up[0], o[1] + U * right[1] + V * up[1], o[2] + U * right[2] + V * up[2],
                np.full(n, self.fwd[0], F), np.full(n, self.fwd[1], F), np.full(n, self.fwd[2], F))

    def projeter(self, p, W, H):
        right, up = self.axes()
        d = p - self.cible
        u = float(d @ right) / self.demi_l
        v = float(d @ up) / (self.demi_l * H / W)
        return (u + 1) / 2, (1 - v) / 2

    # --- géométrie ---
    def morceaux(self, x, y, z):
        m = []
        m.append((boite(x, y, z, 0, -0.45, 0, 8, 0.45, 8, 0.12), SOCLE))

        podium = boite(x, y, z, 0, 0.45, -1.2, 5.2, 0.45, 4.4, 0.02)
        marches = union(*[boite(x, y, z, 0, (0.9 - 0.225 * k) / 2, (6.2 + 0.4 * k) / 2,
                                3.2, (0.9 - 0.225 * k) / 2, (0.2 + 0.4 * k) / 2) for k in (1, 2, 3)])
        m.append((np.minimum(podium, marches), PIERRE))

        # Bloc principal percé de fenêtres (côté +x et façade +z) et d'une grande porte
        bloc = boite(x, y, z, 0, 2.95, -1.75, 4.5, 2.05, 3.25)
        qy = np.abs(y - 2.85) - 0.85
        iz = np.clip(np.round((z + 1.75) / 1.3), -2, 2)
        qz = z + 1.75 - iz * 1.3
        ix = np.clip(np.round(x / 1.5), -2, 2)
        qx = x - ix * 1.5
        trous = union(boite(x, qy, qz, 4.5, 0, 0, 0.18, 0.55, 0.32),
                      boite(qx, qy, z, 0, 0, 1.5, 0.3, 0.55, 0.18),
                      boite(x, y, z, 0, 2.0, 1.5, 0.6, 1.1, 0.2))
        m.append((np.maximum(bloc, -trous), MUR))
        vitres = union(boite(x, qy, qz, 4.38, 0, 0, 0.02, 0.55, 0.32),
                       boite(qx, qy, z, 0, 0, 1.38, 0.3, 0.55, 0.02),
                       boite(x, y, z, 0, 2.0, 1.38, 0.6, 1.1, 0.02))
        m.append((vitres, VITRE))

        # Portique : six colonnes cannelées, entablement, fronton à tympan creusé
        ic = np.clip(np.round((x + 3.75) / 1.5), 0, 5)
        cx = x + 3.75 - ic * 1.5
        cz = z - 2.6
        rr = np.sqrt(cx * cx + cz * cz)
        r_eff = 0.26 + 0.012 * np.cos(20 * np.arctan2(cz, cx))
        dr, dyc = rr - r_eff, np.abs(y - 2.5) - 1.6
        fut = np.minimum(np.maximum(dr, dyc), 0) + np.sqrt(np.maximum(dr, 0) ** 2 + np.maximum(dyc, 0) ** 2)
        colonnes = union(fut, boite(cx, y, cz, 0, 1.0, 0, 0.36, 0.1, 0.36, 0.02),
                         boite(cx, y, cz, 0, 4.0, 0, 0.38, 0.1, 0.38, 0.02))
        entablement = boite(x, y, z, 0, 4.38, 2.3, 4.4, 0.28, 0.88, 0.02)
        y0, Hf, Wf = 4.66, 1.1, 4.4
        fronton = np.maximum(np.maximum((np.abs(x) * Hf + (y - y0 - Hf) * Wf) / math.hypot(Hf, Wf), y0 - y),
                             np.abs(z - 2.3) - 0.88)
        yb, Hi, Wi = 4.8, 0.72, 3.6
        tympan = np.maximum(np.maximum((np.abs(x) * Hi + (y - yb - Hi) * Wi) / math.hypot(Hi, Wi), yb - y),
                            np.abs(z - 3.18) - 0.07)
        fronton = np.maximum(fronton, -tympan)
        tambour = cyl_y(x, y, z, 0, 5.55, -1.8, 1.5, 0.35)
        lanterne = cyl_y(x, y, z, 0, 7.55, -1.8, 0.2, 0.18)
        m.append((union(colonnes, entablement, fronton, tambour, lanterne), MARBRE))

        m.append((boite(x, y, z, 0, 5.1, -1.75, 4.7, 0.1, 3.45, 0.03), TOIT))
        dome = np.maximum(sphere(x, y, z, 0, 5.9, -1.8, 1.5), 5.9 - y)
        m.append((np.minimum(dome, sphere(x, y, z, 0, 7.83, -1.8, 0.11)), BRONZE))

        # Drapeau tunisien sur le toit
        m.append((capsule(x, y, z, vec(4.1, 5.2, 1.2), vec(4.1, 7.1, 1.2), 0.035), METAL))
        m.append((boite(x, y, z, 4.73, 6.68, 1.2, 0.6, 0.38, 0.015, 0.005), DRAPEAU))

        # Jardins : pelouses, haies, oliviers
        gazon = union(boite(x, y, z, -6.7, 0.04, 0, 0.9, 0.08, 7.0, 0.03),
                      boite(x, y, z, 6.7, 0.04, 0, 0.9, 0.08, 7.0, 0.03),
                      boite(x, y, z, -4.1, 0.04, 6.35, 1.9, 0.08, 1.25, 0.03),
                      boite(x, y, z, 4.1, 0.04, 6.35, 1.9, 0.08, 1.25, 0.03),
                      boite(x, y, z, 0, 0.04, -6.85, 5.0, 0.08, 0.75, 0.03))
        m.append((gazon, GAZON))

        bx = np.abs(x) - 6.1
        izb = np.clip(np.round(z / 1.3), -4, 4)
        bz = z - izb * 1.3
        haie_cote = np.sqrt(bx * bx + (y - 0.36) ** 2 * 1.4 + bz * bz) - 0.42
        fx = np.abs(x) - 4.1
        fx = fx - np.clip(np.round(fx / 1.05), -1, 1) * 1.05
        haie_face = sphere(fx, y, z, 0, 0.34, 5.75, 0.38)
        hx = x - np.clip(np.round(x / 1.25), -3, 3) * 1.25
        haie_fond = sphere(hx, y, z, 0, 0.36, -6.85, 0.4)
        feuillage = union(haie_cote, haie_face, haie_fond)
        troncs = []
        for tx, tz in ARBRES:
            troncs.append(capsule(x, y, z, vec(tx, 0, tz), vec(tx, 1.7, tz), 0.13))
            f = sphere(x, y, z, tx, 2.5, tz, 1.1)
            f = smin(f, sphere(x, y, z, tx + 0.55, 2.05, tz + 0.35, 0.78), 0.35)
            f = smin(f, sphere(x, y, z, tx - 0.5, 2.2, tz - 0.4, 0.8), 0.35)
            f = smin(f, sphere(x, y, z, tx + 0.1, 3.15, tz - 0.1, 0.75), 0.35)
            feuillage = np.minimum(feuillage, f)
        feuillage = feuillage + 0.11 * np.sin(4.5 * x) * np.sin(4.5 * y) * np.sin(4.5 * z) \
            + 0.045 * np.sin(13 * x + 2) * np.sin(11 * y) * np.sin(12 * z + 1)
        m.append((feuillage, FEUILLAGE))
        m.append((union(*troncs), TRONC))

        # Lampadaires le long de l'allée, spots au sol sur le pourtour
        lx = np.abs(x) - 2.35
        lz = z - 6.3 - np.clip(np.round((z - 6.3) / 1.2), -1, 1) * 1.2
        m.append((cyl_y(lx, y, lz, 0, 0.6, 0, 0.04, 0.6), METAL))
        m.append((sphere(lx, y, lz, 0, 1.27, 0, 0.13), LAMPE))
        a = np.abs(x) - 7.72
        sz = z - np.clip(np.round(z / 1.9), -4, 4) * 1.9
        b = np.abs(z) - 7.72
        sx = x - np.clip(np.round(x / 1.9), -4, 4) * 1.9
        spots = np.minimum(np.sqrt(a * a + y * y + sz * sz), np.sqrt(sx * sx + y * y + b * b)) - 0.07
        m.append((spots, SPOT))
        return m

    def sdf(self, x, y, z):
        return union(*[d for d, _ in self.morceaux(x, y, z)])

    def sdf_mat(self, x, y, z):
        m = self.morceaux(x, y, z)
        D = np.stack([d for d, _ in m])
        i = np.argmin(D, 0)
        return np.array([k for _, k in m])[i]

    # --- matériaux et lumière ---
    def ombrer(self, x, y, z, dx, dy, dz):
        mat = self.sdf_mat(x, y, z)
        nx, ny, nz = normales(x, y, z, self.sdf, 0.003)
        n = x.size
        alb = BASE_PALAIS[mat].copy()
        emis = np.zeros((n, 3), F)
        brill = BRILLANCE_PALAIS[mat].copy()

        def regler(masque, couleur):
            alb[masque] = couleur[masque] if couleur.ndim == 2 else couleur

        # Dallage du socle et de l'allée
        haut = ny > 0.6
        for k_mat, taille, teinte in ((SOCLE, 0.75, vec(0.30, 0.28, 0.25)), (PIERRE, 0.9, vec(0.52, 0.49, 0.44))):
            mk = (mat == k_mat) & haut
            if mk.any():
                u, v = x[mk] / taille, z[mk] / taille
                fu, fv = fract(u), fract(v)
                joint = np.minimum(np.minimum(fu, 1 - fu), np.minimum(fv, 1 - fv)) < 0.035
                var = 0.85 + 0.25 * hachage(np.floor(u), np.floor(v))
                c = teinte[None, :] * var[:, None]
                c[joint] *= 0.55
                alb[mk] = c
        mk = (mat == PIERRE) & ~haut
        if mk.any():
            lignes = fract(y[mk] / 0.225) < 0.06
            alb[mk] = BASE_PALAIS[PIERRE] * np.where(lignes, 0.75, 1.0)[:, None]
        mk = mat == MUR
        if mk.any():
            lignes = fract(y[mk] / 0.5) < 0.045
            var = 0.85 + 0.3 * bruit(x[mk] * 2, y[mk] * 2, z[mk] * 2)
            alb[mk] = BASE_PALAIS[MUR] * (var * np.where(lignes, 0.6, 1.0))[:, None]
        mk = mat == MARBRE
        if mk.any():
            veine = fbm(x[mk] * 1.5, y[mk] * 1.5, z[mk] * 1.5, 3)
            alb[mk] = BASE_PALAIS[MARBRE] * (0.88 + 0.2 * veine)[:, None]
            # Fentes lumineuses du tambour de la coupole
            r_t = np.sqrt(x[mk] ** 2 + (z[mk] + 1.8) ** 2)
            ang = np.arctan2(z[mk] + 1.8, x[mk])
            fente = (np.abs(r_t - 1.5) < 0.05) & (y[mk] > 5.32) & (y[mk] < 5.78) & \
                (np.abs(fract(ang * 16 / (2 * np.pi)) - 0.5) < 0.16)
            e = np.zeros((mk.sum(), 3), F)
            e[fente] = vec(1.0, 0.66, 0.32) * 1.8
            emis[mk] = e
        mk = mat == VITRE
        if mk.any():
            xv, yv, zv = x[mk], y[mk], z[mk]
            cote = xv > 4.3
            porte = (np.abs(xv) < 0.62) & (yv < 3.15) & (zv > 1.3) & ~cote
            qy = np.abs(yv - 2.85) - 0.85
            izv = np.round((zv + 1.75) / 1.3)
            qz = zv + 1.75 - izv * 1.3
            ixv = np.round(xv / 1.5)
            qx = xv - ixv * 1.5
            ident = np.where(cote, izv * 3 + 1, ixv * 5 + 2) + np.sign(yv - 2.85) * 17
            allume = hachage(ident, 3.7) > 0.22
            inten = np.where(allume, 2.4, 0.18)
            mont = np.where(cote, np.abs(qz) < 0.022, np.abs(qx) < 0.022) | (np.abs(qy - 0.18) < 0.022)
            mont_p = (np.abs(xv) < 0.025) | (np.abs(yv - 2.45) < 0.025)
            mont = np.where(porte, mont_p, mont)
            inten = np.where(porte, 3.2, inten) * np.where(mont, 0.05, 1.0)
            degrade = 0.8 + 0.35 * np.clip((0.55 - qy) / 1.1, 0, 1)
            emis[mk] = vec(1.0, 0.64, 0.30)[None, :] * (inten * degrade)[:, None]
        mk = mat == BRONZE
        if mk.any():
            ang = np.arctan2(z[mk] + 1.8, x[mk])
            cote = np.abs(fract(ang * 12 / (2 * np.pi)) - 0.5) > 0.46
            alb[mk] = BASE_PALAIS[BRONZE] * np.where(cote, 1.8, 1.0)[:, None]
            emis[mk] = vec(0.05, 0.035, 0.02) * (0.5 + 0.5 * ny[mk])[:, None]
        mk = mat == GAZON
        if mk.any():
            alb[mk] = BASE_PALAIS[GAZON] * (0.6 + 0.8 * bruit(x[mk] * 3, z[mk] * 3))[:, None]
        mk = mat == FEUILLAGE
        if mk.any():
            b = fbm(x[mk] * 3, y[mk] * 3, z[mk] * 3, 3)
            c = BASE_PALAIS[FEUILLAGE] * (0.55 + 0.9 * b)[:, None]
            c += vec(0.05, 0.055, 0.04) * lisse(0.6, 0.85, b)[:, None]  # reflets argentés de l'olivier
            alb[mk] = c
        mk = mat == LAMPE
        emis[mk] = vec(1.0, 0.82, 0.55) * 5.0
        mk = mat == SPOT
        emis[mk] = vec(1.0, 0.95, 0.85) * 4.0
        mk = (mat == DRAPEAU) & (np.abs(nz) > 0.5)
        if mk.any():
            fx, fy = x[mk] - 4.73, y[mk] - 6.68
            disque = fx * fx + fy * fy < 0.21 ** 2
            croissant = ((fx + 0.02) ** 2 + fy ** 2 < 0.155 ** 2) & ((fx - 0.03) ** 2 + fy ** 2 > 0.125 ** 2)
            etoile = (fx - 0.045) ** 2 + fy ** 2 < 0.05 ** 2
            blanc = disque & ~croissant & ~etoile
            c = np.tile(BASE_PALAIS[DRAPEAU], (mk.sum(), 1))
            c[blanc] = vec(0.80, 0.80, 0.78)
            alb[mk] = c

        # Éclairage : lumière clé avec ombres douces, remplissage, ciel, lumières ponctuelles
        ex, ey, ez = x + nx * 0.01, y + ny * 0.01, z + nz * 0.01
        sh = ombre(ex, ey, ez, self.L, self.sdf, 0.03, 30.0, 10.0, 0.02, 0.6)
        ao = occlusion(x, y, z, nx, ny, nz, self.sdf, 0.9)
        dif = np.maximum(nx * self.L[0] + ny * self.L[1] + nz * self.L[2], 0) * sh
        fill = np.maximum(nx * self.Lf[0] + ny * self.Lf[1] + nz * self.Lf[2], 0)
        hemi = 0.5 + 0.5 * ny
        lum = dif[:, None] * self.C_CLE + fill[:, None] * self.C_FILL \
            + (hemi[:, None] * vec(0.10, 0.10, 0.12) + (1 - hemi)[:, None] * vec(0.05, 0.04, 0.03)) * ao[:, None]
        for pos, couleur, intensite in self.points:
            lx, ly, lz = pos[0] - x, pos[1] - y, pos[2] - z
            d2 = lx * lx + ly * ly + lz * lz
            inv = 1 / np.sqrt(d2)
            ndl = np.maximum((nx * lx + ny * ly + nz * lz) * inv, 0)
            lum += (ndl * intensite / (1 + d2 * 1.2) * (0.4 + 0.6 * ao))[:, None] * couleur
        hx, hy, hz = self.L[0] - dx, self.L[1] - dy, self.L[2] - dz
        hl = np.sqrt(hx * hx + hy * hy + hz * hz)
        spec = np.maximum((nx * hx + ny * hy + nz * hz) / hl, 0) ** 48 * sh * brill
        return alb * lum + spec[:, None] * self.C_CLE * 0.6 + emis

    def post(self, rgb, touche, prof, ss):
        lum = np.maximum(rgb - 0.85, 0)
        rgb = rgb + 0.45 * flou(lum, 4 * ss) + 0.35 * flou(lum, 14 * ss)
        rgb = aces(rgb * 1.12)
        return rgb, touche.astype(F)


# ================================================================================================
# Scène 2 : nature morte « cabinet d'avocat »
# ================================================================================================
TABLE, SOCLE_B, BOIS, OR, CUIR_R, CUIR_V, PAGES = range(7)
OR_F0 = vec(1.0, 0.76, 0.33)


class Cabinet:
    nom = "cabinet-3d"
    transparent = False
    tmax = 40.0
    eps = 1.5e-4
    rel = 3.5e-4

    def __init__(self):
        self.cam = vec(-0.1, 2.3, 7.7)
        self.cible = vec(0.3, 1.22, -0.3)
        self.fov = math.radians(47)
        self.Lk = unitaire(vec(-0.55, 0.78, 0.5))
        self.Ck = vec(1.0, 0.86, 0.68) * 2.2
        self.Lr = unitaire(vec(0.85, 0.5, -0.8))
        self.Cr = vec(1.0, 0.74, 0.46) * 1.7
        self.H = vec(0.3, 0.50, 0.45)
        self.a = unitaire(vec(0.53, 0.0, 0.85))
        self.E = vec(-1.10, 0.10, 1.32)
        self.b = unitaire(self.E - self.H)
        self.S = vec(1.75, 0.0, -0.9)
        self.livres = [  # centre, demi-tailles, angle (rad), matériau de couverture
            (vec(-1.25, 0.075, -1.05), (0.78, 0.075, 0.56), math.radians(-14), CUIR_R),
            (vec(-1.2, 0.21, -1.08), (0.70, 0.06, 0.50), math.radians(4), CUIR_V),
        ]
        self.mise_au_point = float(np.linalg.norm(self.H - self.cam))

    def rayons(self, W, H):
        fwd = unitaire(self.cible - self.cam)
        right = unitaire(np.cross(fwd, vec(0, 1, 0)))
        up = np.cross(right, fwd).astype(F)
        tx = math.tan(self.fov / 2)
        u = ((np.arange(W, dtype=F) + 0.5) / W * 2 - 1) * tx
        v = (1 - (np.arange(H, dtype=F) + 0.5) / H * 2) * tx * H / W
        U, V = np.meshgrid(u, v)
        U, V = U.ravel(), V.ravel()
        dx = fwd[0] + U * right[0] + V * up[0]
        dy = fwd[1] + U * right[1] + V * up[1]
        dz = fwd[2] + U * right[2] + V * up[2]
        lg = np.sqrt(dx * dx + dy * dy + dz * dz)
        n = U.size
        return (np.full(n, self.cam[0], F), np.full(n, self.cam[1], F), np.full(n, self.cam[2], F),
                dx / lg, dy / lg, dz / lg)

    def projeter(self, p, W, H):
        fwd = unitaire(self.cible - self.cam)
        right = unitaire(np.cross(fwd, vec(0, 1, 0)))
        up = np.cross(right, fwd)
        d = p - self.cam
        z = float(d @ fwd)
        tx = math.tan(self.fov / 2)
        u = float(d @ right) / z / tx
        v = float(d @ up) / z / (tx * H / W)
        return (u + 1) / 2, (1 - v) / 2

    @staticmethod
    def _local(x, y, z, c, angle):
        ca, sa = math.cos(angle), math.sin(angle)
        px, pz = x - c[0], z - c[2]
        return ca * px + sa * pz, y - c[1], -sa * px + ca * pz

    def morceaux(self, x, y, z):
        m = [(y.copy(), TABLE)]
        socle = np.minimum(cyl_y(x, y, z, 0.3, 0.05, 0.45, 0.72, 0.05, 0.02),
                           cyl_y(x, y, z, 0.3, 0.16, 0.45, 0.62, 0.08, 0.025))
        m.append((socle, SOCLE_B))

        H, a, b, E = self.H, self.a, self.b, self.E
        tete = cylindre(x, y, z, H - a * 0.62, H + a * 0.62, 0.26, 0.05)
        manche = np.minimum(capsule(x, y, z, H, E, 0.068), sphere(x, y, z, E[0], E[1], E[2], 0.1))
        m.append((np.minimum(tete, manche), BOIS))
        ors = [cylindre(x, y, z, H + a * 0.35, H + a * 0.43, 0.272),
               cylindre(x, y, z, H - a * 0.43, H - a * 0.35, 0.272),
               cylindre(x, y, z, H + b * 0.24, H + b * 0.31, 0.105),
               cylindre(x, y, z, E - b * 0.22, E - b * 0.16, 0.08)]

        # Balance de la justice
        S = self.S
        sx, sz = float(S[0]), float(S[2])
        ors += [cyl_y(x, y, z, sx, 0.05, sz, 0.5, 0.05, 0.02),
                cyl_y(x, y, z, sx, 0.16, sz, 0.3, 0.06, 0.02),
                cyl_y(x, y, z, sx, 1.36, sz, 0.042, 1.16),
                sphere(x, y, z, sx, 0.34, sz, 0.085),
                sphere(x, y, z, sx, 1.3, sz, 0.065),
                sphere(x, y, z, sx, 2.64, sz, 0.075),
                capsule(x, y, z, vec(sx - 0.95, 2.5, sz), vec(sx + 0.95, 2.5, sz), 0.028),
                sphere(x, y, z, sx, 2.5, sz, 0.065)]
        for cote in (-1, 1):
            ex = sx + cote * 0.95
            ors.append(sphere(x, y, z, ex, 2.5, sz, 0.042))
            for th in (math.pi / 2, math.pi * 7 / 6, math.pi * 11 / 6):
                ors.append(capsule(x, y, z, vec(ex, 2.47, sz),
                                   vec(ex + 0.43 * math.cos(th), 1.44, sz + 0.43 * math.sin(th)), 0.011))
            coque = np.abs(sphere(x, y, z, ex, 1.858, sz, 0.6)) - 0.012
            ors.append(np.maximum(coque, y - 1.44))
        m.append((union(*ors), OR))

        for c, (w, h, d), ang, cuir in self.livres:
            lx, ly, lz = self._local(x, y, z, c, ang)
            couv = union(boite(lx, ly, lz, 0, h - 0.012, 0, w, 0.012, d, 0.006),
                         boite(lx, ly, lz, 0, -(h - 0.012), 0, w, 0.012, d, 0.006),
                         boite(lx, ly, lz, 0, 0, d - 0.016, w, h, 0.016, 0.008))
            m.append((couv, cuir))
            m.append((boite(lx, ly, lz, 0, 0, -0.01, w - 0.022, h - 0.018, d - 0.024), PAGES))
        return m

    def sdf(self, x, y, z):
        return union(*[d for d, _ in self.morceaux(x, y, z)])

    def sdf_mat(self, x, y, z):
        m = self.morceaux(x, y, z)
        D = np.stack([d for d, _ in m])
        i = np.argmin(D, 0)
        return np.array([k for _, k in m])[i]

    def env(self, dx, dy, dz):
        haut = np.clip(dy * 0.5 + 0.5, 0, 1)
        col = vec(0.022, 0.014, 0.009)[None, :] + vec(0.03, 0.018, 0.010)[None, :] * haut[:, None]
        s = dx * self.Lk[0] + dy * self.Lk[1] + dz * self.Lk[2]
        r = dx * self.Lr[0] + dy * self.Lr[1] + dz * self.Lr[2]
        col = col + vec(2.8, 2.2, 1.5) * lisse(0.955, 0.99, s)[:, None] \
            + vec(0.35, 0.22, 0.12) * (np.clip(s, 0, 1) ** 6)[:, None] \
            + vec(1.8, 1.2, 0.6) * lisse(0.965, 0.993, r)[:, None]
        return col

    def albedo(self, x, y, z, mat, nx, ny, nz):
        n = x.size
        alb = np.zeros((n, 3), F)
        reflet = np.zeros(n, F)   # poids de la réflexion (diélectriques)
        brill = np.full(n, 20.0, F)
        metal = mat == OR
        mk = mat == TABLE
        if mk.any():
            pz = z[mk] / 0.6
            planche = np.floor(pz)
            teinte = 0.75 + 0.4 * hachage(planche, 1.3)
            fil = fbm(x[mk] * 0.9 + planche * 7.1, z[mk] * 22.0, None, 4)
            veine = 0.5 + 0.5 * np.sin(z[mk] * 60 + fil * 9)
            g = np.clip(0.35 * veine + 0.75 * fil, 0, 1)
            c = vec(0.045, 0.026, 0.016)[None, :] + (vec(0.13, 0.075, 0.042) - vec(0.045, 0.026, 0.016))[None, :] * g[:, None]
            c *= teinte[:, None]
            c[fract(pz) < 0.012] *= 0.35
            alb[mk] = c
            reflet[mk] = 0.55
            brill[mk] = 70
        mk = (mat == SOCLE_B) | (mat == BOIS)
        if mk.any():
            fil = fbm(x[mk] * 3 + z[mk] * 9, y[mk] * 14, z[mk] * 3, 4)
            g = np.clip(0.3 + 0.9 * fil - 0.2, 0, 1)
            c = vec(0.07, 0.024, 0.013)[None, :] + (vec(0.21, 0.08, 0.04) - vec(0.07, 0.024, 0.013))[None, :] * g[:, None]
            alb[mk] = c
            reflet[mk] = 0.75
            brill[mk] = 110
            # Filet doré sur le socle
            filet = (mat[mk] == SOCLE_B) & (np.abs(y[mk] - 0.16) < 0.012) & (np.abs(ny[mk]) < 0.5)
            idx = np.nonzero(mk)[0][filet]
            metal[idx] = True
        for k_livre, (c0, (w, h, d), ang, cuir) in enumerate(self.livres):
            mk = mat == cuir
            if not mk.any():
                continue
            base = vec(0.15, 0.018, 0.022) if cuir == CUIR_R else vec(0.018, 0.06, 0.04)
            grain = 0.8 + 0.35 * bruit(x[mk] * 40, y[mk] * 40, z[mk] * 40)
            alb[mk] = base * grain[:, None]
            reflet[mk] = 0.12
            brill[mk] = 25
            lx, ly, lz = self._local(x[mk], y[mk], z[mk], c0, ang)
            dos = lz > d - 0.02
            bande = dos & ((np.abs(np.abs(lx) - (w - 0.14)) < 0.014) | (np.abs(np.abs(lx) - (w - 0.2)) < 0.006)
                           | ((np.abs(lx) < 0.2) & (np.abs(ly) < h * 0.38)))
            idx = np.nonzero(mk)[0][bande]
            metal[idx] = True
        mk = mat == PAGES
        if mk.any():
            alb[mk] = vec(0.72, 0.66, 0.52) * (0.85 + 0.15 * bruit(y[mk] * 900, x[mk] * 3, z[mk] * 3))[:, None]
            brill[mk] = 6
        alb[metal] = OR_F0 * 0.06
        brill[metal] = 160
        return alb, reflet, brill, metal

    def _eclairage_simple(self, x, y, z, dx, dy, dz):
        """Ombrage léger pour les points vus en réflexion (sans ombre ni second reflet)."""
        mat = self.sdf_mat(x, y, z)
        nx, ny, nz = normales(x, y, z, self.sdf, 8e-4)
        alb, _, _, metal = self.albedo(x, y, z, mat, nx, ny, nz)
        dif = np.maximum(nx * self.Lk[0] + ny * self.Lk[1] + nz * self.Lk[2], 0)
        rim = np.maximum(nx * self.Lr[0] + ny * self.Lr[1] + nz * self.Lr[2], 0)
        col = alb * (dif[:, None] * self.Ck + rim[:, None] * self.Cr + 0.06)
        if metal.any():
            dn = dx[metal] * nx[metal] + dy[metal] * ny[metal] + dz[metal] * nz[metal]
            rx, ry, rz = dx[metal] - 2 * dn * nx[metal], dy[metal] - 2 * dn * ny[metal], dz[metal] - 2 * dn * nz[metal]
            col[metal] = self.env(rx, ry, rz) * OR_F0
        return col

    def ombrer(self, x, y, z, dx, dy, dz):
        mat = self.sdf_mat(x, y, z)
        nx, ny, nz = normales(x, y, z, self.sdf, 6e-4)
        alb, reflet, brill, metal = self.albedo(x, y, z, mat, nx, ny, nz)
        n = x.size
        ex, ey, ez = x + nx * 2e-3, y + ny * 2e-3, z + nz * 2e-3
        sh_k = ombre(ex, ey, ez, self.Lk, self.sdf, 0.01, 8.0, 14.0, 0.004, 0.25)
        sh_r = ombre(ex, ey, ez, self.Lr, self.sdf, 0.01, 8.0, 10.0, 0.004, 0.25)
        ao = occlusion(x, y, z, nx, ny, nz, self.sdf, 0.25)
        ndk = np.maximum(nx * self.Lk[0] + ny * self.Lk[1] + nz * self.Lk[2], 0) * sh_k
        ndr = np.maximum(nx * self.Lr[0] + ny * self.Lr[1] + nz * self.Lr[2], 0) * sh_r
        hemi = 0.5 + 0.5 * ny
        amb = (hemi[:, None] * vec(0.05, 0.04, 0.035) + (1 - hemi)[:, None] * vec(0.03, 0.018, 0.01)) * ao[:, None]

        def speculaire(L):
            hx, hy, hz = L[0] - dx, L[1] - dy, L[2] - dz
            hl = np.sqrt(hx * hx + hy * hy + hz * hz)
            return np.maximum((nx * hx + ny * hy + nz * hz) / hl, 0) ** brill * (brill + 8) / 60

        sp = speculaire(self.Lk)[:, None] * sh_k[:, None] * self.Ck + speculaire(self.Lr)[:, None] * sh_r[:, None] * self.Cr

        # Réflexions : or et bois verni
        cos_v = np.clip(-(dx * nx + dy * ny + dz * nz), 0, 1)
        schlick = (1 - cos_v) ** 5
        poids = np.where(metal, 1.0, reflet * (0.04 + 0.96 * schlick))
        col_reflet = np.zeros((n, 3), F)
        sel = np.nonzero(poids > 0.01)[0]
        if sel.size:
            dn = dx[sel] * nx[sel] + dy[sel] * ny[sel] + dz[sel] * nz[sel]
            rx, ry, rz = dx[sel] - 2 * dn * nx[sel], dy[sel] - 2 * dn * ny[sel], dz[sel] - 2 * dn * nz[sel]
            ox, oy, oz = x[sel] + nx[sel] * 3e-3, y[sel] + ny[sel] * 3e-3, z[sel] + nz[sel] * 3e-3
            t, hit = marcher(ox, oy, oz, rx, ry, rz, self.sdf, 14.0, iters=140, eps=4e-4, rel=1e-3)
            c = self.env(rx, ry, rz)
            h = np.nonzero(hit)[0]
            if h.size:
                th = t[h]
                c[h] = self._eclairage_simple(ox[h] + rx[h] * th, oy[h] + ry[h] * th, oz[h] + rz[h] * th,
                                              rx[h], ry[h], rz[h])
            col_reflet[sel] = c

        diel = alb * (ndk[:, None] * self.Ck + ndr[:, None] * self.Cr + amb) + sp * 0.25 \
            + col_reflet * (reflet * (0.04 + 0.96 * schlick))[:, None]
        f_or = OR_F0[None, :] + (1 - OR_F0)[None, :] * schlick[:, None]
        met = col_reflet * f_or * (0.55 + 0.45 * ao)[:, None] + sp * OR_F0 * 0.9 + alb * amb * 4
        return np.where(metal[:, None], met, diel)

    def post(self, rgb, touche, prof, ss):
        Hh, W = touche.shape
        brouillard = vec(0.020, 0.012, 0.008)
        f = 1 - np.exp(-np.maximum(np.where(touche, prof, 1e3) - 7.6, 0) * 0.32)
        rgb = rgb * (1 - f[..., None]) + brouillard * f[..., None]
        # Profondeur de champ (mise au point sur le marteau)
        coc = np.clip(np.abs(np.where(touche, prof, 30.0) - self.mise_au_point) / self.mise_au_point * 2.4, 0, 1)
        rgb = rgb * (1 - coc[..., None]) + flou(rgb, 3 * ss) * coc[..., None]
        # Fond : halo chaud et bokeh derrière la balance
        v, u = np.mgrid[0:Hh, 0:W].astype(F)
        u, v = (u + 0.5) / W, (v + 0.5) / Hh
        r = W / Hh
        fond = vec(0.17, 0.095, 0.045)[None, None, :] * np.exp(-(((u - 0.8) * r) ** 2 / 0.25 + (v - 0.22) ** 2 / 0.09))[..., None]
        fond += vec(0.10, 0.05, 0.02)[None, None, :] * np.exp(-(((u - 0.25) * r) ** 2 / 0.5 + (v - 0.1) ** 2 / 0.06))[..., None]
        alea = np.random.default_rng(7)
        for _ in range(16):
            bu, bv = alea.uniform(0.45, 1.0), alea.uniform(0.02, 0.5)
            br = alea.uniform(0.012, 0.05)
            inten = alea.uniform(0.015, 0.09) * (0.4 + bu)
            teinte = vec(1.0, alea.uniform(0.62, 0.84), alea.uniform(0.32, 0.5))
            dist = np.sqrt(((u - bu) * r) ** 2 + (v - bv) ** 2) / br
            disque = lisse(1.0, 0.86, dist) * (0.75 + 0.25 * lisse(0.6, 0.98, dist))
            fond += teinte[None, None, :] * (inten * disque)[..., None]
        rgb = rgb + fond * f[..., None]
        lum = np.maximum(rgb - 1.0, 0)
        rgb = rgb + 0.35 * flou(lum, 5 * ss)
        rgb = aces(rgb * 0.85)
        vign = 1 - 0.42 * np.clip(((u - 0.55) * 1.1) ** 2 + ((v - 0.45) * 1.25) ** 2, 0, 1)
        rgb = rgb * vign[..., None]
        rgb = rgb + (np.random.default_rng(3).random(rgb.shape, dtype=F) - 0.5) / 255
        return rgb, None


# ================================================================================================
SCENES = {"palais": (Palais, 1500), "cabinet": (Cabinet, 1600)}


def produire(nom, largeur, ss, apercu):
    classe, largeur_defaut = SCENES[nom]
    scene = classe()
    W = largeur or largeur_defaut
    if apercu:
        W, ss = W // 3, 1
    ratio = getattr(scene, "ratio", 9 / 16)
    H = int(round(W * ratio))
    print(f"{scene.nom} : {W}×{H} (suréchantillonnage ×{ss})")
    debut = time.time()
    rgb, touche, prof = rendre(scene, W * ss, H * ss)
    rgb, alpha = scene.post(rgb, touche, prof, ss)
    suffixe = "-apercu" if apercu else ""
    chemin = enregistrer(rgb, alpha, (W, H), SORTIE / f"{scene.nom}{suffixe}.webp")
    print(f"→ {chemin.relative_to(RACINE)} en {time.time() - debut:.0f} s")
    if isinstance(scene, Palais):
        reperes = {"porte": vec(0, 2.0, 1.6), "fronton": vec(0, 5.3, 3.2), "coupole": vec(0, 7.0, -1.8),
                   "drapeau": vec(4.7, 6.7, 1.2), "allee": vec(0, 0.0, 6.5), "aile": vec(4.5, 3.7, -1.75)}
    else:
        reperes = {"marteau": scene.H, "balance": vec(1.75, 2.5, -0.9), "livres": vec(-0.7, 0.3, -0.6)}
    for cle, p in reperes.items():
        u, v = scene.projeter(p, W, H)
        print(f"   repère {cle:8s} : left {u * 100:5.1f} %  top {v * 100:5.1f} %")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("scene", choices=[*SCENES, "tout"])
    parser.add_argument("--largeur", type=int, default=0)
    parser.add_argument("--ss", type=int, default=2, help="suréchantillonnage (anticrénelage)")
    parser.add_argument("--apercu", action="store_true", help="rendu rapide au tiers de la taille")
    args = parser.parse_args()
    for nom in (SCENES if args.scene == "tout" else [args.scene]):
        produire(nom, args.largeur, args.ss, args.apercu)


if __name__ == "__main__":
    main()
