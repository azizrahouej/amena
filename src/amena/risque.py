"""Auto-évaluation du niveau de danger (questionnaire indicatif).

Les questions reprennent des facteurs de risque de violence grave largement reconnus dans la
littérature (par exemple le « Danger Assessment » de J. Campbell) : strangulation, menaces de
mort, arme, escalade, séparation récente... Les formulations et les poids sont propres au
projet AMENA. Cet outil N'EST PAS validé cliniquement en Tunisie : il aide une femme à mettre
des mots sur sa situation et à choisir les prochaines étapes, il ne pose aucun diagnostic.

Les réponses ne sont ni enregistrées ni journalisées.
"""

QUESTIONS = [
    {"id": "danger_maintenant", "poids": 0, "critique": True,
     "fr": "Êtes-vous en danger en ce moment même ?",
     "ar": "هل أنت في خطر الآن؟"},
    {"id": "strangulation", "poids": 4, "critique": True,
     "fr": "A-t-il déjà essayé de vous étrangler ou de vous étouffer ?",
     "ar": "هل حاول يوما خنقك أو كتم أنفاسك؟"},
    {"id": "menace_mort", "poids": 4, "critique": False,
     "fr": "A-t-il menacé de vous tuer ?",
     "ar": "هل هددك بالقتل؟"},
    {"id": "arme", "poids": 4, "critique": False,
     "fr": "A-t-il une arme (couteau, arme à feu) ou en a-t-il déjà utilisé une contre vous ?",
     "ar": "هل يملك سلاحا (سكين، سلاح ناري) أو استعمله ضدك من قبل؟"},
    {"id": "peur_mort", "poids": 4, "critique": False,
     "fr": "Pensez-vous qu'il pourrait vous tuer ?",
     "ar": "هل تعتقدين أنه قد يقتلك؟"},
    {"id": "escalade", "poids": 2, "critique": False,
     "fr": "La violence est-elle devenue plus fréquente ou plus grave ces derniers mois ?",
     "ar": "هل أصبح العنف أكثر تكرارا أو أكثر خطورة في الأشهر الأخيرة؟"},
    {"id": "grossesse", "poids": 3, "critique": False,
     "fr": "Vous a-t-il frappée pendant une grossesse ?",
     "ar": "هل ضربك أثناء الحمل؟"},
    {"id": "sexuelle", "poids": 3, "critique": False,
     "fr": "Vous force-t-il à avoir des relations sexuelles ?",
     "ar": "هل يجبرك على علاقات جنسية؟"},
    {"id": "enfants", "poids": 3, "critique": False,
     "fr": "Menace-t-il de faire du mal aux enfants ou de vous les enlever ?",
     "ar": "هل يهدد بإيذاء الأطفال أو بأخذهم منك؟"},
    {"id": "separation", "poids": 2, "critique": False,
     "fr": "Êtes-vous séparée de lui, ou envisagez-vous de partir ?",
     "ar": "هل انفصلت عنه أو تفكرين في المغادرة؟"},
    {"id": "controle", "poids": 2, "critique": False,
     "fr": "Est-il violemment jaloux ou contrôle-t-il vos sorties, votre téléphone, votre argent ?",
     "ar": "هل هو غيور بعنف أو يراقب خروجك وهاتفك ومالك؟"},
    {"id": "suicide_auteur", "poids": 2, "critique": False,
     "fr": "A-t-il menacé de se suicider ?",
     "ar": "هل هدد بالانتحار؟"},
    {"id": "alcool", "poids": 1, "critique": False,
     "fr": "Consomme-t-il de l'alcool ou des drogues de façon excessive ?",
     "ar": "هل يستهلك الكحول أو المخدرات بإفراط؟"},
]

_INDEX = {q["id"]: q for q in QUESTIONS}
SCORE_MAX = sum(q["poids"] for q in QUESTIONS)

