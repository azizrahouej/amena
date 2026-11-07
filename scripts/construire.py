"""Construit toute la chaîne : base juridique, dataset de triage, chunks, index, modèle.

Usage :  python scripts/construire.py
"""

import runpy
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from amena.construction import construire_base, construire_index, entrainer_triage  # noqa: E402

if __name__ == "__main__":
    print("1/4  Base de données juridique (SQLite + FTS5)")
    construire_base()
    print("\n2/4  Génération du jeu de triage synthétique")
    runpy.run_path(str(RACINE / "scripts" / "generer_dataset_triage.py"), run_name="__main__")
    print("\n3/4  Ingestion des fiches et des articles de loi, indexation")
    construire_index()
    print("\n4/4  Entraînement du modèle de triage")
    entrainer_triage()
    print("\nTerminé. Lancez l'évaluation : python scripts/evaluer.py")
