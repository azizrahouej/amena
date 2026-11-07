"""Publie dist/hf-space sur Hugging Face Spaces (SDK Docker).

Prérequis : être connecté (python -m huggingface_hub.cli.hf auth login) ; le jeton reste dans le
gestionnaire de Hugging Face, jamais dans le projet.

    python scripts/preparer_hf_space.py
    python scripts/publier_hf_space.py [nom] [--prive]
"""

import sys
from pathlib import Path

from huggingface_hub import HfApi

DOSSIER = Path(__file__).resolve().parents[1] / "dist" / "hf-space"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    nom = args[0] if args else "amena"
    prive = "--prive" in sys.argv
    api = HfApi()
    compte = api.whoami()["name"]
    depot = f"{compte}/{nom}"
    api.create_repo(depot, repo_type="space", space_sdk="docker", private=prive, exist_ok=True)
    api.upload_folder(folder_path=str(DOSSIER), repo_id=depot, repo_type="space",
                      commit_message="Déploiement d'AMENA (image Docker)")
    print(f"Space : https://huggingface.co/spaces/{depot}")
    print(f"Site  : https://{compte.lower()}-{nom.lower()}.hf.space")


if __name__ == "__main__":
    main()
