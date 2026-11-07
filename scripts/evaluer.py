"""Évaluation complète d'AMENA : triage et recherche.

Usage :  python scripts/evaluer.py

Triage
    A. Validation croisée PAR GABARIT (GroupKFold) sur le jeu synthétique : les
       variantes d'un même gabarit ne sont jamais à la fois en train et en test,
       sinon le score serait artificiellement gonflé (fuite de données).
    B. Test sur 40 messages ÉCRITS À LA MAIN, jamais vus : la mesure honnête.
       On compare quatre configurations pour montrer l'apport de chaque brique.

Recherche (RAG)
    Pour 23 questions annotées avec leur fiche attendue : Hit@1, Hit@k et MRR.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             f1_score, recall_score)
from sklearn.model_selection import GroupKFold

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from amena.config import FICHIER_TRIAGE, RAPPORT_EVALUATION, TOP_K  # noqa: E402
from amena.ingestion import charger_chunks  # noqa: E402
from amena.recherche import MoteurRecherche  # noqa: E402
from amena.securite import regles_danger  # noqa: E402
from amena.triage import CLASSES, Trieur  # noqa: E402


def metriques(vrais, predits):
    return {
        "accuracy": round(accuracy_score(vrais, predits), 3),
        "f1_macro": round(f1_score(vrais, predits, average="macro", labels=CLASSES), 3),
        "rappel_urgence": round(recall_score(vrais, predits, labels=["urgence"], average="macro"), 3),
    }


def validation_croisee(df, k=5):
    predits = np.empty(len(df), dtype=object)
    for train, test in GroupKFold(n_splits=k).split(df, df["label"], df["gabarit"]):
        trieur = Trieur().entrainer(df["texte"].iloc[train], df["label"].iloc[train])
        predits[test] = trieur.predire_lot(df["texte"].iloc[test], avec_regles=False, avec_seuil=False)
    return metriques(df["label"], predits)


def test_manuel(df_train, df_test):
    trieur = Trieur().entrainer(df_train["texte"], df_train["label"])
    textes, vrais = df_test["texte"].tolist(), df_test["label"].tolist()

    regles_seules = ["urgence" if regles_danger(t) else "non_urgence" for t in textes]
    configs = {
        "modele_seul": trieur.predire_lot(textes, avec_regles=False, avec_seuil=False),
        "modele_+_seuil": trieur.predire_lot(textes, avec_regles=False, avec_seuil=True),
        "modele_+_seuil_+_regles (AMENA)": trieur.predire_lot(textes, avec_regles=True),
    }
    resultats = {nom: metriques(vrais, p) for nom, p in configs.items()}
    resultats["regles_seules"] = {"rappel_urgence": round(
        sum(r == "urgence" for r, v in zip(regles_seules, vrais) if v == "urgence")
        / max(1, vrais.count("urgence")), 3)}

    final = configs["modele_+_seuil_+_regles (AMENA)"]
    erreurs = [{"texte": t, "attendu": v, "predit": p}
               for t, v, p in zip(textes, vrais, final) if v != p]
    rapport = classification_report(vrais, final, labels=CLASSES, zero_division=0)
    matrice = pd.DataFrame(confusion_matrix(vrais, final, labels=CLASSES),
                           index=[f"réel {c}" for c in CLASSES],
                           columns=[f"prédit {c}" for c in CLASSES])
    par_langue = {lg: metriques([v for v, l in zip(vrais, df_test["langue"]) if l == lg],
                                [p for p, l in zip(final, df_test["langue"]) if l == lg])
                  for lg in sorted(df_test["langue"].unique())}
    return resultats, rapport, matrice, erreurs, par_langue


def evaluer_recherche():
    moteur = MoteurRecherche(charger_chunks())
    questions = pd.read_csv(RACINE / "data" / "evaluation" / "questions_rag.csv")
    hit1, hitk, rr = [], [], []
    for _, ligne in questions.iterrows():
        # Le jeu de questions annote des fiches : on évalue la recherche dans les fiches.
        fichiers = [r["metadata"]["source"] for r in moteur.rechercher(ligne["question"], k=TOP_K, types={"fiche"})]
        rang = fichiers.index(ligne["source_attendue"]) + 1 if ligne["source_attendue"] in fichiers else None
        hit1.append(rang == 1)
        hitk.append(rang is not None)
        rr.append(1 / rang if rang else 0)
    return {"n_questions": len(questions), "hit@1": round(float(np.mean(hit1)), 3),
            f"hit@{TOP_K}": round(float(np.mean(hitk)), 3), "mrr": round(float(np.mean(rr)), 3)}


def evaluer_recherche_lois():
    """Recherche dans la bibliothèque juridique : le bon texte est-il retrouvé ?"""
    moteur = MoteurRecherche(charger_chunks())
    questions = pd.read_csv(RACINE / "data" / "evaluation" / "questions_lois.csv")
    hit1, hitk, rr = [], [], []
    for _, ligne in questions.iterrows():
        textes = []
        for r in moteur.rechercher(ligne["question"], k=12, types={"loi"}):
            if r["metadata"]["element"] not in textes:
                textes.append(r["metadata"]["element"])
        textes = [t.removeprefix("loi:") for t in textes][:TOP_K]
        rang = textes.index(ligne["texte_attendu"]) + 1 if ligne["texte_attendu"] in textes else None
        hit1.append(rang == 1)
        hitk.append(rang is not None)
        rr.append(1 / rang if rang else 0)
    return {"n_questions": len(questions), "hit@1": round(float(np.mean(hit1)), 3),
            f"hit@{TOP_K}": round(float(np.mean(hitk)), 3), "mrr": round(float(np.mean(rr)), 3)}


def main():
    df = pd.read_csv(FICHIER_TRIAGE)
    df_test = pd.read_csv(RACINE / "data" / "triage" / "test_manuel.csv")

    print("=" * 70, "\nA. Validation croisée par gabarit (jeu synthétique)\n" + "=" * 70)
    cv = validation_croisee(df)
    print(cv)

    print("\n" + "=" * 70, "\nB. Test sur messages écrits à la main\n" + "=" * 70)
    resultats, rapport, matrice, erreurs, par_langue = test_manuel(df, df_test)
    print(pd.DataFrame(resultats).T.to_string())
    print("\nRapport détaillé (configuration AMENA) :\n" + rapport)
    print("Matrice de confusion :\n" + matrice.to_string())
    print("\nPar langue :")
    print(pd.DataFrame(par_langue).T.to_string())
    print(f"\n{len(erreurs)} erreurs :")
    for e in erreurs:
        print(f"  [{e['attendu']:>11} -> {e['predit']:<11}] {e['texte'][:75]}")

    print("\n" + "=" * 70, "\nC. Recherche (RAG)\n" + "=" * 70)
    rag = evaluer_recherche()
    print("Fiches pratiques :", rag)
    lois = evaluer_recherche_lois()
    print("Bibliothèque juridique :", lois)

    RAPPORT_EVALUATION.parent.mkdir(parents=True, exist_ok=True)
    RAPPORT_EVALUATION.write_text(json.dumps({
        "triage_validation_croisee": cv,
        "triage_test_manuel": resultats,
        "triage_test_manuel_par_langue": par_langue,
        "triage_erreurs": erreurs,
        "recherche": rag,
        "recherche_lois": lois,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport enregistré : {RAPPORT_EVALUATION}")


if __name__ == "__main__":
    main()
