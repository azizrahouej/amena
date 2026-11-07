"""Briques de sécurité et de confidentialité, utilisées avant tout traitement IA.

1. anonymiser()        retire numéros de téléphone, CIN et e-mails avant tout envoi
                       à un service externe (LLM) : privacy by design.
2. detecter_langue()   français, arabe ou dialecte tunisien écrit en latin (arabizi).
3. normaliser()        uniformise l'écriture (lettres arabes, lettres répétées...).
4. regles_danger()     filet de sécurité déterministe : certaines expressions
                       déclenchent TOUJOURS le mode urgence, quoi que dise le modèle.
"""

import re
import unicodedata

# --- 1. Anonymisation -------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Téléphone tunisien : +216 optionnel puis 8 chiffres, éventuellement espacés.
_TELEPHONE = re.compile(r"(?:\+?216[\s.-]?)?(?:\d[\s.-]?){7}\d\b")


def anonymiser(texte):
    """Remplace les données personnelles identifiantes par des balises neutres."""
    texte = _EMAIL.sub("[EMAIL]", texte)
    # Un numéro de CIN fait aussi 8 chiffres : la même règle le masque.
    texte = _TELEPHONE.sub("[NUMERO]", texte)
    return texte


# --- 2. Détection de langue -------------------------------------------------

_ARABE = re.compile(r"[؀-ۿ]")
# En arabizi, les chiffres 3, 5, 7, 9 remplacent des lettres arabes (ع, خ, ح, ق).
_CHIFFRE_DANS_MOT = re.compile(r"[a-z][3579]|[3579][a-z]", re.IGNORECASE)
_MOTS_DARIJA = {
    "chnowa", "chnoua", "kifech", "kifeh", "barcha", "rajli", "tawa", "famma",
    "mta3", "mte3i", "n7eb", "nheb", "3afak", "aslema", "yadhrab", "ena", "inti",
    "mouch", "ma3adech", "win", "bech", "ken", "elli", "3liya", "fiya", "wa7di",
}


def detecter_langue(texte):
    """Renvoie 'ar', 'dz' (dialecte tunisien en latin) ou 'fr'."""
    if len(_ARABE.findall(texte)) >= max(3, len(texte) * 0.2):
        return "ar"
    mots = set(re.findall(r"[a-z0-9]+", texte.lower()))
    if _CHIFFRE_DANS_MOT.search(texte) or len(mots & _MOTS_DARIJA) >= 1:
        return "dz"
    return "fr"


# --- 3. Normalisation -------------------------------------------------------

_DIACRITIQUES_ARABES = re.compile(r"[ً-ْـ]")  # tashkeel + tatweel


def normaliser(texte):
    """Uniformise le texte pour que des écritures différentes se ressemblent."""
    texte = texte.lower()
    texte = _DIACRITIQUES_ARABES.sub("", texte)
    # Les variantes de alif, ta marbuta et alif maqsura sont ramenées à une forme.
    texte = re.sub("[إأآ]", "ا", texte).replace("ة", "ه").replace("ى", "ي")
    # "barchaaaaa" et "barchaa" deviennent identiques.
    texte = re.sub(r"(.)\1{2,}", r"\1\1", texte)
    # On retire les accents français : les messages tapés vite les omettent souvent.
    texte = "".join(c for c in unicodedata.normalize("NFD", texte)
                    if unicodedata.category(c) != "Mn" or _ARABE.match(c))
    return re.sub(r"\s+", " ", texte).strip()


# --- 4. Règles de danger ----------------------------------------------------

# Expressions qui suffisent à elles seules : menace de mort, arme, suicide, appel au secours.
_DANGER_FORT = [
    r"\b(veut|va|vais|ve) me tuer\b", r"\bme tuer\b", r"\bsuicid", r"\ben finir\b",
    r"\bje veux mourir\b", r"\bmettre fin a (ma|mes) (vie|jours)\b", r"\bau secours\b",
    r"\bvenez vite\b", r"\bcouteau\b", r"\barme\b", r"\betrangl", r"\bavaler toutes\b",
    r"\byo9tel", r"\bna9tel rou7i\b", r"\bn7eb nmout\b", r"\bmous\b",
    r"\bkammel 3la rou7i\b", r"\bye5na9", r"\b5na9",
    # « النجدة ! » est un appel au secours, mais « أرقام النجدة » désigne les numéros d'urgence.
    "يقتل", "انتحار", "انهي حياتي", "اموت", "سكين", r"(?<!ارقام )(?<!رقم )النجده", "خنق",
]
# Une violence décrite au présent est un danger immédiat.
_VIOLENCE = [r"frapp", r"\btape\b", r"\bbat\b", r"gifl", r"\bcasse", r"cogne",
             r"yadhrab", r"ya3tini", r"ykasar", r"yksar", "يضرب", "يكسر"]
_MAINTENANT = [r"maintenant", r"en ce moment", r"\bvient de\b", r"est en train",
               r"\btawa\b", r"\bdkhal\b", "الان", "الآن"]


def _cherche(motifs, texte):
    return next((m for m in motifs if re.search(m, texte)), None)


def regles_danger(texte):
    """Renvoie la règle qui signale un danger immédiat, ou None.

    Ces règles privilégient le RAPPEL (ne rater aucune urgence) au prix de quelques
    fausses alertes : afficher à tort les numéros d'urgence coûte peu, rater une
    femme en danger peut coûter une vie.
    """
    t = normaliser(texte)
    motif = _cherche(_DANGER_FORT, t)
    if motif:
        return f"danger_fort:{motif}"
    violence, maintenant = _cherche(_VIOLENCE, t), _cherche(_MAINTENANT, t)
    if violence and maintenant:
        return f"violence_immediate:{violence}+{maintenant}"
    return None
