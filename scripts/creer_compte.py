"""Crée un compte partenaire (association) ou administrateur.

Usage :  python scripts/creer_compte.py <pseudo> --role partenaire
Le mot de passe est demandé de façon masquée : il n'apparaît ni à l'écran ni dans l'historique.
"""

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from amena.comptes import ErreurCompte, inscrire  # noqa: E402

if __name__ == "__main__":
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("pseudo")
    parseur.add_argument("--role", choices=["partenaire", "admin"], default="partenaire")
    args = parseur.parse_args()

    mot_de_passe = getpass.getpass("Mot de passe (8 caractères minimum) : ")
    if mot_de_passe != getpass.getpass("Confirmer : "):
        sys.exit("Les mots de passe ne correspondent pas.")
    try:
        inscrire(args.pseudo, mot_de_passe, role=args.role)
    except ErreurCompte as erreur:
        sys.exit(str(erreur))
    print(f"Compte « {args.pseudo} » créé avec le rôle {args.role}.")
