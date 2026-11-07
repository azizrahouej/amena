"""Moteur de recherche de la base de connaissances (le « R » de RAG).

Recherche hybride :
    - TF-IDF sur n-grammes de CARACTÈRES : robuste aux fautes de frappe, à l'arabe
      et aux variantes d'écriture (« plainte », « plaintes », « plainte? ») ;
    - TF-IDF sur MOTS : précis sur les termes juridiques ;
    - embeddings multilingues (optionnel, AMENA_EMBEDDINGS=1) : rapprochent une
      question en arabe d'un passage en français, par le SENS et non par les mots.

Le dialecte tunisien écrit en latin (arabizi) n'est couvert par aucun modèle
pré-entraîné. On ajoute donc une EXPANSION DE REQUÊTE : un petit lexique
darija/arabe -> français, qui traduit les mots-clés avant la recherche.
"""

import re

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .config import INDEX_RECHERCHE, MODELE_EMBEDDINGS, TOP_K, UTILISER_EMBEDDINGS
from .securite import normaliser

LEXIQUE_EXPANSION = {
    # dialecte tunisien (arabizi)
    "chekaya": "plainte", "n9ayed": "porter plainte", "9anoun": "loi droit",
    "rajli": "mari conjoint", "yadhrab": "frappe violence physique",
    "nafa9a": "pension alimentaire", "7imaya": "protection ordonnance",
    "jam3iya": "association", "nomrou": "numéro", "ra9m": "numéro",
    "police": "police plainte", "7aras": "garde nationale", "sbitar": "hôpital",
    "chhada": "certificat médical", "tbiya": "médical", "avocat": "avocat aide juridictionnelle",
    "talak": "divorce", "wled": "enfants garde", "flous": "argent violence économique",
    "5edma": "travail", "facebook": "harcèlement en ligne", "tsawri": "photos images",
    "nbet": "hébergement centre", "centre": "centre hébergement", "psychologue": "soutien psychologique",
    "n7ki": "parler écoute", "wa7di": "seule isolement", "khayfa": "peur",
    # arabe standard
    "شكايه": "plainte", "قانون": "loi", "حمايه": "protection ordonnance",
    "نفقه": "pension alimentaire", "جمعيه": "association", "رقم": "numéro",
    "تحرش": "harcèlement", "طلاق": "divorce", "محامي": "avocat aide juridictionnelle",
    "ايواء": "hébergement centre", "عنف": "violence", "اصغاء": "écoute centre",
}


def etendre_requete(question):
    """Ajoute à la question les traductions françaises de ses mots-clés."""
    q = normaliser(question)
    ajouts = [fr for mot, fr in LEXIQUE_EXPANSION.items() if mot in q]
    return normaliser(q + " " + " ".join(ajouts))


class MoteurRecherche:
    def __init__(self, chunks):
        self.chunks = chunks
        textes = [normaliser(c["texte"]) for c in chunks]

        self.vec_car = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self.vec_mots = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True,
                                        token_pattern=r"(?u)\b\w\w+\b")
        self.mat_car = self.vec_car.fit_transform(textes)
        self.mat_mots = self.vec_mots.fit_transform(textes)

        self.encodeur, self.mat_dense = None, None
        if UTILISER_EMBEDDINGS:
            self._activer_embeddings()

    def _activer_embeddings(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print("sentence-transformers absent : recherche lexicale seule.")
            return
        self.encodeur = SentenceTransformer(MODELE_EMBEDDINGS)
        self.mat_dense = self.encodeur.encode([c["texte"] for c in self.chunks],
                                              normalize_embeddings=True)

    def scores(self, question):
        """Score de pertinence de chaque chunk pour la question (entre 0 et 1 environ)."""
        requete = etendre_requete(question)
        s_car = cosine_similarity(self.vec_car.transform([requete]), self.mat_car)[0]
        s_mots = cosine_similarity(self.vec_mots.transform([requete]), self.mat_mots)[0]
        score = 0.5 * s_car + 0.5 * s_mots
        if self.encodeur is not None:
            q = self.encodeur.encode([question], normalize_embeddings=True)
            s_dense = (self.mat_dense @ q.T).ravel()
            score = 0.4 * score + 0.6 * s_dense
        return score

    def rechercher(self, question, k=TOP_K, seuil=0.03, types=None, pays=None):
        """types : {"fiche", "loi"} pour restreindre ; pays : garde ce pays et l'international."""
        scores = self.scores(question)
        for i, c in enumerate(self.chunks):
            meta = c["metadata"]
            if types and meta.get("type", "fiche") not in types:
                scores[i] = 0
            elif pays and meta.get("type") == "loi" and meta.get("pays") not in (pays, "INT"):
                scores[i] = 0
        meilleurs = np.argsort(scores)[::-1][:k]
        return [{**self.chunks[i], "score": float(scores[i])}
                for i in meilleurs if scores[i] >= seuil]

    # --- persistance ---
    def sauvegarder(self, chemin=INDEX_RECHERCHE):
        chemin.parent.mkdir(parents=True, exist_ok=True)
        # L'encodeur neuronal est rechargé à la demande, pas sérialisé.
        encodeur, self.encodeur = self.encodeur, None
        joblib.dump(self, chemin)
        self.encodeur = encodeur

    @staticmethod
    def charger(chemin=INDEX_RECHERCHE):
        moteur = joblib.load(chemin)
        if UTILISER_EMBEDDINGS and moteur.mat_dense is not None:
            from sentence_transformers import SentenceTransformer
            moteur.encodeur = SentenceTransformer(MODELE_EMBEDDINGS)
        elif UTILISER_EMBEDDINGS:
            moteur._activer_embeddings()
        return moteur


def phrases_pertinentes(question, chunks, n=4):
    """Sélectionne les phrases des chunks les plus proches de la question (mode extractif)."""
    candidates, vues = [], set()
    for c in chunks:
        corps = c["texte"].split("\n\n", 1)[-1]
        # On ne coupe qu'avant une majuscule (ou une lettre arabe) : « Art. 3 » reste entier.
        for p in re.split(r"(?<=[.!?؟])\s+(?=[A-ZÀ-ÖØ-Þ؀-ۿ«])", corps):
            p = p.strip()
            # Le recouvrement entre chunks répète des phrases : on ne les garde qu'une fois.
            if len(p) > 25 and p not in vues:
                vues.add(p)
                candidates.append((p, c))
    if not candidates:
        return []
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    mat = vec.fit_transform([normaliser(p) for p, _ in candidates])
    sims = cosine_similarity(vec.transform([etendre_requete(question)]), mat)[0]
    # Bonus pour les phrases du chunk le mieux classé : elles gardent leur contexte.
    bonus = np.array([0.05 if c is chunks[0] else 0.0 for _, c in candidates])
    ordre = np.argsort(sims + bonus)[::-1][:n]
    # On restitue les phrases dans l'ordre du texte pour garder une lecture naturelle.
    return [candidates[i] for i in sorted(ordre)]