RECOMMANDATIONS = {
    "immediat": {
        "fr": ["Appelez maintenant le 197 (police) ou le 193 (garde nationale).",
               "Si vous le pouvez, éloignez-vous de lui : chez une voisine, dans un lieu public.",
               "Si vous ne pouvez pas parler, restez en ligne : l'opérateur posera des questions fermées."],
        "ar": ["اتصلي الآن بالرقم 197 (الشرطة) أو 193 (الحرس الوطني).",
               "إن استطعت، ابتعدي عنه: عند جارة أو في مكان عام.",
               "إن لم تستطيعي الكلام، ابقي على الخط وسيطرح عليك العون أسئلة بسيطة."],
    },
    "eleve": {
        "fr": ["Votre situation présente des signes de danger grave. Vous n'êtes pas seul(e).",
               "Appelez le 1899 (gratuit) pour construire un plan de mise en sécurité.",
               "Préparez un sac de sécurité et confiez-le à une personne de confiance.",
               "Une ordonnance de protection peut l'obliger à s'éloigner de vous et des enfants."],
        "ar": ["وضعك يحمل علامات خطر جدي. لست وحدك.",
               "اتصلي بالرقم الأخضر 1899 مجانا لإعداد خطة حماية.",
               "حضري حقيبة أمان واتركيها عند شخص تثقين به.",
               "يمكن لقرار الحماية أن يلزمه بالابتعاد عنك وعن الأطفال."],
    },
    "modere": {
        "fr": ["Plusieurs signes de risque sont présents. La violence a tendance à s'aggraver.",
               "Parlez-en à une association ou au 1899 pour être conseillée.",
               "Gardez des preuves en lieu sûr : certificats, photos, messages.",
               "Préparez un plan de sécurité au cas où la situation empire."],
        "ar": ["توجد عدة علامات خطر. العنف يميل إلى التفاقم.",
               "تحدثي مع جمعية أو مع الرقم 1899 للحصول على نصيحة.",
               "احتفظي بالأدلة في مكان آمن: شهادات طبية، صور، رسائل.",
               "حضري خطة أمان تحسبا لتدهور الوضع."],
    },
    "faible": {
        "fr": ["Peu de signes de danger grave aujourd'hui, mais toute violence est inacceptable.",
               "Si la situation change, refaites ce questionnaire.",
               "Vous pouvez parler à AMENA ou au 1899 à tout moment."],
        "ar": ["علامات الخطر الجدي قليلة اليوم، لكن كل عنف غير مقبول.",
               "إن تغير الوضع، أعيدي هذا الاستبيان.",
               "يمكنك التحدث مع أمانة أو مع الرقم 1899 في أي وقت."],
    },
}


def questions(langue="fr"):
    langue = langue if langue in ("fr", "ar") else "fr"
    return [{"id": q["id"], "texte": q[langue]} for q in QUESTIONS]


def evaluer(reponses, langue="fr"):
    """reponses : {id_question: bool}. Renvoie le niveau, le score et les recommandations."""
    langue = langue if langue in ("fr", "ar") else "fr"
    oui = {cle for cle, valeur in reponses.items() if valeur and cle in _INDEX}
    score = sum(_INDEX[cle]["poids"] for cle in oui)

    # Certains facteurs, seuls ou combinés, suffisent à classer le risque comme élevé.
    if "danger_maintenant" in oui:
        niveau = "immediat"
    elif ("strangulation" in oui or {"menace_mort", "arme"} <= oui
          or {"menace_mort", "peur_mort"} <= oui or score >= 10):
        niveau = "eleve"
    elif score >= 5:
        niveau = "modere"
    else:
        niveau = "faible"

    return {
        "niveau": niveau,
        "score": score,
        "score_max": SCORE_MAX,
        "facteurs": [_INDEX[cle][langue] for cle in QUESTIONS_ORDONNEES if cle in oui],
        "recommandations": RECOMMANDATIONS[niveau][langue],
    }


QUESTIONS_ORDONNEES = [q["id"] for q in QUESTIONS]
