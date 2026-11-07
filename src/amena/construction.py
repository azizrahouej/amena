"""Construit tous les artefacts : base juridique, chunks, index de recherche, modèle de triage."""

import pandas as pd

from .config import FICHIER_TRIAGE
from .ingestion import construire_chunks
from .juridique import charger_bibliotheque
from .recherche import MoteurRecherche
from .triage import Trieur


def construire_base(verbeux=True):
    from .base import connexion
    from .donnees_wbl import charger_en_base
    stats = charger_bibliotheque()
    monde = charger_en_base(connexion())
    if verbeux:
        print(f"Base juridique : {stats['pays']} pays/zones, {stats['textes']} textes, "
              f"{stats['articles']} articles, {stats['analyses']} analyses (forces, lacunes, vigilance).")
        print(f"Données Banque mondiale (WBL 2026) : {monde['pays']} pays, {monde['indicateurs']} indicateurs.")
    return stats


def construire_index(verbeux=True):
    chunks = construire_chunks()
    moteur = MoteurRecherche(chunks)
    moteur.sauvegarder()
    if verbeux:
        fiches = sum(1 for c in chunks if c["metadata"]["type"] == "fiche")
        print(f"Index de recherche : {len(chunks)} passages ({fiches} de fiches, {len(chunks) - fiches} d'articles de loi).")
    return moteur


def entrainer_triage(verbeux=True):
    if not FICHIER_TRIAGE.exists():
        import runpy
        from .config import RACINE
        runpy.run_path(str(RACINE / "scripts" / "generer_dataset_triage.py"), run_name="__main__")
    df = pd.read_csv(FICHIER_TRIAGE)
    trieur = Trieur().entrainer(df["texte"], df["label"])
    trieur.sauvegarder()
    if verbeux:
        print(f"Modèle de triage entraîné sur {len(df)} messages.")
    return trieur


def tout_construire(verbeux=True):
    construire_base(verbeux)
    construire_index(verbeux)
    entrainer_triage(verbeux)
