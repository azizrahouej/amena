"""Génère le jeu d'entraînement du module de triage (données SYNTHÉTIQUES).

Pourquoi des données synthétiques ?
    Il n'existe pas de corpus public de messages de femmes victimes de violence en
    Tunisie, et collecter de vrais messages poserait un problème éthique majeur
    (données sensibles au sens de la loi organique 2004-63 sur les données personnelles).
    On construit donc un corpus à partir de gabarits rédigés à la main, en trois
    registres : français, arabe standard et dialecte tunisien écrit en latin (arabizi).

    Le modèle est ensuite évalué sur un jeu de test ÉCRIT À LA MAIN et jamais généré
    (data/triage/test_manuel.csv), pour mesurer honnêtement sa capacité à généraliser.

Les 4 classes :
    urgence      danger immédiat ou idées suicidaires : afficher les numéros d'urgence
    juridique    question sur les droits, la plainte, la loi, le divorce, la protection
    soutien      détresse, besoin d'écoute, doute sur la situation
    information  demande d'orientation : numéro, association, centre, adresse
"""

import random
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from amena.config import FICHIER_TRIAGE  # noqa: E402

random.seed(42)

AUTEURS_FR = ["mon mari", "mon ex-mari", "mon fiancé", "mon frère", "mon père",
              "mon beau-père", "mon patron", "mon voisin", "mon copain", "mon ex"]
AUTEURS_DZ = ["rajli", "ex mte3i", "khatibi", "khouya", "baba", "el patron",
              "jari", "sahbi", "rajel ommi"]
AUTEURS_AR = ["زوجي", "طليقي", "خطيبي", "أخي", "أبي", "مديري في العمل", "جاري"]

