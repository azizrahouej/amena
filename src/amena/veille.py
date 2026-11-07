"""Veille des connaissances : la base juridique et l'index se reconstruisent tout seuls.

Une empreinte (nom, taille, date) de toutes les sources de connaissance est calculée :
    data/lois_officielles/*.pdf      textes officiels intégraux (Constitution, codes, lois)
    data/pdf/*.pdf                   autres documents officiels
    data/juridique/**/*.json         bibliothèque, base d'expertise, catalogue des textes officiels
    data/knowledge_base/*.md         fiches pratiques
Au démarrage du serveur puis toutes les minutes, si l'empreinte a changé (un PDF déposé, une
fiche modifiée), la base SQLite et l'index de recherche sont reconstruits en arrière-plan, puis
l'assistant recharge le nouvel index. Personne n'a besoin de relancer quoi que ce soit.

Désactivation : AMENA_VEILLE=0. Intervalle : AMENA_VEILLE_SECONDES (60 par défaut).
"""

import hashlib
import os
import threading
import time

from .config import DOSSIER_KB, DOSSIER_MODELES, DOSSIER_PDF, RACINE

ACTIVE = os.getenv("AMENA_VEILLE", "1") == "1"
INTERVALLE = int(os.getenv("AMENA_VEILLE_SECONDES", "60"))
FICHIER_EMPREINTE = DOSSIER_MODELES / "empreinte_connaissances.txt"

_SOURCES = [
    (RACINE / "data" / "lois_officielles", "*.pdf"),
    (RACINE / "data" / "lois_officielles", "*.html"),
    (DOSSIER_PDF, "*.pdf"),
    (RACINE / "data" / "juridique", "**/*.json"),
    (DOSSIER_KB, "*.md"),
]
_verrou = threading.Lock()
etat = {"derniere_verification": None, "derniere_reconstruction": None, "reconstructions": 0, "erreur": None}


def empreinte():
    h = hashlib.sha256()
    for dossier, motif in _SOURCES:
        if not dossier.exists():
            continue
        for f in sorted(dossier.glob(motif)):
            if f.name == "extraits.json":      # cache produit par l'extraction elle-même
                continue
            s = f.stat()
            h.update(f"{f.relative_to(RACINE)}|{s.st_size}|{int(s.st_mtime)}\n".encode())
    return h.hexdigest()


def a_jour():
    return FICHIER_EMPREINTE.exists() and FICHIER_EMPREINTE.read_text().strip() == empreinte()


def marquer_a_jour():
    FICHIER_EMPREINTE.parent.mkdir(parents=True, exist_ok=True)
    FICHIER_EMPREINTE.write_text(empreinte())


def reconstruire_si_besoin(apres=None):
    """Reconstruit base et index si les sources ont changé. Renvoie True si c'est le cas."""
    etat["derniere_verification"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if a_jour() or not _verrou.acquire(blocking=False):
        return False
    try:
        from .construction import construire_base, construire_index
        construire_base(verbeux=False)
        construire_index(verbeux=False)
        marquer_a_jour()
        etat.update(derniere_reconstruction=time.strftime("%Y-%m-%d %H:%M:%S"), erreur=None)
        etat["reconstructions"] += 1
        if apres:
            apres()
        return True
    except Exception as erreur:  # une source illisible ne doit jamais arrêter le serveur
        etat["erreur"] = f"{type(erreur).__name__}: {erreur}"
        return False
    finally:
        _verrou.release()


def demarrer(apres=None):
    """Lance la surveillance en arrière-plan (thread démon)."""
    if not ACTIVE:
        return None

    def boucle():
        while True:
            reconstruire_si_besoin(apres)
            time.sleep(INTERVALLE)

    fil = threading.Thread(target=boucle, name="amena-veille", daemon=True)
    fil.start()
    return fil
