"""Système de recommandation hybride (même principe que la séance « système de recommandation »).

Éléments recommandables : les fiches pratiques (fiche:<id>) et les textes de loi (loi:<id>).

Score final = 0,70 × similarité de CONTENU + 0,20 × filtrage COLLABORATIF + 0,10 × POPULARITÉ

    contenu       TF-IDF de chaque élément ; profil de l'utilisatrice = moyenne pondérée des
                  éléments consultés (vue 1, sujet de conversation 1,5, utile 2, favori 3)
                  + ses centres d'intérêt déclarés à l'inscription ;
    collaboratif  « les personnes qui ont consulté X ont aussi consulté Y » : co-occurrences
                  item-item entre utilisatrices (cosinus) ;
    popularité    nombre d'utilisatrices ayant consulté l'élément (démarrage à froid).

Chaque recommandation est accompagnée de son EXPLICATION.
"""

from collections import defaultdict

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import comptes, juridique
from .config import DOSSIER_KB
from .ingestion import sections_markdown
from .securite import normaliser


def catalogue():
    """Tous les éléments recommandables, avec le texte qui les décrit."""
    elements = []
    for fichier in sorted(DOSSIER_KB.glob("*.md")):
        sections = sections_markdown(fichier)
        if sections:
            elements.append({"id": f"fiche:{fichier.stem}", "type": "fiche", "titre": sections[0]["chemin"][0],
                             "texte": " ".join(" ".join(s["chemin"]) + " " + s["texte"] for s in sections),
                             "pays": "TN"})
    for t in juridique.lister_textes():
        detail = juridique.detail_texte(t["id"])
        corps = " ".join(f"{a['titre']} {a['contenu']}" for a in detail["articles"])
        elements.append({"id": f"loi:{t['id']}", "type": "loi", "titre": t["titre"], "pays": t["pays"],
                         "pays_nom": t["pays_nom"],
                         "texte": f"{t['titre']} {' '.join(t['domaines'] * 2)} {t['resume']} {corps}"})
    return elements


class Recommandeur:
    def __init__(self):
        self.elements = catalogue()
        self.index = {e["id"]: i for i, e in enumerate(self.elements)}
        self.vectoriseur = TfidfVectorizer(sublinear_tf=True, ngram_range=(1, 2), min_df=1)
        self.matrice = self.vectoriseur.fit_transform([normaliser(e["texte"]) for e in self.elements])

    def _collaboratif(self, interactions_utilisatrice):
        """Similarité item-item à partir des interactions de toutes les utilisatrices."""
        toutes = comptes.toutes_interactions()
        n = len(self.elements)
        par_utilisatrice = defaultdict(dict)
        for ligne in toutes:
            if ligne["element"] in self.index:
                par_utilisatrice[ligne["utilisateur_id"]][self.index[ligne["element"]]] = ligne["poids"]
        if len(par_utilisatrice) < 2:
            return np.zeros(n), np.zeros(n)
        utilisatrices = list(par_utilisatrice)
        m = np.zeros((len(utilisatrices), n))
        for u, (uid, vus) in enumerate(par_utilisatrice.items()):
            for i, poids in vus.items():
                m[u, i] = poids
        popularite = (m > 0).sum(axis=0) / len(utilisatrices)
        similarite = cosine_similarity(m.T)  # éléments × éléments
        np.fill_diagonal(similarite, 0)
        score = np.zeros(n)
        for element, poids in interactions_utilisatrice.items():
            score += poids * similarite[self.index[element]]
        if score.max() > 0:
            score /= score.max()
        return score, popularite

    def recommander(self, utilisateur, k=6):
        historique = defaultdict(float)
        for ligne in comptes.historique(utilisateur["id"], limite=200):
            if ligne["element"] in self.index:
                historique[ligne["element"]] += ligne["poids"]

        # --- Profil de contenu ---
        profil = np.zeros(self.matrice.shape[1])
        if historique:
            for element, poids in historique.items():
                profil += poids * self.matrice[self.index[element]].toarray()[0]
        if utilisateur.get("interets"):
            interets = self.vectoriseur.transform([normaliser(" ".join(utilisateur["interets"]))]).toarray()[0]
            profil += 2.0 * interets
        contenu = (cosine_similarity(profil.reshape(1, -1), self.matrice)[0]
                   if profil.any() else np.zeros(len(self.elements)))

        collaboratif, popularite = self._collaboratif(historique)
        score = 0.70 * contenu + 0.20 * collaboratif + 0.10 * popularite

        # On privilégie le pays de l'utilisatrice et l'international, et les fiches pratiques
        # (plus directement utiles qu'un texte de loi brut).
        for i, e in enumerate(self.elements):
            if e["pays"] not in (utilisateur.get("pays", "TN"), "INT"):
                score[i] *= 0.5
            if e["type"] == "fiche":
                score[i] *= 1.25

        # On ne recommande pas ce qui est déjà en favori ; ce qui a déjà été lu passe en fin de liste.
        favoris = set(comptes.favoris(utilisateur["id"]))
        candidats = [i for i in np.argsort(score)[::-1] if self.elements[i]["id"] not in favoris]
        ordre = ([i for i in candidats if self.elements[i]["id"] not in historique]
                 + [i for i in candidats if self.elements[i]["id"] in historique])
        if not profil.any() and not collaboratif.any():
            # Démarrage à froid complet : sélection éditoriale (fiches essentielles d'abord).
            ordre = sorted(range(len(self.elements)), key=lambda i: (self.elements[i]["type"] != "fiche", i))

        # Diversité : au plus un texte par pays étranger dans la sélection.
        retenus, pays_vus = [], set()
        for i in ordre:
            e = self.elements[i]
            if e["type"] == "loi" and e["pays"] not in (utilisateur.get("pays", "TN"), "INT"):
                if e["pays"] in pays_vus:
                    continue
                pays_vus.add(e["pays"])
            retenus.append(i)
        ordre = retenus

        sortie = []
        for i in ordre[:k]:
            e = self.elements[i]
            sortie.append({"id": e["id"], "type": e["type"], "titre": e["titre"], "pays": e["pays"],
                           "pays_nom": e.get("pays_nom", "Tunisie"), "score": round(float(score[i]), 3),
                           "raison": self._raison(i, historique, utilisateur, contenu[i], collaboratif[i])})
        return sortie

    def _raison(self, i, historique, utilisateur, s_contenu, s_collab):
        if s_collab > s_contenu and s_collab > 0:
            return "Consulté par des personnes ayant des besoins proches des vôtres"
        if historique:
            proches = sorted(historique, key=lambda el: -cosine_similarity(
                self.matrice[self.index[el]], self.matrice[i])[0, 0])
            proche = next((p for p in proches if p != self.elements[i]["id"]), None)
            if proche:
                return f"Proche de « {self.elements[self.index[proche]]['titre'][:60]} »"
        if utilisateur.get("interets"):
            return f"Correspond à vos centres d'intérêt : {', '.join(utilisateur['interets'][:2])}"
        return "Essentiel pour commencer"
