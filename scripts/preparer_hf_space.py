"""Prépare le dossier à publier sur Hugging Face Spaces (SDK Docker).

    python scripts/preparer_hf_space.py            → crée dist/hf-space/

Le dossier ne contient que ce qu'il faut pour construire l'image : code, interface, données
juridiques publiques, Dockerfile. Jamais .env, la base des comptes, les rapports ni les documents
personnels (rapport, journal de stage). Les secrets (ANTHROPIC_API_KEY, BRAVE_API_KEY) se
définissent dans les « Settings → Variables and secrets » du Space, pas dans les fichiers.
"""

import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
SORTIE = RACINE / "dist" / "hf-space"
A_COPIER = ["src", "web", "mobile", "data", "scripts", "Dockerfile", "requirements-prod.txt", ".dockerignore", ".env.example"]
REMPLACEMENTS_ISTOCK = {"justice-livre.webp": "palais-justice-tunis.webp", "justice-bibliotheque.webp": "kasbah-tunis.webp"}
EXCLUS = {"__pycache__", "amena.db", "amena.db-wal", "amena.db-shm", "dist"}

ENTETE = """---
title: AMENA
emoji: ⚖️
colorFrom: red
colorTo: pink
sdk: docker
app_port: 8000
pinned: false
short_description: Assistant avocat IA — le droit tunisien expliqué à tous
---

# AMENA — أمانة

Assistant avocat intelligent qui explique le droit tunisien à tous, en français, en arabe et en
derja : travail, contrats, famille, terres, pénal, numérique, violences. Projet de fin d'année
(ESPRIT, 2026) de Mohamed Aziz Rahouej.

- Réponses structurées comme une consultation : ce que dit la loi (articles cités), les étapes,
  les preuves, les délais, un conseil, puis le dossier PDF pour l'avocat(e).
- Base juridique : 37 textes, dont les textes officiels intégraux (Constitution, Code pénal,
  Code de procédure pénale, Code du travail, Code des obligations et des contrats, Code des droits
  réels, loi 2017-58, décret-loi 2022-54, Code de la protection de l'enfant).
- Confidentialité : aucun message n'est conservé.

AMENA informe et oriente ; elle ne remplace pas un avocat. En danger : 197 (police), 190 (SAMU),
1899 (violences faites aux femmes).

Configuration (Settings → Variables and secrets) : `ANTHROPIC_API_KEY` (optionnel, réponses
rédigées par Claude), `AMENA_RECHERCHE_EXTERNE=1` et `BRAVE_API_KEY` (optionnel, recherche externe).
"""


def ignorer(dossier, noms):
    return [n for n in noms if n in EXCLUS or n.endswith(".pyc")]


RENDER_YAML = """# Render Blueprint : https://render.com/docs/blueprint-spec
services:
  - type: web
    name: amena
    runtime: docker
    plan: free
    dockerfilePath: ./Dockerfile
    healthCheckPath: /api/sante
    autoDeploy: true
    envVars:
      - key: AMENA_LLM
        value: claude
      - key: AMENA_RECHERCHE_EXTERNE
        value: "0"
      # Secrets facultatifs, à saisir dans le tableau de bord Render (jamais dans ce fichier)
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: BRAVE_API_KEY
        sync: false
"""

GITIGNORE = """__pycache__/
*.pyc
.env
data/amena.db
data/amena.db-*
"""


def main():
    global SORTIE
    render = "render" in sys.argv[1:]
    if render:
        SORTIE = RACINE / "dist" / "render"
    # On vide le dossier, mais on garde son historique Git (.git) : un simple « git push » suffit
    # ensuite pour mettre le site à jour.
    SORTIE.mkdir(parents=True, exist_ok=True)
    for element in SORTIE.iterdir():
        if element.name == ".git":
            continue
        shutil.rmtree(element) if element.is_dir() else element.unlink()
    for nom in A_COPIER:
        source = RACINE / nom
        if source.is_dir():
            shutil.copytree(source, SORTIE / nom, ignore=ignorer)
        elif source.exists():
            shutil.copy2(source, SORTIE / nom)
    # Sur GitHub/Render, pas d'en-tête de configuration Hugging Face.
    (SORTIE / "README.md").write_text(ENTETE.split("---", 2)[2].lstrip() if render else ENTETE, encoding="utf-8")
    if render:
        (SORTIE / "render.yaml").write_text(RENDER_YAML, encoding="utf-8")
        (SORTIE / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
        (SORTIE / ".gitattributes").write_text("* text=auto eol=lf\n*.pdf binary\n*.webp binary\n*.png binary\n*.jpg binary\n*.xlsx binary\n", encoding="utf-8")
    # Photos iStock : licence payante non acquise, donc pas de publication en ligne. Elles sont
    # remplacées par les photos libres de Tunisie (Wikimedia Commons), créditées dans le pied de page.
    photos = SORTIE / "web" / "img" / "photos"
    for istock, libre in REMPLACEMENTS_ISTOCK.items():
        shutil.copy2(photos / libre, photos / istock)
    i18n = SORTIE / "web" / "js" / "i18n.js"
    texte = i18n.read_text(encoding="utf-8")
    i18n.write_text(texte.replace("Freepik, Pngtree, iStock", "Freepik, Pngtree").replace("Freepik، Pngtree، iStock", "Freepik، Pngtree"),
                    encoding="utf-8")
    fichiers = [f for f in SORTIE.rglob("*") if f.is_file()]
    taille = sum(f.stat().st_size for f in fichiers) / 1e6
    print(f"{SORTIE} : {len(fichiers)} fichiers, {taille:.1f} Mo")
    gros = [f for f in fichiers if f.stat().st_size > 10e6]
    if gros:
        print("Fichiers > 10 Mo (stockés en LFS/Xet par Hugging Face) :", [str(f.relative_to(SORTIE)) for f in gros])


if __name__ == "__main__":
    main()
