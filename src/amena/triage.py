"""Module de triage : à quel type de besoin correspond le message ?

Classes : urgence, juridique, soutien, information.

Architecture « modèle + garde-fou » :
    1. un classifieur statistique (TF-IDF caractères + mots -> régression logistique),
       léger, explicable et entraînable sans GPU ;
    2. des règles de danger déterministes (securite.regles_danger) qui forcent la
       classe urgence ;
    3. un SEUIL ABAISSÉ pour la classe urgence : si le modèle lui donne au moins
       SEUIL_URGENCE de probabilité, on bascule en urgence.

Pourquoi biaiser vers l'urgence ? Les erreurs n'ont pas le même coût. Une fausse
alerte affiche des numéros d'urgence inutiles ; une urgence manquée laisse une
femme en danger sans réponse adaptée. On maximise donc le RAPPEL de la classe
urgence, quitte à perdre un peu de précision.
"""

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline

from .config import MODELE_TRIAGE
from .securite import normaliser, regles_danger

CLASSES = ["urgence", "juridique", "soutien", "information"]
SEUIL_URGENCE = 0.30


def creer_pipeline():
    return Pipeline([
        ("features", FeatureUnion([
            # n-grammes de caractères : gèrent l'arabizi, les fautes et l'arabe
            ("car", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5),
                                    sublinear_tf=True, min_df=1)),
            # mots et paires de mots : « porter plainte », « numéro vert »
            ("mots", TfidfVectorizer(analyzer="word", ngram_range=(1, 2),
                                     sublinear_tf=True, token_pattern=r"(?u)\b\w+\b")),
        ])),
        ("clf", LogisticRegression(C=5.0, max_iter=3000, class_weight="balanced")),
    ])


class Trieur:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline or creer_pipeline()

    def entrainer(self, textes, labels):
        self.pipeline.fit([normaliser(t) for t in textes], labels)
        return self

    def probabilites(self, texte):
        probas = self.pipeline.predict_proba([normaliser(texte)])[0]
        return dict(zip(self.pipeline.classes_, probas.round(4).tolist()))

    def predire(self, texte, avec_regles=True):
        """Renvoie la décision finale avec son explication."""
        probas = self.probabilites(texte)
        label = max(probas, key=probas.get)
        raison = "modele"

        if probas.get("urgence", 0) >= SEUIL_URGENCE and label != "urgence":
            label, raison = "urgence", f"seuil_urgence>={SEUIL_URGENCE}"
        if avec_regles:
            regle = regles_danger(texte)
            if regle:
                label, raison = "urgence", regle

        return {"label": label, "confiance": probas[label], "probabilites": probas,
                "raison": raison}

    def predire_lot(self, textes, avec_regles=True, avec_seuil=True):
        sorties = []
        for t in textes:
            if avec_seuil:
                sorties.append(self.predire(t, avec_regles)["label"])
            else:
                probas = self.probabilites(t)
                sorties.append(max(probas, key=probas.get))
        return sorties

    def sauvegarder(self, chemin=MODELE_TRIAGE):
        chemin.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.pipeline, chemin)

    @staticmethod
    def charger(chemin=MODELE_TRIAGE):
        return Trieur(joblib.load(chemin))