GABARITS = {
    "urgence": {
        "fr": [
            "{a} est en train de me frapper, aidez-moi",
            "{a} me menace avec un couteau en ce moment",
            "au secours {a} veut me tuer",
            "je suis enfermée dans la salle de bain, {a} casse la porte",
            "{a} m'a étranglée et il est encore à la maison",
            "j'ai peur qu'il me tue cette nuit",
            "{a} frappe mes enfants maintenant, que faire",
            "je saigne, {a} m'a poussée dans les escaliers",
            "il m'a enfermée dans la maison et a pris mon téléphone",
            "je veux mourir, je n'en peux plus de vivre",
            "je pense à me suicider",
            "j'ai envie d'en finir avec ma vie",
            "{a} m'attend devant la maison avec une arme",
            "urgent {a} me poursuit dans la rue",
            "il a menacé de me brûler ce soir",
        ],
        "dz": [
            "{a} yadhrab fiya tawa, 3aweni",
            "{a} 3andou mous w y9oul bech yo9telni",
            "nkhaf {a} yo9telni lyoum",
            "{a} sakker 3liya fi dar w khdhe tilifouni",
            "3atni {a} 3ale ras w 9a3da nnezef",
            "{a} yadhrab fi wledi tawa",
            "n7eb nmout, ma3adech n7eb n3ich",
            "n7eb na9tel rou7i",
            "{a} 9a3ed yestanna fiya 9odem dar",
            "3aweni 3afak {a} 7ab ye5na9ni",
        ],
        "ar": [
            "{a} يضربني الآن ساعدوني",
            "{a} يهددني بسكين الآن",
            "أخاف أن يقتلني {a} الليلة",
            "{a} حبسني في المنزل وأخذ هاتفي",
            "أريد أن أموت لم أعد أحتمل",
            "أفكر في الانتحار",
            "{a} يضرب أطفالي الآن",
            "النجدة {a} يحاول خنقي",
        ],
    },
    "juridique": {
        "fr": [
            "comment porter plainte contre {a}",
            "est-ce que je peux demander une ordonnance de protection contre {a}",
            "que dit la loi 58 sur la violence psychologique",
            "{a} m'insulte tous les jours, est-ce puni par la loi",
            "est-ce que le viol conjugal est reconnu en Tunisie",
            "j'ai déposé plainte, est-ce que je peux la retirer",
            "comment obtenir un certificat médical pour ma plainte",
            "ai-je droit à un avocat gratuit",
            "{a} ne paie plus la pension alimentaire, que faire légalement",
            "le harcèlement sexuel au travail est-il puni",
            "{a} garde mon salaire, est-ce de la violence économique",
            "la police a refusé ma plainte, est-ce légal",
            "quelles preuves faut-il pour porter plainte",
            "{a} publie mes photos sur facebook, quels sont mes droits",
            "puis-je obtenir la garde des enfants si je quitte {a}",
            "quelle peine risque {a} pour des violences",
        ],
        "dz": [
            "kifech nnajjem n9ayed chekaya 3la {a}",
            "chnowa y9oul el 9anoun 3al {a} elli yadhrab martou",
            "nnajjem nod5el chekaya w ba3d nsa7abha",
            "chnowa lazem bech na3mel chekaya fel police",
            "el police ma 7abouch ya5dhou chekayti, chnowa na3mel",
            "{a} ma y5alasch el nafa9a, kifech n5arjou",
            "andi 7a9 fi avocat bleche",
            "{a} y7ot tsawri fel facebook, chnowa 7a9i",
            "kifech nekhou ordonnance de protection",
        ],
        "ar": [
            "كيف أقدم شكاية ضد {a}",
            "ما هو القانون عدد 58 لسنة 2017",
            "هل يعاقب القانون على العنف المعنوي",
            "هل يمكنني طلب قرار حماية من قاضي الأسرة",
            "هل لي الحق في محامي مجانا",
            "{a} لا يدفع النفقة ماذا أفعل قانونيا",
            "هل التحرش الجنسي في العمل جريمة",
        ],
    },
    "soutien": {
        "fr": [
            "je me sens seule et personne ne me croit",
            "{a} me rabaisse tout le temps, je pense que c'est de ma faute",
            "je ne sais pas si ce que je vis est de la violence",
            "j'ai honte de parler de ce que {a} me fait",
            "je pleure tous les jours depuis des mois",
            "{a} contrôle mon téléphone et mes sorties, c'est normal ?",
            "je n'arrive plus à dormir, j'ai peur tout le temps",
            "ma famille me dit de supporter pour les enfants",
            "je me sens perdue, je ne sais pas quoi faire",
            "{a} s'excuse toujours après, je ne sais plus quoi penser",
            "mon amie est battue par son mari, comment l'aider",
            "j'ai besoin de parler à quelqu'un",
            "je me sens nulle, {a} dit que je ne vaux rien",
        ],
        "dz": [
            "n7es b rou7i wa7di w 7atta 7ad ma ysadda9ni",
            "{a} dima y7a9arni, yemken el 8alta mte3i",
            "ma na3refch ken elli 9a3da n3ich fih 3onf walla le",
            "n7echem n7ki 3la elli ya3mlou fiya {a}",
            "9a3da nebki kol nhar",
            "{a} yraka7 tilifouni w ma y5allinich no5rej",
            "3ayelti t9olli osbri 3al wled",
            "n7eb n7ki m3a 7ad",
            "sa7bti rajelha yadhrabha, kifech n3awenha",
        ],
        "ar": [
            "أشعر بالوحدة ولا أحد يصدقني",
            "{a} يحتقرني دائما وأظن أن الخطأ مني",
            "لا أعرف إن كان ما أعيشه عنفا",
            "أبكي كل يوم ولا أستطيع النوم",
            "عائلتي تقول لي اصبري من أجل الأطفال",
            "أحتاج أن أتحدث مع شخص ما",
        ],
    },
    "information": {
        "fr": [
            "quel est le numéro vert pour les femmes victimes de violence",
            "où trouver un centre d'hébergement à Sfax",
            "y a-t-il une association qui aide les femmes à Sousse",
            "comment contacter l'ATFD",
            "quel numéro appeler pour la garde nationale",
            "où se trouve l'unité spécialisée de police à Tunis",
            "existe-t-il un centre d'écoute près de Bizerte",
            "quels sont les horaires du numéro 1899",
            "je cherche un psychologue gratuit à Gabès",
            "est-ce qu'il y a un foyer pour femmes à Kairouan",
            "quelle association propose une aide juridique gratuite",
            "comment joindre le délégué à la protection de l'enfance",
            "quels sont les numéros d'urgence en Tunisie",
            "quel est le numéro du SAMU",
        ],
        "dz": [
            "chnowa el nomrou el a5dhar mta3 el nsa",
            "win nal9a centre fi sfax",
            "famma jam3iya t3awen el nsa fi sousse",
            "kifech nkallem ATFD",
            "chnowa nomrou el 7aras el watani",
            "win famma blasa nbet fiha fi tounes",
            "famma psychologue blech fi gabes",
            "chnowa nomrou el police",
            "a3tini les numéros d'urgence",
        ],
        "ar": [
            "ما هو الرقم الأخضر للنساء ضحايا العنف",
            "أين يوجد مركز إيواء في صفاقس",
            "هل توجد جمعية تساعد النساء في سوسة",
            "كيف أتصل بالجمعية التونسية للنساء الديمقراطيات",
            "ما هو رقم الحرس الوطني",
            "ما هي أرقام النجدة في تونس",
            "ما هو رقم الشرطة",
            "ما هو رقم الإسعاف",
            "أعطوني أرقام الطوارئ",
        ],
    },
}

