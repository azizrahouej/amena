"""Chemins et réglages centralisés du projet."""

import os
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]

DOSSIER_KB = RACINE / "data" / "knowledge_base"
DOSSIER_PDF = RACINE / "data" / "pdf"
FICHIER_CHUNKS = RACINE / "data" / "processed" / "chunks.jsonl"
FICHIER_TRIAGE = RACINE / "data" / "triage" / "messages_triage.csv"

DOSSIER_MODELES = RACINE / "models"
MODELE_TRIAGE = DOSSIER_MODELES / "triage.joblib"
INDEX_RECHERCHE = DOSSIER_MODELES / "index_recherche.joblib"
RAPPORT_EVALUATION = RACINE / "reports" / "evaluation.json"

DOSSIER_WEB = RACINE / "web"


def _charger_env():
    """Lit un éventuel fichier .env sans dépendance externe."""
    fichier = RACINE / ".env"
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, valeur = ligne.split("=", 1)
        # Une variable déjà définie dans le terminal reste prioritaire.
        os.environ.setdefault(cle.strip(), valeur.strip())


_charger_env()

MODELE_LLM = os.getenv("AMENA_MODEL", "claude-opus-5-5")
UTILISER_EMBEDDINGS = os.getenv("AMENA_EMBEDDINGS", "0") == "1"
MODELE_EMBEDDINGS = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = int(os.getenv("AMENA_TOP_K", "4"))

# Découpage en chunks (mêmes réglages que la séance "Du PDF aux chunks", adaptés
# à des documents plus courts).
CHUNK_CIBLE = 220
CHUNK_OVERLAP = 40
CHUNK_MINIMUM = 15
