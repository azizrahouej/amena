"""Statistiques d'usage ANONYMES et AGRÉGÉES, destinées aux associations partenaires.

On ne conserve que des compteurs (nombre de messages par jour, par catégorie, par langue,
avis utile / pas utile). Aucun texte, aucune adresse IP, aucun identifiant n'est enregistré :
il est impossible de retrouver une conversation à partir de ce fichier.

Désactivation complète : AMENA_STATS=0.
"""

import json
import os
import threading
from collections import Counter
from datetime import date

from .config import RACINE

FICHIER_STATS = RACINE / "reports" / "statistiques.json"
ACTIVEES = os.getenv("AMENA_STATS", "1") == "1"


class Statistiques:
    def __init__(self, fichier=FICHIER_STATS, activees=ACTIVEES):
        self.fichier = fichier
        self.activees = activees
        self._verrou = threading.Lock()
        self._jours = {}
        if fichier.exists():
            try:
                self._jours = json.loads(fichier.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._jours = {}

    def _incrementer(self, cles):
        if not self.activees:
            return
        with self._verrou:
            jour = self._jours.setdefault(date.today().isoformat(), {})
            for cle in cles:
                jour[cle] = jour.get(cle, 0) + 1
            self.fichier.parent.mkdir(parents=True, exist_ok=True)
            self.fichier.write_text(json.dumps(self._jours, indent=1), encoding="utf-8")

    def message(self, label, langue, mode):
        self._incrementer(["messages", f"triage:{label}", f"langue:{langue}", f"mode:{mode}"])

    def avis(self, utile):
        self._incrementer(["avis:utile" if utile else "avis:pas_utile"])

    def evaluation_risque(self, niveau):
        self._incrementer(["risque:total", f"risque:{niveau}"])

    def analyse(self, urgence):
        self._incrementer(["analyse:total"] + (["analyse:urgence"] if urgence else []))

    def resume(self):
        total = Counter()
        for compteurs in self._jours.values():
            total.update(compteurs)

        def groupe(prefixe):
            return {cle.split(":", 1)[1]: n for cle, n in total.items() if cle.startswith(prefixe + ":")}

        jours = sorted(self._jours)[-30:]
        return {
            "activees": self.activees,
            "messages": total.get("messages", 0),
            "par_jour": [{"jour": j, "messages": self._jours[j].get("messages", 0)} for j in jours],
            "triage": groupe("triage"),
            "langue": groupe("langue"),
            "mode": groupe("mode"),
            "avis": groupe("avis"),
            "risque": groupe("risque"),
            "analyse": groupe("analyse"),
        }