AUTEURS = {"fr": AUTEURS_FR, "dz": AUTEURS_DZ, "ar": AUTEURS_AR}

# Petites variations d'écriture réalistes : messages tapés vite sur téléphone.
SUFFIXES = {"fr": ["", "", " svp", " s'il vous plaît", "...", " !!", " ?"],
            "dz": ["", "", " 3afak", " barcha", "...", " !!", " ?"],
            "ar": ["", "", " من فضلكم", "...", " !!", " ؟"]}
PREFIXES = {"fr": ["", "", "bonjour ", "salut, ", "aidez-moi, "],
            "dz": ["", "", "aslema ", "salem, ", "3aslema "],
            "ar": ["", "", "مرحبا ", "السلام عليكم "]}


def variantes(gabarit, langue, n=6):
    """Produit n variantes d'un gabarit en changeant l'auteur et le style."""
    sorties = set()
    for _ in range(n * 3):
        texte = gabarit.format(a=random.choice(AUTEURS[langue]))
        texte = random.choice(PREFIXES[langue]) + texte + random.choice(SUFFIXES[langue])
        if langue != "ar" and random.random() < 0.3:
            texte = texte.lower()
        sorties.add(texte.strip())
        if len(sorties) >= n:
            break
    return sorties


def main():
    lignes = []
    for label, par_langue in GABARITS.items():
        for langue, gabarits in par_langue.items():
            for gabarit in gabarits:
                # Un gabarit sans auteur produit moins de variantes distinctes.
                n = 6 if "{a}" in gabarit else 3
                # L'identifiant de gabarit sert à l'évaluation : les variantes d'un même
                # gabarit ne doivent jamais être à la fois en entraînement et en test.
                gabarit_id = f"{label}_{langue}_{gabarits.index(gabarit):02d}"
                for texte in variantes(gabarit, langue, n):
                    lignes.append({"texte": texte, "label": label, "langue": langue,
                                   "gabarit": gabarit_id})

    df = pd.DataFrame(lignes).drop_duplicates(subset="texte").sample(frac=1, random_state=42)
    FICHIER_TRIAGE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(FICHIER_TRIAGE, index=False, encoding="utf-8-sig")

    print(f"{len(df)} messages écrits dans {FICHIER_TRIAGE}")
    print(df.groupby(["label", "langue"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
