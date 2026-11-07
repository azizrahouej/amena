"""Limite de débit en mémoire : protège le serveur (gratuit, 512 Mo) contre les abus et le spam.

Une fenêtre glissante par adresse et par groupe de routes. Rien n'est écrit sur disque et l'adresse
n'est gardée que le temps de la fenêtre (au plus une heure), sous forme hachée.
"""

import hashlib
import os
import threading
import time
from collections import defaultdict, deque

# groupe → [(fenêtre en secondes, nombre maximal de requêtes)]
REGLES = {
    "question": [(60, int(os.getenv("AMENA_LIMITE_MINUTE", "10"))), (3600, int(os.getenv("AMENA_LIMITE_HEURE", "100")))],
    "compte": [(60, 10), (3600, 60)],
}
ROUTES = {
    "/api/chat": "question", "/api/chat/flux": "question", "/api/analyse": "question", "/api/triage": "question",
    "/api/auth/connexion": "compte", "/api/auth/inscription": "compte",
}
MESSAGE = {
    "fr": "Trop de demandes en peu de temps. Patientez une minute avant de reposer une question. "
          "En danger : 197 (police), 190 (SAMU), 1899.",
    "ar": "طلبات كثيرة في وقت قصير. انتظر دقيقة قبل طرح سؤال جديد. في حالة الخطر: 197، 190، 1899.",
}

_historique = defaultdict(deque)
_verrou = threading.Lock()
_dernier_menage = [0.0]


def _cle(adresse, groupe):
    return groupe + ":" + hashlib.sha256((adresse or "?").encode()).hexdigest()[:20]


def adresse_client(request):
    """Adresse réelle derrière l'hébergeur (en-tête X-Forwarded-For posé par le proxy de Render)."""
    transmis = request.headers.get("x-forwarded-for", "")
    if transmis:
        return transmis.split(",")[0].strip()
    return request.client.host if request.client else "?"


def autoriser(adresse, chemin, maintenant=None):
    """Renvoie (autorisé, secondes à attendre)."""
    groupe = ROUTES.get(chemin)
    if not groupe or os.getenv("AMENA_LIMITES", "1") == "0":
        return True, 0
    maintenant = maintenant or time.time()
    cle = _cle(adresse, groupe)
    plus_longue = max(f for f, _ in REGLES[groupe])
    with _verrou:
        file = _historique[cle]
        while file and maintenant - file[0] > plus_longue:
            file.popleft()
        for fenetre, maximum in REGLES[groupe]:
            recentes = [t for t in file if maintenant - t <= fenetre]
            if len(recentes) >= maximum:
                return False, int(fenetre - (maintenant - recentes[0])) + 1
        file.append(maintenant)
        if maintenant - _dernier_menage[0] > 600:  # ménage : on oublie les adresses inactives
            for k in [k for k, f in _historique.items() if not f or maintenant - f[-1] > plus_longue]:
                del _historique[k]
            _dernier_menage[0] = maintenant
    return True, 0
